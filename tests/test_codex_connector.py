import asyncio
import io
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.tools import codex_connector as connector


def fake_process(monkeypatch,tmp_path,*,image=False,unavailable=False,code=0):
    calls=[]
    monkeypatch.setattr(settings,'CODEX_TRANSPORT','exec')
    monkeypatch.setattr(connector,'DATA',tmp_path)
    monkeypatch.setattr(connector,'command',lambda:['/official/codex'])
    monkeypatch.setattr(connector,'_small_run',lambda args,timeout=15:SimpleNamespace(returncode=0,stdout='Logged in using ChatGPT',stderr=''))
    class Process:
        returncode=code
        pid=99999999
        def __init__(self,args,**kwargs):
            self.args=args;self.kwargs=kwargs;calls.append(self)
        def communicate(self,prompt,timeout):
            self.prompt=prompt
            output=Path(self.args[self.args.index('-o')+1])
            output.write_text('{"ok":true}',encoding='utf-8')
            if image and not unavailable:
                Image.new('RGB',(32,32),'blue').save(output.parent/'image.png')
            return json.dumps({'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':5}}),'private stderr should not escape'
    monkeypatch.setattr(connector.subprocess,'Popen',Process)
    return calls


def test_official_exec_is_isolated_and_does_not_forward_keys(monkeypatch,tmp_path):
    calls=fake_process(monkeypatch,tmp_path)
    monkeypatch.setenv('OPENAI_API_KEY','private-api-key')
    monkeypatch.setenv('CODEX_ACCESS_TOKEN','private-access-token')
    monkeypatch.setattr(settings,'CODEX_MODEL','')
    result=asyncio.run(connector.execute('Synthetic test task only'))
    assert json.loads(result)=={'ok':True}
    args=calls[0].args;env=calls[0].kwargs['env']
    assert '--ignore-user-config' in args and '--ignore-rules' in args and '--ephemeral' in args
    assert args[args.index('--sandbox')+1]=='read-only' and 'shell' not in calls[0].kwargs
    for feature in ['shell_tool','multi_agent','apps','plugins','image_generation']:
        assert any(args[i:i+2]==['--disable',feature] for i in range(len(args)-1))
    assert 'OPENAI_API_KEY' not in env and 'CODEX_ACCESS_TOKEN' not in env
    assert args[-2:]==['--','-'] and '--model' not in args
    assert 'Synthetic test task only' in calls[0].prompt
    receipt=json.loads(next(tmp_path.rglob('receipt.json')).read_text())
    assert receipt['usage']['input_tokens']==10


def test_image_requires_real_file_not_json_success(monkeypatch,tmp_path):
    calls=fake_process(monkeypatch,tmp_path,image=True,unavailable=True)
    with pytest.raises(ValueError,match='真实图片'):
        asyncio.run(connector.execute('Synthetic image test',image_output=True))
    assert len(calls)==1
    fake_process(monkeypatch,tmp_path,image=True)
    raw=asyncio.run(connector.execute('Synthetic image test',image_output=True))
    with Image.open(io.BytesIO(raw)) as im:assert im.size==(32,32)


def test_no_api_auth_fallback_or_error_output_leak(monkeypatch,tmp_path):
    calls=fake_process(monkeypatch,tmp_path)
    monkeypatch.setattr(connector,'_small_run',lambda args,timeout=15:SimpleNamespace(returncode=0,stdout='Logged in using an API key',stderr=''))
    with pytest.raises(ValueError,match='ChatGPT'):
        asyncio.run(connector.execute('Synthetic test'))
    assert not calls
    calls=fake_process(monkeypatch,tmp_path,code=1)
    with pytest.raises(ValueError) as e:asyncio.run(connector.execute('Synthetic test'))
    assert 'private stderr' not in str(e.value) and len(calls)==1


def test_codex_selection_preserves_api_and_installer_has_no_credentials(monkeypatch,tmp_path):
    from app.core import paths
    for name in ['AI_PROVIDER','IMAGE_PROVIDER','LOCAL_GPT_API_KEY','LOCAL_GPT_BASE_URL','DEFAULT_TEXT_MODEL','DEFAULT_VISION_MODEL','DEFAULT_INFERENCE_MODEL','IMAGE_API_KEY','IMAGE_API_BASE_URL','IMAGE_API_MODEL','IMAGE_EDIT_PROVIDER','CODEX_MODEL']:
        monkeypatch.setattr(settings,name,getattr(settings,name))
    monkeypatch.setattr(settings,'LOCAL_GPT_API_KEY','private-text-key')
    monkeypatch.setattr(settings,'LOCAL_GPT_BASE_URL','https://text.example/v1')
    monkeypatch.setattr(settings,'IMAGE_API_KEY','private-image-key')
    monkeypatch.setattr(settings,'IMAGE_API_BASE_URL','https://image.example/v1')
    monkeypatch.setattr(settings,'IMAGE_PROVIDER','chatgpt_desktop')
    monkeypatch.setattr(connector,'status',lambda:{'installed':True,'chatgpt_logged_in':True,'version':'synthetic','detail':'fixture','model_requests':0})
    # The installer reads source files before ROOT is redirected for config writes.
    with TestClient(app) as c:
        import zipfile
        archive=zipfile.ZipFile(io.BytesIO(c.get('/api/codex/installer').content))
        assert 'scripts/install_codex.ps1' in archive.namelist()
        assert all(b'private-text-key' not in archive.read(n) for n in archive.namelist())
        monkeypatch.setattr(paths,'ROOT',tmp_path)
        r=c.put('/api/studio/config',json={'text_provider':'codex_cli','codex_model':''})
        assert r.status_code==200,r.text
        assert settings.AI_PROVIDER=='codex_cli' and settings.image_provider=='chatgpt_desktop'
        assert settings.LOCAL_GPT_API_KEY=='private-text-key' and settings.LOCAL_GPT_BASE_URL=='https://text.example/v1'
        r=c.put('/api/studio/config',json={'image_provider':'codex_cli','use_for_repairs':False})
        assert r.status_code==200,r.text
        assert settings.IMAGE_API_KEY=='private-image-key' and settings.IMAGE_API_BASE_URL=='https://image.example/v1'
        assert 'private-text-key' not in r.text and 'private-image-key' not in r.text
        assert c.get('/api/codex/status',headers={'Origin':'https://evil.example'}).status_code==403


def test_codex_llm_and_images_use_automatic_adapter(monkeypatch):
    from app.tools.llm_client import LLMClient
    from app.tools.image_gen import ImageGeneratorClient
    calls=[]
    async def execute(prompt,images=None,image_output=False):
        calls.append((prompt,images,image_output))
        if not image_output:return '{"ok":true}'
        stream=io.BytesIO();Image.new('RGB',(32,32),'blue').save(stream,format='PNG');return stream.getvalue()
    monkeypatch.setattr(connector,'execute',execute)
    monkeypatch.setattr(settings,'AI_PROVIDER','codex_cli')
    monkeypatch.setattr(settings,'IMAGE_PROVIDER','codex_cli')
    monkeypatch.setattr(settings,'CODEX_MODEL','')
    with TestClient(app):
        assert asyncio.run(LLMClient().generate_json('synthetic'))=={'ok':True}
        url=asyncio.run(ImageGeneratorClient()._generate_image('synthetic','',32,32,'flat',[]))
        assert url.startswith('/media/') and len(calls)==2 and calls[-1][-1]


def test_timeout_terminates_own_process_tree_and_does_not_retry(monkeypatch,tmp_path):
    fake_process(monkeypatch,tmp_path)
    calls=[];kills=[]
    class TimeoutProcess:
        pid=99999999
        def __init__(self,*args,**kwargs):self.count=0;calls.append(self)
        def communicate(self,*args,**kwargs):
            self.count+=1
            if self.count==1:raise connector.subprocess.TimeoutExpired('synthetic',1)
            return '', ''
        def kill(self):kills.append('native-kill')
    monkeypatch.setattr(connector.subprocess,'Popen',TimeoutProcess)
    monkeypatch.setattr(connector.subprocess,'run',lambda args,**kwargs:kills.append(args))
    with pytest.raises(ValueError,match='超时'):
        asyncio.run(connector.execute('synthetic'))
    assert len(calls)==1 and kills

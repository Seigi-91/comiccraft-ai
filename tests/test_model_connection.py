import asyncio
import base64
from io import BytesIO
import httpx
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.tools.image_gen import ImageGeneratorClient


def test_local_config_persistence_and_key_redaction(monkeypatch, tmp_path):
    from app.core import paths
    monkeypatch.setattr(paths, 'ROOT', tmp_path)
    for name in ['IMAGE_PROVIDER','IMAGE_API_BASE_URL','IMAGE_API_MODEL','IMAGE_API_KEY','IMAGE_EDIT_PROVIDER','IMAGE_EDIT_BASE_URL','IMAGE_EDIT_MODEL','IMAGE_EDIT_API_KEY']:
        monkeypatch.setattr(settings, name, getattr(settings, name))
    monkeypatch.setattr(settings, 'ENABLE_LOCAL_SETTINGS', True)
    with TestClient(app) as c:
        payload = {'image_provider':'openai','api_key':'test-secret-value','image_model':'image-test'}
        r = c.put('/api/studio/config', json=payload)
        assert r.status_code == 200
        assert 'test-secret-value' not in r.text
        assert r.json()['image_key_configured'] is True
        assert settings.AI_PROVIDER == 'chatgpt_desktop'
        assert settings.IMAGE_EDIT_API_KEY == 'test-secret-value'
        assert 'test-secret-value' in (tmp_path/'.env').read_text()
        assert c.put('/api/studio/config', json=payload, headers={'Origin':'https://evil.example'}).status_code == 403
        assert c.put('/api/studio/config', json={**payload,'image_base_url':'file:///tmp'}).status_code == 422
        r = c.put('/api/studio/config', json={'image_provider':'chatgpt_desktop','clear_key':True})
        assert r.status_code == 422
        r = c.put('/api/studio/config', json={'image_provider':'openai','clear_key':True})
        assert r.status_code == 200 and not r.json()['image_key_configured']


def test_image_api_generation_and_reference_edit(monkeypatch):
    import app.tools.image_gen as module
    monkeypatch.setattr(settings, 'IMAGE_PROVIDER', 'openai')
    monkeypatch.setattr(settings, 'IMAGE_API_BASE_URL', 'https://images.example/v1')
    monkeypatch.setattr(settings, 'IMAGE_API_KEY', 'test-key')
    monkeypatch.setattr(settings, 'IMAGE_API_MODEL', 'image-test')
    from app.tools.media import save_image_bytes
    stream=BytesIO();Image.new('RGB',(16,16),'red').save(stream,format='PNG')
    raw=stream.getvalue();reference=save_image_bytes(raw)
    requests=[]
    def handle(request):
        requests.append(request)
        assert request.headers['authorization']=='Bearer test-key'
        return httpx.Response(200,json={'data':[{'b64_json':base64.b64encode(raw).decode()}]})
    original=httpx.AsyncClient
    monkeypatch.setattr(module.httpx,'AsyncClient',lambda **kwargs: original(transport=httpx.MockTransport(handle),**kwargs))
    client=ImageGeneratorClient()
    async def run():
        assert (await client._generate_image('test','',1024,1024,'comic',[])).startswith('/media/')
        assert (await client._generate_image('test','',1024,1024,'comic',[reference])).startswith('/media/')
    asyncio.run(run())
    assert requests[0].url.path=='/v1/images/generations'
    assert requests[1].url.path=='/v1/images/edits'
    assert b'name="image[]"' in requests[1].content
    assert b'image-test' in requests[0].content


def test_text_connection_independent_and_persisted(monkeypatch, tmp_path):
    from app.core import paths
    from app.core.config import Settings
    monkeypatch.setattr(paths, 'ROOT', tmp_path)
    names = ['AI_PROVIDER','LOCAL_GPT_BASE_URL','LOCAL_GPT_API_KEY','DEFAULT_TEXT_MODEL','DEFAULT_INFERENCE_MODEL','DEFAULT_VISION_MODEL','IMAGE_PROVIDER','IMAGE_API_BASE_URL','IMAGE_API_MODEL','IMAGE_API_KEY']
    for name in names:
        monkeypatch.setattr(settings, name, getattr(settings, name))
    monkeypatch.setattr(settings, 'AI_PROVIDER', 'chatgpt_desktop')
    monkeypatch.setattr(settings, 'IMAGE_PROVIDER', None)
    with TestClient(app) as c:
        payload = {'text_provider':'local_http','text_base_url':'https://text.example/v1','text_model':'writer-model','vision_model':'vision-model','text_api_key':'private-text-key'}
        r=c.put('/api/studio/config',json=payload)
        assert r.status_code==200 and 'private-text-key' not in r.text
        assert r.json()['provider']=='local_http' and r.json()['image_provider']=='chatgpt_desktop'
        assert r.json()['text_key_configured'] is True
        restored=Settings(_env_file=tmp_path/'.env')
        assert restored.DEFAULT_TEXT_MODEL=='writer-model' and restored.DEFAULT_INFERENCE_MODEL=='writer-model'
        assert restored.DEFAULT_VISION_MODEL=='vision-model' and restored.LOCAL_GPT_API_KEY=='private-text-key'
        assert restored.image_provider=='chatgpt_desktop'
        c.put('/api/studio/config',json={**payload,'text_api_key':None})
        assert settings.LOCAL_GPT_API_KEY=='private-text-key'
        assert c.put('/api/studio/config',json={**payload,'text_base_url':'file:///tmp'}).status_code==422
        assert c.put('/api/studio/config',json={**payload,'text_model':''}).status_code==422
        assert c.put('/api/studio/config',json=payload,headers={'Origin':'https://evil.example'}).status_code==403
        r=c.put('/api/studio/config',json={**payload,'text_provider':'chatgpt_desktop','clear_text_key':True})
        assert r.status_code==422
        r=c.put('/api/studio/config',json={**payload,'clear_text_key':True})
        assert r.status_code==200 and r.json()['text_key_configured'] is False


def test_legacy_http_images_preserved_when_text_switches(monkeypatch, tmp_path):
    from app.core import paths
    monkeypatch.setattr(paths,'ROOT',tmp_path)
    for name in ['AI_PROVIDER','LOCAL_GPT_BASE_URL','LOCAL_GPT_API_KEY','DEFAULT_TEXT_MODEL','DEFAULT_INFERENCE_MODEL','DEFAULT_VISION_MODEL','IMAGE_PROVIDER','IMAGE_API_BASE_URL','IMAGE_API_KEY','IMAGE_API_MODEL']:
        monkeypatch.setattr(settings,name,getattr(settings,name))
    monkeypatch.setattr(settings,'AI_PROVIDER','local_http')
    monkeypatch.setattr(settings,'IMAGE_PROVIDER',None)
    monkeypatch.setattr(settings,'LOCAL_GPT_BASE_URL','https://old.example/v1')
    monkeypatch.setattr(settings,'LOCAL_GPT_API_KEY','old-image-key')
    with TestClient(app) as c:
        r=c.put('/api/studio/config',json={'text_provider':'codex_cli','text_model':'writer','vision_model':'vision'})
        assert r.status_code==200
        assert settings.IMAGE_PROVIDER=='openai'
        assert settings.IMAGE_API_BASE_URL=='https://old.example/v1' and settings.IMAGE_API_KEY=='old-image-key'
        assert settings.IMAGE_API_MODEL==settings.DEFAULT_IMAGE_MODEL


def test_text_and_vision_api_protocol(monkeypatch):
    import json
    import app.tools.llm_client as module
    from app.tools.media import save_image_bytes
    monkeypatch.setattr(settings,'AI_PROVIDER','local_http')
    monkeypatch.setattr(settings,'LOCAL_GPT_BASE_URL','https://text.example/v1')
    monkeypatch.setattr(settings,'LOCAL_GPT_API_KEY','text-test-key')
    monkeypatch.setattr(settings,'DEFAULT_TEXT_MODEL','writer')
    monkeypatch.setattr(settings,'DEFAULT_VISION_MODEL','vision')
    stream=BytesIO();Image.new('RGB',(16,16),'blue').save(stream,format='PNG')
    reference=save_image_bytes(stream.getvalue())
    requests=[]
    def handle(request):
        assert request.url.path=='/v1/chat/completions'
        assert request.headers['authorization']=='Bearer text-test-key'
        requests.append(json.loads(request.content))
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"ok":true}'}}]})
    original=httpx.AsyncClient
    monkeypatch.setattr(module.httpx,'AsyncClient',lambda **kwargs: original(transport=httpx.MockTransport(handle),**kwargs))
    async def run():
        assert await module.LLMClient().generate_json('outline')=={'ok':True}
        assert await module.VisionLLMClient().review_image(reference,'review')=={'ok':True}
    asyncio.run(run())
    assert requests[0]['model']=='writer' and requests[0]['messages'][0]['content']=='outline'
    assert requests[1]['model']=='vision'
    assert requests[1]['messages'][0]['content'][1]['image_url']['url'].startswith('data:image/png;base64,')

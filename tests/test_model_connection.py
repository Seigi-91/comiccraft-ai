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

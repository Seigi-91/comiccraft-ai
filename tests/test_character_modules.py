from fastapi.testclient import TestClient
from app.main import app
from tests.test_studio_workflow import pending


def test_modules_outfits_and_generation_context():
    with TestClient(app) as c:
        p=c.post('/api/projects',json={'name':'服装测试'}).json()
        cid=c.post(f"/api/projects/{p['id']}/characters",params={'name':'小雨','appearance_description':'黑色短发'}).json()['character_id']
        root=f"/api/projects/{p['id']}/characters"
        original=c.get(root).json()[0]
        assert original['modules']['appearance']=='黑色短发'
        data={**original['modules'],'personality':'勇敢细心','voice':'说话简短','outfits':[{'id':'rain','name':'雨衣','description':'红色雨衣','occasion':'雨夜'},{'id':'daily','name':'日常装','description':'白衬衣','occasion':'晴天'}],'active_outfit_id':'rain'}
        assert c.put(root+'/'+cid+'/modules',json=data).status_code==200
        assert c.get(root+'/'+cid).json()['modules']['personality']=='勇敢细心'
        data['active_outfit_id']='missing'
        assert c.put(root+'/'+cid+'/modules',json=data).status_code==422
        data['active_outfit_id']='daily'
        assert c.put(root+'/'+cid+'/modules',json=data).status_code==200
        assert c.get(root).json()[0]['modules']['active_outfit_id']=='daily'
        assert c.put('/api/projects/wrong/characters/'+cid+'/modules',json=data).status_code==404
        chapter=c.post(f"/api/projects/{p['id']}/chapters",json={'title':'换装之后'}).json()
        c.post('/api/tasks/generate-chapter',json={'project_id':p['id'],'chapter_id':chapter['id']})
        prompt=pending(c,chapter['id'])[1]['prompt']
        assert '勇敢细心' in prompt and '白衬衣' in prompt and 'active_outfit' in prompt
        data['outfits']=[];data['active_outfit_id']=None
        assert c.put(root+'/'+cid+'/modules',json=data).status_code==200

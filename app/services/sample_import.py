"""Import bundled, pre-generated artwork without contacting any model service."""
import asyncio
import json
from uuid import uuid5, NAMESPACE_URL
from sqlalchemy import select
from app.core.paths import ROOT
from app.models.orm import Project, Chapter, Task, Panel, CharacterProfile, CharacterDetails, ProductionRecord, ProjectStatus, Phase, TaskStatus, PanelStatus
from app.tools.media import save_image_bytes

sample_lock = asyncio.Lock()


async def import_rain_night(db):
    from app.api.routes.editing import snapshot
    from app.agents.layout_artist import LayoutArtistAgent
    project_id = str(uuid5(NAMESPACE_URL, 'comiccraft:bundled:rain-night:v1'))
    chapter_id = str(uuid5(NAMESPACE_URL, project_id + ':chapter'))
    async with sample_lock:
        if await db.get(Project, project_id):
            return {'project_id': project_id, 'chapter_id': chapter_id, 'reused': True, 'model_calls': 0}
        source = ROOT / 'outputs/rain-night-light'
        production = json.loads((source / 'production.json').read_text(encoding='utf-8'))
        images = []
        for panel in production['panels']:
            images.append(save_image_bytes((source / (panel['slug']+'.png')).read_bytes()))
        reference = save_image_bytes((source / 'characters/characters.png').read_bytes())
        character = {'name': '小雨', 'appearance': '成年女性，黑色齐下巴短发、棕眼，红色连帽雨衣兜帽放下，黑色挎包。',
                     'reference_image_url': reference, 'personality': '安静、细心，愿意照顾弱小生命。'}
        outline = {'title':'雨夜留灯','world_view':'雨夜旧书店，冷蓝街巷与暖黄色灯光。',
                   'characters':[character], 'outline':[{'beat':p['title'],'description':p['caption']} for p in production['panels']]}
        board = {'layout_type':'条漫','panels':[{'index':p['index'],'shot_type':'远景' if p['index']==5 else '中景',
                 'perspective':'平视','composition':{'description':p['title']},'action':p['prompt']} for p in production['panels']]}
        captions = [p['caption'] for p in production['panels']]
        bubbles = {'bubbles':[{'panel_index':i,'text':text[:60],'character':None,'bubble_type':'narration',
                     'position':{'x':73,'y':10},'size':{'width':48,'height':16},'font_size':24} for i,text in enumerate(captions)]}
        panels = [{'index':i,'image_url':url,'status':'passed','shot':board['panels'][i]} for i,url in enumerate(images)]
        final = await LayoutArtistAgent().compose_final(panels, bubbles)
        project = Project(id=project_id,user_id='default_user',name='雨夜留灯 · 可编辑示例',description='预生成示例；导入不调用模型，重复导入不会覆盖修改。',inspiration='在雨夜，为需要归处的生命留一盏灯。',status=ProjectStatus.COMPLETED)
        chapter = Chapter(id=chapter_id,project_id=project_id,title='雨夜留灯',outline=outline,storyboard=board,dialogues=bubbles,phase=Phase.COMPLETED)
        db.add(project);await db.flush();db.add(chapter);await db.flush()
        cid=str(uuid5(NAMESPACE_URL,project_id+':character'))
        db.add(CharacterProfile(id=cid,project_id=project_id,name='小雨',appearance_description=character['appearance'],reference_image_url=reference,is_confirmed=True))
        await db.flush()
        db.add(CharacterDetails(character_id=cid,data={'identity':'雨夜归来的书店访客','personality':character['personality'],'appearance':character['appearance'],'outfits':[{'id':'rain','name':'红色雨衣','description':'红色连帽雨衣，兜帽放下；黑裤、棕靴、黑挎包。','occasion':'雨夜'}],'active_outfit_id':'rain'}))
        for i,url in enumerate(images):
            db.add(Panel(id=str(uuid5(NAMESPACE_URL,chapter_id+str(i))),chapter_id=chapter_id,index=i,image_url=url,status=PanelStatus.PASSED,
                         review_result={'origin':'bundled_example','not_live_model_review':True}))
        state={'project_id':project_id,'current_chapter':chapter_id,'outline':outline,'storyboard':board,'dialogues':bubbles,
               'characters':[character],'panels':panels,'final_comic':final,'next_node':'done','phase':'completed',
               'provenance':{'origin':'bundled_example','model_calls':0,'historical_parameters':'unknown','note':'预生成素材导入；passed 表示可编辑示例就绪，不是本次模型审核。'}}
        task=Task(id=str(uuid5(NAMESPACE_URL,chapter_id+':import')),project_id=project_id,chapter_id=chapter_id,type='sample_import',status=TaskStatus.COMPLETED,result={'state':state,'final_comic':final})
        db.add(task);await db.flush();await snapshot(db,chapter,[task],'示例原稿（预生成素材，无模型调用）')
        await db.commit()
        return {'project_id':project_id,'chapter_id':chapter_id,'reused':False,'model_calls':0}

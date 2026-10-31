// Isolated database on 8016. Synthetic uploads test workflow, not model quality.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'C:/Users/Lenovo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const base=process.env.PRODUCTION_TEST_URL||'http://127.0.0.1:8016',pid='a75ddfc1-9af0-4b35-a14b-a2bd99eac241';
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 const chapters=await(await page.request.get(base+'/api/projects/'+pid+'/chapters')).json();const cid=chapters[0].id,source=chapters[0].panels[0].image_url;
 await page.goto(base+'/projects/'+pid);await page.getByRole('button',{name:'素材生产工作台：快照 / 批量 / 实验 / 特效',exact:true}).click();
 const captured=page.waitForResponse(r=>r.url().endsWith('/capture'));await page.getByRole('button',{name:'记录当前各格设定快照',exact:true}).click();if((await captured).status()!==200)throw Error('Capture failed');
 await page.getByText('当前设定补录，历史生成参数未知',{exact:false}).first().waitFor();
 await page.getByRole('button',{name:'② 批量任务',exact:true}).click();await page.locator('[aria-label="素材生产工作台"] input[type=checkbox]').first().check();
 const created=page.waitForResponse(r=>r.url().endsWith('/batches')&&r.request().method()==='POST');await page.getByRole('button',{name:'创建暂停批次',exact:true}).click();if((await created).status()!==200)throw Error('Batch create failed');
 await page.getByRole('button',{name:'③ 参数实验',exact:true}).click();await page.getByRole('textbox',{name:'实验风格 1',exact:true}).fill('暖色柔光测试');await page.getByRole('textbox',{name:'实验风格 2',exact:true}).fill('冷色清晰线条测试');
 const experiment=page.waitForResponse(r=>r.url().endsWith('/experiments'));await page.getByRole('button',{name:'创建两组实验候选批次',exact:true}).click();const exp=await experiment;if(exp.status()!==200)throw Error(await exp.text());const bid=(await exp.json()).id;
 const card=page.getByRole('article').filter({hasText:'第1格参数实验'}).first();await card.getByRole('button',{name:'开始 / 继续',exact:true}).click();
 for(let i=0;i<2;i++){
  const file=card.locator('input[aria-label="上传实验结果"]');await file.waitFor({state:'attached',timeout:20000});
  const response=page.waitForResponse(r=>r.url().endsWith('/reply')&&r.request().method()==='POST');await file.setInputFiles('data/repair-test-upload.png');if((await response).status()!==200)throw Error('Experiment upload failed');
  await card.getByAltText('实验候选').nth(i).waitFor({timeout:20000});
 }
 let batch=(await(await page.request.get(base+'/api/production/projects/'+pid+'/batches')).json()).find(x=>x.id===bid);if(batch.status!=='completed')throw Error('Batch not complete');
 if((await(await page.request.get(base+'/api/projects/'+pid+'/chapters/'+cid)).json()).panels[0].image_url!==source)throw Error('Experiment overwrote source');
 await page.locator('[aria-label="素材生产工作台"]').screenshot({path:'data/production-experiments.png'});
 await page.getByRole('button',{name:'④ 特效层',exact:true}).click();await page.getByRole('button',{name:'＋ 添加特效层',exact:true}).click();await page.getByRole('combobox',{name:'特效类型 1',exact:true}).selectOption('warm_glow');
 const preview=page.waitForResponse(r=>r.url().endsWith('/effects/preview'));await page.getByRole('button',{name:'预览特效',exact:true}).click();if((await preview).status()!==200)throw Error('Effect preview failed');await page.getByAltText('特效预览',{exact:true}).waitFor();
 const saved=page.waitForResponse(r=>r.url().endsWith('/effects/save'));await page.getByRole('button',{name:'保存特效并更新成稿',exact:true}).click();const sr=await saved;if(sr.status()!==200)throw Error(await sr.text());
 const config=await(await page.request.get(base+'/api/production/chapters/'+cid+'/effects')).json();if(config.effects['0'][0].kind!=='warm_glow')throw Error('Effect not saved');
 await page.reload();await page.getByRole('button',{name:'素材生产工作台：快照 / 批量 / 实验 / 特效',exact:true}).click();await page.getByRole('button',{name:'④ 特效层',exact:true}).click();await page.getByRole('combobox',{name:'特效类型 1',exact:true}).waitFor();
 if(await page.getByRole('combobox',{name:'特效类型 1',exact:true}).inputValue()!=='warm_glow')throw Error('Effect reload failed');
 await page.setViewportSize({width:390,height:844});await page.locator('[aria-label="素材生产工作台"]').screenshot({path:'data/production-mobile.png'});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2))throw Error('Mobile overflow');if(errors.length)throw Error(errors.join(','));
 console.log(JSON.stringify({ok:true,checks:['current snapshots','paused batch creation','two experimental handoffs','candidate comparison without overwrite','effect preview/save/reload','mobile layout','no JS errors'],real_model_inference:false}));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});

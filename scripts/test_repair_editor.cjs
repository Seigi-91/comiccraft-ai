// Isolated SQLite copy, synthetic upload: verifies workflow, not model quality.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'C:/Users/Lenovo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const base=process.env.REPAIR_TEST_URL||'http://127.0.0.1:8015';
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.on('dialog',d=>d.accept());const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const pid='a75ddfc1-9af0-4b35-a14b-a2bd99eac241';const chapters=await(await page.request.get(base+'/api/projects/'+pid+'/chapters')).json();const cid=chapters[0].id;const original=chapters[0].panels[0].image_url;
 await page.goto(base+'/projects/'+pid);await page.getByRole('button',{name:'圈选局部精修',exact:true}).click();
 const image=page.getByAltText('圈选精修原图');await image.scrollIntoViewIfNeeded();const b=await image.boundingBox();
 await page.mouse.move(b.x+b.width*.18,b.y+b.height*.32);await page.mouse.down();await page.mouse.move(b.x+b.width*.34,b.y+b.height*.32,{steps:8});await page.mouse.move(b.x+b.width*.34,b.y+b.height*.43,{steps:8});await page.mouse.move(b.x+b.width*.18,b.y+b.height*.43,{steps:8});await page.mouse.up();
 await page.getByText('已选 1 个区域',{exact:true}).waitFor();await page.getByRole('textbox',{name:'局部修复要求',exact:true}).fill('合成测试图，用于验证蒙版保护与回退');
 await page.getByRole('button',{name:'创建 ChatGPT 精修任务',exact:true}).click();
 await page.locator('input[aria-label="上传精修结果"]').waitFor({state:'attached'});await page.locator('input[aria-label="上传精修结果"]').setInputFiles('data/repair-test-upload.png');
 await page.getByAltText('精修后',{exact:true}).waitFor();await page.getByRole('slider',{name:'修复前后对比',exact:true}).focus();await page.keyboard.press('ArrowRight');
 await page.locator('[aria-label="局部蒙版精修"]').screenshot({path:'data/repair-editor-desktop.png'});
 const done=page.waitForResponse(r=>r.url().endsWith('/accept'));await page.getByRole('button',{name:'采用候选并更新成稿',exact:true}).click();const accepted=await done;if(accepted.status()!==200)throw Error(await accepted.text());
 const after=await(await page.request.get(base+'/api/projects/'+pid+'/chapters/'+cid)).json();if(after.panels[0].image_url===original)throw Error('Candidate not adopted');
 await page.reload();await page.getByRole('button',{name:'圈选局部精修',exact:true}).click();await page.getByText('版本回退（整个章节）',{exact:true}).click();
 const versions=await(await page.request.get(base+'/api/editing/'+cid+'/versions')).json();const before=versions.find(v=>v.label==='采用局部精修前');await page.getByRole('combobox',{name:'精修回退版本',exact:true}).selectOption(before.id);
 const restored=page.waitForResponse(r=>r.url().endsWith('/restore'));await page.getByRole('button',{name:'回退整个章节',exact:true}).click();if((await restored).status()!==200)throw Error('Restore failed');
 const final=await(await page.request.get(base+'/api/projects/'+pid+'/chapters/'+cid)).json();if(final.panels[0].image_url!==original)throw Error('Original not restored');
 await page.setViewportSize({width:390,height:844});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2))throw Error('Mobile overflow');if(errors.length)throw Error(errors.join(','));
 console.log(JSON.stringify({ok:true,checks:['lasso selection','desktop handoff','upload','comparison slider','explicit adopt','final update','version restore','mobile layout','no JS errors'],model_inference_tested:false}));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});

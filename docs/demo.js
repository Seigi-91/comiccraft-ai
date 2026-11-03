'use strict';
const canvas=document.querySelector('#panel'),ctx=canvas.getContext('2d'),image=new Image();
const fiftyFive = new URLSearchParams(location.search).get('sample') === 'fifty-five';
const initial = fiftyFive
 ? {x:8,y:5,w:48,h:17,tx:57,ty:41,text:'先服药。',kind:'dialogue'}
 : {x:64,y:4,w:32,h:18,tx:48,ty:26,text:'别怕，跟我回家吧。',kind:'dialogue'};
if (fiftyFive) {
 document.querySelector('#sample-info').hidden = false;
 document.querySelector('#panel').setAttribute('aria-label', '《我们得谈谈五十五号》气泡编辑画布');
}
let state={...initial},ready=false,drag=null;
const status=document.querySelector('#status'),fields=['x','y','w','h','tx','ty','text','kind'];
function clamp(v,a,b){return Math.max(a,Math.min(b,v));}
function normalize(){state.w=clamp(state.w,25,65);state.h=clamp(state.h,14,40);state.x=clamp(state.x,0,100-state.w);state.y=clamp(state.y,0,100-state.h);state.tx=clamp(state.tx,0,100);state.ty=clamp(state.ty,0,100);}
function sync(){normalize();for(const id of fields){const el=document.getElementById(id);if(id==='x')el.max=100-state.w;if(id==='y')el.max=100-state.h;el.value=state[id];}}
function render(handles=true){
 if(!ready)return;
 normalize();const {x,y,w,h,tx,ty}=Object.fromEntries(['x','y','w','h','tx','ty'].map(k=>[k,state[k]*(['x','w','tx'].includes(k)?canvas.width:canvas.height)/100]));
 ctx.clearRect(0,0,canvas.width,canvas.height);ctx.drawImage(image,0,0,canvas.width,canvas.height);ctx.fillStyle='#fff';ctx.strokeStyle='#20202b';ctx.lineWidth=4;
 if(state.kind==='dialogue'){ctx.beginPath();ctx.moveTo(x+w*.25,y+h*.7);ctx.lineTo(tx,ty);ctx.lineTo(x+w*.65,y+h*.7);ctx.closePath();ctx.fill();ctx.stroke();}
 if(state.kind==='thought'){for(let i=1;i<=3;i++){const k=i/4;ctx.beginPath();ctx.ellipse(x+w/2+(tx-x-w/2)*k,y+h/2+(ty-y-h/2)*k,18-i*4,18-i*4,0,0,Math.PI*2);ctx.fill();ctx.stroke();}}
 ctx.beginPath();ctx.roundRect(x,y,w,h,state.kind==='narration'?5:55);ctx.fill();ctx.stroke();
 let size=38,lines=[];
 function wrap(){lines=[];for(const paragraph of state.text.split('\n')){let line='';for(const char of Array.from(paragraph)){if(ctx.measureText(line+char).width>w-42&&line){lines.push(line);line='';}line+=char;}lines.push(line);}}
 do{ctx.font=`${size}px system-ui,"Microsoft YaHei",sans-serif`;wrap();if(lines.length*size*1.3<=h-30||size<=16)break;size-=2;}while(true);
 ctx.save();ctx.beginPath();ctx.rect(x+12,y+10,w-24,h-20);ctx.clip();ctx.fillStyle='#171721';ctx.textAlign='center';ctx.textBaseline='middle';lines.forEach((line,i)=>ctx.fillText(line,x+w/2,y+h/2+(i-(lines.length-1)/2)*size*1.3));ctx.restore();
 if(handles&&state.kind!=='narration'){ctx.beginPath();ctx.arc(tx,ty,16,0,Math.PI*2);ctx.fillStyle='#8b5cf6';ctx.fill();ctx.strokeStyle='#fff';ctx.stroke();}
}
for(const id of fields)document.getElementById(id).addEventListener('input',e=>{state[id]=['text','kind'].includes(id)?e.target.value:Number(e.target.value);sync();render();});
function point(e){const b=canvas.getBoundingClientRect();return{x:(e.clientX-b.left)/b.width*100,y:(e.clientY-b.top)/b.height*100};}
canvas.addEventListener('pointerdown',e=>{if(!ready)return;const p=point(e);if(state.kind!=='narration'&&Math.hypot(p.x-state.tx,p.y-state.ty)<4)drag={kind:'tail'};else if(p.x>=state.x&&p.x<=state.x+state.w&&p.y>=state.y&&p.y<=state.y+state.h)drag={kind:'bubble',dx:p.x-state.x,dy:p.y-state.y};if(drag){canvas.setPointerCapture(e.pointerId);e.preventDefault();}});
canvas.addEventListener('pointermove',e=>{if(!drag)return;const p=point(e);if(drag.kind==='tail'){state.tx=p.x;state.ty=p.y;}else{state.x=p.x-drag.dx;state.y=p.y-drag.dy;}sync();render();});
for(const event of ['pointerup','pointercancel','lostpointercapture'])canvas.addEventListener(event,()=>{drag=null;});
canvas.addEventListener('keydown',e=>{const delta={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[e.key];if(delta){e.preventDefault();state.x+=delta[0];state.y+=delta[1];sync();render();}});
document.querySelector('#controls').addEventListener('submit',e=>e.preventDefault());
document.querySelector('#reset').addEventListener('click',()=>{state={...initial};sync();render();status.textContent='已重置 / Reset complete';});
document.querySelector('#export').addEventListener('click',()=>{render(false);canvas.toBlob(blob=>{render();if(!blob){status.textContent='导出失败 / Export failed';return;}const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=fiftyFive?'fifty-five-bubble-demo.png':'comiccraft-demo.png';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);status.textContent='PNG 已导出，紫色编辑手柄不会出现在成稿中。 / Exported without handles.';},'image/png');});
image.onload=()=>{if(fiftyFive){canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;}ready=true;sync();render();document.querySelector('#export').disabled=false;status.textContent='示例已就绪，修改仅留在当前页面。 / Ready. Edits stay in this page.';};
image.onerror=()=>{status.textContent='示例加载失败，请刷新或查看仓库中的漫画文件。 / Failed to load sample.';};
image.src=fiftyFive?'assets/web-novel-edit-panel.png':'images/demo-panel.png';

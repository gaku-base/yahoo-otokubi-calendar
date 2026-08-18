(()=>{
'use strict';
const DOW=['日','月','火','水','木','金','土'];

function makeDow(label,index){
  const e=document.createElement('div');
  e.className='dow'+(index===0?' sun':index===6?' sat':'');
  e.textContent=label;
  return e;
}
function makeEmpty(){const e=document.createElement('div');e.className='day empty';return e}
function sundayizeCalendar(){
  const cal=document.querySelector('#calendar');
  if(!cal||typeof view==='undefined')return;
  const buttons=[...cal.querySelectorAll('button.day')].sort((a,b)=>{
    const an=Number((a.getAttribute('aria-label')||'').match(/(\d+)日/)?.[1]||0);
    const bn=Number((b.getAttribute('aria-label')||'').match(/(\d+)日/)?.[1]||0);
    return an-bn;
  });
  const y=view.getFullYear(),m=view.getMonth(),offset=new Date(y,m,1).getDay();
  const nodes=DOW.map(makeDow);
  for(let i=0;i<offset;i++)nodes.push(makeEmpty());
  nodes.push(...buttons);
  while(nodes.length<49)nodes.push(makeEmpty());
  cal.replaceChildren(...nodes.slice(0,49));
}

const previousRender=render;
render=function(){previousRender();sundayizeCalendar()};
queueMicrotask(sundayizeCalendar);

function exportPngSunday(){
  const y=view.getFullYear(),m=view.getMonth(),shop=document.querySelector('#shop')?.value.trim()||'',W=1400,H=1040,p=40,c=document.createElement('canvas');
  c.width=W;c.height=H;const x=c.getContext('2d');x.fillStyle='#fff';x.fillRect(0,0,W,H);x.fillStyle='#171717';x.font='bold 46px -apple-system,sans-serif';x.fillText(`${y}年${m+1}月 Yahoo!お得日カレンダー`,p,70);x.font='28px -apple-system,sans-serif';x.fillText(shop,p,112);
  const top=150,cw=(W-p*2)/7,ch=132;x.textAlign='center';x.font='bold 24px sans-serif';DOW.forEach((d,i)=>x.fillText(d,p+cw*i+cw/2,top+28));x.textAlign='left';
  const first=new Date(y,m,1),days=new Date(y,m+1,0).getDate(),offset=first.getDay();x.strokeStyle='#ddd';
  for(let n=1;n<=days;n++){
    const idx=offset+n-1,row=Math.floor(idx/7),col=idx%7,xx=p+col*cw,yy=top+42+row*ch;
    x.strokeRect(xx,yy,cw,ch);x.fillStyle='#171717';x.font='bold 23px sans-serif';x.fillText(String(n),xx+10,yy+30);
    const iso=`${y}-${String(m+1).padStart(2,'0')}-${String(n).padStart(2,'0')}`,rec=(bonus.days||[]).find(z=>z.date===iso),sr=srFor(rec),ev=eventsFor(iso);let lines=[];
    if(sr.state==='match')lines.push(`BONUS+ +${fmtRate(sr.rate)}%${sr.quality==='partial'?' ?':''}`);else if(sr.state==='error')lines.push('取得エラー');else if(sr.state==='uncertain')lines.push('判定保留');else if(sr.state==='ambiguous')lines.push('候補複数');
    ev.slice(0,2).forEach(e=>lines.push(eventLabel(e)));x.font='bold 17px sans-serif';lines.forEach((t,j)=>x.fillText(t,xx+10,yy+58+j*24));
  }
  x.font='16px sans-serif';x.fillStyle='#666';x.fillText('日曜始まり / LYPプレミアム標準特典は表記省略 / Yahoo!ショッピング公式公開情報を参照',p,H-24);
  c.toBlob(blob=>{if(!blob)return;const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`Yahooお得日_${y}-${String(m+1).padStart(2,'0')}_${shop||'shop'}.png`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),1000)},'image/png');
}
function installPngButton(){
  const old=document.querySelector('#pngBtn');if(!old)return;
  const fresh=old.cloneNode(true);old.replaceWith(fresh);fresh.addEventListener('click',exportPngSunday);
}
installPngButton();
})();

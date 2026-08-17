(()=>{
'use strict';
const RANKS=[{label:'1位',cls:'rank1'},{label:'2位',cls:'rank2'},{label:'3位',cls:'rank3'}];
function isoForDay(y,m,n){return `${y}-${String(m+1).padStart(2,'0')}-${String(n).padStart(2,'0')}`}
function campaignAddRate(e){
  if(!e||e.is_total||e.target_store_limited)return 0;
  const title=String(e.title||'');
  if(title.includes('ボーナスストアPlus'))return 0;
  const n=Number(e.rate);
  return Number.isFinite(n)&&n>0?n:0;
}
function monthRanking(){
  const y=view.getFullYear(),m=view.getMonth(),days=new Date(y,m+1,0).getDate(),shop=currentShopQuery(),rows=[];
  for(let n=1;n<=days;n++){
    const iso=isoForDay(y,m,n),rec=(bonus.days||[]).find(d=>d.date===iso),sr=srFor(rec,shop),ev=eventsFor(iso);
    const bonusRate=sr.state==='match'?Number(sr.rate)||0:0;
    const campaignRate=ev.reduce((sum,e)=>sum+campaignAddRate(e),0);
    const score=bonusRate+campaignRate;
    if(score<=0)continue;
    rows.push({iso,day:n,score,bonusRate,campaignRate,eventCount:ev.length});
  }
  rows.sort((a,b)=>b.score-a.score||b.bonusRate-a.bonusRate||b.eventCount-a.eventCount||a.day-b.day);
  return rows.slice(0,3);
}
function ensureLegend(){
  const legend=document.querySelector('.legend');
  if(!legend||legend.querySelector('.top3Legend'))return;
  const s=document.createElement('span');s.className='top3Legend';s.textContent='👑1位　🥈2位　🥉3位';legend.appendChild(s);
}
function ensureStrip(){
  const pane=document.querySelector('.calendarPane'),cal=document.querySelector('#calendar');
  if(!pane||!cal)return null;
  let strip=document.querySelector('#top3Strip');
  if(!strip){strip=document.createElement('section');strip.id='top3Strip';strip.className='top3Strip';strip.setAttribute('aria-label','今月のお得日トップ3');pane.insertBefore(strip,cal)}
  return strip;
}
function dayButton(day){const m=view.getMonth()+1;return [...document.querySelectorAll('#calendar .day[aria-label]')].find(b=>b.getAttribute('aria-label')===`${m}月${day}日`)}
function updateRankMarks(){
  ensureLegend();
  document.querySelectorAll('#calendar .rankMark').forEach(x=>x.remove());
  document.querySelectorAll('#calendar .day').forEach(x=>x.classList.remove('rank1','rank2','rank3'));
  const ranked=monthRanking(),strip=ensureStrip();if(!strip)return;
  strip.innerHTML='';
  if(!ranked.length){strip.classList.add('emptyTop3');strip.textContent=currentShopQuery()?'この月は順位を付けられる加算特典がありません':'ショップを選ぶと、そのショップのお得日TOP3を表示します';return}
  strip.classList.remove('emptyTop3');
  ranked.forEach((r,i)=>{
    const cfg=RANKS[i],cell=dayButton(r.day);
    if(cell){cell.classList.add(cfg.cls);const mark=document.createElement('span');mark.className=`rankMark ${cfg.cls}`;mark.textContent=i===0?'👑1':i===1?'🥈2':'🥉3';mark.setAttribute('aria-label',cfg.label);cell.appendChild(mark)}
    const b=document.createElement('button');b.type='button';b.className=`top3Item ${cfg.cls}`;
    const rate=`+${fmtRate(r.score)}%`;
    b.innerHTML=`<b>${i===0?'👑':i===1?'🥈':'🥉'} ${cfg.label}</b><span>${r.day}日</span><strong>${rate}</strong>`;
    b.title=`${r.iso} 確認できる特典加算 ${rate}`;
    b.onclick=()=>{const target=dayButton(r.day);if(target)target.click()};strip.appendChild(b)
  })
}
const originalRender=render;
render=function(){originalRender();queueMicrotask(updateRankMarks)};
const originalShowDetail=showDetail;
showDetail=function(iso,rec,sr,ev){originalShowDetail(iso,rec,sr,ev);const r=monthRanking().findIndex(x=>x.iso===iso);if(r>=0){const d=document.querySelector('#detail h3');if(d)d.insertAdjacentHTML('afterend',`<div class="detailRank ${RANKS[r].cls}">${r===0?'👑':r===1?'🥈':'🥉'} 今月のお得度 ${RANKS[r].label}</div>`)}};
window.addEventListener('load',()=>setTimeout(updateRankMarks,250));
})();

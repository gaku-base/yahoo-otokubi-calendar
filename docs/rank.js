(()=>{
'use strict';
const RANKS=[{label:'1位',cls:'rank1'},{label:'2位',cls:'rank2'},{label:'3位',cls:'rank3'}];
function isoForDay(y,m,n){return `${y}-${String(m+1).padStart(2,'0')}-${String(n).padStart(2,'0')}`}
function purchaseAmount(){const el=document.querySelector('#purchaseAmount'),n=Number(el?.value||0);return Number.isFinite(n)&&n>0?n:0}
function campaignAddRate(e){
  if(!e||e.is_total||e.is_max||e.target_store_limited)return 0;
  const title=String(e.title||'');
  if(title.includes('ボーナスストアPlus'))return 0;
  const n=Number(e.rate);
  return Number.isFinite(n)&&n>0?n:0;
}
function conditionMoneyRule(e){
  const text=(Array.isArray(e?.conditions)?e.conditions:[]).join(' ');
  const minMatch=text.match(/(?:注文|決済|合計)[^0-9]{0,12}([0-9,]+)\s*円\s*(?:～|〜|以上)/);
  const capMatch=text.match(/付与上限\s*([0-9,]+)\s*円(?:相当)?/);
  return {min:minMatch?Number(minMatch[1].replaceAll(',','')):0,cap:capMatch?Number(capMatch[1].replaceAll(',','')):Infinity};
}
function campaignMoneyRule(e,iso){
  const title=String(e?.title||'');
  if(title.includes('5のつく日'))return {min:0,cap:iso>='2026-09-05'?2000:1000};
  if(title.includes('ファーストデイ'))return {min:3000,cap:2000};
  return conditionMoneyRule(e);
}
function bonusCap(rate){const r=Number(rate);if(r===10)return 10000;if(r===5)return 5000;return Infinity}
function pointsFor(rate,amount,min=0,cap=Infinity){
  const r=Number(rate);if(!amount||!Number.isFinite(r)||r<=0||amount<min)return 0;
  const p=Math.floor(amount*r/100);return Number.isFinite(cap)?Math.min(p,cap):p;
}
function campaignPoints(e,amount,iso){
  if(!e||e.is_total||e.is_max||e.target_store_limited)return 0;
  const title=String(e.title||'');
  if(title.includes('ボーナスストアPlus'))return 0;
  const r=Number(e.rate);if(!Number.isFinite(r)||r<=0)return 0;
  const rule=campaignMoneyRule(e,iso);return pointsFor(r,amount,rule.min,rule.cap);
}
function scoreDay(iso,day,shop,amount){
  const rec=(bonus.days||[]).find(d=>d.date===iso),sr=srFor(rec,shop),ev=eventsFor(iso);
  const bonusRate=sr.state==='match'?Number(sr.rate)||0:0;
  const campaignRate=ev.reduce((sum,e)=>sum+campaignAddRate(e),0);
  const rateScore=bonusRate+campaignRate;
  const bonusPoints=amount&&sr.state==='match'?pointsFor(bonusRate,amount,0,bonusCap(bonusRate)):0;
  const extraPoints=amount?ev.reduce((sum,e)=>sum+campaignPoints(e,amount,iso),0):0;
  const points=bonusPoints+extraPoints,score=amount?points:rateScore;
  return {iso,day,score,points,amount,rateScore,effectiveRate:amount?points/amount*100:rateScore,bonusRate,campaignRate,bonusPoints,extraPoints,eventCount:ev.length};
}
function monthRows(){
  const y=view.getFullYear(),m=view.getMonth(),days=new Date(y,m+1,0).getDate(),shop=currentShopQuery(),amount=purchaseAmount(),rows=[];
  for(let n=1;n<=days;n++){
    const row=scoreDay(isoForDay(y,m,n),n,shop,amount);
    if(row.score>0)rows.push(row);
  }
  rows.sort((a,b)=>b.score-a.score||b.rateScore-a.rateScore||b.bonusRate-a.bonusRate||b.eventCount-a.eventCount||a.day-b.day);
  rows.forEach((row,i)=>row.rank=i+1);
  return rows;
}
function monthRanking(){return monthRows().slice(0,3)}
function clickedDayInfo(iso){
  const rows=monthRows(),ranked=rows.find(x=>x.iso===iso);if(ranked)return ranked;
  const y=view.getFullYear(),m=view.getMonth(),prefix=`${y}-${String(m+1).padStart(2,'0')}-`;
  if(!String(iso||'').startsWith(prefix))return null;
  const day=Number(String(iso).slice(8));if(!day)return null;
  return {...scoreDay(iso,day,currentShopQuery(),purchaseAmount()),rank:null};
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
  if(!ranked.length){strip.classList.add('emptyTop3');strip.textContent=currentShopQuery()?'この月は順位を付けられる確認済み特典がありません':'ショップを選ぶと、そのショップのお得日TOP3を表示します';return}
  strip.classList.remove('emptyTop3');
  ranked.forEach((r,i)=>{
    const cfg=RANKS[i],cell=dayButton(r.day);
    if(cell){cell.classList.add(cfg.cls);const mark=document.createElement('span');mark.className=`rankMark ${cfg.cls}`;mark.textContent=i===0?'👑1':i===1?'🥈2':'🥉3';mark.setAttribute('aria-label',cfg.label);cell.appendChild(mark)}
    const b=document.createElement('button');b.type='button';b.className=`top3Item ${cfg.cls}`;
    const amountMode=r.amount>0,main=amountMode?`約${Math.round(r.points).toLocaleString('ja-JP')}pt`:`+${fmtRate(r.score)}%`,sub=amountMode?`実質+${fmtRate(Math.round(r.effectiveRate*10)/10)}%`:'';
    b.innerHTML=`<b>${i===0?'👑':i===1?'🥈':'🥉'} ${cfg.label}</b><span>${r.day}日</span><strong>${main}</strong>${sub?`<small>${sub}</small>`:''}`;
    b.title=amountMode?`${r.iso} 予定購入${Math.round(r.amount).toLocaleString('ja-JP')}円 / 確認できる特典 約${Math.round(r.points).toLocaleString('ja-JP')}pt`:`${r.iso} 確認できる特典加算 +${fmtRate(r.score)}%`;
    b.onclick=()=>{const target=dayButton(r.day);if(target)target.click()};strip.appendChild(b)
  })
}
function refreshForAmount(){if(typeof refreshSelectedDetail==='function')refreshSelectedDetail();else render()}
const amountInput=document.querySelector('#purchaseAmount');
if(amountInput){const saved=localStorage.getItem('purchaseAmount');if(saved&&Number(saved)>0)amountInput.value=saved;let t;amountInput.addEventListener('input',()=>{const n=purchaseAmount();if(n)localStorage.setItem('purchaseAmount',String(Math.round(n)));else localStorage.removeItem('purchaseAmount');clearTimeout(t);t=setTimeout(refreshForAmount,80)})}
const originalRender=render;
render=function(){originalRender();queueMicrotask(updateRankMarks)};
const originalShowDetail=showDetail;
showDetail=function(iso,rec,sr,ev){
  originalShowDetail(iso,rec,sr,ev);
  const row=clickedDayInfo(iso),d=document.querySelector('#detail h3');if(!row||!d)return;
  let html='';
  if(row.rank){
    if(row.rank<=3){const cfg=RANKS[row.rank-1];html+=`<div class="detailRank ${cfg.cls}">${row.rank===1?'👑':row.rank===2?'🥈':'🥉'} 今月のお得度 ${row.rank}位</div>`}
    else html+=`<div class="detailRank otherRank">今月のお得度 ${row.rank}位</div>`;
  }else html+='<div class="detailRank noDeal">順位計算に使える確認済み追加特典なし</div>';
  if(row.amount>0){
    const effective=fmtRate(Math.round(row.effectiveRate*10)/10),bonusText=row.bonusPoints?`BONUS+ 約${Math.round(row.bonusPoints).toLocaleString('ja-JP')}pt`:'BONUS+ 0pt',extraText=row.extraPoints?`その他 約${Math.round(row.extraPoints).toLocaleString('ja-JP')}pt`:'その他 0pt';
    html+=`<div class="amountEstimate dayDealInfo">予定購入 ${Math.round(row.amount).toLocaleString('ja-JP')}円 → 順位計算に使える確認済み追加特典 <b>約${Math.round(row.points).toLocaleString('ja-JP')}pt</b>（実質+${effective}%）<br><span class="dealBreakdown">${bonusText} / ${extraText}</span><br><small>入力金額を対象金額として計算した概算です。税・クーポン・対象商品・対象ストア条件などで実際の付与額は変わります。</small></div>`;
  }else{
    const bonusText=row.bonusRate?`BONUS+ +${fmtRate(row.bonusRate)}%`:'BONUS+ 0%',extraText=row.campaignRate?`その他 +${fmtRate(row.campaignRate)}%`:'その他 0%';
    html+=`<div class="amountEstimate dayDealInfo">順位計算に使える確認済み追加特典 <b>+${fmtRate(row.rateScore)}%</b><br><span class="dealBreakdown">${bonusText} / ${extraText}</span><br><small>予定購入金額を入力すると、付与上限を考慮した概算ポイントも表示します。</small></div>`;
  }
  d.insertAdjacentHTML('afterend',html)
};
window.addEventListener('load',()=>setTimeout(updateRankMarks,250));
})();

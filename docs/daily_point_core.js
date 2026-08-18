(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.DailyPointCore=api;})(typeof self!=='undefined'?self:this,function(){
'use strict';
function num(v){const n=Number(v);return Number.isFinite(n)?n:null}
function pointsFor(rate,amount,cap=Infinity){const r=num(rate),a=num(amount);if(r===null||a===null||r<=0||a<=0)return 0;const p=Math.floor(a*r/100);return Number.isFinite(cap)?Math.min(p,cap):p}
function conditionMoneyRule(e){const text=(Array.isArray(e?.conditions)?e.conditions:[]).join(' ');const minMatch=text.match(/(?:注文|決済|合計)[^0-9]{0,12}([0-9,]+)\s*円\s*(?:～|〜|以上)/);const capMatch=text.match(/付与上限\s*([0-9,]+)\s*円(?:相当)?/);return {min:minMatch?Number(minMatch[1].replaceAll(',','')):0,cap:capMatch?Number(capMatch[1].replaceAll(',','')):Infinity}}
function campaignMoneyRule(e,iso){const title=String(e?.title||'');if(title.includes('5のつく日'))return {min:0,cap:iso>='2026-09-05'?2000:1000};if(title.includes('ファーストデイ'))return {min:3000,cap:2000};return conditionMoneyRule(e)}
function campaignDecision(e,srState,settings={},gross=0,iso=''){
  if(!e||e.informational)return {state:'ignored',rate:0,reason:'informational'};
  const title=String(e.title||''),rule=campaignMoneyRule(e,iso),amount=Number(gross)||0;
  if(amount>0&&rule.min>0&&amount<rule.min)return {state:'ineligible',rate:0,reason:`注文下限${rule.min.toLocaleString('ja-JP')}円未満`,rule};
  if(title.includes('5のつく日'))return settings.fiveDayEligible===false?{state:'ineligible',rate:0,reason:'対象支払い方法を使わない',rule}:{state:'eligible',rate:4,reason:'対象支払い方法を使う',rule};
  if(title.includes('ファーストデイ'))return {state:'eligible',rate:num(e.rate)??3,reason:'全員対象',rule};
  if(e.eligibility_rule==='bonus_plus_member'){
    if(srState==='match')return {state:'eligible',rate:num(e.rate)??0,reason:'BONUS+対象ショップ一致',rule};
    if(srState==='not_found')return {state:'ineligible',rate:0,reason:'BONUS+対象ショップ外',rule};
    return {state:'unknown',rate:num(e.rate),reason:'BONUS+対象ショップ判定未確定',rule};
  }
  if(title.includes('プレミアムな日曜日')){
    if(srState==='match')return {state:'eligible',rate:num(e.rate)??5,reason:'BONUS対象ショップ一致',rule};
    if(srState==='not_found')return {state:'ineligible',rate:0,reason:'BONUS対象ショップ外',rule};
    return {state:'unknown',rate:num(e.rate)??5,reason:'BONUS対象ショップ判定未確定',rule};
  }
  if(title.includes('ヤフショ感謝デー')){
    if(srState==='not_found')return {state:'ineligible',rate:0,reason:'BONUS対象ショップ外',rule};
    if(srState!=='match')return {state:'unknown',rate:null,reason:'BONUS対象ショップ判定未確定',rule};
    const rank=String(settings.yahooRank||'unknown');
    if(rank==='gold')return {state:'eligible',rate:5,reason:'ゴールドランク',rule};
    if(rank==='silver')return {state:'eligible',rate:4,reason:'シルバーランク',rule};
    if(rank==='none')return {state:'ineligible',rate:0,reason:'対象ランク外',rule};
    return {state:'unknown',rate:null,reason:'ヤフショランク未設定',rule};
  }
  if(e.eligibility_rule==='preferred_bonus_store'){
    if(srState==='not_found')return {state:'ineligible',rate:0,reason:'BONUS+対象ショップ外',rule};
    return {state:'unknown',rate:num(e.rate),reason:'優良ストア対象可否を自動判定できない',rule};
  }
  if(e.is_total||e.is_max||e.rankable===false||num(e.rate)===null)return {state:'unknown',rate:num(e.rate),reason:'商品・ストア条件を自動確定できない',rule};
  if(!e.target_store_limited||e.eligibility_rule==='all')return {state:'eligible',rate:num(e.rate)??0,reason:'全ストア対象',rule};
  return {state:'unknown',rate:num(e.rate),reason:'対象ストア判定を自動確定できない',rule};
}
function eventPoints(e,srState,settings,gross,target,iso){const d=campaignDecision(e,srState,settings,gross,iso);if(d.state!=='eligible'||!d.rate)return {...d,points:0};return {...d,points:pointsFor(d.rate,target,d.rule?.cap??Infinity)}}
function compareRows(rows,mode='points',options={}){
  const exact=rows.filter(r=>mode==='points'?r.pointExact:r.rateExact),uncertain=rows.filter(r=>!(mode==='points'?r.pointExact:r.rateExact)&&r.hasPotential!==false),key=mode==='points'?'addPoints':'addRate',unknownAsZero=options.unknownAsZero===true,comparable=unknownAsZero?[...exact,...uncertain]:exact;
  const vals=comparable.map(r=>Number(r[key])||0),baseline=vals.length?Math.min(...vals):0,max=vals.length?Math.max(...vals):0;
  const ranked=comparable.filter(r=>(Number(r[key])||0)>baseline).map(r=>({...r,comparisonDelta:(Number(r[key])||0)-baseline,unknownCountedAsZero:unknownAsZero&&uncertain.includes(r)}));
  ranked.sort((a,b)=>(Number(b[key])||0)-(Number(a[key])||0)||(Number(b.addRate)||0)-(Number(a.addRate)||0)||a.day-b.day);ranked.forEach((r,i)=>r.rank=i+1);
  return {mode,exact,uncertain,comparable,baseline,max,ranked,hasDifference:max>baseline,unknownAsZero};
}
return {pointsFor,conditionMoneyRule,campaignMoneyRule,campaignDecision,eventPoints,compareRows};
});

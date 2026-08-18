(()=>{
'use strict';
function stateText(e,iso,rec){
  if(e.informational||e.calculation_mode==='lottery')return '情報表示のみ（くじ・抽選はポイント計算に加算しません）';
  if(e.is_total||e.calculation_mode==='total_max')return '最大表示のため単純加算しません';
  if(!e.target_store_limited)return '対象ストア制限なし';
  const s=OtokubiCore.campaignShopState(e,iso,currentShopQuery(),rec,bonus.store_catalog);
  if(s.state==='eligible')return '選択ショップ：対象確認済み（ポイント計算に反映）';
  if(s.state==='not_eligible')return '選択ショップ：対象外（ポイント計算に加算しません）';
  if(s.state==='no_shop')return 'ショップ選択後に対象可否を判定します';
  return '選択ショップ：対象ストア判定保留（ポイント計算には未加算）';
}
function appendChecks(iso,rec,ev){
  const detail=document.querySelector('#detail'),ul=detail?.querySelector('ul');if(!detail||!ul||!Array.isArray(ev)||!ev.length)return;
  detail.querySelector('.campaignChecks')?.remove();
  const rows=ev.filter(e=>e.target_store_limited||e.informational||e.is_total).map(e=>{
    const rate=e.rank_rates?.gold?`（ゴールド +${e.rank_rates.gold}%）`:'';
    const link=e.detail_url?` <a href="${e.detail_url}" target="_blank" rel="noopener">公式詳細</a>`:'';
    return `<div><b>${esc(e.title||'キャンペーン')}</b>${rate}<br><small>${esc(stateText(e,iso,rec))}${link}</small></div>`;
  });
  if(!rows.length)return;const box=document.createElement('div');box.className='campaignChecks';box.innerHTML=`<b>キャンペーン対象判定</b>${rows.join('')}`;ul.insertAdjacentElement('afterend',box);
}
const original=showDetail;showDetail=function(iso,rec,sr,ev){original(iso,rec,sr,ev);appendChecks(iso,rec,ev)};
})();

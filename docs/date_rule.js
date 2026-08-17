(()=>{
'use strict';
// A shop is shown as BONUS+ only when it is present in that exact day's
// authoritative store list. For a fully captured day, absence means
// non-eligible and should stay visually quiet instead of adding a BONUS+ line.
const originalShowDetail=showDetail;
showDetail=function(iso,rec,sr,ev){
  originalShowDetail(iso,rec,sr,ev);
  if(sr?.state!=='not_found')return;
  const items=[...document.querySelectorAll('#detail li')];
  for(const li of items){
    if((li.textContent||'').includes('BONUS+：全カテゴリ取得成功データでは一致なし'))li.remove();
  }
};
})();

(()=>{
'use strict';
const assumptions=Object.freeze({entryCompleted:true,ignoreCoupons:true});
window.OTOKUBI_CALC_ASSUMPTIONS=assumptions;

const originalShowDetail=showDetail;
showDetail=function(...args){
  originalShowDetail(...args);
  document.querySelectorAll('#detail small').forEach(el=>{
    const text=el.textContent||'';
    if(text.includes('入力金額を対象金額として計算した概算です')){
      el.textContent='入力金額を対象金額として、要エントリー企画はエントリー済・クーポンは使用しない前提で計算しています。税・対象商品・対象ストア・支払い方法などで実際の付与額は変わります。';
    }
  });
};
})();

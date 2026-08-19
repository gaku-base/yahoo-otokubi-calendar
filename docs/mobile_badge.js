(()=>{
'use strict';
function enhanceBonusBadges(){
  document.querySelectorAll('#calendar .badge.b10,#calendar .badge.b5').forEach(b=>{
    if(b.classList.contains('bonusRateBadge'))return;
    const m=(b.textContent||'').trim().match(/^BONUS\+([0-9]+(?:\.[0-9]+)?)%(\s*\?)?$/);
    if(!m)return;
    b.classList.add('bonusRateBadge');
    b.innerHTML=`<span class="bonusPrefix">BONUS+</span><strong class="bonusRate">${m[1]}%</strong>${m[2]?'<span class="bonusPending">?</span>':''}`;
  });
}
function loadFreshCampaigns(){
  if(document.querySelector('script[data-fresh-campaigns]'))return;
  const s=document.createElement('script');s.src='fresh_campaigns.js?v=099';s.async=true;s.dataset.freshCampaigns='1';document.head.appendChild(s);
}
const previousRender=render;
render=function(){previousRender();queueMicrotask(enhanceBonusBadges)};
loadFreshCampaigns();
window.addEventListener('load',()=>setTimeout(enhanceBonusBadges,260));
})();

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
const previousRender=render;
render=function(){previousRender();queueMicrotask(enhanceBonusBadges)};
window.addEventListener('load',()=>setTimeout(enhanceBonusBadges,260));
})();

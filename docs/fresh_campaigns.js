(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports){module.exports=api;return;}
  root.OtokubiFreshCampaigns=api;
  if(typeof window==='undefined')return;
  const run=()=>setTimeout(()=>api.refreshFromMain({
    getCurrent:()=>typeof campaigns!=='undefined'?campaigns:null,
    setCurrent:v=>{campaigns=v;},
    onChanged:()=>{if(typeof refreshSelectedDetail==='function')refreshSelectedDetail();},
    fetcher:window.fetch.bind(window),
    hostname:window.location.hostname
  }),350);
  if(document.readyState==='complete')run();else window.addEventListener('load',run,{once:true});
})(typeof self!=='undefined'?self:this,function(){
'use strict';
const RAW_CAMPAIGNS='https://raw.githubusercontent.com/gaku-base/yahoo-otokubi-calendar/main/data/campaigns.json';
function valid(v){return !!(v&&Array.isArray(v.campaigns));}
function stamp(v){const n=Date.parse(v?.updated_at||'');return Number.isFinite(n)?n:0;}
function selectFresh(local,remote){
  if(!valid(remote))return {data:local,source:'local',changed:false};
  if(!valid(local))return {data:remote,source:'main',changed:true};
  const lt=stamp(local),rt=stamp(remote);
  if(rt>lt)return {data:remote,source:'main',changed:true};
  return {data:local,source:'local',changed:false};
}
function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
async function waitForLocal(getCurrent){
  for(let i=0;i<20;i++){
    const cur=getCurrent();
    if(valid(cur)&&stamp(cur)>0)return cur;
    await sleep(100);
  }
  return getCurrent();
}
async function refreshFromMain(opts={}){
  const hostname=String(opts.hostname||'');
  if(hostname==='127.0.0.1'||hostname==='localhost')return {skipped:true,reason:'local-test'};
  const getCurrent=opts.getCurrent||(()=>null),setCurrent=opts.setCurrent||(()=>{}),onChanged=opts.onChanged||(()=>{}),fetcher=opts.fetcher;
  if(typeof fetcher!=='function')return {skipped:true,reason:'no-fetch'};
  const local=await waitForLocal(getCurrent);
  try{
    const url=RAW_CAMPAIGNS+'?v='+Date.now();
    const r=await fetcher(url,{cache:'no-store',mode:'cors'});
    if(!r||!r.ok)throw new Error(`HTTP ${r?.status||0}`);
    const remote=await r.json();
    const chosen=selectFresh(local,remote);
    if(chosen.changed){setCurrent(chosen.data);onChanged(chosen.data);}
    return {...chosen,localUpdatedAt:local?.updated_at||null,remoteUpdatedAt:remote?.updated_at||null};
  }catch(error){return {data:local,source:'local',changed:false,error:String(error)};}
}
return {RAW_CAMPAIGNS,valid,stamp,selectFresh,refreshFromMain};
});

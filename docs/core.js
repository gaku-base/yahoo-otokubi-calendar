(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.OtokubiCore=api;})(typeof self!=='undefined'?self:this,function(){
  function norm(s){return(s||'').toLowerCase().normalize('NFKC').replace(/[\s\-_・･/／]+/g,'')}
  function slugFromInput(s){try{const u=new URL(s);if(u.hostname.toLowerCase()==='store.shopping.yahoo.co.jp')return u.pathname.split('/').filter(Boolean)[0]?.toLowerCase()||''}catch(e){}return''}
  function matchRows(day,shop,quality){
    const q=norm(shop),qslug=slugFromInput(shop);if(!q&&!qslug)return{rate:null,state:'empty'};const rows=day?.stores||[];
    let hits=qslug?rows.filter(s=>(s.slug||'').toLowerCase()===qslug):[];
    if(!hits.length&&q)hits=rows.filter(s=>norm(s.name)===q);
    if(!hits.length&&q){const partial=rows.filter(s=>norm(s.name).includes(q)||q.includes(norm(s.name)));const identities=new Set(partial.map(s=>s.slug||norm(s.name)));if(identities.size>1)return{rate:null,state:'ambiguous',matches:partial.slice(0,8)};hits=partial;}
    if(hits.length){hits.sort((a,b)=>Number(b.rate)-Number(a.rate));return{rate:Number(hits[0].rate),state:'match',store:hits[0],quality}}
    return quality==='ok'?{rate:0,state:'not_found'}:{rate:null,state:'uncertain'}
  }
  function shopRate(day,shop){if(!day)return{rate:null,state:'missing'};if(day.status==='partial')return matchRows(day,shop,'partial');if(day.status!=='ok')return{rate:null,state:'error'};return matchRows(day,shop,'ok')}
  function eventsFor(iso,campaigns){
    let out=[];const d=new Date(iso+'T00:00:00');
    if([5,15,25].includes(d.getDate()))out.push({title:'5のつく日',kind:'fixed'});
    const dynamic=[];for(const c of campaigns?.campaigns||[])if((c.dates||[]).includes(iso))dynamic.push({title:c.title,period:c.period,kind:'guide'});
    const blocksFirstDay=dynamic.some(x=>x.title.includes('プレミアムな日曜日')||x.title.includes('爆買WEEK'));
    if(d.getDate()===1&&!blocksFirstDay)out.push({title:'ファーストデイ',kind:'fixed'});
    out.push(...dynamic);
    const seen=new Set();return out.filter(x=>{const k=norm(x.title);if(seen.has(k))return false;seen.add(k);return true}).slice(0,5)
  }
  function fmtRate(r){return Number.isInteger(r)?String(r):String(r).replace(/\.0+$/,'')}
  return {norm,slugFromInput,matchRows,shopRate,eventsFor,fmtRate};
});

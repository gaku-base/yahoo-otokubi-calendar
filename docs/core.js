(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.OtokubiCore=api;})(typeof self!=='undefined'?self:this,function(){
  function norm(s){return(s||'').toLowerCase().normalize('NFKC').replace(/[\s\-_・･/／]+/g,'')}
  function slugFromInput(s){try{const u=new URL(s);if(u.hostname.toLowerCase()==='store.shopping.yahoo.co.jp')return u.pathname.split('/').filter(Boolean)[0]?.toLowerCase()||''}catch(e){}return''}
  function rowsFor(day,catalog){
    if(Array.isArray(day?.stores))return day.stores;
    if(Array.isArray(day?.offers)&&Array.isArray(catalog))return day.offers.map(o=>{const c=catalog[o[0]]||[];return{name:c[0]||'',slug:c[1]||'',rate:Number(o[1])}});
    return[];
  }
  function indexedMatches(day,shop,catalog){
    const q=norm(shop),qslug=slugFromInput(shop);if(!q&&!qslug)return{empty:true,hits:[]};
    const offers=day?.offers||[], exactSlug=[], exactName=[], partial=[];
    for(const o of offers){const c=catalog?.[o[0]]||[],name=c[0]||'',slug=(c[1]||'').toLowerCase(),rate=Number(o[1]),row={name,slug,rate};
      if(qslug&&slug===qslug){exactSlug.push(row);continue}
      if(!qslug&&q&&norm(name)===q){exactName.push(row);continue}
      if(!qslug&&q){const n=norm(name);if(n&&(n.includes(q)||q.includes(n)))partial.push(row)}
    }
    if(exactSlug.length)return{hits:exactSlug};if(exactName.length)return{hits:exactName};
    if(partial.length){const identities=new Set(partial.map(s=>s.slug||norm(s.name)));if(identities.size>1)return{ambiguous:true,hits:partial.slice(0,8)};return{hits:partial}}
    return{hits:[]};
  }
  function matchRows(day,shop,quality,catalog){
    if(Array.isArray(day?.offers)&&Array.isArray(catalog)){
      const m=indexedMatches(day,shop,catalog);if(m.empty)return{rate:null,state:'empty'};if(m.ambiguous)return{rate:null,state:'ambiguous',matches:m.hits};
      if(m.hits.length){m.hits.sort((a,b)=>b.rate-a.rate);return{rate:m.hits[0].rate,state:'match',store:m.hits[0],quality}}
      return quality==='ok'?{rate:0,state:'not_found'}:{rate:null,state:'uncertain'};
    }
    const q=norm(shop),qslug=slugFromInput(shop);if(!q&&!qslug)return{rate:null,state:'empty'};const rows=rowsFor(day,catalog);
    let hits=qslug?rows.filter(s=>(s.slug||'').toLowerCase()===qslug):[];
    if(!hits.length&&q)hits=rows.filter(s=>norm(s.name)===q);
    if(!hits.length&&q){const partial=rows.filter(s=>{const n=norm(s.name);return n&&(n.includes(q)||q.includes(n))});const identities=new Set(partial.map(s=>s.slug||norm(s.name)));if(identities.size>1)return{rate:null,state:'ambiguous',matches:partial.slice(0,8)};hits=partial;}
    if(hits.length){hits.sort((a,b)=>Number(b.rate)-Number(a.rate));return{rate:Number(hits[0].rate),state:'match',store:hits[0],quality}}
    return quality==='ok'?{rate:0,state:'not_found'}:{rate:null,state:'uncertain'}
  }
  function shopRate(day,shop,catalog){if(!day)return{rate:null,state:'missing'};if(day.status==='partial')return matchRows(day,shop,'partial',catalog);if(day.status!=='ok')return{rate:null,state:'error'};return matchRows(day,shop,'ok',catalog)}
  function eventsFor(iso,campaigns){
    let out=[];const d=new Date(iso+'T00:00:00');
    if([5,15,25].includes(d.getDate()))out.push({title:'5のつく日',rate:4,rate_label:'+4%',entry_required:true,kind:'fixed'});
    const dynamic=[];for(const c of campaigns?.campaigns||[])if((c.dates||[]).includes(iso))dynamic.push({
      title:c.title,period:c.period,rate:c.rate==null?null:Number(c.rate),rate_label:c.rate_label||null,is_total:!!c.is_total,is_max:!!c.is_max,
      conditions:Array.isArray(c.conditions)?c.conditions:[],entry_required:!!c.entry_required,target_store_limited:!!c.target_store_limited,source:c.source||campaigns?.source||null,kind:'guide'
    });
    const blocksFirstDay=dynamic.some(x=>x.title.includes('プレミアムな日曜日')||x.title.includes('爆買WEEK')||x.title.includes('Brand Week')||x.title.includes('ブランドウィーク'));
    if(d.getDate()===1&&!blocksFirstDay)out.push({title:'ファーストデイ',rate:3,rate_label:'+3%',entry_required:true,kind:'fixed'});
    out.push(...dynamic);
    const merged=[],pos=new Map();
    for(const x of out){const k=norm(x.title)+(x.rate_label||'');if(!pos.has(k)){pos.set(k,merged.length);merged.push(x);continue}const i=pos.get(k);if(merged[i].kind==='fixed'&&x.kind==='guide')merged[i]=x;}
    return merged.slice(0,6)
  }
  function fmtRate(r){return Number.isInteger(r)?String(r):String(r).replace(/\.0+$/,'')}
  return {norm,slugFromInput,rowsFor,indexedMatches,matchRows,shopRate,eventsFor,fmtRate};
});

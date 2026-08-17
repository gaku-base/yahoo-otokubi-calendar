const SHELL_CACHE='otokubi-v067',DATA_CACHE='otokubi-data-v1';
const ASSETS=['./','index.html','styles.css','core.js','app.js','manifest.webmanifest','icon.svg'];
self.addEventListener('install',e=>e.waitUntil(caches.open(SHELL_CACHE).then(c=>c.addAll(ASSETS))));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('otokubi-')&&k!==SHELL_CACHE&&k!==DATA_CACHE).map(k=>caches.delete(k))))));
async function dataResponse(req){
  const cache=await caches.open(DATA_CACHE);
  try{
    const res=await fetch(req,{cache:'no-store'});
    if(!res.ok)throw new Error(`HTTP ${res.status}`);
    await cache.put(req,res.clone());
    return res;
  }catch(err){
    const saved=await cache.match(req,{ignoreSearch:true});
    if(saved)return saved;
    throw err;
  }
}
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  const u=new URL(e.request.url);
  if(u.origin===self.location.origin&&u.pathname.includes('/data/')&&u.pathname.endsWith('.json')){e.respondWith(dataResponse(e.request));return;}
  e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)));
});

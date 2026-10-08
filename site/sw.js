/* Same-origin cache only. Network-first news never silently masquerades as fresh. */
const VERSION='ai-daily-v5-1';
const SHELL=['./','./index.html','./style.css','./v3.css','./v4.css','./v5.css','./app.js','./manifest.webmanifest','./icon.svg','./icon-192.png','./icon-512.png'];
const PAGE_CACHE=VERSION+'-shell',DATA_CACHE=VERSION+'-reports';
self.addEventListener('install',event=>{
  event.waitUntil((async()=>{
    const shell=await caches.open(PAGE_CACHE);
    await shell.addAll(SHELL);
    // Cache the newest dated report at installation, not merely the shell.
    // Otherwise a first-time visitor may get an offline page with no article.
    try{
      const data=await caches.open(DATA_CACHE);
      const response=await fetch('./reports/index.json',{cache:'no-store'});
      if(response.ok){
        const index=await response.clone().json();
        await data.put('./reports/index.json',response);
        const latest=index?.[0]?.date;
        if(/^\d{4}-\d{2}-\d{2}$/.test(latest)){
          const report=await fetch('./reports/'+latest+'.json',{cache:'no-store'});
          if(report.ok) await data.put('./reports/'+latest+'.json',report);
        }
      }
    }catch{/* Offline install keeps usable shell, no fabricated news. */}
    await self.skipWaiting();
  })());
});
self.addEventListener('activate',event=>{
  event.waitUntil(Promise.all([caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('ai-daily-')&&!k.startsWith(VERSION)).map(k=>caches.delete(k)))),self.clients.claim()]));
});
self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET')return;
  const url=new URL(event.request.url);
  if(url.origin!==self.location.origin)return;
  const isData=url.pathname.endsWith('/system-status.json')||url.pathname.includes('/reports/')&&url.pathname.endsWith('.json');
  if(isData){
    event.respondWith((async()=>{
      const cache=await caches.open(DATA_CACHE);
      try{
        const res=await fetch(event.request);
        if(res.ok){await cache.put(event.request,res.clone());await prune(cache,42);}
        return res;
      }catch{return await cache.match(event.request)||Response.error();}
    })());return;
  }
  if(event.request.mode==='navigate'){
    event.respondWith(fetch(event.request).catch(async()=> (await caches.match('./index.html'))||Response.error()));return;
  }
  const shellNames=new Set(SHELL.filter(path=>path!=='./').map(path=>path.slice(2)));
  if(shellNames.has(url.pathname.split('/').pop())){
    event.respondWith(caches.match(event.request).then(cached=>cached||fetch(event.request)));
  }
});
async function prune(cache,limit){const keys=await cache.keys();if(keys.length>limit)await Promise.all(keys.slice(0,keys.length-limit).map(k=>cache.delete(k)));}

/* Same-origin cache only. Network-first news never silently masquerades as fresh. */
const VERSION='ai-daily-V3-novel-reading';
const SHELL=['./','./index.html','./style.css','./v3.css','./v4.css','./v5.css','./v6.css','./v11.css','./v12.css','./v1.css','./reading-theme-v1.css','./cloud-sync.js','./app.js','./offline-glossary.json','./reading-glossary.json','./news-glossary.json','./news-template-glossary.json','./release.json','./manifest.webmanifest','./icon.svg','./icon-192.png','./icon-512.png'];
const PAGE_CACHE=VERSION+'-shell',DATA_CACHE=VERSION+'-reports';
const SCOPE=new URL('./',self.location.href);
function dataKey(value){const url=new URL(typeof value==='string'?value:value.url,SCOPE);url.search='';return url.href;}
function publicData(url){return url.origin===SCOPE.origin&&url.pathname.startsWith(SCOPE.pathname)&&
  (url.pathname===SCOPE.pathname+'system-status.json'||/^reports\/(?:index|\d{4}-\d{2}-\d{2})\.json$/.test(url.pathname.slice(SCOPE.pathname.length)));}
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
  event.waitUntil((async()=>{
    const data=await caches.open(DATA_CACHE);
    const keys=await caches.keys();
    // Carry visited public reports across the V1 -> V2 shell upgrade. Never
    // touch localStorage, auth sessions, cloud vocabulary or another app cache.
    for(const key of keys.filter(k=>k.startsWith('ai-daily-')&&k.endsWith('-reports')&&k!==DATA_CACHE)){
      const previous=await caches.open(key);
      const requests=await previous.keys();
      // Last cached revision wins among old query-string variants; a fresh
      // V2 installation always outranks the older cached same-date report.
      for(const request of requests.reverse()){
        if(!publicData(new URL(request.url)))continue;
        const canonical=dataKey(request);
        if(!(await data.match(canonical))){const response=await previous.match(request);if(response)await data.put(canonical,response);}
      }
    }
    await prune(data,42);
    await Promise.all(keys.filter(k=>k.startsWith('ai-daily-')&&k!==PAGE_CACHE&&k!==DATA_CACHE).map(k=>caches.delete(k)));
    await self.clients.claim();
  })());
});
self.addEventListener('message',event=>{if(event.data?.type==='SKIP_WAITING')event.waitUntil(self.skipWaiting());});
self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET')return;
  const url=new URL(event.request.url);
  if(url.origin!==self.location.origin||!url.pathname.startsWith(SCOPE.pathname))return;
  const isData=publicData(url);
  if(isData){
    event.respondWith((async()=>{
      const cache=await caches.open(DATA_CACHE);
      const key=dataKey(event.request);
      try{
        const res=await fetch(event.request,{cache:'no-store'});
        if(res.ok){await cache.put(key,res.clone());await prune(cache,42);return res;}
        return (await cache.match(key))||res;
      }catch{return await cache.match(key)||Response.error();}
    })());return;
  }
  if(event.request.mode==='navigate'){
    event.respondWith(fetch(event.request).catch(async()=> (await caches.match('./index.html'))||Response.error()));return;
  }
  const shellNames=new Set(SHELL.filter(path=>path!=='./').map(path=>path.slice(2)));
  if(shellNames.has(url.pathname.split('/').pop())){
    event.respondWith((async()=>{
      const cache=await caches.open(PAGE_CACHE);
      // Network first: installed iPhone PWAs must not stay on old CSS or JS
      // after a deployment. Previously a shell-cache hit lasted indefinitely.
      try{
        const response=await fetch(event.request,{cache:'no-cache'});
        if(response.ok)await cache.put(event.request,response.clone());
        return response;
      }catch{
        return (await cache.match(event.request,{ignoreSearch:true}))||Response.error();
      }
    })());
  }
});
async function prune(cache,limit){
  const reports=(await cache.keys()).filter(k=>/\/reports\/\d{4}-\d{2}-\d{2}\.json$/.test(new URL(k.url).pathname))
    .sort((a,b)=>a.url.localeCompare(b.url));
  // Index/status are protected. Query-string refreshes consume one dated slot.
  if(reports.length>limit)await Promise.all(reports.slice(0,reports.length-limit).map(k=>cache.delete(k)));
}

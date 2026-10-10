/* Same-origin cache only. Network-first news never silently masquerades as fresh. */
const VERSION='ai-daily-S1-1-reading';
const SHELL=['./','./index.html','./style.css','./v3.css','./v4.css','./v5.css','./v6.css','./v11.css','./v12.css','./v1.css','./reading-theme-v1.css','./cloud-sync.js','./app.js','./offline-glossary.json','./reading-glossary.json','./news-glossary.json','./news-template-glossary.json','./release.json','./manifest.webmanifest','./icon.svg','./icon-192.png','./icon-512.png'];
const PAGE_CACHE=VERSION+'-shell',DATA_CACHE=VERSION+'-reports';
const SCOPE=new URL('./',self.location.href);
const SHELL_URLS=new Set(SHELL.map(path=>new URL(path,SCOPE).href));
const ownedLegacy=name=>/^ai-daily-(?:V[123]-|S1-)/.test(name);
function dataKey(value){const url=new URL(typeof value==='string'?value:value.url,SCOPE);url.search='';return url.href;}
async function boundedFetch(request,options){
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),8000);
  try{return await fetch(request,{...options,signal:controller.signal});}
  finally{clearTimeout(timer);}
}
function offlineResponse(response){
  if(!response)return Response.error();
  const headers=new Headers(response.headers);headers.set('X-AI-Daily-Cache','offline');
  return new Response(response.body,{status:response.status,statusText:response.statusText,headers});
}
function publicData(url){return url.origin===SCOPE.origin&&url.pathname.startsWith(SCOPE.pathname)&&
  (url.pathname===SCOPE.pathname+'system-status.json'||/^reports\/(?:index|\d{4}-\d{2}-\d{2})\.json$/.test(url.pathname.slice(SCOPE.pathname.length)));}
async function validPublicResponse(request,response){
  try{
    const path=new URL(dataKey(request)).pathname,value=await response.clone().json();
    if(path.endsWith('/reports/index.json'))return Array.isArray(value)&&value.length>0&&value.every(row=>row&&/^\d{4}-\d{2}-\d{2}$/.test(row.date));
    if(path.endsWith('/system-status.json'))return value&&typeof value.state==='string';
    const date=path.match(/\/reports\/(\d{4}-\d{2}-\d{2})\.json$/)?.[1];
    return value?.date===date&&Array.isArray(value.essay)&&value.essay.length>=5&&value.essay.every(p=>typeof p==='string')&&
      value.dictionary&&typeof value.dictionary==='object'&&Array.isArray(value.practice?.items)&&value.practice.items.length>=7;
  }catch{return false;}
}
self.addEventListener('install',event=>{
  event.waitUntil((async()=>{
    const shell=await caches.open(PAGE_CACHE);
    await Promise.all(SHELL.map(async path=>{
      const response=await boundedFetch(new URL(path,SCOPE).href,{cache:'no-cache'});
      if(!response.ok)throw new Error('Shell unavailable: '+path);
      await shell.put(new URL(path,SCOPE).href,response);
    }));
    // Cache the newest dated report at installation, not merely the shell.
    // Otherwise a first-time visitor may get an offline page with no article.
    try{
      const data=await caches.open(DATA_CACHE);
      const response=await boundedFetch(new URL('./reports/index.json',SCOPE).href,{cache:'no-store'});
      if(response.ok&&await validPublicResponse('./reports/index.json',response)){
        const index=await response.clone().json();
        await data.put('./reports/index.json',response);
        const latest=index?.[0]?.date;
        if(/^\d{4}-\d{2}-\d{2}$/.test(latest)){
          const path='./reports/'+latest+'.json';
          const report=await boundedFetch(new URL(path,SCOPE).href,{cache:'no-store'});
          if(report.ok&&await validPublicResponse(path,report))await data.put(path,report);
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
    // Carry visited public reports across the V1/V2/V3 -> S1 shell upgrade. Never
    // touch localStorage, auth sessions, cloud vocabulary or another app cache.
    for(const key of keys.filter(k=>ownedLegacy(k)&&k.endsWith('-reports')&&k!==DATA_CACHE).reverse()){
      const previous=await caches.open(key);
      const requests=await previous.keys();
      // Last cached revision wins among old query-string variants; a fresh
      // S1 installation always outranks the older cached same-date report.
      for(const request of requests.reverse()){
        if(!publicData(new URL(request.url)))continue;
        const canonical=dataKey(request);
        if(!(await data.match(canonical))){const response=await previous.match(request);if(response&&await validPublicResponse(request,response))await data.put(canonical,response);}
      }
    }
    await prune(data,42);
    // CacheStorage is shared by all apps on this origin. Remove only entries
    // owned by this scope, after successful migration; preserve sibling apps.
    for(const key of keys.filter(k=>ownedLegacy(k)&&k!==PAGE_CACHE&&k!==DATA_CACHE)){
      const previous=await caches.open(key);
      for(const request of await previous.keys()){
        const url=new URL(request.url);
        if(url.origin===SCOPE.origin&&url.pathname.startsWith(SCOPE.pathname))await previous.delete(request);
      }
      if(!(await previous.keys()).length)await caches.delete(key);
    }
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
      const cache=await caches.open(DATA_CACHE).catch(()=>null);
      const key=dataKey(event.request);
      try{
        const res=await boundedFetch(event.request,{cache:'no-store'});
        if(res.ok&&await validPublicResponse(event.request,res)){
          if(cache)try{await cache.put(key,res.clone());await prune(cache,42);}catch{/* A full cache must not block a valid online reading. */}
          return res;
        }
        const previous=await cache?.match(key);return previous?offlineResponse(previous):res;
      }catch{return offlineResponse(await cache?.match(key));}
    })());return;
  }
  if(event.request.mode==='navigate'){
    event.respondWith((async()=>{
      const cache=await caches.open(PAGE_CACHE).catch(()=>null);
      try{const res=await boundedFetch(event.request);if(res.ok)return res;
        const previous=await cache?.match(new URL('./index.html',SCOPE).href);return previous?offlineResponse(previous):res;
      }catch{return offlineResponse(await cache?.match(new URL('./index.html',SCOPE).href));}
    })());return;
  }
  if(SHELL_URLS.has(dataKey(event.request))){
    event.respondWith((async()=>{
      const cache=await caches.open(PAGE_CACHE).catch(()=>null);
      // Network first: installed iPhone PWAs must not stay on old CSS or JS
      // after a deployment. Previously a shell-cache hit lasted indefinitely.
      try{
        const response=await boundedFetch(event.request,{cache:'no-cache'});
        if(response.ok){if(cache)try{await cache.put(dataKey(event.request),response.clone());}catch{}return response;}
        const previous=await cache?.match(dataKey(event.request));return previous?offlineResponse(previous):response;
      }catch{
        return offlineResponse(await cache?.match(dataKey(event.request)));
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

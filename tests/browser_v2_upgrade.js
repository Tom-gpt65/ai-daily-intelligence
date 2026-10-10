/* Actual V1/V2/V3 service worker -> S1 upgrade at the production subdirectory scope.
 * Local disposable browser contexts only; cloud configuration is disabled.
 * Real cache migration/network failures; no mocked service worker or private API. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const http=require('node:http');
const {chromium,webkit}=require('playwright');
const ROOT=path.resolve(__dirname,'../site');
const PREFIX='/ai-daily-intelligence/';
const LATEST=JSON.parse(fs.readFileSync(path.join(ROOT,'reports/index.json'),'utf8'))[0].date;
const CACHE_FIXTURE=JSON.parse(fs.readFileSync(path.join(ROOT,'reports/'+LATEST+'.json'),'utf8'));
async function exercise(engine,type,legacyVersion){
  let legacy=true,failedData=false;
  const server=http.createServer((request,response)=>{
    const pathname=new URL(request.url,'http://localhost').pathname;
    if(!pathname.startsWith(PREFIX)){response.writeHead(404).end();return;}
    const relative=pathname.slice(PREFIX.length)||'index.html';
    if(failedData&&relative.startsWith('reports/')){response.writeHead(503).end('Temporary failure');return;}
    if(relative==='cloud-config.json'){
      response.writeHead(200,{'Content-Type':'application/json','Cache-Control':'no-store'})
        .end(JSON.stringify({supabase_url:'',anon_key:''}));return;
    }
    let target=path.resolve(ROOT,relative);
    if(!target.startsWith(ROOT+path.sep)){response.writeHead(403).end();return;}
    if(relative==='sw.js'&&legacy)target=path.join(__dirname,'fixtures/legacy-sw-'+legacyVersion+'.js');
    const mime={'.html':'text/html; charset=utf-8','.js':'application/javascript',
      '.css':'text/css','.json':'application/json','.webmanifest':'application/manifest+json',
      '.png':'image/png','.svg':'image/svg+xml'}[path.extname(target)]||'application/octet-stream';
    fs.readFile(target,(error,body)=>{
      if(error){response.writeHead(404).end();return;}
      response.writeHead(200,{'Content-Type':mime,'Cache-Control':'no-store'}).end(body);
    });
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const BASE='http://127.0.0.1:'+server.address().port+PREFIX;
  let browser,context;
  try{
  browser=await type.launch({headless:true});
  context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,
    hasTouch:true,serviceWorkers:'allow'});
    const page=await context.newPage(),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto(BASE,{waitUntil:'domcontentloaded'});
    await page.locator('#reader .word').first().waitFor();
    await page.evaluate(async()=>{
      await navigator.serviceWorker.register('./sw.js',{updateViaCache:'none'});
      await navigator.serviceWorker.ready;
    });
    await page.waitForFunction(async()=>navigator.serviceWorker.controller&&
      (await caches.keys()).some(key=>(key.startsWith('ai-daily-V')||key.startsWith('ai-daily-S1-2-'))&&key.endsWith('-reports')));
    const stored=await page.evaluate(async fixture=>{
      const snapshot={
        'ai-daily-saved-v2':JSON.stringify({evidence:{word:'evidence',translation:'證據'}}),
        'ai-daily-reading-progress-v1':JSON.stringify({'2026-10-09':48}),
        'ai-daily-answers-v1':JSON.stringify({'2026-10-09':{Q1:'my answer'}}),
        'ai-daily-cloud-cache-v1-user-a':JSON.stringify({privateA:{translation:'帳戶甲'}}),
        'ai-daily-cloud-cache-v1-user-b':JSON.stringify({privateB:{translation:'帳戶乙'}}),
        'ai-daily-cloud-pending-v1-user-a':JSON.stringify([{event_id:'unsent-event'}]),
        'ai-daily-cloud-session-v1':JSON.stringify({access_token:'TEST_ONLY_NEVER_EXPORT',refresh_token:'TEST_REFRESH'})
      };
      for(const [key,value] of Object.entries(snapshot))localStorage.setItem(key,value);
      const cache=await caches.open('ai-daily-V1-paper-calm-reading-reports');
      await cache.put('./reports/2026-10-01.json?rev=old',new Response(JSON.stringify({...fixture,date:'2026-10-01',historicSentinel:true})));
      // Some existing tablets have V2 as their most recent installation.
      // Its visited report must survive the S1 upgrade too.
      const previousV2=await caches.open('ai-daily-V2-stable-reading-reports');
      await previousV2.put('./reports/2026-10-02.json?rev=v2',
        new Response(JSON.stringify({...fixture,date:'2026-10-02',v2Sentinel:true})));
      await caches.open('unrelated-application');
      return snapshot;
    },CACHE_FIXTURE);
    console.log(engine+' seeded V1 public keys:',await page.evaluate(async()=>
      (await (await caches.open('ai-daily-V1-paper-calm-reading-reports')).keys()).map(key=>key.url)));
    legacy=false;
    await page.evaluate(async()=>{const registration=await navigator.serviceWorker.getRegistration();await registration.update();});
    // Poll the ACTUAL cache contents from Node. In some browser engines,
    // passing an async predicate to waitForFunction can incorrectly resolve
    // before the service worker's waitUntil(activate) migration completes.
    // A S1 cache name may exist while it is still EMPTY during install.
    let ready=false,lastState;
    for(let attempt=0;attempt<100;attempt++){
      lastState=await page.evaluate(async()=>{
        const keys=await caches.keys();
        const v2=keys.includes('ai-daily-S1-3-reading-reports');
        let foundIndex=false,foundHistory=false;
        if(v2){
          const store=await caches.open('ai-daily-S1-3-reading-reports');
          const index=await store.match('./reports/index.json');
          const history=await store.match('./reports/2026-10-01.json');
          foundIndex=!!index;
          if(history){
            try{foundHistory=(await history.clone().json()).historicSentinel===true;}
            catch{/* A corrupted migration is a failed acceptance. */}
          }
        }
        return {keys,foundIndex,foundHistory};
      });
      if(lastState.foundIndex&&lastState.foundHistory&&
         !lastState.keys.includes('ai-daily-V1-paper-calm-reading-reports')&&
         !lastState.keys.includes('ai-daily-V2-stable-reading-reports')){
        ready=true;break;
      }
      await new Promise(resolve=>setTimeout(resolve,200));
    }
    assert.ok(ready,engine+' V1/V2->S1 worker activation/migration incomplete: '+JSON.stringify(lastState));
    const migrated=await page.evaluate(async()=>{
      const cache=await caches.open('ai-daily-S1-3-reading-reports');
      const history=await cache.match('./reports/2026-10-01.json');
      return {history:history?await history.json():null, publicKeys:(await cache.keys()).map(key=>key.url),
              index:!!await cache.match('./reports/index.json'),keys:await caches.keys()};
    });
    assert.equal(migrated.history?.historicSentinel,true,engine+' lost public V1 history: '+JSON.stringify(migrated));
    const migratedV2=await page.evaluate(async()=>{
      const store=await caches.open('ai-daily-S1-3-reading-reports');
      const response=await store.match('./reports/2026-10-02.json');
      return response?await response.json():null;
    });
    assert.equal(migratedV2?.v2Sentinel,true,engine+' lost public V2 history');
    assert.ok(!migrated.keys.includes('ai-daily-V2-stable-reading-reports'),
      engine+' did not retire V2 cache safely');
    assert.equal(migrated.index,true);
    assert.ok(migrated.keys.includes('unrelated-application'));
    for(const [key,value] of Object.entries(stored))
      assert.equal(await page.evaluate(key=>localStorage.getItem(key),key),value,engine+' upgrade changed '+key);
    for(let i=0;i<12;i++)await page.evaluate(async({date,i})=>{
      const response=await fetch('./reports/'+date+'.json?rev='+i,{cache:'no-store'});
      if(!response.ok)throw Error('Refresh failed');
      await response.json();
    },{date:LATEST,i});
    const variants=await page.evaluate(async date=>{
      const cache=await caches.open('ai-daily-S1-3-reading-reports');
      return (await cache.keys()).filter(key=>key.url.includes('/'+date+'.json')).map(key=>key.url);
    },LATEST);
    assert.equal(variants.length,1);
    assert.equal(new URL(variants[0]).search,'');
    failedData=true;
    const cached=await page.evaluate(async date=>{
      const response=await fetch('./reports/'+date+'.json?rev=server-failure',{cache:'no-store'});
      return {status:response.status,report:await response.json()};
    },LATEST);
    assert.equal(cached.status,200);
    assert.equal(cached.report.date,LATEST);
    assert.equal(await page.locator('#site-version').innerText(),'S1');
    assert.equal(errors.length,0,errors.join('\n'));
    console.log(engine+' V1/V2 -> S1 PASS: public report migration, unchanged device/account/session/pending data, canonical refreshes, HTTP 503 fallback, subdirectory scope');
  }finally{
    await context?.close();await browser?.close();
    server.closeAllConnections?.();await new Promise(resolve=>server.close(resolve));
  }
}
(async()=>{for(const legacy of ['v1','v2','v3','s1-2']){await exercise('Chromium '+legacy,chromium,legacy);await exercise('WebKit '+legacy,webkit,legacy);}})()
  .catch(error=>{console.error(error);process.exitCode=1;});

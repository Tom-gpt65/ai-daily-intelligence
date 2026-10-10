/* Actual V1 service worker -> V2 upgrade at the production subdirectory scope.
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
async function exercise(engine,type){
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
    if(relative==='sw.js'&&legacy)target=path.join(__dirname,'fixtures/legacy-sw-v1.js');
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
  const browser=await type.launch({headless:true});
  const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,
    hasTouch:true,serviceWorkers:'allow'});
  try{
    const page=await context.newPage(),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto(BASE,{waitUntil:'domcontentloaded'});
    await page.locator('#reader .word').first().waitFor();
    await page.evaluate(async()=>{
      await navigator.serviceWorker.register('./sw.js',{updateViaCache:'none'});
      await navigator.serviceWorker.ready;
    });
    await page.waitForFunction(async()=>navigator.serviceWorker.controller&&
      (await caches.keys()).includes('ai-daily-V1-paper-calm-reading-reports'));
    const stored=await page.evaluate(async()=>{
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
      await cache.put('./reports/2026-10-01.json?rev=old',new Response('{"historicSentinel":true}'));
      await caches.open('unrelated-application');
      return snapshot;
    });
    legacy=false;
    await page.evaluate(async()=>{const registration=await navigator.serviceWorker.getRegistration();await registration.update();});
    await page.waitForFunction(async()=>{
      const keys=await caches.keys();
      return keys.includes('ai-daily-V2-stable-reading-reports')&&!keys.includes('ai-daily-V1-paper-calm-reading-reports');
    },{},{timeout:20000});
    const migrated=await page.evaluate(async()=>{
      const cache=await caches.open('ai-daily-V2-stable-reading-reports');
      return {history:await (await cache.match('./reports/2026-10-01.json')).json(),
              index:!!await cache.match('./reports/index.json'),keys:await caches.keys()};
    });
    assert.equal(migrated.history.historicSentinel,true);
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
      const cache=await caches.open('ai-daily-V2-stable-reading-reports');
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
    assert.equal(await page.locator('#site-version').innerText(),'V2');
    assert.equal(errors.length,0,errors.join('\n'));
    console.log(engine+' V1 -> V2 PASS: public report migration, unchanged device/account/session/pending data, canonical refreshes, HTTP 503 fallback, subdirectory scope');
  }finally{
    await context.close();await browser.close();
    server.closeAllConnections?.();await new Promise(resolve=>server.close(resolve));
  }
}
(async()=>{await exercise('Chromium',chromium);await exercise('WebKit',webkit);})()
  .catch(error=>{console.error(error);process.exitCode=1;});

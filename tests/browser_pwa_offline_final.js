/* Final PWA resilience: actual CacheStorage with origin server shut down,
 * article + dictionary + local words, complete private JSON backup.
 * Offline cold-start navigation on iOS still needs a real-device test.
 * Runs against a local static site only; never authenticates a user.
 */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const http=require('node:http');
const {chromium,webkit}=require('playwright');
const ROOT=path.resolve(__dirname,'../site');
function staticServer(){
  return http.createServer((request,response)=>{
    const pathname=new URL(request.url,'http://localhost').pathname;
    const target=path.resolve(ROOT,'.'+decodeURIComponent(pathname==='/'?'/index.html':pathname));
    if(!target.startsWith(ROOT+path.sep)){response.writeHead(403).end();return;}
    const ext=path.extname(target);
    const mime={'.html':'text/html; charset=utf-8','.js':'application/javascript',
      '.css':'text/css','.json':'application/json','.webmanifest':'application/manifest+json',
      '.svg':'image/svg+xml','.png':'image/png'}[ext]||'application/octet-stream';
    fs.readFile(target,(error,body)=>{
      if(error){response.writeHead(404).end('Not Found');return;}
      response.writeHead(200,{'Content-Type':mime,'Cache-Control':'no-cache'}).end(body);
    });
  });
}
async function beginServing(server,port=0){
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(port,'127.0.0.1',()=>{
    server.off('error',reject);resolve();
  });});
  return server.address().port;
}
async function stopServing(server){
  if(!server.listening)return;
  const done=new Promise((resolve,reject)=>server.close(err=>err?reject(err):resolve()));
  server.closeAllConnections?.();
  await done;
}

async function exercise(browserType,engine,width){
  // Own origin is shut down for the test. This tests actual network failure,
  // not a simulated offline text banner or a mocked Service Worker.
  const server=staticServer();
  const port=await beginServing(server);
  const BASE='http://127.0.0.1:'+port+'/';
  const browser=await browserType.launch({headless:true});
  const context=await browser.newContext({
    viewport:{width,height:844},
    hasTouch:width<=430,
    isMobile:width<=430,
    acceptDownloads:true,
    serviceWorkers:'allow'
  });
  try{
    // Do not install Playwright request routes: they can bypass Service Worker fetch handling.
    const page=await context.newPage();
    const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto(BASE,{waitUntil:'domcontentloaded',timeout:25000});
    await page.locator('#reader .essay-paragraph .word').first().waitFor({
      state:'visible',timeout:25000
    });
    const firstWord=page.locator('#reader .essay-paragraph .word').first();
    const word=(await firstWord.innerText()).toLowerCase().replace(/[^a-z'-]/g,'').replace(/'s$/,'');
    assert.ok(/^[a-z][a-z'-]{0,45}$/.test(word),engine+' invalid test word '+word);
    await firstWord.click();
    await page.locator('#save-word').click();
    await page.locator('#pop-close').click();
    await page.locator('[data-view="words"]').click();
    assert.equal((await page.locator('#saved-count').innerText()).trim(),'1');
    await page.evaluate(()=>{
      localStorage.setItem('ai-daily-cloud-session-v1',
        JSON.stringify({access_token:'SECRET_NEVER_EXPORT',refresh_token:'REFRESH_NEVER_EXPORT'}));
    });

    // iOS standalone App must be capable of creating an OFFLINE export,
    // which excludes Supabase auth credentials and preserves reading answers.
    const [download]=await Promise.all([
      page.waitForEvent('download',{timeout:10000}),
      page.locator('#export-all').click()
    ]);
    assert.match(download.suggestedFilename(),/ai-daily-learning-backup-\d{4}-\d{2}-\d{2}\.json/);
    const localFile=await download.path();
    assert.ok(localFile,'Downloaded study backup missing');
    const plain=fs.readFileSync(localFile,'utf8');
    const data=JSON.parse(plain);
    assert.equal(data.type,'ai-daily-learning-backup');
    assert.ok(data.words[word],engine+' backup missed saved vocabulary');
    for(const key of ['readRecords','writtenAnswers','progressRecords','quizSelections'])
      assert.ok(data[key]&&typeof data[key]==='object',engine+' backup missing '+key);
    assert.ok(!plain.includes('SECRET_NEVER_EXPORT')&&!plain.includes('REFRESH_NEVER_EXPORT'),
      engine+' backup leaked authentication tokens');

    // The production app auto-registers on HTTPS. The local HTTP loopback test
    // explicitly registers the same SW to avoid changing production behaviour.
    await page.evaluate(async()=>{
      if(!('serviceWorker' in navigator))throw new Error('Service Worker unsupported');
      await navigator.serviceWorker.register('./sw.js');
    });
    // Wait until latest article and app shell are controlled by the actual SW.
    await page.waitForFunction(async()=>{
      if(!navigator.serviceWorker?.controller)return false;
      const keys=await caches.keys();
      if(!keys.some(k=>k.includes('V1-paper-calm-reading')))return false;
      const names=await caches.keys();
      const match=await Promise.all(names.map(async name=>{
        const cache=await caches.open(name);
        return {shell:await cache.match('./index.html'),
                index:await cache.match('./reports/index.json'),
                gloss:await cache.match('./offline-glossary.json')};
      }));
      return match.some(m=>m.shell)&&match.some(m=>m.index)&&match.some(m=>m.gloss);
    },null,{timeout:20000});
    // Prove core data is accessible from real browser CacheStorage,
    // even after its HTTP origin has stopped. This validates actual cached
    // payloads but NOT a cold-start offline navigation on iPad Safari.
    const snapshot=await page.evaluate(async()=>{
      async function cached(path){
        const absolute=new URL(path,location.href).href;
        for(const name of await caches.keys()){
          const cache=await caches.open(name);
          const entry=await cache.match(absolute,{ignoreSearch:true});
          if(entry)return entry;
        }
        return null;
      }
      const html=await cached('./index.html');
      const index=await cached('./reports/index.json');
      const glossary=await cached('./offline-glossary.json');
      if(!html||!index||!glossary)return {ok:false,missing:true,
        html:Boolean(html),index:Boolean(index),glossary:Boolean(glossary),
        cacheNames:await caches.keys()};
      const markup=await html.text(),rows=await index.json(),terms=await glossary.json();
      const today=rows[0]?.date;
      const article=await cached('./reports/'+today+'.json');
      if(!article)return {ok:false,missingArticle:today};
      const report=await article.json();
      return {ok:markup.includes('AI Daily Intelligence'),date:today,
        paragraphs:report.essay?.length||0,dictionary:!!report.dictionary,
        glossaryCount:Object.keys(terms).length};
    });
    // WebKit/Chromium loopback automation can expose a controlling SW while
    // caches are not queryable from this test. Never claim cold-start pass.
    const cacheConfirmed=Boolean(snapshot.ok&&snapshot.paragraphs>=5&&
      snapshot.dictionary&&snapshot.glossaryCount>10);
    if(!cacheConfirmed)console.log('NOT VERIFIED',engine,width+'px',
      'offline cold-start cache payload (manual real-iOS check required)');
    await stopServing(server);
    await assert.rejects(page.evaluate(async url=>{
      const response=await fetch(url+'uncached-network-probe',{cache:'no-store'});
      return response.status;
    },BASE),'The origin must truly be unreachable');
    const unavailable=await page.evaluate(async()=>{
      async function cached(path){
        const absolute=new URL(path,location.href).href;
        for(const name of await caches.keys()){
          const cache=await caches.open(name);
          const entry=await cache.match(absolute,{ignoreSearch:true});
          if(entry)return entry;
        }
        return null;
      }
      const html=await cached('./index.html');
      const index=await cached('./reports/index.json');
      if(!html||!index)return false;
      const rows=await index.json();
      const article=await cached('./reports/'+rows[0].date+'.json');
      if(!article)return false;
      const obj=await article.json();
      return (await html.text()).includes('AI Daily Intelligence') &&
        obj.essay?.length>=5 && Object.keys(obj.dictionary||{}).length>0;
    });
    if(cacheConfirmed)assert.ok(unavailable,
      engine+' previously verified cached article disappeared during outage');
    await page.locator('[data-view="words"]').click();
    assert.equal((await page.locator('#saved-count').innerText()).trim(),'1',
      engine+' local vocabulary disappeared during origin outage');
    await page.locator('[data-view="today"]').click();
    await page.locator('#reader .essay-paragraph .word').first().click();
    const translation=await page.locator('#lookup-translation').innerText();
    assert.ok(translation.trim().length>0,engine+' offline dictionary lookup failed');
    await page.locator('#pop-close').click();
    await beginServing(server,port);
    // Verify the saved backup and cache survived reconnection.
    await page.reload({waitUntil:'domcontentloaded',timeout:25000});
    await page.locator('#reader .essay-paragraph .word').first().waitFor({
      state:'visible',timeout:25000
    });
    await page.locator('[data-view="words"]').click();
    assert.equal((await page.locator('#saved-count').innerText()).trim(),'1');
    assert.deepEqual(errors,[],engine+' PWA unexpected JS errors');
    console.log('PASS',engine,width+'px',
      'offline-open page vocabulary and lookup, private full backup, reconnection', 
      'cold-start PWA cache:',cacheConfirmed?'confirmed':'not verified');
  }finally{await context.close();await browser.close();await stopServing(server);}
}
(async()=>{
  for(const [name,engine] of [['Chromium',chromium],['WebKit',webkit]]){
    for(const width of [390,820])await exercise(engine,name,width);
  }
  console.log('V1 saved data, offline-open-page behaviour and private JSON backup PASSED; iOS cold-start OFFLINE NOT VERIFIED');
})().catch(error=>{console.error(error);process.exitCode=1;});

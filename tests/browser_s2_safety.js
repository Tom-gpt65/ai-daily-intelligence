/* Real S2 UI: intentional empty withdrawal, bundled offline translation and
 * delayed legacy translation after article navigation. Isolated local origins. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {chromium,webkit}=require('playwright');
const fixture=require('./browser_fixture'),root=path.resolve(__dirname,'../site');
function server(){return http.createServer((req,res)=>{
  const relative=new URL(req.url,'http://localhost').pathname.slice(1)||'index.html';
  const target=path.resolve(root,relative);
  if(!target.startsWith(root+path.sep)){res.writeHead(403).end();return;}
  fs.readFile(target,(err,raw)=>{
    if(err){res.writeHead(404).end();return;}
    res.writeHead(200,{'Content-Type':{'.js':'application/javascript','.html':'text/html','.json':'application/json','.css':'text/css'}[path.extname(target)]||'application/octet-stream'}).end(raw);
  });
});}
async function fixtures(page){
  await page.route('**/cloud-config.json',r=>r.fulfill({contentType:'application/json',body:'{"supabase_url":"","anon_key":""}'}));
  await page.route('https://api.github.com/**',r=>r.fulfill({contentType:'application/json',body:'{"workflow_runs":[]}'}));
}
async function exercise(type,name){
  const origin=server();await new Promise(resolve=>origin.listen(0,'127.0.0.1',resolve));
  const url='http://127.0.0.1:'+origin.address().port+'/';
  const browser=await type.launch({headless:true});
  try{
    const context=await browser.newContext({serviceWorkers:'block'}),page=await context.newPage(),errors=[];
    page.on('pageerror',e=>errors.push(e.message));await fixtures(page);
    const stored={'ai-daily-saved-v2':'{"evidence":{"translation":"證據"}}',
      'ai-daily-answers-v1':'{"2026-10-09-v7-Q4":"My original answer"}',
      'ai-daily-cloud-cache-v1-user-a':'{"private":{"translation":"私人生字"}}',
      'ai-daily-cloud-pending-v1-user-a':'[{"event_id":"pending"}]',
      'ai-daily-cloud-session-v1':'{"access_token":"TEST_ONLY"}'};
    await page.addInitScript(values=>{for(const [key,value] of Object.entries(values))localStorage.setItem(key,value);},stored);
    await page.goto(url);await page.waitForFunction(()=>document.querySelector('#reader')?.textContent.includes('撤下'));
    assert.equal(await page.locator('#translate-toggle').isDisabled(),true);
    assert.equal(await page.locator('#reader .essay-paragraph').count(),0);
    assert.equal(await page.locator('#question-list .question-item').count(),0);
    await page.locator('#refresh-schedule').click();
    await page.waitForTimeout(250);
    for(const [key,value] of Object.entries(stored))assert.equal(await page.evaluate(k=>localStorage.getItem(k),key),value,name+' withdrawal changed private '+key);
    await page.locator('[data-view="words"]').click();assert.equal((await page.locator('#saved-count').innerText()).trim(),'1');
    assert.deepEqual(errors,[]);await context.close();

    const offline=await browser.newContext({serviceWorkers:'block'});await fixture.clock(offline);
    const p=await offline.newPage();await fixtures(p);
    await p.route('**/reports/**',r=>{
      const raw=fixture.body(new URL(r.request().url()).pathname.slice(1));
      return raw===null?r.continue():r.fulfill({contentType:'application/json',body:raw});
    });
    let external=0;await p.route('https://api.mymemory.translated.net/**',r=>{external++;return r.abort();});
    await p.goto(url);await p.locator('#reader .word').first().waitFor();
    const count=fixture.latest().essay.length;
    await offline.setOffline(true);await p.locator('#translate-toggle').click();
    await p.waitForFunction(n=>document.querySelectorAll('.translation-paragraph').length===n,count);
    assert.equal(external,0,'Bundled S2 translation must not contact a provider');
    await p.locator('#reader .word').first().click();
    assert.match(await p.locator('#lookup-translation').innerText(),/[\u3400-\u9fff]/);
    await offline.close();

    const race=await browser.newContext({serviceWorkers:'block'});await fixture.clock(race);
    const q=await race.newPage();await fixtures(q);q.on('dialog',d=>d.accept());
    await q.route('**/reports/**',r=>{
      const raw=fixture.body(new URL(r.request().url()).pathname.slice(1));
      return raw===null?r.continue():r.fulfill({contentType:'application/json',body:raw});
    });
    await fixture.legacyTranslation(q);
    let pending;await q.route('https://api.mymemory.translated.net/**',r=>{pending=r;return new Promise(resolve=>{r.release=resolve;});});
    await q.goto(url);await q.locator('#reader .word').first().waitFor();
    await q.locator('.paragraph-translate').first().click();
    for(let i=0;i<50&&!pending;i++)await q.waitForTimeout(50);
    assert.ok(pending,'Legacy translation request did not start');
    await q.locator('[data-view="archive"]').click();
    await q.locator('.archive-card').filter({hasText:'7 October 2026'}).click();
    await q.waitForFunction(()=>document.querySelector('#report-metadata')?.textContent.includes('7 October 2026'));
    await pending.fulfill({contentType:'application/json',body:JSON.stringify({responseStatus:200,responseData:{translatedText:'遲到的舊文章翻譯不可污染新文章。'}})});pending.release();
    await q.waitForTimeout(200);
    assert.equal(await q.locator('.translation-paragraph').count(),0,'Stale translation leaked into the new article');
    assert.equal(await q.locator('#translate-toggle').isDisabled(),false,'Old request left new translation locked');
    await race.close();console.log('PASS '+name+' S2 withdrawal/private storage, full offline translation/meaning and delayed-response race');
  }finally{await browser.close();origin.closeAllConnections?.();await new Promise(resolve=>origin.close(resolve));}
}
(async()=>{await exercise(chromium,'Chromium');await exercise(webkit,'WebKit');})().catch(e=>{console.error(e);process.exitCode=1;});

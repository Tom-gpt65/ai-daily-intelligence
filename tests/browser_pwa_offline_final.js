/* Final installed-PWA regression: actual service worker, network cut, offline
 * article + dictionary + local words, then full JSON backup without tokens.
 * Runs against a local static site only; never authenticates a user.
 */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {chromium,webkit}=require('playwright');
const BASE='http://127.0.0.1:8765/';

async function exercise(browserType,engine,width){
  const browser=await browserType.launch({headless:true});
  const context=await browser.newContext({
    viewport:{width,height:844},
    hasTouch:width<=430,
    isMobile:width<=430,
    acceptDownloads:true,
    serviceWorkers:'allow'
  });
  try{
    // No external GitHub API calls are required to read a cached article.
    await context.route('https://api.github.com/**',route=>route.fulfill({
      status:200,contentType:'application/json',
      headers:{'access-control-allow-origin':'*'},
      body:JSON.stringify({workflow_runs:[]})
    }));
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
    await context.setOffline(true);
    await page.reload({waitUntil:'domcontentloaded',timeout:25000});
    await page.locator('#reader .essay-paragraph .word').first().waitFor({
      state:'visible',timeout:25000
    });
    assert.equal(await page.evaluate(()=>navigator.onLine),false,engine+' offline flag failed');
    assert.equal(await page.locator('#site-version').innerText(),'V1');
    await page.locator('[data-view="words"]').click();
    assert.equal((await page.locator('#saved-count').innerText()).trim(),'1',
      engine+' locally saved words lost during PWA offline restart');
    await page.locator('[data-view="today"]').click();
    await page.locator('#reader .essay-paragraph .word').first().click();
    const translation=await page.locator('#lookup-translation').innerText();
    assert.ok(translation.trim().length>0,engine+' offline dictionary unavailable');
    await page.locator('#pop-close').click();
    await context.setOffline(false);
    // Verify the saved backup and cache survived reconnection.
    await page.reload({waitUntil:'domcontentloaded',timeout:25000});
    await page.locator('#reader .essay-paragraph .word').first().waitFor({
      state:'visible',timeout:25000
    });
    await page.locator('[data-view="words"]').click();
    assert.equal((await page.locator('#saved-count').innerText()).trim(),'1');
    assert.deepEqual(errors,[],engine+' PWA unexpected JS errors');
    console.log('PASS',engine,width+'px',
      'real service worker, offline article, dictionary, saved words, safe full backup, reconnection');
  }finally{await context.close();await browser.close();}
}
(async()=>{
  for(const [name,engine] of [['Chromium',chromium],['WebKit',webkit]]){
    for(const width of [390,820])await exercise(engine,name,width);
  }
  console.log('V1 installed-PWA offline resilience and complete JSON backup PASSED');
})().catch(error=>{console.error(error);process.exitCode=1;});

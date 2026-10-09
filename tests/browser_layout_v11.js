/* Layout, zoom and state-reset regression tests for real Chromium and WebKit. */
const assert=require('node:assert/strict');
const {chromium,webkit}=require('playwright');
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const reportIndex=JSON.parse(fs.readFileSync(path.join(root,'site/reports/index.json'),'utf8'));
const date=reportIndex[0].date;
let passes=0;
async function check(engine,browser,width){
 const instance=await browser.launch({headless:true});
 const ctx=await instance.newContext({viewport:{width,height:844},isMobile:width<=430,hasTouch:width<=430,deviceScaleFactor:2,reducedMotion:'reduce'});
 try{
  const page=await ctx.newPage();
  const failures=[];page.on('pageerror',e=>failures.push(e.message));
  await page.route('https://api.github.com/**',r=>r.fulfill({status:200,headers:{'access-control-allow-origin':'*'},contentType:'application/json',body:JSON.stringify({workflow_runs:[]})}));
  await page.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded',timeout:25000});
  await page.locator('.essay-paragraph').first().waitFor({state:'visible',timeout:25000});
  await page.locator('#font-button').click();
  await page.locator('#font-button').click();
  assert.equal(await page.locator('#reader.font-xlarge').count(),1,engine+' '+width+': large font not activated');
  const metric=await page.evaluate(()=>{
    const rect=id=>{const el=document.querySelector(id);if(!el)return null;const r=el.getBoundingClientRect();return {left:r.left,right:r.right,width:r.width}};
    return {viewport:window.innerWidth,documentWidth:document.documentElement.scrollWidth,
       article:rect('#reader'),paragraph:rect('#reader .essay-paragraph'),
       toolbar:rect('.reader-toolbar'),nav:rect('#reader-navigator'),
       card:rect('.briefing-card'),font:getComputedStyle(document.querySelector('#reader')).fontSize}
  });
  assert.ok(metric.documentWidth<=metric.viewport+2,engine+' '+width+': horizontally clipped body '+JSON.stringify(metric));
  for(const key of ['article','paragraph','toolbar','nav','card']){
    assert.ok(metric[key].left>=-2 && metric[key].right<=metric.viewport+2,engine+' '+width+' '+key+' runs off viewport: '+JSON.stringify(metric));
  }
  if(width<=1180){
    assert.ok(await page.locator('#reader-nav-select').isVisible(),engine+' '+width+': accessible chapter selector missing');
    await page.locator('#reader-nav-select').selectOption('3');
    await page.waitForFunction(()=>{
      const top=document.querySelector('#reading-paragraph-3')?.getBoundingClientRect().top;
      return typeof top==='number'&&top>=80&&top<=Math.min(window.innerHeight*0.75,675);
    },null,{timeout:3000});
    const top=await page.locator('#reading-paragraph-3').evaluate(el=>el.getBoundingClientRect().top);
    assert.ok(top>=80&&top<=675,engine+' '+width+': section jump not visible within the readable viewport: '+top);
    assert.ok(await page.locator('#tools-toggle').isVisible(),engine+' '+width+': compact tools toggle absent');
  }
  const original=await page.evaluate(()=>localStorage.getItem('ai-daily-saved-v2'));
  await page.locator('#reset-reading').click();
  assert.equal(await page.locator('#reader.font-xlarge').count(),0,engine+' '+width+': layout reset failed');
  assert.equal(await page.evaluate(()=>localStorage.getItem('ai-daily-font-scale')),'0',engine+' '+width+': font-scale setting not reset');
  assert.equal(await page.evaluate(()=>localStorage.getItem('ai-daily-saved-v2')),original,engine+' '+width+': reset damaged saved words');
  assert.deepEqual(failures,[],engine+' '+width+': uncaught JS failures');
  console.log('PASS',engine,width,'reflow at',metric.font,'and safe reset');
  passes++;
 }finally{await ctx.close();await instance.close();}
}
(async()=>{
 for(const [engine,browser] of [['chromium',chromium],['webkit',webkit]]){
   for(const width of [320,390,820,1024,1180]) await check(engine,browser,width);
 }
 const sw=fs.readFileSync(path.join(root,'site/sw.js'),'utf8');
 assert.ok(sw.includes("fetch(event.request,{cache:'no-cache'})"),'Service worker still serves stale CSS or JavaScript without first checking the network');
 assert.ok(sw.includes("cache.match(event.request,{ignoreSearch:true})"),'Offline fallback ignores version-busting query');
 assert.ok(fs.readFileSync(path.join(root,'site/index.html'),'utf8').includes('app.js?v=15'),
   'HTML does not break old iPhone JavaScript URL');
 console.log('RESULT:',passes,'/ 10 responsive browser layouts plus PWA freshness invariants passed');
})().catch(e=>{console.error(e);process.exit(1)});

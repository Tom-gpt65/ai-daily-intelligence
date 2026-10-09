/* v12 layout regression: actual Chromium/WebKit viewport, reset and cache controls */
const assert=require('node:assert/strict');
const {chromium,webkit}=require('playwright');
(async()=>{
 let count=0;
 for(const [name,engine] of [['Chromium',chromium],['WebKit',webkit]]){
  const browser=await engine.launch({headless:true});
  try{
   for(const width of [375,768,1024]){
    const ctx=await browser.newContext({viewport:{width,height:900},isMobile:width<500,hasTouch:width<500});
    try{
     const page=await ctx.newPage(),errors=[];
     page.on('pageerror',e=>errors.push(e.message));
     await page.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded'});
     await page.locator('#reader .essay-paragraph').first().waitFor({state:'visible',timeout:20000});
     assert.equal(await page.locator('#site-version').innerText(),'v14');
     assert.equal(await page.locator('.intro p').count(),0,'Unnecessary intro copy still displayed');
     const warning=await page.locator('#freshness-note').innerText();
     if(await page.locator('#freshness-note').isVisible())assert.match(warning,/舊文章|示範文章|1,000 字|晚於/,'Visible warning must explain a genuine issue');
     const detailPlace=await page.evaluate(()=>document.querySelector('#technical-status').compareDocumentPosition(document.querySelector('#question-list')) & Node.DOCUMENT_POSITION_PRECEDING);
     assert.ok(detailPlace,'Technical details must follow reading content');
     const measures=await page.evaluate(()=>{
       const p=document.querySelector('#reader .essay-paragraph');
       const rect=p.getBoundingClientRect();
       return {document:document.documentElement.scrollWidth,viewport:window.innerWidth,
         paragraph:rect.width,left:rect.left,right:rect.right,
         select:getComputedStyle(document.querySelector('#reader-nav-select')).display};
     });
     assert.ok(measures.document<=width+2,name+' '+width+' document overflow '+JSON.stringify(measures));
     assert.ok(measures.left>=-1&&measures.right<=width+1,name+' '+width+' paragraph clipped '+JSON.stringify(measures));
     if(width<=1024)assert.notEqual(measures.select,'none','Chapter picker missing');
     await page.locator('#font-button').click();
     const scale=await page.locator('#reader').getAttribute('class');
     assert.ok(scale.includes('font-large'));
     await page.locator('#reset-reading').click({force:true});
     assert.ok(!(await page.locator('#reader').getAttribute('class')).includes('font-large'));
     // Test a missing inflection from the original article dictionary entirely offline.
     await page.evaluate(()=>{
       const paragraph=document.createElement('p');paragraph.className='essay-paragraph';
       paragraph.append(document.createTextNode('A funding round '));
       const button=document.createElement('button');button.id='offline-concerns-probe';
       button.className='word';button.type='button';button.textContent='concerns';
       paragraph.append(button,document.createTextNode(' expectations about future value.'));
       document.querySelector('#reader').append(paragraph);
     });
     await page.locator('#offline-concerns-probe').click();
     assert.match(await page.locator('#lookup-translation').innerText(),/關乎/,'Common inflected word lacks offline meaning');
     assert.ok(await page.locator('#lookup-online').isHidden(),'Offline meaning must not request a third-party translation');
     await page.locator('#pop-close').click();
     assert.deepEqual(errors,[],name+' '+width+' script errors');
     console.log('PASS',name,width,'reader reflow, picker and reset');
     count++;
    }finally{await ctx.close();}
   }
  }finally{await browser.close();}
 }
 console.log('RESULT:',count,'/ 6 v13 browser layout cases passed');
})().catch(e=>{console.error(e);process.exit(1)});

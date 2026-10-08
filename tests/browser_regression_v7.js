/* Real browser-regression smoke test: iPhone-sized Chromium and WebKit.
 * Translation network is mocked here to test UI/consent/progress, not its
 * real-world provider quality; provider health is checked separately. */
const assert=require('node:assert/strict');
const {chromium,webkit}=require('playwright');

(async()=>{
 const cases=[{engine:'chromium',browser:chromium},{engine:'webkit',browser:webkit}];
 let passed=0;
 for(const {engine,browser} of cases){
  const instance=await browser.launch({headless:true});
  try{
   for(const width of [320,375,390,430]){
    const context=await instance.newContext({viewport:{width,height:860},isMobile:true,hasTouch:true,deviceScaleFactor:2});
    const page=await context.newPage();
    const errors=[];
    page.on('pageerror',err=>errors.push(err.message));
    page.on('dialog',dialog=>dialog.accept());
    await page.route('https://api.mymemory.translated.net/**',async route=>{
      await route.fulfill({status:200,contentType:'application/json',
         headers:{'access-control-allow-origin':'*'},
         body:JSON.stringify({responseStatus:200,responseData:{translatedText:'這是作為測試用途的繁體中文段落。'}})});
    });
    try{
     await page.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded',timeout:20000});
     await page.locator('#reader .essay-paragraph').first().waitFor({state:'visible',timeout:20000});
     const count=await page.locator('#reader .essay-paragraph').count();
     assert.ok(count>=5,engine+'/'+width+': paragraphs not loaded');
     await page.locator('#font-button').click();
     await page.locator('#font-button').click();
     const docWidth=await page.evaluate(()=>document.documentElement.scrollWidth);
     assert.ok(docWidth<=width+2,engine+'/'+width+': horizontal page overflow '+docWidth);
     await page.locator('#translate-toggle').click();
     await page.waitForFunction(expected=>document.querySelectorAll('.translation-paragraph').length===expected,count,{timeout:30000});
     const translated=await page.locator('.translation-paragraph').count();
     assert.equal(translated,count,engine+'/'+width+': full translation incomplete');
     await page.locator('#reader .word').first().click();
     await page.locator('#dictionary-popover').waitFor({state:'visible',timeout:7000});
     const rect=await page.locator('#dictionary-popover').boundingBox();
     assert.ok(rect&&rect.x>=-2&&rect.x+rect.width<=width+2,engine+'/'+width+': dictionary outside viewport');
     await page.locator('#pop-close').click();
     const mc=page.locator('#question-list .question-item').filter({has:page.locator('input[type=radio]')}).first();
     assert.ok((await mc.count())===1,engine+'/'+width+': no scored MC task');
     await mc.locator('input[type=radio]').first().check();
     await mc.locator('button.question-action').first().click();
     assert.ok(await mc.locator('input[type=radio]').first().isDisabled(),engine+'/'+width+': first-attempt not locked');
     const evidence=page.locator('#question-list .evidence-jump').first();
     await evidence.click();
     const isMarked=await page.locator('#reader .evidence-focus').count();
     assert.ok(isMarked>=1,engine+'/'+width+': evidence jump did not mark passage');
     assert.deepEqual(errors,[],engine+'/'+width+': browser script errors');
     console.log('PASS',engine,'iPhone',width,'paragraphs',count,'translated',translated);
     passed++;
    } finally{await context.close();}
   }
  }finally{await instance.close();}
 }
 console.log('RESULT:',passed,'/ 8 iPhone-sized browser scenarios passed');
})().catch(error=>{console.error(error);process.exit(1);});

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
  // Recovery scenario: first chunk succeeds; the next request exhausts
  // its retry budget. The second attempt must reuse the already translated
  // chunk rather than spend the anonymous API allowance again.
  const recoverContext=await instance.newContext({
    viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:2
  });
  try{
    const recoverPage=await recoverContext.newPage();
    recoverPage.on('dialog',dialog=>dialog.accept());
    let requests=0;
    await recoverPage.route('https://api.mymemory.translated.net/**',async route=>{
      requests++;
      if(requests===2||requests===3){
        await route.fulfill({status:503,contentType:'application/json',
          headers:{'access-control-allow-origin':'*'},
          body:JSON.stringify({responseStatus:503})});
      }else{
        await route.fulfill({status:200,contentType:'application/json',
          headers:{'access-control-allow-origin':'*'},
          body:JSON.stringify({responseStatus:200,responseData:{translatedText:'已翻譯的部分會儲存供下次接續。'}})});
      }
    });
    await recoverPage.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded',timeout:20000});
    await recoverPage.locator('#reader .essay-paragraph').first().waitFor({state:'visible',timeout:20000});
    await recoverPage.locator('.paragraph-translate').first().click();
    await recoverPage.waitForFunction(()=>document.querySelector('#toast')?.textContent.includes('翻譯未完成'),null,{timeout:15000});
    assert.equal(requests,3,engine+': 1 good + 2 failed request attempts expected');
    const saved=await recoverPage.evaluate(()=>{
      const key=Object.keys(localStorage).find(k=>k.includes('-chunks-0'));
      return key?JSON.parse(localStorage.getItem(key)):null;
    });
    assert.ok(saved,engine+': missing successful chunk cache');
    assert.ok(saved.chunks.length>=2,engine+': paragraph expected to require multiple chunks');
    assert.equal(saved.results.filter(Boolean).length,1,engine+': cached first good chunk missing');
    await recoverPage.locator('.paragraph-translate').first().click();
    await recoverPage.locator('#reader .translation-paragraph').first().waitFor({state:'visible',timeout:20000});
    assert.equal(requests,3+saved.chunks.length-1,engine+': retried an already-translated chunk');
    console.log('PASS',engine,'interrupted paragraph resumed from',saved.results.filter(Boolean).length,'cached chunk');
    passed++;
  }finally{await recoverContext.close();}
  const fullContext=await instance.newContext({
    viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:2
  });
  try{
    const fullPage=await fullContext.newPage();
    fullPage.on('dialog',dialog=>dialog.accept());
    let call=0;
    await fullPage.route('https://api.mymemory.translated.net/**',async route=>{
      call++;
      if(call===3||call===4){
        await route.fulfill({status:503,headers:{'access-control-allow-origin':'*'},
          body:JSON.stringify({responseStatus:503})});
      }else{
        await route.fulfill({status:200,contentType:'application/json',
          headers:{'access-control-allow-origin':'*'},
          body:JSON.stringify({responseStatus:200,responseData:{translatedText:'這是已完成的繁體中文翻譯。'}})});
      }
    });
    await fullPage.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded',timeout:20000});
    await fullPage.locator('#reader .essay-paragraph').first().waitFor({state:'visible',timeout:20000});
    const paragraphs=await fullPage.locator('#reader .essay-paragraph').count();
    await fullPage.locator('#translate-toggle').click();
    await fullPage.waitForFunction(()=>document.querySelector('#toast')?.textContent.includes('暫停在已完成段落'),null,{timeout:20000});
    const buttonText=await fullPage.locator('#translate-toggle').innerText();
    assert.match(buttonText,/繼續翻譯全文|重試全文翻譯/,engine+': user cannot retry an incomplete translation directly');
    await fullPage.locator('#translate-toggle').click();
    await fullPage.waitForFunction(total=>document.querySelectorAll('#reader .translation-paragraph').length===total,paragraphs,{timeout:30000});
    assert.match(await fullPage.locator('#translate-toggle').innerText(),/隱藏繁體中文譯文/,engine+': complete translation should be hideable');
    console.log('PASS',engine,'full translation resumes on one click after provider failure');
    passed++;
  }finally{await fullContext.close();}
  }finally{await instance.close();}
 }
 console.log('RESULT:',passed,'/ 12 iPhone browser scenarios passed');
})().catch(error=>{console.error(error);process.exit(1);});

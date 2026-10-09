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
     assert.equal(await page.locator('#site-version').innerText(),'v16');
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
     const inflectedMeaning=await page.locator('#lookup-translation').innerText();
     assert.match(inflectedMeaning,/[\u3400-\u9fff]/,'Common inflected word lacks a real Chinese offline meaning');
     assert.doesNotMatch(inflectedMeaning,/未收錄|待查|無法取得|請查詢/,'Inflection should not be an untranslated placeholder');
     assert.ok(await page.locator('#lookup-online').isHidden(),'Offline meaning must not request a third-party translation');
     await page.locator('#pop-close').click();
     // Archive regression: missing 8 October entry must open inside v16
     // without overwriting the current dated news report.
     await page.locator('[data-view="archive"]').click();
     const history=page.locator('#archive-list .archive-card').filter({hasText:'8 October 2026'});
     await history.waitFor({state:'visible',timeout:8000});
     await history.click();
     await page.waitForFunction(()=>document.querySelector('#report-headline')?.textContent?.startsWith('AI literacy:'),null,{timeout:12000});
     assert.match(await page.locator('#report-metadata').innerText(),/8 October 2026/,'Historical reading did not open');
     assert.ok(await page.locator('#freshness-note').isHidden(),'Historical reading should not claim the latest edition is missing');
     assert.match(await page.locator('#schedule-text').innerText(),/歷史文章/,'Historical reading must not be labelled as a failed daily schedule');
     assert.ok(await page.locator('#reader .essay-paragraph').count()>=10,'Historical passage paragraphs missing');
     assert.ok(await page.locator('#question-list').count()===1,'Historical practice panel missing');
     const evidence=page.locator('#reader .word').filter({hasText:/^evidence$/i}).first();
     await evidence.click();
     assert.ok((await page.locator('#lookup-translation').innerText()).length>1,'Archived word meaning missing');
     assert.ok(await page.locator('#lookup-online').isHidden(),'Archive words must be available offline');
     // Test real user state changes: saving a word, answering a multiple-choice
     // question, writing a short response, and surviving a full reload.
     await page.locator('#save-word').click();
     await page.locator('#pop-close').click();
     const itemCount=await page.locator('#question-list .question-item').count();
     assert.equal(itemCount,7,'Historical edition must render seven exercises');
     await page.locator('#question-list .question-item').first().locator('input[type="radio"]').first().check();
     await page.locator('#question-list .question-item').first().getByRole('button',{name:'提交選擇題'}).click();
     await page.locator('#question-list .question-answer').first().fill('The author contrasts confidence with verifiable evidence.');
     let persisted=await page.evaluate(()=>({
       word:JSON.parse(localStorage.getItem('ai-daily-saved-v2')||'{}').evidence,
       quiz:JSON.parse(localStorage.getItem('ai-daily-quiz-v6')||'{}')['2026-10-08-v7-Q1'],
       writing:JSON.parse(localStorage.getItem('ai-daily-answers-v1')||'{}')['2026-10-08-v7-Q4']
     }));
     assert.ok(persisted.word?.translation,'Saved vocabulary meaning was not persisted');
     assert.equal(persisted.quiz?.selected,0,'Multiple-choice answer was not persisted');
     assert.match(persisted.writing||'',/contrasts confidence/,'Written answer was not persisted');
     await page.reload({waitUntil:'domcontentloaded'});
     await page.locator('#reader .essay-paragraph').first().waitFor({state:'visible',timeout:20000});
     persisted=await page.evaluate(()=>({
       word:JSON.parse(localStorage.getItem('ai-daily-saved-v2')||'{}').evidence,
       quiz:JSON.parse(localStorage.getItem('ai-daily-quiz-v6')||'{}')['2026-10-08-v7-Q1'],
       writing:JSON.parse(localStorage.getItem('ai-daily-answers-v1')||'{}')['2026-10-08-v7-Q4']
     }));
     assert.ok(persisted.word?.translation && persisted.quiz && persisted.writing,
       'A reload must not erase saved words or practice answers');
     assert.equal(await page.locator('#site-version').innerText(),'v16','Routine archive testing must not upgrade site version');
     const ui=await page.evaluate(()=>{
       const reader=document.querySelector('#reader');
       return {font:getComputedStyle(reader).fontFamily,
         disclosure:!!document.querySelector('.translation-disclosure #translation-policy'),
         quality:!!document.querySelector('.quality-disclosure #reading-quality')};
     });
     assert.match(ui.font,/Iowan|Palatino|Georgia/,'English long-form serif system font missing');
     assert.ok(ui.disclosure&&ui.quality,'Important editorial and privacy notices must remain accessible');
     assert.deepEqual(errors,[],name+' '+width+' script errors');
     console.log('PASS',name,width,'reader reflow, picker and reset');
     count++;
    }finally{await ctx.close();}
   }
  }finally{await browser.close();}
 }
 console.log('RESULT:',count,'/ 6 v16 browser layout cases passed');
})().catch(e=>{console.error(e);process.exit(1)});

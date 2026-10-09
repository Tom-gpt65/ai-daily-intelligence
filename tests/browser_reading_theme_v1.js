/* Real computed-style regression (not a palette mock), Chromium + WebKit.
 * Checks both modes, iPhone / iPad / desktop, word saving, accessible controls,
 * colour contrast, persisted theme, print colours and original reading layout.
 */
'use strict';
const assert=require('node:assert/strict');
const {chromium,webkit}=require('playwright');
const BASE='http://127.0.0.1:8765/';
function rgb(value){
  const m=String(value).match(/rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)/i);
  assert.ok(m,'Invalid computed colour '+value);
  return m.slice(1,4).map(Number);
}
function luminance(value){
  const values=rgb(value).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);
  return .2126*values[0]+.7152*values[1]+.0722*values[2];
}
function contrast(a,b){
  const x=luminance(a),y=luminance(b);
  return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);
}
function eqRgb(a,b){return rgb(a).join(',')===rgb(b).join(',');}
async function computed(page,selector){
  return page.locator(selector).first().evaluate(el=>{
    const s=getComputedStyle(el),r=el.getBoundingClientRect();
    return {color:s.color,background:s.backgroundColor,border:s.borderTopColor,
      outline:s.outlineColor,outlineWidth:s.outlineWidth,
      fontSize:parseFloat(s.fontSize),lineHeight:parseFloat(s.lineHeight),
      opacity:parseFloat(s.opacity),width:r.width,visibility:s.visibility,display:s.display};
  });
}
function minRatio(fore,back,min,where){
  const ratio=contrast(fore,back);
  assert.ok(ratio+0.001>=min,where+' '+ratio.toFixed(2)+':1 below '+min+':1');
}
async function inspect(page,label,mode,width){
  const day=mode==='day';
  const expected=day?{
    bg:'rgb(242, 238, 230)',paper:'rgb(255, 253, 248)',side:'rgb(232, 225, 214)',
    accent:'rgb(53, 92, 78)',highlight:'rgb(229, 239, 232)'
  }:{
    bg:'rgb(23, 28, 30)',paper:'rgb(34, 41, 42)',side:'rgb(29, 37, 40)',
    accent:'rgb(178, 209, 185)',highlight:'rgb(53, 73, 63)'
  };
  const body=await computed(page,'body');
  const paper=await computed(page,'.briefing-card');
  const reader=await computed(page,'#reader');
  const heading=await computed(page,'#report-headline');
  const muted=await computed(page,'.reader-toolbar .helper');
  const toolbar=await computed(page,'.reader-toolbar');
  const sidebar=await computed(page,'.sidebar');
  const navigation=await computed(page,'.nav-item:not(.selected)');
  const selected=await computed(page,'.nav-item.selected');
  const word=await computed(page,'#reader .essay-paragraph .word');
  const line=await computed(page,'#reader .essay-paragraph');
  assert.ok(eqRgb(body.background,expected.bg),label+' incorrect page background');
  assert.ok(eqRgb(paper.background,expected.paper),label+' incorrect paper background');
  assert.ok(eqRgb(reader.background,expected.paper),label+' incorrect reader background');
  assert.ok(eqRgb(sidebar.background,expected.side),label+' incorrect sidebar background');
  minRatio(reader.color,reader.background,7,label+' main reader');
  minRatio(word.color,reader.background,7,label+' clickable word at rest');
  minRatio(heading.color,paper.background,7,label+' headline');
  minRatio(muted.color,toolbar.background,4.5,label+' toolbar hint');
  minRatio(navigation.color,sidebar.background,4.5,label+' sidebar nav');
  minRatio(selected.border,sidebar.background,3,label+' selected navigation border');
  assert.ok(reader.fontSize>=17,label+' small type '+reader.fontSize);
  assert.ok(reader.lineHeight/reader.fontSize>=1.6,label+' inadequate body line spacing');
  assert.ok(line.width<=reader.width+2,label+' paragraph overflows reader');
  assert.ok(width<650||line.width<=760,label+' reading measure unexpectedly broad');
  assert.equal(await page.locator('#site-version').innerText(),'V1',label+' release version changed');
  const dimensions=await page.evaluate(()=>({scrollWidth:document.documentElement.scrollWidth,
    clientWidth:document.documentElement.clientWidth}));
  assert.ok(dimensions.scrollWidth<=dimensions.clientWidth+2,
    label+' horizontal scroll overflow '+JSON.stringify(dimensions));
  const meta=await page.locator('meta[name="theme-color"]').getAttribute('content');
  assert.equal(meta,day?'#F2EEE6':'#171C1E',label+' browser chrome colour');
  await page.locator('[data-view="words"]').click();
  const input=await computed(page,'#sync-password-email');
  const button=await computed(page,'#sync-password-submit');
  const panel=await computed(page,'.cloud-sync-panel');
  const sideStatus=await computed(page,'.cloud-sync-help');
  minRatio(input.color,input.background,7,label+' password field text');
  minRatio(input.border,input.background,3,label+' password field border');
  minRatio(button.color,button.background,4.5,label+' password login button');
  minRatio(sideStatus.color,panel.background,4.5,label+' password help');
  await page.locator('#sync-password-email').focus();
  const focus=await computed(page,'#sync-password-email');
  assert.ok(parseFloat(focus.outlineWidth)>=2,label+' missing keyboard focus outline');
  minRatio(focus.outline,input.background,3,label+' focus ring');
  const legacy=await page.evaluate(()=>JSON.parse(localStorage.getItem('ai-daily-saved-v2')||'{}'));
  assert.ok(legacy.auditword,label+' legacy vocabulary disappeared');
  console.log('PASS',label,'reader contrast, controls, focus, responsive measure and legacy word');
}
(async()=>{
  for(const [engine,browserType] of [['Chromium',chromium],['WebKit',webkit]]){
    const browser=await browserType.launch({headless:true});
    try{
      for(const width of [390,820,1440]){
        const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});
        await context.route('https://api.github.com/**',route=>route.fulfill({
          status:200,contentType:'application/json',
          headers:{'access-control-allow-origin':'*'},
          body:JSON.stringify({workflow_runs:[]})
        }));
        const page=await context.newPage(),errors=[];
        page.on('pageerror',error=>errors.push(error.message));
        await page.goto(BASE,{waitUntil:'domcontentloaded'});
        await page.locator('#reader .essay-paragraph .word').first().waitFor({state:'visible',timeout:20000});
        assert.equal(await page.evaluate(()=>document.documentElement.classList.contains('light')),true,
          engine+' first visit must default to Paper Calm');
        // Local words are never erased or sent to the cloud by colour switching.
        await page.evaluate(()=>localStorage.setItem('ai-daily-saved-v2',JSON.stringify({
          auditword:{translation:'審計詞語',savedAt:'2026-10-09T12:00:00.000Z',reviewLevel:0}
        })));
        await page.reload({waitUntil:'domcontentloaded'});
        await page.locator('#reader .essay-paragraph .word').first().waitFor({state:'visible',timeout:20000});
        const label=engine+' '+width+'px';
        await inspect(page,label+' day','day',width);

        await page.locator('#theme-button').click();
        assert.equal(await page.evaluate(()=>localStorage.getItem('ai-daily-light')),'false');
        await page.locator('[data-view="today"]').click();
        await inspect(page,label+' night','night',width);

        // Old explicit dark preference survives reload; no forcing everyone to paper.
        await page.reload({waitUntil:'domcontentloaded'});
        await page.locator('#reader .essay-paragraph .word').first().waitFor({state:'visible',timeout:20000});
        assert.equal(await page.evaluate(()=>document.documentElement.classList.contains('light')),false,
          label+' saved dark preference lost');
        await page.locator('#theme-button').click();
        assert.equal(await page.evaluate(()=>localStorage.getItem('ai-daily-light')),'true');
        await page.locator('[data-view="today"]').click();
        await inspect(page,label+' persisted day','day',width);

        // Reader focus styling and word-hover highlight both use legible colours.
        await page.locator('[data-view="today"]').click();
        const target=page.locator('#reader .essay-paragraph .word').first();
        await target.hover();
        const focused=await computed(page,'#reader .essay-paragraph .word');
        const colorMatch=eqRgb(focused.background,'rgb(229, 239, 232)');
        assert.ok(colorMatch,label+' expected softly highlighted word background');
        minRatio(focused.color,focused.background,4.5,label+' highlighted word');

        if(width===820){
          await page.emulateMedia({media:'print'});
          const printBody=await computed(page,'body'),printReader=await computed(page,'#reader');
          assert.ok(eqRgb(printBody.background,'rgb(255, 255, 255)'),label+' print must be white paper');
          minRatio(printReader.color,printBody.background,7,label+' ink-on-white print');
          await page.emulateMedia({media:'screen'});
        }
        assert.deepEqual(errors,[],label+' JavaScript errors');
        await context.close();
      }
    }finally{await browser.close();}
  }
  console.log('PASS ALL V1 Paper Calm/Soft Graphite computed-colour, PWA, focus, saved state and print tests');
})().catch(error=>{console.error(error);process.exit(1);});

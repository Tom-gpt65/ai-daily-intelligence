/* Browser regression for visible email OTP feedback.
 * All provider replies are mocked; no real email or login token is generated.
 */
'use strict';
const assert=require('node:assert/strict');
const {chromium,webkit}=require('playwright');
const ORIGIN='http://127.0.0.1:8765/';
const API='https://fake-login.supabase.co';
const KEY='sb_publishable_'.padEnd(40,'x');
const cors={
  'access-control-allow-origin':'*',
  'access-control-allow-headers':'apikey,content-type,authorization',
  'access-control-allow-methods':'OPTIONS,POST,GET'
};
async function mock(context){
  await context.route('**/cloud-config.json',route=>route.fulfill({
    status:200,contentType:'application/json',body:JSON.stringify({supabase_url:API,anon_key:KEY})
  }));
  await context.route(API+'/**',async route=>{
    const request=route.request(),url=new URL(request.url());
    if(request.method()==='OPTIONS')return route.fulfill({status:204,headers:cors});
    assert.equal(url.pathname,'/auth/v1/otp');
    assert.equal(request.method(),'POST');
    const data=JSON.parse(request.postData());
    assert.equal(data.create_user,true);
    assert.ok(url.searchParams.get('redirect_to').endsWith('/'));
    if(data.email==='member@example.com'){
      await new Promise(resolve=>setTimeout(resolve,600));
      return route.fulfill({status:200,headers:cors,contentType:'application/json',body:'{}'});
    }
    if(data.email==='blocked@example.com'){
      return route.fulfill({status:422,headers:cors,contentType:'application/json',
        body:JSON.stringify({error_code:'email_address_not_authorized',msg:'Email address not authorized'})});
    }
    if(data.email==='rate@example.com'){
      return route.fulfill({status:429,headers:cors,contentType:'application/json',
        body:JSON.stringify({msg:'Too many requests'})});
    }
    throw new Error('Unexpected email');
  });
}
async function waitFeedback(page,phrase){
  await page.waitForFunction(text=>{
    const el=document.querySelector('#sync-email-feedback');
    return el&&!el.classList.contains('hidden')&&el.textContent.includes(text);
  },phrase,{timeout:10000});
}
(async()=>{
  for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]){
    const browser=await engine.launch({headless:true});
    const context=await browser.newContext({serviceWorkers:'block'});
    try{
      await mock(context);
      const page=await context.newPage(),errors=[];
      page.on('pageerror',e=>errors.push(e.message));
      await page.goto(ORIGIN,{waitUntil:'domcontentloaded'});
      await page.locator('[data-view="words"]').click();
      await page.locator('#sync-login').waitFor({state:'visible',timeout:15000});

      await page.locator('#sync-email').fill('member@example.com');
      await page.locator('#sync-email-submit').click();
      await waitFeedback(page,'正在寄送登入請求');
      assert.equal(await page.locator('#sync-email-submit').isDisabled(),true);
      await waitFeedback(page,'登入請求已被接受');
      assert.equal(await page.locator('#sync-email-submit').isEnabled(),true);
      assert.match(await page.locator('#sync-status').innerText(),/Supabase 接受/);

      await page.locator('#sync-email').fill('blocked@example.com');
      await page.locator('#sync-email-submit').click();
      await waitFeedback(page,'組織團隊');
      assert.match(await page.locator('#sync-status').innerText(),/未能寄送/);

      await page.locator('#sync-email').fill('rate@example.com');
      await page.locator('#sync-email-submit').click();
      await waitFeedback(page,'次數限制');

      await page.locator('#sync-email').fill('invalid');
      await page.locator('#sync-email-submit').click();
      await waitFeedback(page,'有效的電郵地址');
      assert.deepEqual(errors,[],name+' browser console errors');
      console.log('PASS '+name+' magic-link success, visible progress, restricted email, rate limit and invalid address');
    }finally{await context.close();await browser.close();}
  }
})().catch(error=>{console.error(error);process.exit(1);});

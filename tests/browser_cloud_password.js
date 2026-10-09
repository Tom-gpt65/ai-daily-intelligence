/* Test an actual browser password-login journey against a mocked Supabase Auth API.
 * No Supabase secrets, real accounts, email requests or SMTP are involved.
 */
'use strict';
const assert=require('node:assert/strict');
const {chromium,webkit}=require('playwright');
const ORIGIN='http://127.0.0.1:8765/';
const API='https://mock-password-auth.supabase.co';
const KEY='sb_publishable_'.padEnd(40,'x');
const PASSWORD='local-browser-mock-password';
const USERS={
  'one@example.com':{id:'11111111-1111-4111-a111-111111111111',email:'one@example.com'},
  'two@example.com':{id:'22222222-2222-4222-a222-222222222222',email:'two@example.com'}
};
const events=[];
let sequence=0,otpAttempts=0;
const cors={
  'access-control-allow-origin':'*',
  'access-control-allow-headers':'apikey,authorization,content-type,prefer',
  'access-control-allow-methods':'POST,GET,OPTIONS'
};
function deliver(route,body,status=200){
  return route.fulfill({status,headers:cors,contentType:'application/json',body:JSON.stringify(body)});
}
async function attach(context){
  await context.route('**/cloud-config.json',route=>deliver(route,{supabase_url:API,anon_key:KEY}));
  await context.route(API+'/**',async route=>{
    const request=route.request(),url=new URL(request.url());
    if(request.method()==='OPTIONS')return route.fulfill({status:204,headers:cors});
    if(url.pathname==='/auth/v1/otp'){
      otpAttempts++;
      return deliver(route,{message:'Email OTP should not be used for password sign-in'},500);
    }
    if(url.pathname==='/auth/v1/token'&&url.searchParams.get('grant_type')==='password'){
      const {email,password}=JSON.parse(request.postData());
      assert.equal(request.headers().apikey,KEY);
      if(email==='wrong@example.com')return deliver(route,{message:'Invalid login credentials'},400);
      if(email==='unconfirmed@example.com')return deliver(route,{message:'Email not confirmed'},400);
      if(email==='throttled@example.com')return deliver(route,{message:'Too many requests'},429);
      if(!USERS[email]||password!==PASSWORD)return deliver(route,{message:'Invalid login credentials'},400);
      const token=email==='one@example.com'?'password-one':'password-two';
      return deliver(route,{access_token:token,refresh_token:'refresh-'+token,expires_in:3600,token_type:'bearer'});
    }
    const token=(request.headers().authorization||'').replace(/^Bearer /,'');
    const owner=token==='password-one'?USERS['one@example.com']:
      token==='password-two'?USERS['two@example.com']:null;
    if(!owner)return deliver(route,{message:'Invalid token'},401);
    if(url.pathname==='/auth/v1/user')return deliver(route,owner);
    if(url.pathname==='/rest/v1/vocabulary_events'&&request.method()==='POST'){
      const stamp=new Date(Date.parse('2026-10-09T01:00:00Z')+(++sequence)*1000).toISOString();
      for(const entry of JSON.parse(request.postData())){
        if(entry.user_id!==owner.id)return deliver(route,{message:'RLS denied'},403);
        if(!events.some(row=>row.event_id===entry.event_id))events.push({...entry,created_at:stamp});
      }
      return route.fulfill({status:204,headers:cors});
    }
    if(url.pathname==='/rest/v1/vocabulary_events'&&request.method()==='GET'){
      const offset=Number(url.searchParams.get('offset')||0);
      const page=events.filter(e=>e.user_id===owner.id)
        .slice(offset,offset+1000).map(({event_id,word,payload,deleted,created_at,batch_order})=>
          ({event_id,word,payload,deleted,created_at,batch_order}));
      return deliver(route,page);
    }
    if(url.pathname==='/auth/v1/logout')return deliver(route,{});
    return deliver(route,{message:'unexpected path'},404);
  });
}
async function open(context){
  const page=await context.newPage();
  await page.goto(ORIGIN,{waitUntil:'domcontentloaded'});
  await page.locator('[data-view="words"]').click();
  await page.locator('#sync-password-panel').waitFor({state:'visible',timeout:15000});
  return page;
}
async function signIn(page,email,password){
  await page.locator('#sync-password-email').fill(email);
  await page.locator('#sync-password').fill(password);
  await page.locator('#sync-password-submit').click();
}
async function awaitCount(page,n){
  await page.waitForFunction(target=>document.querySelector('#saved-count')?.textContent.trim()===String(target),n,{timeout:15000});
}
(async()=>{
  for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]){
    events.length=0;sequence=0;otpAttempts=0;
    const browser=await engine.launch({headless:true});
    try{
      const aContext=await browser.newContext({serviceWorkers:'block'});
      const bContext=await browser.newContext({serviceWorkers:'block'});
      const cContext=await browser.newContext({serviceWorkers:'block'});
      for(const ctx of [aContext,bContext,cContext])await attach(ctx);
      const a=await open(aContext),b=await open(bContext),c=await open(cContext);
      const errors=[];
      for(const page of [a,b,c])page.on('pageerror',e=>errors.push(e.message));
      await signIn(a,'wrong@example.com',PASSWORD);
      await a.locator('#sync-password-feedback').getByText(/密碼登入失敗/).waitFor({timeout:10000});
      assert.match(await a.locator('#sync-password-feedback').innerText(),/密碼不正確|帳戶尚未建立/);
      assert.ok(await a.locator('#sync-password-login').isVisible());
      await signIn(a,'unconfirmed@example.com',PASSWORD);
      await a.waitForFunction(()=>document.querySelector('#sync-password-feedback')?.textContent.includes('尚未確認'),null,{timeout:10000});
      await signIn(a,'throttled@example.com',PASSWORD);
      await a.waitForFunction(()=>document.querySelector('#sync-password-feedback')?.textContent.includes('過於頻繁'),null,{timeout:10000});

      // Create a local-only word and ensure explicit migration is still required.
      await a.locator('[data-view="today"]').click();
      await a.locator('#reader .essay-paragraph').first().waitFor({state:'visible',timeout:15000});
      await a.locator('#reader .word').filter({hasText:/^evidence$/i}).first().click();
      await a.locator('#save-word').click();
      await a.locator('#pop-close').click();
      await a.locator('[data-view="words"]').click();
      await awaitCount(a,1);

      await signIn(a,'one@example.com',PASSWORD);
      await a.locator('#sync-account').waitFor({state:'visible',timeout:15000});
      await awaitCount(a,0);
      assert.ok(await a.locator('#sync-import-local').isVisible());
      assert.equal(await a.locator('#sync-password').inputValue(),'');
      assert.ok(await a.locator('#sync-password-login').isHidden());
      await a.locator('#sync-import-local').click();
      await awaitCount(a,1);
      await a.waitForFunction(()=>document.querySelector('#sync-status')?.textContent.includes('同步完成'),null,{timeout:15000});
      assert.equal(events.filter(e=>e.user_id===USERS['one@example.com'].id&&!e.deleted).length,1);

      await signIn(b,'one@example.com',PASSWORD);
      await b.locator('#sync-account').waitFor({state:'visible',timeout:15000});
      await awaitCount(b,1);
      await b.locator('#word-list .word-card').filter({hasText:'evidence'}).getByRole('button',{name:'移除'}).click();
      await awaitCount(b,0);
      await b.waitForFunction(()=>document.querySelector('#sync-status')?.textContent.includes('同步完成'),null,{timeout:15000});
      await a.locator('#sync-now').click();
      await awaitCount(a,0);

      await signIn(c,'two@example.com',PASSWORD);
      await c.locator('#sync-account').waitFor({state:'visible',timeout:15000});
      await awaitCount(c,0);
      const contents=await a.evaluate(()=>Object.values(localStorage).join(' '));
      assert.ok(!contents.includes(PASSWORD),'Password must never be persisted to localStorage');
      assert.equal(otpAttempts,0,'Password login must not invoke the rate-limited email endpoint');
      assert.deepEqual(errors,[],name+' unexpected browser errors');
      console.log('PASS',name,'no-mail login, password errors, explicit backup migration, cross-device sync, deletion and account isolation');
    }finally{await browser.close();}
  }
})().catch(error=>{console.error(error);process.exit(1);});

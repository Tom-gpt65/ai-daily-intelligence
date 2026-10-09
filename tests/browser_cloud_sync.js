/* Browser simulation of two independent devices using a mocked Supabase API.
 * No cloud project, API key or test account is needed to run the regression.
 */
'use strict';
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const ORIGIN='http://127.0.0.1:8765/';
const API='https://mock-project.supabase.co';
const PUB='sb_publishable_'.padEnd(40,'x');
const USERS={
  'user-one':{id:'11111111-1111-4111-a111-111111111111',email:'one@example.com'},
  'user-two':{id:'22222222-2222-4222-a222-222222222222',email:'two@example.com'}
};
const events=[];
let seq=0;
function response(route,body,status=200){
  return route.fulfill({status,contentType:'application/json',
    headers:{'access-control-allow-origin':'*',
      'access-control-allow-headers':'authorization,apikey,content-type,prefer',
      'access-control-allow-methods':'GET,POST,OPTIONS'},
    body:body===undefined?'':JSON.stringify(body)});
}
async function attach(ctx){
  await ctx.route('**/cloud-config.json',r=>response(r,{
    supabase_url:API,anon_key:PUB
  }));
  await ctx.route(API+'/**',async route=>{
    const req=route.request(),url=new URL(req.url());
    if(req.method()==='OPTIONS')return route.fulfill({status:204,headers:{
      'access-control-allow-origin':'*',
      'access-control-allow-headers':'authorization,apikey,content-type,prefer',
      'access-control-allow-methods':'GET,POST,OPTIONS'
    }});
    const token=(req.headers().authorization||'').replace(/^Bearer /,'');
    const user=USERS[token];
    if(!user)return response(route,{message:'invalid login'},401);
    if(url.pathname==='/auth/v1/user')return response(route,user);
    if(url.pathname==='/rest/v1/vocabulary_events'&&req.method()==='POST'){
      for(const entry of JSON.parse(req.postData())){
        if(entry.user_id!==user.id)return response(route,{message:'RLS denied'},403);
        if(!events.some(x=>x.event_id===entry.event_id)){
          events.push({...entry,created_at:new Date(Date.parse('2026-10-09T00:00:00Z')+(++seq)*1000).toISOString()});
        }
      }
      return route.fulfill({status:204,headers:{'access-control-allow-origin':'*'}});
    }
    if(url.pathname==='/rest/v1/vocabulary_events'&&req.method()==='GET'){
      const offset=Number(url.searchParams.get('offset')||0);
      return response(route,events.filter(e=>e.user_id===user.id)
        .slice(offset,offset+1000).map(({event_id,word,payload,deleted,created_at})=>
          ({event_id,word,payload,deleted,created_at})));
    }
    if(url.pathname==='/auth/v1/logout')return response(route,{});
    return response(route,{message:'unknown route'},404);
  });
}
async function login(page,token){
  await page.goto(ORIGIN+'?auth=mock-'+token+'#access_token='+token+'&refresh_token=refresh&expires_in=3600',{
    waitUntil:'domcontentloaded'});
  try{await page.locator('#sync-account').waitFor({state:'visible',timeout:15000});}
  catch(error){
    const diagnostic=await page.evaluate(()=>({
      currentUrl:location.pathname+location.search,
      syncStatus:document.querySelector('#sync-status')?.textContent,
      unavailable:!document.querySelector('#sync-unavailable')?.classList.contains('hidden'),
      loginVisible:!document.querySelector('#sync-login')?.classList.contains('hidden'),
      moduleReady:Boolean(window.AIDailyCloud),
      sessionPresent:Boolean(localStorage.getItem('ai-daily-cloud-session-v1'))
    }));
    throw new Error('Fake Supabase login not active: '+JSON.stringify(diagnostic),{cause:error});
  }
  await page.locator('#sync-now').click();
  await page.waitForFunction(()=>document.querySelector('#sync-status')?.textContent.includes('同步完成'),null,{timeout:15000});
}
async function count(page,n){
  await page.waitForFunction(target=>document.querySelector('#saved-count')?.textContent.trim()===String(target),n,{timeout:15000});
}
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
   const first=await browser.newContext({serviceWorkers:'block'});
   const second=await browser.newContext({serviceWorkers:'block'});
   const third=await browser.newContext({serviceWorkers:'block'});
   await Promise.all([attach(first),attach(second),attach(third)]);
   const a=await first.newPage(),b=await second.newPage(),c=await third.newPage();
   const errs=[];
   for(const page of [a,b,c])page.on('pageerror',error=>errs.push(error.message));
   await a.goto(ORIGIN);
   await a.locator('#reader .essay-paragraph').first().waitFor({state:'visible',timeout:15000});
   await a.locator('#reader .word').filter({hasText:/^evidence$/i}).first().click();
   await a.locator('#save-word').click();
   await a.locator('#pop-close').click();
   await count(a,1);
   await login(a,'user-one');
   await count(a,0);
   assert.ok(await a.locator('#sync-import-local').isVisible(),
      'Original device vocabulary must ask for explicit import');
   await a.locator('#sync-import-local').click();
   await count(a,1);
   await a.waitForFunction(()=>document.querySelector('#sync-status')?.textContent.includes('同步完成 · 1 個'),null,{timeout:15000});
   assert.ok(events.some(e=>e.word==='evidence'&&!e.deleted),'Migration must upload original word');
   await login(b,'user-one');
   await count(b,1);
   await b.locator('[data-view="words"]').click();
   await b.locator('#word-list .word-card').filter({hasText:'evidence'})
     .getByRole('button',{name:'移除'}).click();
   await count(b,0);
   await b.waitForFunction(()=>document.querySelector('#sync-status')?.textContent.includes('同步完成 · 0 個'),null,{timeout:15000});
   await a.locator('[data-view="words"]').click();
   await a.locator('#sync-now').click();
   await count(a,0);
   await login(c,'user-two');
   await count(c,0);
   assert.ok(!events.some(e=>e.user_id===USERS['user-two'].id),'Other account must remain isolated');
   assert.deepEqual(errs,[],'Browser page errors');
   console.log('Cloud V1 browser integration PASS: explicit migration, two-device pull, deletion and account isolation');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});

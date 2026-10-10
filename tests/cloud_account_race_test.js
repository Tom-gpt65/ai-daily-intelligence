'use strict';
const assert=require('node:assert/strict');
const {Client}=require('../site/cloud-sync.js');
const values=new Map();
global.localStorage={getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,String(v)),removeItem:k=>values.delete(k)};
Object.defineProperty(globalThis,'navigator',{value:{onLine:true},configurable:true});
Object.defineProperty(globalThis,'crypto',{value:require('node:crypto').webcrypto,configurable:true});
const a='11111111-1111-4111-a111-111111111111',b='22222222-2222-4222-a222-222222222222';
const token=id=>({access_token:'access-'+id,refresh_token:'refresh-'+id,expires_at:Date.now()+3600000});
const pending=id=>'ai-daily-cloud-pending-v1-'+id;
(async()=>{
  let releaseUpload,rendered=[];
  const client=new Client({onWords:words=>rendered.push(words)});
  client.config={url:'https://example.supabase.co',key:'sb_publishable_test'};
  client.user={id:a};client.session=token(a);
  global.fetch=async url=>{
    if(String(url).includes('logout'))return new Response(null,{status:204});
    if(String(url).includes('on_conflict'))return new Promise(resolve=>{releaseUpload=resolve;});
    throw Error('Old account must not read/render after identity changes');
  };
  client.record('evidence',{translation:'證據'},false);clearTimeout(client.retryTimer);
  const first=client.sync();
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(releaseUpload);
  await client.logout();
  client.epoch++;client.user={id:b};client.session=token(b);client.pending=client.getPending();
  client.record('research',{translation:'研究'},false);clearTimeout(client.retryTimer);
  const bQueue=localStorage.getItem(pending(b));
  releaseUpload(new Response(null,{status:204}));await first;
  assert.equal(rendered.length,0,'Old account rendered into new account');
  assert.equal(JSON.parse(localStorage.getItem(pending(a))).length,1,'Unacknowledged A queue lost');
  assert.equal(localStorage.getItem(pending(b)),bQueue,'A completion changed B queue');
  global.fetch=async (url,options)=>{
    assert.equal(options.headers.Authorization,'Bearer access-'+b);
    if(String(url).includes('on_conflict')){
      assert.ok(JSON.parse(options.body).every(e=>e.user_id===b));
      return new Response(null,{status:204});
    }
    return new Response('[]');
  };
  await client.sync();assert.equal(client.pending.length,0);
  assert.equal(rendered.length,1);
  // Parallel refreshes share one provider request; a late refresh may never
  // resurrect credentials after local logout.
  let releaseRefresh,count=0;
  client.session={...token(b),expires_at:0};
  global.fetch=async url=>{
    if(String(url).includes('logout'))return new Response(null,{status:204});
    count++;return new Promise(resolve=>{releaseRefresh=resolve;});
  };
  const refresh1=client.refresh(),refresh2=client.refresh();
  await new Promise(resolve=>setImmediate(resolve));assert.equal(count,1);
  await client.logout();
  releaseRefresh(new Response(JSON.stringify({access_token:'late-access',refresh_token:'late-refresh'})));
  const results=await Promise.allSettled([refresh1,refresh2]);
  assert.ok(results.every(r=>r.status==='rejected'));
  assert.equal(client.session,null);assert.equal(client.user,null);
  assert.ok(![...values.values()].some(v=>v.includes('late-access')));
  console.log('ACCOUNT RACE PASS: late upload/logout, account queues, shared refresh and no credential resurrection');
})().catch(error=>{console.error(error);process.exitCode=1;});

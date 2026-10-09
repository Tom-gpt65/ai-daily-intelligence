'use strict';
const assert=require('node:assert/strict');
const {Client}=require('../site/cloud-sync.js');
global.localStorage=(()=>{
  const values=new Map();
  return {getItem:key=>values.has(key)?values.get(key):null,
    setItem:(key,value)=>values.set(key,String(value)),
    removeItem:key=>values.delete(key)};
})();
Object.defineProperty(globalThis,'navigator',{value:{onLine:true},configurable:true});
Object.defineProperty(globalThis,'crypto',{value:require('node:crypto').webcrypto,configurable:true});
const user='11111111-1111-4111-a111-111111111111';
let events=[],uploaded=0,rendered={},state='';
const next=()=>new Date(Date.parse('2026-10-09T00:00:00Z')+(++uploaded)*1000).toISOString();
global.fetch=async (url,options={})=>{
  const path=String(url);
  if(path.includes('/rest/v1/vocabulary_events?on_conflict=event_id')){
    assert.equal(options.headers.Prefer,'resolution=ignore-duplicates,return=minimal');
    assert.equal(options.headers.Authorization,'Bearer example-access-token');
    // Supabase's default now() is constant within one INSERT transaction.
    const serverTime=next();
    for(const event of JSON.parse(options.body)){
      assert.equal(event.user_id,user,'Must write only the authenticated owner');
      assert.ok(Number.isInteger(event.batch_order)&&event.batch_order>=0&&event.batch_order<100);
      if(!events.some(row=>row.event_id===event.event_id))events.push({...event,created_at:serverTime});
    }
    return {ok:true,status:201,text:async()=>''};
  }
  if(path.includes('/rest/v1/vocabulary_events?select=')){
    const offset=Number(path.match(/offset=(\d+)/)?.[1]||0);
    const page=events.slice(offset,offset+1000).map(({event_id,word,payload,deleted,created_at,batch_order})=>({event_id,word,payload,deleted,created_at,batch_order}));
    return {ok:true,status:200,text:async()=>JSON.stringify(page)};
  }
  throw new Error('Unexpected request '+path);
};
const client=new Client({
  onStatus:value=>state=value,
  onWords:words=>{rendered=words;}
});
client.config={url:'https://example.supabase.co',key:'sb_publishable_'.padEnd(30,'x')};
client.user={id:user,email:'user@example.com'};
client.session={access_token:'example-access-token',refresh_token:'refresh-token',expires_at:Date.now()+3600000};
(async()=>{
  client.record('concerns',{translation:'關乎',savedAt:new Date().toISOString(),reviewLevel:0});
  clearTimeout(client.retryTimer);
  assert.equal(client.getPending().length,1);
  await client.sync();
  assert.equal(client.getPending().length,0,'Acknowledged events must leave the pending queue');
  assert.equal(rendered.concerns.translation,'關乎');
  assert.equal(events.length,1);
  client.record('concerns',{...rendered.concerns,reviewLevel:2,nextReview:'2026-10-21'});
  clearTimeout(client.retryTimer);
  navigator.onLine=false;
  await client.sync();
  assert.equal(client.getPending().length,1,'Offline review must survive and wait');
  navigator.onLine=true;
  await client.sync();
  assert.equal(rendered.concerns.reviewLevel,2,'Offline review resumes when online');
  client.record('concerns',{},true);
  clearTimeout(client.retryTimer);
  await client.sync();
  assert.equal(rendered.concerns,undefined,'Deletion must propagate by tombstone');
  const count=events.length;
  await client.sync();
  assert.equal(events.length,count,'Repeated sync must not duplicate acknowledged events');
  // Two edits queued before a single server POST share created_at.
  client.record('concerns',{translation:'關乎',reviewLevel:1});
  client.record('concerns',{translation:'關乎',reviewLevel:6});
  clearTimeout(client.retryTimer);
  await client.sync();
  assert.equal(rendered.concerns.reviewLevel,6,'Later edit in one batch must win');
  const finalBatch=events.slice(-2);
  assert.equal(finalBatch[0].created_at,finalBatch[1].created_at);
  assert.deepEqual(finalBatch.map(e=>e.batch_order),[0,1]);
  assert.match(state,/同步完成/);
  console.log('Cloud mocked E2E PASS: create, offline review, reconnect, delete, idempotent sync and tied timestamp ordering');
})().catch(err=>{console.error(err);process.exit(1);});

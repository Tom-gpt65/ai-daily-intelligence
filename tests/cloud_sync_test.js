'use strict';
const assert=require('node:assert/strict');
const {Client,cleanWord,cleanPayload,replay,combineWithPending}=require('../site/cloud-sync.js');
const settingsCheck=new Client({});
assert.equal(settingsCheck.configValid({
  supabase_url:'https://example.supabase.co',
  anon_key:'sb_secret_'.padEnd(40,'x')}),false,'Privileged keys must be rejected');
assert.equal(settingsCheck.configValid({
  supabase_url:'https://example.supabase.co',
  anon_key:'sb_publishable_'.padEnd(35,'x')}),true);
assert.equal(cleanWord('concerns'),'concerns');
for(const word of ['','a'.repeat(47),'../../../x','A','__proto__'])
  assert.equal(cleanWord(word),null,'Reject invalid word '+word);
const original={translation:'關乎',phonetic:'',savedAt:'2026-10-09T00:00:00Z',reviewLevel:0};
const reviewed={...original,reviewLevel:3,nextReview:'2026-10-21'};
const e1={event_id:'1',word:'concerns',payload:original,deleted:false,created_at:'2026-10-09T00:00:00Z'};
const e2={event_id:'2',word:'concerns',payload:reviewed,deleted:false,created_at:'2026-10-09T00:01:00Z'};
const e3={event_id:'3',word:'concerns',payload:{},deleted:true,created_at:'2026-10-09T00:02:00Z'};
assert.equal(replay([e2,e1]).concerns.reviewLevel,3,'Later reviews win');
const tiedTime='2026-10-09T01:00:00Z';
const earlierInBatch={...e1,event_id:'z',created_at:tiedTime,batch_order:0};
const laterInBatch={...e2,event_id:'a',created_at:tiedTime,batch_order:1};
assert.equal(replay([laterInBatch,earlierInBatch]).concerns.reviewLevel,3,
  'Batch order must win when server timestamps tie, not random UUID lexical order');
assert.equal(replay([e3,e2,e1]).concerns,undefined,'Deletion tombstone remains deleted');
assert.equal(replay([e1,e2,e3,e3]).concerns,undefined,'Idempotent replay');
assert.equal(Object.keys(replay([e1,e2,e3])).length,0);
assert.equal(combineWithPending([e1,e2,e3],[{...e2,event_id:'4'}]).concerns.reviewLevel,3,
  'Queued offline reinstatement must not be lost before upload');
assert.equal(combineWithPending([e1,e2],[{...e3,event_id:'4'}]).concerns,undefined,
  'Queued offline deletion must not be resurrected');
assert.deepEqual(cleanPayload({...original,extra:'do not leak'}),{
  translation:'關乎',phonetic:'',savedAt:'2026-10-09T00:00:00Z',
  reviewLevel:0,nextReview:'',lastReviewed:''
});
console.log('Cloud vocabulary conflict, same-timestamp batch order, tombstone, offline replay and data validation PASS');

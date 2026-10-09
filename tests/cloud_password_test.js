/* No-browser password sign-in regression: must work without any mail service. */
'use strict';
const assert=require('node:assert/strict');
const {Client}=require('../site/cloud-sync.js');
const saved=new Map();
global.localStorage={
  getItem:key=>saved.has(key)?saved.get(key):null,
  setItem:(key,v)=>saved.set(key,String(v)),
  removeItem:key=>saved.delete(key)
};
Object.defineProperty(global,'navigator',{configurable:true,value:{onLine:true}});
const project='https://mock.supabase.co';
const email='owner@example.com',password='testing-password-is-not-a-secret';
const uid='11111111-1111-4111-a111-111111111111';
let mailRequests=0,authenticatedUser=null,gotWords=null;
global.fetch=async (url,opts={})=>{
  const path=String(url);
  if(path.includes('/auth/v1/otp')){mailRequests++;throw Error('Email endpoint must not be used');}
  if(path.includes('/auth/v1/token?grant_type=password')){
    const payload=JSON.parse(opts.body);
    assert.equal(payload.email,email);assert.equal(payload.password,password);
    assert.equal(opts.headers.apikey,'sb_publishable_dummykey');
    return {ok:true,status:200,json:async()=>({
      access_token:'realistic-access-token',refresh_token:'refresh-token',expires_in:3600
    })};
  }
  if(path.includes('/auth/v1/user')){
    assert.equal(opts.headers.Authorization,'Bearer realistic-access-token');
    return {ok:true,status:200,json:async()=>({id:uid,email})};
  }
  if(path.includes('/rest/v1/vocabulary_events?select=')){
    return {ok:true,status:200,text:async()=>JSON.stringify([])};
  }
  throw Error('Unexpected API '+path);
};
(async()=>{
  const c=new Client({
    onSignedIn:user=>{authenticatedUser=user;},
    onWords:words=>{gotWords=words;},
    onStatus:()=>{}
  });
  c.config={url:project,key:'sb_publishable_dummykey'};
  const result=await c.signInWithPassword(email,password);
  assert.equal(result.id,uid);
  assert.equal(authenticatedUser.id,uid);
  assert.deepEqual(Object.keys(gotWords),[]);
  assert.ok(c.active);
  assert.equal(mailRequests,0,'No magic-link email requests');
  assert.ok(saved.get('ai-daily-cloud-session-v1').includes('realistic-access-token'));
  assert.ok(![...saved.values()].join(' ').includes(password),'Never cache login password');
  await assert.rejects(()=>c.signInWithPassword('broken',password),/有效的電郵/);
  await assert.rejects(()=>c.signInWithPassword(email,'short'),/至少 8/);
  assert.equal(c.user.id,uid,'Invalid attempts must not clear a valid session');
  console.log('MAIL-FREE PASSWORD AUTH PASS: tokens verified, private identity retained, no OTP/email, no password persisted');
})().catch(error=>{console.error(error);process.exitCode=1;});

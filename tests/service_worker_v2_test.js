/* Deterministic SW contract using the actual worker: canonical public-data keys,
 * legacy migration, protected index, HTTP failures and private endpoint bypass. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const BASE='https://tom-gpt65.github.io/ai-daily-intelligence/';
const cachesMap=new Map(),handlers=new Map();
const normal=value=>new URL(typeof value==='string'?value:value.url,BASE).href;
class MemoryCache{
  constructor(){this.entries=new Map();}
  async put(key,response){this.entries.set(normal(key),response.clone());}
  async match(key){return this.entries.get(normal(key))?.clone();}
  async keys(){return [...this.entries.keys()].map(url=>new Request(url));}
  async delete(key){return this.entries.delete(normal(key));}
  async addAll(paths){for(const path of paths)await this.put(path,new Response('shell'));}
}
const cacheAPI={
  async open(name){if(!cachesMap.has(name))cachesMap.set(name,new MemoryCache());return cachesMap.get(name);},
  async keys(){return [...cachesMap.keys()];},async delete(name){return cachesMap.delete(name);},
  async match(key){for(const cache of cachesMap.values()){const res=await cache.match(key);if(res)return res;}}
};
let failure=false,lastNetworkOptions;
const newest='2026-10-10';
const sandbox={URL,Request,Response,Set,Promise,caches:cacheAPI,
  self:{location:new URL(BASE+'sw.js'),clients:{async claim(){}},async skipWaiting(){},
        addEventListener(type,handler){handlers.set(type,handler);}},
  async fetch(key,options){
    lastNetworkOptions=options;
    if(failure)return new Response('unavailable',{status:503});
    const path=new URL(normal(key)).pathname;
    const body=path.endsWith('/index.json')?[{date:newest}]:{revision:'V3-fresh'};
    return new Response(JSON.stringify(body),{headers:{'Content-Type':'application/json'}});
  }
};
vm.runInNewContext(fs.readFileSync(require('node:path').join(__dirname,'../site/sw.js'),'utf8'),sandbox);
async function emit(type,request){
  let work;
  handlers.get(type)({request,waitUntil(value){work=value;},respondWith(value){work=value;}});
  return work?await work:undefined;
}
(async()=>{
  const old=await cacheAPI.open('ai-daily-V1-paper-calm-reading-reports');
  await old.put('./reports/'+newest+'.json?rev=old',new Response('old revision'));
  for(let i=1;i<=44;i++){
    const day=new Date(Date.UTC(2026,7,i)).toISOString().slice(0,10);
    await old.put('./reports/'+day+'.json?rev=1',new Response('historic '+day));
  }
  await old.put('./system-status.json?check=1',new Response('{"state":"feed_error"}'));
  const v2=await cacheAPI.open('ai-daily-V2-stable-reading-reports');
  await v2.put('./reports/2026-09-15.json?rev=old',
    new Response('{"fromV2":true}'));
  await old.put('https://private.supabase.co/rest/v1/vocabulary_events',new Response('NEVER_COPY'));
  await cacheAPI.open('unrelated-application');
  await emit('install');
  await emit('activate');
  const data=await cacheAPI.open('ai-daily-V3-novel-reading-reports');
  const keys=await data.keys();
  assert.equal(keys.filter(key=>/\/reports\/\d{4}-/.test(key.url)).length,42);
  assert.ok(await data.match('./reports/index.json'),'Index was pruned');
  assert.equal(await (await data.match('./reports/'+newest+'.json')).text(),'{"revision":"V3-fresh"}');
  assert.ok(keys.every(key=>key.url.startsWith(BASE)&&!new URL(key.url).search));
  assert.ok(cachesMap.has('unrelated-application'));
  assert.ok(!cachesMap.has('ai-daily-V1-paper-calm-reading-reports'));
  assert.ok(!cachesMap.has('ai-daily-V2-stable-reading-reports'));
  const historic=await data.match('./reports/2026-09-15.json');
  assert.equal(await historic?.text(),'{"fromV2":true}');
  for(let i=0;i<100;i++)await emit('fetch',new Request(BASE+'reports/'+newest+'.json?rev='+i));
  assert.equal((await data.keys()).filter(key=>key.url.includes(newest+'.json')).length,1);
  assert.ok(await data.match('./reports/index.json'));
  assert.equal(lastNetworkOptions.cache,'no-store');
  failure=true;
  const fallback=await emit('fetch',new Request(BASE+'reports/'+newest+'.json?rev=offline'));
  assert.equal(await fallback.text(),'{"revision":"V3-fresh"}');
  assert.equal(await emit('fetch',new Request('https://private.supabase.co/rest/v1/vocabulary_events')),undefined);
  assert.equal(await emit('fetch',new Request(BASE+'cloud-config.json')),undefined);
  assert.equal(await emit('fetch',new Request(BASE+'../another-project/app.js')),undefined);
  console.log('V3 WORKER PASS: V1 migration, 42 dated reports, protected index/status, 100 canonical refreshes, HTTP 503 fallback, private/sibling origin bypass');
})().catch(error=>{console.error(error);process.exitCode=1;});

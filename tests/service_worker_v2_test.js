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
let failure=false,malformed=false,unrepaired=false,lastNetworkOptions;
const newest='2026-10-10';
const report=(date,extra={})=>({date,essay:Array(5).fill('Cached public passage'),dictionary:{},practice:{items:Array(7).fill({})},...extra});
const json=value=>new Response(JSON.stringify(value),{headers:{'Content-Type':'application/json'}});
const sandbox={
  AbortController,Headers,setTimeout,clearTimeout,URL,Request,Response,Set,Promise,caches:cacheAPI,
  self:{location:new URL(BASE+'sw.js'),clients:{async claim(){}},async skipWaiting(){},
        addEventListener(type,handler){handlers.set(type,handler);}},
  async fetch(key,options){
    lastNetworkOptions=options;
    if(failure)return new Response('unavailable',{status:503});
    if(malformed)return new Response('<html>Temporary error</html>',{headers:{'Content-Type':'text/html'}});
    const path=new URL(normal(key)).pathname;
    const date=path.match(/\/reports\/(\d{4}-\d{2}-\d{2})\.json$/)?.[1]||newest;
    const repaired=unrepaired?{}:{content_generation_profile:'source_outline_v2',practice_revision:'a'.repeat(64)};
    const body=path.endsWith('/index.json')?[{date:newest}]:report(date,{revision:'S1-fresh',...repaired});
    return json(body);
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
  await old.put('./reports/'+newest+'.json?rev=old',json(report(newest,{revision:'old'})));
  await old.put('./reports/2026-10-09.json?rev=bad',json(report('2026-10-09',{revision:'old-repetitive'})));
  for(let i=1;i<=44;i++){
    const day=new Date(Date.UTC(2026,7,i)).toISOString().slice(0,10);
    await old.put('./reports/'+day+'.json?rev=1',json(report(day)));
  }
  await old.put('./system-status.json?check=1',new Response('{"state":"feed_error"}'));
  const v2=await cacheAPI.open('ai-daily-V2-stable-reading-reports');
  await v2.put('./reports/2026-09-15.json?rev=old',
    json(report('2026-09-15',{fromV2:true})));
  await old.put('https://private.supabase.co/rest/v1/vocabulary_events',new Response('NEVER_COPY'));
  const previousS1=await cacheAPI.open('ai-daily-S1-1-reading-reports');
  await previousS1.put('./reports/2026-09-20.json?rev=phase1',json(report('2026-09-20',{fromS1:true})));
  await cacheAPI.open('unrelated-application');
  await emit('install');
  await emit('activate');
  const data=await cacheAPI.open('ai-daily-S1-3-reading-reports');
  const keys=await data.keys();
  assert.equal(keys.filter(key=>/\/reports\/\d{4}-/.test(key.url)).length,42);
  assert.ok(await data.match('./reports/index.json'),'Index was pruned');
  assert.equal((await (await data.match('./reports/'+newest+'.json')).json()).revision,'S1-fresh');
  assert.equal((await (await data.match('./reports/2026-10-09.json')).json()).content_generation_profile,'source_outline_v2','Old Oct9 prose survived migration');
  assert.ok(keys.every(key=>key.url.startsWith(BASE)&&!new URL(key.url).search));
  assert.ok(cachesMap.has('unrelated-application'));
  assert.ok(!(await old.keys()).some(key=>key.url.startsWith(BASE)), 'Legacy in-scope data remained after migration');
  assert.ok(await old.match('https://private.supabase.co/rest/v1/vocabulary_events'),'Unrelated origin cache was removed');
  assert.ok(!cachesMap.has('ai-daily-V2-stable-reading-reports'));
  const historic=await data.match('./reports/2026-09-15.json');
  assert.equal((await historic?.json()).fromV2,true);
  assert.equal((await (await data.match('./reports/2026-09-20.json')).json()).fromS1,true);
  assert.ok(!cachesMap.has('ai-daily-S1-1-reading-reports'));
  for(let i=0;i<100;i++)await emit('fetch',new Request(BASE+'reports/'+newest+'.json?rev='+i));
  assert.equal((await data.keys()).filter(key=>key.url.includes(newest+'.json')).length,1);
  assert.ok(await data.match('./reports/index.json'));
  assert.equal(lastNetworkOptions.cache,'no-store');
  failure=true;
  const fallback=await emit('fetch',new Request(BASE+'reports/'+newest+'.json?rev=offline'));
  assert.equal(fallback.headers.get('X-AI-Daily-Cache'),'offline');
  assert.equal((await fallback.json()).revision,'S1-fresh');
  failure=false;malformed=true;
  const intact=await emit('fetch',new Request(BASE+'reports/'+newest+'.json?broken=1'));
  assert.equal(intact.headers.get('X-AI-Daily-Cache'),'offline');
  assert.equal((await intact.json()).revision,'S1-fresh','Malformed HTTP 200 overwrote valid offline reading');
  malformed=false;
  const put=data.put.bind(data);data.put=async()=>{throw new Error('QuotaExceededError');};
  const online=await emit('fetch',new Request(BASE+'reports/'+newest+'.json?quota=1'));
  assert.equal(online.headers.get('X-AI-Daily-Cache'),null);
  assert.equal((await online.json()).revision,'S1-fresh','A full cache blocked valid network content');
  data.put=put;
  unrepaired=true;
  const rejectedNetwork=await emit('fetch',new Request(BASE+'reports/2026-10-09.json'));
  assert.equal((await rejectedNetwork.json()).content_generation_profile,'source_outline_v2','Unrepaired HTTP 200 resurrected old prose');
  await data.put('./reports/2026-10-09.json',json(report('2026-10-09',{revision:'old-repetitive'})));
  assert.equal((await emit('fetch',new Request(BASE+'reports/2026-10-09.json'))).status,503,'Corrupt repaired-date cache escaped validation');
  failure=true;
  assert.equal((await emit('fetch',new Request(BASE+'reports/2026-10-09.json'))).status,503);
  failure=false;unrepaired=false;
  // Failed install downloads cannot migrate known bad revisions later.
  const badLegacy=await cacheAPI.open('ai-daily-S1-2-reading-reports');
  await badLegacy.put('./reports/2026-10-09.json',json(report('2026-10-09')));
  await data.delete('./reports/2026-10-09.json');
  await emit('activate');
  assert.equal(await data.match('./reports/2026-10-09.json'),undefined);
  assert.equal(await emit('fetch',new Request('https://private.supabase.co/rest/v1/vocabulary_events')),undefined);
  assert.equal(await emit('fetch',new Request(BASE+'cloud-config.json')),undefined);
  assert.equal(await emit('fetch',new Request(BASE+'../another-project/app.js')),undefined);
  console.log('S1 WORKER PASS: legacy migration, 42 dated reports, protected index/status, 100 canonical refreshes, HTTP 503/malformed fallback, quota failure, private/sibling origin bypass');
})().catch(error=>{console.error(error);process.exitCode=1;});

/* Regression tests for live-schedule failure versus successful recovery.
 * Public GitHub and the report date are mocked; claims are tested independently
 * of the date on which CI happens to execute. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium,webkit}=require('playwright');

const root=path.resolve(__dirname,'..');
const reports=path.join(root,'site','reports');
const index=JSON.parse(fs.readFileSync(path.join(reports,'index.json'),'utf8'));
const original=JSON.parse(fs.readFileSync(path.join(reports,index[0].date+'.json'),'utf8'));
const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Hong_Kong',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const dateParts=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Hong_Kong',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
const part=k=>dateParts.find(p=>p.type===k)?.value;
const hkToday=part('year')+'-'+part('month')+'-'+part('day');
const scheduled={id:71001,event:'schedule',status:'completed',conclusion:'failure',
  created_at:new Date(hkToday+'T07:41:00+08:00').toISOString(),
  html_url:'https://github.com/Tom-gpt65/ai-daily-intelligence/actions/runs/71001'};
const recovered={id:71002,event:'workflow_dispatch',status:'completed',conclusion:'success',
  created_at:new Date(hkToday+'T08:36:00+08:00').toISOString(),
  html_url:'https://github.com/Tom-gpt65/ai-daily-intelligence/actions/runs/71002'};
const succeeded={...scheduled,id:71003,conclusion:'success',
  html_url:'https://github.com/Tom-gpt65/ai-daily-intelligence/actions/runs/71003'};

async function scenario(engine,browser,scenarioName,scheduledRuns,manualRuns,reportedTime,expectedClass,expectedText,expectedLink,mode='source_digest'){
 const instance=await browser.launch({headless:true});
 try{
  const context=await instance.newContext({viewport:{width:1024,height:768},deviceScaleFactor:2});
  const page=await context.newPage();
  const errors=[];
  page.on('pageerror',err=>errors.push(err.message));
  // Explicit fixture mode: tests must not silently change based on the
  // mutable latest article (early reading at 07:05, news later at 07:40).
  const edition={...original,mode,date:hkToday,
    updated_at:new Date(hkToday+'T'+reportedTime+'+08:00').toISOString()};
  if(mode==='source_digest'){
    edition.stories=[1,2,3].map(id=>({id:'S'+id,title:'Test source '+id,
      publisher:'Synthetic source',url:'https://example.com/source-'+id}));
    edition.subtitle='Simulated sourced news for status testing';
  }else{
    assert.equal(mode,'reading_feature');
    edition.stories=[];
    edition.subtitle="Original extended English reading · Not today's AI news";
  }
  const reportIndex=[{...index[0],mode,date:hkToday}];
  await page.route(u=>u.href.includes('/reports/index.json'),route=>
    route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(reportIndex)}));
  await page.route(u=>u.href.includes('/reports/'+hkToday+'.json'),route=>
    route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(edition)}));
  await page.route(u=>u.href.includes('/actions/workflows/daily.yml/runs?'),route=>{
    const event=new URL(route.request().url()).searchParams.get('event');
    const workflow_runs=event==='schedule'?scheduledRuns:manualRuns;
    return route.fulfill({status:200,contentType:'application/json',
      headers:{'access-control-allow-origin':'*'},body:JSON.stringify({workflow_runs})});
  });
  await page.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded',timeout:20000});
  await page.locator('#schedule-live.'+expectedClass).waitFor({state:'visible',timeout:20000});
  const label=await page.locator('#schedule-text').innerText();
  assert.ok(label.includes(expectedText),engine+' '+scenarioName+': wrong status: '+label);
  assert.ok(!label.includes('08:00 目標未達成'),engine+': status falsely asserts an exact public deadline');
  if(scenarioName==='scheduled failed + recovery succeeds')assert.ok(label.includes('原定排程失敗'));

  if(expectedLink)assert.ok((await page.locator('#schedule-run-link').getAttribute('href')).includes(expectedLink),engine+' '+scenarioName+': wrong execution link');
  assert.ok(await page.locator('#reader .essay-paragraph').count()>=5,engine+' '+scenarioName+': article not loaded');
  assert.deepEqual(errors,[],engine+' '+scenarioName+': JavaScript errors');
  const width=await page.evaluate(()=>document.documentElement.scrollWidth);
  assert.ok(width<=1026,engine+' '+scenarioName+': iPad landscape overflows at '+width+'px');
  console.log('PASS',engine,scenarioName,label);
 }finally{await instance.close();}
}


async function dictionaryGateDiagnostic(engine,browser){
 const instance=await browser.launch({headless:true});
 try{
  const context=await instance.newContext({viewport:{width:1024,height:768}});
  const page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route(url=>url.pathname.endsWith('/system-status.json'),route=>
    route.fulfill({status:200,contentType:'application/json',
      body:JSON.stringify({state:'incomplete_dictionary',missing_count:2,
        missing_examples:['openai','openproblembench'],
        checked_at:new Date().toISOString(),feeds_failed:0})}));
  await page.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded',timeout:20000});
  const alert=page.locator('#pipeline-alert');
  await page.waitForFunction(()=>document.querySelector('#pipeline-alert')?.textContent?.includes('新聞已收集，但新稿未能發布'),null,{timeout:15000});
  assert.ok(await alert.isVisible(),engine+' missing dictionary alert must be visible above reading overview');
  const label=await alert.innerText();
  assert.match(label,/openai/);
  assert.match(label,/openproblembench/);
  assert.match(label,/備援正常部署/);
  assert.ok(!await alert.evaluate(el=>el.classList.contains('pipeline-success')),
    engine+' a rejected-news article must not display green publication success');
  assert.deepEqual(errors,[],engine+' dictionary alert JavaScript errors');
  console.log('PASS',engine,'rejected sourced news reports dictionary error without claiming new publication');
 }finally{await instance.close();}
}

async function historicalRace(engine,browser){
 const instance=await browser.launch({headless:true});
 try{
  const context=await instance.newContext({viewport:{width:1024,height:768}});
  const page=await context.newPage(),errors=[];
  page.on('pageerror',err=>errors.push(err.message));
  await page.route(url=>url.href.includes('/actions/workflows/daily.yml/runs?'),async route=>{
    await new Promise(resolve=>setTimeout(resolve,1200));
    await route.fulfill({status:200,contentType:'application/json',
      headers:{'access-control-allow-origin':'*'},
      body:JSON.stringify({workflow_runs:[scheduled]})});
  });
  const requested=page.waitForRequest(request=>request.url().includes('/actions/workflows/daily.yml/runs?'),{timeout:15000});
  await page.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded'});
  await requested;
  await page.locator('[data-view="archive"]').click();
  const historical=page.locator('#archive-list .archive-card').filter({hasText:'8 October 2026'});
  await historical.click();
  await page.waitForFunction(()=>document.querySelector('#report-metadata')?.textContent.includes('8 October 2026'),null,{timeout:12000});
  await page.waitForTimeout(1500);
  assert.match(await page.locator('#schedule-text').innerText(),/歷史文章/,
    engine+' delayed scheduled failure overwrote an intentionally opened historical article');
  assert.deepEqual(errors,[],engine+' delayed status page errors');
  console.log('PASS',engine,'delayed GitHub schedule reply does not overwrite historical reading');
 }finally{await instance.close();}
}

(async()=>{
 for(const {engine,browser} of [{engine:'chromium',browser:chromium},{engine:'webkit',browser:webkit}]){
  await scenario(engine,browser,'scheduled failed + recovery succeeds',[scheduled],[recovered],
    '08:44:32','schedule-recovered','補救成功','71002');
  await scenario(engine,browser,'scheduled failed + article stale',[scheduled],[recovered],
    '07:35:00','schedule-failed','尚未確認更新','71001');
  await scenario(engine,browser,'scheduled succeeds',[succeeded],[],
    '07:58:00','schedule-success','原定排程正常','71003');
  await scenario(engine,browser,'scheduled fails but educational reserve is ready',[scheduled],[],
    '07:20:00','schedule-failed','新聞更新工作失敗','71001','reading_feature');
  await scenario(engine,browser,'scheduled and recovery fail but educational reserve is ready',
    [scheduled],[{...recovered,conclusion:'failure'}],
    '07:20:00','schedule-failed','新聞更新工作失敗','71002','reading_feature');
  await scenario(engine,browser,'scheduled succeeds but article remains educational',
    [succeeded],[],
    '07:20:00','schedule-recovered','未有達標即時新聞','71003','reading_feature');
  await dictionaryGateDiagnostic(engine,browser);
  await historicalRace(engine,browser);
 }
 console.log('RESULT: 12 schedule/tablet cases, 2 dictionary rejection alerts and 2 delayed historical status cases passed');
})().catch(err=>{console.error(err);process.exit(1);});

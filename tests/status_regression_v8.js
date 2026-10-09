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

async function scenario(engine,browser,scenarioName,scheduledRuns,manualRuns,reportedTime,expectedClass,expectedText,expectedLink){
 const instance=await browser.launch({headless:true});
 try{
  const context=await instance.newContext({viewport:{width:1024,height:768},deviceScaleFactor:2});
  const page=await context.newPage();
  const errors=[];
  page.on('pageerror',err=>errors.push(err.message));
  const edition={...original,date:hkToday,updated_at:new Date(hkToday+'T'+reportedTime+'+08:00').toISOString()};
  const reportIndex=[{...index[0],date:hkToday}];
  await page.route(u=>u.includes('/reports/index.json'),route=>
    route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(reportIndex)}));
  await page.route(u=>u.includes('/reports/'+hkToday+'.json'),route=>
    route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(edition)}));
  await page.route(u=>u.includes('/actions/workflows/daily.yml/runs?'),route=>{
    const event=new URL(route.request().url()).searchParams.get('event');
    const workflow_runs=event==='schedule'?scheduledRuns:manualRuns;
    return route.fulfill({status:200,contentType:'application/json',
      headers:{'access-control-allow-origin':'*'},body:JSON.stringify({workflow_runs})});
  });
  await page.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded',timeout:20000});
  await page.locator('#schedule-live.'+expectedClass).waitFor({state:'visible',timeout:20000});
  const label=await page.locator('#schedule-text').innerText();
  assert.ok(label.includes(expectedText),engine+' '+scenarioName+': wrong status: '+label);
  if(expectedLink)assert.ok((await page.locator('#schedule-run-link').getAttribute('href')).includes(expectedLink),engine+' '+scenarioName+': wrong execution link');
  assert.ok(await page.locator('#reader .essay-paragraph').count()>=5,engine+' '+scenarioName+': article not loaded');
  assert.deepEqual(errors,[],engine+' '+scenarioName+': JavaScript errors');
  const width=await page.evaluate(()=>document.documentElement.scrollWidth);
  assert.ok(width<=1026,engine+' '+scenarioName+': iPad landscape overflows at '+width+'px');
  console.log('PASS',engine,scenarioName,label);
 }finally{await instance.close();}
}

(async()=>{
 for(const {engine,browser} of [{engine:'chromium',browser:chromium},{engine:'webkit',browser:webkit}]){
  await scenario(engine,browser,'scheduled failed + recovery succeeds',[scheduled],[recovered],
    '08:44:32','schedule-recovered','額外觸發生成已成功','71002');
  await scenario(engine,browser,'scheduled failed + article stale',[scheduled],[recovered],
    '07:35:00','schedule-failed','尚未確認今日文章已更新','71001');
  await scenario(engine,browser,'scheduled succeeds',[succeeded],[],
    '07:58:00','schedule-success','07:40 定時工作成功','71003');
 }
 console.log('RESULT: 6 / 6 schedule and tablet-view regression cases passed');
})().catch(err=>{console.error(err);process.exit(1);});

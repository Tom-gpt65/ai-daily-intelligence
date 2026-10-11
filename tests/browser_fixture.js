/* Local browser laboratory only. Future S2 prose is loaded from actual,
 * automatically accepted reserves; no synthetic essay is a generation proof.
 * A retired V1 educational reading is redated ONLY in this disposable UI
 * fixture to exercise historical MC/backup compatibility after withdrawal. */
'use strict';
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const clockDay='2026-10-12';
function latest(){return JSON.parse(fs.readFileSync(path.join(root,'reading-reserve',clockDay+'.json'),'utf8'));}
function historical(){
  const value=JSON.parse(fs.readFileSync(path.join(root,'content-history/retired/2026-10-08.json'),'utf8'));
  return {...value,date:'2026-10-07'};
}
function row(r){return {date:r.date,headline:r.headline,mode:r.mode,word_count:r.word_count,
  updated_at:r.updated_at,stories:r.stories.length};}
function index(){return [row(latest()),row(historical())];}
function body(relative){
  if(relative==='reports/index.json')return JSON.stringify(index());
  if(relative==='reports/'+clockDay+'.json')return JSON.stringify(latest());
  if(relative==='reports/2026-10-07.json')return JSON.stringify(historical());
  if(relative==='system-status.json')return JSON.stringify({state:'published',latest_date:clockDay,
    mode:'reading_feature',checked_at:clockDay+'T07:05:00+08:00'});
  return null;
}
async function clock(context){
  await context.addInitScript(day=>{
    const Original=Date,stamp=Original.parse(day+'T12:00:00+08:00');
    window.Date=class extends Original{constructor(...args){super(...(args.length?args:[stamp]));}static now(){return stamp;}};
  },clockDay);
}
async function legacyTranslation(page){
  await page.route(url=>url.pathname.endsWith('/reports/'+clockDay+'.json'),route=>{
    const report=latest();report.translations=[];
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(report)});
  });
}
module.exports={clockDay,clock,latest,historical,index,body,legacyTranslation};

/* V5: evidence-first, offline-friendly, accessible reader; no tracking or paid APIs. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const state = { report: null, index: [], dictCache: new Map(), showTranslation: false, largeText: false, fontScale: 0, readingWpm: 115, view: 'today', lookup: '' };
  const safeStorage = {
    get(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } },
    set(key, data) { try { localStorage.setItem(key, JSON.stringify(data)); } catch { toast('瀏覽器無法儲存資料。'); } }
  };
  const SAVED_KEY = 'ai-daily-saved-v2'; // keep keys compatible with v2, never discard prior words
  const READ_KEY = 'ai-daily-read-v1';
  const ANSWERS_KEY = 'ai-daily-answers-v1';
  const PROGRESS_KEY = 'ai-daily-reading-progress-v1';
  let progressRecords = safeStorage.get(PROGRESS_KEY, {});
  let lastFocus = null;
  let requestSerial = 0;
  let scrollingTimer = 0;
  let readRecords = safeStorage.get(READ_KEY, {});
  let writtenAnswers = safeStorage.get(ANSWERS_KEY, {});
  let wordFilter = '';
  let archiveFilter = '';
  let archiveMode = 'all';
  let focusMode = false;
  let reviewQueue = [];
  let reviewPosition = 0;
  const PHRASE_RE = /(\[S\d+\]|[A-Za-z]+(?:['’\-][A-Za-z]+)*)/g;
  let saved = safeStorage.get(SAVED_KEY, {});
  let translationBusy=false;
  let quizSelections=safeStorage.get('ai-daily-quiz-v6',{});
  let toastTimeout;
  function toast(message) { const el = $('toast'); el.textContent = message; el.classList.remove('hidden'); clearTimeout(toastTimeout); toastTimeout = setTimeout(() => el.classList.add('hidden'), 2800); }
  function formatDate(d) { if (!/^\d{4}-\d{2}-\d{2}$/.test(d || '')) return d || ''; return new Date(d + 'T12:00:00+08:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Asia/Hong_Kong' }); }
  const wordKey = w => String(w || '').toLowerCase().replace(/[^a-z'-]/g, '').replace(/'s$/, '');
  const has = (obj, key) => Object.prototype.hasOwnProperty.call(obj || {}, key);
  function stems(w) {
    const v=wordKey(w), forms=[v];
    if(v.length>5 && v.endsWith('ies')) forms.push(v.slice(0,-3)+'y');
    if(v.length>5 && v.endsWith('ing')) {forms.push(v.slice(0,-3),v.slice(0,-3)+'e'); if(v.length>6 && v[v.length-4]===v[v.length-5]) forms.push(v.slice(0,-4));}
    if(v.length>4 && v.endsWith('ed')) forms.push(v.slice(0,-2),v.slice(0,-1));
    if(v.length>4 && v.endsWith('es')) forms.push(v.slice(0,-2));
    if(v.length>4 && v.endsWith('s')) forms.push(v.slice(0,-1));
    if(v.length>5 && v.endsWith('ly')) forms.push(v.slice(0,-2));
    return [...new Set(forms)].filter(Boolean);
  }
  const offlineGlossary=Object.create(null);
  // Essential fallback works even if an outdated PWA has not cached the new glossary.
  offlineGlossary.concern={translation:'關乎；涉及（動詞）；憂慮；關切（名詞）',phonetic:'',part_of_speech:'',definition:''};
  async function preloadOfflineGlossary(){
    try{
      const response=await fetch('./offline-glossary.json',{cache:'force-cache'});
      if(!response.ok)return;
      const words=await response.json();
      if(!words||typeof words!=='object'||Array.isArray(words))return;
      for(const [word,meaning] of Object.entries(words)){
        if(/^[a-z-]+$/.test(word)&&typeof meaning==='string'&&meaning.length>0&&meaning.length<150)
          offlineGlossary[word]={translation:meaning,phonetic:'',part_of_speech:'',definition:''};
      }
    }catch{/* Offline reading is still available with the bundled dictionary and core fallback. */}
  }
  function localMeaning(word) {
    const dic=state.report?.dictionary||{};
    const forms=stems(word);
    for(const key of forms)if(dic[key]?.translation)return {...dic[key],key};
    for(const key of forms)if(offlineGlossary[key]?.translation)return {...offlineGlossary[key],key};
    return null;
  }
  function dueWords() {return Object.keys(saved).filter(key=>!saved[key]?.nextReview || saved[key].nextReview<=hkDate());}
  function updateSavedCount() { $('saved-count').textContent = Object.keys(saved).length; $('review-count').textContent=`(${dueWords().length})`; }
  function reviewNextDate(days) {const dt=new Date(hkDate()+'T00:00:00Z');dt.setUTCDate(dt.getUTCDate()+days);return dt.toISOString().slice(0,10);}
  function renderReview(){
    const panel=$('review-panel');
    if(reviewQueue.length===0){panel.classList.add('hidden');updateSavedCount();return;}
    panel.classList.remove('hidden');
    const key=reviewQueue[0];
    $('review-front').textContent=key;
    $('review-back').textContent=saved[key]?.translation||'暫無可用詞義，請參考原文。';
    $('review-back').classList.add('hidden');
    $('review-show').classList.remove('hidden');
    ['review-again','review-hard','review-remember','review-easy'].forEach(id=>$(id).classList.add('hidden'));
    $('review-position').textContent=`本輪第 ${reviewPosition+1} 張，尚餘 ${reviewQueue.length} 張`;
  }
  function finishReview(rating) {
    const key=reviewQueue.shift(); if(!key || !has(saved,key))return;
    const old=Math.max(0,Math.min(6,Number(saved[key].reviewLevel)||0));
    const levels={again:0,hard:Math.max(0,old),good:Math.min(6,old+1),easy:Math.min(6,old+2)};
    const level=levels[rating] ?? old;
    const days={again:1,hard:[1,1,2,3,5,8,12][old],good:[1,2,4,7,14,28,45][level],easy:[3,5,9,16,30,50,75][level]}[rating] || 1;
    saved[key].reviewLevel=level;
    saved[key].nextReview=reviewNextDate(days);
    saved[key].lastReviewed=new Date().toISOString();
    reviewPosition++;
    safeStorage.set(SAVED_KEY,saved);
    renderWords();renderReview();refreshDashboard();
    if(!reviewQueue.length)toast('本次複習已完成。');
  }
  function readingStreak() {
    const dates = new Set(Object.values(readRecords).filter(v=>typeof v==='string'&&Number.isFinite(Date.parse(v))).map(v=>{const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Hong_Kong',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(v));const get=k=>parts.find(p=>p.type===k)?.value||'';return get('year')+'-'+get('month')+'-'+get('day');}));
    let day = new Date(hkDate() + 'T00:00:00Z');
    if (!dates.has(hkDate())) day.setUTCDate(day.getUTCDate() - 1);
    let length = 0;
    while (dates.has(day.toISOString().slice(0, 10))) {
      length++;
      day.setUTCDate(day.getUTCDate() - 1);
    }
    return length;
  }
  function refreshDashboard(){
    const readCount=Object.keys(readRecords).filter(d=>readRecords[d]).length;
    $('overview-read').textContent=readCount+' 篇';
    $('overview-due').textContent=dueWords().length+' 個待複習 · '+readingStreak()+' 日連續閱讀';
  }
  function downloadJson(name,data){
    const content=new Blob([JSON.stringify(data,null,2)],{type:'application/json;charset=utf-8'});
    const url=URL.createObjectURL(content),a=document.createElement('a');
    a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),800);
  }
  function exportAll(){
    downloadJson('ai-daily-learning-backup-'+hkDate()+'.json',{
      type:'ai-daily-learning-backup', version:5,exported_at:new Date().toISOString(),
      words:saved,readRecords,writtenAnswers,progressRecords,quizSelections
    });
    toast('完整學習進度備份已下載。');
  }
  async function importAll(file){
    if(!file || file.size>1_200_000){toast('檔案不存在或超過 1.2 MB。');return;}
    try{
      const data=JSON.parse(await file.text());
      if(data.type!=='ai-daily-learning-backup'||![3,4,5].includes(data.version)||!data.words||!data.readRecords||!data.writtenAnswers)throw Error('format');
      const w=Object.entries(data.words);
      if(w.length>5000||Object.keys(data.readRecords).length>1500||Object.keys(data.writtenAnswers).length>3000)throw Error('size');
      const clean={};
      for(const [key,value] of w){
        if(!/^[a-z][a-z'-]{0,45}$/.test(key)||!value||typeof value!=='object'||Array.isArray(value))continue;
        clean[key]={translation:String(value.translation||'').slice(0,300),phonetic:String(value.phonetic||'').slice(0,90),savedAt:String(value.savedAt||'').slice(0,45),reviewLevel:Math.max(0,Math.min(6,Number(value.reviewLevel)||0)),nextReview:/^\d{4}-\d{2}-\d{2}$/.test(value.nextReview||'')?value.nextReview:''};
      }
      const rr={},wa={};
      for(const [key,value] of Object.entries(data.readRecords))if(/^\d{4}-\d{2}-\d{2}$/.test(key)&&typeof value==='string')rr[key]=value.slice(0,45);
      for(const [key,value] of Object.entries(data.writtenAnswers))if(/^\d{4}-\d{2}-\d{2}-(?:\d+|v[67]-Q\d+|v[67]-legacy-\d+)$/.test(key)&&typeof value==='string')wa[key]=value.slice(0,2500);
      const pp={};
      if(data.progressRecords && typeof data.progressRecords==='object' && !Array.isArray(data.progressRecords)) {
        for(const [key,value] of Object.entries(data.progressRecords)) {
          if(/^\d{4}-\d{2}-\d{2}$/.test(key) && Number.isFinite(Number(value))) pp[key]=Math.max(0,Math.min(100,Number(value)));
        }
      }
      const qa={};
      if(data.quizSelections&&typeof data.quizSelections==='object'&&!Array.isArray(data.quizSelections)){
        for(const [key,value] of Object.entries(data.quizSelections).slice(0,2500)){
          if(!/^\d{4}-\d{2}-\d{2}-v[67]-Q\d+$/.test(key)||!value||typeof value!=='object')continue;
          if(!Number.isInteger(value.selected)||value.selected<0||value.selected>5)continue;
          qa[key]={selected:value.selected,correct:Boolean(value.correct),submittedAt:String(value.submittedAt||'').slice(0,40)};
        }
      }
      quizSelections={...quizSelections,...qa};safeStorage.set('ai-daily-quiz-v6',quizSelections);
      saved={...saved,...clean};readRecords={...readRecords,...rr};writtenAnswers={...writtenAnswers,...wa};
      progressRecords={...progressRecords,...pp};safeStorage.set(PROGRESS_KEY,progressRecords);
      safeStorage.set(SAVED_KEY,saved);safeStorage.set(READ_KEY,readRecords);safeStorage.set(ANSWERS_KEY,writtenAnswers);
      updateSavedCount();refreshDashboard();renderWords();readingStatus();toast('學習進度已合併還原。');
    }catch{toast('備份檔案無效，沒有修改現有紀錄。');}
  }
  function hkDayFor(timestamp){
    const time=Date.parse(timestamp||'');
    if(!Number.isFinite(time))return '';
    const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Hong_Kong',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(time));
    const find=key=>parts.find(p=>p.type===key)?.value||'';
    return find('year')+'-'+find('month')+'-'+find('day');
  }
  function hkClockFor(timestamp){
    const time=Date.parse(timestamp||'');
    return Number.isFinite(time)?new Intl.DateTimeFormat('zh-HK',{timeZone:'Asia/Hong_Kong',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(time)):'時間未明';
  }
  function reportMorningReady(today){
    const r=state.report;
    if(!r||r.date!==today||r.mode==='demo')return false;
    const time=Date.parse(r.updated_at||'');
    if(!Number.isFinite(time)||hkDayFor(r.updated_at)!==today)return false;
    const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Hong_Kong',hour:'2-digit',minute:'2-digit',hour12:false}).formatToParts(new Date(time));
    const get=k=>Number(parts.find(p=>p.type===k)?.value||-1);
    return get('hour')*60+get('minute') >= (r.mode==='reading_feature'?420:460);
  }
  async function fetchDailyRuns(event){
    const url='https://api.github.com/repos/Tom-gpt65/ai-daily-intelligence/actions/workflows/daily.yml/runs?event='+event+'&per_page=25';
    const response=await fetch(url,{cache:'no-store',headers:{Accept:'application/vnd.github+json'}});
    if(!response.ok)throw new Error('GitHub API '+response.status);
    const json=await response.json();
    if(!Array.isArray(json.workflow_runs))throw new Error('Invalid GitHub response');
    return json.workflow_runs;
  }
  async function renderScheduleHealth(){
    const label=$('schedule-text'),link=$('schedule-run-link'),bar=$('schedule-live');
    if(!label||!link||!bar)return;
    bar.classList.remove('schedule-failed','schedule-success','schedule-recovered');
    label.textContent='正在核對今日定時及補救更新…';
    const today=hkDate();
    const checked=await Promise.allSettled([fetchDailyRuns('schedule'),fetchDailyRuns('workflow_dispatch')]);
    const [scheduled,dispatched]=checked.map(outcome=>outcome.status==='fulfilled'?
      outcome.value.filter(run=>hkDayFor(run.created_at)===today):null);
    const schedule=scheduled?.[0]||null;
    const completedRecovery=dispatched?.find(run=>run.status==='completed'&&run.conclusion==='success')||null;
    const activeRecovery=dispatched?.find(run=>run.status!=='completed')||null;
    const ready=reportMorningReady(today);
    const stamp=ready?hkClockFor(state.report.updated_at):'';
    if(ready&&state.report?.mode==='reading_feature'){
      label.textContent='✓ 今日英文閱讀已提供（AI 延伸閱讀 · 非即時新聞）';
      bar.classList.add('schedule-recovered');
      return;
    }
    const now=new Date();
    const hours=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Hong_Kong',hour:'2-digit',minute:'2-digit',hour12:false}).formatToParts(now);
    const hh=Number(hours.find(x=>x.type==='hour')?.value||0);
    const mm=Number(hours.find(x=>x.type==='minute')?.value||0);
    const late=hh*60+mm>=485;
    // GitHub event=schedule only answers whether the originally scheduled run
    // succeeded. A successful workflow_dispatch is separate evidence, not a
    // retroactive success for the 07:40 schedule.
    if(schedule?.status==='completed'&&schedule.conclusion==='success'&&ready){
      label.textContent='✓ 今日文章已更新 · '+stamp+'（原定排程正常）';
      bar.classList.add('schedule-success');
      link.href=schedule.html_url||link.href;
    }else if(completedRecovery&&ready){
      const previous=schedule?.status==='completed'&&schedule.conclusion!=='success'?
        '原定排程失敗':schedule?'原定排程待核實':'原定排程未確認';
      label.textContent='✓ 今日文章已更新 · '+stamp+'（補救成功；'+previous+'）';
      bar.classList.add('schedule-recovered');
      link.href=completedRecovery.html_url||link.href;
    }else if(schedule?.status==='completed'&&schedule.conclusion!=='success'){
      label.textContent=ready?
        'ⓘ 今日文章已更新 · '+stamp+'（原定排程失敗）':
        '⚠ 今日文章尚未確認更新（原定排程失敗）';
      bar.classList.add(ready?'schedule-recovered':'schedule-failed');
      link.href=schedule.html_url||link.href;
    }else if(schedule?.status==='completed'&&schedule.conclusion==='success'){
      label.textContent='⚠ 原定排程完成，但今日新文章尚未核實';
      bar.classList.add('schedule-failed');
      link.href=schedule.html_url||link.href;
    }else if(schedule&&schedule.status!=='completed'){
      label.textContent=ready?'今日文章已更新 · '+stamp+'（排程仍在執行）':'正在生成今日文章';
      link.href=schedule.html_url||link.href;
    }else if(activeRecovery){
      label.textContent=ready?'今日文章已更新 · '+stamp+'（補救仍在執行）':'正在補救生成今日文章';
      link.href=activeRecovery.html_url||link.href;
    }else if(ready){
      label.textContent='ⓘ 今日文章已更新 · '+stamp+'（排程狀態待核實）';
      bar.classList.add('schedule-recovered');
    }else if(scheduled===null&&dispatched===null){
      label.textContent='排程狀態暫時無法查核，請查看工作紀錄';
    }else if(late){
      label.textContent='⚠ 今日文章尚未更新，請稍後再試';
      bar.classList.add('schedule-failed');
    }else{
      label.textContent='今日文章排程尚待確認';
    }
    // One unavailable endpoint cannot establish that a particular run failed.
    if(scheduled===null||dispatched===null){
      label.textContent+='（部分 GitHub 紀錄暫時無法查核）';
    }
  }
  async function renderPipelineStatus(){
    try{
      const response=await fetch('./system-status.json',{cache:'no-store'});
      if(!response.ok) return;
      const info=await response.json();
      const el=$('pipeline-alert');
      if(info.state==='feed_error'){el.textContent='新聞來源目前無法讀取；沒有證據表示今天沒有重要新聞。請檢查網絡或 GitHub Actions。';el.classList.remove('hidden');}
      else if(info.state==='no_new_stories'){
        el.textContent='最後檢查：'+new Date(info.checked_at).toLocaleString('zh-HK',{timeZone:'Asia/Hong_Kong'})+'。在可讀取的來源中未發現適合發布的新消息，現保留上一份報告。';
        el.classList.remove('hidden');
      } else if(info.state==='new_stories_found'){
        el.textContent='資料更新正在進行或未完成；這並不代表報告已成功發布。';el.classList.remove('hidden');
      } else if(info.state==='insufficient_evidence'){
        el.textContent='⚠ 本日可核實來源不足，或新稿未達 1,000 個英文單字的最低篇幅；沒有冒充合格長篇，網站暫時保留上一份文章。';
        el.classList.remove('hidden');el.classList.remove('pipeline-success');
      } else if(info.state==='editorial_quality_rejected'){
        const issues=Array.isArray(info.quality_issues)?info.quality_issues.join('、'):'品質未達標';
        el.textContent='⚠ 本日新稿未通過內容品質檢查（重複段落、篇幅或來源證據可能不足），已保留上一份報告。診斷：'+issues;
        el.classList.remove('hidden','pipeline-success');
      } else if(info.state==='published'){
        el.textContent='資料處理最近一次完成：'+new Date(info.checked_at).toLocaleString('zh-HK',{timeZone:'Asia/Hong_Kong'})+'。此為生成流程時間，不代表網站在該刻已公開發布。';
        el.classList.remove('hidden');el.classList.add('pipeline-success');
      }
      if(!el.classList.contains('hidden')) {
        if(Number(info.feeds_failed)>0){el.textContent+=' ⚠ '+info.feeds_failed+' 個 RSS 來源無法讀取，本次新聞可能不完整。';el.classList.remove('pipeline-success');}
        const age=(Date.now()-Date.parse(info.checked_at||''))/3_600_000;
        if(Number.isFinite(age)&&age>48){el.textContent+=' ⚠ 最近一次檢查距今超過 48 小時，請確認排程是否仍在執行。';el.classList.remove('pipeline-success');}
      }
    }catch{showConnectivity(true);}
  }
  function readingEstimate(){
    const words=Number(state.report?.word_count)||0;
    return words ? Math.max(1, Math.round(words/state.readingWpm*10)/10) : 0;
  }
  function renderReadingEstimate(){
    const estimate=readingEstimate();
    $('overview-minutes').textContent=estimate ? `約 ${estimate} 分鐘` : '—';
    $('reading-speed').textContent=`閱讀速度：${state.readingWpm} 字／分鐘`;
  }
  function renderStoryCards(r){
    const root=$('story-cards');root.replaceChildren();
    if(r.mode==='reading_feature'){
      const p=document.createElement('p');p.className='demo-explainer';
      p.textContent='今日提供經預先準備的 AI 素養英文閱讀，並非當日新聞；原定新聞更新仍可能稍後發布。';
      root.appendChild(p);return;
    }
    if(r.mode==='demo'){
      const p=document.createElement('p');p.className='demo-explainer';p.textContent='本頁只提供虛構閱讀練習，沒有今日真實新聞。完成部署後，最新報道將顯示在這裏。';root.append(p);return;
    }
    (r.stories||[]).forEach((story,index)=>{
      const card=document.createElement('a');card.className='story-card';
      try{const u=new URL(story.url);if(!['https:','http:'].includes(u.protocol))return;card.href=u.href;}catch{return;}
      card.target='_blank';card.rel='noopener noreferrer';card.referrerPolicy='no-referrer';
      const num=document.createElement('span');num.className='story-num';num.textContent=String(index+1).padStart(2,'0');
      const topic=document.createElement('span');topic.className='story-topic';topic.textContent=story.topic||'General AI';
      const title=document.createElement('strong');title.textContent=story.title||'Source';
      const source=document.createElement('span');source.className='story-origin';source.textContent=(story.publisher||'')+' · '+(story.source_type||'RSS 報道')+' · '+formatSourceDate(story.published);
      const count=Number(story.coverage_count||1);
      const coverage=document.createElement('span');coverage.className='story-evidence';
      coverage.textContent=count>1?`${count} 家不同來源曾報道同一事件 · 非獨立事實核查`:'目前只收錄一個來源 · 重要內容請自行核實';
      card.append(num,topic,title,source,coverage);root.append(card);
    });
  }

  function formatSourceDate(s) {
    if(!s || !Number.isFinite(Date.parse(s))) return '日期未明';
    return new Date(s).toLocaleDateString('zh-HK',{timeZone:'Asia/Hong_Kong',month:'short',day:'numeric'});
  }
  function paragraphNodes(text, paragraphIndex) {
    const p = document.createElement('p'); p.className = 'essay-paragraph'; p.dataset.index = paragraphIndex;
    String(text || '').split(PHRASE_RE).forEach(part => {
      if (/^\[S\d+\]$/.test(part)) {
        const match=(state.report?.stories || []).find(story=>'['+story.id+']'===part);
        if(match){
          const link=document.createElement('a');link.textContent=part;link.className='source-ref';
          try {const u=new URL(match.url);if(['http:','https:'].includes(u.protocol)){link.href=u.href;link.target='_blank';link.rel='noopener noreferrer';link.referrerPolicy='no-referrer';}}
          catch{}
          if(link.href){link.setAttribute('aria-label','查看來源 '+part);p.appendChild(link);}else p.appendChild(document.createTextNode(part));
        }else p.appendChild(document.createTextNode(part));
      } else if (/^[A-Za-z]/.test(part)) {
        const button = document.createElement('button'); button.type = 'button'; button.className = 'word'; button.textContent = part;
        button.setAttribute('aria-label', '查詢 ' + part);
        p.appendChild(button);
      } else p.appendChild(document.createTextNode(part));
    });
    return p;
  }
  function updateProgress(persist=false) {
    if (state.view !== 'today') return;
    const card = document.querySelector('.briefing-card'); if (!card) return;
    const rect = card.getBoundingClientRect();
    const span = Math.max(1, rect.height - window.innerHeight);
    const done = Math.min(100, Math.max(0, Math.round((-rect.top / span) * 100)));
    $('progress-bar').style.width = done + '%'; $('progress-percent').textContent = done + '%';
    if(persist && state.report && state.report.mode!=='demo') {
      const key=state.report.date;
      if(Math.abs((Number(progressRecords[key])||0)-done)>=3) {
        progressRecords[key]=done;
        clearTimeout(scrollingTimer);
        scrollingTimer=setTimeout(()=>safeStorage.set(PROGRESS_KEY,progressRecords),850);
      }
    }
  }
  function scrollToReadingTarget(element){
    if(!element)return;
    // CSS scroll-behavior:smooth can still animate a behaviour:'auto' call,
    // and native iPad/Safari selectors may subsequently restore the menu's
    // scroll position. Scroll synchronously; the selector schedules a second
    // adjustment after it settles.
    const offset=Math.max(110,Math.min(165,window.innerHeight*0.15));
    const absolute=window.scrollY+element.getBoundingClientRect().top-offset;
    const html=document.documentElement,original=html.style.scrollBehavior;
    html.style.scrollBehavior='auto';
    try{window.scrollTo(0,Math.max(0,absolute));}
    finally{html.style.scrollBehavior=original;}
  }
  function renderReaderNavigator(){
    const nav=$('reader-navigator'),r=state.report;
    if(!nav)return;
    nav.replaceChildren();
    if(!r||!Array.isArray(r.essay)||r.essay.length<3){nav.classList.add('hidden');return;}
    nav.classList.remove('hidden');
    const label=document.createElement('label');label.className='reader-nav-title';
    label.setAttribute('for','reader-nav-select');label.textContent='跳至文章章節';
    nav.appendChild(label);
    const dropdown=document.createElement('select');
    dropdown.id='reader-nav-select';dropdown.className='reader-nav-select';
    dropdown.setAttribute('aria-label','選擇文章段落');
    const firstOfStory=new Map();
    for(const story of r.stories||[]){
      const index=r.essay.findIndex(p=>p.includes('['+story.id+']'));
      if(index>=0&&!firstOfStory.has(index))firstOfStory.set(index,story);
    }
    const last=r.essay.length-1;
    const choices=r.essay.map((_,index)=>{
      const story=firstOfStory.get(index);
      const title=index===0?'引言：文章主旨':
        index===last?'結論：整體評估':
        story?'新聞分析：'+String(story.title||story.topic||story.id).slice(0,43):
        '深入分析與比較';
      return {index,title,label:'第 '+(index+1)+' 段 · '+title};
    });
    for(const choice of choices){
      const option=document.createElement('option');
      option.value=String(choice.index);option.textContent=choice.label;
      dropdown.appendChild(option);
    }
    dropdown.addEventListener('change',()=>{
      const index=Number(dropdown.value);
      if(Number.isInteger(index)&&index>=0&&index<r.essay.length){
        const target=$('reading-paragraph-'+index);
        // Safari may restore the native select position after the change
        // event. Scroll once again after the control has finished settling.
        scrollToReadingTarget(target);
        requestAnimationFrame(()=>setTimeout(()=>scrollToReadingTarget(target),70));
      }
    });
    nav.appendChild(dropdown);
    const chips=[choices[0]];
    for(const choice of choices){
      if(firstOfStory.has(choice.index)&&choice.index!==0)chips.push(choice);
    }
    if(last!==0&&!chips.some(item=>item.index===last))chips.push(choices[last]);
    for(const choice of chips){
      const button=document.createElement('button');
      button.type='button';button.className='reader-nav-link';
      button.textContent=choice.index===0?'引言':choice.index===last?'結論':
        '新聞 '+(chips.indexOf(choice))+' · '+choice.title.replace('新聞分析：','').slice(0,23);
      button.setAttribute('aria-label',choice.label);
      button.addEventListener('click',()=>{
        dropdown.value=String(choice.index);
        scrollToReadingTarget($('reading-paragraph-'+choice.index));
      });
      nav.appendChild(button);
    }
  }

  function renderReader() {
    const root = $('reader'); root.replaceChildren();
    const r = state.report; if (!r) { root.textContent = '暫時未有報告。'; return; }
    const translated=translationProgress(r);
    r.essay.forEach((p, idx) => {
      const paragraph=paragraphNodes(p, idx);
      paragraph.id='reading-paragraph-'+idx;
      paragraph.dataset.paragraph=String(idx+1);
      root.appendChild(paragraph);
      const actions=document.createElement('div');actions.className='paragraph-tools';
      const button=document.createElement('button');button.type='button';button.className='paragraph-translate';
      button.textContent=translated[idx]?(state.showTranslation||paragraphOpen.has(idx)?'收起此段譯文':'查看此段譯文'):'翻譯這一段';
      button.disabled=translationBusy;
      button.setAttribute('aria-label','第 '+(idx+1)+' 段翻譯');
      button.addEventListener('click',()=>{
        if(translated[idx]){
          if(paragraphOpen.has(idx))paragraphOpen.delete(idx);
          else paragraphOpen.add(idx);
          renderReader();
        }else translateOneParagraph(idx);
      });
      actions.appendChild(button);root.appendChild(actions);
      if(translated[idx]&&(state.showTranslation||paragraphOpen.has(idx))){
        const trans=document.createElement('p');trans.className='translation-paragraph';
        trans.lang='zh-Hant';trans.textContent=translated[idx];root.appendChild(trans);
      }
    });
    root.classList.toggle('font-large', state.fontScale>=1);root.classList.toggle('font-xlarge', state.fontScale>=2); updateProgress();
  }
  function translationCacheKey(report){
    const text=report.essay.join('\n');let hash=2166136261;
    for(let i=0;i<text.length;i++)hash=Math.imul(hash^text.charCodeAt(i),16777619);
    return 'ai-daily-zh-v6-'+report.date+'-'+(hash>>>0);
  }
  let translationConsent=false;
  let translationCancel=false;
  const paragraphOpen=new Set();
  function validTranslations(english,translations){
    return Array.isArray(translations)&&translations.length===english.length&&translations.every(v=>typeof v==='string'&&/[\u3400-\u9fff]/.test(v));
  }
  function translationProgress(report){
    const full=Array.isArray(report.translations)?report.translations:[];
    if(validTranslations(report.essay,full))return full.slice();
    const local=safeStorage.get(translationCacheKey(report),[]);
    const result=report.essay.map((_,i)=>{
      const v=local?.[i]||full[i];
      return typeof v==='string'&&/[\u3400-\u9fff]/.test(v)?v:'';
    });
    return result;
  }
  function storeTranslationProgress(report, progress){
    safeStorage.set(translationCacheKey(report),progress);
    report.translations=progress;
  }
  function translationPieces(text,maxBytes=380){
    const encoder=new TextEncoder();
    const result=[];let remaining=String(text||'').trim();
    while(remaining){
      if(encoder.encode(remaining).length<=maxBytes){result.push(remaining);break;}
      let low=1,high=remaining.length,limit=1;
      while(low<=high){
        const mid=(low+high)>>1;
        if(encoder.encode(remaining.slice(0,mid)).length<=maxBytes){limit=mid;low=mid+1;}
        else high=mid-1;
      }
      let cut=remaining.lastIndexOf(' ',limit);
      if(cut<Math.max(35,Math.floor(limit/2)))cut=limit;
      result.push(remaining.slice(0,cut).trim());
      remaining=remaining.slice(cut).trim();
    }
    return result;
  }
  function translatedChunkKey(report,index){
    return translationCacheKey(report)+'-chunks-'+index;
  }
  async function resumeTranslationChunks(report,index){
    // Cache is keyed by the complete article hash AND exact chunk text; a
    // re-edited passage cannot accidentally reuse a previous translation.
    const chunks=translationPieces(report.essay[index]);
    const key=translatedChunkKey(report,index);
    const record=safeStorage.get(key,{});
    const matches=Array.isArray(record.chunks)&&record.chunks.length===chunks.length&&
      record.chunks.every((chunk,i)=>chunk===chunks[i]);
    const results=matches&&Array.isArray(record.results)?record.results.slice(0,chunks.length):[];
    for(let i=0;i<chunks.length;i++){
      if(translationCancel)return null;
      if(typeof results[i]==='string'&&/[\u3400-\u9fff]/.test(results[i]))continue;
      const translated=await publicTranslationSegment(chunks[i]);
      results[i]=translated;
      // Save *every* successful request, not just each complete paragraph.
      safeStorage.set(key,{chunks,results});
    }
    return results.join(' ');
  }
  async function publicTranslationSegment(text){
    const url='https://api.mymemory.translated.net/get?langpair=en%7Czh-TW&q='+encodeURIComponent(text);
    for(let attempt=0;attempt<2;attempt++){
      const controller=new AbortController();
      const timeout=setTimeout(()=>controller.abort(),15000);
      try{
        const response=await fetch(url,{mode:'cors',cache:'no-store',signal:controller.signal});
        if(!response.ok)throw new Error('免費翻譯服務網絡錯誤（HTTP '+response.status+'）');
        const data=await response.json();
        const status=Number(data.responseStatus??200);
        if(status>=400)throw new Error('翻譯服務已達用量上限或拒絕請求（'+status+'）');
        const result=String(data.responseData?.translatedText||'').trim();
        if(!/[\u3400-\u9fff]/.test(result))throw new Error('翻譯結果沒有中文，可能是服務額度不足');
        return result;
      }catch(error){
        if(attempt===1||!navigator.onLine)throw error;
        await new Promise(resolve=>setTimeout(resolve,650));
      }finally{clearTimeout(timeout);}
    }
    throw new Error('免費翻譯暫時不可用');
  }
  function agreeToTranslation(){
    if(translationConsent)return true;
    if(!navigator.onLine){toast('目前離線，可閱讀已儲存譯文，但不能取得新翻譯。');return false;}
    const agree=window.confirm('翻譯需要把公開英文文章內容傳送到免費第三方 MyMemory 翻譯服務。服務可能記錄請求、設有免費額度及產生錯誤譯文。是否同意？');
    if(agree)translationConsent=true;
    return agree;
  }
  function syncTranslationButton(){
    const button=$('translate-toggle');
    const report=state.report;
    if(!report)return;
    const partial=translationProgress(report).filter(Boolean).length;
    button.disabled=false;
    const total=report.essay.length;
    button.textContent=translationBusy?'停止翻譯（已完成 '+partial+'/'+total+' 段）':
       state.showTranslation&&partial===total?'隱藏繁體中文譯文':
       partial>0?'繼續翻譯全文（已完成 '+partial+'/'+total+' 段）':
       state.showTranslation?'重試全文翻譯（免費・需連線）':'翻譯全文（免費・需連線）';
    button.title='可先譯單一段落；全部翻譯會分段保存，失敗後可再嘗試。';
  }
  async function translateOneParagraph(index){
    const report=state.report;
    if(!report||translationBusy||index<0||index>=report.essay.length)return;
    const partial=translationProgress(report);
    if(partial[index]){
      paragraphOpen.add(index);
      renderReader();return;
    }
    if(!agreeToTranslation())return;
    translationBusy=true;translationCancel=false;syncTranslationButton();
    try{
      const translated=await resumeTranslationChunks(report,index);
      if(!translationCancel&&translated){
        partial[index]=translated;
        storeTranslationProgress(report,partial);
        paragraphOpen.add(index);
      }
    }catch(error){
      toast('翻譯未完成：'+String(error.message||error).slice(0,60));
    }finally{translationBusy=false;translationCancel=false;renderReader();syncTranslationButton();}
  }
  async function toggleWholeTranslation(){
    const report=state.report;if(!report)return;
    if(translationBusy){translationCancel=true;toast('已要求停止翻譯；完成當前請求後會保留已譯段落。');return;}
    let partial=translationProgress(report);
    if(state.showTranslation&&partial.every(Boolean)){
      state.showTranslation=false;renderReader();syncTranslationButton();return;
    }
    if(partial.every(Boolean)){
      state.showTranslation=true;renderReader();syncTranslationButton();return;
    }
    if(!agreeToTranslation())return;
    translationBusy=true;translationCancel=false;
    state.showTranslation=true;syncTranslationButton();
    try{
      for(let i=0;i<report.essay.length;i++){
        if(translationCancel)break;
        if(partial[i])continue;
        const translated=await resumeTranslationChunks(report,i);
        if(translationCancel||!translated)break;
        partial[i]=translated;
        storeTranslationProgress(report,partial);
        paragraphOpen.add(i);
        syncTranslationButton();
        renderReader();
      }
    }catch(error){
      toast('暫停在已完成段落：'+String(error.message||error).slice(0,60));
    }finally{translationBusy=false;translationCancel=false;renderReader();syncTranslationButton();}
  }
  function setModeBanner(mode) {
    const el = $('status-banner'); el.classList.toggle('demo', mode === 'demo');
    el.textContent = ({demo:'⚠ 示範教材 · 非即時新聞', editorial:'✦ 已整理當日新聞 · AI 英文改寫', source_digest:'ⓘ 來源式英文練習 · 模型改寫未通過審核', reading_feature:'✦ 今日 AI 延伸閱讀 · 非即時新聞'})[mode] || '已發布報告';
  }
  function hkDate() {
    const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Hong_Kong',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
    const get=x=>parts.find(p=>p.type===x)?.value || '';
    return `${get('year')}-${get('month')}-${get('day')}`;
  }
  function daysOld(date) {
    const current=hkDate();
    if(!/^\d{4}-\d{2}-\d{2}$/.test(date || '')) return 0;
    return Math.round((Date.parse(current+'T00:00:00Z')-Date.parse(date+'T00:00:00Z'))/86400000);
  }
  function readingStatus() {
    const r=state.report;if(!r) return;
    const completed=has(readRecords,r.date) && !!readRecords[r.date];
    $('reading-state').textContent=completed?'✓ 已完成閱讀':'';
    $('mark-read').textContent=completed?'取消已讀標記':'✓ 標記為已讀';
    $('mark-read').setAttribute('aria-pressed',String(completed));
  }
  function renderFreshness() {
    const r=state.report, el=$('freshness-note');
    if(!r)return;
    let message='';
    if(r.mode==='demo')
      message='目前為示範文章，並非當日新聞。';
    else if(daysOld(r.date)>0)
      message=`此為 ${formatDate(r.date)} 的舊文章；今日報告尚未確認發布。請查看工作紀錄。`;
    else if(daysOld(r.date)<0)
      message='文章日期晚於香港今日日期，請檢查資料。';
    else if(r.mode==='reading_feature')
      message='今日屬原創 AI 素養延伸閱讀，並非即時新聞。';
    else if(Number(r.word_count)<1000)
      message='⚠ 本篇低於 1,000 字閱讀標準，請查看發布驗證。';
    // The source type and unverified-news disclaimer remain on the article
    // and source desk; do not repeat an intrusive banner on a valid day.
    el.textContent=message;
    el.classList.toggle('hidden',!message);
  }
  function renderResume() {
    const b=$('resume-reading');
    if(!state.report || state.report.mode==='demo') { b.classList.add('hidden'); return; }
    const amount=Number(progressRecords[state.report.date]||0);
    b.classList.toggle('hidden',!(amount>=8 && amount<96));
    b.textContent='接續上次閱讀（'+Math.round(amount)+'%）';
  }
  function renderReport() {
    const r = state.report; if (!r) return;
    $('report-headline').textContent = r.headline || 'AI Daily Briefing';
    $('report-subtitle').textContent = r.subtitle || '';
    $('report-metadata').textContent = `${formatDate(r.date)} · ${r.word_count || 0} words · ${r.mode==='reading_feature'?'延伸閱讀':(r.stories||[]).length+' sources'}`;
    renderReadingEstimate();
    $('overview-words').textContent=`${r.word_count||0} English words${r.mode==='source_digest'?' · 來源式英文深度分析':''}`;
    $('overview-stories').textContent=r.mode==='reading_feature'?'非即時新聞':(r.stories||[]).length+' 則';
    $('overview-vocab').textContent=(r.advanced_vocabulary||[]).length+' 個';
    $('reading-quality').textContent=r.quality_note||'資料可能有誤；請核實來源。';
    renderStoryCards(r);refreshDashboard();renderResume();
    setModeBanner(r.mode); renderFreshness(); renderReader(); renderReaderNavigator(); readingStatus(); updateZoomNotice();
    syncTranslationButton();
    const sources = $('source-list'); sources.replaceChildren();
    if (!(r.stories || []).length) { const note = document.createElement('div'); note.className='empty-state'; note.textContent=r.mode==='reading_feature'?'本篇為原創 AI 素養延伸閱讀，並非即時新聞，因此沒有當日新聞來源。':'此為離線示範教材，不包含實際新聞來源。'; sources.appendChild(note); }
    (r.stories || []).forEach(s => {
      const a = document.createElement('a'); a.className = 'source-item';
      try { const u = new URL(s.url); if (!['http:', 'https:'].includes(u.protocol)) return; a.href=u.href; } catch { return; }
      a.target='_blank'; a.rel='noopener noreferrer';a.referrerPolicy='no-referrer';
      const publisher=document.createElement('div'); publisher.className='source-publisher'; publisher.textContent=s.publisher || 'Source';
      const title=document.createElement('div'); title.className='source-title'; title.textContent=s.title || 'Original report';
      const date=document.createElement('div'); date.className='source-date'; date.textContent=(s.source_type ? s.source_type+' · ' : '')+(s.published ? new Date(s.published).toLocaleString('en-GB',{timeZone:'Asia/Hong_Kong',dateStyle:'medium'}) : '');
      a.append(publisher,title,date);
      const wrap=document.createElement('div');wrap.className='source-cluster';wrap.append(a);
      const alternates=(Array.isArray(s.coverage)?s.coverage:[]).filter(c=>c.publisher!==s.publisher);
      if(alternates.length){
        const evidence=document.createElement('div');evidence.className='source-alternates';
        const prefix=document.createElement('span');prefix.textContent='同一事件的其他報道（並非獨立核查）：';evidence.append(prefix);
        alternates.forEach(c=>{
          try{const u=new URL(c.url);if(!['http:','https:'].includes(u.protocol))return;
            const link=document.createElement('a');link.href=u.href;link.rel='noopener noreferrer';link.target='_blank';
            link.referrerPolicy='no-referrer';link.textContent=c.publisher;evidence.append(link);
          }catch{}
        });
        wrap.append(evidence);
      }
      sources.appendChild(wrap);
    });
    const spotlight=$('vocab-spotlight'); spotlight.replaceChildren();
    (r.advanced_vocabulary || []).forEach(word => {
      const chip=document.createElement('button'); chip.className='vocab-chip'; chip.type='button';
      const label=document.createElement('span');label.textContent=word;
      const small=document.createElement('small');small.textContent=r.dictionary?.[word]?.translation || '點擊查字';
      chip.append(label,small);chip.addEventListener('click',()=>showLookup(word,chip));spotlight.appendChild(chip);
    });
    const questions=$('question-list');questions.replaceChildren();
    const practice=r.practice&&Array.isArray(r.practice.items)?r.practice:null;
    const entries=practice?practice.items:(r.questions||[]).map((text,i)=>({id:'legacy-'+i,type:'short',skill:'Independent reflection',marks:0,stem:text,guidance:['Refer back to the cited sources. No automatic marking is available.']}));
    $('practice-meta').textContent=practice?
      practice.label+' · '+entries.length+' 題 · '+entries.reduce((sum,item)=>sum+(item.marks||0),0)+' 分。僅有客觀選擇題可作參考評分；書面回答須人工判斷。':
      '舊版閱讀練習：請按原始來源核對；非官方評分。';
    function evidenceLink(body,item){
      if(!Number.isInteger(item.paragraph)||item.paragraph<1||item.paragraph>r.essay.length)return;
      const link=document.createElement('button');link.type='button';link.className='question-action evidence-jump';
      link.textContent='↗ 查看原文第 '+item.paragraph+' 段';link.setAttribute('aria-label','回到英文原文第 '+item.paragraph+' 段');
      link.addEventListener('click',()=>{
        const target=document.getElementById('reading-paragraph-'+(item.paragraph-1));
        if(!target)return;target.scrollIntoView({behavior:'smooth',block:'center'});
        target.classList.add('evidence-focus');
        setTimeout(()=>target.classList.remove('evidence-focus'),2000);
      });
      body.appendChild(link);
    }
    entries.forEach((item,index)=>{
      const section=document.createElement('section');section.className='question-item';
      const num=document.createElement('span');num.className='question-number';num.textContent=String(index+1).padStart(2,'0');
      const body=document.createElement('div');body.className='question-content';
      const skill=document.createElement('span');skill.className='question-skill';
      skill.textContent=(item.skill||'Reading comprehension')+' · '+(item.marks||0)+' marks · '+(item.type==='mc'?'Multiple choice':'Written response');
      const label=document.createElement('strong');label.className='question-label';label.textContent=item.stem||String(item);
      body.append(skill,label);
      const key=r.date+'-v7-'+(item.id||index);
      if(item.type==='mc'&&Array.isArray(item.options)&&Number.isInteger(item.answer)){
        const field=document.createElement('div');field.className='question-options';field.setAttribute('role','radiogroup');field.setAttribute('aria-label',item.stem);
        const feedback=document.createElement('div');feedback.className='question-feedback';feedback.hidden=true;feedback.setAttribute('role','status');
        const remembered=quizSelections[key];
        const existing=remembered&&typeof remembered==='object'&&Number.isInteger(remembered.selected)?remembered:null;
        const inputs=[];
        item.options.forEach((option,i)=>{
          const choice=document.createElement('label');choice.className='question-choice';
          const radio=document.createElement('input');radio.type='radio';radio.name='dse-'+r.date+'-'+item.id;radio.value=String(i);
          radio.checked=existing?.selected===i;
          radio.disabled=Boolean(existing);
          choice.append(radio,document.createTextNode(String.fromCharCode(65+i)+'. '+option));field.append(choice);inputs.push(radio);
        });
        const button=document.createElement('button');button.type='button';button.className='question-action';button.textContent=existing?'已提交':'提交選擇題';button.disabled=Boolean(existing);
        function explain(selected){
          feedback.hidden=false;
          const correct=selected===item.answer;
          feedback.classList.toggle('is-wrong',!correct);
          const quote=item.evidence_quote?' 原文提示：「'+item.evidence_quote+'」':'';
          feedback.textContent=(correct?'✓ 首次作答正確（練習分 1）':'首次作答未能得分（練習分 0）')+
             '。參考答案：'+String.fromCharCode(65+item.answer)+'。'+(item.explanation||'')+
             ' 證據定位：'+(item.evidence||'請參閱原文。')+quote;
        }
        if(existing)explain(existing.selected);
        button.addEventListener('click',()=>{
          const selected=inputs.findIndex(input=>input.checked);
          if(selected<0){feedback.hidden=false;feedback.textContent='請先選擇一個答案。';feedback.classList.add('is-wrong');return;}
          if(quizSelections[key]&&typeof quizSelections[key]==='object')return;
          quizSelections[key]={selected,correct:selected===item.answer,submittedAt:new Date().toISOString()};
          safeStorage.set('ai-daily-quiz-v6',quizSelections);
          inputs.forEach(input=>input.disabled=true);button.disabled=true;button.textContent='已提交';
          explain(selected);
        });
        body.append(field,button,feedback);
      }else{
        const answer=document.createElement('textarea');answer.className='question-answer';answer.rows=item.type==='extended'?5:3;
        answer.placeholder=item.type==='extended'?'以英文寫約 60–90 字（需要人手評分）':'以英文作答（不會自動評分）';
        answer.setAttribute('aria-label','Question '+(index+1)+' answer');
        answer.value=writtenAnswers[key]||writtenAnswers[r.date+'-v6-'+(item.id||index)]||'';
        answer.addEventListener('input',()=>{if(answer.value.trim())writtenAnswers[key]=answer.value.slice(0,2500);else delete writtenAnswers[key];safeStorage.set(ANSWERS_KEY,writtenAnswers);});
        const feedback=document.createElement('div');feedback.className='question-feedback';feedback.hidden=true;
        const button=document.createElement('button');button.type='button';button.className='question-action';button.textContent='查看評分準則（非自動判分）';
        button.addEventListener('click',()=>{feedback.hidden=!feedback.hidden;const quote=item.evidence_quote?' 原文摘錄：「'+item.evidence_quote+'」':'';feedback.textContent=(item.guidance||[]).join(' ')+' 證據定位：'+(item.evidence||'請回查文章')+quote;button.setAttribute('aria-expanded',String(!feedback.hidden));});
        body.append(answer,button,feedback);
      }
      evidenceLink(body,item);
      section.append(num,body);questions.append(section);
    });
  }
  function placePopover(target) {
    const pop=$('dictionary-popover');pop.classList.remove('hidden');
    if(innerWidth<=650){pop.style.left='0';pop.style.top='auto';return;}
    const rect=target.getBoundingClientRect(),width=Math.min(326,innerWidth-28);
    const x=Math.max(14,Math.min(rect.left,innerWidth-width-14));
    pop.style.maxHeight=Math.max(180,innerHeight-22)+'px';pop.style.overflowY='auto';
    const height=Math.min(pop.scrollHeight,innerHeight-22);
    let y=rect.bottom+9;
    if(y+height>innerHeight-10) y=rect.top-height-9;
    y=Math.max(8,Math.min(y,innerHeight-height-8));
    pop.style.left=x+'px';pop.style.top=y+'px';
  }
  function sentenceOf(target) {
    const paragraph=target.closest('p');
    if(!paragraph) return '';
    const all=paragraph.textContent;
    const word=target.textContent;
    let index=0;
    for(const node of paragraph.childNodes){
      if(node===target)break;
      index+=node.textContent.length;
    }
    // Vocabulary chips are not necessarily inside paragraphs.
    if(!paragraph.contains(target)) index=Math.max(0,all.toLowerCase().indexOf(word.toLowerCase()));
    const before=all.slice(0,index);
    const start=Math.max(0,before.search(/[^.!?]*$/));
    const suffix=all.slice(index).search(/[.!?](?:\s|$)/);
    const end=suffix<0?all.length:index+suffix+1;
    return all.slice(start,end).trim().slice(0,320);
  }
  async function showLookup(word, target) {
    const key=wordKey(word); if (!key) return;
    state.lookup=word; state.lookupOpened=Date.now(); $('lookup-word').textContent=word; $('lookup-ipa').textContent='';
    $('lookup-note').textContent='詞典列出常見詞義；實際意思須結合文章理解。';
    const entry=localMeaning(key) || (saved[key]?.translation ? saved[key] : null);
    $('lookup-translation').textContent=entry?.translation || '正在查詢繁體中文詞義…';
    $('lookup-ipa').textContent=entry?.phonetic || '';
    $('lookup-pos').textContent=entry?.part_of_speech || '';
    $('lookup-definition').textContent=entry?.definition || '';
    $('lookup-context').textContent=sentenceOf(target);
    $('save-word').textContent=has(saved,key) ? '✓ 已儲存' : '＋ 儲存生字';
    lastFocus=target;placePopover(target);
    $('lookup-online').classList.toggle('hidden',!!entry);
    if(entry)return;
    if(state.dictCache.has(key)){renderRemote(key,state.dictCache.get(key));$('lookup-online').classList.add('hidden');return;}
    $('lookup-translation').textContent='離線詞典未收錄此詞（或其詞形）';
    $('lookup-note').textContent='如有需要，可自行按下方按鈕查詢第三方翻譯服務；只有選定的英文單字會送出。';
  }
  async function queryRemoteDictionary(){
    const key=wordKey(state.lookup);if(!key)return;
    $('lookup-translation').textContent='正在查詢…';
    try {
      const url='https://api.mymemory.translated.net/get?q='+encodeURIComponent(key)+'&langpair=en%7Czh-TW';
      const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),7000);
      let response;
      try { response=await fetch(url,{signal:controller.signal}); } finally {clearTimeout(timer);}
      if(!response.ok)throw Error('Unavailable');
      const data=await response.json(),text=String(data.responseData?.translatedText||'').trim();
      if(!text||text.length>350||/MYMEMORY WARNING|PLEASE SELECT|QUERY LENGTH/i.test(text)||text.toLowerCase()===key)throw Error('No meaning');
      const result={translation:text,phonetic:''};state.dictCache.set(key,result);
      if(wordKey(state.lookup)===key){renderRemote(key,result);$('lookup-online').classList.add('hidden');$('lookup-note').textContent='第三方機器翻譯：可能不符合本文語境，請自行判斷。';}
    }catch{if(wordKey(state.lookup)===key)$('lookup-translation').textContent='無法取得線上詞義，請稍後再試。';}
  }
  function renderRemote(key,result) { if (wordKey(state.lookup)!==key) return;$('lookup-translation').textContent=result.translation;$('lookup-ipa').textContent=result.phonetic || ''; }
  function closePopover(returnFocus=false){$('dictionary-popover').classList.add('hidden');if(returnFocus&&lastFocus?.isConnected)lastFocus.focus({preventScroll:true});}
  function renderArchive() {
    const root=$('archive-list');root.replaceChildren();
    if(!state.index.length){const box=document.createElement('div');box.className='empty-state';box.textContent='尚未有歷史報告。';root.appendChild(box);return;}
    const matches=state.index.filter(item=>(archiveMode==='all'||item.mode===archiveMode)&&(String(item.headline||'').toLowerCase().includes(archiveFilter)||String(item.date||'').includes(archiveFilter)));
    if(!matches.length){const note=document.createElement('p');note.className='empty-state';note.textContent='沒有符合目前搜尋條件的報告。';root.append(note);return;}
    matches.forEach(item=>{
      const b=document.createElement('button');b.className='archive-card';b.type='button';
      const info=document.createElement('div');
      const d=document.createElement('div');d.className='archive-date';d.textContent=`${formatDate(item.date)} · ${item.word_count} words`;
      const title=document.createElement('div');title.className='archive-title';title.textContent=item.headline;
      if(has(readRecords,item.date) && readRecords[item.date]){const done=document.createElement('span');done.className='archive-complete';done.textContent='✓ 已讀';info.appendChild(done);}
      const arrow=document.createElement('span');arrow.className='archive-arrow';arrow.textContent='↗';
      info.append(d,title);b.append(info,arrow);b.addEventListener('click',()=>loadReport(item.date));root.appendChild(b);
    });
  }
  function renderWords(){
    const root=$('word-list');root.replaceChildren();const items=Object.entries(saved).filter(([key,v])=>key.includes(wordFilter) || String(v.translation||'').includes(wordFilter)).sort((a,b)=>(b[1].savedAt||'').localeCompare(a[1].savedAt||''));
    if(!items.length){const el=document.createElement('div');el.className='empty-state';el.textContent=Object.keys(saved).length?'沒有符合搜尋條件的生字。':'你的生字庫目前是空的。返回每日簡報，點擊英文單字後選擇「儲存生字」。';root.append(el);return;}
    items.forEach(([key,v])=>{
      const card=document.createElement('div');card.className='word-card';
      const info=document.createElement('div');const phon=document.createElement('div');phon.className='word-pronunciation';phon.textContent=v.phonetic||'VOCABULARY';
      const title=document.createElement('div');title.className='word-title';title.textContent=key;
      const meaning=document.createElement('div');meaning.className='word-meaning';meaning.textContent=v.translation || '未有中文詞義';info.append(phon,title,meaning);
      if(v.nextReview){const review=document.createElement('div');review.className='word-review-date';review.textContent='下次複習：'+v.nextReview;info.appendChild(review);}
      const acts=document.createElement('div');acts.className='word-actions';const del=document.createElement('button');del.type='button';del.textContent='移除';del.addEventListener('click',()=>{delete saved[key];reviewQueue=reviewQueue.filter(w=>w!==key);safeStorage.set(SAVED_KEY,saved);updateSavedCount();renderWords();renderReview();});acts.append(del);card.append(info,acts);root.append(card);
    });
  }
  function exportVocabulary() {
    const payload={format:'ai-daily-vocabulary',version:1,exported_at:new Date().toISOString(),words:saved};
    const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'});
    const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;
    a.download=`ai-daily-vocabulary-${hkDate()}.json`;document.body.append(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  async function importVocabulary(file) {
    if(!file || file.size>2_000_000){toast('檔案不可超過 2 MB。');return;}
    try {
      const data=JSON.parse(await file.text());
      if(data?.format!=='ai-daily-vocabulary' || data.version!==1 || !data.words || Array.isArray(data.words) || typeof data.words!=='object') throw new Error('invalid file');
      const rows=Object.entries(data.words);if(rows.length>5000) throw new Error('too many words');
      let accepted=0;
      for(const [key,value] of rows){
        if(!/^[a-z][a-z'\-]{0,45}$/.test(key) || !value || typeof value!=='object' || Array.isArray(value)) continue;
        const translation=String(value.translation||'').slice(0,300);
        const phonetic=String(value.phonetic||'').slice(0,90);
        if(!has(saved,key)){saved[key]={translation,phonetic,savedAt:typeof value.savedAt==='string'?value.savedAt.slice(0,45):new Date().toISOString(),reviewLevel:Math.max(0,Math.min(4,Number(value.reviewLevel)||0)),nextReview:/^\d{4}-\d{2}-\d{2}$/.test(value.nextReview||'')?value.nextReview:''};accepted++;}
      }
      safeStorage.set(SAVED_KEY,saved);updateSavedCount();renderWords();toast(`匯入完成，新增 ${accepted} 個生字。`);
    } catch {toast('無法匯入：請使用本網站匯出的 JSON 備份。');}
  }
  function setView(view){
    state.view=view;['today','archive','words'].forEach(name=>{ $('view-'+name).classList.toggle('hidden',name!==view); const b=document.querySelector(`[data-view="${name}"]`); b.classList.toggle('selected',name===view); if(name===view)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current'); });
    $('crumb').textContent=({today:'DAILY BRIEFING',archive:'PAST EDITIONS',words:'VOCABULARY BANK'})[view];
    if(view==='archive')renderArchive();if(view==='words')renderWords();closePopover();window.scrollTo({top:0,behavior:'smooth'});
  }
  async function loadReport(date){
    const serial=++requestSerial;
    if(!/^\d{4}-\d{2}-\d{2}$/.test(date))return;
    try{
      const response=await fetch(`./reports/${date}.json?rev=${Date.now()}`,{cache:'no-store'});
      if(!response.ok) throw new Error('missing report');
      const r=await response.json();if(!isValidReport(r,date))throw new Error('invalid report');
      if(serial!==requestSerial)return;
      state.report=r;state.showTranslation=false;renderReport();setView('today');
    }catch{if(serial===requestSerial)toast('載入報告失敗，請檢查網絡或離線快取。');}
  }
  function isValidReport(r, date){
    return r && r.date===date && ['demo','editorial','source_digest','reading_feature'].includes(r.mode) &&
      Array.isArray(r.essay) && r.essay.length>0 && r.essay.length<=15 &&
      r.essay.every(p=>typeof p==='string'&&p.length<=5000) &&
      Array.isArray(r.stories) && r.stories.length<=8 &&
      r.stories.every(s=>typeof s==='object' && ['http:','https:'].includes((()=>{try{return new URL(s.url).protocol;}catch{return ''}})()));
  }
  function showConnectivity(failed=false){
    const el=$('connection-alert');
    if(!el)return;
    const offline=failed||!navigator.onLine;
    el.classList.toggle('hidden',!offline);
    el.textContent=!navigator.onLine?'目前離線。若已快取文章仍可閱讀；最新新聞及線上查字暫不可用。':'無法確認最新資料，可能正在使用瀏覽器快取。';
  }
  function exportBriefing(){
    if(!state.report)return;
    const r=state.report;
    const sources=(r.stories||[]).map(s=>`[${s.id}] ${s.publisher} · ${s.title}\n${s.url}`).join('\n\n');
    const text=[r.headline,`${r.date} | ${r.mode} | ${r.word_count||0} words`,r.editorial_notice||'',...r.essay,...(r.mode==='reading_feature'?['EVERGREEN EDUCATIONAL READING — NOT TODAY\'S NEWS']:['ORIGINAL SOURCES',sources,'Generated from RSS descriptions; verify claims against originals.'])].join('\n\n');
    const blob=new Blob([text],{type:'text/plain;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download=`ai-daily-${r.date}.txt`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1200);
  }
  function updateZoomNotice(){
    const notice=$('zoom-notice');
    if(!notice)return;
    const zoomed=Number(window.visualViewport?.scale||1)>1.07;
    notice.classList.toggle('hidden',!zoomed||notice.dataset.dismissed==='yes');
  }
  function resetReadingLayout(){
    // Reset presentation, never remove vocabulary, answers or progress.
    state.fontScale=0;safeStorage.set('ai-daily-font-scale',0);
    focusMode=false;document.body.classList.remove('focus-mode','tools-expanded');
    $('focus-toggle').setAttribute('aria-pressed','false');
    $('focus-toggle').textContent='專注閱讀';
    $('tools-toggle').setAttribute('aria-expanded','false');
    $('tools-toggle').textContent='更多閱讀工具 ▾';
    closePopover(false);renderReader();renderReaderNavigator();updateZoomNotice();scrollToReadingTarget($('reader'));
    toast(Number(window.visualViewport?.scale||1)>1.07?
      '字體及版面已重設。Safari 頁面仍被手勢放大，請用雙指縮小至正常比例。':
      '字體及版面已重設；生字、答案和閱讀進度均已保留。');
  }
  async function reloadLatestWebsite(){
    const button=$('reload-latest');button.disabled=true;button.textContent='更新中…';
    try{
      const registration=await navigator.serviceWorker?.getRegistration();
      if(registration){
        await registration.update();
        if(registration.waiting) registration.waiting.postMessage({type:'SKIP_WAITING'});
      }
    }catch{/* A fresh navigation is still attempted. */}
    const url=new URL(location.href);
    url.searchParams.set('fresh',Date.now().toString(36));
    location.assign(url.toString());
  }
  let lastObservedHKDay=hkDate(),lastRefreshAt=0,latestRefreshBusy=false;
  async function refreshLatestReport({force=false,quiet=false}={}){
    if(latestRefreshBusy)return;
    latestRefreshBusy=true;
    const button=$('refresh-schedule');
    button.disabled=true;button.setAttribute('aria-busy','true');
    try{
      const res=await fetch('./reports/index.json?check='+Date.now(),{cache:'no-store'});
      if(!res.ok)throw Error('HTTP '+res.status);
      const idx=await res.json();
      if(!Array.isArray(idx)||!idx.length||!/^\d{4}-\d{2}-\d{2}$/.test(idx[0].date||''))throw Error('日期索引無效');
      const next=idx[0].date;
      const top=idx[0];
      const changed=next!==state.report?.date ||
        Number(top.word_count||0)!==Number(state.report?.word_count||0) ||
        String(top.headline||'')!==String(state.report?.headline||'') ||
        Number(top.stories||0)!==Number(state.report?.stories?.length||0) ||
        (Boolean(top.updated_at) && String(top.updated_at)!==String(state.report?.updated_at||''));
      state.index=idx;
      if(changed||force)await loadReport(next);
      if(!changed&&!force)renderFreshness();
      $('today-label').textContent=new Date().toLocaleDateString('en-GB',{timeZone:'Asia/Hong_Kong',day:'numeric',month:'short',year:'numeric'});
      await Promise.allSettled([renderPipelineStatus(),renderScheduleHealth()]);
      if(!quiet)toast(changed?'新一期文章已載入，學習紀錄保留。':'已重新核對今日報告與排程。');
    }catch(error){
      if(!quiet)toast('更新失敗：'+String(error.message||error).slice(0,50));
      await renderScheduleHealth();
    }finally{latestRefreshBusy=false;button.disabled=false;button.removeAttribute('aria-busy');}
  }
  function checkDailyReset(force=false){
    if(document.visibilityState==='hidden')return;
    const current=hkDate(),changed=current!==lastObservedHKDay;
    if(changed)lastObservedHKDay=current;
    if(!changed&&!force&&Date.now()-lastRefreshAt<300000)return;
    lastRefreshAt=Date.now();
    refreshLatestReport({quiet:true});
  }
  function initEvents(){
    document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));
    $('reader').addEventListener('click',e=>{const t=e.target.closest('button.word');if(t)showLookup(t.textContent,t);});
    $('translate-toggle').addEventListener('click',toggleWholeTranslation);
    $('reset-reading').addEventListener('click',resetReadingLayout);
    $('reload-latest').addEventListener('click',reloadLatestWebsite);
    $('zoom-dismiss')?.addEventListener('click',()=>{const el=$('zoom-notice');el.dataset.dismissed='yes';el.classList.add('hidden');});
    window.visualViewport?.addEventListener('resize',updateZoomNotice,{passive:true});
    window.addEventListener('orientationchange',()=>setTimeout(updateZoomNotice,250),{passive:true});
    document.querySelectorAll('.jump-to-reader,.skip-link').forEach(link=>link.addEventListener('click',event=>{
      event.preventDefault();
      if(state.view!=='today')setView('today');
      scrollToReadingTarget($('reader'));
    }));
    $('tools-toggle').addEventListener('click',()=>{const expanded=document.body.classList.toggle('tools-expanded');$('tools-toggle').setAttribute('aria-expanded',String(expanded));$('tools-toggle').textContent=expanded?'收起其他閱讀工具 ▴':'更多閱讀工具 ▾';});
    $('focus-toggle').addEventListener('click',()=>{focusMode=!focusMode;document.body.classList.toggle('focus-mode',focusMode);$('focus-toggle').setAttribute('aria-pressed',String(focusMode));$('focus-toggle').textContent=focusMode?'離開專注模式':'專注閱讀';});
    $('reading-speed').addEventListener('click',()=>{const speeds=[90,115,145];state.readingWpm=speeds[(speeds.indexOf(state.readingWpm)+1)%speeds.length];safeStorage.set('ai-daily-reading-wpm',state.readingWpm);renderReadingEstimate();});
    $('font-button').addEventListener('click',()=>{state.fontScale=(state.fontScale+1)%3;safeStorage.set('ai-daily-font-scale',state.fontScale);renderReader();toast(['標準字體','放大字體','特大字體'][state.fontScale]);});
    $('theme-button').addEventListener('click',()=>{document.documentElement.classList.toggle('light');safeStorage.set('ai-daily-light',document.documentElement.classList.contains('light'));});
    $('pop-close').addEventListener('click',()=>closePopover(true));
    $('resume-reading').addEventListener('click',()=>{const amount=Number(progressRecords[state.report?.date]||0);const card=document.querySelector('.briefing-card');const target=card.getBoundingClientRect().top+scrollY+(card.offsetHeight-innerHeight)*(amount/100);window.scrollTo({top:Math.max(0,target),behavior:'smooth'});});
    $('export-report').addEventListener('click',exportBriefing);
    $('print-report').addEventListener('click',()=>window.print());
    $('lookup-online').addEventListener('click',queryRemoteDictionary);
    $('mark-read').addEventListener('click',()=>{
      if(!state.report)return;
      const date=state.report.date;
      if(readRecords[date])delete readRecords[date];else readRecords[date]=new Date().toISOString();
      safeStorage.set(READ_KEY,readRecords);readingStatus();refreshDashboard();
      toast(readRecords[date]?'已記錄這一篇的閱讀完成狀態。':'已取消完成標記。');
    });
    $('word-search').addEventListener('input',e=>{wordFilter=e.target.value.trim().toLowerCase();renderWords();});
    $('archive-search').addEventListener('input',e=>{archiveFilter=e.target.value.toLowerCase().trim();renderArchive();});
    $('archive-mode').addEventListener('change',e=>{archiveMode=e.target.value;renderArchive();});
    $('export-vocab').addEventListener('click',exportVocabulary);
    $('import-vocab').addEventListener('click',()=>$('import-file').click());
    $('export-all').addEventListener('click',exportAll);
    $('import-all').addEventListener('click',()=>$('import-all-file').click());
    $('import-all-file').addEventListener('change',async e=>{await importAll(e.target.files?.[0]);e.target.value='';});
    $('import-file').addEventListener('change',async e=>{await importVocabulary(e.target.files?.[0]);e.target.value='';});
    $('start-review').addEventListener('click',()=>{reviewQueue=dueWords().sort();reviewPosition=0;if(!reviewQueue.length){toast('目前沒有需要複習的生字。');return;}renderReview();$('review-panel').scrollIntoView({behavior:'smooth',block:'center'});});
    $('review-show').addEventListener('click',()=>{$('review-back').classList.remove('hidden');$('review-show').classList.add('hidden');['review-again','review-hard','review-remember','review-easy'].forEach(id=>$(id).classList.remove('hidden'));});
    $('review-again').addEventListener('click',()=>finishReview('again'));
    $('review-hard').addEventListener('click',()=>finishReview('hard'));
    $('review-remember').addEventListener('click',()=>finishReview('good'));
    $('review-easy').addEventListener('click',()=>finishReview('easy'));
    $('review-stop').addEventListener('click',()=>{reviewQueue=[];renderReview();});
    $('speak-button').addEventListener('click',()=>{if(!('speechSynthesis' in window)){toast('此瀏覽器不支援語音播放。');return;} speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(state.lookup);u.lang='en-GB';u.rate=.88;speechSynthesis.speak(u);});
    $('save-word').addEventListener('click',()=>{
      const key=wordKey(state.lookup);if(!key)return;
      if(has(saved,key)){toast('此單字已儲存。');return;}
      const entry=localMeaning(key)||state.dictCache.get(key)||{};
      saved[key]={translation:entry.translation||'',phonetic:entry.phonetic||'',savedAt:new Date().toISOString()};
      safeStorage.set(SAVED_KEY,saved);updateSavedCount();$('save-word').textContent='✓ 已儲存';toast('生字已儲存在此瀏覽器。');
    });
    window.addEventListener('scroll',()=>{updateProgress(true);if(Date.now()-(state.lookupOpened||0)>350)closePopover();},{passive:true});
    window.addEventListener('resize',()=>closePopover());
    window.addEventListener('pagehide',()=>safeStorage.set(PROGRESS_KEY,progressRecords));
    window.addEventListener('pageshow',event=>{if(event.persisted)checkDailyReset(true);});
    document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')checkDailyReset();});
    window.addEventListener('offline',()=>showConnectivity());
    window.addEventListener('online',()=>showConnectivity());
    document.addEventListener('keydown',e=>{if(e.key==='Escape')closePopover(true);if(e.key==='/'&&state.view==='words'&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();$('word-search').focus();}});
    document.addEventListener('pointerdown',e=>{if(!$('dictionary-popover').contains(e.target) && !e.target.closest('.word'))closePopover();});
  }
  async function init(){
    if(safeStorage.get('ai-daily-light',false))document.documentElement.classList.add('light');
    state.fontScale=Math.max(0,Math.min(2,Number(safeStorage.get('ai-daily-font-scale',0))||0));
    const storedSpeed=Number(safeStorage.get('ai-daily-reading-wpm',115));state.readingWpm=[90,115,145].includes(storedSpeed)?storedSpeed:115;
    renderReadingEstimate();
    showConnectivity();
    $('today-label').textContent=new Date().toLocaleDateString('en-GB',{timeZone:'Asia/Hong_Kong',day:'numeric',month:'short',year:'numeric'});
    updateSavedCount();refreshDashboard();initEvents();renderPipelineStatus();
    await preloadOfflineGlossary();
    $('refresh-schedule').addEventListener('click',()=>refreshLatestReport({force:true}));
    if('serviceWorker' in navigator && location.protocol==='https:'){navigator.serviceWorker.register('./sw.js').catch(()=>{});}
    try{
      const response=await fetch('./reports/index.json',{cache:'no-store'});if(!response.ok)throw new Error('No report index');
      state.index=await response.json();if(!Array.isArray(state.index)||state.index.length>400||!state.index.every(x=>/^\d{4}-\d{2}-\d{2}$/.test(x.date||'')))throw new Error('Invalid index');
      if(!state.index.length)throw new Error('Empty index');
      await loadReport(state.index[0].date);
      renderScheduleHealth();
    }catch{
      showConnectivity(true);
      $('status-banner').textContent='無法取得最新報告';$('report-headline').textContent='報告正在準備中';
      $('reader').textContent='目前沒有可載入的文章。可能尚未首次發布，也可能是離線而未快取。請重新連線或檢查 GitHub Actions。';
    }
  }
  init();
})();

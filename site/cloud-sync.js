/* V1 cloud vocabulary sync. Optional Supabase endpoint; no credentials in source.
 * Account isolation is enforced by database RLS, NOT by this browser script.
 * Offline changes are append-only events with UUIDs and idempotent uploads.
 */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  if(root)root.AIDailyCloud=api;
})(typeof window!=='undefined'?window:null,function(){
  'use strict';
  const SESSION='ai-daily-cloud-session-v1';
  const WORD=/^[a-z][a-z'-]{0,45}$/;
  const EVENT_LIMIT=50000;
  function cleanWord(word){return typeof word==='string'&&WORD.test(word)?word:null;}
  function cleanPayload(value){
    if(!value||typeof value!=='object'||Array.isArray(value))return null;
    return {
      translation:String(value.translation||'').slice(0,300),
      phonetic:String(value.phonetic||'').slice(0,90),
      savedAt:String(value.savedAt||'').slice(0,45),
      reviewLevel:Math.max(0,Math.min(6,Number(value.reviewLevel)||0)),
      nextReview:/^\d{4}-\d{2}-\d{2}$/.test(value.nextReview||'')?value.nextReview:'',
      lastReviewed:String(value.lastReviewed||'').slice(0,45)
    };
  }
  function orderedEvents(events){
    return events.slice().sort((a,b)=>
      String(a.created_at||'').localeCompare(String(b.created_at||''))||
      String(a.event_id||'').localeCompare(String(b.event_id||'')));
  }
  function replay(events){
    const words=Object.create(null);
    for(const event of orderedEvents(events)){
      const key=cleanWord(event.word);
      if(!key)continue;
      if(event.deleted){delete words[key];continue;}
      const value=cleanPayload(event.payload);
      if(value)words[key]=value;
    }
    return words;
  }
  function combineWithPending(events,pending){
    // Uploading wins only after server acknowledgement. Until then, local
    // operations take precedence even if another device synchronizes.
    const result=replay(events);
    for(const p of pending){
      const key=cleanWord(p.word);
      if(!key)continue;
      if(p.deleted)delete result[key];
      else{const value=cleanPayload(p.payload);if(value)result[key]=value;}
    }
    return result;
  }
  function statusError(err){return err instanceof Error?err.message:String(err);}
  class Client{
    constructor(options){
      this.options=options;this.config=null;this.session=null;this.user=null;
      this.pending=[];this.busy=null;this.retryTimer=null;
    }
    get active(){return Boolean(this.user&&this.session);}
    setStatus(message){this.options.onStatus?.(message);}
    key(){return 'ai-daily-cloud-pending-v1-'+this.user.id;}
    getPending(){
      try{const data=JSON.parse(localStorage.getItem(this.key())||'[]');return Array.isArray(data)?data:[];}
      catch{return [];}
    }
    savePending(){localStorage.setItem(this.key(),JSON.stringify(this.pending));}
    configValid(value){
      if(!value||typeof value!=='object')return false;
      try{
        const u=new URL(value.supabase_url);
        return u.protocol==='https:'&&/^[a-z0-9-]+\.supabase\.co$/.test(u.hostname)
          &&typeof value.anon_key==='string'&&value.anon_key.length>20;
      }catch{return false;}
    }
    async init(){
      let config;
      try{
        const response=await fetch('./cloud-config.json',{cache:'no-store'});
        if(response.ok)config=await response.json();
      }catch{/* Reading is still usable offline without cloud settings. */}
      if(!this.configValid(config)){
        this.setStatus('尚未啟用雲端同步；本機生字與備份功能維持正常。');
        this.options.onAvailable?.(false);
        return false;
      }
      this.config={url:config.supabase_url.replace(/\/+$/,''),key:config.anon_key};
      this.options.onAvailable?.(true);
      const hash=new URLSearchParams(location.hash.replace(/^#/,''));
      if(hash.get('error_description')){
        this.setStatus('電郵登入失敗：'+hash.get('error_description').slice(0,120));
        history.replaceState(null,'',location.pathname+location.search);
      }
      if(hash.has('access_token')&&hash.has('refresh_token')){
        this.session={
          access_token:hash.get('access_token'),
          refresh_token:hash.get('refresh_token'),
          expires_at:Date.now()+Number(hash.get('expires_in')||3600)*1000
        };
        // Tokens must never remain in browser history or be sent as referers.
        history.replaceState(null,'',location.pathname+location.search);
        this.storeSession();
      }else{
        try{this.session=JSON.parse(localStorage.getItem(SESSION)||'null');}
        catch{this.session=null;}
      }
      if(this.session){
        try{
          await this.ensureToken();
          const profile=await this.request('GET','/auth/v1/user');
          if(!/^[0-9a-f-]{36}$/i.test(profile.id||''))throw new Error('登入帳戶無效');
          this.user={id:profile.id,email:profile.email||''};
          this.pending=this.getPending();
          this.options.onSignedIn?.(this.user);
          this.setStatus('已登入，正在同步生字…');
          if(navigator.onLine)await this.sync();
          else this.setStatus('目前離線；已保留此裝置的待同步生字。');
        }catch(err){
          if(/401|403|登入已失效/.test(statusError(err))){
            this.session=null;this.user=null;localStorage.removeItem(SESSION);
            this.options.onSignedOut?.();
          }
          this.setStatus('同步暫時無法連線：'+statusError(err));
        }
      }else this.setStatus('尚未登入；輸入電郵即可在各裝置同步生字。');
      return true;
    }
    storeSession(){localStorage.setItem(SESSION,JSON.stringify(this.session));}
    async request(method,path,body,allowRefresh=true){
      if(!this.config)throw new Error('未設定雲端服務');
      const headers={'apikey':this.config.key,'Content-Type':'application/json'};
      if(this.session?.access_token)headers.Authorization='Bearer '+this.session.access_token;
      const response=await fetch(this.config.url+path,{method,headers,
        ...(body===undefined?{}:{body:JSON.stringify(body)}),
        cache:'no-store'});
      if(response.status===401&&allowRefresh&&this.session?.refresh_token){
        await this.refresh();return this.request(method,path,body,false);
      }
      if(!response.ok){
        const error=await response.json().catch(()=>({}));
        throw new Error((error.msg||error.message||error.error_description||('HTTP '+response.status)).slice(0,150));
      }
      if(response.status===204||response.status===205)return null;
      const bodyText=await response.text();return bodyText?JSON.parse(bodyText):null;
    }
    async refresh(){
      if(!this.session?.refresh_token)throw new Error('登入已失效');
      const r=await fetch(this.config.url+'/auth/v1/token?grant_type=refresh_token',{
        method:'POST',headers:{apikey:this.config.key,'Content-Type':'application/json'},
        body:JSON.stringify({refresh_token:this.session.refresh_token}),cache:'no-store'
      });
      if(!r.ok)throw new Error(r.status===401?'登入已失效':'無法更新登入狀態');
      const value=await r.json();
      this.session={access_token:value.access_token,refresh_token:value.refresh_token,
        expires_at:Date.now()+Number(value.expires_in||3600)*1000};
      this.storeSession();
    }
    async ensureToken(){
      if(!this.session)throw new Error('尚未登入');
      if(this.session.expires_at<Date.now()+90000)await this.refresh();
    }
    async sendEmail(email){
      if(!this.config)throw new Error('雲端同步尚未啟用');
      if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)||email.length>254)
        throw new Error('請輸入有效的電郵地址');
      const target=location.origin+location.pathname;
      const response=await fetch(this.config.url+'/auth/v1/otp?redirect_to='+encodeURIComponent(target),{
        method:'POST',headers:{apikey:this.config.key,'Content-Type':'application/json'},
        body:JSON.stringify({email,create_user:true}),cache:'no-store'
      });
      if(!response.ok){
        const error=await response.json().catch(()=>({}));
        throw new Error(error.msg||error.message||'寄送登入電郵失敗');
      }
      this.setStatus('登入連結已寄出。請於同一裝置開啟電郵，然後返回網站。');
    }
    record(word,payload,deleted=false){
      if(!this.active)return false;
      const key=cleanWord(word);
      if(!key)throw new Error('生字格式不正確');
      const entry={event_id:crypto.randomUUID(),word:key,deleted:Boolean(deleted),
        payload:deleted?{}:cleanPayload(payload)};
      if(!deleted&&!entry.payload)throw new Error('生字資料不正確');
      this.pending.push(entry);this.savePending();
      this.setStatus('變更已在此裝置保存，等待雲端同步。');
      this.schedule();return true;
    }
    schedule(){
      clearTimeout(this.retryTimer);
      if(!this.active||!navigator.onLine)return;
      this.retryTimer=setTimeout(()=>this.sync().catch(()=>{}),1000);
    }
    async sync(){
      if(!this.active||!navigator.onLine)return;
      if(this.busy)return this.busy;
      this.busy=(async()=>{
        await this.ensureToken();
        const snapshot=this.pending.slice();
        for(let i=0;i<snapshot.length;i+=100){
          const batch=snapshot.slice(i,i+100).map(e=>({...e,user_id:this.user.id}));
          await this.request('POST','/rest/v1/vocabulary_events?on_conflict=event_id',batch);
          const acknowledged=new Set(batch.map(e=>e.event_id));
          this.pending=this.pending.filter(e=>!acknowledged.has(e.event_id));
          this.savePending();
        }
        const events=[];
        for(let offset=0;offset<EVENT_LIMIT;offset+=1000){
          const path='/rest/v1/vocabulary_events?select=event_id,word,payload,deleted,created_at'
            +'&order=created_at.asc,event_id.asc&limit=1000&offset='+offset;
          const page=await this.request('GET',path);
          if(!Array.isArray(page))throw new Error('雲端返回的資料格式不正確');
          events.push(...page);
          if(page.length<1000)break;
          if(events.length>=EVENT_LIMIT)throw new Error('同步紀錄已達安全上限，請先匯出備份並聯絡管理員');
        }
        const words=combineWithPending(events,this.pending);
        this.options.onWords?.(words);
        this.setStatus('雲端同步完成 · '+Object.keys(words).length+' 個生字');
        if(this.pending.length)this.schedule();
      })().catch(err=>{
        this.setStatus('雲端未能同步；變更仍保存在此裝置。'+statusError(err));
        throw err;
      }).finally(()=>{this.busy=null;});
      return this.busy;
    }
    async logout(){
      if(this.session){
        try{await this.request('POST','/auth/v1/logout',{});}catch{/* Local logout always works offline. */}
      }
      this.session=null;this.user=null;this.pending=[];
      localStorage.removeItem(SESSION);
      this.options.onSignedOut?.();
      this.setStatus('已登出雲端帳戶；原有本機生字仍保留。');
    }
  }
  return {Client,cleanWord,cleanPayload,replay,combineWithPending};
});
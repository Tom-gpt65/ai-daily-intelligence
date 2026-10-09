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
  const CONFIG_CACHE='ai-daily-cloud-public-config-v1';
  const USER_CACHE='ai-daily-cloud-verified-user-v1';
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
      (Number(a.batch_order)||0)-(Number(b.batch_order)||0)||
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
        if(u.protocol!=='https:'||!/^[a-z0-9-]+\.supabase\.co$/.test(u.hostname))return false;
        const key=value.anon_key;
        if(typeof key!=='string'||key.length<21||/sb_secret_|service_role/i.test(key))return false;
        // Legacy anon JWTs are public, but a service_role JWT grants privileged
        // access. Never accept one in the world-readable Pages configuration.
        if(key.split('.').length===3){
          try{
            const part=key.split('.')[1].replace(/-/g,'+').replace(/_/g,'/');
            const claims=JSON.parse(atob(part));
            return claims.role==='anon';
          }catch{return false;}
        }
        return /^sb_publishable_/.test(key);
      }catch{return false;}
    }
    async init(){
      let config;
      try{
        const response=await fetch('./cloud-config.json',{cache:'no-store'});
        if(response.ok)config=await response.json();
      }catch{/* Reading is still usable offline without cloud settings. */}
      if(this.configValid(config)){
        try{localStorage.setItem(CONFIG_CACHE,JSON.stringify(config));}catch{/* restricted storage */}
      }else if(!navigator.onLine){
        try{config=JSON.parse(localStorage.getItem(CONFIG_CACHE)||'null');}catch{config=null;}
      }else{
        // An intentionally disabled cloud config must disable sync, even if
        // this device previously cached another project's public settings.
        try{localStorage.removeItem(CONFIG_CACHE);}catch{/* restricted storage */}
      }
      if(!this.configValid(config)){
        this.options.onSignedOut?.();
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
        localStorage.removeItem(USER_CACHE); // A new magic-link identity must be verified first.
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
        let cached;
        try{cached=JSON.parse(localStorage.getItem(USER_CACHE)||'null');}
        catch{cached=null;}
        try{
          if(!navigator.onLine)throw new Error('目前離線');
          await this.ensureToken();
          const profile=await this.request('GET','/auth/v1/user');
          if(!/^[0-9a-f-]{36}$/i.test(profile.id||''))throw new Error('登入帳戶無效');
          this.user={id:profile.id,email:profile.email||''};
          localStorage.setItem(USER_CACHE,JSON.stringify(this.user));
          this.pending=this.getPending();
          this.options.onSignedIn?.(this.user);
          this.setStatus('已登入，正在同步生字…');
          await this.sync();
        }catch(err){
          if(/401|403|登入已失效/.test(statusError(err))){
            this.session=null;this.user=null;localStorage.removeItem(SESSION);
            localStorage.removeItem(USER_CACHE);
            this.options.onSignedOut?.();
            this.setStatus('登入已失效，請重新寄送登入連結。');
          }else if(cached&&/^[0-9a-f-]{36}$/i.test(cached.id||'')&&this.session){
            // Previously verified account can continue saving offline.
            // Cloud RLS validates credentials before any future upload.
            this.user=cached;this.pending=this.getPending();
            this.options.onSignedIn?.(this.user);
            this.setStatus('離線或伺服器暫時無法連線；此裝置變更會保留並等待同步。');
          }else this.setStatus('暫時無法確認登入：'+statusError(err));
        }
      }else {this.options.onSignedOut?.();this.setStatus('尚未登入；輸入電郵即可在各裝置同步生字。');}
      return true;
    }
    storeSession(){localStorage.setItem(SESSION,JSON.stringify(this.session));}
    async request(method,path,body,allowRefresh=true){
      if(!this.config)throw new Error('未設定雲端服務');
      const headers={'apikey':this.config.key,'Content-Type':'application/json'};
      if(this.session?.access_token)headers.Authorization='Bearer '+this.session.access_token;
      if(method==='POST'&&path.startsWith('/rest/v1/vocabulary_events'))
        headers.Prefer='resolution=ignore-duplicates,return=minimal';
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
    async signInWithPassword(email,password){
      if(!this.config)throw new Error('雲端同步尚未啟用');
      if(typeof email!=='string'||!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(email)||email.length>254)
        throw new Error('請輸入有效的電郵地址');
      if(typeof password!=='string'||password.length<8||password.length>256)
        throw new Error('請輸入至少 8 字元的帳戶密碼');
      if(!navigator.onLine)throw new Error('目前離線，首次登入需要網絡');
      // Password goes only to Supabase Auth via HTTPS. Never cache or log it.
      const controller=new AbortController();
      const timeout=setTimeout(()=>controller.abort(),20000);
      let response,profile;
      try{
        response=await fetch(this.config.url+'/auth/v1/token?grant_type=password',{
          method:'POST',headers:{apikey:this.config.key,'Content-Type':'application/json'},
          body:JSON.stringify({email,password}),cache:'no-store',signal:controller.signal
        });
        if(!response.ok){
          const error=await response.json().catch(()=>({}));
          const message=String(error.msg||error.message||error.error_description||'');
          if(response.status===429)throw new Error('登入嘗試過於頻繁，請稍後再試。');
          if(/not.confirmed|email.not.confirmed/i.test(message))
            throw new Error('此帳戶尚未確認。請在 Supabase Users 後台建立或確認帳戶。');
          if(response.status===400||response.status===401||response.status===422)
            throw new Error('電郵或密碼不正確，或帳戶尚未建立。請在 Supabase Authentication → Users 核對。');
          throw new Error('Supabase 登入失敗（HTTP '+response.status+'）');
        }
        const tokens=await response.json();
        if(typeof tokens.access_token!=='string'||!tokens.access_token||
           typeof tokens.refresh_token!=='string'||!tokens.refresh_token)
          throw new Error('Supabase 未返回有效的登入憑證');
        // A successful password check is not enough to switch device vocabulary:
        // first verify the exact identity attached to the returned access token.
        const who=await fetch(this.config.url+'/auth/v1/user',{
          method:'GET',headers:{apikey:this.config.key,
            Authorization:'Bearer '+tokens.access_token},
          cache:'no-store',signal:controller.signal
        });
        if(!who.ok)throw new Error('登入後無法核實帳戶身分（HTTP '+who.status+'）');
        profile=await who.json();
        if(!/^[0-9a-f-]{36}$/i.test(profile?.id||'')||typeof profile.email!=='string')
          throw new Error('Supabase 返回的使用者資料無效');
        const nextSession={
          access_token:tokens.access_token,
          refresh_token:tokens.refresh_token,
          expires_at:Date.now()+Number(tokens.expires_in||3600)*1000
        };
        // Do not switch to an unverified user or lose another account's queue.
        this.session=nextSession;
        this.user={id:profile.id,email:profile.email};
        this.storeSession();
        localStorage.setItem(USER_CACHE,JSON.stringify(this.user));
        this.pending=this.getPending();
        this.options.onSignedIn?.(this.user);
        this.setStatus('已使用密碼登入，正在同步生字…');
        // A temporary sync error must not discard the verified login.
        try{await this.sync();}catch{/* sync() already reports an error */}
        return this.user;
      }catch(error){
        if(error?.name==='AbortError')
          throw new Error('登入連線逾時（20 秒），請檢查網絡後再試。');
        if(error instanceof TypeError)
          throw new Error('無法連接 Supabase 登入服務，請檢查網絡。');
        throw error;
      }finally{clearTimeout(timeout);}
    }
    async sendEmail(email){
      if(!this.config)throw new Error('雲端同步尚未啟用');
      if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)||email.length>254)
        throw new Error('請輸入有效的電郵地址');
      const target=location.origin+location.pathname;
      const controller=new AbortController();
      const timeout=setTimeout(()=>controller.abort(),20000);
      let response;
      try{
        response=await fetch(this.config.url+'/auth/v1/otp?redirect_to='+encodeURIComponent(target),{
          method:'POST',headers:{apikey:this.config.key,'Content-Type':'application/json'},
          body:JSON.stringify({email,create_user:true}),cache:'no-store',signal:controller.signal
        });
      }catch(error){
        if(error?.name==='AbortError')throw new Error('連線等待超過 20 秒。請檢查網絡後再試，避免短時間內重複寄送。');
        throw new Error('無法連接 Supabase 郵件服務。請確認已連線，或稍後重試。');
      }finally{clearTimeout(timeout);}
      if(!response.ok){
        const error=await response.json().catch(()=>({}));
        const code=String(error.error_code||error.code||'');
        const message=String(error.msg||error.message||error.error_description||'');
        if(code==='email_address_not_authorized'||/email address not authorized/i.test(message))
          throw new Error('此電郵不屬於 Supabase 組織團隊。預設郵件服務只可寄給團隊成員；其他電郵須先設定自訂 SMTP。');
        if(response.status===429||/rate.limit|too many requests/i.test(message))
          throw new Error('已達電郵發送次數限制。請稍後再試，避免連續按下寄送。');
        throw new Error((message||'寄送登入電郵失敗（HTTP '+response.status+'）').slice(0,180));
      }
      this.setStatus('登入請求已被 Supabase 接受。請檢查收件匣及垃圾郵件，並於同一裝置開啟登入連結。');
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
          // PostgreSQL now() gives all rows in one request the same timestamp.
          // Explicit batch order makes consecutive edits deterministic.
          const batch=snapshot.slice(i,i+100).map((e,batch_order)=>({...e,user_id:this.user.id,batch_order}));
          await this.request('POST','/rest/v1/vocabulary_events?on_conflict=event_id',batch);
          const acknowledged=new Set(batch.map(e=>e.event_id));
          this.pending=this.pending.filter(e=>!acknowledged.has(e.event_id));
          this.savePending();
        }
        const events=[];
        for(let offset=0;offset<EVENT_LIMIT;offset+=1000){
          const path='/rest/v1/vocabulary_events?select=event_id,word,payload,deleted,created_at,batch_order'
            +'&order=created_at.asc,batch_order.asc,event_id.asc&limit=1000&offset='+offset;
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
      localStorage.removeItem(USER_CACHE);
      this.options.onSignedOut?.();
      this.setStatus('已登出雲端帳戶；原有本機生字仍保留。');
    }
  }
  return {Client,cleanWord,cleanPayload,replay,combineWithPending};
});
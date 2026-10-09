# V1 跨裝置生字同步啟用指引（Supabase）

**網站已備妥跨裝置同步程式；但在完成以下設定前，雲端功能會顯示「尚未啟用」，生字仍只存在瀏覽器。** GitHub Pages 是靜態網站，不包含身份驗證或私人資料庫，不能單靠 GitHub Pages 直接保存每位用戶的私人生字。

## 1. 建立安全的 Supabase 專案

1. 在 [Supabase](https://supabase.com/dashboard) 建立新專案，記下 **Project URL**（格式 `https://xxxx.supabase.co`）與可公開的 **anon／publishable key**。
2. 打開 **SQL Editor**，完整執行 [SUPABASE_VOCABULARY.sql](SUPABASE_VOCABULARY.sql)（已執行舊版 SQL 的專案亦須重新執行以補上 `batch_order` 欄位及欄位權限）。確認 `public.vocabulary_events` 已啟用 Row Level Security（RLS），SELECT／INSERT 僅容許登入的 `auth.uid() = user_id`；`created_at` 只能由資料庫產生，瀏覽器不能自行指定。
3. 到 **Authentication → Providers → Email** 啟用 Email OTP／Magic Link。到 **Authentication → URL Configuration**：
   - **Site URL**：`https://tom-gpt65.github.io/ai-daily-intelligence/`
   - **Redirect URLs**：加入相同完整網址；測試本機可另外加入 `http://127.0.0.1:8765/`。
4. Email 登入需要可送信的郵件服務；Supabase 預設郵件服務有配額及限制，大量使用應設定 SMTP。若無收到郵件，查看 Supabase Auth Logs／Email provider。

## 2. 在 GitHub Pages 發布公開配置

編輯倉庫 `site/cloud-config.json`：

```json
{
  "supabase_url": "https://YOUR_PROJECT_REF.supabase.co",
  "anon_key": "YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY"
}
```

只有這個 **公開／匿名 key** 可以放在靜態網站！**禁止**貼 `service_role`、`sb_secret_`、資料庫密碼、JWT 私鑰、管理員帳戶資料。這些密鑰能繞過或擴大伺服器權限，絕不能放進公開 GitHub 倉庫。

此 JSON 是公開設定，不是登入憑證。安全性完全依賴伺服器真正啟用的 Supabase Auth 與 SQL Row Level Security。編輯並提交後等待 GitHub Pages 完成部署；首頁仍叫 **V1**，並非 V2。

## 3. 在 iPhone、iPad、電腦使用同一帳戶

1. 在 iPhone 開啟網站 → **我的生字庫 → 跨裝置同步** → 輸入你的電郵，點選「寄送安全登入連結」。
2. 在該裝置打開收到的電郵連結；登入成功後返回生字庫，應顯示「已連接帳戶」。
3. **首次登入且已有舊生字時**，按「將原有本機生字加入雲端」。這是明確的使用者選擇；網站不會偷偷上傳未登入前的資料。雲端同名詞語保留雲端版本，本機原始資料會留作備份。
4. 在 iPad 和電腦，以**同一電郵**登入，點「立即同步」後應看到相同生字。
5. 離線時先前登入的裝置可以繼續儲存／複習，事件會留在該裝置排隊；回復網絡後按「立即同步」，或待網站自動同步。
6. 首次使用、轉換帳戶、修改裝置前，建議先按「匯出生字庫」和「備份全部學習進度」保存 JSON 檔。

## 4. 避免混淆及已知限制

- **只同步生字庫和生字複習資料**。閱讀位置、文章已讀日期、閱讀理解答案仍留在每部裝置的本機，未加入雲端同步。
- 對同一個字有衝突修改時，依資料庫賦予的接收時間排序；同一次請求批量上傳、具有相同資料庫時間的多項操作，再按 `batch_order` 保留該批次中的修改先後次序。離線裝置最後補傳的改動可能覆蓋已上傳的修改。跨裝置幾乎同時提交時仍採用伺服器時間與排序後備規則，**不是跨裝置語義合併**。所有歷史事件仍儲存在擁有人帳戶下，可以由管理員協助復原。
- 刪除生字會新增刪除事件，讓另一部裝置亦刪除。**舊資料事件仍存於雲端事件紀錄**；要永久刪除所有私人雲端詞庫資料，須執行已登入身份的擁有人 DELETE 操作或由專案管理員協助刪除。不能以「刪除生字」當成完全抹除雲端歷史。
- 使用者的 access／refresh session token 儲存在各裝置此網站的 localStorage。共用裝置請登出；清空瀏覽器資料會清除本機未同步佇列。單一裝置的瀏覽器隱私設定可能阻止持久保存。
- 需要網絡才能首次登入、完成郵件驗證，以及提交雲端變更。**目前未有真實 Supabase 帳戶測試**時，不能宣稱已達成實際跨裝置同步。
- 本服務沒有私人伺服器，依賴 Supabase 免費／付費方案的可用性、速率和儲存限制。此方案使用可重播事件紀錄；長期大量使用需增加安全的歸檔／壓縮程序。
- GitHub Pages 公開專案的 `cloud-config.json` 不涉及用戶生字或密碼；**切勿把匯出之 JSON 生字備份上傳到公開倉庫**。

## 5. 驗收測試

- `node tests/cloud_sync_test.js`：詞語格式、離線變更、刪除事件、冪等重播及同時間批次排序。
- `node --check site/cloud-sync.js` 及 `node --check site/app.js`：JavaScript 語法。
- 原有 Chromium／WebKit 瀏覽器測試：未連雲端時不妨礙閱讀、生字儲存、測驗及舊 JSON 備份。
- **真實環境驗收**：在兩個不同裝置登入相同電郵，測試新增、刪除、複習評級、離線修改後重連，以及不同電郵之間的資料隔離。**未完成之前不能視為整個功能正式啟用。**

官方參考：[Supabase Passwordless Sign-In](https://supabase.com/docs/guides/auth/auth-email-passwordless) · [Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)。

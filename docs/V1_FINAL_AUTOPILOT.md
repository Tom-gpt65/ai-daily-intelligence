# AI Daily Intelligence V1｜終極穩定與低維護運行手冊

**目標：** 保留已驗收的 V1 iPad／iPhone PWA，不再增加大量功能。依靠既有每日出稿、備援、補救及讀取驗證，最後補上每日跨服務健康巡檢、真正離線實測、個人資料備份驗證，以及可執行的故障處理步驟。

本方案不購買服務、不新增個人資料託管、不索取帳戶密碼、不修改 Supabase RLS、也不重設本機學習紀錄。

## 1. 已有的全自動機制（香港時間）

| 時間 | 工作 | 實際保障與限制 |
|---|---|---|
| **06:25** | **`first-attempt-canary.yml`**：只讀模擬「07:05 已有備援 → 07:40 首次新聞更新」及未來五個日期，使用正式 `validate_site` 驗證，提前揭露會令首次出稿阻塞的固定程式問題；GitHub 排程仍可能延遲 |
| 07:05 | `early-reading.yml` | 優先備好當日超過 1,000 字、附離線詞義的教育文章；備援不冒充當日新聞 |
| 07:40 | `daily.yml` | 有足夠 RSS 來源才嘗試當日新聞版；免費本地模型／排程不是零故障 |
| 08:05、09:17、13:17 | `audit.yml` | 核對公開文章、更新日期、發稿狀況；排程未成功須誠實標示 |
| 08:20、09:40、10:25、12:25 | `recovery.yml` | 有條件檢查缺稿並按既有次數限制啟動補救；不無限重試 |
| **14:35** | **`v1-final-autopilot.yml`** | **獨立檢查公開 PWA 所有核心檔案、當日閱讀、獨立安裝 manifest、Supabase Auth 和匿名詞庫隔離** |

GitHub 定時執行不是絕對準點；平台可能延遲、略過排程或在服務故障時連檢查也無法執行。不能承諾永久零維護。

## 2. 最終新增安全網

### A. 只讀每日健康巡檢

GitHub → Repository → **Actions → V1 final autopilot — public PWA and cloud safety**。

- 網站 HTML、App JS、CSS、字典、Service Worker、App 圖示、manifest 須可公開載入。
- 當日 `reports/index.json` 指向香港當日文章，文章須通過已有的 `assess_public` 審核：日期、長度、非示範、來源標示、可點擊字詞有繁體中文意思等。
- Public Cloud Config 必須與 Repository 中版本一致，而且只可含 **Publishable Key**（不得包含秘密金鑰）。
- Supabase Auth 公開 Health Endpoint 必須 HTTP 200。
- 匿名存取 `vocabulary_events` 必須被 HTTP 401/403 拒絕；如果回傳 HTTP 200，**也必須是空陣列**，任何可讀取紀錄皆屬安全故障。
- 只顯示健康狀態，不列印 Publishable Key、登入 token、用戶電郵、個人生字或密碼。
- **故障時 GitHub Actions 以紅色 Fail 呈現**，不自動刪除詞庫、刪除帳戶、更改資料庫政策或覆蓋閱讀文章。

限制：此公開監測只驗證外部服務可用及基本權限，**不能代替真實已登入帳戶的跨裝置同步測試**；對於 Supabase 內部非公開錯誤、Apple 系統更新、實際視覺舒適度或文章事實真確性均不作百分百保證。

### B. 真正斷網的 PWA 驗收

`tests/browser_pwa_offline_final.js` 在 Chromium 與 WebKit，分別使用手機及平板寬度測試：

1. 完整安裝、啟動和取得 Service Worker 控制權。
2. 確認安裝後已有 HTML、離線詞典和最新文章的快取。
3. **直接停止測試網站伺服器，證實未快取的網絡請求失敗**，驗證已開啟的 App 仍能使用本機生字／字義，並嘗試讀取 CacheStorage 裏的 HTML、當日文章與離線詞典。**測試環境無法在每個引擎證實 CacheStorage 可讀或離線重新導航，這部分會標示「未驗證」而非成功**；必須在 iPad/iPhone 真機另行驗收。
4. 確認本機生字在網站無法連線和恢復連線後保留；真機關閉再開啟的情況仍須手動驗證。
5. **下載真正的「備份全部學習進度」JSON**，確認生字／閱讀／答題欄位齊全；模擬登入 token 不可被匯出。
6. 顯示 V1，不能因更新把正式版本自動變成 V2。

這是瀏覽器自動化驗證，不等於直接讀取擁有者私人 iOS App 資料，也不能代替 iPad／iPhone 真機最終驗收。

### C. 個人學習資料保護

雲端只同步生字及複習欄位；**閱讀進度、理解題答案及書面答案留在裝置本機**。清除 App／Safari 資料、移除 App、重設裝置，均可能導致只存在該裝置的學習資料流失。

建議每月一次、以及換手機前，在**每一部有獨立學習記錄的裝置**進行：

1. 開啟 **AI Daily → 我的生字庫 → 備份全部學習進度**。
2. 確認檔案已儲存至私人「檔案」或 iCloud Drive 位置，名稱為 `ai-daily-learning-backup-YYYY-MM-DD.json`。
3. 不要上傳 GitHub、公開論壇或將個人資料備份貼到聊天視窗。
4. 如需復原，先備份目前資料，才按 **還原學習進度**。此動作為合併還原；登入雲端後可能連帶觸發生字同步。
5. 已知只有「匯出生字庫」不包含全部閱讀／答題資料；須使用 **備份全部學習進度**。

**完全無人操作的伺服器備份並不可行**：GitHub 不應取得 iOS 本機學習資料，也沒有你的私人 Supabase 管理員金鑰。此專案採用明確手動、裝置內下載的安全策略。

## 3. 故障分流：只處理紅色問題

| GitHub Actions 失敗訊息 | 應檢查 | 明確禁止 |
|---|---|---|
| Public daily article stale/invalid | Actions → Early daily English reading、AI Daily Intelligence、Automatic missed-edition recovery；檢視最新完成工作 | 不可偽造當日新聞、不直接刪除報告 |
| Public PWA asset unavailable | Actions → AI Daily Intelligence → 查看 Pages 部署；重試一次正常部署 | 不要清除個人生字及閱讀資料 |
| Supabase Auth health unavailable | Supabase Dashboard → Project / Auth 狀況，等候平台恢復或查看官方事故 | 不要重設 Supabase Project 或刪除 User ID |
| SECURITY: anonymous vocabulary data unexpectedly readable | 立即檢查 Supabase Table Editor → RLS 是否開啟及 `public.vocabulary_events` 政策 | 不可暫時關閉 RLS 來「恢復同步」 |
| PWA offline fail | 先連網啟動 App，完成閱讀後再測試離線；檢查 Service Worker 安裝及 Pages | 不要未備份就卸載 App |
| 健康檢查根本沒有執行 | GitHub Actions 排程權限、Repository 活動與 GitHub 平台狀況 | 不要假定「沒有紅燈＝當天已驗證」 |

Github Actions 的通知取決於你的 GitHub 通知設定與平台能否運行；如需收到失敗郵件，於 GitHub **Settings → Notifications → Actions** 核對相應通知選項。這套專案沒有加入需要額外金鑰的 Telegram、電郵發送服務或外部監測供應商。

## 4. 最後封版規則（仍是 V1）

- 此後不因每日新聞更新、GitHub Actions 排程、錯誤修正或微調配色自動升級 V1。
- 不主動修改已通過驗收的帳戶、詞庫格式、RLS、PWA 資料來源或 Supabase 專案。
- 如發現風險：先建分支、PR、Python／Node 與 Chromium／WebKit 測試，經過正式 Pages 驗證再合併。
- **不把任何登入憑證、Supabase Secret Key、個人備份或私人生字放入 GitHub。**
- 每月一個手動學習資料備份，是使用者仍需做的最小日常維護。

## 5. 2026-10-10 新聞更新阻塞：根因及永久工程防護

**事件：** 香港時間 2026-10-10 的 07:47 定時出稿，以及 08:47、09:54 兩次補救出稿皆在 `Run pre-publication checks` 失敗，並未進入 RSS 資料收集。與此同時，07:05 的教育閱讀備援成功發布並顯示於 V1。故「App 有今日閱讀文章」不等於「今日新聞更新成功」。

**直接根因：** 舊 `tests/test_v6.py::test_public_article_is_educational_not_certified` 錯誤地要求最新文章必須為 `source_digest` 或 `editorial`，並要求非空 `stories`。實際產品早在 07:05 先刊出合法的 `reading_feature`：它必須沒有當日新聞來源，並清楚註明並非即時新聞。測試將正確備援視為故障，`daily.yml` 又把**整套單元測試**放在 RSS 前當硬門檻，造成每次補救均重複進入同一失敗點。

**為甚麼昨天通過，今天卻失敗：** 10 月 9 日當時最新文章是有五條來源的 `source_digest`，因此舊測試碰巧通過。10 月 10 日先發布合法的 `reading_feature` 後，同一套測試因最新資料型別改變而失敗。先前封版並未在每個 CI 分支都固定模擬「早上先備援、然後嘗試新聞」的跨日序列；這是測試覆蓋缺口，不是 iPad PWA 或個人登入故障。

**已加入的持久修正：**

- `tests/test_v6.py` 明確允許已標示為「Not today's AI news」、零來源、擁有七道非官方理解題及完整離線字義的合法備援，亦嚴格要求新聞模式有至少三條可追溯來源，防止把備援偽裝成新聞。
- `tests/browser_regression_v7.js` 同時修正了另一個跨日測試假設：有來源的新聞版需要多個新聞章節捷徑，但教育備援只有「引言／結論」兩個快捷鍵、下拉選單仍提供每一段；因此不得把合法備援誤判為「手機導覽消失」。
- `site/app.js` 的每日狀態列現會**同時說明「教育文章已提供」與「新聞更新工作失敗」**，不會像 10 月 10 日的舊版本一樣，在讀到 `reading_feature` 時立即顯示綠色狀態並跳過 GitHub 排程失敗檢查。新增 Chromium／WebKit 狀態測試，分開模擬「新聞正常／失敗」與「教育備援存在／不存在」。
- `test_morning_fallback_does_not_block_later_news_generation` 使用不同日期的**合成備援**，即使 PR 當時最新文章是新聞，仍會測試下一日先有備援的情境；另有反例測試阻止不當來源標籤。
- `daily.yml`／`early-reading.yml` 的執行期門檻只使用 `scripts/validate_site.py` 驗證真實公開文章與本機 JS 語法。**所有單元及瀏覽器回歸測試繼續於 PR／CI 執行**，但不再讓測試程式對動態最新文章的假設阻斷每日發布。
- `test_daily_guarantee.py` 定期檢查上述 CI／發布職責分離，並要求 PR CI 在文章產生程式及早上 workflow 異動時啟動，防止往後把完整單元測試重新放回每天出稿的前置硬門檻。

**首次執行防護增強（後續補丁）：** 在早上 06:25 新增獨立、不讀私隱資料、不發布網頁的 `first-attempt-canary.yml`；它將當日及未來多日的合法教育備援暫存在臨時檔案中，再使用與正式發布**完全相同**的 `scripts/validate_site.py` 驗證，避免下一次「昨天是新聞、今天先有備援」才首次暴露不相容。07:05 建立文章之後**再次驗證最新實際產物**，以免不合格備援進入第一次正式新聞更新。CI 也會要求該 Canary 通過才可合併修改。

`daily.yml` 現將**可選的 OpenCC 安裝、RSS 擷取、新聞稿產生**視為可降級步驟；即使遇到短暫 PyPI／來源／模型錯誤，仍會執行具權限限制的備援步驟，**但發布前必須再次通過完整實際文章檢驗及「必須是香港今天日期」的斷言**，防止以報錯為由放行舊稿、不完整字典或虛構新聞。失敗來源會以 GitHub `::warning` 記錄，不會被偽稱為已發布即時新聞。

此防護可減少「第一次出稿就被早可發現的程式或短暫網絡問題中斷」，**但不能保證 RSS 一定有可靠新聞、GitHub 100% 準點運行或第三方永不失效**。首次可成功發布今日教育閱讀，與首次即能發布有來源的即時新聞，是兩個不同的驗收標準。

**不會更改：** Supabase、User ID、RLS、個人生字、PWA 離線快取、已發表文章歷史及 V1 版本名稱。

**限制與應對：** 此修正能防止「合法備援令舊單元測試中止新聞發布」這一類故障再發生；仍不能保證外部 RSS、免費本地模型、GitHub 排程或 Pages 100% 成功。若更新後仍只有 `reading_feature`，須查本日新聞 RSS 是否達發布品質門檻，而不能自動宣稱整個服務故障。歷史紅色 GitHub Actions 不會因程式修正而消失；應查看新提交的工作結果與最新公開內容。

## 6. 簡明驗收定義

只有 GitHub 上的 Python／Node、Chromium／WebKit、公開網站部署以及每日監測工作都成功時，才可以說 **「自動化技術驗收通過」**；此處的離線自動驗收特指 CacheStorage 在服務中斷期間可讀取，**不代表已驗證 iOS 冷啟動離線導航**。

另外，**真正的 iPad/iPhone App 安裝、個人登入和跨裝置使用狀況**須根據使用者親自驗收，不可以把模擬服務結果當成正式登入；個人舒適度、教育文章學術正確性及 GitHub 平台未來長期可用性，均不屬於能被一次測試永久保證的事項。

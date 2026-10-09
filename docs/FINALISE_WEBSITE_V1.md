# AI Daily Intelligence V1 — GitHub 正式啟用與驗收清單

> 本文件只記錄設定和驗收方法。**每日文章、測試、補檔不得因此增加網站版本號**。首頁及 Service Worker 保持 V1；只有另行批准正式功能發布時才增加版本號。

## A. 必須保留的 GitHub 設定

1. 進入 `Tom-gpt65/ai-daily-intelligence`。確認儲存庫不是 Archived，預設分支為 `main`。免費 GitHub Pages 用戶須確保符合公開儲存庫的方案要求。
2. 進入 **Settings → Pages → Build and deployment → Source**，確認選擇 **GitHub Actions**，不要改用 `Deploy from a branch`；網站已由 `daily.yml` 及 `early-reading.yml` 使用 `actions/deploy-pages` 發布 `site/`。
3. 進入 **Settings → Actions → General**，確認允許執行 Actions、允許倉庫使用所需官方 Actions；核實預設 `GITHUB_TOKEN` 權限及組織政策不會阻止工作流程明確要求的 `contents: write`、`pages: write`、`id-token: write` 或補救工作的 `actions: write`。
4. 進入 **Settings → Environments → github-pages**。建議把部署分支限制於 `main`；請勿新增未滿足的人工審批規則，以免早上排程被卡住。
5. 進入 **Actions**，確認下列工作流程沒有被停用；請勿刪除 `.github/workflows/`、`scripts/`、`site/` 和 `tests/`。

## B. 香港時間每日運作

| 預定時間 | 工作流程 | 作用 |
|---|---|---|
| 07:05 | `early-reading.yml` | 先發布千字、七題、逐詞離線字義的備援英文閱讀 |
| 07:40 | `daily.yml` | RSS 有足夠來源及可核實資料時，以真實新聞更新當日文章 |
| 08:05、09:17、13:17 | `audit.yml` | 獨立檢查公開網站、文章日期與完整性 |
| 08:20、09:40、10:25、12:25 | `recovery.yml` | 缺稿才啟動最多兩次額外生成 |
| 15:05 | `longform-validation.yml` | 不部署網站；驗證全部保留的文章、字典及七題 |
| 15:20 | `browser-v7.yml` | 不部署網站；以 Chromium／WebKit 檢查閱讀及學習操作 |

> GitHub 的排程可能延遲或被省略。時間是計劃，不是服務等級承諾。首次驗證隔天排程需待明天實際執行。

## C. 完成網站的人工驗收步驟

1. 以 **Safari** 開啟 https://tom-gpt65.github.io/ai-daily-intelligence/ ，確認首頁顯示 **V1**、文章能載入、英文行寬不超出螢幕。
2. 開啟「過往報告」，選擇 **2026-10-08**，確認是明確標示的補建教材。核對 **2026-10-09** 正式新聞文章仍可讀。
3. 在文章點選一般英文詞語及變化詞（例如 `concerns`），確認可離線顯示繁體中文詞義；斷線前須先在同一瀏覽器完成首次載入／快取。詞義未經逐字人工語境核證。
4. 儲存一個生字、回答一道選擇題、輸入一道書面題，重新整理網站後確認內容仍存在；測試閱讀進度、章節跳轉、字體縮放及「重設版面」。可由「我的生字庫」備份生字或整個學習紀錄。
5. 網頁的逐段／全文機器翻譯屬外部第三方服務；即使基本連線測試成功，也不能保證每次均能翻譯。失效時先檢查網絡、供應商額度與瀏覽器 CORS。
6. 到 **Actions** 檢查 `Early daily English reading safety net`、`AI Daily Intelligence — free daily briefing`、`Independent daily publication audit`、`Validate long-form reading`、`iPhone browser regression`。若出現紅色失敗，打開失敗 Job 和 Logs，按原因處理，不要直接冒稱文章已成功發布。
7. 建議在 GitHub 個人通知設定啟用 Actions 失敗通知，並連續觀察至少 **七個香港日**，記錄每日的日期、文章模式、公開可讀時間及失敗次數。單次測試成功不能證明將來永不缺稿。

## D. 日常維護與版本規則

- **每日生成、重試、歷史補檔及測試不應變更網站的 V1 版本號**；Git Commit SHA 可以每天改變，這與正式前端版本不同。
- 新聞不足時，只允許明確標示為**非即時新聞**的原創英文延伸閱讀；不可將備援內容偽裝成當日新聞。
- 不要清空 `localStorage`、修改既有學習紀錄鍵名或取消下載備份功能。
- 新功能發版需先通過 Python 單元測試、完整歷史文章、逐詞離線字典、Chromium／WebKit 操作測試及公開 Pages 檢查，再由你決定是否升級前端版本。
- GitHub Docs 指出：公開倉庫連續 60 日沒有活動，排程工作可能被自動停用；定期核對 Actions 是否仍啟用。
- 可選擇在 GitHub 建立 Release／Tag `V1` 作正式標記（尚未自動建立 Tag），但**不要把一般出稿或功能測試當成新版本發布**。

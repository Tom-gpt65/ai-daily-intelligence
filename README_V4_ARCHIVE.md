# AI Daily Intelligence v4 — Ultimate Free Reading Studio

**繁體中文 · 互動式 AI 新聞網站 · 免費開源語言模型 · 無 OpenAI API · 香港時間每日 08:00 預定觸發**

本版本由 v3 延伸，完成 **48 項可追查的程式優化**。所有功能由靜態網頁、Python RSS 收集程式、Ollama 本地模型及 GitHub Actions/Pages 組成。

> **本版本尚未替你上傳到 GitHub、未部署到正式網站。** 自帶的 `site/reports/2026-10-09.json` 是虛構練習文章，**不是 2026 年 10 月 9 日的實際新聞**。首次成功執行定時更新之後，才會有真實 RSS 摘要。
>
> **不保證 100% 完美：** GitHub 免費排程可能延遲，免費模型可能拒絕生成或產生錯誤。HKDSE 5★ 是英文學習目標，不是已獲認證的自動難度級別。

## 一、主要功能

| 功能 | v4 狀態 |
|---|---|
| 每日新聞 | 從 6 個免付費 RSS 來源讀取最近 36 小時 AI 內容，並行抓取、去重、分類、記錄失敗情況 |
| 英文文章 | 免費開源模型目標撰寫 450–600 字高階英語，失敗時顯示來源摘要，不虛構長文 |
| 來源透明 | 保留新聞來源、原始連結、發布時間與來源類別；模型文本必須標引用途 |
| 一鍵查字 | 點文章單字顯示繁中詞義、詞性、IPA（有資料時）、英文解說及當前句子的語境 |
| 學習進度 | 已讀標記、生字庫、四級間隔複習、實際閱讀連續日數、閱讀進度續讀 |
| 導出 | 全部學習紀錄 JSON 備份、v3 舊版匯入相容、單篇英文文章 TXT 匯出、列印排版 |
| UX | 手機／電腦、深淺模式、三級字體、鍵盤操作、專注模式、無障礙和離線提示 |
| PWA | 可安裝、快取瀏覽過的報告；離線版本不被視作已更新新聞 |
| 狀態診斷 | 區分「新聞不足」、「RSS 全部失敗」、「部分 RSS 失敗」和「48 小時未更新」 |

全部 48 項具體實作及程式對照見 [`OPTIMISATION_48_ROUNDS.md`](OPTIMISATION_48_ROUNDS.md)。

## 二、立即預覽，不必部署

建議使用 Python 3.11+。解壓後在專案根目錄執行：

```bash
python scripts/preview.py
```

根據終端機顯示的本機網址打開網站。示範報告為**虛構英文練習文章**；可以測試查字、讀書紀錄、備份和版面，但不代表已完成新聞自動更新。

![桌面真實模擬畫面](docs/desktop-browser-smoke.png)
![手機真實模擬畫面](docs/mobile-browser-smoke.png)

## 三、免費部署到 GitHub Pages

1. 在 GitHub 建立一個 **Public 公開儲存庫**。不要上傳個人資料、API 金鑰或個人生字備份。
2. 把本 ZIP **解壓後的全部內部檔案**上傳到儲存庫根目錄。確保隱藏目錄 `.github/workflows/daily.yml` 也已上傳。
3. 到儲存庫 **Settings → Pages → Build and deployment → Source**，選擇 **GitHub Actions**。
4. 如有需要，到 **Settings → Actions → General → Workflow permissions** 開啟 **Read and write permissions**，方便每日把報告提交回儲存庫。
5. 前往 **Actions → Daily AI intelligence v4 (zero paid API) → Run workflow**，第一次先手動執行。
6. 檢查各步驟，包括 `Regression checks`、`Collect and assess fresh RSS first`、`Build daily report`、`Publish diagnostics` 和 `Publish website`。如失敗，查看該步日誌；不要假設網站已上線。
7. 待動作成功完成，在 **Settings → Pages** 查看 GitHub 實際提供的網站連結。之後每日香港時間 08:00 預定開始自動檢查。

GitHub 官方參考：<https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onschedule>、<https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site>。

**重要：** 08:00 是排程預定觸發時間，不代表 08:00 前報告一定已完成。免費公開儲存庫的排程可能延遲、跳過或在長時間無活動後停用。`ollama pull phi3:mini` 下載模型及生成英文亦可能逾時或因資源不足而失敗。若模型失敗，系統使用有清楚標註的來源摘要模式。

## 四、本機驗證及使用方式

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/validate_site.py
node --check site/app.js
node --check site/sw.js
```

如果已安裝 Chromium 及 Playwright，可執行選用的瀏覽器模擬測試：

```bash
python tests/browser_smoke_optional.py
```

若要本機抓取真正 RSS 而不啟動 Ollama：

```bash
python scripts/build.py --prefetch
```

預抓資料保存在 `.cache/candidates.json`。如沒有足夠新聞，工作流程不會為了湊數而造出今天的長文。

## 五、操作說明

- **每日簡報：** 先瀏覽新聞卡，再閱讀英文文章；點字查繁中釋義。字典不保證每字都有翻譯。
- **字體調整：** 按 `AA` 可循環切換三級字體。點 `接續閱讀` 回到該篇之前保存的閱讀進度。
- **生字學習：** 在查字視窗選 `儲存生字`；到生字庫複習或匯出進度。
- **完整備份：** 生字、已讀、思考題及閱讀進度匯成 JSON，跨裝置由你手動還原。
- **其他閱讀方式：** 按 `匯出文章` 將當篇下載為 TXT；按 `列印` 可以選擇在瀏覽器儲存為 PDF。
- **離線：** 首次成功快取才可離線閱讀相關報告。離線或網站更新延遲時均會顯示警告。

## 六、數據和私隱

- 網站毋須用戶帳戶、沒有追蹤或分析工具，不需要付費 API 金鑰。
- 個人生字、文章進度及英文答案只保存在使用裝置的 localStorage；清除瀏覽器資料會遺失紀錄，請定期自行匯出。
- **只有讀者主動選擇**第三方免費翻譯按鈕，才會將當前單一英文單字送到 MyMemory；網絡服務可能無法使用或譯錯。私人學習進度不會自動傳送到網站或 GitHub。
- 正式網站及其日報對所有人公開；請不要將個人備份、身分資料或憑證上傳到公開 GitHub 儲存庫。
- 來源文本只是 RSS 標題及摘要，不等於實際文章全文的查證。系統的結構檢查不是事實核查。

## 七、已驗證與尚未驗證

**已驗證：** 54 項 Python 離線單元測試、靜態網站檔案檢查、JavaScript 語法，以及 Chromium 1440px 和 390px 的模擬瀏覽器互動測試。

**尚待驗證：** 真正雲端長期執行、RSS 來源可用性、Ollama 模型在 GitHub Runner 上的成功率、真實產出是否符合 5 分鐘／DSE 5★ 目標、完整機器中文譯文的語義準確度。

本版本不使用 OpenAI API，也不能由本 ChatGPT 對話自動充當每天的 RSS 後台；真正自動工作的是 GitHub Actions。

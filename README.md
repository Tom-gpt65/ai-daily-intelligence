# AI Daily Intelligence v5 — Evidence First

**繁體中文 · 免費新聞來源與免費開源本地模型 · 只用互動網站 · 每日香港時間 08:00 預定觸發**

v5 專注改善三個目標：**內容價值、準確性、計算及閱讀效率**。不需要 OpenAI API，不會寄送電子郵件，也不會把個人學習紀錄送到伺服器。

> **狀態：未部署。** `site/reports/2026-10-09.json` 是明確標示的虛構練習教材，並不是當天的真實 AI 新聞。只有部署、首次抓取 RSS 並成功執行排程後，才可產出每日真實新聞。
>
> 本程式無法保證任何新聞或生成內容 100% 正確。「HKDSE 5★」是學習目標，不是模型已獲認證的英文難度。程式結構檢查不能取代專業事實核查。

## v5 實質改善

| 項目 | v5 做法 | 用戶價值與限制 |
|---|---|---|
| 新聞選擇 | 重要事件字詞、標題具體程度、有限時效性加權、適度主題分散及低質量噱頭降權 | 比純粹追求最新更有條理；評分仍只是啟發式 |
| 事件去重 | 不合併明確不同機構或不同模型版本的新聞 | 減低誤把相近標題合為同一事件的風險 |
| 多來源 | 同一事件保留其他媒體原文連結，網站清楚標示來源數量 | 來源重複**不代表事實已被獨立核實** |
| 來源安全 | 過濾帶有典型指令注入語句的 RSS 標題及摘要 | 減低不可信新聞資料對生成器的干擾，但非完整防護 |
| 生成品質 | 來源太薄弱時不勉強生成五分鐘長文；過濾部分可疑引用、非英文輸出及長引述 | 不造出看似完整卻缺乏支持的內容；可能當天只能看簡報 |
| 處理效率 | **預設只生成英文**；完整中文翻譯是可選的第二次本地模型工作 | 省去預設第二次高成本 CPU 推論；單字翻譯仍可用 |
| 診斷 | 記錄 RSS 收集、模型生成、全文翻譯與詞典處理時間 | 有助在真實部署後找出瓶頸，非事先保證加速 |
| 英文練習 | 問題綁定當天至少一則真實來源 ID | 降低每日無關泛問的情況 |
| 閱讀體驗 | 90／115／145 字每分鐘三段估算 | 按自身程度估計閱讀時間，並不改變文章 |
| 查字語境 | 修正同一段多次出現相同單字時，錯誤指向第一次出現的情況 | 按實際點擊位置顯示句子 |
| 前端驗證 | 新增來源群組、同一事件其他報道及安全連結 | 一次查閱不同來源，不假裝已完成獨立核實 |

技術詳情、設計取捨及測試位置：[`OPTIMISATION_V5.md`](OPTIMISATION_V5.md)。v4 改良歷史仍保存在 `OPTIMISATION_48_ROUNDS.md`。

## 本機預覽

要求 Python 3.11+，可先**不用安裝模型**而試用虛構練習文章：

```bash
python scripts/preview.py
```

根據終端機顯示的 `http://localhost:...` 網址開啟。這只是本機網站，不是實時更新。

## 零付費部署至 GitHub

1. 在 GitHub 建立 **Public** Repository，並把 ZIP 解壓後的**內部檔案**上傳到根目錄，包含 `.github/workflows/daily.yml`。
2. 在 Repository 的 **Settings → Pages → Build and deployment → Source** 選擇 **GitHub Actions**。
3. 確認 GitHub Actions 有 `contents: write` 所需權限，以保存每日報告。
4. 前往 **Actions → Daily AI intelligence v5 (zero paid API) → Run workflow**，手動執行一次並查看完整日誌。
5. 檢查模型安裝、RSS 預抓取、模型生成、網站發布及 Diagnostics。成功後，從 **Settings → Pages** 取得實際網址。

**重要限制：** GitHub 排程可指定 `Asia/Hong_Kong`，但預定 08:00 不保證準時完成；RSS 可能失敗，免費公開 Repository 的排程長期無活動時可能停用。下載 Ollama 與模型也可能在免費 Runner 超時或資源不足。只有在真實部署後才可確認實際成功率。公開網站上的日報任何人都能讀取，請勿將個人備份或秘密金鑰上傳到 Repository。

## 模型與翻譯的速度選擇

- **預設 `TRANSLATE_ENABLED=0`：** 不呼叫第二次本地模型生成中文全文，保留文章內一鍵生字翻譯（離線預載詞典）。
- 如果願意增加本地模型執行時間，將 workflow 的 `TRANSLATE_ENABLED` 改成 `'1'`，可以**嘗試**生成全文繁體中文翻譯；翻譯不一定能通過格式檢查，也不保證語義完全準確。
- 模型透過 `OLLAMA_MODEL` 指定，預設 `phi3:mini`。模型更換前應先量度 CPU／RAM、英文品質及失敗率；沒有任何模型被保證最好。
- 免費詞典可能缺詞、詞性錯誤或不符合當前語境；不要把點擊查字結果視作已核證的學術翻譯。

## 測試

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/validate_site.py
node --check site/app.js
node --check site/sw.js
# 系統有 Chromium 與 Playwright 時：
python tests/browser_smoke_optional.py
```

測試以離線模擬資料為主，不會發送任何付費 AI API 請求，也**不能證明**外部 RSS 或正式 Ollama 工作流每天可靠。更多舊版操作細節見 [`README_V4_ARCHIVE.md`](README_V4_ARCHIVE.md)。

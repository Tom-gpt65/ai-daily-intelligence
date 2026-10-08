# AI Daily Intelligence v4 — 48 項連續優化紀錄

> 這 48 項是基於 v3 程式實際落地、可以追查對應程式位置的改動，並非 48 次獨立雲端發布，也非保證系統無錯。

| 輪次 | 範疇 | 已落實的具體改善 | 主要程式位置 |
|---|---|---|---|
| 01 | 新聞擷取 | RSS 請求可重試，減少暫時網絡故障造成的空白日 | `scripts/build.py · fetch_feed` |
| 02 | 新聞擷取 | 每份 RSS 設定 2 MB 上限，避免異常大型回應 | `scripts/build.py · MAX_FEED_BYTES` |
| 03 | 新聞擷取 | 拒絕不是 XML 形態的 HTTP 回應 | `scripts/build.py · fetch_feed` |
| 04 | 新聞安全 | 拒絕帶有 DOCTYPE 的 XML，降低非預期實體處理風險 | `scripts/build.py · feed_entries` |
| 05 | 新聞安全 | 拒絕 ENTITY 宣告，限制不受信任的 RSS XML | `scripts/build.py · feed_entries` |
| 06 | 新聞格式 | 優先使用 Atom rel=alternate 真正文章連結 | `scripts/build.py · feed_entries` |
| 07 | 新聞格式 | 正確抽取 Atom/RSS 含內嵌元素的文字摘要 | `scripts/build.py · feed_entries` |
| 08 | 新聞效率 | RSS 解析上限 100 篇，再以來源最新 35 篇為選取範圍 | `scripts/build.py · feed_entries / collect` |
| 09 | 新聞效率 | 最多 5 個來源同時抓取，避免逐一等待所有網絡逾時 | `scripts/build.py · ThreadPoolExecutor` |
| 10 | 內容穩定 | 同分新聞以來源和標題作穩定次序排序 | `scripts/build.py · collect` |
| 11 | 內容廣度 | 不為湊夠新聞數量而破壞單一媒體上限 | `scripts/build.py · collect` |
| 12 | 數據品質 | 收集成功／失敗來源、閱讀條目及可用新聞數 | `scripts/build.py · diagnostics` |
| 13 | 事實透明 | 來源全部無法連接時標示 feed_error，而非「沒有新聞」 | `scripts/build.py · build_live / main` |
| 14 | 事實透明 | 來源部分失敗時在網頁顯示新聞可能不完整 | `site/app.js · renderPipelineStatus` |
| 15 | 資料驗證 | 預抓新聞快照的 ID、URL、日期、數量及長度須通過檢查 | `scripts/build.py · validate_candidate_sources` |
| 16 | 日期準確 | 無時區標記的日期不擅自推斷為 UTC | `scripts/build.py · parse_entry_date` |
| 17 | 英文品質 | 限制每段最大長度，減少難以閱讀的單段堆疊 | `scripts/build.py · review_model_text` |
| 18 | 英文品質 | 拒絕不具足夠內容的短段落 | `scripts/build.py · review_model_text` |
| 19 | 來源支持 | 要求中段段落附來源標記，而非只在文尾羅列 | `scripts/build.py · review_model_text` |
| 20 | 英文品質 | 拒絕完全相同的重複段落 | `scripts/build.py · review_model_text` |
| 21 | 來源安全 | 拒絕模型輸出意外外部連結與廣告式字句 | `scripts/build.py · review_model_text` |
| 22 | 來源追蹤 | 真實報告建立後，從歷史索引排除虛構示範條目 | `scripts/build.py · put_report` |
| 23 | 翻譯效率 | 整篇翻譯由多次請求改為一次 JSON 陣列請求 | `scripts/build.py · translate_essay` |
| 24 | 翻譯誠實 | 翻譯段數不符時不顯示可能錯位的譯文 | `scripts/build.py · translate_essay` |
| 25 | 發布診斷 | GitHub Actions 顯示每次新聞讀取的健康狀態 | `daily.yml · GITHUB_STEP_SUMMARY` |
| 26 | 部署相容 | 更新 GitHub Pages 上傳工作流程至 v4 動作 | `daily.yml · upload-pages-artifact@v4` |
| 27 | 發布品質 | 部署前驗證網站引用檔案、重複 ID、文章索引與資產 | `scripts/validate_site.py` |
| 28 | 資料安全 | 瀏覽器讀取文章時驗證日期、模式及資料欄位結構 | `site/app.js · isValidReport` |
| 29 | 競態處理 | 快速切換歷史文章時避免較慢的舊請求覆蓋新文章 | `site/app.js · requestSerial` |
| 30 | 讀取效率 | 英文單字改用集中式點擊事件，減少大量獨立事件監聽 | `site/app.js · reader click` |
| 31 | 學習品質 | 跨文章查字時優先重用個人生字庫的已知中文詞義 | `site/app.js · showLookup` |
| 32 | 閱讀理解 | 詞義彈窗以目前英文句子作語境，而非任意截取段首 | `site/app.js · sentenceOf` |
| 33 | 無障礙 | 按 Escape 關閉查字並把焦點還原至原始單字 | `site/app.js · closePopover` |
| 34 | 閱讀體驗 | 字級改為三段循環選擇，並記住裝置設定 | `site/app.js · fontScale；site/v4.css` |
| 35 | 持續學習 | 記錄文章閱讀進度，提供接續上次閱讀按鈕 | `site/app.js · progressRecords / renderResume` |
| 36 | 學習數據 | 連續閱讀日數按實際完成日期而非報告出版日期計算 | `site/app.js · readingStreak` |
| 37 | 內容攜帶 | 可將當篇英文、說明與原始資料來源下載為文字檔 | `site/app.js · exportBriefing` |
| 38 | 閱讀媒介 | 提供適合列印及儲存 PDF 的文章專用版面 | `site/v4.css · @media print` |
| 39 | 跨版本相容 | 完整版資料備份可匯入 v3 與 v4 格式 | `site/app.js · importAll` |
| 40 | 離線可信 | 顯示離線／無法確認最新資料提示，不偽裝即時更新 | `site/app.js · showConnectivity` |
| 41 | 更新監察 | 超過 48 小時未檢查時呈現明確異常提醒 | `site/app.js · renderPipelineStatus` |
| 42 | 資訊清晰 | 每日新聞卡加入來源出版日期 | `site/app.js · formatSourceDate` |
| 43 | 頁面安全 | 外部新聞來源連結不傳送網站 Referrer | `site/app.js + index.html · no-referrer` |
| 44 | PWA 快取 | 更新快取版本並加強本地靜態檔案辨識 | `site/sw.js · ai-daily-v4-1` |
| 45 | 裝置體驗 | 提供 192／512 像素安裝圖示與 Apple Touch Icon | `site/manifest.webmanifest · icon-*.png` |
| 46 | 閱讀舒適 | 改善手機觸控區、字體比例、長標題換行及高對比模式 | `site/v4.css` |
| 47 | 測試覆蓋 | 新增後端錯誤、XML、日期、模型、備份及發布流程測試 | `tests/test_v4.py` |
| 48 | 介面驗證 | 加入桌面／手機瀏覽器內的字級、下載、匯入及鍵盤測試 | `tests/browser_smoke_optional.py` |

## 評估標準

- 與 v3 兼容：原有測試仍通過。
- 減少失實：能區分 `feed_error`、`no_new_stories`、示範文章與來源摘要。
- 不收費：不使用 OpenAI API、不要求註冊付費 RSS。
- 體驗：能在手機和電腦查字、標記閱讀、備份、匯入、下載文章。
- 內容：來源可追溯；英語 5★ 僅作訓練目標，不當作已認證水平。

## 已測與尚待實測

本機單元測試、靜態檔案檢查、JavaScript 語法和 Chromium 模擬操作均有對應測試。RSS 真正上線率、GitHub Actions 模型可持續運行程度、中文翻譯語義和 HKDSE 難度仍待實際長期運作及人工評閱驗證。

## 未能宣稱 100% 完美的原因

第三方新聞來源、免費 GitHub 排程、免費開源語言模型、讀者裝置語音合成功能均非本程式完全控制。即使所有單元測試通過，也不能推論真實世界中的新聞來源或模型產出永不出錯。

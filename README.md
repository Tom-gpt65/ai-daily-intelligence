# AI Daily Intelligence — S1 正式版

[English News App](https://tom-gpt65.github.io/ai-daily-intelligence/) · 繁體中文介面 · 英文長篇閱讀 · 離線詞義 · 私人生字與複習

S1（2026-10-10）統一前端、release.json、Service Worker、發布驗收與巡檢的版本。保留 V1／V2／V3 的 localStorage 鍵、個人生字、答案、閱讀進度、Supabase 身分、雲端事件格式與備份相容性。網站發布版本與儲存 schema 是不同用途，升級 S1 不會重新編號使用者資料。

三篇既有文章（2026-10-08／09／10）保持原始位元組；保護清單見 [S1_PRESERVED_FILES.json](docs/S1_PRESERVED_FILES.json)。歷史重製只產生預覽檔案，不能直接改動正式文章或發布網站。

## 每日行為與誠實狀態

| 香港時間 | 工作 | 未能完成時 |
|---|---|---|
| 06:25 | 首發 canary：在臨時站點連續模擬未來日期 | Actions 顯示失敗；不改正式內容 |
| 07:05 | 自動生成並核驗教育閱讀備援 | 若沒有新稿通過，保留原日期的合格留存閱讀，明確標示 |
| 07:40 | 收集 RSS，以來源摘要自動編成英文閱讀分析 | 證據、詞庫或原創性不足時拒稿；先發布安全備援，再讓新聞驗收顯示失敗 |
| 08:05／09:17／13:17 | 公開網站、文章與排程巡檢 | 顯示缺稿、過期或失敗，不以備援冒充新聞 |
| 08:20／09:40／10:25／12:25 | 補救檢查 | 沒有正在生成的工作時，每日最多兩次新聞重試 |
| 14:35／15:05／15:20 | 公開健康、Python／Node、瀏覽器回歸檢查 | 保留可追查的 Actions 結果 |

GitHub 排程指定 `Asia/Hong_Kong`，但仍可能延遲或略過。08:00 可閱讀是目標，並非交付保證。所有正式內容由程式生成，沒有人工撰寫日報；不保證每日都能取得足夠新新聞。

## 正式稿驗收

- 1,000–1,550 英文字、5–15 段、至少 7 題原創閱讀理解題；題目引用必須存在於指定段落。
- 每個可點擊英文詞都必須附有實際中文離線詞義；缺詞時拒稿，不以「待查」填充。
- 新聞至少有三個不同來源項目、有效連結、時間與足夠摘要；引用 ID 必須與文章一致。RSS 摘要不是獨立事實核查。
- 對近 60 天已出版文章及未列入索引的 dated JSON 核對五詞片語；**重複率必須嚴格 <16%**，16% 本身亦拒絕。另檢查長段落、導言結論、標題、來源與寫作方式重用。
- 備援的新稿同樣通過原創性檢查；有限教育詞庫耗盡時，不重新標日期或把舊文章當成新稿。
- 歷史資料損壞時停止原創性驗收，顯示故障。發布、巡檢與補救使用同一份閱讀契約。
- 正式 S1 使用來源歸屬清楚的確定性閱讀分析。手動 `use_model=true` 只產生 runner 內的模型預覽；模型草稿不會公開發布。結構檢查不能證明模型陳述的事實，因此不將它直接放入正式日報。

## 資料安全與離線升級

保留私人生字庫、各帳戶的未送出同步事件、登入身分、備份 version 3／4／5 與詞庫備份 version 1。帳戶切換或登出後，舊網絡回應不能寫入新帳戶或恢復已登出的憑證。

S1 快取名稱為 `ai-daily-S1-2-reading`；僅遷移本網站的 V1／V2／V3 公開文章快取。42 篇 dated 文章上限不包含索引與狀態，刷新參數共用一個快取鍵。HTTP 錯誤或損壞回應保留可用快取，介面標示離線；快取額滿亦不阻擋正常線上閱讀。雲端端點及私人備份不由 Service Worker 快取。

不要以清除網站資料作為一般升級或故障處理方式。真實兩帳戶／兩裝置登入與 RLS 隔離仍需使用者持有的測試帳戶驗證；自動化瀏覽器的模擬登入不能代替此項檢查。

## 執行與驗證

Python 3.11+、Node 22+。預覽保留正式資料快照及每篇文章日期，不會自動變成當日新聞。

```bash
python scripts/preview.py
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
node tests/run_js_tests.js
python scripts/validate_site.py
python scripts/morning_canary.py --first-day 2026-10-11
python scripts/morning_canary.py --first-day 2026-12-31
npm ci --ignore-scripts
npx playwright install --with-deps chromium webkit
node tests/run_js_tests.js --browser
python scripts/verify_publication.py --live
```

測試涵蓋連續日期、年末跨日、重複來源、RSS 中斷、字典缺詞、原創性邊界、並行寫入、Git 部署衝突、帳戶非同步切換、兩種瀏覽器及 V1／V2／V3 升級。合成新聞輸入只留在臨時測試站點，不會發布。詳細修正、實際測試紀錄與維運處置見 [S1 工程審查與維運](docs/S1_RELEASE_AUDIT.md)。

## 發布與維運

GitHub Pages 使用 Actions。兩個發布 workflow 共用 `ai-daily-news` 排隊，待執行工作不互相取消；每次開始讀取最新 main。報告提交先合併遠端歷史，保留有效新聞的優先權，驗證合併後的實際檔案，再以一般 push 提交，不 force push。code push 經回歸測試後發布介面，沒有自動改寫既有文章。

[每日生成](https://github.com/Tom-gpt65/ai-daily-intelligence/actions/workflows/daily.yml) · [備援](https://github.com/Tom-gpt65/ai-daily-intelligence/actions/workflows/early-reading.yml) · [巡檢](https://github.com/Tom-gpt65/ai-daily-intelligence/actions/workflows/audit.yml) · [補救](https://github.com/Tom-gpt65/ai-daily-intelligence/actions/workflows/recovery.yml)

有限模板、免費 RSS／詞典、GitHub Actions／Pages、瀏覽器儲存與 Supabase 都有可用性限制。S1 提供可維運的驗收與降級機制，不能宣稱零故障、每日真實新聞或已達成商業 SLA。舊版歷史詳見 [V3](docs/V3_EDITORIAL_NOVELTY.md)、[V2](docs/V2_STABILITY.md)、[V1](docs/FINALISE_WEBSITE_V1.md)。

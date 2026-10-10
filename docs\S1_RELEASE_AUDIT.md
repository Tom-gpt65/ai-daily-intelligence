# S1 工程審查與維運紀錄

日期：2026-10-10。審查基線：`bf4dfe51ae69a4dbeddc3df60accbf341418bd2b`（GitHub main）。
範圍：公開程式、所有 workflow、現存測試、文章生成／發布／讀取／巡檢／補救路徑與個人資料相容性。
本紀錄列出實際可重現修正與驗證，不構成無缺陷證明。

## 版本與保護範圍

前端 S1、asset_revision `s1-2`、SW `ai-daily-S1-2-reading`，release.json 記載五詞、60 日、嚴格 <0.16。
保留 manifest id／scope／start_url、cloud-config、Supabase SQL、2026-10-08／09／10 的原始 Git blob SHA256，清單見 S1_PRESERVED_FILES.json。Windows checkout 的 CRLF 只在測試時正規化為原始 LF，不修改受保護檔案。既有第三日最高 pairwise 五詞片語重複率為約 13.181%；原文不重寫。

本次工程在獨立 checkout 執行。原工作目錄已有未提交的 V2 變更，已備份，沒有覆蓋。工程前的本機快照與 GitHub main 三日文章皆保存於工作區 s1-evidence；私人瀏覽器資料未讀取、未搬移、未上傳。

## 已修正的可重現問題

| 路徑 | 問題與 S1 行為 |
|---|---|
| content_novelty | 先四捨五入會錯誤處理 15.96%／16% 邊界。改用實值比較；60 日含第 60 天，亦查 orphan dated JSON，損壞歷史 fail closed |
| edition_contract | 發布、巡檢、補救曾用不同的「合格」定義。統一段落、字數、詞義、7 題證據、來源、日期及嚴格原創性核驗 |
| reading_backup | 教育備援原本繞過跨日重複檢查。先審核 24 種程式候選；沒有新稿通過則保留原日期留存文章並寫明原因 |
| build | 多輪候選重複讀檔且預先生成全部內容。改為惰性候選及一次歷史載入；重複 URL／來源、缺詞、不足證據或題目引用失效均不提交 |
| longform | 固定來源摘要中，未明示的「既有股東」、產品名字及動機可能被自行補入。僅保留來源明示的事實；分析使用條件式，不能稱獨立核實 |
| optional model | 模型的數字／名字檢查不能證明所有敘述。手動模型草稿只保留在 ignored runner 預覽，正式 S1 使用來源歸屬分析 |
| dse_assessment | 跨段落答案合併後截斷可丟失第二項證據。兩項各自截斷，再合併並核對各段落 |
| atomic writes | 固定 tmp 檔與並行索引修改可互相覆蓋。唯一 tmp＋fsync／replace，加 OS 鎖；損壞索引不被當空索引重建 |
| publish_reports | 遲到教育稿可能覆蓋新聞，或保留原文時丟掉新故障狀態。合格新聞優先；最新故障依 checked_at 合併；只合併本輪實際有變更的 dated JSON，純留存備援不重放舊稿；合併狀態重新核對遠端實際閱讀，不 force push |
| fetched code | reset 到新 main 後，舊 Python 模組仍留在記憶體。合併後亦啟動新的驗證程序，套用實際最新程式規則 |
| public verification | 同日期不代表同內容。核對完整 report、release、核心資源內容（只正規化換行）與狀態；公開備援驗證後，新聞不足的 daily 才以失敗結束 |
| workflow | 多個 Pages 發布可互相干擾，預設 concurrency 會取消舊 pending。共同 queue:max，cancel-in-progress:false，開工 checkout main；歷史重製改為只讀預覽 |
| app | 背景刷新可覆蓋使用者正在選擇的歷史文章。以請求序號保留後來的選擇；詞庫預載不阻塞閱讀；逾時與 SW 註冊失敗可見 |
| SW | 帶查詢參數的文章無限增長、42 筆上限可能丟掉索引、HTTP 503 無備援。改為 canonical key、保護索引／狀態、網絡逾時與損壞 JSON 回退、快取額滿不阻擋線上回應 |
| SW migration | 保留本網站 V1／V2／V3 公開歷史，不複製私人端點或其他 scope。新安裝稿優先；僅移除本 scope 的已遷移舊項目 |
| cloud-sync | 帳戶切換、登出、refresh、未完成同步可發生舊回應回寫。加入帳戶 epoch、登入意圖序號、單次 refresh 與逾時；不同帳戶 pending queue 保持原儲存鍵 |

## 驗證紀錄（本機與 GitHub 正式驗收）

- 基線：原程式 Python 171 項，Windows 臨時目錄改到工作區後 OK、skipped=1；首次預設 temp 執行因 sandbox 權限失敗，沒有把該輪列作通過。
- 本機 Python **186 項，185 passed、1 skipped**；Windows MSYS bare Git 限制導致跳過。GitHub Linux **186 項全通過、零跳過**，已實際核對並行 Git 修改、純留存備援不重放舊稿及晚到備援不能降級新聞。
- Node：6 組實際測試及全部 site／test JS 語法檢查通過，包含帳戶 race、快取失敗、私人成員隔離與詞庫相容。
- 靜態站點驗收：PASS。歷史重製預覽：PASS，最高 pairwise 五詞片語約 **13.4%**；未修改正式三日文章。
- 連續未來日期與年末跨日由同一臨時 archive 依序執行，包含 +1／2／3／4／5／7／30／59／60／61 日。重複來源不產生新新聞；RSS 中斷及無詞義輸入拒稿；原稿保留，備援名稱與日期明確。
- 瀏覽器：十組測試全部通過，包括 Chromium／WebKit 的 V1／V2／V3 六次真實 worker 升級、離線詞義、版面、備份與模擬登入。本機與 GitHub 均執行完成。
- [S1 PR #11](https://github.com/Tom-gpt65/ai-daily-intelligence/pull/11) 四組 workflow 全通過後合併；[Linux 合約與跨日](https://github.com/Tom-gpt65/ai-daily-intelligence/actions/runs/38057406598)、[瀏覽器](https://github.com/Tom-gpt65/ai-daily-intelligence/actions/runs/38057406596)、[完整長篇驗收](https://github.com/Tom-gpt65/ai-daily-intelligence/actions/runs/38057406587)、[首發 canary](https://github.com/Tom-gpt65/ai-daily-intelligence/actions/runs/38057406619)。
- [正式 S1 Pages 發布與公開核對](https://github.com/Tom-gpt65/ai-daily-intelligence/actions/runs/38057962972)：PASS；[公開 PWA／Auth／匿名隔離健康](https://github.com/Tom-gpt65/ai-daily-intelligence/actions/runs/38058121217)：PASS。本機亦執行 verify_publication --live，完整 report、release、核心資源與 status 一致。網站保留 10 月 10 日既有 V3 來源閱讀；這次 code release 沒有宣稱重新生成新聞。
- 即時來源測試：6/6 RSS 可讀，取得 5 則候選。在完整 ECDICT＋OpenCC 下仍缺 devday、ma、medbenchagent、vision-language、year's，程式拒稿（incomplete_dictionary），臨時站點通過驗收，正式資料未改。不把「安全拒稿測試成功」稱作「當日新聞生成成功」。
- 初次 Linux 驗收曾失敗：兩個舊版文字斷言、六項 CRLF／LF 雜湊差異與一個純備援重放舊稿問題；修正後重跑全通過。首次 main 發布的兩個公開驗證先於部署讀到 V3 而失敗；觸發改為兩個發布 workflow completed 後執行，並重跑確認。後續驗證詳見發布後工作紀錄。

## 路徑審查與有限責任

生成來源為 build／source_context，編稿為 longform／learning_editorial／dse_editorial，題目為 dse_assessment_v7，詞庫為 edition_guarantee；demo 是明示的本機示範，不經正式稿驗收。preview 只提供已保存資料。
content_novelty 與 edition_contract 是正式稿的獨立守門；validate_site 亦檢查歷史、前端資源與私密檔案。publish_reports 提交後，verify_publication 驗證公開版本；audit_publication、recover_daily、v1_final_health 負責誠實巡檢與有界重試。
app 負責閱讀／詞庫／備份，cloud-sync 負責各使用者的 Supabase 事件；SW 只處理本 scope 的公開閱讀資源。全部 workflow 都已逐一檢視觸發、權限、發布副作用與等待條件。

V3 的 10 月 9 日歷史重製保存了重製時間作 updated_at，並標示來源快照日期；為保持原文不改，此歷史時間特例只容許截止 2026-10-10 的既有 profile。所有之後的稿必須是 s1，來源時間與當日 revision 會嚴格核對。此相容特例不是未來稿的繞過途徑。

## 故障處置

1. 開啟公開 system-status.json 及其 workflow_run_url，確認是 RSS、重複稿、缺詞、歷史損壞或發布失敗。
2. 若顯示留存備援，檢查原文章日期，不改日期、不清除使用者資料、不取消 <16% 門檻。
3. 檢查 Actions 是否停用、排程延遲、Pages 權限或 runner 外部下載失敗；補救每日最多兩次。人工重試會占用同一配額。
4. 字典缺詞應補充有來源的詞義後重新執行生成；不能用「待查」湊出完整詞庫。RSS 摘要不足時等待新資料。
5. 索引／歷史損壞時從已驗證備份核對恢復，不讓程式重建空歷史以繞過原創性。
6. code 回退需新 asset_revision／SW namespace；沿用原網站 origin、manifest identity、localStorage 鍵、cloud project 與資料 schema。先備份，不靠清空儲存修復。
7. 正式網站安全備援可用與「今日新聞成功」分開看待。每日真實到稿率須持續量測；本次跨日模擬不能證明翌日排程實際執行。

## 遺留限制

有限模板可能連續拒稿，尤其來源內容相近；此時安全留存閱讀會明確顯示，並沒有偷偷放寬原創性。五詞片語測試不能證明語義從未重複或內容完全正確。詞義結構完整不等於每個語境或專有名詞翻譯完全準確。

GitHub Actions／Pages、RSS／metadata／ECDICT、Supabase、瀏覽器儲存仍是外部依賴。匿名 API 健康與未暴露資料不證明真實兩帳戶 RLS 隔離；未使用使用者私人憑證，實際雙裝置登入及雲端寫入需另行測試。WebKit 自動化不是實機 iPhone 的冷啟動證明。沒有無根據的零故障或商業 SLA 保證。

排程語法與排隊依官方文件核對：[schedule timezone](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)、[concurrency queue](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)。

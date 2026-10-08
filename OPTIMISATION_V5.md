# v5 內容、速度、準確性專項改良紀錄

本輪以 **v4 為基線**，不是再堆疊 30 個外觀功能。以下是有程式碼及測試對應的改良，不聲稱任何一項等於實際的獨立事實核查。

| # | 問題 | 已完成的具體改善 | 位置／驗證 |
|---|---|---|---|
| 01 | 最新消息壟斷排序 | 時效分數設上限 | `scripts/build.py:importance_score` |
| 02 | 缺乏重要性判斷 | 依事件性質加入具體規管、發布、安全等信號 | `importance_score`、`test_importance_newer_not_always_better` |
| 03 | 標題黨可能得高分 | 誇張用語扣分 | `VAGUE_TERMS`、`test_hype_penalty` |
| 04 | RSS 很簡略卻可能獲高分 | 加入摘要具體度指標 | `importance_score` |
| 05 | 重複報道導致清單擠壓 | 將標題相近的報道保存在事件群組 | `collect`、`test_cross_publisher_duplicates_keep_coverage` |
| 06 | 多來源證據鏈遺失 | 保留其他報道的來源標題、連結及日期 | `coverage`、前端 `source-alternates` |
| 07 | 同一媒體重複佔多個來源 | 群組來源只計不同 publisher | `test_one_publisher_duplicate_does_not_claim_second_source` |
| 08 | 不同公司新聞被誤合併 | 公司名稱錨點辨識 | `headline_anchors`、`test_distinct_organisations_not_collapsed` |
| 09 | 不同模型版本被誤合併 | 標題數字／版本錨點辨識 | `headline_anchors`、`test_distinct_model_versions_not_collapsed` |
| 10 | RSS 內含「忽略指令」可能影響模型 | 偵測典型提示注入並跳過該新聞 | `appears_to_be_instruction`、`test_rss_instruction_quarantined` |
| 11 | 預抓快取可能被改寫後交給模型 | 快照重新檢查來源附加連結與注入語句 | `validate_candidate_sources`、`test_malicious_coverage_rejected` |
| 12 | 僅靠篇幅就生成容易擴寫錯誤 | 資料不足時走明確來源摘要模式 | `build_live`、`test_quality_requires_evidence` |
| 13 | 英文報告可能夾雜非英文 | 生成結果拒絕中文字元 | `review_model_text`、`test_chinese_contamination_rejected` |
| 14 | RSS 無法核實大段直接引述 | 拒絕可疑長直接引語 | `review_model_text` |
| 15 | 機器中文全文翻譯使執行倍增 | 關閉**預設**的第二次翻譯模型工作；保留點字查譯 | `TRANSLATE_ENABLED=0`、workflow |
| 16 | 不知道更新慢在哪裏 | RSS、生成、翻譯及字典均有耗時紀錄 | `system-status.json`、Actions Summary |
| 17 | 思考題每天無關新聞 | 至少一題引用當天主新聞來源 ID | `make_questions`、`test_question_references_real_story` |
| 18 | 五分鐘速度對個別學生不準 | 新增三段自訂每分鐘英文詞數 | `site/app.js:readingEstimate` |
| 19 | 多次出現相同字時例句錯位 | 依點擊 DOM 字詞在段落中的實際位置抽取語境 | `site/app.js:sentenceOf` |
| 20 | 新聞多來源容易造成「已核查」錯覺 | 介面明示「多來源報道 ≠ 獨立核實」 | `site/app.js:renderStoryCards` |
| 21 | 看不到對應的其他報道 | 原始來源面板加入其他媒體連結 | `site/app.js:renderReport` |
| 22 | 改版後離線快取可能繼續舊版 | Service Worker 快取版本升級到 v5 | `site/sw.js` |
| 23 | 加功能可能破壞舊程式 | 保留 v4 舊測試並新增 v5 功能測試 | `tests/test_v5.py` |
| 24 | 主題多樣性過度主導選稿 | 將主題分散改為溫和加分，避免擠走更重要報道 | `collect`（排序時用加權綜合分數） |

## 測試與界限

`python -m unittest discover -s tests -q`、`python scripts/validate_site.py`、`node --check` 和 Playwright 桌面／手機互動測試。均屬本機測試；模型生成時間、RSS 活躍狀態、香港時間 08:00 實際部署及真實報告的 DSE 難度，**尚需 GitHub 正式運行觀察**。

### 下階段的高價值測量

- 正式執行 14 天：排程成功率、RSS 可讀來源數、當日發報成功率、需要降級為摘要的日數。
- 抽樣核實 50 個新聞陳述：每一處是否能回溯到原始來源、是否有無依據數字或誇大的因果關係。
- 對英文報告進行人工難度校準：篇幅、文法自然度、資訊密度、學習詞彙的可遷移性。
- 將實際 `model_seconds` 與備用摘要比對：若 5 分鐘英文報告品質不足，不應單純換更慢的模型。

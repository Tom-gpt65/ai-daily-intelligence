# DSE student-first quality review — v6

> 本文件為獨立自製閱讀教材的品質檢查準則；**並非考評局官方認證**。現時系統不能僅靠字數、句長、或題數聲稱達到 HKDSE Level 5★ 難度。

## 官方評核依據（與實際來源區分）

- [HKEAA 2026 English Language Assessment Framework](https://www.hkeaa.edu.hk/DocLibrary/HKDSE/Subject_Information/eng_lang/2026hkdse-e-elang.pdf)：Paper 1 Reading 包含必答 Part A，以及 B1/B2 二選一；B2 是難度較高的部分。題型涵蓋 multiple choice、short answers 與 extended open-ended response。
- [HKEAA 官方 2024 樣本試卷總覽](https://www.hkeaa.edu.hk/en/hkdse/assessment/sample_practice_paper/)：公開樣本索引；無授權不可把真題或標準答案直接複製到公開網站。
- [HKEAA 官方考生表現示例](https://www.hkeaa.edu.hk/en/HKDSE/assessment/subject_information/category_a_subjects/eng_lang/sp/2026.html)：適合用來校準實際評分與考生作答要求。
- [HKEAA 英文閱讀短答 FAQ](https://www.hkeaa.edu.hk/tc/hkdse/assessment/subject_information/category_a_subjects/eng_lang/faq_q/q3.html)：較長回答必須清晰表達意思；拼寫／語法問題並非一律直接扣分。

## 每日高品質文章檢查

- [ ] 報告日期正確，所有新增新聞事實均有來源；RSS 提供資料不足時須標示來源摘要，不能臆測。
- [ ] 最少 **1,000 個英文單字**（通常目標約 1,100–1,350 字）是閱讀篇幅**目標**，不是為湊數而重複字句。文章有可追蹤主旨、支持、反方考慮及有保留的總結。
- [ ] 主要段落不能連續使用 `According to…`；不在原始資料未證實時虛構數字、研究成效、引述及結論。
- [ ] 至少包含語境詞義、作者態度、主旨／目的、推論及文本之間的關聯。
- [ ] 所有可自動判分的選擇題必須有唯一正確答案及可回查的原文證據；開放題如未能可靠自動評分，就只顯示規準，不暗示給予官方分數。
- [ ] 增設段落語篇結構問題、指代／銜接詞解釋、作者寫作手法等，並輪替題型；不應每天使用同一組答案。
- [ ] 每週以學生的真實作答紀錄（本機保存）檢視常錯技能；不應只用背熟詞彙作為閱讀理解進步的證據。

## iPhone 可用性檢查

- [ ] 320、375、390、430px 寬度，以及大字體、放大設定時，正文不出現水平裁切。
- [ ] 翻譯／詞典面板不遮住關閉控制；長段落可以捲動，點字後能回到原句。
- [ ] 首頁可一鍵跳到正文；輔助工具應可展開／收起，不擠佔大半個畫面。
- [ ] 全文翻譯需要**事先同意**第三方服務傳輸；同時考慮 CORS、配額、翻譯錯誤與離線顯示。
- [ ] 瀏覽器模擬測試不能取代真實 iPhone Safari 手動測試。

## 尚未解決的實質限制（請勿隱藏）

1. **數據深度**：目前免費 RSS 摘要未必足以支持深入、精確的分析；日後須加強取得可靠原文內容（尊重版權）及核實來源。
2. **模板重複**：當 Ollama 本地模型英文生成失敗，備援編輯文章仍有部分可重複的分析框架，不能每天保證新穎。
3. **真正 DSE 校準**：尚未用一組可重複、帶人手評級的 HKEAA 實卷題目及考生答案對標，因此不能給出 5★ 難度保證。
4. **翻譯可靠性**：免費第三方翻譯有使用額度，已通過接口／跨域標頭檢查，但仍需由使用者用真實 iPhone Safari 完成全篇測試。
5. **閱讀時間**：現時長篇通常需約 8–14 分鐘**僅指文章**；正式理解題、訂正及複習是額外練習，不應誤報為五分鐘內可完成全部。

# AI Daily Intelligence v7 — 學生導向品質更新

## 評核依據
參照 [HKEAA 2026 English Language Assessment Framework](https://www.hkeaa.edu.hk/DocLibrary/HKDSE/Subject_Information/eng_lang/2026hkdse-e-elang.pdf) 的閱讀目標：主旨、語境詞義、作者態度、複雜論點評估、修辭特色及跨文本整合。這是原創 Part B2-style 教材，**不是考評局官方試題或獲認證的 Level 5★ 難度**。

## 實際改良
- iPhone 320／375／390／430px：版面、字體、查字底部面板、閱讀工具列。
- 翻譯可全篇或逐段取得；每段成功便保存在瀏覽器，網絡失敗可以續譯。須事前同意將公開英文傳送到免費 MyMemory 翻譯服務；翻譯可能不準確或受免費額度限制。
- 自動化每日產生文章專屬的閱讀題，保留段落位置、原文摘錄及答案理由。客觀選擇題首次作答即鎖定；書面題只提供評分準則，不偽稱自動精確評分。
- 支援保存與備份答題紀錄，並新增原文段落跳轉。
- 改善免費模型正文品質檢查，移除每段必須重複標來源的限制，仍保留來源核對與禁止沒有根據的數字。
- RSS 可按需補充公開文章 metadata；不抓取付費文章全文、不把來源主張當成獨立查核結果。
- 免費開源模型不合格時，使用有明確標示的教育性來源摘要，並輪換不同文章論述角度。
- GitHub 發布時如遇其他程式碼提交，重新取得主分支、只保留新生成新聞檔案，最多安全重試四次。
- 網站顯示當日 07:40 排程成功、失敗或執行中的實際狀態。

## 驗證入口
- [GitHub 網站及 Python 測試](https://github.com/Tom-gpt65/ai-daily-intelligence/actions/workflows/daily.yml)
- [WebKit + Chromium 手機瀏覽器測試](https://github.com/Tom-gpt65/ai-daily-intelligence/actions/workflows/browser-v7.yml)
- [公開網站檢查](https://github.com/Tom-gpt65/ai-daily-intelligence/actions/workflows/verify-pages.yml)
- [香港時間 08:05／09:17 定期獨立驗證](https://github.com/Tom-gpt65/ai-daily-intelligence/actions/workflows/audit.yml)

## 未能保證的部分
1. 首次 07:40 定時執行約在 07:47 啟動，並因同時修改程式碼而發生 Git 推送衝突。安全重試機制已部署，尚待下一次真正定時執行驗證。
2. 公開 RSS 及 metadata 無法代替新聞全文逐項核查。
3. 自製 7 題短篇教材不等同實際 HKDSE Paper 1 Part B2 的篇幅、文類、整體難度及官方評分。
4. 免費第三方翻譯可能受額度、私隱、網絡與翻譯質素影響；模擬 WebKit 通過不代表真實 iPhone Safari 必定通過。
5. GitHub Actions 可延遲排程；上午 8 時「可讀」只是目標，並非保證。

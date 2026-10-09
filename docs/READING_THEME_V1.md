# AI Daily Intelligence V1｜閱讀舒適配色規格

**正式主題：** Paper Calm（日間，首次使用預設）與 Soft Graphite（夜間，可由使用者自行選擇）。此文件記錄部署配色、對比目標及驗收方法，不聲稱同一種顏色適合所有人，也不作醫學上的防疲勞保證。

## 1. 設計原則

1. 文章採用中性／暖色低彩度背景配深色正文；夜間使用石墨灰與非純白文字。強調色只用於互動／狀態／標記，**全文可點擊詞語在未互動時維持正文顏色**。
2. 預設 Paper Calm；如果舊用戶曾選擇深色模式，維持本機 `ai-daily-light=false` 設定。主題首次呈現前完成套用以避免深淺閃爍，日後手動切換繼續記住個人選擇。
3. 不因配色修改而改動正式版本 **V1**、詞庫 `ai-daily-saved-v2`、複習資料、其他學習進度、Supabase 金鑰／RLS／帳戶登入、離線事件佇列。
4. 夜間模式是可選項，不暗示「黑底必然更護眼」。閱讀舒適度仍受環境照明、系統亮度、視覺狀況及字體設定影響。

## 2. 設計色票

| 用途 / CSS token | Paper Calm（日間） | Soft Graphite（夜間） |
| --- | --- | --- |
| 外層 `--bg` | `#F2EEE6` | `#171C1E` |
| 導航 `--side` | `#E8E1D6` | `#1D2528` |
| 紙張 `--reader-paper`、`--surface` | `#FFFDF8` | `#22292A` |
| 操作面板 `--surface2` | `#F5F1E8` | `#2B3535` |
| 正文 `--text` | `#292C29` | `#E8E4DB` |
| 註解 `--muted` | `#5D655E` | `#B9B8AE` |
| 強調 `--accent` | `#355C4E` | `#B2D1B9` |
| 互動背景 `--accent-low` | `#E5EFE8` | `#35493F` |
| 連結 `--link` | `#2E5D70` | `#ABD3E1` |
| 裝飾邊界 `--border` | `#D2CABD` | `#53615E` |
| 必要表單邊界 `--input-border` | `#838E83` | `#82938B` |
| 已選導航邊界 `--nav-border` | `#737E73` | `#82938B` |
| 鍵盤焦點 `--focus-ring` | `#2B6378` | `#B1D3E0` |
| 強調按鈕上的文字 `--on-accent` | `#FFFFFF` | `#171C1E` |
| 成功 `--success` | `#2D6A4F` | `#B2D9BF` |
| 警告 `--warning` | `#855A20` | `#F0C98C` |
| 錯誤 `--danger` | `#A1433F` | `#F0ADA5` |

裝飾線不作為唯一的必要控制邊界。按鈕、輸入框、已選導航的辨識邊界使用另外的 `--control-border` 或 `--input-border`、`--nav-border`；成功、錯誤等狀態必須以文字／圖示呈現，不可單靠顏色。

## 3. 驗收標準

| 項目 | 最低標準 |
| --- | --- |
| 主要正文 / 紙張 | 對比度 ≥ **7:1**（超過 WCAG AAA 普通文字目標） |
| 普通次文字與表單文字 | 對比度 ≥ **4.5:1** |
| 連結 / 紙張 | 對比度 ≥ **7:1** |
| 強調背景上的文字 / 成功、警告、錯誤提示 | 對比度 ≥ **4.5:1** |
| 重要表單邊界、已選導航邊界、焦點外框 | 對比度 ≥ **3:1** |
| 英文正文 | 手機原有 V1 ≥ 17px、正文 line-height ≥ 1.6；桌面文章保持合理行寬，不能水平溢出 |
| 功能 | 日／夜切換並儲存偏好，既有暗色選擇不被強制覆蓋；詞庫、複習、Supabase 登入和 PWA 離線均不被破壞 |
| 瀏覽器 | Chromium 和 WebKit，390px（手機）、820px（平板）、1440px（桌面）；另檢查列印為白紙深字 |
| 發布 | Pull Request 全部必要測試通過，合併後 GitHub Pages 公開資產及配色驗證通過 |

**重要：** 對比度只是可檢查的工程指標，不會單獨決定主觀閱讀舒適度。除了自動測試，仍建議日後讓真實使用者在日光及夜間各閱讀約 20–30 分鐘，再按個人回饋調整螢幕亮度與配色。

## 4. 自動驗證

- `node tests/reading_theme_tokens_v1.js`：利用 W3C relative luminance 公式檢查兩套主題的文字、邊界、選取與焦點對比度。
- `node tests/browser_reading_theme_v1.js`：實際啟動 Chromium／WebKit，取得 computed style，驗證行寬、文字對比、切換／重新載入偏好、保留本機生字、焦點可見性、表單、列印配色及不同屏幕寬度。
- 原有 `browser_cloud_password.js`、`browser_cloud_sync.js`、`browser_layout_v11.js`、`browser_v12_layout.js` 及全部 Python/Node 測試：確保閱讀、學習及登入功能並未倒退。
- `.github/workflows/cloud-live-check.yml` 與 `verify-pages.yml`：確認正式 GitHub Pages 已更新到本版配色並保持 Supabase 匿名存取保護。

參考標準：[W3C WCAG 2.2 Contrast (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)、[Contrast (Enhanced)](https://www.w3.org/WAI/WCAG22/Understanding/contrast-enhanced.html)、[Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)、[Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)。

## 5. CSS 架構與回滾

新的 `site/reading-theme-v1.css` 置於既有 `style.css`、`v3.css` 至 `v12.css`、`v1.css` 之後，只覆蓋配色相關 token／規則，不重置閱讀排版、文章內容或用戶資料。更換色票或退回舊顏色可透過獨立 PR 反轉 CSS／HTML／主題初始化更動，不需要資料庫遷移。

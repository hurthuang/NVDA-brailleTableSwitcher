# brailleTableSwitcher

NVDA addon，讓使用者透過快速鍵在台灣中文點字表與 UEB 點字表之間循環切換輸出轉譯表。

## 功能

| 快速鍵 | 功能 |
|--------|------|
| `NVDA + Alt + B` | 在勾選的**輸出**點字表間循環切換 |
| `NVDA + Alt + I` | 在勾選的**輸入**點字表間循環切換 |
| `NVDA + Alt + O` | 報讀目前的輸出與輸入點字表 |
| `NVDA + Alt + P` | 開啟設定，選擇要循環的點字表 |

每次切換時，NVDA 會語音播報目前選用的點字表名稱。快速鍵可在「NVDA 偏好設定 → 輸入手勢 → Braille Table Switcher」中自訂。

### 選擇循環的點字表

`NVDA + Alt + P`，或「NVDA 偏好設定 → 設定 → 點字表切換」，可分別勾選輸出與輸入要循環的點字表（至少各勾一個）。預設列出推薦的點字表；勾選「顯示所有點字表」可列出 NVDA 所有點字表。

推薦的輸出點字表：

| 點字表 | 說明 | 預設 |
|--------|------|------|
| `zh-tw.ctb` | 注音點字 | 勾選 |
| `zh-tw-ueb-g1.ctb` | 注音點字 + UEB Grade 1（逐字對應） | 勾選 |
| `zh-tw-ueb-g2.ctb` | 注音點字 + UEB Grade 2（含英文縮寫） | 勾選 |
| `zh-tw-suodian.ctb` | 縮點閱讀 | 不勾 |

推薦的輸入點字表：英文電腦點字（en-us-comp8）、UEB 一級、UEB 二級，預設全部勾選。

### 縮點閱讀

把注音點字的調號那一方併到第 7、8 點，平均每字約少一方。聲母、韻母點位不變；聲母與韻母的點型不重疊，所以拿掉調號後，字和字的分界仍由韻母判斷。

| 聲調 | 寫法 | 例 |
|------|------|----|
| 一聲 | 不標 | 他 ＝ 1247-345 |
| 二聲 | 韻母加點 7 | 學 ＝ 15-2367 |
| 三聲 | 韻母加點 7、8 | 我 ＝ 2578 |
| 四聲 | 韻母加點 8 | 是 ＝ 24-1568 |
| 輕聲 | 聲母加點 8；沒有聲母的輕聲不標 | 的 ＝ 1458-2346 |

- 原表以 7、8 點區分的代名詞：他、你、她、妳保留聲母上的記號；牠、祂的記號在韻母上，會與聲調混淆，維持原寫法。
- 縮點閱讀是閱讀用的點字表；點字輸入的縮點模式請見 [6d-IME](https://github.com/hurthuang/6d-IME)。
- 構想來源：[注音點字改良思考](https://class.kh.edu.tw/19061/bulletin/msg_view/197)（2018）；輸入的做法見 [縮點輸入法](https://class.kh.edu.tw/19061/bulletin/msg_view/497)（2020）。

## 安裝需求

- NVDA 2021.1 或更新版本
- 測試版本：NVDA 2026.2

## 安裝方式

1. 下載最新版的 `brailleTableSwitcher.nvda-addon`
2. NVDA 執行中，雙擊 `.nvda-addon` 檔案
3. 依提示完成安裝，重新啟動 NVDA

## 技術說明

`zh-tw-ueb-g1.ctb` 與 `zh-tw-ueb-g2.ctb` 以台灣中文注音點字規則為基礎，僅將英文點字部分替換為對應的 UEB 表，中文注音規則完整保留。`zh-tw-suodian.ctb` 由 `tools/build_suodian_ctb.py` 從 NVDA 內建的 `zh-tw.ctb` 自動轉換產生，不要手動修改。ctb 檔案直接打包在 addon 內，安裝後即可使用，不需要額外設定。

切換方式採用 `braille.handler.table` 直接賦值，自訂點字表透過 `manifest.ini` 的 `[brailleTables]` 區段向 NVDA 登記。循環清單存在 nvda.ini 的 `[brailleTableSwitcher]` 區段。解除安裝時若目前使用中的是自訂表，會自動重設回 `zh-tw.ctb`。

## 授權

GPL v2

# brailleTableSwitcher

NVDA addon，讓使用者透過快速鍵在台灣中文點字表與 UEB 點字表之間循環切換輸出轉譯表。

## 功能

按下 **`NVDA + Alt + B`** 循環切換三個輸出點字表：

| 點字表 | 說明 |
|--------|------|
| `zh-tw.ctb` | 注音點字（預設） |
| `zh-tw-ueb-g1.ctb` | 注音點字 + UEB Grade 1（逐字對應） |
| `zh-tw-ueb-g2.ctb` | 注音點字 + UEB Grade 2（含英文縮寫） |

每次切換時，NVDA 會語音播報目前選用的點字表名稱。快速鍵可在「NVDA 偏好設定 → 輸入手勢 → Braille Table Switcher」中自訂。

## 安裝需求

- NVDA 2021.1 或更新版本
- 測試版本：NVDA 2025.3

## 安裝方式

1. 下載最新版的 `brailleTableSwitcher.nvda-addon`
2. NVDA 執行中，雙擊 `.nvda-addon` 檔案
3. 依提示完成安裝，重新啟動 NVDA

## 技術說明

`zh-tw-ueb-g1.ctb` 與 `zh-tw-ueb-g2.ctb` 以台灣中文注音點字規則為基礎，僅將英文點字部分替換為對應的 UEB 表，中文注音規則完整保留。ctb 檔案直接打包在 addon 內，安裝後即可使用，不需要額外設定。

切換方式採用 `braille.handler.table` 直接賦值，自訂點字表透過 `manifest.ini` 的 `[brailleTables]` 區段向 NVDA 登記。解除安裝時若目前使用中的是自訂表，會自動重設回 `zh-tw.ctb`。

## 授權

GPL v2

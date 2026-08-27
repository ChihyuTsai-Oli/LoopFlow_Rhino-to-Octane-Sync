# LoopFlow R2O — 使用說明

本文件記錄目前 1.x 對使用者可見的行為，是 2.0 重構期間不得無意改變的操作契約。完整逐步教學仍以 `USER_GUIDE_zh-TW.md` 為準。

2.0 採乾淨重建；本文件用於理解舊工作流與建立 fixtures，不要求開發中的半成品持續相容 v1。命名、Python↔Lua schema 與操作若經使用者裁決可在 2.0 改變，但必須記錄於 `_R2O_命名與資料契約.md`，並在發布前完成新版使用說明。

## 產品邊界

R2O 分為三個部分：

1. Rhino Producer：Models、Scatter、Point、Camera、Open／Config。
2. Octane LiveLink Consumer：讀取、驗證與套用同步資料。
3. Octane Authoring Tools：Auto Align、材質轉換、PBR／UV 等獨立工具。

Authoring tools 可以和 LiveLink 放在同一 repo，但不是 Models／Scatter／Point／Camera 的必要相依。

## 使用環境

- Rhino 8／CPython 3.9
- Windows 10／11
- OctaneRender Standalone；最低相容版本尚未有可靠實測矩陣，不得自行猜測或寫入文件。
- Rhino 端 Python，Octane 端 Lua。

2.0 開發版必須使用獨立 Rhino scripts／data／RHC、Octane scripts／shortcut、同步輸出與測試場景，不覆蓋穩定 1.x。

## Rhino 指令

| 指令 | 行為契約 |
|---|---|
| `R2O_Models` | 發布 USDZ；不得永久改來源材質狀態，後處理失敗不得回報成功。**2.0 已決（ED-02＝A）**：Octane 端僅手動置換模型，不做 Models LiveLink |
| `R2O_Scatter` | 將 Block／instance 發布為 USD；不得留下來源 Block 位移 |
| `R2O_Point` | 將 Point／Block layer 資料寫成 Lua 同步資料 |
| `R2O_Camera` | Rhino：event＋節流持續發布相機資料。Octane 1.x：快捷鍵／腳本**執行一次**套用最新檔（非背景輪詢） |
| `R2O_Open` | 開啟設定、資料與相關工具 |

各功能可獨立使用，不強迫成連續工作流。

## Octane LiveLink

| Script | 用途 |
|---|---|
| `LiveLink_R2O_Camera.lua` | 讀取並套用 Rhino camera 資料（1.x：手動跑一次；2.0 意向見決策表 `R2O-ED-19` 可開關 real-time） |
| `LiveLink_R2O_Point.lua` | 讀取 Point／Block 類型與 transform，更新 Octane nodes（身分見 ED-05；刪節點見 ED-10＝A） |

**2.0 無 Models LiveLink**：模型更新靠手動置換 USDZ（ED-02＝A）。consumer 只有 parse 與 apply 成功後才能更新 state；壞檔或半寫入資料不得被視為已處理。

## Octane Authoring Tools

- `Auto_PBR_Universal.lua`
- `Auto_PBR_Switch_UV.lua`
- `Auto_Convert_StdSurf_to_Universal.lua`
- `Auto_Align_Nodes.lua`
- Shortcut open／setup scripts

2.0 只整理文件、生命週期、錯誤與 build，不新增 authoring 功能。

## 使用安全契約

任何同步在成功、取消、失敗或中斷後都必須符合：

- Rhino 原文件的物件、Block transform、layer、selection、visibility、material source 與未存內容不變。
- Models／Scatter 新輸出完整驗證前保留上一份有效 USD／USDZ。
- USDZ material binding postprocess 失敗即整體失敗，不得只因檔案存在就顯示成功。
- Point 對引號、反斜線、換行、中文、emoji、空名稱與同名末層有確定且可測結果。
- Camera／Point 的 Python producer 與 Lua consumer 使用一致 schema version／escaping。
- 單一 Scatter item 失敗不破壞其他項目或 last good output。

## Golden workflow

修改對應範圍前，使用測試 `.3dm`／Octane scene 記錄：

- Models：material source、取消／失敗、後處理、last good USDZ。
- Scatter：Block transform、單項失敗、重複同步與 last good USD。
- Point：特殊字元、中文、emoji、同名 layer、stable ID、Lua consumer。
- Camera：event lifecycle、throttle、座標／焦距；**consumer 為一次套用或（2.0）可開關輪詢**（見 `前期規劃/資料生態決策表_三家建議.md` ED-13／ED-19）。
- Octane：安裝、shortcut、module loading、reload 與錯誤輸入。
- Authoring tools：現行操作與重複執行。

實機結果以 `architecture/PROGRESS.md` 為準。

## 設定與問題定位

- 設定檔：`%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\R2O_Path.txt`
- Debug log：同一 Data 目錄下的 `cursor_R2O_debug_log.txt`
- Shortcut 一般流程：Open Shortcuts → 修改 → Setup Shortcuts → Octane rescan。
- 先保存 Rhino／Octane 版本、錯誤畫面、log、輸入與輸出檔，再交由 AI 處理。
- 不要自行刪除 Data、USD／USDZ、shortcut、正式 scene 或設定；先由 AI 檢查 last good 與回復方式。

## 文件責任

- `USER_GUIDE_zh-TW.md`：公開逐步使用指南。
- `_R2O_使用說明.md`：重構期間的行為契約。
- `_R2O_系統設定.md`：目前結構、設定與 Python↔Lua 契約。
- `_R2O_命名與資料契約.md`：2.0 指令、Python↔Lua schema、Octane ID 與 migration 的權威來源。
- `_R2O_重構計畫.md`：2.0 目標架構與遷移順序。
- `architecture/PROGRESS.md`：即時進度、檢查與下一步。

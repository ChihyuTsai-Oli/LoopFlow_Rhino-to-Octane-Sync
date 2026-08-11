# LoopFlow Rhino-to-Octane Sync 2.0 重構進度

- 建立日期：2026-08-12
- 目標版本：`v2.0.0`
- 整合分支：`v2-development`
- 建立基準：`main` / `54ea9a6f26f3e678546fec30ceeab4d75c299c07`
- 穩定回復點：`v1.0.0` / `caf737f6bd22068da537573ccdea1de49fe2fc53`
- 狀態：重構模式已定案；命名與 Python／Lua 資料契約待完整盤點；尚未修改產品程式碼

## AI 接手入口

本 repo 已建立自足的繁中維護文件。AI 開始前依序讀取根目錄 `AGENTS.md`、`docs/_R2O_使用說明.md`、`docs/_R2O_系統設定.md`、`docs/_R2O_命名與資料契約.md`、`docs/_R2O_重構計畫.md`，最後讀本文件確認即時進度。外部分析檔不再是必要輸入。

## Release 回復資產

| 項目 | 值 |
|---|---|
| 檔案 | `LoopFlow_R2O_v1.0.0.zip` |
| 大小 | 61,015 bytes |
| ZIP 項目數 | 17 |
| SHA-256 | `5a74abd07e6b152c01983dd5e5d86e6781d0c3479a08500f3a4dd588a435f0e9` |

此 ZIP 已能正常開啟，並與 GitHub `v1.0.0` Release 資產的大小一致。Tag 與 Release 不移動、不覆寫。

## 分支規則

- `main`：2.0 正式發布前維持可發布的 1.x。
- `v2-development`：2.0 的唯一整合線。
- 每批工作從 `v2-development` 建立 `codex/v2-<scope>` 短期分支，檢查通過後才合入。
- `main` 原則上凍結，僅在使用者明確要求維護 1.x 時，才另開獨立 hotfix 分支並將必要修正同步至 `v2-development`。
- `v2.0.0` 只在 RC 與 Rhino / Octane 實機驗收完成、合回 `main` 後建立。

## Golden workflow 基準

合約盤點期間，先從穩定版與既有範例整理可自動比對的 fixture、預期輸出與必要畫面基準。新版主要工作流串接完成後，再使用隔離的 Rhino 8、Octane、測試 `.3dm`／scene 與輸出目錄，依下列清單進行完整實機端到端驗證：

- Models：來源材質狀態、取消／失敗、USDZ 後處理與最後有效輸出。
- Scatter：Block 位置／transform、單項失敗、重複同步與最後有效 USD。
- Point：特殊字元、中文、emoji、同名末層、stable ID 與 Lua consumer。
- Camera：event lifecycle、throttle、座標／焦距與 producer / consumer 狀態。
- Octane LiveLink：安裝、shortcut、module loading、reload 與錯誤輸入。
- Authoring tools：Auto Align、材質轉換、PBR / UV；2.0 核心重構期間不擴充功能。

fixture 與預期結果應在對應功能建造前完成；實機結果則在主要工作流串接後集中補入本文件。未驗證項目不得標記為通過。

## 第一階段順序

1. 盤點完整 Rhino → Python 輸出 → Lua／Octane 消費工作流，以及所有命名與版本相依點。
2. 完成指令、設定、檔名、資料夾、資料 schema、Point ID、Octane node、shortcut 與版本契約。
3. 固定 fixture、預期輸出、schema version 與舊專案轉換邊界；舊名稱只由獨立遷移工具辨識。
4. 建立新版 Rhino、Python 與 Lua 最小架構，先驗證 import、module loading、reload 與安裝隔離。
5. 契約確認後，依 Models → Scatter → Point → Camera → Octane consumer 的真實操作順序接入功能並同步建立自動化與契約測試。
6. 主流程串接完成後，集中進行 Rhino／Octane 實機端到端測試，再完成 authoring tools 邊界、遷移工具、安裝包與 RC。

## 驗證紀錄

| 日期 | 分支 / commit | 檢查 | 結果 | 限制 |
|---|---|---|---|---|
| 2026-08-12 | `v2-development` 建立基準 | Git 同步、Release ZIP 完整性與 SHA-256、6 支 Python 靜態語法、RHC XML | 通過 | Lua interpreter 不在 PATH；Rhino / Octane 實機流程由後續批次逐項驗證 |
| 2026-08-12 | 文件 SSOT 建置 | 建立繁中使用說明、系統設定、重構計畫與 repo AI 規則；Markdown 本機連結檢查 | 通過 | Python／Lua 大型標頭與英文註解依 feature 批次遷移 |
| 2026-08-12 | 重構模式裁決 | 新版乾淨重建、一次切換；命名與 Python／Lua 資料契約先於程式架構 | 通過 | 尚未開始命名盤點與產品程式碼修改 |

## 下一步

從 `v2-development` 建立 `codex/v2-naming-contract`，先盤點整套工作流及所有指令、設定、檔名、schema、Point ID、Octane node、shortcut 與版本名稱。使用者確認契約前，不開始正式功能程式碼。

# LoopFlow Rhino-to-Octane Sync 2.0 重構進度

- 建立日期：2026-08-12
- 目標版本：`v2.0.0`
- 整合分支：`v2-development`
- 建立基準：`main` / `54ea9a6f26f3e678546fec30ceeab4d75c299c07`
- 穩定回復點：`v1.0.0` / `caf737f6bd22068da537573ccdea1de49fe2fc53`
- 狀態：隔離整合線已建立；尚未修改產品程式碼

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
- 1.x 的 P0 修復從 `main` 開獨立 hotfix 分支，發布後再同步至 `v2-development`。
- `v2.0.0` 只在 RC 與 Rhino / Octane 實機驗收完成、合回 `main` 後建立。

## Golden workflow 基準

開始修改對應功能前，使用隔離的 Rhino 8、Octane、測試 `.3dm`／scene 與輸出目錄，記錄以下現行結果：

- Models：來源材質狀態、取消／失敗、USDZ 後處理與最後有效輸出。
- Scatter：Block 位置／transform、單項失敗、重複同步與最後有效 USD。
- Point：特殊字元、中文、emoji、同名末層、stable ID 與 Lua consumer。
- Camera：event lifecycle、throttle、座標／焦距與 producer / consumer 狀態。
- Octane LiveLink：安裝、shortcut、module loading、reload 與錯誤輸入。
- Authoring tools：Auto Align、材質轉換、PBR / UV；2.0 核心重構期間不擴充功能。

實機結果與 fixture 路徑必須在相關批次開始前補入本文件；未驗證項目不得標記為通過。

## 第一階段順序

1. Models P0：不永久改來源 `MaterialSource`，後處理失敗不得回報成功。
2. Scatter P0：不移動原始 Block；保留最後有效輸出。
3. Installer P0：移除 `wmic`、備份名稱不碰撞、失敗可回復。
4. Rhino import spike、bootstrap、command catalog、foundation。
5. Models / Scatter safe exporter 與 atomic publisher。

## 驗證紀錄

| 日期 | 分支 / commit | 檢查 | 結果 | 限制 |
|---|---|---|---|---|
| 2026-08-12 | `v2-development` 建立基準 | Git 同步、Release ZIP 完整性與 SHA-256、6 支 Python 靜態語法、RHC XML | 通過 | Lua interpreter 不在 PATH；Rhino / Octane 實機流程由後續批次逐項驗證 |

## 下一步

依共同風險順序，優先從 `v2-development` 建立 `codex/v2-models-p0`；不在整合分支直接進行未分批的大型改寫。

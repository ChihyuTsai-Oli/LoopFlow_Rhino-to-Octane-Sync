# LoopFlow R2O 2.0 — 任務切分與開發路徑

本文件把 Rhino → Octane 2.0 重構拆成可在單一工作時段完成、驗證、提交與推送的工作單位。Python↔Lua 契約以 `_R2O_命名與資料契約.md` 為準；即時狀態只記錄於 `PROGRESS.md`。

## 執行規則

- 一次只修改一個 repo；同一 repo 同一時間只由一台電腦／一個 AI 作業。
- 每項任務從 `v2-development` 建立 `codex/v2-<scope>`，結束前完成檢查、commit、push 與交接。
- Rhino producer、Octane LiveLink、Octane authoring tools 是不同邊界，不在同一任務混入無關整理。
- 開發期 Rhino 按鈕指向 repo 的 `wip/src/rhino/entrypoints/`；正式安裝／RC 才使用隔離 `%APPDATA%`、Octane scripts、shortcut 與 scene。
- 下表可隨功能、路徑、Octane 相容性與實測結果調整；同步更新本文件、系統設定與 `PROGRESS.md`。

## 階段與任務

| ID | 任務／建議分支 scope | 前置 | 主要產出 | 完成檢查與安全停點 |
|---|---|---|---|---|
| R2O-A01 | 端到端工作流盤點／`workflow-inventory` | 無 | Models／Scatter／Point／Camera 至 Octane consumer 的輸入、輸出、state、副作用與失敗條件 | 可追溯至現行 Python／Lua；只改文件 |
| R2O-A02 | 指令、設定與檔案命名／`naming-contract` | A01 | command、`R2O_Path.txt`、檔案、資料夾、shortcut、顯示名稱與 migration 邊界 | 使用者可見變更已裁決；未定案明示 |
| R2O-A03 | Python↔Lua schema／`sync-schema` | A01–A02 | version、型別、座標、單位、escaping、session／document ID、成功條件 | Python producer／Lua consumer 共用 fixtures |
| R2O-A04 | Point／Octane ID 契約／`point-node-contract` | A01–A03 | full layer path、stable ID、display name、node／pin／state key | 同名、空名、特殊字元與未知 type 已定義 |
| R2O-A05 | Shortcut／Authoring 邊界／`octane-boundary` | A01–A02 | LiveLink、authoring tools、shortcut metadata 與 module loading 邊界 | 不把 authoring 工具變成同步主鏈依賴 |
| R2O-A06 | Golden fixtures／`contract-fixtures` | A03–A05 | Models、Scatter、Point 特殊字元、Camera、壞資料與預期輸出 | 不含私人 scene；兩端結果可機器比對 |
| R2O-B01 | 最小 source／測試骨架／`source-skeleton` | A02–A06 | Rhino／Octane source layout、schemas、entrypoints、tests | repo 入口可載入，不覆蓋穩定安裝 |
| R2O-B02 | 共用 foundation／`foundation-core` | B01 | result、stage、logging、version、config、path、atomic publish | Python 測試通過；Lua 契約有可執行備案 |
| R2O-B03 | Rhino document adapter／`rhino-platform` | B01–B02 | explicit source、temporary data、狀態 snapshot／restore | success／cancel／failure／interruption 測試 |
| R2O-B04 | Octane module loading spike／`octane-loading` | B01–B02、A05 | `require`／reload／bundle 路線與隔離載入方式 | 有 runtime 時實測；無 runtime 時限制明示 |
| R2O-C01 | Models producer／`models-producer` | A03、B02–B03 | temporary data → pending USDZ → postprocess → validate → replace | material source 不變、last good 保留 |
| R2O-C02 | Models Octane 接入／`models-consumer` | C01、B04 | Models LiveLink／載入邊界與 state | parse＋apply 成功才更新 state |
| R2O-C03 | Scatter producer／`scatter-producer` | A03、B02–B03 | 不移動來源 Block 的逐項發布 pipeline | 單項失敗不破壞其他輸出或來源 transform |
| R2O-C04 | Scatter Octane 接入／`scatter-consumer` | C03、B04 | Scatter consumer 與 node 更新 | 重複同步、刪除與未知 type 明確 |
| R2O-D01 | Point producer／`point-producer` | A03–A04、B02–B03 | versioned serializer、stable ID、escaping | 引號、反斜線、換行、中文、emoji、同名通過 |
| R2O-D02 | Point Lua consumer／`point-consumer` | D01、B04 | parse、apply、node collision 與 state | 壞檔不污染 scene 且可重試 |
| R2O-D03 | Camera producer／`camera-producer` | A03、B02–B03 | atomic payload、throttle／content diff 與入口 | 座標、焦距、event lifecycle 通過 |
| R2O-D04 | Camera Lua consumer／`camera-consumer` | D03、B04 | parse、apply、state 與錯誤處理 | 只有成功才更新 state |
| R2O-E01 | Rhino Open／Config／`rhino-diagnostics` | A02、B02 | Open／Config／診斷入口 | 路徑與錯誤可理解，不混入 Octane UI |
| R2O-E02 | Shortcut 安裝與 rescan／`shortcuts` | A05、B04 | metadata、open／setup、rescan 與版本對照 | 重複安裝保存使用者 shortcut |
| R2O-E03 | Event／state lifecycle／`sync-lifecycle` | C02、C04、D02、D04 | consumer 共通生命週期與 reload | 啟用、停用、壞檔、重試與中斷通過 |
| R2O-F01 | Authoring tools baseline／`authoring-baseline` | 主同步鏈穩定 | Auto Align、材質轉換、PBR／UV 現況契約與 fixtures | 不擴充功能，不阻塞 LiveLink |
| R2O-F02 | Authoring tools 整理／`authoring-structure` | F01 | node／material／shortcut 分群與必要共用 helper | 每個工具獨立驗證與提交 |
| R2O-G01 | Installer P0／`installer-safety` | B02、E02 | 移除 `wmic`、保存 Data／config／shortcut、rollback | 全新／重複／失敗安裝通過 |
| R2O-G02 | v1 migration／`migration` | schema 與 ID 穩定 | scanner、預覽、備份、converter、rollback | 只測資料副本，失敗可回復 |
| R2O-G03 | Version／Build／RHC／`build-release` | 核心功能完成 | version SSOT、compatibility matrix、RHC、ZIP、清單、SHA-256 | Rhino／Octane 路徑與資產一致 |
| R2O-G04 | Rhino → Octane RC／`rc-validation` | G01–G03 | 隔離環境完整驗收記錄 | Models／Scatter／Point／Camera 正常、取消、失敗、中斷與 last good 通過 |

## 建議開發波次

1. A01–A06：先鎖定 Python↔Lua、Point／node、shortcut 契約與 fixtures。
2. B01–B04：建立最小骨架並先證明 Rhino import 與 Octane loading 路線。
3. C01–C04：Models、Scatter 的資料安全 P0 與兩端接入。
4. D01–E03：Point、Camera、診斷、shortcut 與 lifecycle。
5. F01–F02：主鏈穩定後整理 authoring tools。
6. G01–G04：installer、migration、build、相容矩陣與 RC；最後才合入 `main`。

## 雙機換機檢查點

每次換機前確認工作樹乾淨、任務分支已 push、upstream 差距 `0/0`，並在 `PROGRESS.md` 記錄已驗證事實、限制與下一步。不可同時在兩台電腦修改本 repo；Octane shortcut、私人 `.3dm`／scene 與輸出產物不代替 Git 交接。

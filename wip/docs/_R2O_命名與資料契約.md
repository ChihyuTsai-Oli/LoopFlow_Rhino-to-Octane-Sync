# LoopFlow R2O — 命名與資料契約

本文件是 R2O 2.0 的指令、設定、Python↔Lua schema、Octane node 與跨軟體資料契約權威來源。程式架構建立前先完成盤點與裁決。

## 狀態

- 階段：**準備盤點／決策確認中**
- 套用版本：R2O `v2.0.0`
- 舊版參考：`v1.0.0`
- 原則：2.0 核心只使用新契約；舊版相容留在獨立 migration 邊界
- **尚待確認事項的唯一來源**：`前期規劃/資料生態決策表.md`
- 開發期 Rhino 指令與按鈕巨集：`rhino指令.md`

## 核心裁決

- Rhino producer、Octane LiveLink、Octane authoring tools 各自有清楚 namespace。
- Python 與 Lua 以語言中立 schema／fixtures 對齊，不各自猜測或複製規格。
- 2.0 不在核心散落 v1 alias、雙寫欄位或臨時 escaping。
- 正式 v1 安裝與輸出保持不動；2.0 使用隔離 scripts、data、RHC、shortcut、scene 與輸出。
- Octane `NT_*`、`P_*`、pin ID 等外部 API 名稱維持原文，文件用中文說明用途。
- **設定與即時檔路徑已定**：工作檔所在資料夾的 `_LoopFlow_Config/loopflow_R2O/`。父資料夾 `_LoopFlow_Config` 與 LoopFlow／R2B／QTY 共用，產品各用自己的子資料夾。已發布 1.x 的 AppData `Data\` 保持不動，2.0 一次切換。

## 必須盤點的命名層級

| 層級 | 範圍 |
|---|---|
| Rhino commands | Models、Scatter、Point、Camera、Open／Config |
| Config | `R2O_Path.txt` 欄位、型別、預設與使用者可調範圍 |
| Files | USD／USDZ、Camera／Point Lua data、log、pending、last good |
| Python↔Lua schema | version、欄位、型別、座標、單位、escaping、成功條件 |
| Point identity | full layer path、stable type ID、display name、同名處理 |
| Octane nodes | node graph、group、prefix、state key、event key |
| Shortcut | 顯示名稱、script path、metadata 與 rescan 流程 |
| Authoring tools | material／node／UV 工具 namespace |
| Version／build | RHC、installer、ZIP、schema 與 compatibility matrix |

## 依賴盤點格式

| 現行名稱 | 意義 | Python producer | Lua consumer | 儲存／註冊位置 | 衝突／問題 | 2.0 canonical 名稱 | 遷移方式 | 狀態 |
|---|---|---|---|---|---|---|---|---|
| 待盤點 |  |  |  |  |  |  |  | 未定案 |

## Python↔Lua schema 規則

- 每種資料有 `schema_version`、producer version 與 session／document identity。
- 定義欄位型別、必要值、空資料、座標系、單位與成功條件。
- 字串規格涵蓋引號、反斜線、換行、中文、emoji 與空名稱。
- terminal layer name 不作唯一 ID；stable ID 與 display name 分離。
- Lua consumer 只有 parse + apply 成功才更新 state。
- Python 與 Lua 使用同一組 fixtures／expected output。

## Octane 命名規則

- 對使用者顯示名稱、Octane node name、內部 stable ID 分開。
- `NT_*`、`P_*`、pin ID 是外部 API，不轉成使用者設定。
- LiveLink 與 authoring tools 不共用模糊的 global state／shortcut 名稱。
- node collision、重複同步、刪除與未知 type 都有明確行為。

## v1 → v2 遷移邊界

若需升級設定、shortcut 或場景，使用獨立 scanner／migration：

```text
掃描 v1 設定、輸出與 Octane scene
→ 顯示衝突與將修改項目
→ 備份
→ 一次轉換
→ 以 v2 Python／Lua fixtures 驗證
→ 失敗回復
```

2.0 一般同步指令不長期雙寫 v1／v2 格式。

## 定案門檻

- 三個產品邊界與 namespace 完成。
- 所有 Python↔Lua 欄位有型別、單位、escaping 與成功條件。
- Point stable ID、Octane node、shortcut 與檔名規則完成。
- schema、fixtures、compatibility matrix 與 migration 範圍完成。
- `_R2O_系統設定.md` 與 `_R2O_重構計畫.md` 已同步。

完成後才建立 2.0 bootstrap、command catalog 與新 source layout。

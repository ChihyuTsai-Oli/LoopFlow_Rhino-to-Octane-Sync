# R2O 2.0 — Rhino 指令與測試入口

本文件是**開發期 Rhino 測試按鈕**巨集與**全部 Rhino 指令名稱**的清單。方便在 Rhino 建立／核對按鈕。正式 command 契約仍以 `資料契約.md` 與 `前期規劃/資料生態決策表_三家建議.md` 裁決後回寫為準。

系統設定裡的「重構期間的 Rhino 測試入口」一節改為指向本檔；路徑或指令增減時**先改本檔**，再同步系統設定摘要與測試工具列。

## 規則

- 入口檔名＝開發期指令 ID。入口只轉交 command，不放業務邏輯。
- 巨集路徑指向**這台開發機**的 repo；換機只改路徑前綴，不改指令名稱。程式與契約不得寫死 Dropbox 或他機絕對路徑。
- 目前 `wip/src/rhino/entrypoints/` **尚未建立**；按鈕先照下列名稱建好，等入口檔落地即可跑。
- 改程式或入口後須**完全關掉 Rhino 再開**。
- 不要用已發布 1.x 工具列與 2.0 開發按鈕混著測同一案。
- 下列名稱是開發暫定，**不是**已凍結的 2.0 contract；若決策表改名，同步改本檔與入口檔名。

## 路徑前綴（本機）

```text
E:\_GitHub\LoopFlow_Rhino-to-Octane-Sync\wip\src\rhino\entrypoints\
```

## 全部 Rhino 指令（開發暫定）

| 指令 ID（入口檔名） | 顯示用途（暫） | 狀態 |
|---|---|---|
| `R2O_Models` | 發布／更新模型 USDZ | 暫定；入口未建 |
| `R2O_Scatter` | 發布 Block／家具實例 | 暫定；入口未建 |
| `R2O_Point` | 發布點位（燈／代理對齊） | 暫定；入口未建 |
| `R2O_Camera` | 發布相機資料 | 暫定；入口未建 |
| `R2O_Open` | 開啟設定／工作資料夾／說明 | 暫定；入口未建 |

是否改名、Authoring 是否另列 Rhino 指令 → 見決策表。

## 按鈕巨集（可直接貼上）

```text
R2O_Models
_-ScriptEditor _Run "E:\_GitHub\LoopFlow_Rhino-to-Octane-Sync\wip\src\rhino\entrypoints\R2O_Models.py"

R2O_Scatter
_-ScriptEditor _Run "E:\_GitHub\LoopFlow_Rhino-to-Octane-Sync\wip\src\rhino\entrypoints\R2O_Scatter.py"

R2O_Point
_-ScriptEditor _Run "E:\_GitHub\LoopFlow_Rhino-to-Octane-Sync\wip\src\rhino\entrypoints\R2O_Point.py"

R2O_Camera
_-ScriptEditor _Run "E:\_GitHub\LoopFlow_Rhino-to-Octane-Sync\wip\src\rhino\entrypoints\R2O_Camera.py"

R2O_Open
_-ScriptEditor _Run "E:\_GitHub\LoopFlow_Rhino-to-Octane-Sync\wip\src\rhino\entrypoints\R2O_Open.py"
```

## 不經 Rhino 按鈕

- Octane 測試入口：工作檔  
  `<LOOPFLOW_R2O_WORKFILES_ROOT>\_LoopFlow_Config\loopflow_R2O\lua\`  
  （家中：`E:\Dropbox (個人)\LoopFlow_Series\Workfiles\WIP_R2O\_LoopFlow_Config\loopflow_R2O\lua`）。  
  Git：`wip/src/octane/entrypoints\`；拷貝腳本 `wip/tools/deploy_dev_lua.ps1`。  
  檔：`R2O_Camera.lua`、`R2O_Point.lua`、`R2O_Open.lua`。不要蓋 1.x AppData。
- 不經上列 Rhino 巨集啟動。

## 變更紀錄

| 日期 | 說明 |
|---|---|
| 2026-08-29 | Octane 測試 Lua：工作檔 `_LoopFlow_Config/loopflow_R2O/lua`（Git 空殼＋deploy 腳本） |
| 2026-08-29 | 發布契約：Rhino yak 只含指令／RUI；Octane Lua 不進包 |
| 2026-08-28 | 註明 Octane stub Lua 入口測法（對齊 Rhino entrypoints） |
| 2026-08-27 | 初版：自系統設定抽出完整指令清單與巨集 |

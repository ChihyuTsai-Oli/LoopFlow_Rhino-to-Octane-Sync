# R2O 2.0 — Rhino 指令與測試入口

本文件是**開發期 Rhino 測試按鈕**巨集與**全部 Rhino 指令名稱**的清單。方便在 Rhino 建立／核對按鈕。正式 command 契約仍以 `資料契約.md` 為準。

系統設定裡的「重構期間的 Rhino 測試入口」一節改為指向本檔；路徑或指令增減時**先改本檔**，再同步系統設定摘要與測試工具列。

## 規則

- 入口檔名＝開發期指令 ID。入口只轉交 command，不放業務邏輯。
- 巨集路徑指向**這台開發機**的 repo；換機只改路徑前綴，不改指令名稱。程式與契約不得寫死 Dropbox 或他機絕對路徑。
- 改程式或入口後須**完全關掉 Rhino 再開**。
- 同一 Rhino 可測 R2B 與 R2O：每個入口會清掉對方的 `rhino`／`foundation` 快取。仍須關再開才載入最新腳本。
- 不要用已發布 1.x 工具列與 2.0 開發按鈕混著測同一案。
- `ROCamera`／`ROCameraPush`／`ROPoint`／`ROModels`／`ROObjects`／`ROOpen` **已凍結**（2026-08-29 自 `R2O_*` 改連寫）。Octane Lua 檔名仍是 `R2O_*.lua`。

## 路徑前綴（本機）

```text
E:\_GitHub\LoopFlow_Rhino-to-Octane-Sync\wip\src\rhino\entrypoints\
```

## 全部 Rhino 指令

| 指令 ID（入口檔名） | 顯示用途 | 狀態 |
|---|---|---|
| `ROCamera` | 開／關相機持續發布 | **已凍結**；入口已接 |
| `ROCameraPush` | 手動推送 camera.json 一次 | **已凍結**；入口已接 |
| `ROModels` | 發布／更新模型 USDZ | **已凍結**；入口已接 |
| `ROObjects` | 發布選取組件 USDZ | **已凍結**；入口已接 |
| `ROPoint` | 發布點位（燈／代理對齊） | **已凍結**；入口已接 |
| `ROOpen` | Open / Health；Open Docs | **已接**；四顆等寬：Config／live／models／Docs |

## 開發按鈕巨集（ScriptEditor，可直接貼上）

**正式工具列不要用下面這段。** 正式左鍵請用下一節 `! _ROCamera` 等。

```text
ROCamera
_-ScriptEditor _Run "E:\_GitHub\LoopFlow_Rhino-to-Octane-Sync\wip\src\rhino\entrypoints\ROCamera.py"

ROCameraPush
_-ScriptEditor _Run "E:\_GitHub\LoopFlow_Rhino-to-Octane-Sync\wip\src\rhino\entrypoints\ROCameraPush.py"

ROModels
_-ScriptEditor _Run "E:\_GitHub\LoopFlow_Rhino-to-Octane-Sync\wip\src\rhino\entrypoints\ROModels.py"

ROObjects
_-ScriptEditor _Run "E:\_GitHub\LoopFlow_Rhino-to-Octane-Sync\wip\src\rhino\entrypoints\ROObjects.py"

ROPoint
_-ScriptEditor _Run "E:\_GitHub\LoopFlow_Rhino-to-Octane-Sync\wip\src\rhino\entrypoints\ROPoint.py"

ROOpen
_-ScriptEditor _Run "E:\_GitHub\LoopFlow_Rhino-to-Octane-Sync\wip\src\rhino\entrypoints\ROOpen.py"
```

## 正式工具列巨集（yak 裝上之後）

左鍵填這些；右鍵留空。指令尚未登錄前按了不會動。RUI 請 `ExportRuiFile` 存到 `wip/docs/toolbar/`。Authoring 不要做成 Rhino 按鈕。

```text
! _ROCamera
! _ROCameraPush
! _ROModels
! _ROObjects
! _ROPoint
! _ROOpen
```

## 相機實機（英文介面）

1. 先存 `.3dm`（未存檔會停）。作用中視埠必須是 Perspective。
2. Rhino：`ROCamera` 開持續寫 `_LoopFlow_Config/loopflow_R2O/live/camera.json`。
3. OctaneRender Studio+ 2026.4：跑測檔根 `lua\R2O_Camera.lua`（Ctrl+Q）。**沒有視窗**；套用一次後腳本結束，Octane 可繼續操作。
4. 場景恰好一台已 Expand 的 Thin Lens。轉 Rhino 視角後再按一次 Ctrl+Q 才會跟上。
5. 熱鍵：跑 `__Open_Shortcuts.lua` 編輯 `R2O_Shortcuts.txt` → 跑 `__Setup_Shortcuts.lua` → 重掃 Octane 腳本資料夾。deploy Lua 後須再跑 Setup。

## 模型實機（英文介面）

1. 先存 `.3dm`。建築等實模放在要匯出的父圖層（含子圖層；例如 `R2O::MDL::Architecture`）。不想匯出的圖層名稱加 `//`。
2. 若 Rhino 已開著舊腳本：先關再開，再跑 `ROModels`。應連續出現三個視窗：Exclude Token → 圖層樹 → 幾何類別（Point／Curve 預設不勾）。寫 `_LoopFlow_Config/loopflow_R2O/models/R2O.usdz`。不自動存檔；隱藏／鎖定也會匯出。
3. OctaneRender Studio+ 2026.4：**沒有** Models 腳本。第一次把場景載入這份 `R2O.usdz` 並接材質。接口＝Rhino **材質名稱**：不同圖層／物件只要名稱相同就是同一個接口。
4. 再改幾何、再跑 `ROModels` 覆寫同一檔。Octane **不要**按 Reload mesh／Load new mesh；**關掉再開**，已連結的 USDZ 會自己跟上；材質名不變則接線應仍在。失敗時舊 `R2O.usdz` 應仍在。Camera／Point 檔不該被刪。

## 點位實機（英文介面）

1. 先存 `.3dm`。點或 Block 放在 `R2O::` 子圖層（例如 `R2O::LT_Points::Downlight`）。
2. Rhino：`ROPoint` 寫 `_LoopFlow_Config/loopflow_R2O/live/point.json`。
3. OctaneRender Studio+ 2026.4：跑測檔根 `lua\R2O_Point.lua`（無預設熱鍵）。套用一次後腳本結束。
4. Scatter 應出現在**場景根**（可接 Geometry，不必炸開）。第二次跑腳本應出現 `[Update]` 與 `xyz=`。已接好的 Proxy 不該被拆掉。刪掉 Rhino 某類型後再跑一次，對應受管節點應被刪。舊的空 `R2O_Point` 群組可手動刪。
5. 不要與 1.x 舊節點名混用。deploy Lua 後若改過熱鍵表，再跑 Setup。

## 選取組件 Objects 實機（英文介面）

1. 先存 `.3dm`。資產 Block 建議在 `USD::`。
2. **先選物件**，再跑 `ROObjects`。沒選就應擋住。寫 `_LoopFlow_Config/loopflow_R2O/models/R2O_Objects_YYMMDD_時分秒.usdz`。不覆蓋舊檔。跑完物件應仍在原位，檔案不該被自動存檔。
3. Octane：**沒有** Objects 腳本。自己載入這份新 USDZ。不要 Reload／Load new mesh。

## Authoring 實機（英文介面；不擴功能）

1. 跑 `wip/tools/deploy_dev_lua.ps1` 把 Git Lua 拷到測檔根 `lua\`。**已存在的 `R2O_Shortcuts.txt` 不會被覆蓋**；若該表沒有 Auto 四行，用編輯器補上（見 `資料契約.md`）或刪掉該表再 deploy。
2. OctaneRender Studio+ 2026.4：跑 `__Setup_Shortcuts.lua`，再重掃腳本資料夾。
3. 四支操作（家中 **已通過**）：
   - `Auto_Align_Nodes`（Alt+A）：選取要對齊的 nodes 後執行，並設定間距。
   - `Auto_Convert_StdSurf_to_Universal`（Shift+M）：選取 USDZ node 後執行，將所有材質轉換為 Universal。
   - `Auto_PBR_Universal`（Ctrl+Shift+T）：執行後彈窗選擇 PBR 貼圖資料夾，自動建立打包好的材質球。
   - `Auto_PBR_Switch_UV`（Ctrl+T）：在 `Auto_PBR_Universal` 材質球內，任選一個 node 後執行，切換 UV 模式。

## Open／Health 實機（英文介面）

1. 先存 `.3dm`。關再開 Rhino 後跑 `ROOpen`。
2. 應出現英文對話框：摘要含 Config 路徑、Camera／Point／Models／Objects 時間。四顆等寬按鈕 **Open Config → Open live → Open models → Open Docs**。
3. 未存檔應擋住。不該改來源 `.3dm`、不該寫交換檔。
4. **Open Docs** 開 GitHub `docs/README.md`（開發期 `v2-development`）。合入整合分支前該頁可能還不在遠端。

## 不經 Rhino 按鈕

- Octane 測試入口：工作檔  
  `<LOOPFLOW_R2O_WORKFILES_ROOT>\_LoopFlow_Config\loopflow_R2O\lua\`  
  （家中：`E:\Dropbox (個人)\LoopFlow_Series\Workfiles\WIP_R2O\_LoopFlow_Config\loopflow_R2O\lua`）。  
  Git：`wip/src/octane/entrypoints\`；拷貝腳本 `wip/tools/deploy_dev_lua.ps1`。  
  檔：`R2O_Camera.lua`、`R2O_Point.lua`（已接功能）、`R2O_Open.lua`、`__Open_Shortcuts.lua`、`__Setup_Shortcuts.lua`、`R2O_Shortcuts.txt`、Authoring 四支 `Auto_*.lua`（1.x 原樣）。不要蓋 1.x AppData。

## 變更紀錄

| 日期 | 說明 |
|---|---|
| 2026-08-30 | G02：正式工具列巨集 `! _ROCamera` 等；開發 ScriptEditor 巨集分開寫 |
| 2026-08-29 | Authoring 四支 Auto 家中實機通過；操作說明寫入工作流程／契約 |
| 2026-08-29 | `ROOpen`：Health 摘要＋四顆等寬 Config／live／models／Docs（GitHub `docs/README.md`） |
| 2026-08-29 | Rhino 指令改連寫：`ROCamera`／`ROCameraPush`／`ROModels`／`ROObjects`／`ROPoint`／`ROOpen`（Lua 檔名不變） |
| 2026-08-29 | `_-Export` 一律 TEMP `R2O.usdz` 再拷 pending（不再用 8.3 原地寫） |
| 2026-08-29 | 入口隔離 R2B／R2O；USDZ 內檔改 `R2O.usda`（勿留 `_pending`） |
| 2026-08-29 | Objects：`ROObjects`／`models/R2O_Objects_時戳.usdz`；Models 曾用 `R2O_Models.usdz` |
| 2026-08-29 | Models 合入 `v2-development` |
| 2026-08-29 | Models 更新：關再開 Octane；不要 Reload／Load new mesh（2026.4 限制） |
| 2026-08-29 | Models 三步視窗＋`_-Export` 走 8.3／TEMP（修括號路徑寫不出） |
| 2026-08-29 | Models：`ROModels`／`models/models.usdz`；Octane 手動置換 |
| 2026-08-29 | 相機＋點位合入 `v2-development` |
| 2026-08-29 | 點位實機通過：場景根 Scatter；第二次套用有更新 |
| 2026-08-29 | Point Scatter 改放場景根（有接腳、不必炸開）；受管＝前綴 |
| 2026-08-29 | 第二次套用改從整場找 Scatter 再 Update（對齊 1.x） |
| 2026-08-29 | Point 兩端：`ROPoint`／`live/point.json`；Octane 套用一次 |
| 2026-08-29 | 熱鍵實機通過；新增功能先填 1.x 預設鍵 |
| 2026-08-29 | LiveLink 熱鍵：`__Open_Shortcuts.lua`／`__Setup_Shortcuts.lua`；相機中文路徑已通過 |
| 2026-08-29 | Octane 相機改回 Ctrl+Q 套用一次（realtime 會鎖 UI） |
| 2026-08-29 | Octane 測試 Lua：工作檔 `_LoopFlow_Config/loopflow_R2O/lua`（Git 空殼＋deploy 腳本） |
| 2026-08-29 | 發布契約：Rhino yak 只含指令／RUI；Octane Lua 不進包 |
| 2026-08-28 | 註明 Octane stub Lua 入口測法（對齊 Rhino entrypoints） |
| 2026-08-27 | 初版：自系統設定抽出完整指令清單與巨集 |

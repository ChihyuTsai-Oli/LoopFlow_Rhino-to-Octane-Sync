# LoopFlow R2O 指令逐項說明

> 同一專案不要混用舊版的工具列、套件或 Octane Lua。
>
> 整體流程見 [使用說明總覽](./USER_GUIDE_zh-TW.md)。指令名稱是 Rhino 命令列裡的正式名稱（連寫，例如 `ROModels`）。
>
> Rhino 對話框為英文。Octane Lua 檔名仍是 `R2O_*.lua`。

## 專案資料夾原則

開始前先把 `.3dm` 存檔。**`.3dm` 所在資料夾就是作業資料夾**；交換檔在同層 `_LoopFlow_Config/loopflow_R2O/`。整包搬到其他磁碟或電腦仍可使用，不必改絕對路徑。

## 快速索引

| 階段 | Rhino | Octane | 一句話 |
|---|---|---|---|
| 開案 | `ROOpen` | （無） | 看設定根與上次成功時間；開資料夾或本說明 |
| 主模型 | `ROModels` | 載入／關再開 `R2O.usdz` | 選圖層匯出有材質的 USDZ |
| 選取物件 | `ROObjects` | 自行載入時戳 USDZ | 目前選取 → 時戳 USDZ |
| 相機 | `ROCamera`／`ROCameraPush` | `R2O_Camera.lua`（Ctrl+Q） | 作用視角寫到 `live/camera.json`，Octane 套用一次 |
| 點位 | `ROPoint` | `R2O_Point.lua` | `R2O::` 上的 Point／Block 寫到 `live/point.json` |
| 著色輔助 | （無） | Authoring 四支 Auto | 對齊節點、轉 Universal、建 PBR、切 UV |

工具列四顆鈕，左鍵／右鍵：

| 鈕 | 左鍵 | 右鍵 |
|---|---|---|
| 1 | `ROOpen` | — |
| 2 | `ROModels` | `ROObjects` |
| 3 | `ROCamera` | `ROCameraPush` |
| 4 | `ROPoint` | — |

## 目錄

[01 開啟設定與說明](#01-開啟設定與說明) · [02 主模型](#02-主模型) · [03 選取物件](#03-選取物件) · [04 相機](#04-相機) · [05 點位](#05-點位) · [06 Octane Lua](#06-octane-lua) · [07 Authoring](#07-authoring) · [08 不要做的事](#08-不要做的事)

---

## 01　開啟設定與說明

**指令**：`ROOpen`

已存檔後執行。跳出英文 Health 視窗，四顆等寬按鈕由左到右：

- **Open Config** — 開啟 `_LoopFlow_Config/loopflow_R2O/`
- **Open live** — 相機／點位 JSON
- **Open models** — `R2O.usdz` 與選取物件檔
- **Open Docs** — 本 GitHub 文件入口

摘要會列出設定根路徑，以及 Camera／Point／Models／Objects 上次成功寫出的時間。未存檔會被擋住。

Octane 目前沒有對等的 Health 面板。

---

## 02　主模型

**指令**：`ROModels`

匯出給 Octane 主同步用的乾淨 USDZ（**有材質**）。

1. 檔案須已存檔。
2. 可輸入排除標記（預設 `//`；空白＝不排除）。圖層路徑含此文字者不匯出。
3. 選要匯出的圖層（含子層，可捲動）。
4. 勾選幾何類別。同一 Rhino 視窗會記住上次成功的勾選；第一次時 Point／Curve 預設不勾。
5. 成功後寫入 `models/R2O.usdz`。失敗不會蓋掉上次成功的檔。來源 Rhino 檔會回到執行前的狀態。

隱藏或鎖定的物件也會匯出。過程**不會**自動存來源 `.3dm`。

Octane：**沒有** Models 腳本。第一次把場景載入這份 `R2O.usdz` 並接材質。接口＝Rhino **材質名稱**；不同圖層／物件只要名稱相同就是同一個接口。之後再跑 `ROModels` 覆寫同一檔時，**不要**按 Reload mesh／Load new mesh；**關掉 Octane 再開**，已連結的 USDZ 會自己跟上。這是 Studio+ 2026.4 的限制。

改 Rhino 材質名＝新接口，舊接線對不上。

---

## 03　選取物件

**指令**：`ROObjects`

把**目前選取**匯成 USDZ，給 Octane 自行載入當組件。

- 每次新檔：`models/R2O_Objects_年月日_時分秒.usdz`，不覆蓋舊檔
- **先選再跑**；沒選就會被擋住
- 不限 Block；**不搬原點**

資產 Block 建議放在 `USD::`（不要放在 `R2O::`），才不會被點位掃進去。

Octane：**沒有** Objects 腳本。自己載入這份新 USDZ。不要 Reload／Load new mesh。

不要把 `R2O.usdz` 當組件檔交叉使用，也不要把時戳檔當主模型去關再開期待不斷線。

---

## 04　相機

**指令**：`ROCamera`（開／關持續寫出）、`ROCameraPush`（手動推一次）

- 用透視作用視角；不是透視就停止
- 檔案須已存檔
- 寫入 `live/camera.json`
- 再開一次 `ROCamera` 就停止持續寫出

Octane：跑 `R2O_Camera.lua`（預設 Ctrl+Q）。**套用目前檔一次即結束**，不是開著一直跟。場景必須恰好一台已從 Render Target Expand 出來的 Thin Lens。轉完 Rhino 視角後再按一次 Ctrl+Q 才會跟上。

---

## 05　點位

**指令**：`ROPoint`

掃 **`R2O::` 子圖層**上的 Point 與 Block（含子層；含隱藏／鎖定）。父層 `R2O` 本身不要放點。`USD::` 下的資產 Block 不會被掃到。

**Rhino 圖層範例**

| 圖層 | 放什麼 | 會同步？ |
|---|---|---|
| `R2O`（根） | 不要放 Point／Block | 否 |
| `R2O::LT_Points::Downlight` | Point | 是；類型跟完整圖層路徑走 |
| `R2O::FUR_Points::Sofa_A` | Block | 是；帶變換 |

寫入 `live/point.json`。

Octane：跑 `R2O_Point.lua`（無預設熱鍵）。**套用一次即結束**。Scatter 出現在**場景根**，前綴 `R2O_Point_`，可直接接 Geometry。已接好的 Proxy 不會被拆掉。Rhino 刪掉某類型後再套用一次，對應受管節點會被刪。場景裡若還有空的 `R2O_Point` 群組，可手動刪。

建給 Scatter 用的 Block：先在世界裡擺正，再以世界原點當插入點建立 Block。

---

## 06　Octane Lua

腳本放在專案 `_LoopFlow_Config/loopflow_R2O/lua/`。熱鍵表是同層 `R2O_Shortcuts.txt`。

1. 把 Git 上的 Lua 拷到該資料夾。
2. 需要改鍵時跑 `__Open_Shortcuts.lua` 編輯表。
3. 跑 `__Setup_Shortcuts.lua`，再重掃 Octane 腳本資料夾。

| 腳本 | 熱鍵 | 說明 |
|---|---|---|
| `R2O_Camera.lua` | Ctrl+Q | 套用相機一次 |
| `R2O_Point.lua` | （無預設） | 套用點位一次 |
| `R2O_Open.lua` | — | 目前空殼 |

主模型與選取物件**沒有** LiveLink 腳本。

---

## 07　Authoring

著色輔助，與相機／點位同步分開。不進 Rhino 工具列，也不進 `.yak`。

| 腳本 | 熱鍵 | 說明 |
|---|---|---|
| `Auto_Align_Nodes` | Alt+A | 選好節點後對齊並設間距 |
| `Auto_Convert_StdSurf_to_Universal` | Shift+M | 選 USDZ 節點，把材質轉成 Universal |
| `Auto_PBR_Universal` | Ctrl+Shift+T | 選 PBR 資料夾，自動建材質球 |
| `Auto_PBR_Switch_UV` | Ctrl+T | 在上述材質球內切 UV 模式 |

---

## 08　不要做的事

- 未存檔就按發布
- 更新主模型時按 Reload mesh／Load new mesh（請關再開）
- 把 `R2O.usdz` 與時戳組件檔交叉當對方用
- 在 Blender 流程裡期待這套 Octane 按鈕
- 為了同步去改來源 `.3dm` 的檔名或把作業檔存成中間檔

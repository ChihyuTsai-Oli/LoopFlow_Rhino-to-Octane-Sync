# LoopFlow R2O 使用說明

> Rhino 端指令在 Rhino 8 (CPython 3.9) 環境中執行。
> Octane 端工具為 LUA 腳本，需在 OctaneRender Standalone 中設定腳本路徑並完成熱鍵綁定。

最後更新：2026-04-28

---

## 目錄

1. [Rhino 端指令](#rhino-端指令)
2. [Octane 端 — 同步功能](#octane-端--同步功能)
3. [Octane 端 — 輔助工具](#octane-端--輔助工具)
4. [設定檔](#設定檔)

---

## Rhino 端指令

---

### R2O_Models（模型同步）

一鍵匯出選定圖層的 USDZ 模型。

**執行流程：**

1. 若 Rhino 檔案已存檔，自動儲存一次
2. 跳出圖層選擇視窗，選取要匯出的父圖層（記住上次選取）
3. 忽略圖層與物件的隱藏、鎖定狀態，強制匯出所有可渲染幾何（Brep / Mesh / SubD / Block）
4. 強制將物件材質來源改為「圖層」，確保 UUID 與圖層名稱綁定
5. 執行前快照狀態，匯出後自動還原所有圖層與物件狀態

**材質不斷線的關鍵：**

USDZ 以圖層名稱對應 USD Prim Path，決定 UUID。只要圖層名稱不變，UUID 就不變，Octane 中已接好的材質就不斷線。

> **圖層命名注意**：重新命名圖層會改變 UUID，導致材質需重新綁定。如需重構圖層結構，請在開始 Render 作業前確定命名。

---

### R2O_Camera（相機即時同步）

Toggle 設計：執行一次開始同步，再次執行停止。

- 偵測 Rhino 視窗旋轉或縮放事件即即時寫出相機資料（每 0.2 秒最多寫出一次）
- 輸出格式為 LUA（`R2O_Camera_Sync_Data.lua`），供 Octane 端 `LiveLink_R2O_Camera.lua` 讀取
- 座標系自動轉換（Rhino Y-up → Octane Y-up / Z-forward），並以 Rhino 單位縮放至公尺
- 不需要儲存 Rhino 檔案即可同步

> **停止方式**：再次執行 R2O_Camera 指令即可停止背景監聽。

---

### R2O_Point（燈光與家具位置同步）

掃描場景中的 Points 與 Blocks，輸出位置與旋轉矩陣資料，供 Octane Scatter 節點使用。

- 讀取設定中 `PointLayer` 指定的圖層前綴（預設：`R2O`）
- **子圖層名稱**作為 Scatter 節點類型（`type`），Octane 端依此對應燈具或家具 Proxy
- **Point 物件**：傳遞位置，使用單位矩陣旋轉
- **Block 物件**：傳遞完整變換矩陣（含縮放與旋轉）
- 輸出 `R2O_Point_Sync_Data.lua`

**圖層命名範例：**

```
R2O/
  LT_Points/
    Downlight        ← type = "Downlight" → Octane 中的 Scatter 節點
    WallLight
  FUR_Points/
    Sofa_A           ← type = "Sofa_A" → 家具 Proxy
    Table_B
```

> **命名唯一性**：不同父圖層下若有相同的終端子圖層名稱（例如 `R2O::LT::Chair` 與 `R2O::FUR::Chair`），會合併至同一個 Scatter 節點。確保終端名稱全域唯一。

---

### R2O_Scatter（Block USD 匯出）

將選取的 Block 物件匯出為獨立的 `.usd` 檔案，作為 Octane Scatter 的 Proxy 來源。

**執行流程：**

1. 在 Rhino 中選取一個或多個 Block 物件（支援預選）
2. 腳本驗證所有選取物件均為 Block；若包含非 Block 物件則中止並警告
3. 選擇 USD 匯出目標資料夾
4. 對每個唯一的 Block 定義（相同名稱只匯出一次）：
  - 將 Block 移至世界原點後匯出為 `{BlockName}.usd`
  - 匯出完成後還原原始位置

> **重要**：Block 內部幾何的原點必須對齊世界原點 `(0,0,0)`，Scatter 旋轉軸才會正確。
>
> Block 可放在 `USD::<名稱>` 圖層（不在 `R2O::` 下），這樣 R2O_Point 不會將它當作同步點位。

---

### R2O_Open（快速開啟工具）

從 Rhino 指令列快速開啟相關檔案。


| 選項             | 說明                                 |
| -------------- | ---------------------------------- |
| **Config**     | 開啟 `R2O_Path.txt` 設定檔              |
| **DataFolder** | 開啟資料目錄                             |
| **DebugLog**   | 開啟 `cursor_R2O_debug_log.txt` 除錯記錄 |


---

## Octane 端 — 同步功能

---

### LiveLink_R2O_Camera.lua

讀取 Rhino 端寫出的相機同步檔，更新 Octane 場景中的 Thin Lens Camera。

**預設熱鍵：** `Ctrl + Q`

**使用方式：**

1. Rhino 端啟動 `R2O_Camera` 即時同步（保持運行中）
2. 在 Octane 中按下 `Ctrl + Q`，套用目前最新的相機視角

> **注意**：Thin Lens Camera 節點必須從 Render Target 中**展開**為獨立節點（Expand out），腳本才能找到並操作它；收折在 Render Target 內的相機無法被讀取。

---

### LiveLink_R2O_Point.lua

讀取 Rhino 端寫出的 Points 同步檔，在 Octane 場景中建立或更新 Scatter 節點。

**使用方式：**

1. Rhino 端執行 `R2O_Point` 匯出同步資料
2. 在 Octane 中執行此腳本，Scatter 節點自動建立或更新

**節點管理邏輯：**

- **已有節點**：直接更新 Transform 資料，不移動位置（保留使用者的節點連接）
- **新增節點**：在設定中 `PointNgName` 指定的 Group（預設：`R2O_Point`）內建立
- **已移除類型**：只清除 Group 內的孤立節點，不影響 Group 外的節點

---

## Octane 端 — 輔助工具

以下工具與 R2O 同步流程無關，可獨立使用。

---

### Auto_PBR_Universal.lua（PBR 材質自動建置）

**預設熱鍵：** `Ctrl + Shift + T`

選取紋理資料夾，自動識別並建立 Universal Material，打包為 Nodegraph。

- 自動辨識 PBR 貼圖類型（Albedo、Roughness、Normal、Metallic、Displacement 等）
- 自動建立 Box Projection + 3D Transform 節點組
- Displacement 貼圖建立獨立節點（Group B），不自動連接至材質，手動連接
- Nodegraph 預設材質名稱取自貼圖檔名前綴
- 記住上次選取的資料夾路徑
- 支援 ACEScg（預設）或 sRGB 色彩工作流（修改 `CS_COLOR` 變數）

> **Spawn 位置**：執行前先選取場景中任一節點，新 Nodegraph 會產生在該節點右側。

---

### Auto_PBR_Switch_UV.lua（UV 模式切換）

**預設熱鍵：** `Ctrl + T`

切換 `Auto_PBR_Universal` 建立的 Nodegraph 的 UV 投影模式。


| 模式                         | 說明                                 |
| -------------------------- | ---------------------------------- |
| **Mode 1（Box Projection）** | 貼圖透過 BoxProjection → Transform（預設） |
| **Mode 2（UV Transform）**   | 貼圖直接透過 Transform，斷開 BoxProjection  |


選取方式（任一均可）：

- 選取目標 Nodegraph
- 選取 Nodegraph 內任一節點
- 選取 Canvas 上的 Universal Material 節點
- 在 Nodegraph 內的 Canvas 中無選取狀態下執行

---

### Auto_Convert_StdSurf_to_Universal.lua（材質格式轉換）

**預設熱鍵：** `Shift + M`

將選取的 USD 幾何節點中的 Standard Surface 材質轉換為 Universal Material。

- 自動備份 Texture 路徑、顏色值等資訊，建立新 Universal Material 後還原
- 相同 Pin ID 的節點自動繼承；需 Remap 的 Pin（如 Base Color → Albedo）重建連接
- IOR 值自動對應至 Universal Material 的 IOR Pin
- 適用於從外部 USD 資產匯入後，一鍵轉換材質格式

---

### Auto_Align_Nodes.lua（節點自動對齊）

**預設熱鍵：** `Alt + A`

選取至少 2 個節點後執行，對齊至同一水平基準線，並依 X 位置由左至右排列。

- 執行前跳出對話框，輸入節點間距（px，可為負值以重疊排列，預設 `-10`）
- 水平基準依最上方節點的 Y 座標對齊

---

## 設定檔

### `R2O_Path.txt`（位於 `%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\`）

首次執行時自動建立，欄位缺失時自動補全。


| 欄位               | 預設值                        | 說明                          |
| ---------------- | -------------------------- | --------------------------- |
| `DataPath`       | （自動）                       | 資料輸出根目錄                     |
| `ModelDir`       | （空白）                       | USDZ 模型輸出目錄；空白時退回至 DataPath |
| `PointLayer`     | `R2O`                      | Points / Blocks 同步圖層根前綴     |
| `ModelFile`      | `R2O.usdz`                 | USDZ 模型輸出檔名稱                |
| `CameraFile`     | `R2O_Camera_Sync_Data.lua` | 相機同步 LUA 檔名稱                |
| `PointFile`      | `R2O_Point_Sync_Data.lua`  | Points 同步 LUA 檔名稱           |
| `PointNgName`    | `R2O_Point`                | Octane 端 Scatter 群組節點名稱     |
| `PointPrefix`    | `R2O_Point`_               | Scatter 節點名稱前綴              |
| `LastModelLayer` | （自動）                       | 記住上次模型匯出選取的圖層               |


> 使用 `R2O_Open > Config` 可直接從 Rhino 指令列開啟此檔案。
> Octane 端 LUA 腳本讀取相同的 `R2O_Path.txt`，因此 Rhino 與 Octane 共用同一份設定。


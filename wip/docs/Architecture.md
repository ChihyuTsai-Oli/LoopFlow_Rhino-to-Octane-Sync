# LoopFlow R2O 2.0 — 邏輯架構

> 用 ASCII 圖說明 R2O 整體是怎麼組成的，輔助閱讀，**不是規格**。
> 內容整理自 `實作總覽.md`、`工作流程.md` 與實際程式目錄；若與六份實作文件不同，以六份為準。
> 中文字在等寬字型下寬度不一，方框右側刻意不封邊，避免歪掉。

---

## 一、產品邊界：兩端靠「檔案」溝通

```
+----------------------------+        +-----------------------+        +-----------------------------+
| Rhino 端（發布者）         |        | 交換檔                |        | Octane 端（接收者）
| 指令 ROModels、ROCamera…   | -----> | 放在工作檔旁的        | -----> | Lua 腳本，手動執行
| 只負責「安全地寫出檔案」   |  寫出  | _LoopFlow_Config/     |  讀取  | 每跑一次＝套用一次
| 不含任何 Octane 邏輯       |        | loopflow_R2O/         |        | （Octane 無法不鎖畫面做即時）
+----------------------------+        +-----------------------+        +-----------------------------+
              |                                                                    ^
              +--> 本機指標 %APPDATA%\LoopFlow\R2O\current_project.json ----------+
                   告訴 Lua「目前是哪個專案」，不是交換檔

主鏈之外（獨立，不讀交換檔）：
+--------------------------------------------------------------------------+
| Authoring 四支 Auto（Octane Lua，自 1.x 原樣保留，2.0 不擴充功能）
|   Auto_Align_Nodes                    對齊節點
|   Auto_Convert_StdSurf_to_Universal   材質轉成 Universal
|   Auto_PBR_Universal                  選貼圖資料夾自動建材質球
|   Auto_PBR_Switch_UV                  切換 UV 模式
+--------------------------------------------------------------------------+
```

---

## 二、五條通道

```
通道      Rhino 指令                交換檔                               Octane 端
--------  ------------------------  -----------------------------------  ---------------------------
Models    ROModels                  models/R2O.usdz                      沒有 Lua
主模型    排除記號 --> 圖層樹       每次覆寫同一檔                       第一次手動載入並接材質
          --> 幾何類別                                                   之後「關掉 Octane 再開」重讀
                                                                         （不要按 Reload mesh）

Objects   ROObjects                 models/R2O_Objects_時戳.usdz         沒有 Lua
選取物件  先選取再匯出              每次新檔、不覆蓋                     自己載入當組件

Camera    ROCamera（持續發布）      live/camera.json                     R2O_Camera.lua（Ctrl+Q）
相機      ROCameraPush（推一次）                                         套用一次即結束
                                                                         場景須恰好一台獨立相機

Point     ROPoint                   live/point.json                      R2O_Point.lua
點位      掃 R2O:: 子圖層的                                              套用一次即結束
          Point 與 Block                                                 在場景根建立／更新 Scatter
                                                                         已刪的類型下次套用時清掉

Open      ROOpen                    （不寫交換檔）                       無（R2O_Open.lua 仍是空殼）
健康檢查  顯示路徑與各通道
          最後成功時間
```

接材質的規則：Octane 的接口跟 **Rhino 材質名稱** 走，同名＝同一接口；改名＝新接口。

---

## 三、安全發布：寧可不更新，也不留半套

```
USDZ（Models、Objects）

  [Rhino _-Export 到 %TEMP%] --> [拷成 pending] --> [材質提升後處理] --> [驗證] --> [原子替換成正式檔]
               |                        |                   |                |
               +------------ 任一步失敗／取消 --------------+----------------+
                                        |
                                        v
                    正式檔（last-good）完全不動，來源 .3dm 狀態還原

JSON（Camera、Point）

  [寫 pending] --> [原子替換成 camera.json／point.json] --> [更新本機指標]

  相機持續發布時另有節流：姿態沒變就略過，連續變動約 0.2 秒合併一次
  Octane Lua 讀到半寫或讀不懂的檔 --> 不套用

共同規則：工作檔沒存檔就不發布；空圖層、取消、沒勾類別都停止。
例外：Point 的空清單仍會發布，用來清掉已刪除的類型。
```

---

## 四、程式分層（`wip/src/`）

```
+--------------------------------------------------------------------------+
| Rhino 端  src/rhino/
|
|   entrypoints/   每支指令一個檔（ROModels.py …），只轉交
|        |
|        v
|   commands/      各通道的實際流程
|                  models   主模型      objects  選取物件
|                  camera   相機        point    點位
|                  open     健康檢查
|        |
|        v
|   layer_collect  依圖層收集物件
|   ui/            layer_picker 階層圖層樹選擇視窗
+--------------------------------------------------------------------------+
                  |
                  v
+--------------------------------------------------------------------------+
| 共用基礎  src/foundation/   （不依賴 Rhino，可單獨測試）
|
|   camera_payload／point_payload   交換檔格式
|   camera_math／point_math         座標與鏡頭換算
|   camera_hotpath                  相機持續發布的節流判斷
|   export_cmd                      給 Rhino 匯出用的暫存路徑（避開中文路徑）
|   usdz_postprocess                USDZ 材質提升後處理
|   atomic     安全寫檔             pointer   本機專案指標
|   paths      設定根與交換檔路徑   health    健康摘要
|   object_stamp 物件檔時戳命名     user_assets 拷貝 Lua 到使用者資料夾
|   result／log／docs
+--------------------------------------------------------------------------+
                  |
                  v  （不是程式呼叫，而是透過交換檔）
+--------------------------------------------------------------------------+
| Octane 端  src/octane/entrypoints/   （Lua 腳本）
|
|   同步用     R2O_Camera.lua   套用相機
|              R2O_Point.lua    套用點位（Scatter）
|              R2O_Open.lua     空殼
|   熱鍵設定   R2O_Shortcuts.txt
|              __Open_Shortcuts.lua／__Setup_Shortcuts.lua
|   Authoring  Auto_*.lua 四支（獨立工具）
+--------------------------------------------------------------------------+
```

---

## 五、磁碟位置與周邊

```
<已存檔 .3dm 同一層>/
  _LoopFlow_Config/loopflow_R2O/
    config.json / r2o.log            設定與紀錄
    live/camera.json                 相機（另有 camera_pending.json）
    live/point.json                  點位（另有 point_pending.json）
    models/R2O.usdz                  主模型
    models/R2O_Objects_時戳.usdz     選取物件，每次一份

文件\LoopFlow\Rhino to OctaneRender Sync\lua\
    Octane 的 Lua 腳本放這裡（由正式指令從安裝包拷出，不放在專案裡）
    Octane 的 Script directory 要指到這個資料夾

%APPDATA%\LoopFlow\R2O\current_project.json
    本機指標：目前專案的位置

+-------------------------------+     +--------------------------------------+
| 品質把關  wip/tests/          |     | 打包  wip/packaging/
| 格式、換算、後處理、安全寫檔  |     | .yak 安裝包（內含 Rhino 指令與 Lua）
| 不需要開 Rhino／Octane        |     |
+-------------------------------+     +--------------------------------------+
+-------------------------------+     +--------------------------------------+
| 開發工具  wip/tools/          |     | 文件
| deploy_dev_lua.ps1 部署開發   |     | wip/docs/  實作規格（本資料夾，繁中）
| 版 Lua、決策表產生器          |     | 根 docs/   公開使用說明（中英）
+-------------------------------+     +--------------------------------------+
```

---

## 一句話總結

Rhino 端把模型寫成 USDZ、把相機與點位寫成 JSON，Octane 端沒有常駐程式，靠手動執行 Lua「套用一次」或重開場景重讀；兩端只靠工作檔旁的 `_LoopFlow_Config/loopflow_R2O/` 溝通，任何失敗都保留上一份有效檔。Authoring 四支 Auto 是與同步無關的獨立材質工具。

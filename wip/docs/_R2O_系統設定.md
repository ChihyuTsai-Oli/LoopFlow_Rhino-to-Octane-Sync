# LoopFlow R2O — 系統設定

本文件是 R2O 維護設定與現況架構的權威來源。2.0 遷移方式另見 `_R2O_重構計畫.md`。

## Repo 與版本

| 項目 | 設定 |
|---|---|
| 穩定分支 | `main`（1.x） |
| 2.0 整合分支 | `v2-development` |
| 短期工作分支 | `codex/v2-<scope>` |
| 穩定 tag | `v1.0.0` |
| 目標版本 | `v2.0.0` |
| Rhino runtime | Rhino 8 / CPython 3.9 |
| Octane runtime | Lua；最低相容版本待實機矩陣確認 |

## 重構工作檔根目錄

- 本機環境變數：`LOOPFLOW_R2O_WORKFILES_ROOT`
- 公司電腦：`D:\Dropbox\LoopFlow_Series\Workfiles\WIP_R2O`
- Rhino／Octane 交換 JSON：`%LOOPFLOW_R2O_WORKFILES_ROOT%\exchange\`

2.0 producer／consumer 只透過環境變數解析工作根目錄，不寫死公司路徑。新版即時交換資料採 JSON；確切檔名、schema 與 Lua parser 邊界後續由資料契約固定。即時檔不提交 Git。

## 2.0 開發模式

- `main`、`v1.0.0` 與既有 `releases/` 作為舊版行為參考，不在重構過程逐支改造成半新半舊系統。
- 2.0 在新的 `wip/src/`、隔離 Rhino／Octane 安裝、shortcut、scene 與輸出中乾淨建立，正式發布時一次切換。
- 建立 feature 前先完成 `_R2O_命名與資料契約.md` 的 command、Python↔Lua schema、Point identity、Octane node 與 shortcut。
- 新核心只使用 2.0 contract；v1 設定／scene 升級由獨立 migration 工具負責。
- 每個階段仍做自動／contract 測試；完整 Rhino→Octane 實機測試於主鏈接通後執行。

## 目前 Repo 結構

```text
releases/LoopFlow_Rhino-to-Octane-Sync/
  Python/                 # Rhino producer，共 6 支 Python
  LUA/                    # LiveLink consumer 與 authoring tools，共 8 支 Lua
  Data/R2O_Shortcuts.txt
  LoopFlow_R2O.rhc
  install_LoopFlow_R2O.bat
docs/
  USER_GUIDE*.md           # 公開使用指南
wip/
  README.md
  docs/
    _R2O_*.md              # 重構維護 SSOT
    architecture/DEVELOPMENT_ROADMAP.md
    architecture/PROGRESS.md
  src/                     # 2.0 原始碼（後續建立）
  tests/                   # 測試（後續建立）
  fixtures/                # 可提交的輕量測試資料（後續建立）
```

目前 `releases/` 同時是 source 與 payload。只有在 Python／Lua module-loading spike 與 build 驗證完成後，才切換 `wip/src/` 為唯一來源。

## 重構期間的 Rhino 測試入口

重構期間直接從 repo 執行 Rhino producer 入口，不必先複製到 `%APPDATA%`。測試按鈕固定指向 `entrypoints/`，不要直接指向仍會調整的 feature 或 foundation 模組：

```text
E:\_GitHub\LoopFlow_Rhino-to-Octane-Sync\wip\src\rhino\entrypoints\
```

按鈕巨集範例：

```text
_-ScriptEditor _Run "E:\_GitHub\LoopFlow_Rhino-to-Octane-Sync\wip\src\rhino\entrypoints\R2O_Models.py"
```

目前預計入口：

```text
R2O_Models.py
R2O_Scatter.py
R2O_Point.py
R2O_Camera.py
R2O_Open.py
```

這是開發期暫定清單，不是凍結的 2.0 command contract。功能增減、入口檔名或 repo 內路徑改變時，應同步更新本節與測試工具列；正式安裝／RC 驗證才改用隔離的 `%APPDATA%` Rhino 開發安裝位置。Octane Lua scripts 仍使用隔離測試位置，不經 Rhino 按鈕直接啟動。

## 現行安裝位置

```text
%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\
  Data\
    R2O_Path.txt
    R2O_Shortcuts.txt
    cursor_R2O_debug_log.txt
    R2O.usdz
    R2O_Camera_Sync_Data.lua
    R2O_Point_Sync_Data.lua
  Py\
    LiveLink_R2O_*.py
  Lua\
    LiveLink_R2O_*.lua
    Auto_*.lua
    __Open_Shortcuts.lua
    __Setup_Shortcuts.lua
```

## `R2O_Path.txt` 設定

| 欄位 | 預設值／規則 | 用途 |
|---|---|---|
| `DataPath` | 安裝目錄下 `Data` | 同步資料根目錄 |
| `ModelDir` | 空白 | 空白時使用 `DataPath` |
| `PointLayer` | `R2O` | Point／Block root layer prefix |
| `ModelFile` | `R2O.usdz` | Models 輸出檔名 |
| `CameraFile` | `R2O_Camera_Sync_Data.lua` | Camera 資料檔 |
| `PointFile` | `R2O_Point_Sync_Data.lua` | Point 資料檔 |
| `PointNgName` | `R2O_Point` | Octane Scatter group node |
| `PointPrefix` | `R2O_Point_` | Point node prefix |
| `LastModelLayer` | 空白 | 上次 Models 選擇 |

現行 `LiveLink_R2O__Config.py` 同時處理 config、debug log、exception formatting、atomic text write 與 type name normalization，責任過多；2.0 會先加測試再逐項拆分。

## 內部契約，不是使用者設定

以下內容留在所屬 module 並測試，不直接加入 `R2O_Path.txt`：

- `state_key`、`event_key` 與 Rhino API object mask。
- 35mm FOV、座標與單位轉換規則。
- Rhino command 字串。
- Octane `NT_*`、`P_*`、pin ID 與 node layout 常數。
- schema version、stable ID、escaping 與成功條件。

## Python↔Lua 契約

兩個 runtime 不直接共享程式碼，以語言中立規格維持一致：

- schema version、欄位、型別、必要值。
- path、檔名、座標、單位與命名碰撞。
- 引號、反斜線、換行、Unicode／emoji escaping。
- parse／apply／publish 的成功條件與 state 更新時機。
- 同一組 fixtures 同時測 Python producer 與 Lua consumer。

若 build 可從 schema 產生兩端常數就採生成；否則用 contract tests 防止兩份實作漂移。

## Models／Scatter 發布規則

- 明確 source → temporary data → pending export → postprocess → validate → atomic replace → result。
- 不在來源物件永久改 `MaterialSource`。
- 不移動原始 Block；若過渡期不得不改來源，必須立即 `try/finally` snapshot／restore。
- last good USD／USDZ 在新輸出完成驗證前不得刪除。

## Installer／RHC／Shortcut

- Installer 不依賴已淘汰的 `wmic`；日期使用 PowerShell `Get-Date` 並包含時間。
- 重複安裝保存 Data、config、shortcut，失敗可 rollback。
- Rhino 8 path 不在 BAT、RHC、Lua、Python 文件各自維護；由 build config 產生或驗證。
- RHC 的 R2B 殘留另批清理並做 Rhino 實機驗證。
- Shortcut metadata 與 command catalog 必須可對照。

## 文件與程式註解規則

- 維護 SSOT：本文件、`_R2O_使用說明.md`、`_R2O_重構計畫.md`、`architecture/PROGRESS.md`。
- 任務切分、依賴順序與雙機安全停點：`architecture/DEVELOPMENT_ROADMAP.md`。
- 命名與 Python↔Lua schema SSOT：`_R2O_命名與資料契約.md`。
- 內部文件與新增／修改的 Python／Lua 註解使用繁體中文。
- 完整流程、schema、責任、副作用與回復方式寫入 docs；程式只保留必要原因、API 限制與 invariant。
- 現有 Python 有長篇英文標頭，Lua 亦有既有說明；按 feature 逐批遷移，不一次製造純翻譯的大型 diff。
- 公開英文 README／Guide 是發布翻譯，不是 AI 重構指令。

## 基準檢查

目前沒有 CI／pytest 設定。每批至少執行：

- Python 靜態語法解析。
- Lua 語法／module loading（有對應 runtime 時）。
- RHC XML 解析。
- Installer、ZIP、shortcut 與 release 檔案清單（涉及 build 時）。
- Rhino producer 與 Octane consumer 的同組 fixtures／golden workflow。
- `git diff --check`、秘密與非預期產物檢查。

未在 Rhino／Octane 執行的項目不得寫成通過。

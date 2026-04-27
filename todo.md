# LoopFlow Rhino-to-Octane-Sync — 開發待辦清單

**建立日期**：2026-04-27
**說明**：審查 5 支 Python 腳本與 6 支 Lua 腳本後規劃的硬編碼集中化工作，配合未來安裝檔部署路徑設計。

---

## 目標安裝目錄結構

```
%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\
│
├── Data\                        ← 所有使用者可見檔案
│   ├── R2O_Path.txt             ← 主設定檔
│   ├── R2O_Shortcuts.txt        ← 熱鍵設定檔（新增）
│   ├── cursor_R2O_debug_log.txt ← 除錯日誌（自動產生）
│   ├── R2O.usdz                 ← Models.py 輸出，Octane 讀取
│   ├── R2O_Camera_Sync_Data.lua ← Camera.py 輸出，LiveLink_R2O_Camera.lua 讀取
│   └── R2O_Point_Sync_Data.lua  ← Point.py 輸出，LiveLink_R2O_Point.lua 讀取
│
├── Python\                      ← Rhino 端 Python 腳本
│   ├── LiveLink_R2O__Config.py
│   ├── LiveLink_R2O_Camera.py
│   ├── LiveLink_R2O_Models.py
│   ├── LiveLink_R2O_Point.py
│   └── LiveLink_R2O_Scatter.py
│
└── LUA\                         ← Octane 端 Lua 腳本
    ├── Auto_Align_Nodes.lua
    ├── Auto_Convert_StdSurf_to_Universal.lua
    ├── Auto_PBR_Switch_UV.lua
    ├── Auto_PBR_Universal.lua
    ├── LiveLink_R2O_Camera.lua
    ├── LiveLink_R2O_Point.lua
    └── Setup_Shortcuts.lua      ← 新增
```

---

## R2O_Path.txt 完整欄位（目標狀態）

```
DataPath:       （安裝時動態推算，預設同 Data\ 目錄）
PointLayer:     R2O
ModelFile:      R2O.usdz
CameraFile:     R2O_Camera_Sync_Data.lua
PointFile:      R2O_Point_Sync_Data.lua
PointNgName:    R2O_Point
PointPrefix:    R2O_Point_
LastModelLayer: （空白，記憶上次匯出的 Rhino 圖層）
```

> 移除的欄位：`ModelLayer`（改為每次執行 Models.py 時彈出圖層選擇視窗）

## R2O_Shortcuts.txt 完整欄位（目標狀態）

```
Auto_Align_Nodes:                   alt+a
Auto_Convert_StdSurf_to_Universal:  Shift+M
Auto_PBR_Switch_UV:                 Ctrl+T
Auto_PBR_Universal:                 Ctrl+Shift+T
LiveLink_R2O_Camera:                Ctrl+Q
LiveLink_R2O_Point:
```

---

## 待辦項目

### Python 端

- [ ] **`LiveLink_R2O__Config.py`**
  - `CONFIG_DIR = r"C:\_RH_Tools"` → 改用 `__file__` 自動推算：
    ```python
    _PYTHON_DIR    = os.path.dirname(os.path.abspath(__file__))
    INSTALL_DIR    = os.path.dirname(_PYTHON_DIR)
    DATA_DIR       = os.path.join(INSTALL_DIR, "Data")
    CONFIG_DIR     = DATA_DIR
    CONFIG_FILE    = os.path.join(DATA_DIR, "R2O_Path.txt")
    DEBUG_LOG_FILE = os.path.join(DATA_DIR, "cursor_R2O_debug_log.txt")
    ```
  - `DEFAULT_CONFIG` 移除 `ModelLayer`，新增以下六個欄位：
    ```python
    DEFAULT_CONFIG = {
        "DataPath":       DATA_DIR,
        "PointLayer":     "R2O",
        "ModelFile":      "R2O.usdz",
        "CameraFile":     "R2O_Camera_Sync_Data.lua",
        "PointFile":      "R2O_Point_Sync_Data.lua",
        "PointNgName":    "R2O_Point",
        "PointPrefix":    "R2O_Point_",
        "LastModelLayer": "",
    }
    ```
  - `_FIELD_ORDER` 同步更新（移除 `ModelLayer`，加入六個新欄位）
  - docstring 中所有 `C:\_RH_Tools` 路徑範例 → `%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O`

- [ ] **`LiveLink_R2O_Camera.py`**
  - `sys.path.insert(0, r"C:\_RH_Tools\Python")` → 改為：
    ```python
    import os, sys
    _HERE = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, _HERE)
    ```
  - `SYNC_FILE_NAME = "R2O_Camera_Sync_Data.lua"` → 改從 `cfg["CameraFile"]` 讀取
  - 將函式內的技術參數浮出至模組頂部常數區：
    ```python
    DEFAULT_LENS_MM  = 50.0   # 無焦距資訊時的預設焦長（mm）
    MIN_INTERVAL_SEC = 0.2    # 相機更新最短間隔（秒）
    EPS_POSITION     = 1e-4   # 位置變化偵測閾值（公尺）
    EPS_FOV          = 1e-4   # FOV 變化偵測閾值（度）
    ```
  - docstring 路徑範例同步更新

- [ ] **`LiveLink_R2O_Models.py`**
  - `sys.path.insert` 改用 `__file__`（同上）
  - 移除 `ModelLayer` 讀取邏輯，改為圖層選擇視窗：
    ```python
    cfg = load_r2o_config()
    last_layer = cfg.get("LastModelLayer", "") or None
    target_layer_root = rs.GetLayer("選擇要匯出的模型圖層", default_layer=last_layer)
    if not target_layer_root:
        return
    cfg["LastModelLayer"] = target_layer_root
    _write_config(cfg)
    ```
  - `"R2O.usdz"` 改從 `cfg["ModelFile"]` 讀取
  - docstring 路徑範例同步更新

- [ ] **`LiveLink_R2O_Point.py`**
  - `sys.path.insert` 改用 `__file__`
  - `SYNC_FILE_NAME = "R2O_Point_Sync_Data.lua"` → 改從 `cfg["PointFile"]` 讀取
  - docstring 路徑範例同步更新

- [ ] **`LiveLink_R2O_Scatter.py`**
  - `sys.path.insert` 改用 `__file__`
  - docstring 路徑範例同步更新

---

### Lua 端

- [ ] **`LiveLink_R2O_Camera.lua`**
  - 腳本頂部加入路徑常數區（取代函式內硬編碼）：
    ```lua
    local APPDATA     = os.getenv("APPDATA")
    local INSTALL_DIR = APPDATA .. "\\McNeel\\Rhinoceros\\8.0\\scripts\\LoopFlow_R2O"
    local DATA_DIR    = INSTALL_DIR .. "\\Data"
    local CONFIG_FILE = DATA_DIR .. "\\R2O_Path.txt"
    ```
  - `getGlobalPath()` 升級為 `loadConfig()`，讀取完整 config table（含所有欄位）：
    ```lua
    local function loadConfig()
        local cfg = {
            DataPath   = DATA_DIR,
            CameraFile = "R2O_Camera_Sync_Data.lua",
        }
        local f = io.open(CONFIG_FILE, "r")
        if f then
            for line in f:lines() do
                local k, v = line:match("^(%w+):%s*(.*)")
                if k and cfg[k] ~= nil then cfg[k] = v end
            end
            f:close()
        end
        return cfg
    end
    ```
  - `local syncFileName = "R2O_Camera_Sync_Data.lua"` → 改從 `cfg.CameraFile` 讀取
  - `-- @shortcut Ctrl + Q` 保留（預設值）
  - docstring 路徑範例同步更新

- [ ] **`LiveLink_R2O_Point.lua`**
  - 腳本頂部加入路徑常數區（同上 Camera）
  - `getGlobalPath()` 升級為 `loadConfig()`，讀取完整 config table（含 PointNgName、PointPrefix）
  - `local syncFileName = "R2O_Point_Sync_Data.lua"` → 改從 `cfg.PointFile` 讀取
  - `local NG_NAME = "R2O_Point"` → 改從 `cfg.PointNgName` 讀取
  - `local NODE_PREFIX = "R2O_Point_"` → 改從 `cfg.PointPrefix` 讀取
  - 新增空白 `-- @shortcut` 行（預留熱鍵位置）
  - docstring 路徑範例同步更新

- [ ] **新增 `LUA/Setup_Shortcuts.lua`**
  - 腳本頂部路徑推算：
    ```lua
    local APPDATA        = os.getenv("APPDATA")
    local INSTALL_DIR    = APPDATA .. "\\McNeel\\Rhinoceros\\8.0\\scripts\\LoopFlow_R2O"
    local DATA_DIR       = INSTALL_DIR .. "\\Data"
    local LUA_DIR        = INSTALL_DIR .. "\\LUA"
    local SHORTCUTS_FILE = DATA_DIR .. "\\R2O_Shortcuts.txt"
    ```
  - 讀取 `R2O_Shortcuts.txt`
  - 對 `LUA\` 下每支 `.lua`（排除自身）：更新 `-- @shortcut` 行
  - 輸出修改摘要，提示使用者重新掃描 Octane 腳本目錄
  - 本身不設 `-- @shortcut`

- [ ] **新增 `Data/R2O_Shortcuts.txt`（由安裝檔建立）**
  - 內容見上方「R2O_Shortcuts.txt 完整欄位」

---

## 不需處理的項目

| 項目 | 原因 |
|---|---|
| `state_key`、`event_key`（Camera.py） | Rhino sticky dict 版本戳，內部機制 |
| `rs.ObjectsByType(1)` / `(4096)`（Point.py） | Rhino API 代碼 |
| `36.0`（Camera.py FOV 公式） | 35mm 底片物理常數 |
| `"_-Save _Enter"`、`"_-Export..."` | Rhino 命令語法 |
| Octane NT_* / P_* / pin ID 數字 | Octane API 常數 |
| `"BoxProjection_A"`、`"Transform_A"`（Auto_PBR_Switch_UV） | 兩腳本內部命名約定 |
| `NODE_SPACING_X`、`NODE_START_X`、`NODE_START_Y`（Point.lua） | 版面參數，已在頂部 |
| UI 提示字串（中文對話框文字） | 日後 i18n 再處理 |

---

## 備註

- **`__file__` 備案**：若 Rhino 8 CPython 的 `__file__` 不可靠，改為每支腳本頂部保留單一 `_INSTALL_DIR` 常數，需逐檔修改但仍比現在集中。
- **安裝腳本**：`install_LoopFlow_R2O.bat` 模式參考 `../LoopFlow/releases/LoopFlow/install_LoopFlow.bat`，需額外複製 `Python\` 和 `LUA\` 兩個子目錄至 `%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\`，並在 `Data\` 建立初始設定檔。
- **現有安裝遷移**：`DataPath` 預設值變更不會自動套用至既有的 `R2O_Path.txt`，使用者需手動修改。

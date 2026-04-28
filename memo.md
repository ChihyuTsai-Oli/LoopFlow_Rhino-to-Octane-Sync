# LoopFlow Rhino-to-Octane-Sync — 開發備忘

---

## 安裝目錄結構

```
%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\
│
├── Data\                        ← 所有使用者可見檔案
│   ├── R2O_Path.txt             ← 主設定檔
│   ├── R2O_Shortcuts.txt        ← 熱鍵設定檔
│   ├── cursor_R2O_debug_log.txt ← 除錯日誌（自動產生）
│   ├── R2O.usdz                 ← Models.py 輸出，Octane 讀取
│   ├── R2O_Camera_Sync_Data.lua ← Camera.py 輸出，LiveLink_R2O_Camera.lua 讀取
│   └── R2O_Point_Sync_Data.lua  ← Point.py 輸出，LiveLink_R2O_Point.lua 讀取
│
├── Py\                          ← Rhino 端 Python 腳本
│   ├── LiveLink_R2O__Config.py
│   ├── LiveLink_R2O_Camera.py
│   ├── LiveLink_R2O_Models.py
│   ├── LiveLink_R2O_Open.py
│   ├── LiveLink_R2O_Point.py
│   └── LiveLink_R2O_Scatter.py
│
└── Lua\                         ← Octane 端 Lua 腳本
    ├── __Open_Shortcuts.lua
    ├── Auto_Align_Nodes.lua
    ├── Auto_Convert_StdSurf_to_Universal.lua
    ├── Auto_PBR_Switch_UV.lua
    ├── Auto_PBR_Universal.lua
    ├── LiveLink_R2O_Camera.lua
    ├── LiveLink_R2O_Point.lua
    └── __Setup_Shortcuts.lua
```

---

## R2O_Path.txt 欄位

```
DataPath:       （安裝時動態推算，預設同 Data\ 目錄）
ModelDir:       （空白 = 使用 DataPath；可填絕對路徑自訂 USDZ 輸出目錄）
PointLayer:     R2O
ModelFile:      R2O.usdz
CameraFile:     R2O_Camera_Sync_Data.lua
PointFile:      R2O_Point_Sync_Data.lua
PointNgName:    R2O_Point
PointPrefix:    R2O_Point_
LastModelLayer: （空白，記憶上次匯出的 Rhino 圖層）
```

> `ModelLayer` 已移除，改為每次執行 Models.py 時彈出圖層選擇視窗。  
> `ModelDir` 空白時自動 fallback 至 `DataPath`。

---

## R2O_Shortcuts.txt 欄位

```
Auto_Align_Nodes:                   alt+a
Auto_Convert_StdSurf_to_Universal:  Shift+M
Auto_PBR_Switch_UV:                 Ctrl+T
Auto_PBR_Universal:                 Ctrl+Shift+T
LiveLink_R2O_Camera:                Ctrl+Q
LiveLink_R2O_Point:
```

**Octane 修改熱鍵步驟：**
1. 在 Octane 中執行 `__Open_Shortcuts.lua` → 開啟 `R2O_Shortcuts.txt`
2. 修改熱鍵值並儲存
3. 在 Octane 中執行 `__Setup_Shortcuts.lua`
4. 在 Octane 中 Script > Rescan script folder
5. Done! (原則上不需要重啟 Octane)

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

- **`__file__` 備案**：若 Rhino 8 CPython 的 `__file__` 不可靠，改為每支腳本頂部保留單一 `_INSTALL_DIR` 常數，需逐檔修改但仍比過去集中。
- **安裝腳本**：參考 `../LoopFlow/releases/LoopFlow/install_LoopFlow.bat`，需複製 `Python\` 和 `LUA\` 至安裝目錄，並在 `Data\` 建立初始設定檔。
- **既有安裝遷移**：`DataPath` 預設值變更不會自動套用至既有的 `R2O_Path.txt`，使用者需手動修改。

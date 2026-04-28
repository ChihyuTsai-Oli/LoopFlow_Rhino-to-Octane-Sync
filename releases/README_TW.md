# LoopFlow Rhino-to-Octane Sync — Releases

### 安裝方式

**Rhino 端**

1. 從 Releases 下載最新版本的 ZIP
2. 解壓縮後進入 `LoopFlow_Rhino-to-Octane-Sync/` 資料夾
3. 執行 `install_LoopFlow_R2O.bat`，自動安裝 Rhino 端腳本與 LUA 腳本
4. 將 `LoopFlow_R2O.rhc` 拖曳至 Rhino 視窗，工具列即出現

**Octane 端**

5. 在 OctaneRender 中設定 LUA 腳本路徑為：
   `%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Lua`
6. 重新掃描腳本，完成熱鍵設定

> 重複安裝時，既有的 `R2O_Shortcuts.txt` 熱鍵設定不會被覆蓋，
> 新範本會以 `R2O_Shortcuts_YYYYMMDD.txt` 格式另存於同目錄供比對。

### 包含檔案

| 檔案 / 資料夾 | 說明 |
|---|---|
| `LoopFlow_Rhino-to-Octane-Sync/Python/` | Rhino 端 Python 腳本 |
| `LoopFlow_Rhino-to-Octane-Sync/LUA/` | Octane 端 LUA 腳本與熱鍵管理工具 |
| `LoopFlow_Rhino-to-Octane-Sync/Data/` | 熱鍵設定範本（`R2O_Shortcuts.txt`） |
| `LoopFlow_Rhino-to-Octane-Sync/install_LoopFlow_R2O.bat` | 自動安裝程式 |
| `LoopFlow_Rhino-to-Octane-Sync/LoopFlow_R2O.rhc` | Rhino 工具列定義檔 |

### 資料夾結構

```
releases/
  LoopFlow_Rhino-to-Octane-Sync/
    Python/                    ← Rhino 端 Python 腳本
    LUA/                       ← Octane 端 LUA 腳本
    Data/
      R2O_Shortcuts.txt        ← 熱鍵設定範本（安裝時保護，不覆蓋）
    install_LoopFlow_R2O.bat
    LoopFlow_R2O.rhc
  README.md
```

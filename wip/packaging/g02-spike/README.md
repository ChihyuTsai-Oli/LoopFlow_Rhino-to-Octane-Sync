# R2O 2.0 yak 建置

正式版號 **`2.1.1`**。`v2.0.0`～`v2.0.16`、`v2.1.0` 與 `v2.1.1` 永不移動。工具列會自動載入。yak 含 Octane Lua（`templates/`）；第一次跑任一產品指令拷到「文件\LoopFlow\Rhino to OctaneRender Sync\lua」。換版時清空該 lua 資料夾再拷官方檔。不自動寫入 Octane Preferences。工具列 RUI 進包時改成與 `.rhp` 同名，Rhino 才會自動載入。

**戳記：** `build.ps1` 從 `manifest.yml` 的 `version:` 寫入 `templates/.loopflow_yak_version`。禁止寫死舊版號。升版只改 manifest、卻讓戳記停在舊數字，Package Manager 更新後正式指令會跳過拷 Lua。Package Manager 本身不拷檔；使用者須完全關再開 Rhino，再跑任一正式指令。

畫面名（已凍）：`loopflow Rhino to OctaneRender Sync`  
機器名：`loopflow-rhino-to-octanerender-sync`

## 你要交的檔（可與指令檔並行）

放到 `wip/docs/toolbar/`：

- 產品 `.rui`（`ExportRuiFile` 匯出；含 `tool_bar_group`；不要寫 `SelectedToolbarSet`）
- Package Manager 圖示 PNG（800×800），檔名 `icon.png`

正式按鈕巨集（不要抄開發用 ScriptEditor 路徑）：

```text
! _ROCamera
! _ROCameraPush
! _ROModels
! _ROObjects
! _ROPoint
! _ROOpen
```

Authoring 四支 Auto 仍是 Octane Lua，不要做成 Rhino 按鈕。

## Script Editor 必須你點一次（不能手寫 rhproj）

Rhino 8.11 以上：

1. 完全關掉再打開 Rhino。
2. Script Editor → 新增專案（Python）。**不要**跟 R2B 那份專案混在同一個 rhproj。
3. 加入 `commands/` 底下 **只有** `指令名稱.txt` 列出的六支 `.py`（不要加 `command_locate.py`、`_gen_commands.py`）。
4. Libraries 加入 `wip/src`。
5. 另存成：  
   `wip/packaging/g02-spike/loopflow-rhino-to-octanerender-sync.rhproj`
6. 跟我說存好了。之後才跑 `build.ps1`。

不要改開發入口 `wip/src/rhino/entrypoints/`。

## 建置（有 rhproj 之後）

```powershell
cd wip/packaging/g02-spike
.\build.ps1
```

腳本會刪掉 RhinoCode 自動產生的 `.rui`，若 `wip/docs/toolbar/` 有產品 RUI／`icon.png` 再複製進去。進包時 RUI 檔名必須與 `.rhp` 相同。產出 `.yak` 不進 Git。建包後核對 stage／yak 內的 `.loopflow_yak_version` 必須等於 `manifest.yml` 的 `version:`。

裝完須**完全關 Rhino 再開**。不要跟 1.x 或開發按鈕混測。正式進版打 `v2.1.1`；永不覆寫 `v2.0.0`～`v2.0.16` 與 `v2.1.0`。Rhino 8 與 Rhino 9 裝同一份 `rh8_0`，不另發 `rh9_0`。

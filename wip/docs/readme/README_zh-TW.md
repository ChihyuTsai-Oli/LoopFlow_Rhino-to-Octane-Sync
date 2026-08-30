# LoopFlow｜Rhino to Octane Sync

> 2.0 公開說明初稿（`wip/docs/readme/`）。尚未取代 repo 根目錄的 1.x 文件。英文尚未撰寫。

[1.x English homepage](../../../README.md)

> 把 Rhino 的模型、相機與點位，單向同步到 OctaneRender。

2.0 是重建，不是 1.x 的修補版。Rhino 端裝一份 `.yak`；Octane 端另裝 Lua 腳本（不進 `.yak`）。同一專案不要混用 1.x 與 2.0。

[▶ 使用說明](./README.md) · [▶ Releases](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync/releases) · [▶ 教學影片](https://www.youtube.com/playlist?list=PLiJmu8T_uzJKBQ9LUzSmd7_OHV5fYjzII)

## 主要功能

- **模型同步** — 從作業中的 Rhino 檔匯出乾淨 USDZ；Octane 載入後接材質，之後更新靠關再開
- **選取物件** — 把目前選取匯成另一份時戳 USDZ，自行載入當組件
- **相機同步** — 將 Rhino 作用視角寫出；Octane 套用一次
- **點位對齊** — Rhino `R2O::` 圖層上的 Point 與 Block，用來對齊 Octane Scatter 上的燈與家具 Proxy

各通道彼此獨立，不必照固定順序一次做完。Octane 裡另有 Authoring 輔助腳本，不參與同步。

## 與 1.x 的差異

- 2.0 是重建；指令改為 `ROModels`、`ROOpen` 等連寫名稱，不是舊的 `R2O_Models`
- 設定改放在已存檔 `.3dm` 旁的 `_LoopFlow_Config/loopflow_R2O/`，不再用 AppData 當交換根
- Rhino 套件只含 Rhino；Octane Lua **不進** `.yak`，由 GitHub 說明安裝
- 相機與點位在 Octane 都是「跑腳本套用一次」，不是開著一直跟
- 更新主模型時不要按 Reload mesh／Load new mesh；關掉 Octane 再開
- 同一專案、同一套按鈕不要混用 1.x 與 2.0

## 系統需求

- **Rhino 8**（Windows）
- **OctaneRender Studio+ 2026.4**（2.0 目標版本）

Rhino 對話框為英文；本說明為正體中文。

## 快速開始

教學影片尚未全部改為 2.0。

### 安裝

不要用 1.x 的解壓腳本或舊工具列。

**Rhino**

1. 開啟 Rhino 8，命令列執行 `PackageManager`
2. 正式上架後搜尋畫面名 **`loopflow Rhino to OctaneRender Sync`**
3. 或從 [Releases](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync/releases) 下載 `.yak`，在 Package Manager 選擇從檔案安裝
4. **完全關掉 Rhino 再開**
5. 使用工具列 **Rhino to OctaneRender Sync**；不要按 1.x 按鈕

2.0 正式上架前，請用本機／GitHub 提供的 `.yak` 從檔案安裝，不要搜尋到 1.x 就裝上去混用。

**Octane**

1. 把本 repo 的 Lua 放到專案 `_LoopFlow_Config/loopflow_R2O/lua/`（開發期可用拷貝腳本；正式發布見 GitHub 說明）
2. 跑 `__Setup_Shortcuts.lua`，再重掃 Octane 腳本資料夾
3. 不要蓋掉 1.x 裝在 AppData 的舊 Lua

完整步驟與按鈕說明見 [使用說明](./README.md)。

## 基本工作流程

1. 把 `.3dm` 存檔（未存檔則無法發布）
2. `ROOpen` 確認設定資料夾與各通道上次成功時間
3. 需要模型時跑 `ROModels`（有材質）或 `ROObjects`（選取）
4. 需要相機或點位時在 Rhino 寫出，再到 Octane 跑對應 Lua 套用一次
5. 主模型之後若覆寫同一份 `R2O.usdz`：關掉 Octane 再開，不要 Reload

每一步都要自己按。走錯就停在該通道重跑，不必推翻整場。

## 支援與回報

- [Discussions](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync/discussions)：提問與使用經驗
- [Issues](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync/issues)：回報錯誤或建議
- [Releases](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync/releases)：已發布版本

LoopFlow 是由建築及室內設計師從實際工作中發展的單人專案。程式開發與文件整理使用 AI 協助；工作流程需求、設計決策與實務驗證仍以作者本人的專業經驗為基礎。

維護與回覆速度會依工作狀況調整。

## 相關專案

- [LoopFlow｜Half-automatic 2D/3D Sync](https://github.com/ChihyuTsai-Oli/LoopFlow/blob/main/README_zh-TW.md)
- [LoopFlow｜Rhino to Blender Sync](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Blender-Sync/blob/main/README_zh-TW.md)

## 授權與致謝

本專案採用 [MIT License](../../../LICENSE) 發布。開發背景與致謝請參考 [CREDITS](./CREDITS.md)。

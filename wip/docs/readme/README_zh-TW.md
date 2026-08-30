# LoopFlow｜Rhino to Octane Sync

> 同一專案不要混用舊版的工具列、套件或 Octane Lua。

> 把 Rhino 的模型、相機與點位，單向同步到 OctaneRender。

Rhino 端裝一份 `.yak`；Octane 端另裝 Lua 腳本（不進 `.yak`）。

[▶ 使用說明](./docs/README.md) · [▶ Releases](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync/releases) · [▶ 教學影片](https://www.youtube.com/playlist?list=PLiJmu8T_uzJKBQ9LUzSmd7_OHV5fYjzII)

## 主要功能

- **模型同步** — 從作業中的 Rhino 檔匯出乾淨 USDZ；Octane 載入後接材質，之後更新靠關再開
- **選取物件** — 把目前選取匯成另一份時戳 USDZ，自行載入當組件
- **相機同步** — 將 Rhino 作用視角寫出；Octane 套用一次
- **點位對齊** — Rhino `R2O::` 圖層上的 Point 與 Block，用來對齊 Octane Scatter 上的燈與家具 Proxy

各通道彼此獨立，不必照固定順序一次做完。Octane 裡另有 Authoring 輔助腳本，不參與同步。

## 系統需求

- **Rhino 8**（Windows）
- **OctaneRender Studio+ 2026.4**

Rhino 對話框為英文；本說明為正體中文。

## 快速開始

教學影片尚未全部更新。

### 安裝

**Rhino**

1. 開啟 Rhino 8，命令列執行 `PackageManager`
2. 正式上架後搜尋畫面名 **`loopflow Rhino to OctaneRender Sync`**
3. 或從 [Releases](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync/releases) 下載 `.yak`，在 Package Manager 選擇從檔案安裝
4. **完全關掉 Rhino 再開**
5. 使用工具列 **Rhino to OctaneRender Sync**

尚未上架時，請用本機／GitHub 提供的 `.yak` 從檔案安裝。

**Octane**

1. 把本 repo 的 Lua 放到專案 `_LoopFlow_Config/loopflow_R2O/lua/`
2. 跑 `__Setup_Shortcuts.lua`，再重掃 Octane 腳本資料夾

完整步驟與按鈕說明見 [使用說明](./docs/README.md)。

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

本專案採用 [MIT License](./LICENSE) 發布。開發背景與致謝請參考 [CREDITS](./CREDITS.md)。

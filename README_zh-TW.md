# LoopFlow｜Rhino to Octane Sync

[English](./README.md)

> 同一專案不要混用舊版的工具列、套件或 Octane Lua。

> 把 Rhino 的模型、相機與點位，單向同步到 OctaneRender。

Rhino 端裝一份 `.yak`（內含 Octane Lua）。第一次跑任一 Rhino 指令後，lua 會拷到「文件\LoopFlow\Rhino to OctaneRender Sync\lua」。

[▶ 使用說明](./docs/README.md) · [▶ Releases](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync/releases) · [▶ 教學影片](https://www.youtube.com/playlist?list=PLiJmu8T_uzJKBQ9LUzSmd7_OHV5fYjzII)

## 主要功能

- **模型同步** — 從作業中的 Rhino 檔匯出乾淨 USDZ；Octane 載入後接材質，之後更新靠關再開
- **選取物件** — 把目前選取匯成另一份時戳 USDZ，自行載入當組件
- **相機同步** — 將 Rhino 作用視角寫出；Octane 套用一次
- **點位對齊** — Rhino `R2O::` 圖層上的 Point 與 Block，用來對齊 Octane Scatter 上的燈與家具 Proxy

各通道彼此獨立，不必照固定順序一次做完。Octane 裡另有 Authoring 輔助腳本，不參與同步。

## 系統需求

- **Rhino 8**（Windows）
- **OctaneRender Studio+ 2026.4**（開發環境）

Rhino 對話框為英文；本說明為正體中文。

## 快速開始

教學影片尚未全部更新。

### 安裝

**Rhino**

1. 開啟 Rhino 8，命令列執行 `PackageManager`
2. 搜尋畫面名 **`loopflow Rhino to OctaneRender Sync`** 並安裝
3. 或從 [Releases](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync/releases) 下載 `loopflow-rhino-to-octanerender-sync-2.0.3-rh8_0-win.yak`，在 Package Manager 選擇從檔案安裝
4. **完全關掉 Rhino 再開**
5. 使用工具列 **Rhino to OctaneRender Sync**。若沒出現：到 **Tools → Options → Plug-ins**（工具 → 選項 → 外掛程式）勾選 **LoopFlow R2O**。仍沒有時，命令列打一次 `ROOpen`

第一次跑產品指令會把 lua 拷到「文件\LoopFlow\Rhino to OctaneRender Sync\lua」。裝新版後，下一次跑指令會先清空這個 lua 資料夾，再放入這版官方檔（含 `R2O_Shortcuts.txt`）。同一版號則不動。升版前若改過熱鍵，要自己再改一次。

**Octane**

1. 跑一次任一 Rhino 指令，讓 lua 出現在「文件\LoopFlow\Rhino to OctaneRender Sync\lua」
2. 該資料夾裡有 `Set_Octane_Script_Directory.txt`（英上中下）
3. **File → Preferences → Directories and caching → Default locations → Script directory**，指到該 `lua` 資料夾（或你搬過去的任意複本；整包要在一起）
4. 重開 Octane；腳本出現在下拉 **Script**
5. 跑 `__Setup_Shortcuts.lua`，再重掃腳本資料夾

完整步驟與按鈕說明見 [使用說明](./docs/README.md)。

## 基本工作流程

1. 把 `.3dm` 存檔（未存檔則無法發布）
2. `ROOpen` 確認設定資料夾與各通道上次成功時間
3. 需要模型時跑 `ROModels`（有材質）或 `ROObjects`（選取）
4. 需要相機或點位時在 Rhino 寫出，再到 Octane 跑對應 Lua 套用一次
5. 主模型之後若覆寫同一份 `R2O.usdz`：關掉 Octane 再開，不要 Reload／Load new mesh

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

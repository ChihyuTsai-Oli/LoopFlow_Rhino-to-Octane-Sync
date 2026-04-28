# LoopFlow — Rhino 到 Octane Render 同步

> **擁抱循環，讓它流動。**

讓 Rhino 場景與 OctaneRender 保持完美同步，幾何體、相機與燈光隨設計演進自動更新。

[▶ 觀看示範（YouTube）](https://www.youtube.com/@LoopFlow) · [📦 Releases](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync/releases) · [📋 更新日誌](memo.md)

## 功能

- **模型同步** — 一鍵從 Rhino 匯出 USDZ；Octane 透過圖層 prim path 識別物件，更換模型並保留材質
- **相機同步** — 即時將 Rhino 作業視窗的視角鏡射到 Octane 的 Thin Lens Camera
- **燈光對齊** — Rhino 點物件自動透過 Scatter 驅動 Octane 的燈具對齊
- **家具代理** — Rhino Block 插入點自動透過 Scatter 驅動 Octane 的家具代理對齊

## 安裝方式

請參閱 **[releases/README.md](releases/README.md)** 的逐步安裝說明。

## 相關專案

- [LoopFlow](https://github.com/ChihyuTsai-Oli/LoopFlow) — Rhino 2D/3D 自動同步
- [LoopFlow_Rhino-to-Blender-Sync](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Blender-Sync) — Rhino 到 Blender 同步

## 致謝

- 使用 [Cursor](https://cursor.sh) + Claude Sonnet 4.6 協助開發

## 授權

MIT © 2026 Chihyu

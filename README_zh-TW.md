# LoopFlow｜Rhino to Octane Sync

[▶ How it works（YouTube）](https://www.youtube.com/playlist?list=PLiJmu8T_uzJKBQ9LUzSmd7_OHV5fYjzII) · [▶ Releases](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync/releases) · [▶ 指令說明](./docs/USER_GUIDE_zh-TW.md)

## 主要功能

- **模型同步** — 一鍵匯出乾淨 USDZ；Octane 單純置換模型、維持既有材質
- **相機同步** — 將 Rhino 的相機視角同步至 Octane
- **燈光對齊** — Rhino Points 位置同步，Octane 根據點位將燈光、燈具自動對齊
- **家具代理** — Rhino Block 透過 Proxy 代理，Octane 根據 Block 位置自動使家具對齊

## 材質同步原理

主要功能是同步模型，不管同步幾次都可保持材質不斷連。USDZ 格式會賦予每個 Rhino 圖層 UUID，UUID 會隨著圖層名稱變動；只要圖層名稱沒有更動，UUID 就不會變，利用這個原理達成已經接好的材質不斷線。

## 模組化設計

所有同步功能各自獨立，你可以只使用模型同步、或是只同步燈光等，這之間沒有連續的流程，自由選擇需要同步的項目即可，沒有限制。

## 為什麼是 OctaneRender Standalone？

他是個基於真實物理的無偏差 Render 引擎，對光影表現能力非常優秀（我私心認為這部分他是最優秀的）。透過上述的同步方式，可以彌補原生操作性能不足的問題，成為非常具有威力的工具。

## 安裝方式

請參閱 **[releases/README.md](releases/README.md)** 的逐步安裝說明。

## 也許你還有興趣

- [LoopFlow｜Half-automatic 2D/3D Sync](https://github.com/ChihyuTsai-Oli/LoopFlow)
- [LoopFlow｜Rhino to Blender Sync](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Blender-Sync)

## 致謝

- 看哪～Token在燃燒！

---

*最後更新：2026 年 4 月*
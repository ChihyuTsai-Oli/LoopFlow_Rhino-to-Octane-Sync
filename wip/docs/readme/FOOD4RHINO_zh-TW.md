# Food4Rhino 中文初稿（尚未上架）

LoopFlow Rhino to OctaneRender Sync 把 Rhino 8 的模型、相機與點位，單向同步到 OctaneRender。它不是另一個 BIM 系統，也不要求固定範本或參數化流程；你仍然掌控每一步，LoopFlow 負責匯出乾淨 USDZ、寫出視角與點位，Octane 端再套用。

主要流程是：在 Rhino 裡照原本方式建模，按需要發布模型、選取物件、相機或點位。主模型第一次在 Octane 載入並接材質；之後覆寫同一份 USDZ 時關掉 Octane 再開，不要 Reload mesh。材質接口跟 Rhino 材質名稱走。各通道彼此獨立，不必一次做完。

已在實際設計專案中使用。目標是保留 Rhino 的設計自由，同時減少改完模型後在渲染場景裡重做一遍的重複工作。

請用 Rhino 的 Package Manager 安裝（搜尋 **loopflow Rhino to OctaneRender Sync**）。Octane 的 Script directory 指到套件拷到「文件\LoopFlow」的 lua 資料夾（整包要在一起）。

不要把舊版 1.x 的工具列、套件或 Octane Lua 與本版混在同一專案。

系統需求：Rhino 8（Windows 10/11）、OctaneRender Studio+ 2026.4（開發環境）。介面：English。說明文件：English / Traditional Chinese。

免費開源，MIT License。

Category:
Architecture, Rendering

License Type: MIT

Cost: Free

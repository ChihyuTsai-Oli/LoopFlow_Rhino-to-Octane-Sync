# Food4Rhino 中文（已送審，待審核通過後再補頁面網址）

LoopFlow Rhino to OctaneRender Sync 把 Rhino 8 與 Rhino 9 的模型、相機與點位，單向同步到 OctaneRender。兩邊安裝同一份套件。匯出乾淨 USDZ、寫出視角與點位，Octane 端再套用。

主要流程：在 Rhino 裡照原本方式建模，按需要發布模型、選取物件、相機或點位。主模型第一次在 Octane 載入並接材質；之後覆寫同一份 USDZ 時關掉 Octane 再開即可自動更新模型，不要 Reload mesh。材質接口跟 Rhino 材質名稱走；圖層沒指定材質時用圖層路徑（中文改成底線）。點位產生的 Scatter 與 `R2O_Point_Geometry` 包在 `R2O_Point` node graph 裡，每次套用依名稱由左到右排列，場景接這個圖表；燈與家具仍接在各 Scatter 的輸入。各通道彼此獨立，不必一次做完。

目標是保留 Rhino 的設計自由，同時減少改完模型後在渲染場景裡重做一遍的重複工作。

請用 Rhino 的 Package Manager 安裝（搜尋 **loopflow Rhino to OctaneRender Sync**）。Octane 的 Script directory 指到套件拷到「文件\LoopFlow」的 lua 資料夾（整包要在一起）。

不要把舊版 1.x 的工具列、套件或 Octane Lua 與本版混在同一專案。

系統需求：Rhino 8 與 Rhino 9（Windows 10/11；同一份套件）、OctaneRender Studio+ 2026.6（目前驗收）。介面：English。說明文件：English / Traditional Chinese。

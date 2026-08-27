# R2O 2.0 — 操作流程模擬

> 依 [`資料生態決策表_三家建議.md`](資料生態決策表_三家建議.md)／[`資料生態決策表_合併.md`](資料生態決策表_合併.md) 的**已決原則**，用數字列表模擬真實操作。  
> 這是 **2.0 目標行為**的驗收腳本草案，不是現行已發布 1.x 保證會發生的事。  
> 指令名見 [`../rhino指令.md`](../rhino指令.md)。  
> 主線：Models → Camera → Point（light）→ **Scatter**；再進入第二輪改模型／相機／點位。

## 本模擬假設的專案

- 工作檔：`Demo_Apt.3dm`（已存檔）
- 設定根：同目錄 `_LoopFlow_Config/loopflow_R2O/`（XF-ECO-02）
- Octane 端以本機指標＋可手動覆寫找到同一設定根（XF-ED-04＝C）
- Point／Camera 資料檔為 **JSON**（R2O-ED-18＝B）；Lua 只 parse／apply，**不** `loadfile()` 執行專案資料
- 圖層與 Block（示範）：

| 用途 | Rhino 示範 | 誰讀它 |
|---|---|---|
| 建築等實模幾何 | `R2O::MDL::Architecture` 等 | Models → USDZ |
| 燈光／代理對齊點 | `R2O::LT::Downlight`、`R2O::FUR::Chair`（完整路徑成 `type_id`） | Point |
| 家具 Block 定義 | Block 名如 `Chair_A` | Scatter → 各 type 的 USD |
| 其他 | （任意） | 本輪可忽略 |

- 同末層名、不同父層 → **多個** Octane 節點，禁止靜默合併（R2O-ED-06＝B）。
- Models／Camera／Point／Scatter **可獨立執行**；文件建議順序如下，程式不強制整條重跑（R2O-ECO-04）。

---

## A. 開案與檢查

1. Rhino 開啟 `Demo_Apt.3dm` 並確認已存檔。未存檔則發布類指令停止（XF-ECO-01＝B）；Camera 也因設定在 `.3dm` 旁，未存檔無法寫路徑。
2. 按 `R2O_Open`：確認 `loopflow_R2O/`、Health（路徑、各通道 last-good、JSON schema、指標是否過期）。
3. 開 Octane 場景：LiveLink 讀指標或你手動填的專案路徑；Authoring 可分開安裝，不影響本模擬主鏈（R2O-ED-04＝B）。
4. （可選）確認舊 1.x 與 2.0 不混用同一專案設定（XF-ED-02：不升級、不可混用）。

---

## B. 第一輪：Models → Camera → Point → Scatter

### B1. Models 同步

5. 把要進實模的幾何整理到示範圖層（或依選取模式選好）。
6. 按 `R2O_Models`。
7. 預期磁碟：USDZ 走 pending → **材質後處理驗證通過** → atomic last-good（XF-ECO-04；R2O-ECO-03：後處理失敗＝整次失敗，不得假成功）。
8. 預期 Rhino：來源文件零變更；不會對已存檔文件自動 `Save`（XF-ECO-03）。
9. 在 Octane：**手動置換** USDZ（本輪主路徑；R2O-ED-02 文件應寫清手動置換）。材質應留在圖層 Xform 上，重換模型不掉接線。
10. 空範圍：阻擋，不發布。

### B2. Camera 同步

11. **先分清兩端（ED-13／ED-19）**  
    - **Rhino**：按 `R2O_Camera` 後持續寫 `live/camera.json`（event＋節流；安靜後必補最後一幀）。  
    - **1.x Octane 現況**：不背景讀檔；按 **Ctrl+Q**（跑一次 Lua）才套用——早期持續讀檔曾 lag，才改成「執行一次再同步」。  
    - **2.0 目標**：Octane 再試 **可開關的 real-time 輪詢**（mtime／revision 變才 parse＋apply）；關掉＝回到手動一次。
12. Rhino 調到透視視角（非透視應停止，ED-12）；確認已存檔後開／維持 Camera 發布。
13. 預期磁碟：`_LoopFlow_Config/loopflow_R2O/live/camera.json` atomic 發布（相對設定根的 `live/`）。
14. Octane：  
    - **手動模式**：跑一次 Camera LiveLink（或快捷鍵）套用最新 JSON。  
    - **real-time 模式（試用）**：開啟輪詢後，轉 Rhino 視角應跟到 Octane；若明顯 lag／雲端狂同步，關掉輪詢並回報（ED-19）。  
    - 找不到 Thin Lens／未指定目標相機＝套用失敗，不得標成已同步（XF-ECO-05、ED-12）。
15. 無有效相機：警告且不覆寫 last-good。

### B3. Point（light／代理點）同步

16. 確認對齊用 Point／相關物件在正確圖層路徑下（例如 R2O::LT::Downlight）。身分用專案內穩定 	ype_id（完整路徑映射），不是只靠末層同名（R2O-ECO-05、ED-05）。
17. 按 R2O_Point。
18. 預期：Point 通道寫出 **JSON**（ED-18＝B）；含 	ype_id、變換、可診斷用的來源資訊；經 validate 後 atomic last-good。
19. Octane：依 	ype_id 更新 Scatter／點群節點；缺 Proxy 的 type **略過並明確警告**，不靜默建空節點硬當成功（R2O-ED-08＝B）。
20. 未知 type、節點鍵碰撞：報告或整批停止（ED-11／ED-09），禁止默默進 Default_Point 或覆寫錯節點。

### B4. Scatter（接在 light／Point 之後）

21. 若場景有家具／燈具代理幾何：在 Rhino 確認對應 Block 定義存在（例如 Chair_A）。
22. 按 R2O_Scatter。
23. 預期：各 Block 匯出為獨立 USD（pending→validate→atomic）；單項失敗列出摘要，且**不得把來源 Block 永久留在原點**（R2O-ED-07＝A＋還原保證）。
24. 在 Octane：把 Scatter 資產接到對應 	ype_id 節點（Point 已建好的那側）。名稱對照以契約／manifest 為準，不要靠記憶把「圖層名」和「Block 名」混成同一個字。
25. 到這裡，第一輪「實模＋相機＋點位＋代理幾何」齊備。

---

## C. 第二輪：改模型後重同步 → 再更新相機、點位（必要時再 Scatter）

### C1. 改模型並重跑 Models

26. Rhino 改建築幾何並存檔；再按 R2O_Models。
27. Octane 再手動置換新的 last-good USDZ；材質接線應仍在。Point／Camera／Scatter 檔不應被 Models 指令刪掉。

### C2. 改相機與燈光點後再同步

28. 改視角：Rhino Camera 持續寫檔；Octane 若開著 real-time 應自動跟，否則再手動跑一次 LiveLink（ED-19）。
29. 移動／增刪 Point 圖層上的點 → R2O_Point。Octane 更新矩陣；Rhino 已刪的 type 依契約清理受管節點（ED-10），範圍一致。
30. 若換了家具 Block 定義或新增代理種類：再按一次 R2O_Scatter，然後在 Octane 確認資產與 	ype_id 仍對得上。
31. 任一步失敗：該通道 last-good 保留；來源 .3dm 不被改寫。

---

## D. 你應該感覺到的安全差異

32. Models 失敗時舊 USDZ 還在（不先刪再匯）。
33. Point／Camera 是 JSON 純資料，圖層名含引號也不會變成「可執行腳本」。
34. 同名末層、不同父層不會再靜默併成一個錯節點。
35. 未存檔不能發布；指標過期或路徑不存在時 consumer 停止並提示（XF-ED-04）。
36. Camera real-time 可關；關掉後行為應等同 1.x「手動一次套用」，不得卡住場景。

---

## E. 本模擬不涵蓋

- Authoring 工具擴充（本輪不擴功能）
- Models 的 Octane LiveLink 自動置換（若決定列曾寫 C，2.0 文件仍以手動置換為主路徑寫清）
- 與 R2B 共用 runtime（禁止；只共用文件層語彙）

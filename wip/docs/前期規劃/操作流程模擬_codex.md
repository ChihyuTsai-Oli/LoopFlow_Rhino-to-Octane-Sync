# R2O 2.0 — 操作流程模擬（Codex 版）

> 本文依 [`資料生態決策表_合併.md`](./資料生態決策表_合併.md) 的已決內容，並交叉核對 [`資料生態決策表_三家建議.md`](./資料生態決策表_三家建議.md)、[`現況與工作鏈藍圖.md`](./現況與工作鏈藍圖.md)、[`../rhino指令.md`](../rhino指令.md)、六份重構 SSOT 與現行 1.x Python／Lua 程式。
>
> 這是一份 **2.0 目標行為的操作與驗收模擬**，不是現行 1.x 功能保證，也不取代決策表或回寫後的正式契約。下列檔名代表已採用的角色方向；正式實作前仍須回寫 SSOT，凍結精確名稱與 schema。

## 先釐清 XF-ED-02

「不升級，新舊版不可混用」不是把舊版作業檔原地轉成新版。

- 舊版 `R2O_Path.txt`、AppData 資料、可執行 Lua 資料檔、快捷鍵與既有 Octane scene 保留給 1.x 使用。
- 進入 2.0 時，改用隔離的 LiveLink 安裝與全新的專案設定根；不讓 1.x、2.0 同時讀寫同一套同步資料。
- 原本的 Rhino `.3dm` 可以作為設計來源，但 2.0 不自動搬設定、不改寫來源，也不承諾把舊 Octane 節點身分自動轉換。
- 舊 scene／設定對照是人工重建與驗收依據，不代表存在 migration 工具。

## 模擬專案與資料角色

- Rhino 工作檔：`Demo_Apt.3dm`，已存檔於可寫入位置。
- Octane 工作場景：`Demo_Apt_R2O.orbx`，使用隔離的 2.0 LiveLink。
- 專案設定根：與 `.3dm` 同目錄的 `_LoopFlow_Config/loopflow_R2O/`。
- 示範資料：建築模型、`Tree_A`／`Sofa_B` Block 資產、各類 Point／Block instance、有效透視 viewport。
- Models、Scatter、Point、Camera 可單獨執行，沒有強制順序；第一次建案建議 Models → Scatter → Point → Camera，讓 Proxy 資產先於 instance 到位。

| 資料角色 | 模擬中的位置 | 發布規則 |
|---|---|---|
| 專案設定與穩定對照 | `config.json` | 包含外部 `type_id`／asset 對照；錯誤就停止 |
| Models | `models/` 下的 pending 與 last-good USDZ | 匯出＋材質後處理＋validate 全部成功才 atomic replace |
| Scatter assets | `scatter/` 下每個 `asset_key` 的 pending 與 last-good USD | 單項可失敗，其他項繼續；每項各自保留 last-good |
| Camera | `live/` 下的 pending 與 last-good JSON | Rhino event＋throttle＋trailing write；Octane 可切 real-time／手動 |
| Point | `live/` 下的 pending 與 last-good JSON | 只存資料，Lua 只 parse／apply，不執行專案資料檔 |
| 記錄 | `r2o.log` | 失敗可由訊息直接開到對應 channel／stage |

## 情境一：第一次以 2.0 建立專案

### 1. 隔離版本並建立設定根

1. 關閉仍使用 1.x LiveLink 的 Octane；不要用 2.0 覆蓋 1.x Lua 或讓兩版指向同一資料夾。
2. 在 Rhino 開啟 `Demo_Apt.3dm`。若尚未存檔，任何會建立設定或發布檔的動作都停止，不再沿用「新檔也寫到 AppData」的 1.x 行為（XF-ECO-01／R2O-ND-10）。
3. 按 `R2O_Open`，建立或確認 `_LoopFlow_Config/loopflow_R2O/`，並查看 Models、Scatter、Point、Camera 的 last-good、Octane 連線路徑與錯誤狀態。
4. Octane 端先讀本機「目前專案指標」；若使用者填過手動路徑，以手動覆寫為準。路徑不存在、產品不是 R2O、來源文件不符或指標過舊時停止，不猜最近資料夾（XF-ED-04）。
5. LiveLink 與 Authoring Tools 分開安裝。主流程只要求 LiveLink；Authoring 與其快捷鍵可不裝，不得阻塞同步（R2O-ED-04／17）。

### 2. 第一次發布 Models

6. 按 `R2O_Models`，選取要發布的模型範圍並確認物件數。空範圍、無可匯出幾何或取消都不碰 last-good。
7. Producer 由明確來源建立 pending USDZ；不搬動、不解鎖後遺留、不自動保存或改寫來源 `.3dm`。
8. USDZ 匯出後執行材質 binding 後處理，再驗證檔案可讀、非空、層級與材質結果。任何一步失敗都視為整次 Models 失敗（R2O-ECO-03）。
9. 全部通過才 atomic replace Models last-good；成功訊息包含物件數、檔案、revision 與完成時間，失敗訊息包含 stage、可採取動作與 log（R2O-ED-03）。
10. Octane 2.0 要同時定義兩種消費入口（R2O-ED-02＝C）：
    - 手動置換：使用者把既有 USDZ 節點改指向新的 last-good；這是現行程式已有證據的可靠主線。
    - LiveLink 更新：由 2.0 consumer 套用同一份 last-good；只有完整成功後才更新已套用 revision。
11. 不論走哪個入口，都不得因幾何更新而破壞 Octane-owned 材質、燈光參數或其他使用者節點；精確保留範圍在正式實作前寫入 ownership matrix。

### 3. 第一次發布 Scatter 資產

12. 在 Rhino 準備 `Tree_A`、`Sofa_B` 等 Block 定義，按 `R2O_Scatter` 選擇要發布的資產。
13. Producer 先對整批做 preflight：解析穩定 `type_id`、`asset_key`、輸出檔名與顯示名；正規化後若兩個來源會撞成同一技術鍵或檔名，整批在寫檔前停止並列出來源（R2O-ED-09）。
14. 每個 Block 在暫存資料／文件中以原點匯出，不移動工作 `.3dm` 裡的 Block instance。即使某一項丟出例外，來源位置與文件狀態也必須恢復（XF-ECO-03）。
15. 各資產獨立走 pending → validate → atomic last-good。`Tree_A` 失敗時可略過並繼續 `Sofa_B`，最後摘要成功、失敗與仍保留的舊版資產（R2O-ED-07）。

### 4. 第一次發布 Point／instance

16. 在 Rhino 的 Point 根圖層下放置 Point 或 Block instance。燈光與家具都走 Point 通道，以 `type_id`／subtype 區分，不另抄一條 R2B Light 指令（R2O-ED-15）。
17. 外部專案設定為每個來源角色保存穩定 `type_id`；完整圖層路徑只作 locator／來源資訊，末層名稱只作 `display_name`，兩者都不是永久 ID（R2O-ECO-05／ED-05）。
18. 按 `R2O_Point`。Producer 先檢查未知 type、重複 `type_id`、asset 對照與所有結構鍵，再寫 JSON；不得產生可被 `loadfile()` 執行的 Lua 資料（R2O-ED-18）。
19. 顯示名稱可保留引號、反斜線、換行、CJK 與 emoji；結構鍵若空白、非法或碰撞則硬失敗，不靠靜默消毒後覆寫另一筆（R2O-ND-05）。
20. Octane Lua 解析完整 JSON、驗證分通道 `schema_version`，確認整批可 apply 後才動場景，也只有 apply 成功才更新已套用狀態（XF-ECO-05／R2O-ND-04）。
21. 對每個已知 `type_id`，consumer 更新對應 Scatter node 的 transforms；位置、旋轉、縮放來自 Rhino，Proxy 幾何與材質由 Octane 擁有。
22. 若缺少對應 Proxy，略過該 type、清楚報告，並保留既有節點／舊狀態；未知 type 同樣略過並報告，不建立無內容的 `Default_Point`（R2O-ED-08／11）。
23. 同末層名但不同父圖層可形成兩個技術節點；兩者可有相同顯示名，但 `type_id` 不得相同（R2O-ED-06）。
24. 位置型燈光只同步 transform／type。能量、顏色與 IES 仍由 Octane 管理，不從 Rhino Point 推送（R2O-ED-16）。

### 5. 第一次同步 Camera

25. 在 Rhino 切到唯一要同步的有效透視 viewport，按 `R2O_Camera` 啟用 producer。非透視 viewport 不發布。
26. Rhino 端維持 view event＋節流；快速轉動後要補 trailing write，且必須提供手動推送一次，確保最後停下的視角會被發布（R2O-ED-13）。
27. Camera JSON 以 pending → validate → atomic last-good 發布，保留已驗證的 1.x 座標／FOV 數學並以 fixtures 鎖定（R2O-ND-12）。
28. Octane 明確指定目標 Thin Lens Camera。找不到、找到多台卻未指定時停止，不用 `cams[1]` 猜測（R2O-ED-12）。
29. Octane consumer 有兩種可切換模式（R2O-ED-19＝B）：
    - real-time：timer 只在 revision／mtime 改變時 parse＋apply；可隨時關閉。
    - 手動一次：按 `Ctrl+Q` 或執行 LiveLink Camera，套用最新 last-good。
30. 若 real-time 在實機重現 lag，預設切回手動一次，但保留 real-time 開關供後續測試；不能為了即時感強制永久輪詢。

## 情境二：日常增量更新

31. 使用者修改 Rhino 模型、移動 `Sofa_B` instances、新增 `Tree_A` 點位，並調整相機。需要保存設計變更時，由使用者自己存 `.3dm`。
32. 幾何改變時重跑 `R2O_Models`。Octane 走手動置換或 LiveLink 更新，兩者都只在新 last-good 完整可用後切換。
33. 若只是 instance 數量或 transforms 改變，只跑 `R2O_Point`；不必重跑 Models 或 Scatter。
34. 若 `Sofa_B` 的資產幾何本身改變，只發布該 Scatter 資產；Point 的穩定 `type_id` 不變，因此既有 transforms 與 Octane 節點關係不斷鏈。
35. Camera producer 已開啟時自動發布最後視角；Octane real-time 關閉時，在要定稿的時刻按一次 `Ctrl+Q`。
36. 任一通道失敗時，該通道仍使用上一份 last-good；其他通道可繼續獨立工作。

## 情境三：刪除與錯誤復原

| 操作／故障 | 2.0 預期結果 | 使用者下一步 |
|---|---|---|
| 未存檔便發布 | 停止，不寫 AppData 後備路徑 | 先存 `.3dm`，再重跑 |
| Models 材質後處理失敗 | 整次 Models 失敗，last-good 不變 | 由錯誤訊息開 log，修正後重跑 |
| Scatter 某一個 Block 匯出失敗 | 該項失敗、其他項繼續；來源 Block 不位移 | 看摘要修正該資產，舊資產 last-good 繼續可用 |
| 中文／emoji 顯示名 | 原樣保留於 display 欄位 | 不需為技術鍵改掉人類可讀名稱 |
| 兩個來源正規化後鍵值碰撞 | apply 前整批停止，不覆寫、不臨時加尾碼 | 在外部對照中指定不同穩定鍵 |
| Point 引用缺少 Proxy 的 type | 略過並報告，既有／stale 節點保留 | 先發布或連接 Proxy，再重跑 Point |
| Point 資料缺少／未知 type | 略過並報告，不塞入預設群組 | 補正 type 對照後重跑 |
| Rhino 刪除某個 type／全部點 | 只有完整權威 apply 後才把受管理節點標 inactive／隔離；不碰使用者節點 | 在 Octane 檢查後再決定清理或恢復 |
| Camera JSON 半寫／schema 不符 | 不 apply、不前移成功狀態，保留上一視角 | 等下一份完整發布或手動重跑 |
| Octane 有多台 Thin Lens Camera | 未指定時停止，不猜第一台 | 明確選擇目標相機 |
| real-time Camera lag | 關閉輪詢，回到手動一次 | Rhino 維持發布，定稿時按 `Ctrl+Q` |

## 完成驗收

37. Models 匯出、材質後處理或驗證任一失敗時，確認 Octane 仍能使用上一份 USDZ。
38. Scatter 人為製造單項失敗，確認其他項成功、失敗清單完整，且 Rhino Block instance 位置與文件 Modified 狀態不變。
39. 用同末層名、CJK、emoji、空名與正規化碰撞 fixtures 驗證：顯示名可保存，結構錯誤在寫檔／apply 前被擋下。
40. Point 重送相同 revision 不重複建立節點；刪除 type 時只處理受 R2O 管理範圍，先 inactive／隔離，不刪使用者節點。
41. Camera 快速連續移動後停下，確認 trailing write 是最後視角；real-time 與手動一次都套用到同一結果。
42. 分別中斷 Models、Scatter、Point、Camera，確認四條通道各自保留 last-good、訊息指出 channel＋stage，且其餘通道仍可執行。
43. 在隔離環境驗證 1.x Lua 資料檔不會被 2.0 `loadfile()` 執行；2.0 專案資料只走 JSON，Authoring Tools 缺席也不影響主鏈。

## 本輪刻意不做

- 不做 1.x→2.0 自動升級、雙寫、alias 或同一 Octane scene 混用。
- 不強迫 Models、Scatter、Point、Camera 依固定順序執行；第一次建案順序只是降低缺 Proxy 的建議。
- 不把燈能量、顏色、IES、Proxy 材質等 Octane-owned 內容寫回 Rhino。
- 不擴充 Authoring Tools，也不讓其 GUI／快捷鍵相容性阻塞 LiveLink。
- 不把開發機 repo 絕對路徑或 Dropbox 測試資產路徑寫入產品 runtime。

# R2O 2.0 — 操作流程模擬（Claude 版）

> 與 [`操作流程模擬_cursor_grok.md`](操作流程模擬_cursor_grok.md) 同源、不同視角，兩份並存互相對照，**都不改寫對方**。
> 依據：[`資料生態決策表_合併.md`](資料生態決策表_合併.md) 的已決欄、[`現況與工作鏈藍圖.md`](現況與工作鏈藍圖.md)、`_R2O_重構計畫.md`，以及現行 1.x 程式（Rhino 端 6 支 Python、Octane 端 8 支 Lua）。
> 這是 **2.0 目標行為**的驗收腳本草案，不是 1.x 現在會發生的事。指令名見 [`../rhino指令.md`](../rhino指令.md)。

本版維持三個獨有視角，這也是它和 grok 版的分工：

1. **磁碟上實際長什麼樣** — 每一步之後 `loopflow_R2O/` 裡多了什麼、少了什麼。可以直接開資料夾對照，不必猜。
2. **失敗、取消、中斷時停在哪裡** — 每一步都寫出「停下來時，Rhino／Octane／磁碟各是什麼狀態」。
3. **哪些現在就必須有、哪些可以晚點補** — 第一次實機測試不需要整條鏈都做完。

---

## 讀之前：五處裁決文字互相矛盾，我在模擬裡採用的讀法

多數決自動填入時，有幾列的「你的決定」與同列的整合建議方向、或與其他已採用的原則對不上。我沒有改動決策表，只在這裡說明本模擬採用哪一種讀法，**這五列請你回頭確認**。

| ID | 決定欄目前寫的 | 為什麼對不上 | 本模擬採用 |
|---|---|---|---|
| `R2O-ED-05` | 採 **C**（新 GUID 由 R2O 寫入） | C 必須把新 GUID 寫進 `.3dm` 的 UserText，直接違反 `XF-ECO-03`（來源零變更，強烈建議×3、已採用）。同列整合建議的方向其實是「完整圖層路徑正規化成 `type_id`」 | **完整路徑 → `type_id`**，另存 `display_name` 與 `source_layer_path`；不寫任何東西回 Rhino |
| `R2O-ND-02` | 採 **A**（維持 `R2O.usdz`、`R2O_Camera_Sync_Data.lua`、`R2O_Point_Sync_Data.lua`） | `R2O-ED-18` 已決採 JSON，被凍結的兩個檔名卻是 `.lua` 結尾 | **角色名＋ `.json`**：`models.usdz`／`camera.json`／`point.json`，各配一個 `*_pending` |
| `R2O-ED-10` | 採 **C**（標 inactive） | Octane 的 Scatter 節點沒有可放 inactive 的現成欄位，實作等於另發明一套命名；同列整合建議方向是 A，grok 版模擬第 29 步寫的也是 A 的行為 | **A（刪除受管節點）＋刪除清單列進報告**；範圍與更新一致（都限受管群組內） |
| `R2O-ED-02` | 採 **C**（手動置換 USDZ 與 LiveLink 腳本都要） | Octane 端目前**沒有任何** Models 相關 Lua；做 B 等於在 2.0 新增一種同步方式，與重構計畫「2.0 不新增同步種類」相衝突 | **A 為主路徑**（手動置換），B 標為 2.1 候選並在文件寫明現在沒有 |
| `XF-ED-02` | 不升級，新舊版不可混用 | 與 `R2O-ND-11`（Shortcut ID 凍結 1.x）並不衝突，但「不升級」讓 migration 的定義改變 | migration **只產生一份唯讀對照清單**（舊 `R2O_Path.txt` 的值長怎樣），供你手動重設，不自動轉換 |

另外有六列的決定欄只是把建議文字截斷貼上、沒有寫出選項字母（`R2O-ECO-03`、`ED-09`、`ED-12`、`ND-05`、`ND-07`、`ND-08`）。這些我照同列整合建議的方向讀，模擬內文有標出來。

---

## 示範專案

| 項目 | 本模擬用的值 |
|---|---|
| 工作檔 | `…\WIP_R2O\source\Demo_Apt.3dm`（已存檔） |
| 設定根 | `…\WIP_R2O\source\_LoopFlow_Config\loopflow_R2O\`（`XF-ECO-02`） |
| Octane 如何找到它 | AppData 指標檔為預設，Octane 端可手動覆寫；手動優先（`XF-ED-04`＝C） |
| 介面語言 | 全英文（`XF-ED-01`＝A）——下面引號內的訊息就是使用者實際會看到的字 |
| 資料檔格式 | JSON（`R2O-ED-18`＝B）。Lua 只 parse／apply，**不** `loadfile()` 專案資料 |

圖層與 Block：

| 用途 | Rhino 示範 | 誰讀它 | 產出 |
|---|---|---|---|
| 實模幾何 | `R2O::MDL::Architecture` 及其子層 | `R2O_Models` | `models.usdz` |
| 燈光對齊點 | `R2O::LT::Downlight`（Point 物件） | `R2O_Point` | `point.json` 的一筆 `type_id` |
| 家具代理點 | `R2O::FUR::Chair`（Point 或 Block instance） | `R2O_Point` | 同上，靠 `type` 欄區分燈／家具（`ED-15`＝A） |
| 家具幾何來源 | Block 定義 `Chair_A` | `R2O_Scatter` | `scatter/Chair_A.usd` |

`R2O::LT::Chair` 與 `R2O::FUR::Chair` 末層同名，在 2.0 會是**兩個**節點（`ED-06`＝B）。1.x 會把它們靜默併成一個（`LiveLink_R2O_Point.py` 說明第 23-24 行寫著這件事）。

---

## 磁碟：跑完一整輪之後，設定根應該長這樣

```text
Demo_Apt.3dm
_LoopFlow_Config/
  loopflow_R2O/
    config.json              ← 取代 R2O_Path.txt（ND-03＝B）
    r2o.log                  ← 取代 cursor_R2O_debug_log.txt（ND-08）
    live/                    ← 高頻小檔；Camera 每秒可能寫好幾次
      camera.json            last-good
      camera_pending.json    只在發布中的瞬間存在
      point.json             last-good
      point_pending.json
    models/                  ← 低頻大檔
      models.usdz            last-good
      models_pending.usdz
    scatter/
      Chair_A.usd
      Chair_A_pending.usd
```

分成 `live/` 與 `models/` 是因為工作檔在 Dropbox 裡（見工作區 `工作檔路徑.md`）。`camera.json` 最快 0.2 秒寫一次，和 USDZ 這種大檔放同一層，會讓雲端同步一直被觸發，也比較容易出現「衝突複本」讓 Octane 讀到錯的檔。**這是本模擬的建議，`R2O-ND-08` 的決定欄沒有寫到子資料夾層級，需要你確認。**

---

## 階段 0｜開案與 Health

**`R2O_Open`** → 從目前 `.3dm` 推出設定根 → 讀 `config.json` → 更新 AppData 指標檔 → 印出實際生效值與各通道 last-good 時間。

這一步 1.x 沒有等價物：現況每支程式各自從 AppData 推路徑，你無法確認「我改的設定有沒有生效」。2.0 加這一步是為了兩件事——確認 Octane 待會兒會讀到同一個資料夾，以及在還沒發布任何東西之前就先發現路徑問題。

畫面應該像這樣（全英文）：

```text
Project   : Demo_Apt.3dm
Config    : ...\_LoopFlow_Config\loopflow_R2O\
Pointer   : updated (AppData\...\current_project.json)
Last good : models.usdz  2026-08-27 14:02
            camera.json  2026-08-27 14:05
            point.json   (none)
```

> **使用者介入**：只在路徑或設定有問題時。日常開案不必按。
>
> **停在哪裡**：文件未存檔 → 顯示 `Save the file first.` 後停止，不建立任何資料夾、不猜路徑（`XF-ECO-01`＝B、`ND-10`＝A）。

**與 1.x 的差別你會感覺到**：現在 `R2O_Models` 遇到已存檔的文件會**直接幫你存檔**（`LiveLink_R2O_Models.py:184`）。2.0 之後不會——存檔完全由你決定，指令只負責檢查。

---

## 階段 1｜Models（USDZ）

**`R2O_Models`** → 選圖層 → 收集明確物件 ID → 在**暫存資料**上套材質規則 → 匯出 `models_pending.usdz` → 材質綁定後處理 → 驗證 → atomic 換成 `models.usdz`。

磁碟依序：`models_pending.usdz` 出現 → 後處理改寫它 → 驗證通過 → 一次改名成 `models.usdz`（舊的在這一刻才被取代）。

在 Octane：**手動置換** USDZ（`ED-02` 主路徑）。材質綁定會留在 `/Rhino/Geometry/<LayerName>` 這個 Xform 上，所以重換模型不會掉接線——這是 1.x 已經做對、2.0 要保留的行為（`LiveLink_R2O_Models.py:40-51` 的說明）。

> **使用者介入**：選圖層；在 Octane 手動置換。
>
> **停在哪裡**：
> - 空範圍 → `No exportable geometry in layer '<name>'.`，不發布，`models.usdz` 不動。
> - 匯出失敗 → `models_pending.usdz` 刪除或留著供診斷，`models.usdz` 是上一版。
> - **材質後處理失敗 → 整次失敗**（`R2O-ECO-03`），pending 不 promote。這一列的決定欄只寫「採用」，我照建議方向讀成「不得回報成功」。
> - 中途取消 → 來源 `.3dm` 的物件、圖層、選取、可見／鎖定狀態與 `doc.Modified` 全部與執行前相同。

**與 1.x 的三個差別**：(1) 現在是先 `os.remove` 舊 USDZ 再匯出（`:340-344`），失敗時 last-good 已經先沒了；(2) 現在後處理整段被 `except Exception: pass` 吞掉（`:159-160`），外層只看「檔案存在」就印成功（`:362-364`），所以你會拿到一個看起來成功、材質卻綁錯層級的 USDZ；(3) 現在會把來源物件的 `MaterialSource` 改成 `MaterialFromLayer` 並 `CommitChanges()`（`:322-324`），而還原只還原隱藏／鎖定，不還原這個。

---

## 階段 2｜Camera（JSON）

這一階段**兩端行為不同**，是本輪最需要講清楚的一段。

**Rhino 端**（`ED-13`＝A）：按 `R2O_Camera` 開始持續發布。event 觸發、約 0.2 秒節流，**安靜下來之後必須補送最後一幀**。

**Octane 端**（`ED-19`＝B）：2.0 再試可開關的 real-time 輪詢；關掉就回到 1.x 的行為——按 `Ctrl+Q` 跑一次才套用。

磁碟：`live/camera_pending.json` → validate → atomic → `live/camera.json`。payload 帶 `schema_version`（`ND-04`＝B，Camera 與 Point 各自一個版本號）。

座標與焦距數學凍結 1.x（`ND-12`＝A）：座標 `(x, z, -y)` 轉 Y-up、長度乘 `UnitScale(模型單位 → 公尺)`、FOV 用 `2·atan(36 / (2·鏡頭mm))`。**感光元件寬度是 36 mm，不是 35 mm**；決策表標題的「35mm」指的是等效焦距。

> **使用者介入**：切到你要的透視視角；決定 Octane 要開輪詢還是手動一次。
>
> **停在哪裡**：
> - 目前視埠不是透視 → 停止並提示，不發布（`ED-12`）。
> - Octane 找不到 Thin Lens 節點、或場景有多台而未指定 → **算套用失敗**，不更新「已套用」狀態（`XF-ECO-05`＋`ED-12`）。1.x 這裡只印一行 warning 就結束（`LiveLink_R2O_Camera.lua:72-75`）。
> - 沒有有效相機 → 警告，不覆寫 `camera.json`。
> - 開了輪詢之後明顯 lag 或雲端狂同步 → 關掉輪詢，回報實測值；預設改回手動，但**不刪掉開關**（`ED-19`）。

**與 1.x 的差別**：現在的節流在間隔不足 0.2 秒時直接 `return`（`LiveLink_R2O_Camera.py:100-101`），**沒有補送**。所以你快速轉完視角放手，最後一個位置可能永遠不會寫出去，Octane 停在中途畫面，要再跑一次才會對齊。2.0 的 trailing write 就是修這個。

---

## 階段 3｜Point（燈光／代理對齊）

**`R2O_Point`** → 掃 `PointLayer` 底下的 Point 與 Block → 每一項算出 `type_id`（完整圖層路徑正規化）、`type`（燈／家具，`ED-15`＝A）與變換矩陣 → 寫 `live/point_pending.json` → validate → atomic。

Octane 端依 `type_id` 更新 `R2O_Point_<type_id>` 節點；節點名前綴維持 `R2O_Point_`、群組維持 `R2O_Point`（`ND-06`＝A，改名會讓你現有場景的節點全變孤兒）。

字串處理（`ND-05`，決定欄只寫「契約寫死」）：同一支正規化函式、CJK 保留原字當顯示名、另存 ASCII 安全鍵當節點名；結構欄含不可表示字元一律硬失敗。

> **使用者介入**：把點放對圖層；在 Octane 把幾何接到對應節點。
>
> **停在哪裡**：
> - 正規化後 `type_id` 撞名 → **在寫任何檔案之前**整批停止，列出兩個原始圖層路徑（`ED-09`）。
> - 未知或缺 `type` → 略過並列進報告（`ED-11`＝B），不再靜默丟進 `Default_Point` 桶。
> - Octane 找不到對應 Proxy 幾何 → 略過該 type 並明確警告（`ED-08`＝B），不建空節點假裝成功。
> - Rhino 已刪的 type → 刪除受管節點並把刪除清單列進報告（本模擬採 A，見上方矛盾表）。

**與 1.x 的三個差別**：(1) 現在 `type` 就是末層圖層名（`LiveLink_R2O_Point.py:73`），同名末層會靜默合併；(2) 現在圖層名**未經任何處理**直接內插進 Lua 字串（`:93`），含引號的圖層名不只是壞資料，而是會被 Octane 執行到的內容——這正是 `ED-18` 改 JSON 的理由；(3) 現在更新是全場景搜尋（`LiveLink_R2O_Point.lua:137`）、清理只清群組內（`:182-187`），你把節點拖出群組之後它會一直被更新卻永遠不會被刪。

---

## 階段 4｜Scatter（Block → USD）

**`R2O_Scatter`** → 選 Block → 每個 Block 定義各自匯出 `scatter/<name>_pending.usd` → validate → atomic。

`ED-01`＝A：Scatter 維持獨立通道。代價要寫進使用說明——Scatter 的檔名來自 **Block 名**，Point 的 `type_id` 來自 **圖層路徑**，這是兩套詞彙，靠你在 Octane 手動接起來，沒有任何程式檢查它們對得上。

> **使用者介入**：選 Block；在 Octane 把 USD 接到 Point 已建好的節點。
>
> **停在哪裡**：
> - 單項失敗 → 略過該項、繼續其他項，最後列出失敗清單（`ED-07`＝A）。
> - **不論成功或失敗，來源 Block 都不得留在原點**。這是 A 的第二個完成條件。
> - 檔名碰撞 → 在寫檔前整批停止，列出兩個 Block 名（`ED-09`）。

**與 1.x 的兩個差別**：(1) 現在會把來源 Block 搬到原點再搬回（`LiveLink_R2O_Scatter.py:103、126`），而搬回**不在 `try/finally` 內**——中途失敗，Block 就永久停在原點；(2) 現在 `normalize_type_name()` 會把非 ASCII 整段刪掉並回傳預設值 `unnamed_block`（`LiveLink_R2O__Config.py:149-152`），所以兩個中文名的 Block 會同時寫成 `unnamed_block.usd`，後者直接蓋掉前者，沒有任何訊息。

---

## 第二輪：改東西之後

| 你改了什麼 | 要重跑什麼 | 不該被影響的 |
|---|---|---|
| 建築幾何 | `R2O_Models` → Octane 手動置換 | `camera.json`、`point.json`、`scatter/*.usd` 都不該被 Models 指令碰到 |
| 視角 | 不必按任何東西（Camera 持續發布）；Octane 開輪詢就自動跟，沒開就手動跑一次 | 其他三個通道 |
| 移動／增刪對齊點 | `R2O_Point` → Octane 更新矩陣 | Octane 端你手接的材質與幾何連線 |
| 換家具 Block 定義 | `R2O_Scatter`，然後確認 `type_id` 與資產仍對得上 | `point.json` |

四個通道可獨立執行、沒有強制順序（`ECO-04`）。文件寫的順序只是建議。

---

## 中斷、取消與失敗停在哪裡

這張表是我認為最該拿去當驗收清單的一張。每一格都應該可以在實機上真的做出來。

| 情境 | Rhino 來源文件 | 設定根磁碟 | Octane 場景 | 使用者看到 |
|---|---|---|---|---|
| 文件未存檔就按發布指令 | 不變 | 完全不建立 | 不變 | `Save the file first.` |
| Models 匯出中按 Esc | 物件／圖層／選取／`doc.Modified` 全部與執行前相同 | `models.usdz` 是上一版 | 不變 | `Cancelled at stage: export.` |
| Models 材質後處理失敗 | 同上 | `models.usdz` 是上一版；pending 保留供診斷 | 不變 | `Failed at stage: material post-process.` ＋可開 log |
| Scatter 第 3 項失敗 | 前 2 項的 Block 已還原原位；第 3 項的 Block **也**必須還原 | 前 2 個 `.usd` 已發布，第 3 個維持上一版 | 不變 | `Exported 2 of 3. Failed: Chair_C.` |
| Camera 寫檔時 Dropbox 鎖住檔案 | 不變 | `camera.json` 是上一版 | 停在上一個位置 | log 有記錄；不跳視窗打斷建模 |
| Octane 讀到寫到一半的 JSON | 不變 | 不變 | 不變，**且下一輪會重試** | 輪詢模式下靜默重試；手動模式下印失敗原因 |
| Octane 找不到 Thin Lens | 不變 | 不變 | 不變 | `No thin lens camera found.`，且**不**標成已同步 |
| Rhino 當掉 | 只可能少掉你自己還沒存的東西——**指令本身不會吃掉未存修改** | 最多留下一個 `*_pending` 檔 | 不變 | — |

最後一列是 R2O 和 R2B 現況最大的差別：R2O 目前不會偷改 `doc.Modified`，R2B 會（見 R2B 那份模擬）。

---

## 第一階段最小可用範圍

第一次實機測試不需要整條鏈。我建議的順序是：

1. **設定根＋指標檔＋Health**（階段 0）。沒有這個，後面每一步都無法確認 Octane 讀的是不是同一個資料夾。這也是 `XF-ED-04` 唯一能被驗證的方式。
2. **atomic publisher 一支**，先給 Camera 用。Camera 是寫最頻繁的通道，publisher 有問題最快在這裡暴露。
3. **Camera 端到端**（Rhino 發布 → Octane 手動一次套用）。先不做輪詢——手動模式等同 1.x 行為，可以直接和現況比對。
4. **Point**：`type_id` 正規化＋碰撞檢查＋JSON schema。這一段的 fixtures 最值錢（中文、引號、emoji、空名、同末層名）。
5. **Models**：pending → 後處理 → validate → atomic。
6. **Scatter**：最後做，因為它的價值依賴 Point 已經正確。
7. **Camera 輪詢**（`ED-19`）：放在最後，因為它是唯一「試試看、不行就關掉」的項目，不該擋住前面六項。

可以晚點補、不影響前六項的：Authoring 分包（`ED-04`）、shortcut 預設鍵（`ED-17`）、log 檔改名、`R2O_Open` 的完整診斷畫面。

---

## 這條流程還沒回答的問題

寫完這一輪，我認為還有四件事沒有答案，而且都會在實作時擋住人：

1. **指標檔過期怎麼判定。** `XF-ED-04`＝C 已定，但沒有定義「過舊」是多久、以及 Octane 開著沒關而你在 Rhino 換了專案時該怎麼辦。建議：指標帶來源文件路徑＋更新時間，Octane 每次 apply 前比對，不一致就停止並顯示兩邊的值。
2. **`type_id` 正規化規則本身還沒寫死。** `ND-05` 說「契約寫死」，但完整路徑要怎麼變成一個 ASCII 安全鍵（分隔符、大小寫、長度上限、CJK 怎麼處理）沒有定案。這件事一旦上線就不能改，因為它決定 Octane 節點名。
3. **Point 與 Scatter 的配對關係沒有機制。** 兩套詞彙靠人手接，錯了不會有人發現。最便宜的補法是讓 `point.json` 帶一個 `expected_asset` 欄位，Octane 端只做比對與報告，不自動接線。
4. **Camera 輪詢的 lag 標準沒定。** `ED-19` 說「lag 復發則改回手動」，但沒有可判定的門檻。建議先量一個數字（例如視角停止後多久 Octane 跟上），否則「有沒有 lag」會變成主觀爭論。

---

## 與 cursor grok 版的主要差異

兩份都依同一張決策表，結論方向一致。差別在於：

| | grok 版 | 本版 |
|---|---|---|
| 形式 | 一條連續編號的操作清單（36 步） | 分階段，每階段附磁碟狀態與停點 |
| 對矛盾裁決的處理 | 直接採用建議方向（例如 `ED-05` 實際寫成 `type_id`，`ED-10` 寫成清理節點），未說明與決定欄的落差 | 開頭獨立一節列出五處落差與本模擬採用的讀法，請你回頭確認 |
| 失敗行為 | 分散在各步驟的但書 | 集中成一張中斷矩陣，可直接當驗收表 |
| 與 1.x 的對照 | 「你應該感覺到的安全差異」四點 | 每階段末尾附具體 `檔名:行號`，說明現在為什麼會出錯 |
| 實作順序 | 未涵蓋 | 「第一階段最小可用範圍」七步 |
| 未決事項 | 未涵蓋 | 「還沒回答的問題」四項 |

建議兩份一起看：grok 版適合照著點一遍確認流程順不順，本版適合在寫程式前確認每一步的失敗行為與磁碟狀態。

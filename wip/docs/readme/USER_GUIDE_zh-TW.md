# LoopFlow R2O 2.0 使用說明總覽

> 一分鐘理解 2.0 怎麼運作。按鈕與逐步操作見 [指令逐項說明](./COMMANDS_zh-TW.md)。產品介紹與安裝見 [專案主頁初稿](./README_zh-TW.md)。

## 核心邏輯：單向、分通道

**Rhino 產出，Octane 讀取。** 不會從 Octane 改回 Rhino。

1. **先把 `.3dm` 存檔。** 未存檔就不能發布。設定與交換檔都放在這份檔案旁邊，不寫死某台電腦的路徑。
2. **各通道獨立。** 模型、選取物件、相機、點位可以分開跑，沒有必須一次做完的固定流水線。
3. **成對使用。** Rhino 的 `ROModels` 對 Octane 載入／關再開 `R2O.usdz`；`ROObjects` 對自行載入時戳 USDZ。不要交叉拿檔。

模型同步的重點是：不管更新幾次，Octane 裡已經接好的同名材質接口可以留下。接口跟 **Rhino 材質名稱** 走，不是圖層名。

## 專案以資料夾為單位

已存檔的 `.3dm` 所在資料夾就是作業資料夾。LoopFlow 會在同一層建立：

```text
_LoopFlow_Config/loopflow_R2O/
  live/      ← 相機、點位
  models/    ← R2O.usdz、選取物件的時戳 USDZ
  lua/       ← Octane 腳本（開發期測檔根會有；不是每案必有）
```

換電腦時把整個專案資料夾一起搬即可。

1.x 把交換檔放在 AppData。2.0 不再用那裡當交換根。

## 兩端怎麼對

| 你要做的事 | Rhino | Octane |
|---|---|---|
| 主模型（有材質） | `ROModels` | 第一次載入 `R2O.usdz`；之後覆寫同一檔則**關再開** |
| 選取物件 | `ROObjects` | 自行載入時戳 USDZ |
| 相機 | `ROCamera` 開／關；右鍵 `ROCameraPush` 推一次 | 跑 `R2O_Camera.lua`（Ctrl+Q）套用一次 |
| 點位（燈／家具） | `ROPoint` | 跑 `R2O_Point.lua` 套用一次 |
| 看設定與說明 | `ROOpen` | （目前無對等面板） |

Rhino 工具列 **Rhino to OctaneRender Sync** 有四顆鈕：左鍵是 Open／Models／Camera／Point，右鍵是 Objects／Camera Push。Authoring 不在這份工具列。

## 幾個要先懂的名詞

| 名詞 | 意思 |
|---|---|
| **作業資料夾** | 已存檔 `.3dm` 所在層。 |
| **關再開** | 主模型更新後關掉 Octane 再開，已連結的 USDZ 才會跟上。不要按 Reload mesh／Load new mesh。 |
| **材質接口** | Rhino 裡的**材質名稱**。不同圖層只要同名就是同一個接口。 |
| **Scatter** | 點位套用後出現在場景根；前綴 `R2O_Point_`。用來接燈與家具 Proxy。 |
| **Health** | 設定根路徑，以及 Camera／Point／Models／Objects 上次成功寫出的時間。 |

## 失敗時會停在哪

- 未存檔：發布停止，並用英文說明。
- 匯出取消、失敗或中斷：仍在原來的工作檔；上次成功的輸出不會被半套檔蓋掉。
- 相機：Octane 場景必須恰好一台已 Expand 的 Thin Lens，否則不改節點。

系統不會自己往下一通道繼續跑。

## 想知道怎麼按

這一頁只講邏輯。指令列名稱、工具列左／右鍵、Octane 腳本與圖層怎麼擺，見 [指令逐項說明](./COMMANDS_zh-TW.md)。

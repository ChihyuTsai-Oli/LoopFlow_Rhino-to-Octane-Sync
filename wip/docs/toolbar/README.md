# 產品工具列與 Package Manager 圖示

把 `ExportRuiFile` 匯出的 `.rui` 與清單圖示 `icon.png` 放在這裡，建置時由 `wip/packaging/g02-spike/build.ps1` 複製進 yak。

正式工具列分頁是 **LoopFlow R2O**。四顆鈕懸停（左鍵／右鍵）：R2O Config／R2O Model（按鈕面 R2O Models）+R2O Objects／R2O Camera+R2O Camera Push／R2O Point。Authoring 不進這份 Rhino 工具列。

RUI 需要一個 `tool_bar_group`。分頁與工具列清單顯示 **LoopFlow R2O**。不要寫入 `SelectedToolbarSet`。不要改 GUID。Package Manager 圖示檔名 `icon.png`。

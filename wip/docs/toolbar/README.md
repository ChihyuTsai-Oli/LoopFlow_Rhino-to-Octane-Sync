# 產品工具列與 Package Manager 圖示

把 `ExportRuiFile` 匯出的 `.rui` 與清單圖示 `icon.png` 放在這裡，建置時由 `wip/packaging/g02-spike/build.ps1` 複製進 yak。

正式按鈕左鍵（右鍵留空）：

```text
! _ROCamera
! _ROCameraPush
! _ROModels
! _ROObjects
! _ROPoint
! _ROOpen
```

RUI 需要一個 `tool_bar_group`（顯示名建議 `Rhino to OctaneRender Sync`）。不要寫入 `SelectedToolbarSet`。不要改 GUID。Authoring 不進這份 Rhino 工具列。

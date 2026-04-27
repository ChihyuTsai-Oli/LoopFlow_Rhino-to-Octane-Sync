# -*- coding: utf-8 -*-
"""
============================================================
程式名稱 (Program) : LiveLink Rhino to Octane Standalone (Point Sender)
版本 (Version)     : v4.0
日期 (Date)        : 2026-04-27
開發者 (Author)    : Cursor + Claude Sonnet 4.6
開發環境 (Env)     : Rhino 8 (CPython 3.9) / Python 3
同步檔案 (File)    : 由 R2O_Path.txt 的 PointFile 欄位決定（預設 R2O_Point_Sync_Data.lua）
============================================================
【使用說明】
1. 確保環境：程式會自動讀取或建立設定檔（%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\R2O_Path.txt）。
2. 放置標記：在 PointLayer 根圖層下建立任意子圖層結構，將點或圖塊放置其中。
   例：R2O::LT_Points::Downlight_A、R2O::FUR_Points::Sofa_B、R2O::PPL::Person_A
3. 執行同步：執行本程式，即可輸出帶有位移與旋轉資訊的 Lua 同步檔。

【圖層導向分類與雙模態】
- 範圍判斷：物件所在圖層路徑必須以 PointLayer + "::" 開頭（預設 "R2O::"）。
- 類型命名：Scatter 節點類型名稱取自最末端子圖層名稱（split("::")[-1]）。
- 雙模態支援：使用「點」僅傳遞位置（identity 旋轉）；「圖塊」傳遞完整變換矩陣。
- 命名唯一性：跨群組若末段名稱相同（如 R2O::LT::Chair 與 R2O::FUR::Chair），
  會合併至同一 Scatter 節點，請確保命名唯一。

【Scatter 用 USD 製作說明】
- 若要在 Octane Scatter 中使用 USD 作為散佈幾何，來源物件在 Rhino 端必須為 Block。
- Block 原點須對齊世界座標原點（0, 0, 0），以確保 Scatter 旋轉軸正確。
- 欲匯出的 Block 可單獨放置於 `USD::物件名稱` 圖層（不需放在 R2O:: 之下），
  再另行執行 USD 匯出流程，與本腳本的點位同步互不干擾。

【變數連動注意事項】
- 讀取 R2O_Path.txt：
  - `DataPath`：輸出同步檔目錄
  - `PointLayer`：根圖層前綴（預設 R2O）
  - `PointFile`：同步檔檔名（預設 R2O_Point_Sync_Data.lua）
- 例外會寫入：%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\cursor_R2O_debug_log.txt
============================================================
"""
import rhinoscriptsyntax as rs
import Rhino
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from LiveLink_R2O__Config import load_r2o_config, log_exception, safe_write_text_atomic

def export_octane_points():
    doc = Rhino.RhinoDoc.ActiveDoc
    cfg = load_r2o_config()
    export_dir = cfg["DataPath"]
    target_prefix = cfg["PointLayer"] + "::"
    sync_file_name = cfg["PointFile"]

    points = rs.ObjectsByType(1) or []
    blocks = rs.ObjectsByType(4096) or []
    all_objects = points + blocks

    if not all_objects:
        print("R2O Point: 場景中找不到任何點或圖塊。")
        return

    scale = Rhino.RhinoMath.UnitScale(doc.ModelUnitSystem, Rhino.UnitSystem.Meters)
    entries = []

    for obj_id in all_objects:
        layer_full = rs.ObjectLayer(obj_id)

        if not layer_full.startswith(target_prefix):
            continue

        layer_type = layer_full.split("::")[-1]

        if rs.ObjectType(obj_id) == 1:
            coord = rs.PointCoordinates(obj_id)
            oct_x = coord.X * scale
            oct_y = coord.Z * scale
            oct_z = -coord.Y * scale

            row0 = [1.0, 0.0, 0.0, oct_x]
            row1 = [0.0, 1.0, 0.0, oct_y]
            row2 = [0.0, 0.0, 1.0, oct_z]

        elif rs.ObjectType(obj_id) == 4096:
            m = rs.BlockInstanceXform(obj_id)
            row0 = [m.M00, m.M02, -m.M01, m.M03 * scale]
            row1 = [m.M20, m.M22, -m.M21, m.M23 * scale]
            row2 = [-m.M10, -m.M12, m.M11, -m.M13 * scale]
        else:
            continue

        entry = '        {{ type = "{}", xform = {{ {:.5f}, {:.5f}, {:.5f}, {:.5f},  {:.5f}, {:.5f}, {:.5f}, {:.5f},  {:.5f}, {:.5f}, {:.5f}, {:.5f} }} }},'.format(
            layer_type,
            row0[0], row0[1], row0[2], row0[3],
            row1[0], row1[1], row1[2], row1[3],
            row2[0], row2[1], row2[2], row2[3]
        )
        entries.append(entry)

    if not entries:
        print("R2O Point: 在 [{}] 圖層內找不到任何點位或圖塊。".format(target_prefix))
        return

    lua_content = "return {{\n    items = {{\n{}\n    }}\n}}".format("\n".join(entries))
    sync_file_path = os.path.join(export_dir, sync_file_name)

    try:
        safe_write_text_atomic(sync_file_path, lua_content, encoding="utf-8")
        print("R2O Point: 成功打包了 {} 個物件至 {} (根圖層: {})".format(
            len(entries), export_dir, target_prefix
        ))
    except Exception as e:
        log_exception("LiveLink_R2O_Point", e, context={"sync_file_path": sync_file_path, "export_dir": export_dir})

if __name__ == "__main__":
    export_octane_points()

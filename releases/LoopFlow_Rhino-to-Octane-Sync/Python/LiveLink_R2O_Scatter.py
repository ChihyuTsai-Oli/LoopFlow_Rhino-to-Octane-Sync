# -*- coding: utf-8 -*-
"""
============================================================
程式名稱 (Program) : LiveLink Rhino to Octane Standalone (Scatter USD Exporter)
版本 (Version)     : v2.0
日期 (Date)        : 2026-04-27
開發者 (Author)    : Cursor + Claude Sonnet 4.6
開發環境 (Env)     : Rhino 8 (CPython 3.9) / Python 3
同步檔案 (File)    : 無（各 Block 個別匯出為 {Block名稱}.usd）
============================================================
【使用說明】
1. 在 Rhino 中選取一或多個 Block 物件（可預先選取後再執行腳本）。
2. 腳本會驗證所有選取物件均為 Block；若包含非 Block 物件，
   將跳出警告視窗並中止操作。
3. 執行後彈出資料夾選擇視窗，指定 USD 匯出目的地資料夾。
4. 每個 Block 定義（依名稱去重複）依序執行：
   - 以插入點（base point）為基準平移至世界原點
   - 匯出為 {Block定義名稱}.usd
   - 還原至原始位置
5. 完成後於命令列輸出成功/失敗統計。

【注意事項】
- Block 需先確保自身幾何的原點已對齊世界座標 (0,0,0)，
  才能讓 Scatter 旋轉軸在 Octane 中正確對應。
- 若同一 Block 定義有多個 Instance，只會匯出一次（幾何相同）。
- Block 名稱中的特殊字元會自動替換為底線以確保檔名合法。

【變數連動注意事項】
- 匯出路徑：由使用者每次執行時即時選擇，不讀取 R2O_Path.txt。
- 例外會寫入：%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\cursor_R2O_debug_log.txt
============================================================
"""
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from LiveLink_R2O__Config import log_exception, normalize_type_name


def RhinoToOctaneScatter():
    export_dir = None
    try:
        # 1. 取得選取物件（支援預先選取）
        obj_ids = rs.GetObjects(
            "選取要匯出的 Block 物件",
            filter=0,
            preselect=True,
            select=False
        )
        if not obj_ids:
            return

        # 2. 驗證全部為 Block，否則彈出警告並中止
        non_blocks = [oid for oid in obj_ids if not rs.IsBlockInstance(oid)]
        if non_blocks:
            rs.MessageBox(
                "選取的物件中包含 {} 個非 Block 物件。\n"
                "請確認所有選取物件均為 Block 後再執行。\n\n操作已中止。".format(len(non_blocks)),
                buttons=0,
                title="R2O Scatter 警告"
            )
            return

        # 3. 選取匯出資料夾
        export_dir = rs.BrowseForFolder(message="選取 USD 匯出資料夾")
        if not export_dir:
            return

        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        # 4. 依 Block 定義名稱去重複（同名 Block 幾何相同，只需匯出一次）
        unique_blocks = {}
        for oid in obj_ids:
            name = rs.BlockInstanceName(oid)
            if name and name not in unique_blocks:
                unique_blocks[name] = oid

        if not unique_blocks:
            print("R2O Scatter: 無法取得 Block 名稱，匯出取消。")
            return

        exported_count = 0
        failed_names = []

        rs.EnableRedraw(False)
        try:
            for block_name, oid in unique_blocks.items():
                # 5. 取得插入點，平移至原點
                ins_pt = rs.BlockInstanceInsertPoint(oid)
                if ins_pt is None:
                    print("R2O Scatter: 無法取得 {} 的插入點，略過。".format(block_name))
                    failed_names.append(block_name)
                    continue

                move_to_origin = [-ins_pt.X, -ins_pt.Y, -ins_pt.Z]
                move_back = [ins_pt.X, ins_pt.Y, ins_pt.Z]

                rs.MoveObject(oid, move_to_origin)

                # 6. 建立匯出路徑（Block 名稱做為檔名）
                safe_name = normalize_type_name(block_name, "unnamed_block")
                export_path = os.path.join(export_dir, safe_name + ".usd")

                if os.path.exists(export_path):
                    try:
                        os.remove(export_path)
                    except Exception:
                        pass

                # 7. 選取此 Block 並匯出
                rs.UnselectAllObjects()
                rs.SelectObject(oid)

                quote = chr(34)
                usd_cmd = '_-Export ' + quote + export_path + quote + ' _Enter _Enter'
                rs.Command(usd_cmd, False)

                rs.UnselectAllObjects()

                # 8. 移回原位
                rs.MoveObject(oid, move_back)

                if os.path.exists(export_path):
                    print("R2O Scatter: 已匯出 {} -> {}".format(block_name, export_path))
                    exported_count += 1
                else:
                    print("R2O Scatter: {} 匯出失敗，檔案未產生。".format(block_name))
                    failed_names.append(block_name)

        finally:
            rs.EnableRedraw(True)

        # 9. 完成統計
        print("R2O Scatter: 完成，共匯出 {} / {} 個 Block USD 檔案。".format(
            exported_count, len(unique_blocks)
        ))
        if failed_names:
            print("R2O Scatter: 以下 Block 匯出失敗：{}".format(", ".join(failed_names)))

    except Exception as exc:
        log_exception(
            "LiveLink_R2O_Scatter",
            exc,
            context={
                "export_dir": export_dir,
            },
        )


if __name__ == "__main__":
    RhinoToOctaneScatter()

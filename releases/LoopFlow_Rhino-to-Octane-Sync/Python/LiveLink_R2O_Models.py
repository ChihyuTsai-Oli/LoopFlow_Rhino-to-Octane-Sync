# -*- coding: utf-8 -*-
"""
============================================================
程式名稱 (Program) : LiveLink Rhino to Octane Standalone (USDZ Model Sync)
版本 (Version)     : v3.0
日期 (Date)        : 2026-04-27
開發者 (Author)    : Cursor + Claude Sonnet 4.6
開發環境 (Env)     : Rhino 8 (CPython 3.9) / Python 3
同步檔案 (File)    : 由 R2O_Path.txt 的 ModelFile 欄位決定（預設 R2O.usdz）
============================================================
【使用說明】
1. 確保環境：程式會自動讀取或建立設定檔（%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\R2O_Path.txt）。
2. 圖層選擇：每次執行時彈出圖層選擇視窗，可選任意母圖層；上次選擇會記憶為預設值。
3. 強制匯出：無視圖層內的隱藏或鎖定狀態，必定強制打包匯出。
4. 幾何淨化：自動濾除圖層內的點、線、註解等非渲染物件。
5. 輸出路徑：ModelDir 不為空時輸出至 ModelDir，空白時 fallback 至 DataPath。

【變數連動注意事項】
- 讀取 R2O_Path.txt：
  - `DataPath`：預設輸出目錄（ModelDir 為空時使用）
  - `ModelDir`：自訂 USDZ 輸出目錄（空白 = fallback 至 DataPath）
  - `ModelFile`：輸出檔名（預設 R2O.usdz）
  - `LastModelLayer`：記憶上次匯出的圖層名稱
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
from LiveLink_R2O__Config import load_r2o_config, log_exception, _write_config

def RhinoToOctaneModelSync():
    export_usd_path = None
    export_dir = None
    target_layer_root = None
    try:
        cfg = load_r2o_config()

        # 彈出圖層選擇視窗，記憶上次選擇
        last_layer = cfg.get("LastModelLayer", "") or None
        target_layer_root = rs.GetLayer("選擇要匯出的模型圖層", default_layer=last_layer)
        if not target_layer_root:
            return
        cfg["LastModelLayer"] = target_layer_root
        _write_config(cfg)

        # 輸出路徑：ModelDir 不為空時使用 ModelDir，否則 fallback 至 DataPath
        model_dir = cfg.get("ModelDir", "").strip() or cfg["DataPath"]
        export_usd_path = os.path.join(model_dir, cfg["ModelFile"])
        export_dir = model_dir

        if sc.doc.Path:
            rs.Command("_-Save _Enter", False)

        rs.EnableRedraw(False)
        try:
            doc = Rhino.RhinoDoc.ActiveDoc
            if not doc:
                print("R2O Models: 找不到作用中的 RhinoDoc，匯出取消。")
                return

            if not os.path.exists(export_dir):
                os.makedirs(export_dir)

            # 1) 以圖層白名單挑選要匯出的物件（避免切檔/開啟中轉檔）
            target_fullpaths = set()
            for layer in doc.Layers:
                if layer is None or layer.IsDeleted:
                    continue
                fp = layer.FullPath
                if fp == target_layer_root or fp.startswith(target_layer_root + "::"):
                    target_fullpaths.add(fp)

            if not target_fullpaths:
                print("R2O Models: 找不到目標圖層 {}，匯出取消。".format(target_layer_root))
                return

            # 2) 只保留可渲染的幾何類型（濾除點/線/註解等 2D 類）
            allowed_types = (
                Rhino.DocObjects.ObjectType.Brep
                | Rhino.DocObjects.ObjectType.Extrusion
                | Rhino.DocObjects.ObjectType.Mesh
                | Rhino.DocObjects.ObjectType.SubD
                | Rhino.DocObjects.ObjectType.Surface
                | Rhino.DocObjects.ObjectType.InstanceReference
            )

            # 3) 無視圖層/物件狀態：包含不可見圖層、鎖定、隱藏物件
            layer_state_before = {}
            obj_state_before = {}  # id -> (was_hidden, was_locked)

            def snapshot_layer_states():
                for layer in doc.Layers:
                    if layer is None or layer.IsDeleted:
                        continue
                    layer_state_before[layer.Id] = (layer.IsVisible, layer.IsLocked)

            def force_layers_visible_unlocked():
                for layer in doc.Layers:
                    if layer is None or layer.IsDeleted:
                        continue
                    fp = layer.FullPath
                    if fp in target_fullpaths:
                        if not layer.IsVisible:
                            layer.IsVisible = True
                        if layer.IsLocked:
                            layer.IsLocked = False
                        layer.CommitChanges()

            def snapshot_object_state(rh_obj):
                try:
                    obj_state_before[rh_obj.Id] = (bool(rh_obj.IsHidden), bool(rh_obj.IsLocked))
                except Exception:
                    obj_state_before[rh_obj.Id] = (False, False)

            def force_object_visible_unlocked(obj_id):
                try:
                    doc.Objects.Unlock(obj_id, True)
                except Exception:
                    pass
                try:
                    doc.Objects.Show(obj_id, True)
                except Exception:
                    pass

            def restore_object_states():
                for obj_id, (was_hidden, was_locked) in obj_state_before.items():
                    try:
                        if was_locked:
                            doc.Objects.Lock(obj_id, True)
                        else:
                            doc.Objects.Unlock(obj_id, True)
                    except Exception:
                        pass
                    try:
                        if was_hidden:
                            doc.Objects.Hide(obj_id, True)
                        else:
                            doc.Objects.Show(obj_id, True)
                    except Exception:
                        pass

            def restore_layer_states():
                for layer in doc.Layers:
                    if layer is None or layer.IsDeleted:
                        continue
                    st = layer_state_before.get(layer.Id)
                    if not st:
                        continue
                    try:
                        layer.IsVisible = st[0]
                        layer.IsLocked = st[1]
                        layer.CommitChanges()
                    except Exception:
                        pass

            snapshot_layer_states()
            force_layers_visible_unlocked()

            # 用 enumerator 取得包含 hidden/locked 的物件清單
            settings = Rhino.DocObjects.ObjectEnumeratorSettings()
            settings.IncludeDeletedObjects = False
            settings.IncludeGrips = False
            settings.HiddenObjects = True
            settings.LockedObjects = True

            export_ids = []
            for obj in doc.Objects.GetObjectList(settings):
                if obj is None or obj.IsDeleted:
                    continue

                try:
                    layer_index = obj.Attributes.LayerIndex
                    layer = doc.Layers[layer_index] if layer_index >= 0 else None
                    layer_fp = layer.FullPath if layer else None
                except Exception:
                    continue

                if not layer_fp or layer_fp not in target_fullpaths:
                    continue

                if (obj.ObjectType & allowed_types) == 0:
                    continue

                snapshot_object_state(obj)
                force_object_visible_unlocked(obj.Id)

                # 強制 Material 走圖層（避免物件自帶材質來源造成不一致）
                try:
                    attr = obj.Attributes
                    if attr.MaterialSource != Rhino.DocObjects.ObjectMaterialSource.MaterialFromLayer:
                        attr.MaterialSource = Rhino.DocObjects.ObjectMaterialSource.MaterialFromLayer
                        obj.CommitChanges()
                except Exception:
                    pass

                export_ids.append(obj.Id)

            if not export_ids:
                print("R2O Models: {} 圖層內沒有可匯出的模型（Brep/Mesh/SubD/Block），匯出取消。".format(target_layer_root))
                return

            # 4) 最終 USDZ 匯出（以「選取後 Export」方式）
            if os.path.exists(export_usd_path):
                try:
                    os.remove(export_usd_path)
                except Exception:
                    pass

            rs.UnselectAllObjects()
            rs.SelectObjects(export_ids)

            selected = rs.SelectedObjects() or []
            print("R2O Models: 準備匯出 {} 個物件至 {}".format(len(selected), export_usd_path))

            quote = chr(34)
            usd_cmd = '_-Export ' + quote + export_usd_path + quote + ' _Enter _Enter'
            rs.Command(usd_cmd, False)

            rs.UnselectAllObjects()
            restore_object_states()
            restore_layer_states()

        finally:
            rs.EnableRedraw(True)
            if os.path.exists(export_usd_path):
                print("R2O Models: 成功將 {} 圖層產出為 {}".format(target_layer_root, export_usd_path))
            else:
                print("R2O Models: 檔案未產生，請確認路徑或權限。")
    except Exception as exc:
        log_exception(
            "LiveLink_R2O_Models",
            exc,
            context={
                "export_usd_path": export_usd_path,
                "export_dir": export_dir,
                "target_layer_root": target_layer_root,
            },
        )

if __name__ == "__main__":
    RhinoToOctaneModelSync()

# -*- coding: utf-8 -*-
"""
============================================================
Script Name        : LiveLink Rhino to Octane Standalone (USDZ Model Sync)
Version            : v1.0
Date               : 2026-04-28
Author             : Cursor + Claude Sonnet 4.6
Environment        : Rhino 8 (CPython 3.9) / Python 3
Sync File          : Determined by the ModelFile field in R2O_Path.txt (default: R2O.usdz)
============================================================
[Usage]
1. Environment: the script auto-reads or creates the config file
   (%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\R2O_Path.txt).
2. Layer selection: a layer picker appears on each run; any parent layer can be chosen;
   the last selection is remembered as the default.
3. Force export: hidden or locked states inside the layer are ignored; everything is exported.
4. Geometry cleanup: points, curves, annotations, and other non-render objects are filtered out.
5. Output path: writes to ModelDir when set; falls back to DataPath if empty.

[Variable Notes]
- Reads R2O_Path.txt:
  - `DataPath`      : default output directory (used when ModelDir is empty)
  - `ModelDir`      : custom USDZ output directory (empty = fallback to DataPath)
  - `ModelFile`     : output file name (default: R2O.usdz)
  - `LastModelLayer`: remembers the last exported layer name
- Exceptions are written to: %APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\cursor_R2O_debug_log.txt
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

        # Show layer picker; remember last selection
        last_layer = cfg.get("LastModelLayer", "") or None
        target_layer_root = rs.GetLayer("Select the model layer to export", layer=last_layer)
        if not target_layer_root:
            return
        cfg["LastModelLayer"] = target_layer_root
        _write_config(cfg)

        # Output path: use ModelDir when set, otherwise fall back to DataPath
        model_dir = cfg.get("ModelDir", "").strip() or cfg["DataPath"]
        export_usd_path = os.path.join(model_dir, cfg["ModelFile"])
        export_dir = model_dir

        if sc.doc.Path:
            rs.Command("_-Save _Enter", False)

        rs.EnableRedraw(False)
        try:
            doc = Rhino.RhinoDoc.ActiveDoc
            if not doc:
                print("R2O Models: No active RhinoDoc found. Export cancelled.")
                return

            if not os.path.exists(export_dir):
                os.makedirs(export_dir)

            # 1) Build a layer whitelist to select objects (avoids switching/opening intermediate files)
            target_fullpaths = set()
            for layer in doc.Layers:
                if layer is None or layer.IsDeleted:
                    continue
                fp = layer.FullPath
                if fp == target_layer_root or fp.startswith(target_layer_root + "::"):
                    target_fullpaths.add(fp)

            if not target_fullpaths:
                print("R2O Models: Target layer '{}' not found. Export cancelled.".format(target_layer_root))
                return

            # 2) Keep only renderable geometry types (filter out points, curves, annotations, etc.)
            allowed_types = (
                Rhino.DocObjects.ObjectType.Brep
                | Rhino.DocObjects.ObjectType.Extrusion
                | Rhino.DocObjects.ObjectType.Mesh
                | Rhino.DocObjects.ObjectType.SubD
                | Rhino.DocObjects.ObjectType.Surface
                | Rhino.DocObjects.ObjectType.InstanceReference
            )

            # 3) Ignore layer/object state: include invisible, locked, and hidden objects
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

            # Use an enumerator to get the full object list including hidden/locked items
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

                # Force material source to layer (prevents per-object material sources causing inconsistency)
                try:
                    attr = obj.Attributes
                    if attr.MaterialSource != Rhino.DocObjects.ObjectMaterialSource.MaterialFromLayer:
                        attr.MaterialSource = Rhino.DocObjects.ObjectMaterialSource.MaterialFromLayer
                        obj.CommitChanges()
                except Exception:
                    pass

                export_ids.append(obj.Id)

            if not export_ids:
                print("R2O Models: No exportable geometry (Brep/Mesh/SubD/Block) found in layer '{}'. Export cancelled.".format(target_layer_root))
                return

            # 4) Final USDZ export (via "select then Export")
            # Octane identifies objects by USD prim path (derived from Rhino layer names).
            # As long as layer names are unchanged, prim paths remain stable and materials stay connected.
            if os.path.exists(export_usd_path):
                try:
                    os.remove(export_usd_path)
                except Exception:
                    pass

            rs.UnselectAllObjects()
            rs.SelectObjects(export_ids)

            selected = rs.SelectedObjects() or []
            print("R2O Models: Exporting {} object(s) to {}".format(len(selected), export_usd_path))

            quote = chr(34)
            usd_cmd = '_-Export ' + quote + export_usd_path + quote + ' _Enter _Enter'
            rs.Command(usd_cmd, False)

            rs.UnselectAllObjects()
            restore_object_states()
            restore_layer_states()

        finally:
            rs.EnableRedraw(True)
            if os.path.exists(export_usd_path):
                print("R2O Models: Layer '{}' exported successfully to {}.".format(target_layer_root, export_usd_path))
            else:
                print("R2O Models: Output file was not created. Please check the path and permissions.")
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

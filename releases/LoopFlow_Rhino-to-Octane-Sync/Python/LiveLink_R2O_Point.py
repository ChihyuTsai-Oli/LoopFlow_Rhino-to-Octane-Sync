# -*- coding: utf-8 -*-
"""
============================================================
Script Name        : LiveLink Rhino to Octane Standalone (Point Sender)
Version            : v1.0
Date               : 2026-04-28
Author             : Cursor + Claude Sonnet 4.6
Environment        : Rhino 8 (CPython 3.9) / Python 3
Sync File          : Determined by the PointFile field in R2O_Path.txt (default: R2O_Point_Sync_Data.lua)
============================================================
[Usage]
1. Environment: the script auto-reads or creates the config file
   (%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\R2O_Path.txt).
2. Place markers: create any sublayer structure under the PointLayer root layer
   and place Points or Blocks inside them.
   E.g. R2O::LT_Points::Downlight_A, R2O::FUR_Points::Sofa_B, R2O::PPL::Person_A
3. Run the script to output a Lua sync file containing position and rotation data.

[Layer-driven classification & dual mode]
- Scope: the object's layer path must start with PointLayer + "::" (default "R2O::").
- Type name: the Scatter node type is taken from the terminal sub-layer name (split("::")[-1]).
- Dual mode: Points pass position only (identity rotation); Blocks pass the full transform matrix.
- Naming uniqueness: if two groups share the same terminal name
  (e.g. R2O::LT::Chair and R2O::FUR::Chair) they merge into one Scatter node — ensure names are unique.

[Creating scatter USD assets]
- To use USD geometry in an Octane Scatter, the source object must be a Block in Rhino.
- The Block's origin must be aligned to the world origin (0, 0, 0) for correct Scatter rotation.
- The Block can be placed in a `USD::<name>` layer (not under R2O::) and exported separately;
  this does not interfere with the point sync in this script.

[Variable Notes]
- Reads R2O_Path.txt:
  - `DataPath`  : output directory for the sync file
  - `PointLayer`: root layer prefix (default: R2O)
  - `PointFile` : sync file name (default: R2O_Point_Sync_Data.lua)
- Exceptions are written to: %APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\cursor_R2O_debug_log.txt
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
        print("R2O Point: No Points or Blocks found in the scene.")
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
        print("R2O Point: No Points or Blocks found under layer prefix [{}].".format(target_prefix))
        return

    lua_content = "return {{\n    items = {{\n{}\n    }}\n}}".format("\n".join(entries))
    sync_file_path = os.path.join(export_dir, sync_file_name)

    try:
        safe_write_text_atomic(sync_file_path, lua_content, encoding="utf-8")
        print("R2O Point: Successfully exported {} entry(ies) to {} (root layer: {})".format(
            len(entries), export_dir, target_prefix
        ))
    except Exception as e:
        log_exception("LiveLink_R2O_Point", e, context={"sync_file_path": sync_file_path, "export_dir": export_dir})

if __name__ == "__main__":
    export_octane_points()

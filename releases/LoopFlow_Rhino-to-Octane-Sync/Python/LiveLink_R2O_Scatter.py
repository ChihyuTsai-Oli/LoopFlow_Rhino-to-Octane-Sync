# -*- coding: utf-8 -*-
"""
============================================================
Script Name        : LiveLink Rhino to Octane Standalone (Scatter USD Exporter)
Version            : v1.0
Date               : 2026-04-28
Author             : Cursor + Claude Sonnet 4.6
Environment        : Rhino 8 (CPython 3.9) / Python 3
Sync File          : None (each Block is exported individually as {BlockName}.usd)
============================================================
[Usage]
1. Select one or more Block objects in Rhino (pre-selection before running is supported).
2. The script validates that all selected objects are Blocks; if non-Block objects are
   included, a warning dialog appears and the operation is aborted.
3. A folder picker opens — choose the USD export destination folder.
4. For each unique Block definition (deduplicated by name):
   - Translate to the world origin using the insertion point (base point)
   - Export as {BlockDefinitionName}.usd
   - Restore to original position
5. A success/failure summary is printed to the command line on completion.

[Notes]
- The Block's internal geometry origin must be aligned to the world origin (0,0,0)
  for the Scatter rotation axis to work correctly in Octane.
- If the same Block definition has multiple instances, it is exported only once (geometry is identical).
- Special characters in Block names are automatically replaced with underscores for valid file names.

[Variable Notes]
- Export path: chosen by the user at runtime; R2O_Path.txt is not read.
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
from LiveLink_R2O__Config import log_exception, normalize_type_name, DATA_DIR


def RhinoToOctaneScatter():
    export_dir = None
    try:
        # 1. Get selected objects (pre-selection supported)
        obj_ids = rs.GetObjects(
            "Select Block objects to export",
            filter=0,
            preselect=True,
            select=False
        )
        if not obj_ids:
            return

        # 2. Validate all objects are Blocks; abort with warning if not
        non_blocks = [oid for oid in obj_ids if not rs.IsBlockInstance(oid)]
        if non_blocks:
            rs.MessageBox(
                "The selection contains {} non-Block object(s).\n"
                "Please ensure all selected objects are Blocks before running.\n\nOperation aborted.".format(len(non_blocks)),
                buttons=0,
                title="R2O Scatter Warning"
            )
            return

        # 3. Select export folder
        export_dir = rs.BrowseForFolder(message="Select the USD export folder", folder=DATA_DIR)
        if not export_dir:
            return

        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        # 4. Deduplicate by Block definition name (identical geometry — export once)
        unique_blocks = {}
        for oid in obj_ids:
            name = rs.BlockInstanceName(oid)
            if name and name not in unique_blocks:
                unique_blocks[name] = oid

        if not unique_blocks:
            print("R2O Scatter: Could not retrieve Block names. Export cancelled.")
            return

        exported_count = 0
        failed_names = []

        rs.EnableRedraw(False)
        try:
            for block_name, oid in unique_blocks.items():
                # 5. Get insertion point and move to origin
                ins_pt = rs.BlockInstanceInsertPoint(oid)
                if ins_pt is None:
                    print("R2O Scatter: Could not get insertion point for '{}'. Skipping.".format(block_name))
                    failed_names.append(block_name)
                    continue

                move_to_origin = [-ins_pt.X, -ins_pt.Y, -ins_pt.Z]
                move_back = [ins_pt.X, ins_pt.Y, ins_pt.Z]

                rs.MoveObject(oid, move_to_origin)

                # 6. Build export path (Block name used as file name)
                safe_name = normalize_type_name(block_name, "unnamed_block")
                export_path = os.path.join(export_dir, safe_name + ".usd")

                if os.path.exists(export_path):
                    try:
                        os.remove(export_path)
                    except Exception:
                        pass

                # 7. Select this Block and export
                rs.UnselectAllObjects()
                rs.SelectObject(oid)

                quote = chr(34)
                usd_cmd = '_-Export ' + quote + export_path + quote + ' _Enter _Enter'
                rs.Command(usd_cmd, False)

                rs.UnselectAllObjects()

                # 8. Restore to original position
                rs.MoveObject(oid, move_back)

                if os.path.exists(export_path):
                    print("R2O Scatter: exported {} -> {}".format(block_name, export_path))
                    exported_count += 1
                else:
                    print("R2O Scatter: Export failed for '{}' — output file not created.".format(block_name))
                    failed_names.append(block_name)

        finally:
            rs.EnableRedraw(True)

        # 9. Summary
        print("R2O Scatter: Done. Exported {} / {} Block USD file(s).".format(
            exported_count, len(unique_blocks)
        ))
        if failed_names:
            print("R2O Scatter: The following Blocks failed to export: {}".format(", ".join(failed_names)))

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

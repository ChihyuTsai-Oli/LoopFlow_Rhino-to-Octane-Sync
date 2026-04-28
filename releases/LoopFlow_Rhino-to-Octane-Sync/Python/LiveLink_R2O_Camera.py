# -*- coding: utf-8 -*-
"""
============================================================
Script Name        : LiveLink Rhino to Octane Standalone (Camera Sender)
Version            : v1.0
Date               : 2026-04-28
Author             : Cursor + Claude Sonnet 4.6
Environment        : Rhino 8 (CPython 3.9) / Python 3
Sync File          : Determined by the CameraFile field in R2O_Path.txt (default: R2O_Camera_Sync_Data.lua)
============================================================
[Usage]
1. Environment: the script auto-reads or creates the config file
   (%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\R2O_Path.txt).
2. Live sync: no need to save the file first; new unsaved files are synced immediately.
3. Run the script to start/stop camera live sync.

[Variable Notes]
- Reads R2O_Path.txt:
  - `DataPath`  : output directory for the sync file
  - `CameraFile`: sync file name (default: R2O_Camera_Sync_Data.lua)
- Exceptions are written to: %APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\cursor_R2O_debug_log.txt
============================================================
"""
import Rhino
import scriptcontext as sc
import os
import math
import sys
import System
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from LiveLink_R2O__Config import load_r2o_config, log_exception, safe_write_text_atomic

# ── Module-level constants (centralised for easy tuning) ──────────────────
DEFAULT_LENS_MM  = 50.0
MIN_INTERVAL_SEC = 0.2
EPS_POSITION     = 1e-4
EPS_FOV          = 1e-4

def export_octane_camera(sender, e):
    try:
        doc = Rhino.RhinoDoc.ActiveDoc
        if not doc:
            return

        if not doc.Views.ActiveView:
            return

        vp = doc.Views.ActiveView.ActiveViewport

        cfg = load_r2o_config()
        export_dir = cfg["DataPath"]
        sync_file_name = cfg["CameraFile"]
        sync_file_path = os.path.join(export_dir, sync_file_name)

        scale = Rhino.RhinoMath.UnitScale(doc.ModelUnitSystem, Rhino.UnitSystem.Meters)

        def convert_coord(rh_obj, is_point=True):
            oct_x = rh_obj.X
            oct_y = rh_obj.Z
            oct_z = -rh_obj.Y
            if is_point:
                return oct_x * scale, oct_y * scale, oct_z * scale
            return oct_x, oct_y, oct_z

        loc = convert_coord(vp.CameraLocation, True)
        tar = convert_coord(vp.CameraTarget, True)
        up = convert_coord(vp.CameraUp, False)

        lens_length = float(vp.Camera35mmLensLength) if vp.Camera35mmLensLength else 0.0
        if lens_length <= 0.0:
            lens_length = DEFAULT_LENS_MM

        fov_degrees = 2.0 * math.atan(36.0 / (2.0 * lens_length)) * (180.0 / math.pi)

        payload = (loc, tar, up, round(fov_degrees, 6))

        state_key = "R2O_CAMERA_SYNC_STATE_V3_2"
        state = sc.sticky.get(state_key, {})
        now = time.monotonic()

        last_time = state.get("last_time", 0.0)
        last_payload = state.get("last_payload")

        if last_payload is not None:
            try:
                loc_d = max(abs(payload[0][i] - last_payload[0][i]) for i in range(3))
                tar_d = max(abs(payload[1][i] - last_payload[1][i]) for i in range(3))
                up_d = max(abs(payload[2][i] - last_payload[2][i]) for i in range(3))
                fov_d = abs(payload[3] - last_payload[3])
                no_change = loc_d < EPS_POSITION and tar_d < EPS_POSITION and up_d < EPS_POSITION and fov_d < EPS_FOV
            except Exception:
                no_change = False

            if no_change:
                return

        if (now - last_time) < MIN_INTERVAL_SEC:
            return

        lua_content = """return {{
    position = {{{0:.5f}, {1:.5f}, {2:.5f}}},
    target = {{{3:.5f}, {4:.5f}, {5:.5f}}},
    up_vector = {{{6:.5f}, {7:.5f}, {8:.5f}}},
    fov_degrees = {9:.5f}
}}""".format(
            loc[0], loc[1], loc[2],
            tar[0], tar[1], tar[2],
            up[0], up[1], up[2],
            fov_degrees
        )

        safe_write_text_atomic(sync_file_path, lua_content, encoding="utf-8")

        state["last_time"] = now
        state["last_payload"] = payload
        state["sync_file_path"] = sync_file_path
        sc.sticky[state_key] = state
    except Exception as exc:
        log_exception("LiveLink_R2O_Camera", exc)

def toggle_octane_camera_sync():
    event_key = "R2Octane_Camera_Sync_Delegate_V3_2"

    if event_key in sc.sticky:
        handler = sc.sticky[event_key]
        Rhino.Display.RhinoView.Modified -= handler
        sc.sticky.pop(event_key, None)
        print("R2O Camera Sync: Live sync stopped.")
    else:
        cfg = load_r2o_config()
        handler = System.EventHandler[Rhino.Display.ViewEventArgs](export_octane_camera)
        sc.sticky[event_key] = handler
        Rhino.Display.RhinoView.Modified += handler

        export_octane_camera(None, None)
        print("R2O Camera Sync: Live sync started. (Output bound to {})".format(cfg["DataPath"]))

if __name__ == "__main__":
    toggle_octane_camera_sync()

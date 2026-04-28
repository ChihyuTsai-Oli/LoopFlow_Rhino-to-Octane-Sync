# LoopFlow R2O User Guide

> All Rhino-side scripts run in the Rhino 8 (CPython 3.9) environment.
> Octane-side tools are LUA scripts. Set the script path in OctaneRender Standalone and complete the shortcut binding before use.

Last updated: 2026-04-28

---

## Table of Contents

1. [Rhino-Side Scripts](#rhino-side-scripts)
2. [Octane Side — Sync Functions](#octane-side--sync-functions)
3. [Octane Side — Utility Tools](#octane-side--utility-tools)
4. [Config File](#config-file)

---

## Rhino-Side Scripts

---

### R2O_Models (Model Sync)

One-click export of the selected layer as a USDZ model.

**Execution steps:**

1. If the Rhino file is already saved, it is auto-saved once before export
2. A layer picker appears — select the parent layer to export (last selection is remembered)
3. Hidden and locked states on layers and objects are ignored; all renderable geometry is force-exported (Brep / Mesh / SubD / Block)
4. Material source is forced to "by layer" on all objects, ensuring UUID is tied to the layer name
5. Layer and object states are snapshotted before export and fully restored afterwards

**Why materials stay connected:**

USDZ maps layer names to USD Prim Paths, which determine the UUID. As long as the layer name does not change, the UUID remains the same, keeping all material assignments in Octane intact across syncs.

> **Layer naming warning:** Renaming a layer changes its UUID, requiring material re-assignment. Finalise your layer structure before starting render work.

---

### R2O_Camera (Live Camera Sync)

Toggle design: run once to start, run again to stop.

- Writes camera data immediately on any Rhino viewport rotation or zoom (at most once per 0.2 s)
- Outputs a LUA file (`R2O_Camera_Sync_Data.lua`) read by `LiveLink_R2O_Camera.lua` in Octane
- Coordinate system is converted automatically (Rhino Y-up → Octane Y-up / Z-forward) and scaled to metres
- No need to save the Rhino file first

> **To stop:** run R2O_Camera again to terminate the background listener.

---

### R2O_Point (Light and Furniture Position Sync)

Scans Point and Block objects in the scene and outputs position and transform matrix data for Octane Scatter nodes.

- Reads the layer prefix set by `PointLayer` in the config (default: `R2O`)
- The **terminal sub-layer name** is used as the Scatter node type; Octane matches it to a light fixture or furniture proxy
- **Point objects:** position only, identity rotation
- **Block objects:** full transform matrix (including scale and rotation)
- Outputs `R2O_Point_Sync_Data.lua`

**Layer naming example:**

```
R2O/
  LT_Points/
    Downlight        ← type = "Downlight" → Scatter node in Octane
    WallLight
  FUR_Points/
    Sofa_A           ← type = "Sofa_A" → furniture proxy
    Table_B
```

> **Naming uniqueness:** if two different parent layers share the same terminal sub-layer name (e.g. `R2O::LT::Chair` and `R2O::FUR::Chair`), they merge into one Scatter node. Ensure all terminal names are globally unique.

---

### R2O_Scatter (Block USD Export)

Exports selected Block objects as individual `.usd` files for use as Octane Scatter proxies.

**Execution steps:**

1. Select one or more Block objects in Rhino (pre-selection is supported)
2. The script validates all selected objects are Blocks; aborts with a warning if non-Block objects are included
3. Choose a USD export destination folder
4. For each unique Block definition (same name exported only once):
   - Moves the Block to the world origin, exports as `{BlockName}.usd`, then restores the original position

> **Important:** The internal geometry origin of the Block must be aligned to `(0,0,0)` for the Scatter rotation axis to work correctly in Octane.
>
> Blocks can be placed in a `USD::<name>` layer (outside `R2O::`) so that R2O_Point does not treat them as sync point markers.

---

### R2O_Open (Quick Open Utility)

Opens related files directly from the Rhino command line.

| Option | Description |
|---|---|
| **Config** | Open `R2O_Path.txt` config file |
| **DataFolder** | Open the data directory |
| **DebugLog** | Open `cursor_R2O_debug_log.txt` debug log |

---

## Octane Side — Sync Functions

---

### LiveLink_R2O_Camera.lua

Reads the camera sync file written by Rhino and updates the Thin Lens Camera in the Octane scene.

**Default shortcut:** `Ctrl + Q`

**Usage:**

1. Start `R2O_Camera` live sync on the Rhino side (keep it running)
2. In Octane, press `Ctrl + Q` to apply the latest camera view

> **Note:** The Thin Lens Camera node must be **expanded** out of the Render Target as a standalone node. A camera collapsed inside the Render Target cannot be accessed by this script.

---

### LiveLink_R2O_Point.lua

Reads the Points sync file written by Rhino and creates or updates Scatter nodes in the Octane scene.

**Usage:**

1. Run `R2O_Point` on the Rhino side to export sync data
2. Run this script in Octane — Scatter nodes are automatically created or updated

**Node management logic:**

- **Existing nodes:** Transform data is updated in place without moving the node (preserving user connections)
- **New nodes:** Created inside the Group specified by `PointNgName` in the config (default: `R2O_Point`)
- **Removed types:** Only orphaned nodes inside the Group are deleted; nodes outside the Group are untouched

---

## Octane Side — Utility Tools

The following tools are independent of the R2O sync workflow and can be used on their own.

---

### Auto_PBR_Universal.lua (PBR Material Builder)

**Default shortcut:** `Ctrl + Shift + T`

Select a texture folder and automatically build a Universal Material packed into a Nodegraph.

- Auto-detects PBR map types (Albedo, Roughness, Normal, Metallic, Displacement, etc.)
- Automatically creates Box Projection + 3D Transform node groups
- Displacement maps are created as a separate Group B node — not connected to the material by default; connect manually
- Nodegraph name is derived from the common prefix of texture filenames
- Remembers the last selected folder path
- Supports ACEScg (default) or sRGB colour workflow (change the `CS_COLOR` variable)

> **Spawn position:** select any node in the scene before running — the new Nodegraph spawns to the right of the selected node.

---

### Auto_PBR_Switch_UV.lua (UV Mode Toggle)

**Default shortcut:** `Ctrl + T`

Toggles the UV projection mode of a Nodegraph created by `Auto_PBR_Universal`.

| Mode | Description |
|---|---|
| **Mode 1 (Box Projection)** | Textures routed through BoxProjection → Transform (default) |
| **Mode 2 (UV Transform)** | Textures routed directly through Transform; BoxProjection pin disconnected |

Accepted selections (any of the following):
- Select the target Nodegraph
- Select any node inside the Nodegraph
- Select a Universal Material node on the canvas
- Run inside the Nodegraph canvas with nothing selected

---

### Auto_Convert_StdSurf_to_Universal.lua (Material Format Conversion)

**Default shortcut:** `Shift + M`

Converts Standard Surface materials inside selected USD geometry nodes to Universal Material.

- Automatically backs up texture paths and colour values; restores them after creating the new Universal Material
- Nodes with matching Pin IDs are auto-inherited; remapped pins (e.g. Base Color → Albedo) are rebuilt
- IOR values are mapped to the corresponding Universal Material IOR pins
- Useful for one-click conversion after importing USD assets from external sources

---

### Auto_Align_Nodes.lua (Node Auto-Align)

**Default shortcut:** `Alt + A`

Select at least 2 nodes, then run to align them to a common horizontal baseline and arrange them left-to-right by X position.

- A dialog appears before execution to set the gap between nodes (px; negative values cause overlap; default `-10`)
- Horizontal baseline is aligned to the Y coordinate of the topmost selected node

---

## Config File

### `R2O_Path.txt` (located at `%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\`)

Auto-created on first run; missing fields are backfilled automatically.

| Field | Default | Description |
|---|---|---|
| `DataPath` | (auto) | Root data output directory |
| `ModelDir` | (empty) | USDZ model output directory; falls back to DataPath when empty |
| `PointLayer` | `R2O` | Root layer prefix for Points / Blocks sync |
| `ModelFile` | `R2O.usdz` | USDZ model output file name |
| `CameraFile` | `R2O_Camera_Sync_Data.lua` | Camera sync LUA file name |
| `PointFile` | `R2O_Point_Sync_Data.lua` | Points sync LUA file name |
| `PointNgName` | `R2O_Point` | Scatter group node name in Octane |
| `PointPrefix` | `R2O_Point_` | Scatter node name prefix |
| `LastModelLayer` | (auto) | Remembers the last layer selected for model export |

> Use `R2O_Open > Config` to open this file directly from the Rhino command line.
> The Octane-side LUA scripts read the same `R2O_Path.txt`, so Rhino and Octane share a single config.

# Changelog

## [2.1.0] - 2026-11-14

Rhino 8 and Rhino 9 install the same `rh8_0` package. On Rhino 9, `ROObjects` and `ROModels` write a USDZ file. `ROModels` lists only the top layer and then opens Detailed Mesh Settings. Choosing that layer still exports its sublayers. Canceling the mesh dialog does not write a file. Do not overwrite `v2.0.16`. Quit Rhino completely after install.

## [2.0.16] - 2026-11-10

Toolbar buttons now have dedicated light and dark SVG artwork for Rhino 8 themes. Do not overwrite `v2.0.15`. Quit Rhino completely after install.

## [2.0.15] - 2026-11-09

Material and layer-node names keep only English letters, digits, and underscores. Every other character becomes `_`. Do not overwrite `v2.0.14`.

## [2.0.14] - 2026-11-08

`R2O_Camera.lua` applies the camera connected to the Render Target. The Thin Lens can sit outside the node or stay inside it. Success does not show a dialog. Do not overwrite `v2.0.13`.

## [2.0.13] - 2026-11-07

Each apply of `R2O_Point.lua` places managed Scatter nodes left to right by name, including a re-import. `R2O_Point_Geometry` stays where it is, and existing wires are left in place. Do not overwrite `v2.0.12`.

## [2.0.12] - 2026-11-07

Leaf layer nodes include the parent layer name, so the same child name under different parents stays separate. Each leaf gets its own material socket, and the exported shader is kept so Octane lists it. After `ROModels` or `ROObjects`, layer visibility and lock return to each layer's own state. The source `.3dm` is not saved. Do not overwrite `v2.0.11`.

## [2.0.11] - 2026-11-06

USD material sockets stay on the Rhino material name, so a later export after geometry edits keeps the Octane wires. Layer names in the USD stay ASCII; two layers that would collapse to the same underscores get `_2`. Confirmed on Rhino 8 and OctaneRender Studio+ 2026.6. The first export after this version needs each Universal wired once. Do not overwrite `v2.0.10`.

## [2.0.10] - 2026-11-04

Point scatters and `R2O_Point_Geometry` pack into the `R2O_Point` node graph. The graph exposes one geometry output (`NT_OUT_GEOMETRY`); wire that into the scene. Adding or deleting Rhino `R2O::` types and applying again updates the graph in place. Do not overwrite `v2.0.9`.

## [2.0.9] - 2026-11-04

Package updates write the Lua stamp from the yak `manifest.yml` version. Updating from 2.0.8 then running any formal command empties the Documents lua folder and copies the official scripts, including the Point Geometry group. Do not overwrite `v2.0.8`.

## [2.0.8] - 2026-11-03

Point scatters connect into one Geometry group named `R2O_Point_Geometry`, so the scene wires that group once. Each scatter input is still where you attach a light or furniture proxy. `ROObjects` starts again after the locked-layer export helpers were renamed. Do not overwrite `v2.0.7`.

## [2.0.7] - 2026-11-03

`ROModels` exports geometry on locked layers, including locked parent layers and layers inside block definitions. Blocks are not exploded. If those objects cannot be selected, the previous `R2O.usdz` is left in place. Do not overwrite `v2.0.6`.

## [2.0.6] - 2026-10-12

The Rhino toolbar is included again and opens on install. **LoopFlow R2X** stays an optional extra toolbar. Do not overwrite `v2.0.5`.

## [2.0.5] - 2026-10-12

This package no longer opens its own Rhino tab. Use the shared **LoopFlow R2X** tab from `loopflow-R2X-Toolbar`. A tab already loaded in Rhino stays until you close it. Do not overwrite `v2.0.4`.

## [2.0.4] - 2026-09-28

Patch release.

- Package Manager listing icon (800×800). Food4Rhino listing was updated separately.

## [2.0.3] - 2026-08-31

Patch release.

- Prefer Package Manager install src over stale `.rhinocode/libs` cache when resolving foundation.
- Formal commands use `find_templates` (not a new import) so an old cache cannot ImportError.

## [2.0.2] - 2026-08-31

Patch release.

- Formal Rhino commands always retry copying Octane Lua into Documents before the per-session `_started` gate.
- Pass package `src_root` into sync; show a MessageBox when yak `templates` are missing (e.g. Script Editor / Git button instead of Package Manager toolbar).

## [2.0.1] - 2026-08-31

Patch release.

- Fix Octane `__Open_Shortcuts.lua` / `__Setup_Shortcuts.lua` when `debug.getinfo` has no `@…lua` path: fall back to `Documents\LoopFlow\Rhino to OctaneRender Sync\lua` and show a MessageBox instead of a silent flash-exit.

## [2.0.0] - 2026-08-31

First public 2.0 release (Rhino yak with Octane Lua). See GitHub Release notes for the full feature set.

## [1.0.0] - 2026-04-28

First public release.

### Rhino-Side Scripts
- **LiveLink_R2O_Models** — One-click USDZ export; preserves layer-based UUID for material continuity across syncs
- **LiveLink_R2O_Camera** — Toggle-based live camera sync; writes LUA data file on every rotation/zoom
- **LiveLink_R2O_Point** — Scans Points and Blocks; exports full transform matrix data for Octane Scatter nodes
- **LiveLink_R2O_Scatter** — Exports selected Blocks as individual USD files for use as Octane Scatter proxies
- **LiveLink_R2O_Open** — Quick open utility for config file, data folder, and debug log

### Octane-Side LUA Scripts — Sync
- **LiveLink_R2O_Camera.lua** — Reads camera LUA sync file and updates Thin Lens Camera node (`Ctrl+Q`)
- **LiveLink_R2O_Point.lua** — Reads Points sync file; creates or updates Scatter nodes in scene

### Octane-Side LUA Scripts — Utilities
- **Auto_PBR_Universal.lua** — Auto-builds Universal Material Nodegraph from a texture folder (`Ctrl+Shift+T`)
- **Auto_PBR_Switch_UV.lua** — Toggles UV projection mode between Box Projection and UV Transform (`Ctrl+T`)
- **Auto_Convert_StdSurf_to_Universal.lua** — Converts Standard Surface materials to Universal Material (`Shift+M`)
- **Auto_Align_Nodes.lua** — Aligns selected nodes to a horizontal baseline with configurable gap (`Alt+A`)

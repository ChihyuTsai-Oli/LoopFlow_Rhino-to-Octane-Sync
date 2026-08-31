# Changelog

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

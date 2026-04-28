# Changelog

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

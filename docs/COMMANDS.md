# LoopFlow R2O commands

> Do not mix old toolbars, packages, or Octane Lua in the same project.
>
> Workflow logic: [user guide](./USER_GUIDE.md). Command names are the Rhino command-line names (no spaces), for example `ROModels`.
>
> Rhino dialogs are English. Octane Lua files stay named `R2O_*.lua`.

## Project folder

Save the `.3dm` first. **That folder is the work folder.** Exchange files live in `_LoopFlow_Config/loopflow_R2O/` next to it. You can move the whole pack to another disk or computer without editing absolute paths.

## Quick index

| Stage | Rhino | Octane | In one line |
|---|---|---|---|
| Open | `ROOpen` | (none) | Config root, last-good times, folders, this documentation |
| Main model | `ROModels` | Load / quit-and-reopen `R2O.usdz` | Layer export of textured USDZ |
| Selection | `ROObjects` | Load stamped USDZ yourself | Current selection → stamped USDZ |
| Camera | `ROCamera` / `ROCameraPush` | `R2O_Camera.lua` (Ctrl+Q) | Active view → `live/camera.json`, apply once |
| Points | `ROPoint` | `R2O_Point.lua` | Points / Blocks on `R2O::` → `live/point.json` |
| Shading extras | (none) | Authoring Auto scripts | Align nodes, convert Universal, build PBR, switch UV |

Toolbar, four buttons, left / right click:

| Button | Left | Right |
|---|---|---|
| 1 | `ROOpen` | — |
| 2 | `ROModels` | `ROObjects` |
| 3 | `ROCamera` | `ROCameraPush` |
| 4 | `ROPoint` | — |

## Contents

[01 Open and docs](#01-open-and-docs) · [02 Main model](#02-main-model) · [03 Selected objects](#03-selected-objects) · [04 Camera](#04-camera) · [05 Points](#05-points) · [06 Octane Lua](#06-octane-lua) · [07 Authoring](#07-authoring) · [08 Do not](#08-do-not)

---

## 01 Open and docs

**Command:** `ROOpen`

Run after the file is saved. An English Health window appears, four equal-width buttons left to right:

- **Open Config** — `_LoopFlow_Config/loopflow_R2O/`
- **Open live** — camera / point JSON
- **Open models** — `R2O.usdz` and selection files
- **Open Docs** — this GitHub documentation entry

The summary lists the config-root path and last-good times for Camera / Point / Models / Objects. An unsaved file is blocked.

Octane has no matching Health panel yet.

---

## 02 Main model

**Command:** `ROModels`

Export the clean USDZ for Octane’s main sync (**with materials**).

1. The file must be saved.
2. Optional exclude mark (default `//`; empty = none). Layer paths that contain this text are skipped.
3. Pick layers to export (including children; the list scrolls).
4. Check geometry types. The same Rhino window remembers the last successful set. The first time, Point / Curve start unchecked.
5. On success, `models/R2O.usdz` is written. Failure does not replace the last good file. The source Rhino file is restored.

Hidden or locked objects are exported too. The source `.3dm` is **not** auto-saved.

Octane has **no** Models script. Load this `R2O.usdz` once and wire materials. Sockets = Rhino **material names**; the same name on different layers or objects is one socket. When you run `ROModels` again and overwrite the same file, **do not** Reload mesh / Load new mesh; **quit Octane and reopen**. Linked USDZ then follows. That is a Studio+ 2026.4 limit.

Renaming a Rhino material makes a new socket. Old wiring will not match.

---

## 03 Selected objects

**Command:** `ROObjects`

Export the **current selection** as a USDZ for Octane to load as a component.

- New file each time: `models/R2O_Objects_YYYYMMDD_HHMMSS.usdz`. Old files are kept.
- **Select first**; nothing selected is blocked.
- Not limited to Blocks; **origin is not moved**.

Keep asset Blocks under `USD::` (not `R2O::`) so point sync does not pick them up.

Octane has **no** Objects script. Load this new USDZ yourself. Do not Reload / Load new mesh.

Do not use `R2O.usdz` as a component file, and do not treat a stamped file as the main model you quit-and-reopen.

---

## 04 Camera

**Commands:** `ROCamera` (keep writing on/off), `ROCameraPush` (once)

- Uses the active perspective viewport; not perspective → stop
- File must be saved
- Writes `live/camera.json`
- Run `ROCamera` again to stop writing

Octane: run `R2O_Camera.lua` (default Ctrl+Q). **Applies the current file once and stops.** It does not keep following. The scene must have exactly one Thin Lens expanded from a Render Target. After you orbit in Rhino, press Ctrl+Q again.

---

## 05 Points

**Command:** `ROPoint`

Scans **Points and Blocks on `R2O::` child layers** (including nested, hidden, and locked). Do not put points on the parent `R2O` itself. Asset Blocks under `USD::` are not scanned.

**Rhino layers**

| Layer | Put | Synced? |
|---|---|---|
| `R2O` (root) | No Points / Blocks | No |
| `R2O::LT_Points::Downlight` | Points | Yes; type follows the full layer path |
| `R2O::FUR_Points::Sofa_A` | Blocks | Yes; includes transform |

Writes `live/point.json`.

Octane: run `R2O_Point.lua` (no default hotkey). **Applies once and stops.** Scatter appears at the **scene root**, prefix `R2O_Point_`, ready for Geometry. Wired proxies are not torn down. If you delete a type in Rhino and apply again, matching managed nodes are removed. Empty leftover `R2O_Point` groups can be deleted by hand.

Blocks meant for Scatter: place them correctly in world space first, then make the Block with the world origin as the insertion point.

---

## 06 Octane Lua

Lua is **not** one copy per project. After the first Rhino command, the default is `Documents\LoopFlow\Rhino to OctaneRender Sync\lua`. You can put the whole pack anywhere as long as Octane’s Script directory points there. The hotkey table `R2O_Shortcuts.txt` lives next to the scripts. That folder also has `Set_Octane_Script_Directory.txt` (English then Chinese). After a yak upgrade, this lua folder is emptied and refilled with the official files, including the hotkey table.

1. Octane: **File → Preferences → Directories and caching → Default locations → Script directory**, point at that folder.
2. Restart Octane. Scripts appear under **Script**.
3. To change keys, run `__Open_Shortcuts.lua` and edit the table.
4. Run `__Setup_Shortcuts.lua`, then rescan the script folder.

| Script | Hotkey | What it does |
|---|---|---|
| `R2O_Camera.lua` | Ctrl+Q | Apply camera once |
| `R2O_Point.lua` | (none) | Apply points once |
| `R2O_Open.lua` | — | Empty shell for now |

Main model and selected objects have **no** LiveLink scripts.

---

## 07 Authoring

Shading extras, separate from camera / point sync. Not on the Rhino toolbar. Same lua folder as LiveLink.

| Script | Hotkey | What it does |
|---|---|---|
| `Auto_Align_Nodes` | Alt+A | Align selected nodes and set spacing |
| `Auto_Convert_StdSurf_to_Universal` | Shift+M | Convert materials on selected USDZ nodes to Universal |
| `Auto_PBR_Universal` | Ctrl+Shift+T | Pick a PBR folder and build materials |
| `Auto_PBR_Switch_UV` | Ctrl+T | Switch UV mode inside those materials |

---

## 08 Do not

- Publish before saving
- Reload mesh / Load new mesh after a main-model update (quit and reopen instead)
- Cross `R2O.usdz` and stamped component files onto the other use
- Expect these Octane buttons inside a Blender workflow
- Rename the source `.3dm` or save the work file as an intermediate file just to sync

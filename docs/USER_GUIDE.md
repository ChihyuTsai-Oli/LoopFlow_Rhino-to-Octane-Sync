# LoopFlow R2O user guide

> Do not mix old toolbars, packages, or Octane Lua in the same project.
>
> This page is the one-minute picture. Buttons and steps are in the [command notes](./COMMANDS.md). Product overview and install are on the [homepage](../README.md).

## One way, separate channels

**Rhino writes. Octane reads.** Nothing is sent back to Rhino.

1. **Save the `.3dm` first.** Unpublished files cannot publish. Settings and exchange files sit next to that file. Paths are not hard-coded to one computer.
2. **Channels are independent.** Models, selected objects, camera, and points can run on their own. There is no required pipeline.
3. **Use matching pairs.** Rhino `ROModels` goes with loading / quit-and-reopen of `R2O.usdz`. `ROObjects` goes with loading a stamped USDZ yourself. Do not cross the files.

Model sync is meant so material sockets you already wired in Octane can stay. When a layer has a material, the socket follows that **Rhino material name**. When it does not, the socket is the full layer path.

## The project is a folder

The folder of the saved `.3dm` is the work folder. LoopFlow creates, next to it:

```text
_LoopFlow_Config/loopflow_R2O/
  live/      ← camera, points
  models/    ← R2O.usdz, stamped selection USDZ
```

Octane Lua is not per project. The default is `Documents\LoopFlow\Rhino to OctaneRender Sync\lua`. You can move the whole pack and point Octane’s Script directory at it. If the default folder is missing, any formal Rhino command copies it there again.

Move the whole project folder when you change computers.

## How the two sides meet

| You want | Rhino | Octane |
|---|---|---|
| Main model (with materials) | `ROModels` | Load `R2O.usdz` once; later overwrite → **quit and reopen** |
| Selection | `ROObjects` | Load the stamped USDZ yourself |
| Camera | `ROCamera` on/off; right-click `ROCameraPush` | Run `R2O_Camera.lua` (Ctrl+Q) once |
| Points (lights / furniture) | `ROPoint` | Run `R2O_Point.lua` once |
| Settings and docs | `ROOpen` | (no matching panel yet) |

The Rhino toolbar **LoopFlow R2O** has four buttons. Left-click hover names are **R2O Config**, **R2O Model** (the button face says **R2O Models**), **R2O Camera**, and **R2O Point**. Right-click hover names are **R2O Objects** and **R2O Camera Push**. Authoring is not on this toolbar.

Rhino 8 and Rhino 9 use the same package. On Rhino 9 the layer list shows only the top layer; the sublayers of that choice are still exported. `ROModels` then opens Detailed Mesh Settings. Cancel does not write a file. `ROObjects` does not open that mesh dialog.

## Terms

| Term | Meaning |
|---|---|
| **Work folder** | Folder of the saved `.3dm`. |
| **Quit and reopen** | After a main-model update, quit Octane and reopen so the linked USDZ catches up. Do not Reload mesh / Load new mesh. |
| **Material socket** | The **material name** in Rhino. Same name on different layers is still one socket. The USD prim is `material_` plus that name. A layer with no material uses its full layer path. Material and node names keep only letters, digits, and underscores; any other character becomes `_`. A `_2` suffix appears only when two names collapse to the same text. The first export that switches to this name needs the Octane wires connected once. |
| **Scatter** | Created inside the `R2O_Point` node graph after points apply; prefix `R2O_Point_`. Each apply, including a re-import, places them left to right by name. Auto-wired to `R2O_Point_Geometry`. Wire the graph’s geometry output into the scene. Light and furniture proxies stay on each Scatter input. |
| **Health** | Config-root path, plus last-good times for Camera / Point / Models / Objects. |

## Where it stops

- Unsaved file: publish stops, with an English message.
- Export cancelled, failed, or interrupted: you stay on the original work file. The last good output is not replaced by a half-written file.
- Camera: applies the camera connected to the only Render Target, whether that camera sits inside the node or is expanded. If the values do not stick, a dialog appears and other nodes are left unchanged.

The tool does not continue into the next channel by itself.

## How to press the buttons

This page is the logic. Command names, left/right-click, Octane scripts, and layers are in the [command notes](./COMMANDS.md).

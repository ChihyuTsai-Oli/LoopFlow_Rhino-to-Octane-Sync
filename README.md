# LoopFlow｜Rhino to Octane Sync

[繁體中文](./README_zh-TW.md)

> Do not mix old toolbars, packages, or Octane Lua in the same project.

Push Rhino models, cameras, and point positions one way into OctaneRender. You stay in control of every step; LoopFlow only writes what you ask for.

Rhino installs as a single `.yak`. The first product command copies the Octane Lua pack to `Documents\LoopFlow\Rhino to OctaneRender Sync\lua`.

[▶ Documentation](./docs/README.md) · [▶ Releases](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync/releases) · [▶ Tutorials](https://www.youtube.com/playlist?list=PLiJmu8T_uzJKBQ9LUzSmd7_OHV5fYjzII)

## Features

- **Model sync** — Export a clean USDZ from the working Rhino file. Load it once in Octane and wire materials; later updates are quit-and-reopen, not Reload mesh.
- **Selected objects** — Export the current selection as a stamped USDZ and load it yourself as a component.
- **Camera sync** — Write the active Rhino viewport; apply once in Octane.
- **Point alignment** — Points and Blocks on `R2O::` layers align Octane Scatter lights and furniture proxies.

Each channel is independent. Authoring scripts in Octane are extras and are not part of sync.

## System requirements

- **Rhino 8** (Windows)
- **OctaneRender Studio+ 2026.4** (development target)

Rhino dialogs are English. This page is English; a Traditional Chinese edition is linked above.

## Quick start

Not every tutorial video is updated yet.

### Installation

**Rhino**

1. Open Rhino 8 and run `PackageManager`.
2. Search for **`loopflow Rhino to OctaneRender Sync`** and install.
3. Or download `loopflow-rhino-to-octanerender-sync-2.0.2-rh8_0-win.yak` from [Releases](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync/releases) and install from file.
4. **Quit Rhino completely and reopen it.**
5. Use the **Rhino to OctaneRender Sync** toolbar. If it does not appear: **Tools → Options → Plug-ins**, enable **LoopFlow R2O**. If it still does not show, type `ROOpen` once.

The first product command copies the Lua pack to `Documents\LoopFlow\Rhino to OctaneRender Sync\lua`. After you install a new version, that command empties this lua folder and copies the official files from the package, including `R2O_Shortcuts.txt`. The same version does nothing. If you edited hotkeys, set them again after the upgrade.

**Octane**

1. Run any Rhino product command so Lua appears in `Documents\LoopFlow\Rhino to OctaneRender Sync\lua`.
2. That folder includes `Set_Octane_Script_Directory.txt` (English then Chinese).
3. **File → Preferences → Directories and caching → Default locations → Script directory**, point at that `lua` folder (or any full copy you moved; keep the pack together).
4. Restart Octane. Scripts appear under **Script**.
5. Run `__Setup_Shortcuts.lua`, then rescan the script folder.

Full command notes: [documentation](./docs/README.md).

## Basic workflow

1. Save the `.3dm` (unpublished files cannot publish).
2. Run `ROOpen` to check the config folder and last-good times.
3. For models, run `ROModels` (with materials) or `ROObjects` (selection).
4. For camera or points, write from Rhino, then run the matching Lua once in Octane.
5. After overwriting the same `R2O.usdz`: quit Octane and reopen. Do not Reload / Load new mesh.

Every step is started by you. If one channel fails, rerun that channel. You do not have to rebuild the whole scene.

## Support

- [Discussions](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync/discussions)
- [Issues](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync/issues)
- [Releases](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync/releases)

LoopFlow is a solo project by an architect and interior designer. AI assists with code and documentation; workflow, design decisions, and production checks stay with the author.

Response times vary with project workload.

## Related projects

- [LoopFlow｜Half-automatic 2D/3D Sync](https://github.com/ChihyuTsai-Oli/LoopFlow)
- [LoopFlow｜Rhino to Blender Sync](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Blender-Sync)

## License and credits

Released under the [MIT License](./LICENSE). See [CREDITS](./CREDITS.md).

# LoopFlow Rhino-to-Octane Sync — Releases

[▶ Watch on YouTube](https://www.youtube.com/@LoopFlow) · [🏠 Project Page](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync)

---

## Installation

**Rhino Side**

1. Download the latest release ZIP from [Releases](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync/releases)
2. Navigate into the `LoopFlow_Rhino-to-Octane-Sync/` folder
3. Run `install_LoopFlow_R2O.bat` to automatically install the Rhino scripts and LUA scripts
4. Drag `LoopFlow_R2O.rhc` into the Rhino viewport — the toolbar will appear

**Octane Side**

5. In OctaneRender, set the LUA scripts folder to:
   `%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Lua`
6. Rescan scripts to register hotkeys

> On reinstall, the existing `R2O_Shortcuts.txt` hotkey config is preserved.
> The new template is saved as `R2O_Shortcuts_YYYYMMDD.txt` in the same folder for comparison.

---

## Included Files

| File / Folder | Description |
|---|---|
| `LoopFlow_Rhino-to-Octane-Sync/Python/` | Rhino-side Python scripts |
| `LoopFlow_Rhino-to-Octane-Sync/LUA/` | Octane-side LUA scripts and hotkey management tools |
| `LoopFlow_Rhino-to-Octane-Sync/Data/` | Hotkey config template (`R2O_Shortcuts.txt`) |
| `LoopFlow_Rhino-to-Octane-Sync/install_LoopFlow_R2O.bat` | Auto-installer |
| `LoopFlow_Rhino-to-Octane-Sync/LoopFlow_R2O.rhc` | Rhino toolbar definition |

---

## Folder Structure

```
releases/
  LoopFlow_Rhino-to-Octane-Sync/
    Python/                    ← Rhino-side Python scripts
    LUA/                       ← Octane-side LUA scripts
    Data/
      R2O_Shortcuts.txt        ← Hotkey config template (preserved on reinstall)
    install_LoopFlow_R2O.bat
    LoopFlow_R2O.rhc
  README.md
  README_zh-TW.md
```

---

## Credits

- Developed with [Cursor](https://cursor.sh) + Claude Sonnet 4.6

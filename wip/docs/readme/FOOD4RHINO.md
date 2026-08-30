# Food4Rhino listing（已送審，待審核通過後再補頁面網址）

LoopFlow Rhino to OctaneRender Sync pushes models, cameras, and point positions one way from Rhino 8 into OctaneRender. It exports a clean USDZ, writes the view and point positions, and applies them on the Octane side.

Typical flow: model in Rhino as you already do, then publish the model, a selection, the camera, or points when you need them. Load the main model once in Octane and wire materials. After that, overwrite the same USDZ, quit Octane, and reopen — do not Reload mesh. Material sockets follow Rhino material names. Each channel is independent; you do not have to run them all at once.

The aim is to keep Rhino's design freedom, while cutting the repeat work of rebuilding the render scene after every model change.

Install from Rhino's Package Manager (search **loopflow Rhino to OctaneRender Sync**). Point Octane's Script directory at the lua folder the package copies into Documents\LoopFlow (keep the pack together).

Do not mix old 1.x toolbars, packages, or Octane Lua with this version in the same project.

Requirements: Rhino 8 (Windows 10/11), OctaneRender Studio+ 2026.4 (development target). UI: English. Documentation: English / Traditional Chinese.

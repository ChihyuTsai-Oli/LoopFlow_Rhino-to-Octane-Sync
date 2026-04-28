# LoopFlow｜Rhino to Octane Sync

[▶ How it works（YouTube）](https://www.youtube.com/playlist?list=PLiJmu8T_uzJKBQ9LUzSmd7_OHV5fYjzII) · [▶ Releases](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Octane-Sync/releases) · [▶ User Guide](./docs/USER_GUIDE.md)

## Key Features

- **Model Sync** — One-click USDZ export; replace geometry in Octane while preserving all materials
- **Camera Sync** — Mirrors the active Rhino viewport to Octane's camera
- **Light Alignment** — Rhino Points sync; lights and fixtures auto-align to point positions in Octane
- **Furniture Proxy** — Rhino Blocks via Proxy; furniture and objects auto-align to Block positions in Octane

## How Material Sync Works

The core feature is model sync — no matter how many times you sync, materials stay connected. The USDZ format assigns a UUID to each Rhino layer, tied to the layer name. As long as the layer name doesn't change, the UUID stays the same, which keeps all material assignments intact across syncs.

## Modular by Design

Every sync function is independent. Use model sync only, light sync only, or any combination — there's no fixed sequence. Pick what you need, skip what you don't.

## Why OctaneRender Standalone?

Octane is an unbiased, physically based render engine with exceptional lighting quality — in my opinion, the best in class for that. The sync workflow described above compensates for its native scene management limitations, turning it into an extremely powerful tool.

## Installation

See **[releases/README.md](releases/README.md)** for step-by-step setup instructions.

## You Might Also Like

- [LoopFlow｜Half-automatic 2D/3D Sync](https://github.com/ChihyuTsai-Oli/LoopFlow)
- [LoopFlow｜Rhino to Blender Sync](https://github.com/ChihyuTsai-Oli/LoopFlow_Rhino-to-Blender-Sync)

## Credits

- Thank you, token-burning warrior.

---

*Last updated: April 2026*
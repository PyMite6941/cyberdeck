# DFCD part sizing reference

Measured 2026-06-11 with headless FreeCAD 1.1.1 (`os/image/measure_parts.py`,
bounding boxes of the upstream STEP assemblies, all values in mm).

| Module | Width (X) | Depth (Y) | Height (Z) | Solids |
|---|---|---|---|---|
| Central unit (chassis + sliding screen + keyboard bay) | 334.8 | 80.6 | 226.8 | 87 |
| Battery module (right side) | 90.5 | 64.7 | 100.6 | 44 |
| Trackball module (right side) | 101.1 | 67.7 | 157.0 | 44 |
| Scroll module (left side) | 107.9 | 58.3 | 188.7 | 46 |
| External connector module (left side) | 114.2 | 82.5 | 76.5 | 41 |
| Dragchain segment (each) | 26.9 | 21.4 | 8.5 | 1 |

## What the numbers mean for part selection

- **Full deployed footprint** ≈ **545 mm wide** (335 central + ~108 + ~101 side
  modules) × ~81 mm deep × ~227 mm tall. It's a chunky shoulder-strap device,
  not a laptop.
- **Screen bay**: the 335 mm-wide central unit is built around a **10.1″ panel**
  (active area ~217 × 136 mm, outer ~229 × 149 mm). A bigger panel will not fit;
  a smaller one leaves visible gaps in the printed frame.
- **Keyboard bay**: hides under the sliding screen inside the central unit —
  usable width is ~315 mm. A **60–65% / "mini" mechanical board** (~293–310 mm,
  like the NOS C-450 Mini) fits; a TKL (~360 mm) does **not**.
- **Battery module** (91 × 65 × 101 mm) is moulded around the **Sony NP-F
  format** (NP-F970: 70.8 × 38.4 × 58.9 mm + contact plate + release). Other
  battery types need a redesigned module.
- **Trackball module** (101 × 68 × 157 mm) is dimensioned for the **Logitech
  Trackman Marble** PCB and its 40 mm ball — that's why the BOM says to harvest
  one.
- **Pi bay**: the central unit hosts a full-size Pi (85 × 56 mm) plus the Joy-IT
  power board stacked — both **Pi 4B and Pi 5 share the same 85 × 56 footprint
  and mounting holes (58 × 49 mm)**, so either fits physically; only rear port
  cutouts differ (Pi 4: 2×micro-HDMI order and USB/Ethernet swapped vs Pi 5).
- **Printability**: the largest single pieces (lower chassis halves, screen
  frame halves) are **~215 mm on their longest edge** (measured: 162×215,
  140×215, 170×215 mm footprints). They fit a **220 × 220 mm bed** (Ender-class)
  but with only **~5 mm margin** — so a ≥220 mm bed is required and 250 mm
  (Bambu/Prusa-XL class) is comfortable. Everything else is well under.
- **Mesh notes**: a FreeCAD print-readiness sweep (`os/image/print_check.py`)
  flags ~15 `.3mf` files as non-manifold / self-intersecting. These are
  tessellation artifacts from the solid→mesh export, not design defects (the
  upstream deck was physically built and printed) — every common slicer
  auto-repairs them on load. Regenerate clean meshes from the STEP sources only
  if you want pristine files; not required to print.
- **Dragchain**: each link is 26.9 × 21.4 × 8.5 mm; the chain carries USB
  between modules across the screen slide — print ~10–14 segments + 2 ends.

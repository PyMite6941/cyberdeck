#!/usr/bin/env python3
"""Parametric 3D-printed bracket for a GT-521F32 / R307 fingerprint scanner.

Generates a STEP file you can open in FreeCAD to adjust before printing.

Usage:
    python make_fingerprint_mount.py         # default: GT-521F32
    python make_fingerprint_mount.py --r307  # R307/R503 variant

The mount holds the scanner sensor face flush with the deck body, with M2 screw
bosses for the scanner PCB and optional M3 bosses for mounting to the deck.

Output: hardware-custom/Biometrics/<variant>.step
"""

import argparse, os, sys

OS = sys.platform

# Try to import FreeCAD — if absent, print the design and exit.
try:
    import FreeCAD as App
    import Part
except ImportError:
    print("FreeCAD not available — run this script on a machine with FreeCAD installed.")
    print("Design parameters (edit and run on the Pi or your CAD machine):")
    print()
    SCANNERS = {
        "gt521f32": {"width": 20.0, "depth": 25.0, "height": 8.0, "pcb_w": 16.0, "pcb_d": 20.0,
                      "sensor_x": 10.0, "sensor_y": 12.0, "mount_holes": [(3.5, 3.5), (16.5, 3.5), (3.5, 21.5), (16.5, 21.5)]},
        "r307":     {"width": 22.0, "depth": 24.0, "height": 7.5, "pcb_w": 18.0, "pcb_d": 19.0,
                      "sensor_x": 11.0, "sensor_y": 11.5, "mount_holes": [(3.0, 3.0), (19.0, 3.0), (3.0, 21.0), (19.0, 21.0)]},
    }
    scanner = SCANNERS.get("gt521f32", SCANNERS["gt521f32"])
    print(f"  Scanner: {scanner['width']}×{scanner['depth']}×{scanner['height']} mm")
    print(f"  PCB:     {scanner['pcb_w']}×{scanner['pcb_d']} mm")
    print(f"  Sensor window: {scanner['sensor_x']}×{scanner['sensor_y']} mm (centered)")
    sys.exit(0)


SCANNER_PARAMS = {
    "gt521f32": {
        "label": "GT-521F32",
        "body_w": 20.0,   # scanner body width
        "body_d": 25.0,   # scanner body depth
        "body_h": 8.0,    # scanner body height (above PCB)
        "pcb_w": 16.0,    # PCB width
        "pcb_d": 20.0,    # PCB depth
        "pcb_h": 1.6,     # PCB thickness
        "sensor_x": 10.0, # sensor window X
        "sensor_y": 12.0, # sensor window Y
        "mount_holes": [(3.5, 3.5), (16.5, 3.5), (3.5, 21.5), (16.5, 21.5)],
        "hole_dia": 2.2,  # M2 screw
    },
    "r307": {
        "label": "R307 / R503",
        "body_w": 22.0,
        "body_d": 24.0,
        "body_h": 7.5,
        "pcb_w": 18.0,
        "pcb_d": 19.0,
        "pcb_h": 1.6,
        "sensor_x": 11.0,
        "sensor_y": 11.5,
        "mount_holes": [(3.0, 3.0), (19.0, 3.0), (3.0, 21.0), (19.0, 21.0)],
        "hole_dia": 2.2,
    },
}


def make_bracket(params):
    """Build the bracket as a FreeCAD Compound."""
    body_w = params["body_w"]
    body_d = params["body_d"]
    body_h = params["body_h"]
    pcb_w = params["pcb_w"]
    pcb_d = params["pcb_d"]
    pcb_h = params["pcb_h"]
    sensor_x = params["sensor_x"]
    sensor_y = params["sensor_y"]
    mount_holes = params["mount_holes"]
    hole_dia = params["hole_dia"]

    # Total bracket size: scanner body + 2mm wall on each side
    wall = 2.0
    bracket_w = body_w + 2 * wall
    bracket_d = body_d + 2 * wall
    bracket_h = body_h + pcb_h + 3.0  # body + PCB + floor

    # Base plate
    base = Part.makeBox(bracket_w, bracket_d, bracket_h)

    # Cutout for scanner body (centered)
    cx = bracket_w / 2
    cy = bracket_d / 2
    cutout = Part.makeBox(body_w, body_d, body_h + 1,
                          App.Vector(cx - body_w / 2, cy - body_d / 2, bracket_h - body_h - 1))

    # Sensor window at the top
    window = Part.makeBox(sensor_x, sensor_y, bracket_h + 1,
                          App.Vector(cx - sensor_x / 2, cy - sensor_y / 2, bracket_h - body_h - 0.5))

    # PCB screw holes (M2, through the floor)
    floor_thick = 2.0
    for hx, hy in mount_holes:
        # Offset holes relative to the scanner body position
        ox = cx - body_w / 2 + hx
        oy = cy - body_d / 2 + hy
        hole = Part.makeCylinder(hole_dia / 2, bracket_h,
                                 App.Vector(ox, oy, 0))
        base = base.cut(hole)

    # M3 mounting holes to the deck (corners of the bracket)
    margin = 3.0
    deck_mount_holes = [
        (margin, margin),
        (bracket_w - margin, margin),
        (margin, bracket_d - margin),
        (bracket_w - margin, bracket_d - margin),
    ]
    for dx, dy in deck_mount_holes:
        deck_hole = Part.makeCylinder(1.5, bracket_h, App.Vector(dx, dy, 0))
        base = base.cut(deck_hole)

    # USB cable exit notch (rear, bottom edge)
    notch_w = 6.0
    notch_h = 2.5
    notch = Part.makeBox(notch_w, notch_h, bracket_h + 1,
                         App.Vector(cx - notch_w / 2, bracket_d - notch_h - 0.1, -0.1))
    base = base.cut(notch)

    # Subtract scanner cavity and window
    base = base.cut(cutout)
    base = base.cut(window)

    # Round corners (optional — keep square for printability)
    # Add fillet around edges
    try:
        edges = []
        for e in base.Edges:
            if e.Length > bracket_w - 0.1 or e.Length > bracket_d - 0.1:
                edges.append(e)
        base = base.makeFillet(1.0, edges)
    except Exception:
        pass  # fillet is optional

    return base


def main():
    parser = argparse.ArgumentParser(description="Generate fingerprint scanner mount")
    parser.add_argument("--scanner", choices=list(SCANNER_PARAMS.keys()), default="gt521f32",
                        help="Scanner model (default: gt521f32)")
    parser.add_argument("--output", help="Output STEP file path")
    args = parser.parse_args()

    params = SCANNER_PARAMS[args.scanner]
    label = params["label"]

    out_dir = os.path.dirname(os.path.abspath(__file__))
    if args.output:
        out_path = args.output
    else:
        safe_name = args.scanner.replace("/", "_").replace(" ", "_")
        out_path = os.path.join(out_dir, f"fingerprint_mount_{safe_name}.step")

    doc = App.newDocument("FingerprintMount")
    bracket = make_bracket(params)
    obj = doc.addObject("Part::Feature", "Bracket")
    obj.Shape = bracket
    doc.recompute()

    Part.export([obj], out_path)
    print(f"Exported {label} mount: {out_path}")
    print(f"  Dimensions: {20+4:.1f}×{25+4:.1f}×{8+1.6+3:.1f} mm (approx)")


if __name__ == "__main__":
    main()

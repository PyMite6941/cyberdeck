# Cut a 3mm status-LED hole into the right screen frame, in a solid gap within
# the front button column (the "by the buttons" spot). Tests several candidate
# positions, picks the one that removes real material, validates, exports.
# Run: FreeCADCmd.exe make_led_button.py  (use short 8.3 path if in Unicode dir)
import os
import Mesh
import Part
from FreeCAD import Vector

FRONT_Y = 33.1
LED_D = 3.0
CB_D = 4.5
CB_DEPTH = 1.0
MIN_REMOVED = 40.0   # mm3 — below this the spot isn't solid front wall

# candidates (X, Z, label) — gaps between the stacked controls, then fallbacks
CANDS = [
    (275.5, 38.5,  "between top button & switch"),
    (275.5, 1.4,   "between middle & top button"),
    (275.5, -35.6, "between bottom & middle button"),
    (258.0, -17.0, "left of the column"),
    (275.5, -78.0, "below the bottom button"),
]

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRAME = os.path.join(BASE, "hardware", "DFCD mesh files", "Central unit",
                     "Screen", "Screen frame", "Rigth screen frame.3mf")
OUTDIR = os.path.join(BASE, "hardware-custom", "Screen frame")

m = Mesh.Mesh(); m.read(FRAME)
shape = Part.Shape(); shape.makeShapeFromMesh(m.Topology, 0.1)
solid = Part.makeSolid(shape)
v0 = solid.Volume

best = None
for (x, z, label) in CANDS:
    probe = Part.makeCylinder(LED_D / 2.0, 16, Vector(x, FRONT_Y + 0.5, z), Vector(0, -1, 0))
    removed = v0 - solid.cut(probe).Volume
    print("  probe %-32s X=%.1f Z=%.1f -> removed %.1f mm3" % (label, x, z, removed))
    if removed >= MIN_REMOVED and best is None:
        best = (x, z, label)

if best is None:
    print("NO SOLID SPOT FOUND in candidates — widen the search.")
else:
    x, z, label = best
    print("CHOSEN: %s (X=%.1f Z=%.1f)" % (label, x, z))
    hole = Part.makeCylinder(LED_D / 2.0, 16, Vector(x, FRONT_Y + 0.5, z), Vector(0, -1, 0))
    cbore = Part.makeCylinder(CB_D / 2.0, CB_DEPTH + 0.5, Vector(x, FRONT_Y + 0.5, z), Vector(0, -1, 0))
    result = solid.cut(hole).cut(cbore)
    print("result valid=%s closed=%s removed=%.1f mm3"
          % (result.isValid(), (result.Solids and result.Solids[0].isClosed()), v0 - result.Volume))
    if not os.path.isdir(OUTDIR):
        os.makedirs(OUTDIR)
    result.exportStep(os.path.join(OUTDIR, "Right screen frame with LED.step"))
    out = Mesh.Mesh(); out.addFacets(result.tessellate(0.05))
    out.write(os.path.join(OUTDIR, "Right screen frame with LED.3mf"))
    out.write(os.path.join(OUTDIR, "Right screen frame with LED.stl"))
    print("EXPORTED to %s" % OUTDIR)
print("LED_DONE")

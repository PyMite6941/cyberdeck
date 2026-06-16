# Generate "GFPIO lid raised 12mm" — splits the stock lid at its constant
# wall cross-section, inserts a 12mm extruded spacer band, fuses, exports to
# hardware-custom/. Gives headroom over the GPIO header (RTC module, cables).
# Run: FreeCADCmd.exe make_raised_lid.py  (8.3 path)
import os
import Mesh
import Part
from FreeCAD import Vector

RAISE = 12.0
BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "hardware")
LID = os.path.join(BASE, "DFCD mesh files", "Central unit", "Screen",
                   "Screen frame", "GFPIO lid.3mf")
OUTDIR = os.path.join(os.path.dirname(BASE), "hardware-custom", "Screen frame")

m = Mesh.Mesh()
m.read(LID)
shape = Part.Shape()
shape.makeShapeFromMesh(m.Topology, 0.1)
solid = Part.makeSolid(shape)
bb = solid.BoundBox

# The lid is a cap: one Y side is the closed face, the other the open rim.
# Slice near both Y extremes; the rim side yields 2+ wires (wall ring).
def wires_at(y):
    try:
        return solid.slice(Vector(0, 1, 0), y)
    except Exception:
        return []

lo_w = wires_at(bb.YMin + 1.0)
hi_w = wires_at(bb.YMax - 1.0)
print("wires near YMin: %d, near YMax: %d" % (len(lo_w), len(hi_w)))
rim_is_low = len(lo_w) >= len(hi_w)
ycut = (bb.YMin + 2.0) if rim_is_low else (bb.YMax - 2.0)
wires = wires_at(ycut)
print("cut at y=%.2f (rim %s), wires=%d" % (ycut, "low" if rim_is_low else "high", len(wires)))

# Face of the wall cross-section (outer wire minus holes).
wires = sorted(wires, key=lambda w: -Part.Face(w).Area)
face = Part.Face(wires[0])
for w in wires[1:]:
    face = face.cut(Part.Face(w))
print("section area: %.1f mm2" % face.Area)
face.translate(Vector(0, ycut - face.BoundBox.YMin, 0))

# Split solid, shift the rim-side away from the cap by RAISE, bridge with band.
big = Part.makeBox(bb.XLength + 20, bb.YLength + 40, bb.ZLength + 20)
if rim_is_low:
    big.translate(Vector(bb.XMin - 10, ycut - (bb.YLength + 40), bb.ZMin - 10))
    rim_half = solid.common(big)
    cap_half = solid.cut(big)
    band = face.extrude(Vector(0, -RAISE, 0))
    rim_half.translate(Vector(0, -RAISE, 0))
else:
    big.translate(Vector(bb.XMin - 10, ycut, bb.ZMin - 10))
    rim_half = solid.common(big)
    cap_half = solid.cut(big)
    band = face.extrude(Vector(0, RAISE, 0))
    rim_half.translate(Vector(0, RAISE, 0))

raised = cap_half.fuse(band).fuse(rim_half).removeSplitter()
rb = raised.BoundBox
print("raised lid: %.1f x %.1f x %.1f (was %.1f x %.1f x %.1f)"
      % (rb.XLength, rb.YLength, rb.ZLength, bb.XLength, bb.YLength, bb.ZLength))

if not os.path.isdir(OUTDIR):
    os.makedirs(OUTDIR)
raised.exportStep(os.path.join(OUTDIR, "GFPIO lid raised 12mm.step"))
out_mesh = Mesh.Mesh()
out_mesh.addFacets(raised.tessellate(0.05))
out_mesh.write(os.path.join(OUTDIR, "GFPIO lid raised 12mm.3mf"))
out_mesh.write(os.path.join(OUTDIR, "GFPIO lid raised 12mm.stl"))
print("EXPORT_OK %s" % OUTDIR)

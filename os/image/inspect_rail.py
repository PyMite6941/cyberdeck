# Extract the picatinny rail cross-section so the comms-module clamp foot can be
# designed to match the deck's actual printed rail.
# Run: FreeCADCmd.exe inspect_rail.py  (via the 8.3 OneDrive path)
import os
import Mesh
import Part
from FreeCAD import Vector

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAIL = os.path.join(BASE, "hardware", "DFCD mesh files", "Central unit",
                    "Chassis", "picatinny rails", "picatinny rail.3mf")

m = Mesh.Mesh(); m.read(RAIL)
bb = m.BoundBox
print("bbox X=%.2f Y=%.2f Z=%.2f" % (bb.XLength, bb.YLength, bb.ZLength))
print("X[%.2f,%.2f] Y[%.2f,%.2f] Z[%.2f,%.2f]"
      % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))

sh = Part.Shape(); sh.makeShapeFromMesh(m.Topology, 0.05)
dims = {'X': bb.XLength, 'Y': bb.YLength, 'Z': bb.ZLength}
longax = max(dims, key=dims.get)
nrm = {'X': Vector(1, 0, 0), 'Y': Vector(0, 1, 0), 'Z': Vector(0, 0, 1)}[longax]
mid = {'X': (bb.XMin + bb.XMax) / 2, 'Y': (bb.YMin + bb.YMax) / 2,
       'Z': (bb.ZMin + bb.ZMax) / 2}[longax]
print("long axis: %s  (slice at %.2f)" % (longax, mid))

wires = sh.slice(nrm, mid)
print("cross-section wires: %d" % len(wires))
axes = [a for a in 'XYZ' if a != longax]
if wires:
    face = sorted(wires, key=lambda w: -Part.Face(w).Area)[0]
    f = Part.Face(face)
    fb = f.BoundBox
    w0 = getattr(fb, axes[0] + 'Length'); w1 = getattr(fb, axes[1] + 'Length')
    print("section: %s=%.2f mm  %s=%.2f mm  area=%.1f mm2" % (axes[0], w0, axes[1], w1, f.Area))
    # sample width along the taller axis to capture the trapezoid taller->base
    tall = axes[0] if w0 >= w1 else axes[1]
    wide = axes[1] if tall == axes[0] else axes[0]
    lo = getattr(fb, tall + 'Min'); hi = getattr(fb, tall + 'Max')
    print("profile (%s height -> %s width):" % (tall, wide))
    for frac in (0.1, 0.3, 0.5, 0.7, 0.9):
        h = lo + (hi - lo) * frac
        ln = sh.slice({'X': Vector(1,0,0),'Y': Vector(0,1,0),'Z': Vector(0,0,1)}[tall], h)
        wmax = 0.0
        for e in ln:
            eb = e.BoundBox
            wmax = max(wmax, getattr(eb, wide + 'Length'))
        print("  h=%.2f  width=%.2f" % (h, wmax))
print("RAIL_DONE")

# Inspect the button body (Body2) to place a status-LED hole beside the buttons.
# Reports orientation, solid validity, a test cut, and the existing hole/feature
# centres (via a mid-thickness slice) so we can pick a free spot.
# Run: FreeCADCmd.exe inspect_buttonbody.py  (8.3 path)
import os
import Mesh
import Part
from FreeCAD import Vector

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BODY = os.path.join(BASE, "hardware", "DFCD mesh files", "Central unit",
                    "Screen", "Buttons", "Body2.3mf")

m = Mesh.Mesh(); m.read(BODY)
bb = m.BoundBox
print("bbox X=%.1f Y=%.1f Z=%.1f" % (bb.XLength, bb.YLength, bb.ZLength))
print("X[%.1f,%.1f] Y[%.1f,%.1f] Z[%.1f,%.1f]"
      % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
print("facets=%d solidMesh=%s" % (m.CountFacets, m.isSolid()))

shape = Part.Shape(); shape.makeShapeFromMesh(m.Topology, 0.1)
solid = Part.makeSolid(shape)
print("solid: valid=%s closed=%s volume=%.0f"
      % (solid.isValid(), (solid.Solids and solid.Solids[0].isClosed()), solid.Volume))

dims = {'X': bb.XLength, 'Y': bb.YLength, 'Z': bb.ZLength}
thin = min(dims, key=dims.get)
nrm = {'X': Vector(1, 0, 0), 'Y': Vector(0, 1, 0), 'Z': Vector(0, 0, 1)}[thin]
lo = {'X': bb.XMin, 'Y': bb.YMin, 'Z': bb.ZMin}[thin]
hi = {'X': bb.XMax, 'Y': bb.YMax, 'Z': bb.ZMax}[thin]
mid = (lo + hi) / 2.0
print("thin axis=%s (thickness %.1f) — slicing at mid to map holes" % (thin, hi - lo))

ax = [a for a in 'XYZ' if a != thin]
wires = solid.slice(nrm, mid)
print("slice wires: %d  (1 outline + N holes)" % len(wires))
faces = sorted(wires, key=lambda w: -Part.Face(w).Area)
for i, w in enumerate(faces):
    c = w.BoundBox.Center
    wb = w.BoundBox
    tag = "OUTLINE" if i == 0 else "hole"
    print("  %-7s %s=%.1f %s=%.1f  size %.1fx%.1f"
          % (tag, ax[0], getattr(c, ax[0]), ax[1], getattr(c, ax[1]),
             getattr(wb, ax[0] + 'Length'), getattr(wb, ax[1] + 'Length')))

# confirm a boolean cut works on this mesh
drill = Part.makeCylinder(1.6, dims[thin] + 4, Vector(
    bb.XMin - 2 if thin == 'X' else bb.Center.x,
    bb.YMin - 2 if thin == 'Y' else bb.Center.y,
    bb.ZMin - 2 if thin == 'Z' else bb.Center.z), nrm)
try:
    print("TEST-CUT valid=%s" % solid.cut(drill).isValid())
    print("BOOLEAN_OK")
except Exception as e:
    print("TEST-CUT FAILED: %s" % e)
    print("BOOLEAN_BAD")
print("BUTTONBODY_DONE")

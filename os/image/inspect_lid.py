# Inspect the GFPIO lid mesh: bounding box + cross-section wire counts near
# both Z extremes, to find the mating-rim plane for a riser collar.
# Run: FreeCADCmd.exe inspect_lid.py  (8.3 path)
import os
import Mesh
import Part

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "hardware")
LID = os.path.join(BASE, "DFCD mesh files", "Central unit", "Screen", "Screen frame", "GFPIO lid.3mf")

m = Mesh.Mesh()
m.read(LID)
bb = m.BoundBox
print("lid bbox: X=%.1f Y=%.1f Z=%.1f  (Z range %.1f..%.1f)"
      % (bb.XLength, bb.YLength, bb.ZLength, bb.ZMin, bb.ZMax))
print("facets=%d volume=%.1fcm3 solid=%s" % (m.CountFacets, m.Volume / 1000.0, m.isSolid()))

shape = Part.Shape()
shape.makeShapeFromMesh(m.Topology, 0.1)
print("shape faces=%d" % len(shape.Faces))

from FreeCAD import Vector
for label, z in (("near-bottom", bb.ZMin + 0.6), ("near-top", bb.ZMax - 0.6),
                 ("mid", (bb.ZMin + bb.ZMax) / 2.0)):
    try:
        wires = shape.slice(Vector(0, 0, 1), z)
        info = []
        for w in wires:
            wb = w.BoundBox
            info.append("%.1fx%.1f%s" % (wb.XLength, wb.YLength,
                                         "C" if w.isClosed() else "o"))
        print("slice %s z=%.1f: %d wires [%s]" % (label, z, len(wires), ", ".join(info)))
    except Exception as e:
        print("slice %s failed: %s" % (label, e))
print("INSPECT_DONE")

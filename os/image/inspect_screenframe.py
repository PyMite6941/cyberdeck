# Inspect the screen frame to (a) understand its orientation and (b) test
# whether its mesh can be boolean-cut cleanly for a 3mm status-LED hole.
# Run: FreeCADCmd.exe inspect_screenframe.py  (8.3 path)
import os
import Mesh
import Part
from FreeCAD import Vector

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRAME = os.path.join(BASE, "hardware", "DFCD mesh files", "Central unit",
                     "Screen", "Screen frame", "Rigth screen frame.3mf")

m = Mesh.Mesh(); m.read(FRAME)
bb = m.BoundBox
print("bbox X=%.1f Y=%.1f Z=%.1f" % (bb.XLength, bb.YLength, bb.ZLength))
print("X[%.1f,%.1f] Y[%.1f,%.1f] Z[%.1f,%.1f]"
      % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
print("facets=%d solidMesh=%s" % (m.CountFacets, m.isSolid()))

# Try to make a solid we can boolean.
shape = Part.Shape(); shape.makeShapeFromMesh(m.Topology, 0.1)
try:
    solid = Part.makeSolid(shape)
    print("solid: valid=%s closed=%s volume=%.0f"
          % (solid.isValid(), (solid.Solids and solid.Solids[0].isClosed()), solid.Volume))
except Exception as e:
    solid = None
    print("makeSolid FAILED: %s" % e)

# Test a boolean cut (3mm hole) into the thin (X) face at mid Y/Z, to see if
# the mesh booleans cleanly. We cut along +X through the frame thickness.
if solid is not None:
    ymid = (bb.YMin + bb.YMax) / 2.0
    zmid = (bb.ZMin + bb.ZMax) / 2.0
    drill = Part.makeCylinder(1.5, bb.XLength + 4,
                              Vector(bb.XMin - 2, ymid, zmid), Vector(1, 0, 0))
    try:
        cut = solid.cut(drill)
        ok = cut.isValid()
        print("TEST-CUT: valid=%s solids=%d" % (ok, len(cut.Solids)))
        print("BOOLEAN_OK" if ok else "BOOLEAN_BAD")
    except Exception as e:
        print("TEST-CUT FAILED: %s" % e)
        print("BOOLEAN_BAD")
print("FRAME_DONE")

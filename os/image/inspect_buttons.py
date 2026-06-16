# Map the full button-cluster envelope (all big buttons + retainers) in assembly
# coords, so the status LED can be placed in a verified-free spot beside them.
# Run: FreeCADCmd.exe inspect_buttons.py  (8.3 path)
import os
import Mesh

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BDIR = os.path.join(BASE, "hardware", "DFCD mesh files", "Central unit",
                    "Screen", "Buttons")

parts = ["big b 1.3mf", "big b 2.3mf", "big b 3.3mf", "Body2.3mf",
         "Lower button retainer left.3mf", "Lower button retainer rigth.3mf",
         "Rigth button retainer.3mf", "Switch.3mf"]

ux0 = uy0 = uz0 = 1e9
ux1 = uy1 = uz1 = -1e9
for p in parts:
    path = os.path.join(BDIR, p)
    if not os.path.isfile(path):
        print("missing: %s" % p); continue
    m = Mesh.Mesh(); m.read(path)
    bb = m.BoundBox
    print("%-32s X[%.1f,%.1f] Y[%.1f,%.1f] Z[%.1f,%.1f]"
          % (p, bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
    ux0, uy0, uz0 = min(ux0, bb.XMin), min(uy0, bb.YMin), min(uz0, bb.ZMin)
    ux1, uy1, uz1 = max(ux1, bb.XMax), max(uy1, bb.YMax), max(uz1, bb.ZMax)

print("CLUSTER ENVELOPE X[%.1f,%.1f] Y[%.1f,%.1f] Z[%.1f,%.1f]"
      % (ux0, ux1, uy0, uy1, uz0, uz1))
print("  -> free to the RIGHT of cluster: X > %.1f" % ux1)
print("  -> free BELOW cluster: Z < %.1f" % uz0)
print("  -> front face Y ~ %.1f" % uy1)
print("BUTTONS_DONE")

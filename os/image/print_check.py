# Print-readiness sweep of all DFCD print files + our generated custom parts.
# Run: FreeCADCmd.exe print_check.py   (via the 8.3 OneDrive path)
# Per file: bounding box (bed fit), facet count, solid?, non-manifold?
# Flags: NOT-SOLID, NON-MANIFOLD, BED (won't lie flat on a 220x220 bed).
import os
import Mesh

BED = 220.0          # Ender-class bed, mm
TIGHT = 210.0

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOTS = [
    os.path.join(BASE, "hardware", "DFCD mesh files"),
    os.path.join(BASE, "hardware-custom"),
]

def check(path):
    flags = []
    try:
        m = Mesh.Mesh()
        m.read(path)
    except Exception as e:
        return ("READ-ERROR: %s" % e,), (0, 0, 0)
    bb = m.BoundBox
    dims = sorted([bb.XLength, bb.YLength, bb.ZLength])
    # footprint when laid flat = the two smallest dims
    if dims[1] > BED:
        flags.append("BED(%.0f>%.0f)" % (dims[1], BED))
    elif dims[1] > TIGHT:
        flags.append("tight(%.0f)" % dims[1])
    try:
        if not m.isSolid():
            flags.append("NOT-SOLID")
    except Exception:
        flags.append("solid?")
    for meth in ("hasNonManifolds", "hasSelfIntersections"):
        try:
            if getattr(m, meth)():
                flags.append(meth.replace("has", "").upper())
        except Exception:
            pass
    return flags, dims

total = 0
problems = 0
print("=== PRINT-READINESS SWEEP ===")
for root in ROOTS:
    if not os.path.isdir(root):
        continue
    for dirpath, _, files in os.walk(root):
        for f in sorted(files):
            if not f.lower().endswith(".3mf"):
                continue
            total += 1
            path = os.path.join(dirpath, f)
            flags, dims = check(path)
            rel = os.path.relpath(path, BASE)
            if flags:
                problems += 1
                print("[!] %-55s %s  (%.0fx%.0fx%.0f)"
                      % (f, " ".join(flags), dims[0], dims[1], dims[2]))
print("--- checked %d mesh files, %d flagged ---" % (total, problems))

# Validate the generated raised lid as a B-rep solid too.
import Part
lid_step = os.path.join(BASE, "hardware-custom", "Screen frame", "GFPIO lid raised 12mm.step")
if os.path.isfile(lid_step):
    s = Part.Shape()
    s.read(lid_step)
    print("RAISED LID step: solids=%d valid=%s closed=%s"
          % (len(s.Solids), s.isValid(), (s.Solids and s.Solids[0].isClosed())))
print("PRINTCHECK_DONE")

# Find the Raspberry Pi PCB inside the Central unit assembly and measure how
# much free space sits above it (HAT clearance), to judge whether an M.2
# HAT+ / extra storage fits inside the chassis.
# Run: FreeCADCmd.exe check_pi_clearance.py   (use short 8.3 path if in Unicode dir)
import os
import Part

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "hardware")
shape = Part.read(os.path.join(BASE, "DFCD STEP files", "Central unit.step"))
sols = shape.Solids
print("solids: %d" % len(sols))

AX = ("X", "Y", "Z")


def dims(bb):
    return (bb.XLength, bb.YLength, bb.ZLength)


def rng(bb, a):
    return ((bb.XMin, bb.XMax), (bb.YMin, bb.YMax), (bb.ZMin, bb.ZMax))[a]


# Pi 4/5 PCB: 85 x 56 x ~1.4-1.7 mm in some orientation.
pi_idx = []
for i, s in enumerate(sols):
    d = sorted(dims(s.BoundBox))
    if d[0] < 3.0 and 50 <= d[1] <= 62 and 80 <= d[2] <= 90:
        pi_idx.append(i)
        bb = s.BoundBox
        print("PI-CANDIDATE #%d dims=%.1f,%.1f,%.1f  X[%.1f,%.1f] Y[%.1f,%.1f] Z[%.1f,%.1f]"
              % (i, bb.XLength, bb.YLength, bb.ZLength,
                 bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))

# Largest solids = chassis walls, for context on interior bounds.
big = sorted(range(len(sols)), key=lambda i: -sols[i].Volume)[:6]
for i in big:
    bb = sols[i].BoundBox
    print("BIG #%d vol=%.0fcm3 dims=%.1f,%.1f,%.1f Z[%.1f,%.1f] Y[%.1f,%.1f]"
          % (i, sols[i].Volume / 1000.0, bb.XLength, bb.YLength, bb.ZLength,
             bb.ZMin, bb.ZMax, bb.YMin, bb.YMax))

for pi in pi_idx:
    pbb = sols[pi].BoundBox
    d = dims(pbb)
    thin = d.index(min(d))          # axis normal to the PCB plane
    longs = [a for a in range(3) if a != thin]
    plo, phi = rng(pbb, thin)
    print("--- candidate #%d: PCB normal axis = %s ---" % (pi, AX[thin]))
    for sign in (+1, -1):
        best = None
        who = None
        for j, s in enumerate(sols):
            if j == pi:
                continue
            obb = s.BoundBox
            # require XY-plane overlap of at least 20mm on both long axes
            ok = True
            for a in longs:
                lo1, hi1 = rng(pbb, a)
                lo2, hi2 = rng(obb, a)
                if min(hi1, hi2) - max(lo1, lo2) < 20:
                    ok = False
                    break
            if not ok:
                continue
            olo, ohi = rng(obb, thin)
            gap = (olo - phi) if sign > 0 else (plo - ohi)
            if gap >= -0.5 and (best is None or gap < best):
                best, who = gap, j
        side = "above (component side?)" if sign > 0 else "below"
        if best is None:
            print("  %s: no facing solid — open space" % side)
        else:
            obb = sols[who].BoundBox
            print("  %s: %.1f mm to solid #%d (dims %.1f,%.1f,%.1f)"
                  % (side, best, who, obb.XLength, obb.YLength, obb.ZLength))
print("CLEARANCE_DONE")

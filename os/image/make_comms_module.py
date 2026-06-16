# Generate the DFCD comms-module enclosure (v1, parametric).
# A clamp-on pod for: Pi Pico (USB bridge) + PN532 NFC + RFM9x LoRa.
# Mounts via the deck's existing printed picatinny rail clamp (bolt pattern in
# the floor); USB cable exits to a rail USB port. NFC reads through a thinned
# front window; LoRa exits an SMA hole. Run: FreeCADCmd.exe make_comms_module.py
#
# All dimensions mm — tune the block below; rail envelope measured at 12.4x26.
import os
import Part
import Mesh
from FreeCAD import Vector

# ---- parameters ----
EXT_X, EXT_Y, EXT_Z = 82.0, 60.0, 32.0   # external box (W x D x H)
WALL = 2.5
FLOOR = 2.5
LID_T = 3.0
SMA_D = 6.5                # LoRa SMA panel-mount hole
USB_W, USB_H = 13.0, 8.0   # Pico USB cable exit slot
BOLT_SPACING = 30.0        # base bolts to the rail clamp (match your printed clamp)
BOLT_D = 3.4               # M3 clearance
PICO_HX, PICO_HY = 47.0, 11.4   # Pi Pico mounting-hole pattern
PICO_HOLE = 2.1
INSET = 5.0                # lid-screw boss inset from corners

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTDIR = os.path.join(BASE, "hardware-custom", "Comms module")


def export(shape, name):
    shape.exportStep(os.path.join(OUTDIR, name + ".step"))
    mesh = Mesh.Mesh()
    mesh.addFacets(shape.tessellate(0.04))
    mesh.write(os.path.join(OUTDIR, name + ".3mf"))
    mesh.write(os.path.join(OUTDIR, name + ".stl"))


if not os.path.isdir(OUTDIR):
    os.makedirs(OUTDIR)

# ---- body: open-top shell ----
outer = Part.makeBox(EXT_X, EXT_Y, EXT_Z)
inner = Part.makeBox(EXT_X - 2 * WALL, EXT_Y - 2 * WALL, EXT_Z - FLOOR + 1)
inner.translate(Vector(WALL, WALL, FLOOR))
body = outer.cut(inner)

# NFC read window — thin the front (+Y) wall to ~1.2 mm over a central area
win = Part.makeBox(40, WALL - 1.2 + 0.01, 24)
win.translate(Vector((EXT_X - 40) / 2.0, EXT_Y - (WALL - 1.2), FLOOR + 4))
body = body.cut(win)

# LoRa SMA hole through the +X end wall
sma = Part.makeCylinder(SMA_D / 2.0, WALL + 2,
                        Vector(EXT_X - WALL - 1, EXT_Y / 2.0, EXT_Z - 9), Vector(1, 0, 0))
body = body.cut(sma)

# USB cable slot through the -X end wall (reaches a rail USB port)
usb = Part.makeBox(WALL + 2, USB_W, USB_H)
usb.translate(Vector(-1, (EXT_Y - USB_W) / 2.0, FLOOR + 3))
body = body.cut(usb)

# Pi Pico standoffs (4 posts, 2.1 mm holes) centred on the floor
cx, cy = EXT_X / 2.0, EXT_Y / 2.0
for dx in (-PICO_HX / 2.0, PICO_HX / 2.0):
    for dy in (-PICO_HY / 2.0, PICO_HY / 2.0):
        post = Part.makeCylinder(2.6, 6, Vector(cx + dx, cy + dy, FLOOR))
        hole = Part.makeCylinder(PICO_HOLE / 2.0, 7, Vector(cx + dx, cy + dy, FLOOR))
        body = body.fuse(post.cut(hole))

# lid-screw bosses in the 4 corners (M3 self-tap pilot 2.7 mm)
corners = [(INSET, INSET), (EXT_X - INSET, INSET),
           (INSET, EXT_Y - INSET), (EXT_X - INSET, EXT_Y - INSET)]
for (bx, by) in corners:
    boss = Part.makeCylinder(4, EXT_Z - FLOOR, Vector(bx, by, FLOOR))
    pilot = Part.makeCylinder(1.35, EXT_Z - FLOOR, Vector(bx, by, FLOOR))
    body = body.fuse(boss.cut(pilot))

# base mounting holes (M3 through) for the rail clamp
for dx in (-BOLT_SPACING / 2.0, BOLT_SPACING / 2.0):
    h = Part.makeCylinder(BOLT_D / 2.0, FLOOR + 2, Vector(cx + dx, cy, -1))
    body = body.cut(h)

body = body.removeSplitter()

# ---- lid ----
lid = Part.makeBox(EXT_X, EXT_Y, LID_T)
for (bx, by) in corners:
    h = Part.makeCylinder(BOLT_D / 2.0, LID_T + 2, Vector(bx, by, -1))
    lid = lid.cut(h)
lid = lid.removeSplitter()

export(body, "Comms module body")
export(lid, "Comms module lid")

bb = body.BoundBox
print("BODY  %.1f x %.1f x %.1f  solids=%d valid=%s closed=%s"
      % (bb.XLength, bb.YLength, bb.ZLength, len(body.Solids),
         body.isValid(), body.Solids and body.Solids[0].isClosed()))
lb = lid.BoundBox
print("LID   %.1f x %.1f x %.1f  solids=%d valid=%s closed=%s"
      % (lb.XLength, lb.YLength, lb.ZLength, len(lid.Solids),
         lid.isValid(), lid.Solids and lid.Solids[0].isClosed()))
print("COMMS_DONE %s" % OUTDIR)

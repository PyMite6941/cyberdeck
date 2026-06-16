#!/usr/bin/env python3
"""Generate the cyberdeck wallpaper (1280x800, matches the 10.1" panel).

Runs ON THE PI during setup (needs python3-pil, preinstalled on Pi OS desktop):
    python3 make_wallpaper.py /opt/cyberdeck/wallpaper.png
Dark green-on-black grid with a DFCD wordmark - same palette as the shell theme.
"""
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 800
BG = (7, 11, 8)
GRID = (15, 36, 21)
GRID_BOLD = (22, 54, 31)
ACCENT = (57, 255, 20)
DIM = (28, 90, 40)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# grid: fine every 40px, bold every 200px
for x in range(0, W + 1, 40):
    d.line([(x, 0), (x, H)], fill=GRID_BOLD if x % 200 == 0 else GRID, width=1)
for y in range(0, H + 1, 40):
    d.line([(0, y), (W, y)], fill=GRID_BOLD if y % 200 == 0 else GRID, width=1)

# corner brackets
for cx, cy, sx, sy in ((40, 40, 1, 1), (W - 40, 40, -1, 1),
                       (40, H - 40, 1, -1), (W - 40, H - 40, -1, -1)):
    d.line([(cx, cy), (cx + 60 * sx, cy)], fill=DIM, width=3)
    d.line([(cx, cy), (cx, cy + 60 * sy)], fill=DIM, width=3)

# wordmark bottom-right
try:
    font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 64)
    font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 22)
except OSError:
    font_big = font_sm = ImageFont.load_default()

d.text((W - 80, H - 170), "DFCD", fill=ACCENT, font=font_big, anchor="rs")
d.text((W - 80, H - 120), "designated freecad device // cyberdeck",
       fill=DIM, font=font_sm, anchor="rs")
d.line([(W - 80 - 420, H - 100), (W - 80, H - 100)], fill=DIM, width=2)

out = sys.argv[1] if len(sys.argv) > 1 else "wallpaper.png"
img.save(out)
print("wrote %s" % out)

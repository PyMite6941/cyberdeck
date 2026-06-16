# Headless FreeCAD measurement of the DFCD STEP assemblies.
# Run: FreeCADCmd.exe measure_parts.py
# Prints bounding-box size (mm) and solid count per module.
import os
import Part

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "hardware")

FILES = [
    ("Central unit",        os.path.join(BASE, "DFCD STEP files", "Central unit.step")),
    ("Battery module",      os.path.join(BASE, "DFCD STEP files", "Battery module compact v29.step")),
    ("External connectors", os.path.join(BASE, "DFCD STEP files", "External connector module.step")),
    ("Scroll module",       os.path.join(BASE, "DFCD STEP files", "Scroll module v48.step")),
    ("Trackball unit",      os.path.join(BASE, "DFCD STEP files", "Trackball unit marble compatible v29.step")),
    ("Dragchain segment",   os.path.join(BASE, "Dragchain step", "Dragchain segment.step")),
    ("Dragchain end",       os.path.join(BASE, "Dragchain step", "Dragchain end segment.step")),
]

print("PART | X(mm) | Y(mm) | Z(mm) | solids")
for name, path in FILES:
    try:
        shape = Part.read(path)
        bb = shape.BoundBox
        print("%s | %.1f | %.1f | %.1f | %d"
              % (name, bb.XLength, bb.YLength, bb.ZLength, len(shape.Solids)))
    except Exception as e:
        print("%s | ERROR: %s" % (name, e))
print("MEASURE_DONE")

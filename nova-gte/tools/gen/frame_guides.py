"""Put the wheel guides on the photo/BA frame's axles, y -1.1715 / +1.1715 (DECISIONS 2026-10-26 (9)).

They were placed at -1.141 / +1.202 in phase 1, a frame whose origin sat 30.5 mm ahead of the wheelbase
midpoint, while every photo measurement, every camera and the body built from them use the midpoint.
Idempotent: each guide is moved so its own centre lands on its axle.

blender -b blender/nova_proc.blend --python tools/gen/frame_guides.py -- out.blend
"""
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args else None
for name, y_ax in (("Wheel_Guide_Front", -1.1715), ("Wheel_Guide_Rear", 1.1715),
                   ("Axle_Front", -1.1715), ("Axle_Rear", 1.1715)):
    o = bpy.data.objects.get(name)
    if not o or o.type != "MESH" or not len(o.data.vertices):
        continue
    ys = [(o.matrix_world @ v.co).y for v in o.data.vertices]
    dy = y_ax - 0.5 * (min(ys) + max(ys))
    o.location += Vector((0.0, dy, 0.0))
    print("%-18s moved %+.4f m -> centre y %+.4f" % (name, dy, y_ax))
if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)

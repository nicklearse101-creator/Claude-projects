"""Bring the FreeCAD-lofted shell into the blend, replacing the lattice version."""
import math
import os
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args else None
ROOT = r"D:\Claude\vauxhall_nova_gte_1989"
OBJ = os.path.join(ROOT, "export", "shell.obj")

before = set(bpy.data.objects.keys())
bpy.ops.wm.obj_import(filepath=OBJ, forward_axis="Y", up_axis="Z")
new = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]
print("imported %d object(s): %s" % (len(new), [o.name for o in new]))

name = "Body_Shell"
old = bpy.data.objects.get(name)
coll = old.users_collection[0] if old else bpy.data.objects["Door_Left"].users_collection[0]
if old:
    bpy.data.objects.remove(old, do_unlink=True)

ob = new[0]
for extra in new[1:]:
    bpy.data.objects.remove(extra, do_unlink=True)
ob.name = name
ob.data.name = name
for c in list(ob.users_collection):
    c.objects.unlink(ob)
coll.objects.link(ob)

me = ob.data
if hasattr(me, "shade_smooth"):
    me.shade_smooth()
for _n in ("set_sharp_from_angle", "set_sharpness_by_angle"):
    _f = getattr(me, _n, None)
    if _f:
        _f(angle=math.radians(40))
        break
paint = bpy.data.materials.get("paint_gunmetal")
if paint and not me.materials:
    me.materials.append(paint)

vs = [ob.matrix_world @ v.co for v in me.vertices]
print("%s: %d verts, %d faces; x %.3f..%.3f  y %+.3f..%+.3f  z %.3f..%.3f"
      % (name, len(vs), len(me.polygons), min(v.x for v in vs), max(v.x for v in vs),
         min(v.y for v in vs), max(v.y for v in vs), min(v.z for v in vs), max(v.z for v in vs)))

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)

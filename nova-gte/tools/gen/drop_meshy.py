"""Take the Meshy shell out of the working blend for good.

Nik, 2026-10-26: the shell is for the general shape of the car and nothing else - it is not to be used
to build from, nor overlaid, nor compared against. Everything it was being used for is now traced:
blender/data/{side,plan,section,roof,skirt}_profile.json and tools/photomatch/body_profile.json.

blender -b blender/nova_proc.blend --python tools/gen/drop_meshy.py -- out.blend
"""
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args else None

gone = []
for ob in list(bpy.data.objects):
    if ob.name.startswith("MESHY"):
        gone.append("%s (%d faces)" % (ob.name, len(ob.data.polygons) if ob.type == "MESH" else 0))
        bpy.data.objects.remove(ob, do_unlink=True)
for name in [c.name for c in bpy.data.collections if c.name.startswith("MESHY")]:
    coll = bpy.data.collections.get(name)
    if coll is not None and not coll.objects:
        bpy.data.collections.remove(coll)
        gone.append("collection %s" % name)
for me in list(bpy.data.meshes):
    if me.users == 0:
        bpy.data.meshes.remove(me)
print("removed: %s" % (", ".join(gone) if gone else "nothing - already clean"))

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)

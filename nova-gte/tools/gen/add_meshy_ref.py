"""Append the Meshy shell into the procedural blend as a measuring reference (Nik 2026-10-26: carry on
editing the blocky from-scratch model, with the Meshy shell as the ruler).

The shell lands in a MESHY_REF collection, renamed MESHY_REF / MESHY_REF_DOOR_L / _R, hidden in the
viewport and excluded from renders. Both files use the same frame (x+ = car's left, y- = front, z up,
ground z = 0), so nothing is moved. Scripts measure against it with ray_cast / closest_point_on_mesh.

The two door objects carry an object-level location in the Meshy file (the door cut left them with their
origins where Blender put them), and appending dropped it, so they landed ~744 mm inboard and the door
area of the ruler was a hole. The source is therefore opened first and the transforms baked into the
mesh data before anything is appended.

blender -b blender/nova_proc.blend --python tools/gen/add_meshy_ref.py -- src.blend out.blend
"""
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = args[0], args[1]

want = {"Meshy_Body": "MESHY_REF", "DOOR_L": "MESHY_REF_DOOR_L", "DOOR_R": "MESHY_REF_DOOR_R"}

# bake the source transforms into the mesh data, via a scratch copy, so the append cannot lose them
import os
import tempfile

HERE = bpy.data.filepath
FLAT = os.path.join(tempfile.gettempdir(), "meshy_ref_flat.blend")
bpy.ops.wm.open_mainfile(filepath=bpy.path.abspath(SRC))
for name in want:
    ob = bpy.data.objects.get(name)
    if ob is None:
        continue
    if ob.matrix_world != ob.matrix_world.Identity(4):
        ob.data.transform(ob.matrix_world)
        print("baked %s transform: loc %s" % (name, tuple(round(v, 4) for v in ob.location)))
    ob.matrix_world = ob.matrix_world.Identity(4)
bpy.ops.wm.save_as_mainfile(filepath=FLAT, copy=True)
bpy.ops.wm.open_mainfile(filepath=HERE)

# clear any previous reference only now: doing it before the reopen above would be undone by it, and
# the appended copies would then come in as MESHY_REF.001
for name in want.values():
    ob = bpy.data.objects.get(name)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)
coll = bpy.data.collections.get("MESHY_REF")
if coll:
    bpy.data.collections.remove(coll)
coll = bpy.data.collections.new("MESHY_REF")
bpy.context.scene.collection.children.link(coll)

with bpy.data.libraries.load(FLAT) as (src, dst):
    dst.objects = [n for n in src.objects if n in want]
for ob in dst.objects:
    if ob is None:
        continue
    new = want[ob.name]
    coll.objects.link(ob)
    ob.name = new
    ob.hide_viewport = True
    ob.hide_render = True
    ob.hide_select = True
    print("ref: %s  %d faces" % (new, len(ob.data.polygons)))

lc = next(c for c in bpy.context.view_layer.layer_collection.children if c.collection is coll)
lc.exclude = False
lc.hide_viewport = True

bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
print("saved", OUT)

"""Prepare the fitted Meshy body: axles onto the Nova axles (y shift), decimate to a workable count (UVs kept).
blender -b blender/nova_meshy.blend --python prep_meshy.py -- dy ratio"""
import sys, bpy
args = sys.argv[sys.argv.index("--") + 1:]
dy, ratio = float(args[0]), float(args[1])
body = bpy.data.objects["Meshy_Body"]
from mathutils import Matrix
body.data.transform(Matrix.Translation((0, dy, 0)))
n0 = len(body.data.polygons)
bpy.context.view_layer.objects.active = body
if ratio < 1.0:        # NB: Blender's collapse decimation scrambles the UVs at seams - use Meshy's remesh instead
    m = body.modifiers.new("dec", "DECIMATE"); m.decimate_type = "COLLAPSE"; m.ratio = ratio; m.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=m.name)
body["axle_shift_y"] = dy
# glTF import splits vertices at every UV seam: weld them so the shell is one surface (UVs stay on the face corners)
import bmesh
bm = bmesh.new(); bm.from_mesh(body.data)
nv = len(bm.verts)
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
print("welded %d seam vertices" % (nv - len(bm.verts)))
bm.to_mesh(body.data); bm.free()
body.data.polygons.foreach_set("use_smooth", [True] * len(body.data.polygons)); body.data.update()
print("faces %d -> %d" % (n0, len(body.data.polygons)))
bpy.ops.wm.save_mainfile()

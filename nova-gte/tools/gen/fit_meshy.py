"""Fit a Meshy GLB to the Nova frame (x+ = car's left, y- = front, z up, ground z = 0, length centred on y = 0) and
measure it against the master dimensions. blender -b --factory-startup --python fit_meshy.py -- in.glb out.blend"""
import sys, math, bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
args = sys.argv[sys.argv.index("--") + 1:]
src, out = args[0], args[1]
L, W, H, WB = 3.622, 1.532, 1.365, 2.343
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
for o in bpy.context.scene.objects:
    o.select_set(o in obs)
bpy.context.view_layer.objects.active = obs[0]
if len(obs) > 1:
    bpy.ops.object.join()
body = bpy.context.view_layer.objects.active
body.name = "Meshy_Body"
bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
me = body.data
V = np.array([v.co[:] for v in me.vertices])
ext = V.max(0) - V.min(0)
print("raw extent", ext.round(3))
# length along the longest horizontal axis -> Y
if ext[0] > ext[1]:
    me.transform(Matrix.Rotation(math.pi / 2, 4, "Z")); V = np.array([v.co[:] for v in me.vertices])
# front = the end whose top (max z over the last 15 % of length) is lower (bonnet vs tailgate)
ymin, ymax = V[:, 1].min(), V[:, 1].max(); span = ymax - ymin
top_a = V[V[:, 1] < ymin + 0.15 * span][:, 2].max(); top_b = V[V[:, 1] > ymax - 0.15 * span][:, 2].max()
if top_a > top_b:                                     # the low end must be at -y
    me.transform(Matrix.Rotation(math.pi, 4, "Z")); V = np.array([v.co[:] for v in me.vertices])
s = L / (V[:, 1].max() - V[:, 1].min())
me.transform(Matrix.Scale(s, 4)); V = np.array([v.co[:] for v in me.vertices])
c = Vector(((V[:, 0].max() + V[:, 0].min()) / 2, (V[:, 1].max() + V[:, 1].min()) / 2, V[:, 2].min()))
me.transform(Matrix.Translation(-c)); V = np.array([v.co[:] for v in me.vertices]); me.update()
print("uniform scale %.4f -> extent %s" % (s, (V.max(0) - V.min(0)).round(3)))
# body width without mirrors: widest at door-mirror height excluded -> take z bands
for z0, z1 in ((0.25, 0.45), (0.45, 0.65), (0.65, 0.85), (0.85, 1.0), (1.1, 1.3)):
    m = (V[:, 2] > z0) & (V[:, 2] < z1)
    print("  z %.2f-%.2f  width %.3f" % (z0, z1, V[m, 0].max() - V[m, 0].min()))
print("height %.3f (spec %.3f)" % (V[:, 2].max(), H))
# wheel contact patches: lowest 2 cm, cluster by y sign and x sign
m = V[:, 2] < 0.02
P = V[m]
for name, sel in (("front-left", (P[:, 1] < 0) & (P[:, 0] > 0)), ("front-right", (P[:, 1] < 0) & (P[:, 0] < 0)),
                  ("rear-left", (P[:, 1] > 0) & (P[:, 0] > 0)), ("rear-right", (P[:, 1] > 0) & (P[:, 0] < 0))):
    Q = P[sel]
    if len(Q):
        print("  contact %-11s y %.3f x %.3f (%d verts)" % (name, Q[:, 1].mean(), Q[:, 0].mean(), len(Q)))
bpy.ops.wm.save_as_mainfile(filepath=out)
print("saved", out)

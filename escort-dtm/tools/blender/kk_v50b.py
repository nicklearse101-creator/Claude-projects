"""v50b: VFD was mirrored in game -> screen UVs flipped in u. Gaps between the screen and the binnacle (engine bay visible) ->
black backing VFD_BACK 2 mm behind the screen, the screen outline grown 45 mm (hidden by the hood outside the opening)."""
import json, sys
import bmesh, bpy, numpy as np
from mathutils import Vector
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kk_build as kb
main = bpy.data.scenes["Scene"]
scr = next(o for o in main.objects if o.name == "VFD_SCREEN")
uvl = scr.data.uv_layers.active.data
# texture u must run left -> right as the driver sees it: u = 0 at the driver's left (+x)
co0 = kb.world_co(scr)
if max((co0[l.vertex_index][0], uvl[i].uv[0]) for i, l in enumerate(scr.data.loops))[1] > 0.5:
    for d in uvl:
        d.uv = (1.0 - d.uv[0], d.uv[1])
if "kn5_pristine" in scr:
    scr["kn5_pristine"] = False
for o in [o for o in main.objects if o.name.startswith("VFD_BACK")]:
    bpy.data.objects.remove(o)
# backing
me = scr.data
co = kb.world_co(scr)
c = co.mean(0)
n = np.array(scr.matrix_world.to_3x3() @ me.polygons[0].normal); n /= np.linalg.norm(n)
cen = co[0]                                     # fan centre vertex (first created)
bm = bmesh.new()
rim = [v for v in co[1:]]
up = np.array([0, 0, 1.0]); up = up - n * up.dot(n); up /= np.linalg.norm(up)
rt = np.cross(up, n)
A = [(r - cen) @ rt for r in rim]; U = [(r - cen) @ up for r in rim]
a0, a1, u0, u1 = min(A), max(A), min(U), max(U)
H = u1 - u0
shape = [(a0, u0 - 0.002, -0.002), (a1, u0 - 0.002, -0.002), (a1 + 0.045, u0 + 0.35 * H, -0.002),
         (a1 + 0.045, u1 + 0.012, -0.002), (a0 - 0.045, u1 + 0.012, -0.002), (a0 - 0.045, u0 + 0.35 * H, -0.002)]
# wide upper sides; the top edge leans 20 mm towards the driver so it closes the gap under the hood without poking
# through the dash top; bottom corners tucked in
vs = [bm.verts.new(Vector(cen + rt * x + up * y + n * z)) for x, y, z in shape]
cv = bm.verts.new(Vector(cen - n * 0.002))
for k in range(len(vs)):
    f = bm.faces.new((cv, vs[k], vs[(k + 1) % len(vs)])); f.normal_update()
    if f.normal.dot(Vector(n)) < 0:
        f.normal_flip()
# ceiling strip: from the backing's top edge towards the glass, above the screen (closes the gap under the hood seen
# from a low eye point)
ct = [bm.verts.new(Vector(cen + rt * x + up * (u1 + 0.012) + n * z)) for x, z in
      ((a0 - 0.045, -0.002), (a1 + 0.045, -0.002), (a1 + 0.045, 0.007), (a0 - 0.045, 0.007))]
f = bm.faces.new(ct); f.normal_update()
if f.normal.dot(Vector(-up)) < 0:
    f.normal_flip()
mb = bpy.data.meshes.new("VFD_BACK"); bm.to_mesh(mb); bm.free()
ob = bpy.data.objects.new("VFD_BACK", mb)
mats = {json.loads(bpy.data.materials[x]["kn5_def"])["name"]: bpy.data.materials[x] for x in json.loads(main["kn5_materials"])}
kb.set_material(ob, mats["Material #166GG45"])
bpy.data.collections["KADETT_KIT"].objects.link(ob)
root = next(o for o in main.objects if o.get("kn5_root"))
ob.parent = root; ob.matrix_parent_inverse = root.matrix_world.inverted()
print("REPORT flipped", len(uvl), "backing faces", len(mb.polygons))
bpy.ops.wm.save_mainfile()

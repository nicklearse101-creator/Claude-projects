"""v48 on the v47 model (Nik 23 Nov 09:02): rectangular yellow fog lamps on the front valance under the indicators.
Housing (black) on the body, chrome bezel, yellow lens = own mesh KK_fog_lens + own material (lit by CSP on high beam).
Run on "escort_v47 liners belts.blend"; saves "escort_v48 fog lamps.blend", exports export_staging_v48."""
import json, sys
import bmesh, bpy
from mathutils import Vector
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kk_build as kb
import kk_finish as kf

kf.STAGE = r"D:\Claude\escort_mk2_dtm\export_staging_v48"
OUT = r"D:\Claude\escort_mk2_dtm\blender\escort_v48 fog lamps.blend"
X0, X1 = 0.475, 0.605            # under the indicators (x 0.496..0.62), clear of the kit's corner pods
Z0, Z1 = 0.108, 0.163            # between the bumper (bottom z 0.20) and the splitter
Y_BACK, Y_FRONT = -1.770, -1.838  # valance face y ~ -1.78
main = bpy.data.scenes["Scene"]; bpy.context.window.scene = main
mats = kf.mats_of(main)
black, steel = mats["Material #166GG45"], mats["Material #503ds"]
lens_mat = bpy.data.materials.get("KK_fog_lens") or bpy.data.materials.new("KK_fog_lens")
lens_mat.use_nodes = True
bsdf = next(n for n in lens_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Base Color"].default_value = (1.0, 0.78, 0.08, 1.0)


def box(bm, x0, x1, y0, y1, z0, z1):
    v = [bm.verts.new((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        bm.faces.new([v[i] for i in f])


hous, bez, lens = bmesh.new(), bmesh.new(), bmesh.new()
uvl = lens.loops.layers.uv.new("UVMap")
for s in (1, -1):
    xa, xb = sorted((s * X0, s * X1))
    box(hous, xa, xb, Y_FRONT + 0.004, Y_BACK, Z0, Z1)                     # body of the lamp
    t = 0.006                                                            # bezel frame round the lens
    for (a, b, c, d) in ((xa, xb, Z1 - t, Z1), (xa, xb, Z0, Z0 + t), (xa, xa + t, Z0, Z1), (xb - t, xb, Z0, Z1)):
        box(bez, a, b, Y_FRONT, Y_FRONT + 0.006, c, d)
    vs = [lens.verts.new(p) for p in ((xa + t, Y_FRONT + 0.003, Z0 + t), (xb - t, Y_FRONT + 0.003, Z0 + t),
                                      (xb - t, Y_FRONT + 0.003, Z1 - t), (xa + t, Y_FRONT + 0.003, Z1 - t))]
    f = lens.faces.new(vs); f.normal_update()
    if f.normal.y > 0:
        f.normal_flip()
    for lp, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        lp[uvl].uv = uv
for b in (hous, bez):
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
root = next(o for o in main.objects if o.get("kn5_root"))
col = bpy.data.collections["KADETT_KIT"]
objs = []
for bm_, name, mat in ((hous, "KK_fog_housing", black), (bez, "KK_fog_bezel", steel), (lens, "KK_fog_lens", lens_mat)):
    me = bpy.data.meshes.new(name); bm_.to_mesh(me); bm_.free()
    ob = bpy.data.objects.new(name, me); kb.set_material(ob, mat)
    kb.link(ob, main, root, col); objs.append(ob)
# LOD B / C
for tag in "BC":
    sc = bpy.data.scenes[kf.SCENES[tag]]
    lm = kf.mats_of(sc)
    lroot = next(o for o in sc.objects if o.get("kn5_root"))
    for src in objs:
        ob = src.copy(); ob.data = src.data.copy(); ob.name = src.name
        if src.name != "KK_fog_lens":
            k = kf.kname(src.material_slots[0].material)
            ob.material_slots[0].material = lm.get(k, lm["Material #166GG45"])
        next(c for c in sc.collection.children).objects.link(ob)
        w = src.matrix_world.copy(); ob.parent = lroot; ob.matrix_parent_inverse.identity(); ob.matrix_world = w
bpy.context.window.scene = main
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("REPORT", json.dumps({"parts": [o.name for o in objs], "export": kf.export_all()}))

"""ESCORT 15" v10 fixes (run on escort15_v10.blend, saves in place):
  - old injectors (V8_black / V8_anodised_blue / V8_alloy islands poking into the trumpet bases: |x| < 0.13, z 0.45-0.60,
    within 40 mm of a trumpet axis, < 400 verts) deleted - on ITBs the injectors live in the throttle bodies
  - HT leads re-routed: distributor -> forward/out to the front of each cam cover -> along the cover top (x +-0.225,
    between trumpets and coil packs) -> down onto each coil
  - "V8 4.0" lettering rebuilt bigger (0.05) higher up the outer cover face."""
import json, math, sys
import bmesh, bpy, numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kk_build as kb
main = bpy.data.scenes["Scene"]; bpy.context.window.scene = main
root = next(o for o in main.objects if o.get("kn5_root")); col = bpy.data.collections["KADETT_KIT"]
CYL = {1: [-1.385, -1.28, -1.175, -1.07], -1: [-1.365, -1.26, -1.155, -1.05]}
rep = {}
src = open(r"D:\Claude\escort_mk2_dtm\tools\blender\kk15h_engine.py", encoding="utf-8").read()
for fn in ("def obj(", "def mdef(", "def drop_islands(", "def new_obj(", "def lathe(", "def tube(", "def bez("):
    i = src.index(fn); j = src.index("\n\n\n", i); exec(src[i:j])


def in_trumpet_zone(p):
    if np.abs(p[:, 0]).max() > 0.13 or len(p) > 400:
        return False
    for s, ys in CYL.items():
        for y in ys:
            d = np.hypot(p[:, 0] - s * 0.135, p[:, 1] - y)
            if ((d < 0.04) & (p[:, 2] > 0.45) & (p[:, 2] < 0.60)).any():
                return True
    return False


rep["injectors"] = {n: drop_islands(obj(n), in_trumpet_zone) for n in ("V8_black", "V8_anodised_blue", "V8_alloy")}

# HT leads
M_YEL = bpy.data.materials["KK_yellow_lead"]
DC = Vector((0, -1.50, 0.40)); Z = Vector((0, 0, 1))
bl = bmesh.new(); ul = bl.loops.layers.uv.new("UVMap")
for s in (1, -1):
    for i, y in enumerate(CYL[s]):
        a = math.radians(-50 + 100 * (i / 3)) + (0 if s > 0 else math.pi)
        p0 = DC + Vector((math.cos(a) * 0.034, math.sin(a) * 0.034, 0.098))
        xr = s * (0.215 + 0.008 * i)                         # 4 leads side by side along the cover top
        z_top = 0.522 + 0.004 * i
        path = bez(p0, p0 + Vector((0, 0, 0.04)), Vector((xr, -1.47, z_top + 0.01)), Vector((xr, -1.44, z_top)), 10)
        path += [Vector((xr, yy, z_top)) for yy in np.linspace(-1.42, y - 0.03, 6)]
        path += bez(Vector((xr, y - 0.02, z_top)), Vector((xr, y, z_top)), Vector((s * 0.25, y, z_top - 0.002)), Vector((s * 0.255, y, 0.512)), 6)[1:]
        tube(bl, ul, path, 0.0045, seg=8)
old = [o for o in main.objects if o.name == "KK_ht_leads"]
for o in old:
    bpy.data.objects.remove(o)
new_obj("KK_ht_leads", bl, M_YEL)

# lettering
for o in [o for o in main.objects if o.name.startswith("KK_cam_lettering")]:
    bpy.data.objects.remove(o)
cc = obj("V8_cam_covers"); co = kb.world_co(cc)
M_POL = bpy.data.materials["KK_polished"]
txts = []
for s in (1, -1):
    pts = co[(co[:, 0] * s > 0.2) & (co[:, 0] * s < 0.31) & (co[:, 2] > 0.40) & (co[:, 2] < 0.47) & (co[:, 1] > -1.36) & (co[:, 1] < -1.06)]
    cen = pts.mean(0); _, _, vt = np.linalg.svd(pts - cen); nrm = Vector(vt[2])
    if nrm.dot(Vector((s, 0, 0.3))) < 0:
        nrm = -nrm
    bpy.ops.object.text_add(location=(0, 0, 0)); t = bpy.context.object
    t.data.body = "V8 4.0"; t.data.size = 0.05; t.data.extrude = 0.0018; t.data.align_x = "CENTER"; t.data.align_y = "CENTER"
    bpy.ops.object.convert(target="MESH"); t = bpy.context.object
    xa = Vector((0, 1, 0)) if s > 0 else Vector((0, -1, 0)); za = nrm; ya = za.cross(xa).normalized(); xa = ya.cross(za).normalized()
    t.matrix_world = Matrix.Translation(Vector(cen) + nrm * 0.004) @ Matrix((xa, ya, za)).transposed().to_4x4()
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True); txts.append(t)
bpy.ops.object.select_all(action="DESELECT")
for t in txts:
    t.select_set(True)
bpy.context.view_layer.objects.active = txts[0]; bpy.ops.object.join(); lt = bpy.context.object
lt.name = "KK_cam_lettering"; lt.data.name = "KK_cam_lettering"
if not lt.data.uv_layers:
    lt.data.uv_layers.new(name="UVMap")
vco = np.array([lt.data.vertices[l.vertex_index].co[:] for l in lt.data.loops])
lt.data.uv_layers[0].data.foreach_set("uv", np.c_[vco[:, 1] * 3 + 0.5, vco[:, 2] * 3 + 0.5].ravel())
for c_ in list(lt.users_collection):
    c_.objects.unlink(lt)
kb.set_material(lt, M_POL); kb.link(lt, main, root, col)
c = kb.world_co(lt); rep["lettering"] = [round(float(v), 3) for v in (c[:, 2].min(), c[:, 2].max(), np.ptp(c[:, 1]))]
bpy.ops.wm.save_mainfile()
print("REPORT", json.dumps(rep))

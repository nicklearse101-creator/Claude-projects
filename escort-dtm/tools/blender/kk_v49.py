"""v49 on the v48 model (Nik 23 Nov):
  1 paint: Material #25DQW used the skin's AO_BODY as txMaps too (red channel = specular -> red went white in sun);
    now its own neutral maps texture ESCORT_BODY_MAPS.dds
  2 wing (KK_wing), mirrors (AERO_mirror_L/R), splitter (KK_splitter), diffuser (NICK3 carbon, rear part) on the body
    paint material with UVs in a free strip of AO_BODY (u 0.91-0.995, v 0.06-0.79) - paintable like the body
  3 belts: CINTURE_ON (shown in game) given the CINTURE_OFF meshes/materials (shown in CM) - same look in both
  4 old arch lips: wing/quarter panels cut with a smooth curve just outside the kit's lip (exact boolean), no teeth
  5 LOD B/C/D regenerated from this model (decimated) - the old LODs still had the old spoiler/kit
Run on "escort_v48 fog lamps.blend"."""
import json, math, os, sys
import bmesh, bpy, numpy as np
from mathutils import Vector
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kk_build as kb
import kk_finish as kf
import ac_kn5_export as ex

STAGE = r"D:\Claude\escort_mk2_dtm\export_staging_v49"
OUT = r"D:\Claude\escort_mk2_dtm\blender\escort_v49.blend"
MAPS = "ESCORT_BODY_MAPS.dds"
MAPS_RGBA = (170, 230, 190, 255)       # specular 0.67, gloss 0.9, reflection 0.75 - same for every colour
STRIP = (0.910, 0.995, 0.060, 0.790)   # free AO_BODY area (checked: no body UVs there)
LOD_RATIO = {"B": 0.30, "C": 0.12, "D": 0.04}
main = bpy.data.scenes["Scene"]; bpy.context.window.scene = main; bpy.context.view_layer.update()
mats = kf.mats_of(main)
paint = mats["Material #25DQW"]
rep = {}


def world(o):
    return kb.world_co(o)


def set_world(o, w):
    inv = np.linalg.inv(np.array(o.matrix_world))
    o.data.vertices.foreach_set("co", ((np.c_[w, np.ones(len(w))] @ inv.T)[:, :3]).ravel()); o.data.update()


def unpristine(o):
    if "kn5_pristine" in o:
        o["kn5_pristine"] = False


def obk(name):
    return next(o for o in main.objects if o.type == "MESH" and (o.get("kn5_name") == name or o.name == name))


# 1 ---------------------------------------------------------------- paint maps
tex_dir = main["kn5_tex_dir"]
assert os.path.exists(os.path.join(tex_dir, MAPS)), "make the maps dds with PIL first (Blender has no PIL)"
texs = json.loads(main["kn5_textures"])
if MAPS not in [t["name"] for t in texs]:
    texs.append({"name": MAPS, "active": 1}); main["kn5_textures"] = json.dumps(texs)
d = json.loads(paint["kn5_def"])
for smp in d["samplers"]:
    if smp[0] == "txMaps":
        smp[2] = MAPS
paint["kn5_def"] = json.dumps(d)
rep["maps"] = [s for s in d["samplers"]]

# 2 ---------------------------------------------------------------- paintable parts
parts = [("KK_wing", 0.30), ("KK_splitter", 0.24), ("NICK3_STATIC_MESH_NICK3_carbon", 0.13),
         ("AERO_mirror_L", 0.03), ("AERO_mirror_R", 0.03)]
u0, u1, v0, v1 = STRIP
v = v1
gap = (v1 - v0 - sum(p[1] for p in parts)) / (len(parts) - 1)
for name, vlen in parts:
    o = obk(name)
    w = world(o)
    if name.startswith("NICK3_STATIC_MESH_NICK3_carbon"):
        pass                                        # front half was cut in v37: what is left is the diffuser
    xr = w[:, 0].max() - w[:, 0].min(); yr = w[:, 1].max() - w[:, 1].min() + 1e-6; zr = w[:, 2].max() - w[:, 2].min() + 1e-6
    depth = (w[:, 1] - w[:, 1].min()) / yr * 0.6 + (w[:, 2] - w[:, 2].min()) / zr * 0.4
    uu = u0 + depth * (u1 - u0)
    vv = (v - vlen) + (w[:, 0] - w[:, 0].min()) / (xr + 1e-6) * vlen
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uvl = me.uv_layers.active.data
    for lp, dd in zip(me.loops, uvl):
        dd.uv = (uu[lp.vertex_index], vv[lp.vertex_index])
    for i in range(len(o.material_slots)):
        o.material_slots[i].material = paint
    unpristine(o)
    v -= vlen + gap
rep["paintable"] = [p[0] for p in parts]

# 3 ---------------------------------------------------------------- belts
pairs = (("CINTURE_OFF_SUB1", "CINTURE_ON_SUB1"), ("CINTURE_OFF_SUB0", "CINTURE_ON_SUB0"),
         ("CINTURE_OFF_SUB1__lr", "CINTURE_ON_SUB1__lr"))
done = []
for s, t in pairs:
    so, to = obk(s), obk(t)
    w = world(so)
    to.data = so.data.copy()
    set_world(to, w)
    unpristine(to); done.append(t)
rep["belts"] = done

# 4 ---------------------------------------------------------------- smooth arch cut
kco = np.vstack([world(o) for o in main.objects if o.type == "MESH" and o.name in ("KK_kit",)])
cutters = []
for (wy, wz) in (kb.E_F, kb.E_R):
    for side in (1, -1):
        near = kco[(kco[:, 0] * side > 0.78) & (np.abs(kco[:, 1] - wy) < 0.65)]
        dd = near[:, 1:] - np.array([wy, wz]); rr = np.hypot(dd[:, 0], dd[:, 1])
        tt = np.degrees(np.arctan2(dd[:, 1], dd[:, 0]))
        degs = np.arange(-40, 221, 3)
        prof = []
        for a in degs:
            m = np.abs(((tt - a + 180) % 360) - 180) < 3
            prof.append(rr[m].min() if m.any() else np.nan)
        prof = np.array(prof)
        ok = np.isfinite(prof)
        degs, prof = degs[ok], prof[ok]
        prof = np.convolve(np.pad(prof, 2, mode="edge"), np.ones(5) / 5, mode="valid")   # smooth curve
        rc = prof + 0.010
        pts = [(wy + r * math.cos(math.radians(a)), wz + r * math.sin(math.radians(a))) for a, r in zip(degs, rc)]
        pts = [(pts[0][0], wz - 1.0)] + pts + [(pts[-1][0], wz - 1.0)]
        bm = bmesh.new()
        xa, xb = sorted((side * 0.50, side * 1.20))
        lo = [bm.verts.new((xa, y, z)) for y, z in pts]
        hi = [bm.verts.new((xb, y, z)) for y, z in pts]
        n = len(pts)
        for k in range(n):
            k2 = (k + 1) % n
            bm.faces.new((lo[k], lo[k2], hi[k2], hi[k]))
        bm.faces.new(lo[::-1]); bm.faces.new(hi)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new("CUT"); bm.to_mesh(me); bm.free()
        c = bpy.data.objects.new("CUT", me); main.collection.objects.link(c); c.hide_render = True
        cutters.append(c)
cut_rep = {}
for name in ("fenders_a_SUB2", "body_a_SUB1"):
    o = obk(name)
    before = len(o.data.polygons)
    from mathutils import kdtree
    pre = world(o)
    kd = kdtree.KDTree(len(pre))
    for i, p_ in enumerate(pre):
        kd.insert(Vector(p_), i)
    kd.balance()
    for c in cutters:
        mod = o.modifiers.new("CUT", "BOOLEAN"); mod.operation = "DIFFERENCE"; mod.object = c
        mod.solver = "EXACT"; mod.use_hole_tolerant = True
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    newme = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    o.modifiers.clear()
    old = o.data; o.data = newme
    for i, s in enumerate(old.materials):
        if i < len(o.material_slots):
            o.material_slots[i].material = s
    unpristine(o)
    # slivers made by the cut (a vertex not in the panel before the cut) poked out as spikes - delete only those
    mw = o.matrix_world
    bm = bmesh.new(); bm.from_mesh(o.data)
    newv = {v for v in bm.verts if kd.find(mw @ v.co)[2] > 1e-4}
    bad = []
    for f in bm.faces:
        if any(v in newv for v in f.verts):
            L = max(((mw @ e.verts[0].co) - (mw @ e.verts[1].co)).length for e in f.edges)
            if L > 0.04 and f.calc_area() / (L * L) < 0.02:
                bad.append(f)
    bmesh.ops.delete(bm, geom=bad, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(o.data); bm.free()
    cut_rep[name] = (before, len(newme.polygons), "new verts", len(newv), "slivers removed", len(bad))
for c in cutters:
    bpy.data.objects.remove(c)
rep["arch_cut"] = cut_rep

bpy.ops.wm.save_as_mainfile(filepath=OUT)

# 5 ---------------------------------------------------------------- export main + LODs from this model
os.makedirs(STAGE, exist_ok=True)
root = next(o for o in main.objects if o.get("kn5_root"))
st = ex.export_kn5(os.path.join(STAGE, kf.FILES["A"]), [root])
rep["A"] = st.get("tris")
meshes = [o for o in main.objects if o.type == "MESH" and not o.get("no_export")]
saved = {o.name: o.get("kn5_pristine") for o in meshes}
for o in meshes:
    if "kn5_pristine" in o:
        o["kn5_pristine"] = False
for tag, ratio in LOD_RATIO.items():
    for o in meshes:
        n = len(o.data.polygons)
        if n > 24:
            m = o.modifiers.new("LOD", "DECIMATE"); m.ratio = max(ratio, 12 / n); m.use_collapse_triangulate = True
    bpy.context.view_layer.update()
    keep_tex = main["kn5_textures"]; main["kn5_textures"] = "[]"      # LODs carry no textures (AC takes them from the main kn5)
    try:
        st = ex.export_kn5(os.path.join(STAGE, kf.FILES[tag]), [root], share_textures=True)
    finally:
        main["kn5_textures"] = keep_tex
    rep[tag] = st.get("tris")
    for o in meshes:
        for m in [m for m in o.modifiers if m.name == "LOD"]:
            o.modifiers.remove(m)
for o in meshes:
    if saved[o.name] is not None:
        o["kn5_pristine"] = saved[o.name]
print("REPORT", json.dumps(rep, default=str))

"""v47 on the v46 model (Nik 23 Nov 08:45):
  * see-through arches: black inner wheel-arch liners (curved roof over each wheel + inner wall, both faces drawn)
  * belts: v40's re-route made NaN vertices (straps vanished). Original strap meshes taken back from the live import
    (kit 0 blend), re-routed robustly to the floor behind the seats; CINTURE_ON (the set shown while driving, switched
    off by the NICK3 work) switched back on and re-routed the same; the chrome anchor eyes on the parcel shelf moved
    to the floor where the straps now end.
Run on "escort_v46 kit in 10mm.blend"; saves "escort_v47 liners belts.blend", exports export_staging_v47."""
import json, math, sys
import bmesh, bpy, numpy as np
from mathutils import Vector
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kk_build as kb
import kk_finish as kf

kf.STAGE = r"D:\Claude\escort_mk2_dtm\export_staging_v47"
OUT = r"D:\Claude\escort_mk2_dtm\blender\escort_v47 liners belts.blend"
SRC0 = r"D:\Claude\escort_mk2_dtm\blender\escort_v37 kadett kit 0 live import.blend"
STRAPS = ("CINTURE_OFF_SUB0", "CINTURE_OFF_SUB003", "CINTURE_OFF_SUB0__lr", "CINTURE_ON_SUB0")
ANCHORS = ("Object001csaas", "Object001csaas001", "CINTURE_OFF_SUB1__lr")
SHELF = (np.array([-0.6, 1.15, 0.55]), np.array([0.6, 1.45, 0.75]))
Y0, YA = 0.55, 0.95                      # strap leaves the seat top at y 0.55, floor anchor at y 0.95
LINER = {"F": dict(x_in=0.50, R=0.335), "R": dict(x_in=0.60, R=0.335)}   # front wall further in: wheels steer
main = bpy.data.scenes["Scene"]; bpy.context.window.scene = main; bpy.context.view_layer.update()
rep = {}


def world(o):
    return kb.world_co(o)


def set_world(o, w):
    inv = np.linalg.inv(np.array(o.matrix_world))
    o.data.vertices.foreach_set("co", ((np.c_[w, np.ones(len(w))] @ inv.T)[:, :3]).ravel()); o.data.update()


# ---------------- belts
dg = bpy.context.evaluated_depsgraph_get()
h = main.ray_cast(dg, Vector((0.27, YA, 0.6)), Vector((0, 0, -1)), distance=1.0)
floor_z = h[1].z if h[0] else 0.13
ZA = floor_z + 0.015
with bpy.data.libraries.load(SRC0) as (src, dst):
    dst.objects = [n for n in src.objects]
orig = {o.get("kn5_name"): o for o in dst.objects if o is not None and o.type == "MESH" and o.get("kn5_name") in STRAPS}
fixed = {}
for o in main.objects:
    k = o.get("kn5_name")
    if o.type != "MESH" or k not in STRAPS or k not in orig:
        continue
    o.data = orig[k].data.copy()
    w = world(o)                                   # original strap, this object's transform
    assert np.isfinite(w).all()
    m = w[:, 1] > Y0
    if not m.any():
        continue
    ymax = w[:, 1].max()
    # strap centreline z(y) from the original geometry (binned), then the run behind the seat is re-laid
    bins = np.linspace(Y0, ymax, 12)
    zc = [w[(w[:, 1] >= a) & (w[:, 1] <= b)][:, 2].mean() if ((w[:, 1] >= a) & (w[:, 1] <= b)).any() else np.nan
          for a, b in zip(bins[:-1], bins[1:])]
    mids = (bins[:-1] + bins[1:]) / 2
    ok = np.isfinite(zc)
    zcl = np.interp(w[m, 1], mids[ok], np.array(zc)[ok])
    t = (w[m, 1] - Y0) / (ymax - Y0)
    z0 = np.interp(Y0, mids[ok], np.array(zc)[ok])
    w[m, 2] = z0 + t * (ZA - z0) + (w[m, 2] - zcl)
    w[m, 1] = Y0 + t * (YA - Y0)
    assert np.isfinite(w).all()
    set_world(o, w)
    if "custom_normal" in o.data.attributes:
        o.data.attributes.remove(o.data.attributes["custom_normal"])
    if "kn5_pristine" in o:
        o["kn5_pristine"] = False
    for p in o.data.polygons:
        p.use_smooth = True
    fixed[k] = int(m.sum())
rep["straps"] = fixed
for o in list(dst.objects):
    if o is not None and o.users == 0:
        bpy.data.objects.remove(o)
# driving belts back on
for o in main.objects:
    if o.get("kn5_name") == "CINTURE_ON" and "kn5_flags" in o:
        fl = json.loads(o["kn5_flags"]); fl["active"] = 1; o["kn5_flags"] = json.dumps(fl); rep["cinture_on"] = "active"
# anchor eyes from the shelf to the floor
moved = {}
for o in main.objects:
    if o.type != "MESH" or o.get("kn5_name") not in ANCHORS:
        continue
    w = world(o); r = kb.islands(o.data); n = 0
    for k in np.unique(r):
        mm = r == k
        if ((w[mm] > SHELF[0]) & (w[mm] < SHELF[1])).all():
            w[mm, 1] += YA - 1.28
            w[mm, 2] += ZA - 0.645
            n += mm.sum()
    if n:
        set_world(o, w); moved[o.get("kn5_name")] = int(n)
rep["anchors_moved"] = moved

# ---------------- wheel-arch liners
mats = kf.mats_of(main)
black = mats["Material #166GG45"]
root = next(o for o in main.objects if o.get("kn5_root"))
col = bpy.data.collections["KADETT_KIT"]
bm = bmesh.new()


def quad(a, b, c, d):
    for vs in ((a, b, c, d), (d, c, b, a)):            # both faces drawn
        bm.faces.new([bm.verts.new(v) for v in vs])


for tag, (wy, wz) in (("F", kb.E_F), ("R", kb.E_R)):
    R, x_in = LINER[tag]["R"], LINER[tag]["x_in"]
    th = np.radians(np.linspace(-25, 205, 47))
    arc = [(wy + R * math.cos(a), wz + R * math.sin(a)) for a in th]
    for side in (1, -1):
        x0, x1 = side * x_in, side * 0.975
        for (y1, z1), (y2, z2) in zip(arc[:-1], arc[1:]):
            quad(Vector((x0, y1, z1)), Vector((x1, y1, z1)), Vector((x1, y2, z2)), Vector((x0, y2, z2)))
        # inner wall: fan from below the wheel centre to the arc
        c = Vector((x0, wy, wz - 0.20))
        for (y1, z1), (y2, z2) in zip(arc[:-1], arc[1:]):
            for vs in ((c, Vector((x0, y1, z1)), Vector((x0, y2, z2))), (c, Vector((x0, y2, z2)), Vector((x0, y1, z1)))):
                bm.faces.new([bm.verts.new(v) for v in vs])
me = bpy.data.meshes.new("KK_arch_liners"); bm.to_mesh(me); bm.free()
lin = bpy.data.objects.new("KK_arch_liners", me); kb.set_material(lin, black)
kb.link(lin, main, root, col)
rep["liners_faces"] = len(me.polygons)
# into LOD B/C (copied like the rest of the kit)
for tag in "BC":
    sc = bpy.data.scenes[kf.SCENES[tag]]
    lm = kf.mats_of(sc)
    ob = lin.copy(); ob.data = lin.data.copy(); ob.name = "KK_arch_liners"
    ob.material_slots[0].material = lm["Material #166GG45"]
    next(c for c in sc.collection.children).objects.link(ob)
    lroot = next(o for o in sc.objects if o.get("kn5_root"))
    w = lin.matrix_world.copy(); ob.parent = lroot; ob.matrix_parent_inverse.identity(); ob.matrix_world = w

bpy.ops.wm.save_as_mainfile(filepath=OUT)
rep["export"] = kf.export_all()
print("REPORT", json.dumps(rep))

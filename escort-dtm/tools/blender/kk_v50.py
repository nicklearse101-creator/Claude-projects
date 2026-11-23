"""v50 on the v49 model (Nik 23 Nov): the analogue cluster replaced by a backlit 1980s VFD.
Old parts switched off (kn5 active 0, so nothing renders or conflicts): dial faces, needles + hubs, odometer, warning lamp strip,
trip knob, night-glow layer. New VFD_SCREEN: a flat screen fitted to the old dial plate (its plane, its outline shrunk 6 mm,
3 mm towards the driver, behind the cluster glass), UV 0..1 across it, own copy of the RaceLogic ksPerPixel material
(the CSP script draws into txDiffuse; ksEmissive lights what is drawn). Cluster glass and surround kept."""
import json, sys
import bmesh, bpy, numpy as np
from mathutils import Vector
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kk_build as kb

OFF = ("Object001", "Object002", "Object003", "Object004", "Object005", "Object006", "dashstructure_a_SUB29",
       "gaugecluster_a_SUB1", "gaugecluster_a_SUB0", "Object011", "Object011__lr", "Object012")
SPLIT = ("Object010", "DASH_NIGTH", "gaugecluster_a_SUB2")      # these also hold the centre-console gauges: cut only x > 0.1
X_CLUSTER = 0.10
main = bpy.data.scenes["Scene"]; bpy.context.view_layer.update()
rep = {"off": []}
for sc in bpy.data.scenes:
    for o in sc.objects:
        if o.type == "MESH" and o.get("kn5_name") in OFF and "kn5_flags" in o:
            fl = json.loads(o["kn5_flags"]); fl["active"] = 0; o["kn5_flags"] = json.dumps(fl)
            if sc == main:
                rep["off"].append(o.get("kn5_name"))

rep["split"] = {}
for o in [o for o in main.objects if o.type == "MESH" and o.get("kn5_name") in SPLIT]:
    co = kb.world_co(o); r = kb.islands(o.data)
    drop = np.zeros(len(co), bool)
    for k in np.unique(r):
        m = r == k
        if co[m][:, 0].min() > X_CLUSTER:
            drop[m] = True
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if drop[v.index]], context="VERTS")
    bm.to_mesh(o.data); bm.free(); rep["split"][o.get("kn5_name")] = int(drop.sum())
    if "kn5_pristine" in o:
        o["kn5_pristine"] = False
glass = next(o for o in main.objects if o.type == "MESH" and o.get("kn5_name") == "dashstructure_a_SUB17")
G = kb.world_co(glass); rg = kb.islands(glass.data)
P = np.vstack([G[rg == k] for k in np.unique(rg) if G[rg == k][:, 0].min() > X_CLUSTER - 0.05])
c = P.mean(0)
u_, s_, vt = np.linalg.svd(P - c)
n = vt[2]
eye = np.array([0.29, 0.05, 0.95])
if np.dot(eye - c, n) < 0:
    n = -n
up = np.array([0, 0, 1.0]); up = up - n * up.dot(n); up /= np.linalg.norm(up)
right = np.cross(n, up)
loc2 = np.c_[(P - c) @ right, (P - c) @ up]
idx = sorted(range(len(loc2)), key=lambda i: (loc2[i][0], loc2[i][1]))
cr = lambda o_, a, b: (loc2[a][0] - loc2[o_][0]) * (loc2[b][1] - loc2[o_][1]) - (loc2[a][1] - loc2[o_][1]) * (loc2[b][0] - loc2[o_][0])
lo, hi = [], []
for i in idx:
    while len(lo) >= 2 and cr(lo[-2], lo[-1], i) <= 0:
        lo.pop()
    lo.append(i)
for i in reversed(idx):
    while len(hi) >= 2 and cr(hi[-2], hi[-1], i) <= 0:
        hi.pop()
    hi.append(i)
hull = np.array([loc2[i] for i in lo[:-1] + hi[:-1]])
cen = hull.mean(0)
hull = cen + (hull - cen) * (1 - 0.004 / np.linalg.norm(hull - cen, axis=1))[:, None]   # shrink 4 mm
# depth: half way between the glass and the first thing behind it (face panel), measured by rays
bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
for o in main.objects:
    if o.type == 'MESH' and (o.get('kn5_name') in OFF or o == glass):
        o.hide_viewport = True
bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
ds = []
for a, b in list(hull) + [cen]:
    q = c + right * (cen[0] + 0.8 * (a - cen[0])) + up * (cen[1] + 0.8 * (b - cen[1])) + n * 0.03
    h = main.ray_cast(dg, Vector(q), Vector(-n), distance=0.2)
    if h[0]:
        ds.append(float(np.dot(np.array(h[1]) - c, n)))
for o in main.objects:
    o.hide_viewport = False
back = min(ds) if ds else -0.02
glass_front = float(max((P - c) @ n))
glass_back = float(min((P - c) @ n))
DEPTH = glass_back - 0.003                       # just behind the cluster glass, in front of the old face panel
rep['depth'] = {'panel': round(back * 1000, 1), 'glass_back': round(glass_back * 1000, 1), 'glass_front': round(glass_front * 1000, 1), 'screen': round(DEPTH * 1000, 1)}
mn, mx = hull.min(0), hull.max(0)
rep["screen_mm"] = [round(1000 * float(v), 1) for v in (mx - mn)]

bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
pts = [Vector(c + right * a + up * b + n * DEPTH) for a, b in hull]
cv = bm.verts.new(Vector(c + right * cen[0] + up * cen[1] + n * DEPTH))
vs = [bm.verts.new(p) for p in pts]
uv = lambda a, b: ((a - mn[0]) / (mx[0] - mn[0]), (b - mn[1]) / (mx[1] - mn[1]))
for k in range(len(vs)):
    f = bm.faces.new((cv, vs[k], vs[(k + 1) % len(vs)])); f.normal_update()
    if f.normal.dot(Vector(n)) < 0:
        f.normal_flip()
    for lp in f.loops:
        q = np.array(lp.vert.co) - c
        lp[uvl].uv = uv(q @ right, q @ up)
me = bpy.data.meshes.new("VFD_SCREEN"); bm.to_mesh(me); bm.free()
ob = bpy.data.objects.new("VFD_SCREEN", me)
src = next(o for o in main.objects if o.type == "MESH" and o.get("kn5_name") == "RACE_LOGIC").data.materials[0]
mat = src.copy(); d = json.loads(src["kn5_def"]); d["name"] = "VFD_SCREEN"; mat["kn5_def"] = json.dumps(d); mat.name = "VFD_SCREEN"
kb.set_material(ob, mat)
root = next(o for o in main.objects if o.get("kn5_root"))
bpy.data.collections["KADETT_KIT"].objects.link(ob)
ob.parent = root; ob.matrix_parent_inverse = root.matrix_world.inverted()
mats = json.loads(main["kn5_materials"])
if mat.name not in mats:
    mats.append(mat.name); main["kn5_materials"] = json.dumps(mats)
# anything (other than the glass) between the screen and the glass would cover the display: list it
bpy.context.view_layer.update()
between = {}
for o in main.objects:
    if o.type != "MESH" or o in (glass, ob) or o.get("kn5_name") in OFF:
        continue
    co = kb.world_co(o)
    q = co - c
    a, b, d_ = q @ right, q @ up, q @ n
    m = (a > mn[0]) & (a < mx[0]) & (b > mn[1]) & (b < mx[1]) & (d_ > DEPTH) & (d_ < glass_front + 0.002)
    if m.sum():
        between[o.get("kn5_name") or o.name] = int(m.sum())
rep["between"] = between
# old face-panel bezels between screen and glass: delete their islands (those mostly inside the screen footprint)
rep["bezels"] = {}
for o in main.objects:
    if o.type != "MESH" or (o.get("kn5_name") or "") not in between:
        continue
    co = kb.world_co(o); q = co - c
    a, b, d_ = q @ right, q @ up, q @ n
    inside = (a > mn[0]) & (a < mx[0]) & (b > mn[1]) & (b < mx[1]) & (d_ > back - 0.01)
    r = kb.islands(o.data); drop = np.zeros(len(co), bool)
    for k in np.unique(r):
        m = r == k
        if inside[m].mean() > 0.6 and (d_[m] > DEPTH).any():
            drop[m] = True
    if drop.any():
        bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if drop[v.index]], context="VERTS")
        bm.to_mesh(o.data); bm.free()
        if "kn5_pristine" in o:
            o["kn5_pristine"] = False
        rep["bezels"][o.get("kn5_name")] = int(drop.sum())
print("REPORT", json.dumps(rep))
bpy.ops.wm.save_as_mainfile(filepath=r"D:\Claude\escort_mk2_dtm\blender\escort_v50 vfd.blend")

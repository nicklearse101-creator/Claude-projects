"""ESCORT 15" v10 - racey Rover-V8-style engine (Nik 24 Nov: velocity stacks/ITBs, red crinkle cam covers, race dress-up,
black & alloy finish). Run on "escort15_v9.blend"; saves "escort15_v10.blend" (v9 = backup).
  - road plenum + runner tops (V8_alloy islands |x|<0.17, z>0.36, y -1.46..-0.95) and the front throttle body / filter
    (V8_black, V8_anodised_red, V8_alloy islands |x|<0.065, y<-1.42, z>0.28) deleted
  - 8 ITBs over the intake ports (x +-0.135, cylinder y's): machined throttle body + short runner + polished flared trumpet
    (to z 0.595, bonnet underside >= 0.627), dark throttle plate inside
  - cam covers -> KK_redcrinkle (red tint of the crinkle texture, same normal map) + raised "V8 4.0" on each outer face
  - V8_alloy split: block (islands z max < 0.30, |x| max < 0.25) -> KK_V8_block in satin black; heads etc -> machined alloy
  - distributor at the front + 8 yellow HT leads to the coil packs; braided fuel lines (rails -> bulkhead, front crossover)
    with red/blue anodised fittings
New parts use ksPerPixel materials (no normal map) or get real non-degenerate UVs (tangents) - see v7 lesson."""
import json, math, sys
import bmesh, bpy, numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kk_build as kb

OUT = r"D:\Claude\escort_mk2_dtm\blender\escort15_v10.blend"
main = bpy.data.scenes["Scene"]; bpy.context.window.scene = main; bpy.context.view_layer.update()
root = next(o for o in main.objects if o.get("kn5_root")); col = bpy.data.collections["KADETT_KIT"]
rep = {}
CYL = {1: [-1.385, -1.28, -1.175, -1.07], -1: [-1.365, -1.26, -1.155, -1.05]}


def obj(n):
    return next(o for o in main.objects if o.type == "MESH" and (o.get("kn5_name") or o.name) == n)


def mdef(m):
    return json.loads(m["kn5_def"])


def add_tex(name):
    t = json.loads(main["kn5_textures"])
    if name not in [x["name"] for x in t]:
        t.append({"name": name, "active": 1}); main["kn5_textures"] = json.dumps(t)


def make_mat(name, base_name, samplers, props):
    base = next(m for m in bpy.data.materials if m.get("kn5_def") and mdef(m)["name"] == base_name)
    m = bpy.data.materials.get(name) or base.copy(); m.name = name
    d = mdef(base); d["name"] = name
    for p in d["props"]:
        if p[0] in props:
            v = props[p[0]]
            if isinstance(v, (list, tuple)):
                p[4:4 + len(v)] = list(v)
            else:
                p[1] = v
    d["samplers"] = [[s[0], s[1], samplers.get(s[0], s[2])] for s in d["samplers"]]
    for s in samplers.values():
        add_tex(s)
    m["kn5_def"] = json.dumps(d)
    ml = json.loads(main["kn5_materials"])
    if name not in ml:
        ml.append(name); main["kn5_materials"] = json.dumps(ml)
    return m


def drop_islands(o, test):
    co = kb.world_co(o); r = kb.islands(o.data); drop = np.zeros(len(co), bool)
    for k in np.unique(r):
        if test(co[r == k]):
            drop[r == k] = True
    if drop.any():
        bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if drop[v.index]], context="VERTS")
        bm.to_mesh(o.data); bm.free()
        if "kn5_pristine" in o:
            o["kn5_pristine"] = False
    return int(drop.sum())


def new_obj(name, bm, mat):
    for o in [o for o in main.objects if o.name == name]:
        bpy.data.objects.remove(o)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me); kb.set_material(ob, mat); kb.link(ob, main, root, col)
    return ob


def lathe(bm, uvl, c, axis, prof, seg=24, inward=False):
    """surface of revolution: prof = [(r, h), ...] along axis from c. UVs: u around, v along (0..1)."""
    axis = axis.normalized(); ref = Vector((1, 0, 0)) if abs(axis.x) < 0.9 else Vector((0, 1, 0))
    u = axis.cross(ref).normalized(); v = axis.cross(u)
    rings = [[bm.verts.new(c + axis * h + (u * math.cos(a) + v * math.sin(a)) * r) for a in np.linspace(0, 2 * math.pi, seg, endpoint=False)] for r, h in prof]
    n = len(prof)
    for j in range(n - 1):
        mid = c + axis * ((prof[j][1] + prof[j + 1][1]) / 2)
        for k in range(seg):
            f = bm.faces.new((rings[j][k], rings[j][(k + 1) % seg], rings[j + 1][(k + 1) % seg], rings[j + 1][k]))
            f.normal_update()
            out = f.calc_center_median() - mid; out = out - axis * out.dot(axis)
            if (f.normal.dot(out) < 0) != inward:
                f.normal_flip()
            for lp in f.loops:
                jj = j if lp.vert in rings[j] else j + 1; kk = rings[jj].index(lp.vert)
                lp[uvl].uv = (kk / seg, jj / (n - 1))


def tube(bm, uvl, path, r, seg=10):
    prev = None; rings = []
    for i, p in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        if prev is None:
            ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0)); nrm = t.cross(ref).normalized()
        else:
            nrm = (prev - t * prev.dot(t)).normalized()
        prev = nrm; bi = t.cross(nrm)
        rings.append([bm.verts.new(p + (nrm * math.cos(a) + bi * math.sin(a)) * r) for a in np.linspace(0, 2 * math.pi, seg, endpoint=False)])
    L = [0.0]
    for a, b in zip(path[:-1], path[1:]):
        L.append(L[-1] + (b - a).length)
    for j in range(len(path) - 1):
        mid = (path[j] + path[j + 1]) / 2
        for k in range(seg):
            f = bm.faces.new((rings[j][k], rings[j][(k + 1) % seg], rings[j + 1][(k + 1) % seg], rings[j + 1][k]))
            f.normal_update()
            if f.normal.dot(f.calc_center_median() - mid) < 0:
                f.normal_flip()
            for lp in f.loops:
                jj = j if lp.vert in rings[j] else j + 1; kk = rings[jj].index(lp.vert)
                lp[uvl].uv = (kk / seg, L[jj] * 8)


def bez(p0, p1, p2, p3, n=16):
    return [p0 * (1 - t) ** 3 + p1 * 3 * t * (1 - t) ** 2 + p2 * 3 * t * t * (1 - t) + p3 * t ** 3 for t in np.linspace(0, 1, n)]


# ---------------------------------------------------------------- materials
alu = next(m for m in bpy.data.materials if m.get("kn5_def") and mdef(m)["name"] == "v8_cast_alu")
crink = next(m for m in bpy.data.materials if m.get("kn5_def") and mdef(m)["name"] == "v8_crinkle_black")
M_RED = make_mat("KK_redcrinkle", "v8_crinkle_black", {"txDiffuse": "KK_crinkle_red.png"}, {})
M_BLK = make_mat("KK_alu_black", "v8_cast_alu", {"txDiffuse": "KK_alu_satinblack.png"}, {"ksSpecular": 0.25, "ksSpecularEXP": 25.0})
M_MAC = make_mat("KK_alu_machined", "v8_cast_alu", {"txDiffuse": "KK_alu_machined.png"}, {"ksSpecular": 0.7, "ksSpecularEXP": 60.0})
M_POL = make_mat("KK_polished", "v8_anodised_red", {"txDiffuse": "KK_polished.png"}, {"ksDiffuse": 0.35, "ksAmbient": 0.35, "ksSpecular": 1.5, "ksSpecularEXP": 120.0})
M_YEL = make_mat("KK_yellow_lead", "v8_anodised_red", {"txDiffuse": "KK_yellow.png"}, {"ksSpecular": 0.3, "ksSpecularEXP": 30.0})
M_BRD = make_mat("KK_braid", "v8_anodised_red", {"txDiffuse": "KK_braid.png"}, {"ksSpecular": 0.9, "ksSpecularEXP": 60.0})
M_ARED = next(m for m in bpy.data.materials if m.get("kn5_def") and mdef(m)["name"] == "v8_anodised_red")
M_ABLU = next(m for m in bpy.data.materials if m.get("kn5_def") and mdef(m)["name"] == "v8_anodised_blue")
M_DARK = next(m for m in bpy.data.materials if m.get("kn5_def") and mdef(m)["name"] == "bumperFrame_radiator")
for m in (M_ARED, M_ABLU, M_DARK):
    assert mdef(m)["shader"] == "ksPerPixel", m.name

# ---------------------------------------------------------------- remove road plenum + front throttle body
v8a, v8b, v8r = obj("V8_alloy"), obj("V8_black"), obj("V8_anodised_red")
rep["plenum"] = drop_islands(v8a, lambda p: np.abs(p[:, 0]).max() < 0.17 and p[:, 2].min() > 0.36 and p[:, 1].min() > -1.46 and p[:, 1].max() < -0.95)
front = lambda p: np.abs(p[:, 0]).max() < 0.065 and p[:, 1].max() < -1.42 and p[:, 2].min() > 0.28
rep["throttle_body"] = [drop_islands(o, front) for o in (v8a, v8b, v8r)]

# ---------------------------------------------------------------- block black / heads machined
co = kb.world_co(v8a); r = kb.islands(v8a.data); is_block = np.zeros(len(co), bool)
for k in np.unique(r):
    p = co[r == k]
    if p[:, 2].max() < 0.30 and np.abs(p[:, 0]).max() < 0.25:
        is_block[r == k] = True
blk = v8a.copy(); blk.data = v8a.data.copy(); blk.name = "KK_V8_block"; blk["kn5_name"] = "KK_V8_block"
for c in v8a.users_collection:
    c.objects.link(blk)
blk.parent = v8a.parent; blk.matrix_world = v8a.matrix_world.copy()
for o, keep in ((blk, is_block), (v8a, ~is_block)):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not keep[v.index]], context="VERTS"); bm.to_mesh(o.data); bm.free()
    if "kn5_pristine" in o:
        o["kn5_pristine"] = False
kb.set_material(blk, M_BLK); kb.set_material(v8a, M_MAC)
rep["block_verts"] = int(is_block.sum())

# ---------------------------------------------------------------- red crinkle cam covers
cc = obj("V8_cam_covers"); kb.set_material(cc, M_RED)

# ---------------------------------------------------------------- ITBs
bt, bp, bd = bmesh.new(), bmesh.new(), bmesh.new()
ut, up_, ud = bt.loops.layers.uv.new("UVMap"), bp.loops.layers.uv.new("UVMap"), bd.loops.layers.uv.new("UVMap")
Z = Vector((0, 0, 1))
for s, ys in CYL.items():
    for y in ys:
        c = Vector((s * 0.135, y, 0.36))
        lathe(bt, ut, c, Z, [(0.022, 0.0), (0.022, 0.04), (0.027, 0.04), (0.027, 0.095), (0.022, 0.095)])     # runner + throttle body
        prof = [(0.022 + 0.014 * (t ** 2.2), 0.095 + 0.14 * t) for t in np.linspace(0, 1, 9)]
        prof += [(0.040, 0.237), (0.041, 0.233), (0.039, 0.229)]                                          # rolled lip
        lathe(bp, up_, c, Z, prof)
        lathe(bp, up_, c, Z, [(0.0205 + 0.014 * (t ** 2.2), 0.095 + 0.134 * t) for t in np.linspace(0, 1, 9)], inward=True)
        lathe(bd, ud, c, Z, [(0.0, 0.105), (0.021, 0.105)])                                                # throttle plate (dark)
ob_t = new_obj("KK_itb_bodies", bt, M_MAC); ob_p = new_obj("KK_itb_trumpets", bp, M_POL); ob_d = new_obj("KK_itb_plates", bd, M_DARK)
# UVs of the machined bodies: keep inside a small patch of the alu atlas (normal-mapped shader -> valid tangents)
for o, patch in ((ob_t, 0.25),):
    lay = o.data.uv_layers[0]; a = np.empty(len(o.data.loops) * 2); lay.data.foreach_get("uv", a); a = a.reshape(-1, 2)
    lay.data.foreach_set("uv", (np.array([0.3, 0.3]) + a * patch).ravel())

# ---------------------------------------------------------------- "V8 4.0" on the cam cover outer faces
co = kb.world_co(cc); r = kb.islands(cc.data)
txts = []
for s in (1, -1):
    pick = [k for k in np.unique(r) if (co[r == k][:, 0] * s).min() > 0.19 and (co[r == k][:, 0] * s).max() < 0.31 and np.ptp(co[r == k][:, 1]) > 0.35]
    pts = np.vstack([co[r == k] for k in pick]) if pick else co[(co[:, 0] * s > 0.2)]
    face = pts[(pts[:, 2] > 0.37) & (pts[:, 2] < 0.47) & (pts[:, 0] * s > 0.24)]
    cen = face.mean(0); _, _, vt = np.linalg.svd(face - cen); nrm = Vector(vt[2])
    if nrm.dot(Vector((s, 0, 0.3))) < 0:
        nrm = -nrm
    bpy.ops.object.text_add(location=(0, 0, 0)); t = bpy.context.object
    t.data.body = "V8 4.0"; t.data.size = 0.034; t.data.extrude = 0.0015; t.data.align_x = "CENTER"; t.data.align_y = "CENTER"
    bpy.ops.object.convert(target="MESH"); t = bpy.context.object
    along = Vector((0, 1, 0)) if s > 0 else Vector((0, -1, 0))        # reads front-to-back on the left, back-to-front on the right
    xa = along; za = nrm; ya = za.cross(xa).normalized(); xa = ya.cross(za).normalized()
    R = Matrix((xa, ya, za)).transposed().to_4x4()
    t.matrix_world = Matrix.Translation(Vector(cen) + nrm * 0.004) @ R
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    txts.append(t)
bpy.ops.object.select_all(action="DESELECT")
for t in txts:
    t.select_set(True)
bpy.context.view_layer.objects.active = txts[0]; bpy.ops.object.join(); lt = bpy.context.object
lt.name = "KK_cam_lettering"; lt.data.name = "KK_cam_lettering"
if not lt.data.uv_layers:
    lt.data.uv_layers.new(name="UVMap")
lay = lt.data.uv_layers[0]; vco = np.array([lt.data.vertices[l.vertex_index].co[:] for l in lt.data.loops])
lay.data.foreach_set("uv", np.c_[vco[:, 1] * 3 + 0.5, vco[:, 2] * 3 + 0.5].ravel())
for c_ in list(lt.users_collection):
    c_.objects.unlink(lt)
kb.set_material(lt, M_POL); kb.link(lt, main, root, col)

# ---------------------------------------------------------------- distributor + HT leads
bd2 = bmesh.new(); u2 = bd2.loops.layers.uv.new("UVMap")
DC = Vector((0, -1.50, 0.40))
lathe(bd2, u2, DC, Z, [(0.0, 0.0), (0.03, 0.0), (0.03, 0.05), (0.046, 0.055), (0.046, 0.09), (0.03, 0.105), (0.0, 0.108)])
ob_dist = new_obj("KK_distributor", bd2, M_DARK)
bl = bmesh.new(); ul = bl.loops.layers.uv.new("UVMap")
for i, (s, y) in enumerate([(s, y) for s in (1, -1) for y in CYL[s]]):
    a = math.radians(-60 + 120 * ((i % 4) / 3)) + (0 if s > 0 else math.pi)
    p0 = DC + Vector((math.cos(a) * 0.036, math.sin(a) * 0.036, 0.098))
    p3 = Vector((s * 0.255, y, 0.515))
    tube(bl, ul, bez(p0, p0 + Vector((0, 0, 0.06)), p3 + Vector((-s * 0.05, 0, 0.08)), p3), 0.0045, seg=8)
new_obj("KK_ht_leads", bl, M_YEL)

# ---------------------------------------------------------------- braided lines + fittings
bb = bmesh.new(); ub = bb.loops.layers.uv.new("UVMap")
bf, uf = bmesh.new(), None; uf = bf.loops.layers.uv.new("UVMap")
bfb = bmesh.new(); ufb = bfb.loops.layers.uv.new("UVMap")
lines = []
for s in (1, -1):
    a = Vector((s * 0.09, -0.965, 0.497)); b = Vector((s * 0.24, -0.83, 0.56))
    lines.append(bez(a, a + Vector((0, 0.06, 0.03)), b + Vector((-s * 0.05, -0.04, 0.0)), b))
a = Vector((0.09, -1.445, 0.497)); b = Vector((-0.09, -1.445, 0.497))
lines.append(bez(a, a + Vector((0, -0.05, 0.08)), b + Vector((0, -0.05, 0.08)), b))
for i, L in enumerate(lines):
    tube(bb, ub, L, 0.006, seg=10)
    for end, nxt, fb in ((L[0], L[1], bf if i % 2 == 0 else bfb), (L[-1], L[-2], bfb if i % 2 == 0 else bf)):
        d = (nxt - end).normalized()
        lathe(fb, fb.loops.layers.uv.active, end - d * 0.004, d, [(0.0, 0.0), (0.0095, 0.0), (0.0095, 0.018), (0.0075, 0.022), (0.0, 0.022)], seg=6)
new_obj("KK_braided_lines", bb, M_BRD); new_obj("KK_fittings_red", bf, M_ARED); new_obj("KK_fittings_blue", bfb, M_ABLU)

bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("REPORT", json.dumps(rep))

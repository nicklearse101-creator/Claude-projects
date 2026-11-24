"""ESCORT 15" v6 (Nik 24 Nov: "chrome and 8 of them"): one stack per cylinder - 4 per bank in a row just outboard of the
bonnet vents, each a 45 mm primary from its exhaust port up through the bonnet, 90 mm chrome tip (up, a little out/back),
rolled lip, soot disc, black collar. Own chrome material KK_chrome (ksPerPixelMultiMap, white maps = full spec/gloss/
reflection) and cylindrical UVs (the old pipes had none -> sampled black). Flames: KK_flame_L/R1..3 rebuilt with a flame on
every stack (one length per mesh, hidden by default; exhaust_flames.lua unchanged).
Run on "escort15_v5.blend"; saves "escort15_v6.blend". Prints AC-space tips for ext_config / flames.ini."""
import json, math, sys
import bmesh, bpy, numpy as np
from mathutils import Vector
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kk_build as kb

OUT = r"D:\Claude\escort_mk2_dtm\blender\escort15_v6.blend"
PIPE_R, TIP_R = 0.0225, 0.025
X_EXIT = 0.525
YS = (-1.35, -1.22, -1.09, -0.97)                     # along each bank, front to back (cylinder spacing ~0.13)
D = Vector((0.30, 0.20, 0.93)).normalized()
TIP_LEN = 0.09
FLAME_LENGTHS = (0.15, 0.24, 0.34)
main = bpy.data.scenes["Scene"]; bpy.context.window.scene = main
for o in main.objects:                                    # bonnet height rays must not hit the old exhaust / flames
    if o.name.startswith(("KK_exhaust_", "KK_flame_")):
        o.hide_viewport = True
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()


def catmull(pts, n=8):
    out = []; P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1]); return out


def tube(bm, uvl, path, r, seg=18):
    prev = None; rings = []; L = 0.0; lens = [0.0]
    for a, b in zip(path[:-1], path[1:]):
        L += (b - a).length; lens.append(L)
    for i, p in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        if prev is None:
            ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0)); nrm = t.cross(ref).normalized()
        else:
            nrm = (prev - t * prev.dot(t)).normalized()
        prev = nrm; bi = t.cross(nrm)
        rings.append([bm.verts.new(p + (nrm * math.cos(a) + bi * math.sin(a)) * r) for a in np.linspace(0, 2 * math.pi, seg, endpoint=False)])
    for j, (a, b) in enumerate(zip(rings[:-1], rings[1:])):
        for k in range(seg):
            f = bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
            for lp, (u, v) in zip(f.loops, ((k / seg, lens[j]), ((k + 1) / seg, lens[j]), ((k + 1) / seg, lens[j + 1]), (k / seg, lens[j + 1]))):
                lp[uvl].uv = (u, v * 4)


def disc(bm, uvl, c, n, r_in, r_out, seg=20):
    ref = Vector((1, 0, 0)) if abs(n.x) < 0.9 else Vector((0, 1, 0))
    u = n.cross(ref).normalized(); v = n.cross(u)
    ring = lambda r: [bm.verts.new(c + (u * math.cos(a) + v * math.sin(a)) * r) for a in np.linspace(0, 2 * math.pi, seg, endpoint=False)]
    fs = []
    if r_in <= 0:
        fs.append(bm.faces.new(ring(r_out)))
    else:
        a, b = ring(r_in), ring(r_out)
        fs += [bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k])) for k in range(seg)]
    for f in fs:
        f.normal_update()
        if f.normal.dot(n) < 0:
            f.normal_flip()
        for lp in f.loops:
            lp[uvl].uv = (0.5, 0.5)


def bonnet_z(x, y):
    hit = main.ray_cast(dg, Vector((x, y, 1.5)), Vector((0, 0, -1)), distance=1.2)
    return hit[1].z if hit[0] else 0.66


# chrome material
tex = json.loads(main["kn5_textures"]); names = [t["name"] for t in tex]
need = ("rgbaffffffff.dds", "flat_nm.dds", "rgbab6b6b6ff.dds")
assert all(n in names for n in need), [n for n in need if n not in names]
base = next(m for m in bpy.data.materials if m.get("kn5_def") and json.loads(m["kn5_def"])["name"] == "Material #400312")
chrome = bpy.data.materials.get("KK_chrome") or base.copy(); chrome.name = "KK_chrome"
dd = json.loads(base["kn5_def"]); dd["name"] = "KK_chrome"
for p in dd["props"]:
    k = p[0]
    if k == "ksAmbient": p[1] = 0.25
    if k == "ksDiffuse": p[1] = 0.08
    if k == "ksSpecular": p[1] = 2.0
    if k == "ksSpecularEXP": p[1] = 400.0
    if k == "fresnelC": p[1] = 0.85
    if k == "fresnelMaxLevel": p[1] = 1.0
    if k == "fresnelEXP": p[1] = 2.0
    if k == "isAdditive": p[1] = 1.0
    if k == "useDetail": p[1] = 0.0                       # the detail slot holds the skin colour on this car
    if k == "ksEmissive": p[1:11] = [0.0] * 10
dd["samplers"] = [[s[0], s[1], {"txDiffuse": "rgbab6b6b6ff.dds", "txNormal": "flat_nm.dds", "txMaps": "rgbaffffffff.dds"}.get(s[0], s[2])] for s in dd["samplers"]]
chrome["kn5_def"] = json.dumps(dd)
mats = json.loads(main["kn5_materials"])
if "KK_chrome" not in mats:
    mats.append("KK_chrome"); main["kn5_materials"] = json.dumps(mats)

old = {n: next(o for o in main.objects if o.type == "MESH" and o.name == n) for n in ("KK_exhaust_pipes", "KK_exhaust_tips", "KK_exhaust_dark")}
bms = {n: bmesh.new() for n in old}
uvs = {n: b.loops.layers.uv.new("UVMap") for n, b in bms.items()}
tips_ac = []; tips_bl = []
for s in (1, -1):
    for y in YS:
        d = Vector((s * D.x, D.y, D.z))
        bz = bonnet_z(s * X_EXIT, y)
        ex = Vector((s * X_EXIT, y, bz))
        pts = [Vector((s * 0.33, y, 0.30)), Vector((s * 0.42, y, 0.36)), Vector((s * 0.49, y, 0.50)), Vector((s * 0.515, y, bz - 0.05)), ex - d * 0.02]
        tube(bms["KK_exhaust_pipes"], uvs["KK_exhaust_pipes"], catmull(pts), PIPE_R)
        end = ex + d * TIP_LEN
        tube(bms["KK_exhaust_tips"], uvs["KK_exhaust_tips"], [ex - d * 0.03, ex + d * (TIP_LEN / 2), end], TIP_R)
        tube(bms["KK_exhaust_tips"], uvs["KK_exhaust_tips"], [end, end - d * 0.004], TIP_R - 0.003)
        disc(bms["KK_exhaust_dark"], uvs["KK_exhaust_dark"], end - d * 0.010, d, 0, TIP_R - 0.002)
        disc(bms["KK_exhaust_dark"], uvs["KK_exhaust_dark"], ex + Vector((0, 0, 0.003)), Vector((0, 0, 1)), TIP_R + 0.001, TIP_R + 0.015)
        tips_bl.append((end.copy(), d.copy(), s))
        tips_ac.append(((round(end.x, 4), round(end.z, 4), round(-end.y, 4)), (round(d.x, 4), round(d.z, 4), round(-d.y, 4))))
for n, ob in old.items():
    me = bpy.data.meshes.new(n); bms[n].to_mesh(me); bms[n].free()
    for p in me.polygons:
        p.use_smooth = True
    me.transform(ob.matrix_world.inverted())
    keep = ob.material_slots[0].material
    ob.data = me; ob.hide_viewport = False
    kb.set_material(ob, chrome if n != "KK_exhaust_dark" else keep)
    if "kn5_pristine" in ob:
        ob["kn5_pristine"] = False

# flames: one mesh per (side, length), a flame on each of that side's 4 stacks
fl = [o for o in main.objects if o.name.startswith("KK_flame_") and o.type == "MESH"]
fmat = fl[0].material_slots[0].material
flags = {o.name: o.get("kn5_flags") for o in fl}
for o in [o for o in main.objects if o.name.startswith("KK_flame_")]:
    bpy.data.objects.remove(o)
root = next(o for o in main.objects if o.get("kn5_root")); col = bpy.data.collections["KADETT_KIT"]
made = []
for tag, s in (("L", 1), ("R", -1)):
    for k, L in enumerate(FLAME_LENGTHS, 1):
        bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
        wid = 0.05 + 0.03 * k
        for tip, d, side in tips_bl:
            if side != s:
                continue
            up = Vector((0, 1, 0)); a1 = (up - d * up.dot(d)).normalized(); a2 = d.cross(a1).normalized()
            for ang in (0, 60, 120):
                ax = (a1 * math.cos(math.radians(ang)) + a2 * math.sin(math.radians(ang))).normalized()
                q = [tip - ax * wid / 2, tip + ax * wid / 2, tip + d * L + ax * wid / 2, tip + d * L - ax * wid / 2]
                f = bm.faces.new([bm.verts.new(p) for p in q])
                for lp, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                    lp[uvl].uv = uv
                f2 = bm.faces.new([bm.verts.new(p) for p in reversed(q)])
                for lp, uv in zip(f2.loops, ((0, 1), (1, 1), (1, 0), (0, 0))):
                    lp[uvl].uv = uv
        name = f"KK_flame_{tag}{k}"
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(name, me); kb.set_material(ob, fmat); kb.link(ob, main, root, col)
        ob["kn5_flags"] = json.dumps({"active": 0, "cast": 0, "visible": 1, "transparent": 1, "renderable": 1})
        made.append(name)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("REPORT", made)
print("TIPS_AC", json.dumps(tips_ac))

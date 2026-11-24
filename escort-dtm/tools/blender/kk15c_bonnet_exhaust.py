"""ESCORT 15" v5 (Nik 24 Nov "replace side exits" with exhausts out of the bonnet + flames):
  - old side-exit pipes/tips/soot (KK_exhaust_pipes/tips/dark) replaced - same object names, so ext_config refs keep working
  - per bank: pipe from the header turn-down (x 0.31, y -1.00, z 0.27) up and outward, through the bonnet just outboard of
    the bonnet vents (x 0.525, y -1.02, bonnet z ~0.66), tip pointing up, a little out and back; black collar on the bonnet
  - mesh flames KK_flame_L/R1..3 rebuilt at the new tips (kk_v51_flames with the new TIP/DIR, hidden by default)
Run on "escort15_v4.blend"; saves "escort15_v5.blend". Prints the AC-space tip positions/directions for ext_config/flames.ini."""
import json, math, sys
import bmesh, bpy, numpy as np
from mathutils import Vector
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kk_build as kb

OUT = r"D:\Claude\escort_mk2_dtm\blender\escort15_v5.blend"
PIPE_R, TIP_R = 0.035, 0.038
EXIT = Vector((0.525, -1.02, 0.660))
D = Vector((0.30, 0.20, 0.93)).normalized()            # up, a little outward (x) and back (+y = rear)
TIP_LEN = 0.10
main = bpy.data.scenes["Scene"]; bpy.context.window.scene = main


def catmull(pts, n=10):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return out


def tube(bm, path, r, seg=20):
    prev = None; rings = []
    for i, p in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        if prev is None:
            ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            nrm = t.cross(ref).normalized()
        else:
            nrm = (prev - t * prev.dot(t)).normalized()
        prev = nrm; bi = t.cross(nrm)
        rings.append([bm.verts.new(p + (nrm * math.cos(a) + bi * math.sin(a)) * r) for a in np.linspace(0, 2 * math.pi, seg, endpoint=False)])
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(seg):
            bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    return rings


def disc(bm, c, n, r_in, r_out, seg=24):
    ref = Vector((1, 0, 0)) if abs(n.x) < 0.9 else Vector((0, 1, 0))
    u = n.cross(ref).normalized(); v = n.cross(u)
    ring = lambda r: [bm.verts.new(c + (u * math.cos(a) + v * math.sin(a)) * r) for a in np.linspace(0, 2 * math.pi, seg, endpoint=False)]
    if r_in <= 0:
        f = bm.faces.new(ring(r_out)); f.normal_update()
        if f.normal.dot(n) < 0:
            f.normal_flip()
        return
    a, b = ring(r_in), ring(r_out)
    for k in range(seg):
        f = bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k])); f.normal_update()
        if f.normal.dot(n) < 0:
            f.normal_flip()


old = {n: next(o for o in main.objects if o.type == "MESH" and o.name == n) for n in ("KK_exhaust_pipes", "KK_exhaust_tips", "KK_exhaust_dark")}
pipe, tips, dark = bmesh.new(), bmesh.new(), bmesh.new()
tips_ac = []
for s in (1, -1):
    m = lambda v: Vector((s * v.x, v.y, v.z))
    d = m(D); ex = m(EXIT)
    pts = [m(Vector((0.31, -1.00, 0.27))), m(Vector((0.40, -1.00, 0.33))), m(Vector((0.47, -1.01, 0.47))),
           m(Vector((0.51, -1.02, 0.60))), ex - d * 0.02]
    tube(pipe, catmull(pts, 10), PIPE_R)
    end = ex + d * TIP_LEN
    tube(tips, [ex - d * 0.03, ex + d * (TIP_LEN / 2), end], TIP_R)
    tube(tips, [end, end - d * 0.004], TIP_R - 0.003)                            # rolled lip
    disc(dark, end - d * 0.012, d, 0, TIP_R - 0.002)                            # soot inside the tip
    disc(dark, ex + Vector((0, 0, 0.003)), Vector((0, 0, 1)), TIP_R + 0.001, TIP_R + 0.022)   # collar on the bonnet
    tips_ac.append(((end.x, end.z, -end.y), (d.x, d.z, -d.y)))
for bmx, ob in ((pipe, old["KK_exhaust_pipes"]), (tips, old["KK_exhaust_tips"]), (dark, old["KK_exhaust_dark"])):
    me = bpy.data.meshes.new(ob.name); bmx.to_mesh(me); bmx.free()
    for p in me.polygons:
        p.use_smooth = True
    inv = ob.matrix_world.inverted(); me.transform(inv)
    mats = [s.material for s in ob.material_slots]
    ob.data = me
    kb.set_material(ob, mats[0])
    if "kn5_pristine" in ob:
        ob["kn5_pristine"] = False

# flames at the new tips
src = open(r"D:\Claude\escort_mk2_dtm\tools\blender\kk_v51_flames.py", encoding="utf-8").read()
tip_end = EXIT + D * TIP_LEN
src = src.replace('TIP = (0.952, 0.18, -0.03)', f'TIP = ({tip_end.x:.4f}, {tip_end.y:.4f}, {tip_end.z:.4f})')
src = src.replace('DIR = Vector((0.894, 0.447, 0.0))', f'DIR = Vector(({D.x:.4f}, {D.y:.4f}, {D.z:.4f}))')
src = src.replace(r'OUT = r"D:\Claude\escort_mk2_dtm\blender\escort_v51 flames.blend"', f'OUT = r"{OUT}"')
assert "TIP = (0.952" not in src and "DIR = Vector((0.894" not in src and OUT in src
exec(compile(src, "kk_v51_flames", "exec"), {"__name__": "flames"})
print("TIPS_AC", json.dumps([[[round(v, 4) for v in p], [round(v, 4) for v in dd]] for p, dd in tips_ac]))

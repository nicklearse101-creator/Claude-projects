"""Bolt-on exterior details for the Nova GTE (runs inside Blender), placed from the photo-matched points
(tools/photomatch/ba_result.json, BA frame) and onto the body surface via body_geom (so they sit on the skin
after the shell is refitted). Sizes ESTIMATE from the photos unless noted. Objects go in collection DETAILS;
left-hand parts are mirrored for the right where the car is symmetric.

Parts: door mirrors (black sail + body-colour housing), door handles + lock, side repeaters, fuel cap (right),
number plates (520 x 111 mm, UK), grille slats + GTE badge, rear panel grey bar + badges, hatch roof spoiler,
wipers (front pair, rear), exhaust tailpipe, arch liner material on the arch cutters.
"""
import importlib
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(r"D:\Claude\vauxhall_nova_gte_1989")
if str(ROOT / "blender" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "blender" / "scripts"))
import body_geom as g  # noqa: E402
importlib.reload(g)

DET = "DETAILS"
DZ = g.DZ


def coll():
    c = bpy.data.collections.get(DET) or bpy.data.collections.new(DET)
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


def mat_new(name, rgba, preset, metallic=0.0, rough=0.5):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = rgba
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    m.diffuse_color = rgba
    m.metallic = metallic
    m.roughness = rough
    m["ac_preset"] = preset
    m["ac_shader"] = "ksPerPixelMultiMap"
    return m


def remove(name):
    o = bpy.data.objects.get(name)
    if o:
        me = o.data
        bpy.data.objects.remove(o)
        if me and me.users == 0:
            bpy.data.meshes.remove(me)


def obj(name, bm, materials, bevel=0.0, smooth=True, segs=2):
    remove(name)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    o = bpy.data.objects.new(name, me)
    for m in materials:
        o.data.materials.append(m)
    coll().objects.link(o)
    if bevel:
        b = o.modifiers.new("Bevel", "BEVEL")
        b.width = bevel
        b.segments = segs
        b.limit_method = "ANGLE"
        b.harden_normals = False
    return o


def box(bm, lo, hi, mi=0, xf=None):
    r = bmesh.ops.create_cube(bm, size=1.0)
    for v in r["verts"]:
        v.co = Vector(((lo[0] if v.co.x < 0 else hi[0]), (lo[1] if v.co.y < 0 else hi[1]), (lo[2] if v.co.z < 0 else hi[2])))
    if xf is not None:
        bmesh.ops.transform(bm, matrix=xf, verts=r["verts"])
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mi
    return r["verts"]


def cyl(bm, centre, axis, radius, depth, segs=24, mi=0, cap=True):
    r = bmesh.ops.create_cone(bm, cap_ends=cap, segments=segs, radius1=radius, radius2=radius, depth=depth)
    q = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized())
    bmesh.ops.transform(bm, matrix=Matrix.Translation(centre) @ q.to_matrix().to_4x4(), verts=r["verts"])
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mi
    return r["verts"]


def mirrored(src, name):
    remove(name)
    o = src.copy()
    o.data = src.data.copy()
    o.name = name
    o.data.name = name
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.transform(bm, matrix=Matrix.Scale(-1, 4, (1, 0, 0)), verts=bm.verts[:])
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(o.data)
    bm.free()
    coll().objects.link(o)
    return o


def face_y_front(z):
    """y of the centreline front face (bumper / grille / lamp face) at height z, unswept."""
    lo, hi = g.Y_FRONT, -1.70
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if g.TOP_F(mid) < z:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def strip(bm, x0, x1, y0, depth, z0, z1, mi=0, n=12):
    """Box across x (n segments) whose every vertex goes through the end sweep: parts on the curved nose/tail."""
    rows = []
    for k in range(n + 1):
        x = x0 + (x1 - x0) * k / n
        rows.append([bm.verts.new(P(x, y0 + dy, z)) for dy, z in ((0, z0), (depth, z0), (depth, z1), (0, z1))])
    for a, b in zip(rows, rows[1:]):
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((a[i], b[i], b[j], a[j])).material_index = mi
    bm.faces.new(rows[0]).material_index = mi
    bm.faces.new(rows[-1][::-1]).material_index = mi


def surf_y(x, z, front=True):
    """Unswept y of the top-row surface (front or rear face) at lateral x, height z."""
    lo, hi = (g.Y_FRONT, -1.69) if front else (1.69, g.Y_REAR)
    f = lambda y: g.top_z(y, abs(x)) - z
    flo = f(lo)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if (f(mid) > 0) == (flo > 0):
            lo, flo = mid, f(mid)
        else:
            hi = mid
    return 0.5 * (lo + hi)


def lamp_unit(name, x0, x1, z0, z1, lens_bands, front=True, depth=0.055, bowl=0.035, nx=10, nz=6, refl_mat=1, house_mat=2,
              frame=False, recess=0.0):
    """Lamp unit filling a shell opening: lens on the body surface (bands of materials up the lens), black
    housing walls going into the body, chrome reflector bowl at the back, bulb. Left side; mirror for the right."""
    bm = bmesh.new()
    sgn = 1.0 if front else -1.0                          # into the body = +y at the front, -y at the rear
    grid = {}
    for i in range(nx + 1):
        for k in range(nz + 1):
            x = x0 + (x1 - x0) * i / nx
            z = z0 + (z1 - z0) * k / nz
            y = surf_y(x, z, front)
            grid[i, k] = (x, y, z)
    # final-space lens points and outward normals (so the housing goes straight into the body even where the
    # surface wraps round a corner)
    FP = {key: P(*p) for key, p in grid.items()}

    def normal(i, k):
        a = FP[min(i + 1, nx), k] - FP[max(i - 1, 0), k]
        b = FP[i, min(k + 1, nz)] - FP[i, max(k - 1, 0)]
        n = a.cross(b).normalized()
        return n if (n.y < 0) == front else -n
    N = {key: normal(*key) for key in grid}
    lv = {key: bm.verts.new(FP[key] + N[key] * (0.001 - recess)) for key in grid}
    for i in range(nx):
        for k in range(nz):
            zc = z0 + (z1 - z0) * (k + 0.5) / nz
            frac = (zc - z0) / (z1 - z0)
            mi = next(m for top, m in lens_bands if frac <= top)
            if frame:
                # black surround (outer cells) and thin black dividers where the colour band changes (photos cAR/c24)
                fu = z0 + (z1 - z0) * (k + 1.5) / nz
                up = next(m for top, m in lens_bands if (fu - z0) / (z1 - z0) <= top) if k < nz - 1 else mi
                if i in (0, nx - 1) or k in (0, nz - 1) or up != mi:
                    mi = house_mat
            f = bm.faces.new((lv[i, k], lv[i + 1, k], lv[i + 1, k + 1], lv[i, k + 1]) if front else (lv[i, k], lv[i, k + 1], lv[i + 1, k + 1], lv[i + 1, k]))
            f.material_index = mi
    ring = [(i, 0) for i in range(nx)] + [(nx, k) for k in range(nz)] + [(i, nz) for i in range(nx, 0, -1)] + [(0, k) for k in range(nz, 0, -1)]
    if recess > 0:
        # lens set into the body: black wall from the surface edge down to the lens (photos: lamp sits in a black
        # surround, the body / pillar end standing proud round it)
        sv = {key: bm.verts.new(FP[key] + N[key] * 0.001) for key in set(ring)}
        for a, b in zip(ring, ring[1:] + ring[:1]):
            bm.faces.new((sv[a], lv[a], lv[b], sv[b]) if front else (sv[a], sv[b], lv[b], lv[a])).material_index = house_mat
    back = {}
    for key in grid:
        u = 2 * (key[0] / nx) - 1; w = 2 * (key[1] / nz) - 1
        d = depth * 0.45 + bowl * (1 - min(1.0, 0.75 * (u * u + w * w)))
        back[key] = bm.verts.new(FP[key] - N[key] * d)
    rim = {key: bm.verts.new(FP[key] - N[key] * depth * 0.45) for key in set(ring)}
    for a, b in zip(ring, ring[1:] + ring[:1]):
        bm.faces.new((lv[a], rim[a], rim[b], lv[b]) if front else (lv[a], lv[b], rim[b], rim[a])).material_index = house_mat
    for i in range(nx):
        for k in range(nz):
            bm.faces.new((back[i, k], back[i, k + 1], back[i + 1, k + 1], back[i + 1, k]) if front else (back[i, k], back[i + 1, k], back[i + 1, k + 1], back[i, k + 1])).material_index = refl_mat
    for a, b in zip(ring, ring[1:] + ring[:1]):
        bm.faces.new((rim[a], back[a], back[b], rim[b]) if front else (rim[a], rim[b], back[b], back[a])).material_index = refl_mat
    # bulb
    c = (nx // 2, nz // 2)
    r = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=6, radius=0.009)
    bmesh.ops.translate(bm, verts=r["verts"], vec=FP[c] - N[c] * (depth * 0.45 + bowl * 0.6))
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = refl_mat
    return bm


def mirror_wedge(bm, x0, x1, n=10):
    """Door-mirror housing as on the photos (cS side view: 17 cm long y -0.385..-0.555, 12 cm tall z 0.858..0.968,
    wedge - flat vertical rear face carrying the glass, top edge falling forward to a slanted nose; tip |x| 0.868 =
    BA MIR). Lofted outward along x from the door root; the section shrinks and rounds towards the tip.
    Materials 0 paint, 1 black, 2 glass. Photo frame (P() applies the sweep / DZ)."""
    prof = [(-0.388, 0.852), (-0.388, 0.968), (-0.460, 0.965), (-0.522, 0.950), (-0.548, 0.920), (-0.556, 0.880),
            (-0.542, 0.854)]
    cy = sum(p[0] for p in prof) / len(prof); cz = sum(p[1] for p in prof) / len(prof)
    rings = []
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        s = 1.0 - 0.06 * t - 0.15 * max(0.0, (t - 0.85) / 0.15) ** 2    # slight taper, rounded tip
        ring = [bm.verts.new(P(x, cy + (yy - cy) * s, cz + (zz - cz) * s)) for yy, zz in prof]
        rings.append(ring)
    m = len(prof)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(m):
            k1 = (k + 1) % m
            f = bm.faces.new((r0[k], r0[k1], r1[k1], r1[k]))
            f.material_index = 2 if k == 0 and 0 < (r0 is not rings[0]) else 0   # rear face: mirror glass
    bm.faces.new(rings[-1]).material_index = 0
    bm.faces.new(rings[0][::-1]).material_index = 1
    return rings


def mirror_pod(bm, x0, x1, yb, depth, zc, hz, n=12, m=20):
    """Door-mirror housing: superellipse sections lofted outward along x, flat rear (glass side, black rim),
    rounded front and tip; mirror glass inset in the rear face. Materials 0 paint, 1 black, 2 glass."""
    rings = []
    for i in range(n + 1):
        t = i / n
        tip = math.sqrt(max(0.0, 1 - ((t - 0.80) / 0.20) ** 2)) if t > 0.80 else 1.0
        inner = 0.70 + 0.30 * min(1.0, t / 0.35)
        az = hz * inner * (0.35 + 0.65 * tip)
        ay = depth * (0.55 + 0.45 * min(1.0, t / 0.5)) * (0.35 + 0.65 * tip)
        x = x0 + (x1 - x0) * t
        ring = []
        for k in range(m):
            a = 2 * math.pi * k / m
            c, s = math.cos(a), math.sin(a)
            yy = yb - ay * 0.5 * (1 - math.copysign(abs(c) ** 0.45, c))   # c=+1 -> rear plane yb, c=-1 -> front
            zz = zc + az * math.copysign(abs(s) ** 0.45, s)
            ring.append(bm.verts.new((x, yy, zz)))
        rings.append(ring)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(m):
            k1 = (k + 1) % m
            f = bm.faces.new((r0[k], r0[k1], r1[k1], r1[k]))
            ang = 2 * math.pi * (k + 0.5) / m
            f.material_index = 1 if math.cos(ang) > 0.55 else 0
            faces.append(f)
    tipc = bm.verts.new((x1 + 0.004, yb - depth * 0.2, zc))
    for k in range(m):
        bm.faces.new((rings[-1][k], rings[-1][(k + 1) % m], tipc)).material_index = 0
    bm.faces.new(rings[0][::-1]).material_index = 1
    g0 = [bm.verts.new(p) for p in ((x0 + 0.012, yb + 0.001, zc - hz * 0.70), (x1 - 0.020, yb + 0.001, zc - hz * 0.62),
                                     (x1 - 0.020, yb + 0.001, zc + hz * 0.62), (x0 + 0.012, yb + 0.001, zc + hz * 0.70))]
    bm.faces.new(g0).material_index = 2
    return {"glass": g0}



def surface_z():
    """z of the top body surface (BODY_shell / BODY_glass, mirror applied) at model (x, y): raycast from above."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    trees = []
    for n in ("BODY_shell", "BODY_glass"):
        o = bpy.data.objects.get(n)
        if o:
            trees.append((BVHTree.FromObject(o, dg), o.matrix_world.copy()))

    def z(x, y):
        best = None
        for t, M in trees:
            Mi = M.inverted()
            h = t.ray_cast(Mi @ Vector((x, y, 3.0)), (Mi.to_3x3() @ Vector((0, 0, -1))).normalized())
            if h[0] is not None:
                w = M @ h[0]
                best = w.z if best is None else max(best, w.z)
        return best if best is not None else 0.0
    return z


def box_between(bm, a, b, side, up, w, h, mi=0):
    """Box of width w / height h from point a to point b (side / up axes, derived if None)."""
    d = (b - a); L = d.length; d.normalize()
    if side is None:
        side = Vector((0, 0, 1)).cross(d)
        side = side.normalized() if side.length > 1e-6 else Vector((1, 0, 0))
        up = d.cross(side).normalized()
        if up.z < 0:
            up = -up
    vs = []
    for e in (a, b):
        for ss, uu in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            vs.append(bm.verts.new(e + side * (ss * w / 2) + up * (uu * h / 2)))
    for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        bm.faces.new([vs[i] for i in f]).material_index = mi
    return vs

def P(x, y, z):
    """Photo-frame point on/near the body -> model frame (end sweep + DZ)."""
    return Vector(g.to_model(x, y, z))


def build():
    paint, black, grey = bpy.data.materials["paint_gunmetal"], bpy.data.materials["trim_black"], bpy.data.materials["trim_grey"]
    glass = bpy.data.materials["glass_tint"]
    amber = bpy.data.materials["lamp_amber"]
    plate_w = mat_new("plate_white", (0.85, 0.85, 0.82, 1), "trim", rough=0.35)
    plate_y = mat_new("plate_yellow", (0.85, 0.66, 0.04, 1), "trim", rough=0.35)
    chrome = mat_new("chrome", (0.8, 0.8, 0.8, 1), "chrome", metallic=1.0, rough=0.08)
    mirror_glass = mat_new("mirror_glass", (0.6, 0.62, 0.65, 1), "chrome", metallic=1.0, rough=0.02)
    rubber = mat_new("rubber_black", (0.02, 0.02, 0.02, 1), "trim", rough=0.8)
    liner = mat_new("arch_liner", (0.012, 0.012, 0.012, 1), "trim", rough=0.9)
    steel_dark = mat_new("exhaust_steel", (0.22, 0.21, 0.20, 1), "trim", metallic=0.8, rough=0.5)
    out = []
    for n in ("MIRROR_L", "MIRROR_R", "HANDLE_L", "HANDLE_R", "FUEL_FLAP", "WIPERS_F", "WIPER_R", "SPOILER_HATCH", "SCUTTLE_VENT", "DRIP_RAILS", "PILLAR_TIP_L", "PILLAR_TIP_R",
              "PLATE_F", "PLATE_R", "EXHAUST_TIP", "EXHAUST_SILENCER", "GRILLE"):
        remove(n)

    # ---- door mirror (left): black triangular sail in the front corner of the door glass, body-colour housing
    # on a short neck; housing tip |x| 0.868 (BA MIR), side view y -0.38..-0.55, z 0.84..0.96 (cS rays)
    bm = bmesh.new()
    # black sail filling the window's front lower corner (cS / c22 photos: from the A-pillar foot along the belt
    # under the housing, its front edge up the A-pillar line to ~0.97)
    ys0, ys1, zb = -0.662, -0.420, 0.850
    xs = g.skin_x(-0.53, 0.85) - 0.02
    yt, zt = -0.628, 0.968
    sail = [bm.verts.new(P(xs, ys0, zb)), bm.verts.new(P(xs, ys1, zb)), bm.verts.new(P(xs - 0.012, yt, zt)),
            bm.verts.new(P(xs + 0.012, ys0, zb)), bm.verts.new(P(xs + 0.012, ys1, zb)), bm.verts.new(P(xs, yt, zt))]
    for f in ((0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)):
        bm.faces.new([sail[i] for i in f]).material_index = 1
    box(bm, (xs + 0.008, -0.545, 0.884), (0.712, -0.478, 0.926), 1)                     # mounting boss
    mirror_wedge(bm, x0=max(xs + 0.010, 0.712), x1=0.868)
    box(bm, (xs - 0.004, -0.556, 0.840), (0.735, -0.392, 0.856), 1)                     # black base under the housing
    bmesh.ops.translate(bm, verts=[v for v in bm.verts if v not in sail], vec=(0, 0, DZ))
    m = obj("MIRROR_L", bm, [paint, black, mirror_glass], bevel=0.010, segs=3)
    out += [m, mirrored(m, "MIRROR_R")]

    # ---- door handle (grey pull, 140 x 35 mm, BA HANDLE_F/R y 0.306..0.445, z ~0.766) + lock barrel
    bm = bmesh.new()
    xh = g.skin_x(0.375, 0.766)
    box(bm, (xh - 0.004, 0.300, 0.749 + DZ), (xh + 0.011, 0.447, 0.783 + DZ), 0)
    cyl(bm, (xh + 0.003, 0.452, 0.735 + DZ), (1, 0, 0), 0.009, 0.012, 16, 1)
    h = obj("HANDLE_L", bm, [black, chrome], bevel=0.004, segs=2)          # black pull (F400 PTF, cAR photo)
    out += [h, mirrored(h, "HANDLE_R")]

    # ---- door glass division bar (fixed front quarter light): cS rays onto the glass (2026-10-13), top
    # (0.536, -0.177, 1.187) under the frame, foot (0.619, -0.201, 0.848) at the waist seal; ~24 mm wide, black
    bm = bmesh.new()
    top, foot = Vector((0.536, -0.177, 1.197)), Vector((0.619, -0.201, 0.840))
    ax = (top - foot).normalized()
    nrm = Vector((ax.z, 0.0, -ax.x)).normalized()                     # outward, square to the bar in the x-z plane
    vs = []
    for e in (foot, top):
        for dy, dn in ((-0.012, -0.004), (0.012, -0.004), (0.012, 0.006), (-0.012, 0.006)):
            q = e + nrm * dn
            vs.append(bm.verts.new(P(q.x, q.y + dy, q.z)))
    for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        bm.faces.new([vs[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    db = obj("DOOR_BAR_L", bm, [black], bevel=0.002, segs=1)
    out += [db, mirrored(db, "DOOR_BAR_R")]

    # ---- side repeaters (BA SR 0.721, -0.789, 0.735): small amber oval
    bm = bmesh.new()
    xr = g.skin_x(-0.789, 0.735)
    r = bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((xr, -0.789, 0.735 + DZ)) @ Matrix.Diagonal((0.007, 0.022, 0.012, 1)), verts=r["verts"])
    s = obj("REPEATER_L", bm, [amber])
    out += [s, mirrored(s, "REPEATER_R")]

    # ---- fuel cap (right rear quarter, cS ray 0.8625, 0.5936; ~100 mm black cap in a shallow recess)
    bm = bmesh.new()
    xf = g.skin_x(0.8625, 0.5936)
    cyl(bm, (-(xf + 0.002), 0.8625, 0.5936 + DZ), (1, 0, 0), 0.050, 0.008, 32, 0)
    out.append(obj("FUEL_FLAP", bm, [black], bevel=0.003))

    # ---- number plates, 520 x 111 mm (UK, SOURCED). Front plate: front_end.json (build_front.py); rear on the
    # black panel
    bm = bmesh.new()
    yr = 1.7335 + 0.004
    box(bm, (-0.26, yr, 0.612), (0.26, yr + 0.006, 0.723), 0, Matrix.Translation((0, 0, DZ)))
    out.append(obj("PLATE_R", bm, [plate_y], bevel=0.002, smooth=False))

    # ---- lamp units in the shell openings: headlamp (clear, chrome reflector), indicator (amber), tail lamp
    # (red / amber / clear bands, photos cAR / c24), grille (black recess with 5 slats + GTE badge)
    hl, ind, gr, tl = g.ZN["headlamp"], g.ZN["indicator"], g.ZN["grille"], g.ZN["tail_lamp"]
    lens_clear = mat_new("lamp_glass_clear", (0.92, 0.93, 0.95, 1), "glass", rough=0.02)
    lens_amber = mat_new("lamp_glass_amber", (0.95, 0.42, 0.02, 1), "glass", rough=0.05)
    lens_red = mat_new("lamp_glass_red", (0.60, 0.02, 0.02, 1), "glass", rough=0.05)
    refl = mat_new("lamp_reflector", (0.85, 0.85, 0.85, 1), "chrome", metallic=1.0, rough=0.12)
    house = mat_new("lamp_housing", (0.02, 0.02, 0.02, 1), "trim", rough=0.6)
    for mm, a in ((lens_clear, 0.25), (lens_amber, 0.55), (lens_red, 0.6)):
        mm["ac_alpha"] = a; mm["ac_blend"] = 1; mm["ac_depth"] = 1; mm["ac_shader"] = "ksPerPixel"
    # front lamps, grille and bumper come from front_end.json (build_front.py) since 2026-10-12
    for n in ("HEADLAMP_L", "HEADLAMP_R", "GRILLE_L", "GRILLE_R"):   # legacy names only (INDICATOR_F_* come from build_front)
        remove(n)
    # frame 5 mm larger than the body opening all round, so its black surround covers the cut edge
    bm = lamp_unit("TAILLAMP_L", tl["x_in"] - 0.005, tl["x_out"] + 0.005, tl["z"][0] - 0.005, tl["z"][1] + 0.005,
                   [(0.20, 0), (0.45, 1), (1.01, 2)], False, 0.05, 0.02,
                   nx=12, nz=36, refl_mat=3, house_mat=4, frame=True, recess=0.014)
    u = obj("TAILLAMP_L", bm, [lens_clear, lens_amber, lens_red, refl, house], smooth=True)
    out += [u, mirrored(u, "TAILLAMP_R")]



    # ---- rear panel: grey bar above the plate (hatch release housing) with the lock, GTE letters (car's left).
    # cAR rays on the panel plane (2026-10-13): bar x +-0.32, z 0.750-0.789 with round ends, lock at its centre
    # (z 0.767); badge x 0.384-0.543, letters ~20 mm high (z ~0.762-0.782). Built through P() so the parts follow
    # the panel's plan sweep towards the corners.
    YF = 1.7335
    bm = bmesh.new()
    zc, hz, x1 = 0.7695, 0.0195, 0.32
    outline = []
    for k in range(9):                                            # right end (-x), then left end (+x)
        a_ = math.pi / 2 + math.pi * k / 8
        outline.append((-x1 + hz + hz * math.cos(a_), zc + hz * math.sin(a_)))
    for k in range(9):
        a_ = -math.pi / 2 + math.pi * k / 8
        outline.append((x1 - hz + hz * math.cos(a_), zc + hz * math.sin(a_)))
    layers = [(YF - 0.002, 1.0), (YF + 0.011, 1.0), (YF + 0.015, 0.80)]   # back, front edge, chamfered face
    rings = []
    for yy, sc in layers:
        ring = []
        for xx, zz in outline:
            ring.append(bm.verts.new(P(xx * (1 - (1 - sc) * 0.03), yy, zc + (zz - zc) * sc)))
        rings.append(ring)
    n = len(outline)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.faces.new(rings[-1]); bm.faces.new(rings[0][::-1])
    lock = cyl(bm, P(0.0, YF + 0.017, 0.767), (0, 1, 0), 0.009, 0.006, 16, 1)
    # GTE letters (seen from behind, the car's +x is on the viewer's left): strokes in (s across, t up) per letter
    st, hgt, wl, gap = 0.0045, 0.020, 0.045, 0.012
    letters = {"G": [(0, 1, 0, 0), (0, 1, 1, 1), (0, 0, 0, 1), (1, 1, 0, 0.5), (0.5, 1, 0.5, 0.5)],
               "T": [(0, 1, 1, 1), (0.5, 0.5, 0, 1)],
               "E": [(0, 0, 0, 1), (0, 1, 1, 1), (0, 0.8, 0.5, 0.5), (0, 1, 0, 0)]}
    xl = 0.543
    for ch in "GTE":
        for s0, s1, t0, t1 in letters[ch]:
            xa, xb = xl - s0 * (wl - st), xl - s1 * (wl - st) - st
            za, zb = 0.762 + t0 * (hgt - st), 0.762 + t1 * (hgt - st) + st
            vs = [bm.verts.new(P(xx, yy, zz)) for yy in (YF - 0.001, YF + 0.002) for xx, zz in ((xa, za), (xb, za), (xb, zb), (xa, zb))]
            for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
                bm.faces.new([vs[i] for i in f]).material_index = 1
        xl -= wl + gap
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    out.append(obj("REAR_PANEL_TRIM", bm, [grey, chrome], bevel=0.0))

    # ---- roof drip rails: body-colour rail along each roof edge just above the window frames, with the dark gutter
    # line over it (cS: continuous dark line ~2 cm above the frame tops from the A-pillar top to the C-pillar)
    bm = bmesh.new()
    ys = [-0.17 + (1.24 + 0.17) * i / 60 for i in range(61)]          # header corner .. ahead of the spoiler
    for sx in (1, -1):
        for prof, mi in (([(-0.003, -0.010), (0.004, -0.009), (0.006, 0.000), (0.004, 0.005), (-0.003, 0.006)], 0),
                         ([(0.000, 0.006), (0.0035, 0.0065), (0.0025, 0.0105), (-0.002, 0.011)], 1)):
            rows = []
            for y in ys:
                zr = g.interp(g.CANT, y) + 0.034                       # gutter 2.7-4.1 cm above the glass top (cS)
                tp = g.smoothstep((y + 0.17) / 0.10) * g.smoothstep((1.24 - y) / 0.10)   # ends taper into the skin
                rows.append([bm.verts.new(P(sx * ((g.skin_x(y, zr + dz_ * tp) or 0.5) + dx * tp - 0.003 * (1 - tp)), y,
                                            zr + dz_ * tp)) for dx, dz_ in prof])
            for r0, r1 in zip(rows, rows[1:]):
                for i in range(len(prof) - 1):
                    q = (r0[i], r1[i], r1[i + 1], r0[i + 1])
                    bm.faces.new(q if sx > 0 else q[::-1]).material_index = mi
            bm.faces.new(rows[0] if sx > 0 else rows[0][::-1]).material_index = mi
            bm.faces.new(rows[-1][::-1] if sx > 0 else rows[-1]).material_index = mi
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    out.append(obj("DRIP_RAILS", bm, [paint, black], smooth=True))

    # ---- roof visor (GTE spoiler): a moulding on the roof end overhanging the recessed tailgate glass. Trailing edge
    # underside at the centreline (y 1.400, z 1.275) triangulated c24 + cAR (ray gap 1 mm, 2026-10-13); ~17 mm thick
    # edge, black underside (photos c23/c24/redgte_25); spans the roof, the overhang pulled in at the ends where it
    # meets the fins. Profile (y, z) at the centreline, photo frame; the roof crown is added across x.
    # 2026-10-13 revision: flush with the roof line (the side photo shows no raised blade): trailing edge at y 1.375
    # (cS silhouette corner; the rear photos fix its height, 1.27), ~12 mm red edge face, black underside
    # 2026-10-13 rev 3: thicker lip - body-colour trailing face ~16 mm (c24 / cAR: red band above the dark underside),
    # slight kick at the edge, black underside back to the glass top
    prof = [(1.235, None, 0), (1.300, 1.2955, 0), (1.345, 1.2905, 0), (1.372, 1.2870, 0), (1.380, 1.2835, 0),
            (1.3815, 1.2740, 0), (1.379, 1.2680, 1), (1.360, 1.2620, 1), (1.320, 1.2650, 1), (1.270, 1.2850, 1)]
    bm = bmesh.new()
    n = 30; rows = []
    xmax = 0.49
    for k in range(n + 1):
        x = -xmax + 2 * xmax * k / n
        e = g.smoothstep((abs(x) - 0.40) / 0.12)                      # 0 across the glass, 1 at the roof corners
        pull = 0.060 * e                                              # overhang runs out into the pillar tops
        drop = g.top_z(1.30, abs(x)) - g.top_z(1.30, 0.0)
        ring = []
        for yy, zc, _ in prof:
            yv = yy if yy < 1.30 else yy - pull * (yy - 1.30) / 0.0815
            zr = g.top_z(min(yv, 1.36), abs(x))                       # roof surface under this point
            z = zr - 0.001 if zc is None else zc + drop
            z = z + (min(z, zr + 0.004) - z) * e if zc is not None and zc > 1.28 else z + (zr - 0.006 - z) * e * (zc is not None)
            if zc is None:
                z = zr - 0.002                                                  # leading edge buried in the roof
            ring.append(bm.verts.new(P(x, yv, z)))
        rows.append(ring)
    for a_, b_ in zip(rows, rows[1:]):
        for i in range(len(prof)):
            j = (i + 1) % len(prof)
            bm.faces.new((a_[i], a_[j], b_[j], b_[i])).material_index = prof[i][2]
    bm.faces.new(rows[0][::-1]).material_index = 1; bm.faces.new(rows[-1]).material_index = 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    out.append(obj("SPOILER_HATCH", bm, [paint, black], bevel=0.003, segs=2))

    # ---- wipers: pivots on the scuttle (centre pivot triangulated c20 + cCF at (0, -0.800, 0.933); driver-side
    # pivot from c20 at x -0.44, same 60 mm ahead of the screen base), RHD: both park towards the passenger side,
    # blades ~400 mm lying on the glass just above the base seal (body_profile scuttle_curve)
    surf = surface_z()
    yb = g.screen_base_y
    bm = bmesh.new()
    for xp, (xa, xb) in ((0.0, (0.035, 0.455)), (-0.44, (-0.425, -0.035))):
        pv = Vector((xp, yb(abs(xp)) - 0.060, 0.0))
        pv.z = surf(pv.x, pv.y)
        cyl(bm, pv + Vector((0, 0, 0.008)), (0, 0, 1), 0.016, 0.016, 16, 0)          # pivot housing
        ends = []
        for xe in (xa, xb):
            ye = yb(abs(xe)) + 0.040
            ends.append(Vector((xe, ye, surf(xe, ye) + 0.010)))
        a, b = ends
        d = (b - a).normalized(); side = Vector((0, 0, 1)).cross(d).normalized()
        up = d.cross(side).normalized()
        if up.z < 0:
            up = -up
        for c0, c1, w, h, lift in ((a, b, 0.009, 0.013, 0.0), (a + (b - a) * 0.08, b - (b - a) * 0.05, 0.020, 0.006, 0.010)):
            box_between(bm, c0 + up * lift, c1 + up * lift, side, up, w, h, 0)       # rubber blade + spine
        mid = (a + b) / 2 + up * 0.016
        box_between(bm, pv + Vector((0, 0, 0.016)), mid, None, None, 0.012, 0.007, 0)  # arm to the blade centre
    out.append(obj("WIPERS_F", bm, [rubber], bevel=0.002, smooth=False))

    # ---- scuttle vent louvres: row of short slots just ahead of the screen base seal, |x| < 0.46 (c20: continuous
    # row both sides, ~12 mm pitch; cCF), interrupted at the wiper pivots; washer jets at x +-0.175 (c20 + cCF)
    xl, d0, d1, pitch, wsl = g.SCU["louvre"]
    bm = bmesh.new()
    n = int(xl / pitch)
    for i in range(-n, n + 1):
        x = i * pitch
        if abs(x - 0.0) < 0.03 or abs(x + 0.44) < 0.03:
            continue
        t = Vector((-2 * g.SCU["k"] * x, 1.0, 0.0)).normalized()          # across the curve (fore-aft)
        sx = Vector((t.y, -t.x, 0.0))
        quad = []
        for dd, ss in ((-d1, -wsl / 2), (-d1, wsl / 2), (-d0, wsl / 2), (-d0, -wsl / 2)):
            q = Vector((x, yb(abs(x)), 0.0)) + t * dd + sx * ss
            q.z = surf(q.x, q.y) + 0.0008
            quad.append(bm.verts.new(q))
        bm.faces.new(quad)
    for sx_ in (1, -1):
        jx, jy = 0.175 * sx_, -0.811
        cyl(bm, Vector((jx, jy, surf(jx, jy) + 0.005)), (0, 0.4, 1), 0.006, 0.012, 12, 0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        if f.normal.z < 0 and len(f.verts) == 4 and abs(f.normal.z) > 0.9:
            f.normal_flip()
    out.append(obj("SCUTTLE_VENT", bm, [black], smooth=False))
    # rear wiper on the recessed tailgate glass (photos c24 / cAR): blade parked ~5 cm above the glass bottom from
    # the car's left (+x 0.40) to just right of centre, arm down to the pivot on the panel under the glass
    bm = bmesh.new()
    gh = bpy.data.objects.get("GLASS_HATCH")
    nG = Vector((0.0, 0.80, 0.60)); vG = Vector((0.0, -0.60, 0.80))
    def on_glass(x, v):
        base = Vector((x, 1.629, 0.905 + DZ)) + vG * v
        if gh:
            from mathutils.bvhtree import BVHTree
            dg = bpy.context.evaluated_depsgraph_get()
            t = BVHTree.FromObject(gh, dg)
            h = t.ray_cast(base + nG * 0.3, -nG, 0.6)
            if h[0] is not None:
                return h[0]
        return base
    a, b = on_glass(0.40, 0.055), on_glass(-0.04, 0.055)
    box_between(bm, a + nG * 0.008, b + nG * 0.008, None, None, 0.009, 0.012, 0)          # blade
    box_between(bm, a + nG * 0.017, b + nG * 0.017, None, None, 0.018, 0.005, 0)          # spine
    piv = Vector((-0.07, 1.672, 0.868 + DZ))
    cyl(bm, piv, (0, 0.8, 0.6), 0.014, 0.020, 16, 0)
    box_between(bm, piv + nG * 0.012, (a + b) * 0.5 + nG * 0.020, None, None, 0.011, 0.006, 0)   # arm
    out.append(obj("WIPER_R", bm, [rubber], bevel=0.002, smooth=False))

    # ---- exhaust: rear silencer under the boot floor and a plain steel tailpipe tucked under the valance on the
    # car's left, angled outward (cAR: pipe end ~(0.48, 1.63, 0.25) - ray fixed by the valance height, ESTIMATE)
    bm = bmesh.new()
    box(bm, (0.08, 1.40, 0.205), (0.50, 1.58, 0.315), 0, Matrix.Translation((0, 0, DZ)))
    out.append(obj("EXHAUST_SILENCER", bm, [rubber], bevel=0.03, segs=3))
    bm = bmesh.new()
    ax = Vector((0.26, 0.97, -0.03)).normalized()
    cyl(bm, Vector((0.48, 1.63, 0.25 + DZ)) - ax * 0.07, ax, 0.022, 0.14, 24, 0, cap=False)
    out.append(obj("EXHAUST_TIP", bm, [steel_dark]))

    # ---- wheel-arch liners: black tub inside each arch cut (the Boolean on the open shell leaves no wall),
    # reaching out to just inside the skin so the inner shell is never seen through the arch
    for key in ("front", "rear"):
        # tub: from the lip (3 mm inside the skin) it opens out 35 mm by 25 mm in and 80 mm at x 0.50, away from the
        # wheel centre - the wheelhouse is taller than the lip opening, so the tyre (top ~ lip top) clears it
        cy, cz = g.arch_centre(key)
        lip = [(y, z) for y, z in g.arch_poly(key) if z > 0.18]
        dense = []
        for (y0, z0), (y1, z1) in zip(lip, lip[1:]):
            n_ = max(1, int(math.hypot(y1 - y0, z1 - z0) / 0.02))
            dense += [(y0 + (y1 - y0) * k / n_, z0 + (z1 - z0) * k / n_) for k in range(n_)]
        dense.append(lip[-1])
        bm = bmesh.new(); rows = []
        for y, z in dense:
            zp = z - DZ
            x = 0.74; yu = y
            for _ in range(6):
                yu = y - g.sweep(x, yu, zp)
                xs = g.skin_x(yu, zp)
                x = (xs if xs else 0.74)
            xo = min(x - 0.003, 0.785)
            dv = Vector((0.0, y - cy, z - cz)); dv = dv.normalized() if dv.length > 1e-6 else Vector((0, 0, 1))
            dv.z = max(dv.z, 0.0)                                  # grow up / sideways, never down
            ring = []
            for xx, off in ((xo, 0.0), (xo - 0.025, 0.035), (0.50, 0.080)):
                ring.append(bm.verts.new((xx, y + dv.y * off, z + dv.z * off)))
            rows.append(ring)
        for r0, r1 in zip(rows, rows[1:]):
            for i in range(2):
                bm.faces.new((r0[i], r1[i], r1[i + 1], r0[i + 1]))
        c = bm.verts.new((0.50, cy, cz + 0.05))
        for r0, r1 in zip(rows, rows[1:]):
            bm.faces.new((c, r1[2], r0[2]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        # normals must face the wheel (into the opening): check one face of the outer band
        f0 = next(iter(bm.faces))
        if f0.normal.x > 0.5:
            bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        lo = obj("ARCH_LINER_%s_L" % key, bm, [liner], smooth=True)
        out += [lo, mirrored(lo, "ARCH_LINER_%s_R" % key)]

    # ---- arch cutters carry the black liner material into the Boolean result
    for k in ("CUT_arch_front", "CUT_arch_rear"):
        co = bpy.data.objects.get(k)
        if co:
            co.data.materials.clear(); co.data.materials.append(liner)
    body = bpy.data.objects.get("BODY_shell")
    if body:
        if liner.name not in [m.name for m in body.data.materials if m]:
            body.data.materials.append(liner)
        for md in body.modifiers:
            if md.type == "BOOLEAN":
                md.material_mode = "TRANSFER"
        sol = body.modifiers.get("Inner")
        if sol:
            sol.use_even_offset = False
    return [o.name for o in out]


if __name__ == "__main__":
    print(build())

"""90s-DTM aero kit for the Escort Mk2 model (runs inside Blender on blender/escort_aero.blend, after
escort_scene.load_all()). Repeatable: build() deletes the previous AERO parts and makes them again.

Parts (Blender space: metres, car faces -Y, Z up, +X = car's left, model origin = the kn5's):
  AERO_wing        inverted cambered main plane + Gurney, parented to the boot lid node hood_trunk (opens with it)
  AERO_endplates   flat plates at the wing tips                                     } satin black trim
  AERO_wing_stalks two pedestal stalks from the lid to the wing                     } (the car's own window-trim
  AERO_splitter    flat blade under the air dam                                     }  material, Material #166GG45)
  AERO_rear_lip    drop lip along the rear valance with an exhaust notch + 4 strakes}
  AERO_air_dam     body-colour dam grown down from the valance's real lower edge (paint material #25DQW)
  AERO_skirts      small body-colour sill lips between the arches
Lessons carried over from the Sunbeam: every add-on starts ON a traced body edge/surface and is pinned ~1 mm into
the paint; body-colour parts use ONE clean paint UV; the splitter stays well clear of the front tyres at full lock.
Measured body facts (2026-10-05, from the model): valance lower edge z 0.010, y -1.778 centre / -1.716 at x 0.64,
turning up the arch from x 0.67; sill rolls under below z ~0.005 (x 0.66-0.69 there); boot lid z 0.70 (y 1.80) ->
0.60 (y 2.08), rear edge y ~2.10; rear valance edge z 0.083-0.094 at y 2.04-2.02; exhaust tip x 0.31-0.40.
Estimated ground (model wheel nodes, tyre r 0.268, v20 ~25 mm lower than the mod): -0.082 at the front valance,
-0.12 mid-sill, -0.17 at the rear valance - recheck in game.
"""
import json
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

PAINT, TRIM = "Material #25DQW", "Material #166GG45"      # kn5 material names
COLLECTION = "AERO"
GROUND_FRONT, GROUND_MID, GROUND_REAR = -0.082, -0.12, -0.17   # estimates (see above)

# ---- design values -------------------------------------------------------------------------------------------
WING = dict(half_span=0.675, chord=0.26, le_y=1.865, mid_z=0.905, incidence=10.0, camber=0.06, camber_pos=0.40,
            thickness=0.12, gurney=0.015, gurney_t=0.003, stations=36)
ENDPLATE = dict(t=0.006, ahead=0.035, behind=0.025, above=0.055, below=0.075)
STALK = dict(x=0.38, t=0.008, top=(0.30, 0.72), base=(1.885, 2.075), sink=0.003)   # top = chord fractions
DAM = dict(drop=0.030, lean=0.008, t=0.012, x_full=0.58, x_end=0.69, pin=0.004)
SPLITTER = dict(proud=0.045, t=0.006, x_full=0.50, x_end=0.60, under=0.030)
# v23 (Nik: "bring the side skirt/flare along to seamlessly join the wheel arch trim"): the skirt runs the full sill,
# from the front arch's opening (y -0.874 at sill height) to the rear arch's rounded front corner (+0.835), 2-3 mm
# inside each, at full section (no fade) - its outer face follows the flares' 1.5-4 cm outward kick into the arches
# (sections every 5 mm near the ends). v21: -0.80..0.80 tapering to nothing over 9 cm, short of both arches.
SKIRT = dict(y_start=-0.872, y_end=0.832, taper=0.0, attach_z=0.045, bottom_z=-0.018, proud=0.004, depth=0.050,
             end_dense=0.08)
REAR_LIP = dict(drop=0.045, kick=0.015, t=0.006, x_full=0.50, x_end=0.60, notch=(0.28, 0.46), notch_ramp=0.02)
STRAKES = dict(x=(-0.52, -0.16, 0.16, 0.52), t=0.005, y_front=1.92, top_z=0.095)


# ---- helpers -------------------------------------------------------------------------------------------------
def main_scene():
    return bpy.data.scenes["Scene"]


def material(kname):
    for n in json.loads(main_scene()["kn5_materials"]):
        m = bpy.data.materials[n]
        if json.loads(m["kn5_def"])["name"] == kname:
            return m
    raise KeyError(kname)


def kn5_obj(name, typ="MESH"):
    return next(o for o in main_scene().objects if o.get("kn5_name") == name and o.type == typ)


def root():
    return next(o for o in main_scene().objects if o.get("kn5_root"))


def world_verts(o):
    me = o.data
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co)
    m = np.array(o.matrix_world)
    return co.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]


def paint_bvh():
    """World-space BVH of the body paint (body shell, front wings/valance, bonnet, boot lid, door skins)."""
    mat = material(PAINT)
    bm = bmesh.new()
    for o in main_scene().objects:
        if o.type == "MESH" and o.data.materials and o.data.materials[0] == mat:
            t = o.data.copy(); t.transform(o.matrix_world); bm.from_mesh(t); bpy.data.meshes.remove(t)
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    return tree


def pick_uv(mat, near):
    """UV of the corner nearest `near` on any main-scene mesh using `mat`: one clean texel for a whole part
    (nearest-vertex UVs per new vertex picked up stray texels on the Sunbeam - zebra stripes)."""
    best = None
    for o in main_scene().objects:
        if o.type != "MESH" or not o.data.materials or o.data.materials[0] != mat or not len(o.data.loops):
            continue                                 # (v24's door split left a few emptied original meshes)
        me = o.data
        co = world_verts(o)
        lv = np.empty(len(me.loops), np.int64); me.loops.foreach_get("vertex_index", lv)
        d = np.linalg.norm(co[lv] - np.array(near), axis=1)
        i = int(d.argmin())
        if best is None or d[i] < best[0]:
            u = me.uv_layers.active.data[i].uv
            best = (float(d[i]), (u[0], u[1]), o.get("kn5_name"))
    return best


def smoothstep_down(v, full, end):
    """1 up to |v| = full, easing to 0 at |v| = end."""
    u = np.clip((np.abs(v) - full) / (end - full), 0.0, 1.0)
    return 1.0 - (3 * u ** 2 - 2 * u ** 3)


def loft(sections, caps=True):
    """Closed-loop sections (same point count) -> (verts, faces): quads between neighbours + end caps."""
    k = len(sections[0])
    verts = [tuple(p) for s in sections for p in s]
    faces = []
    for i in range(len(sections) - 1):
        a, b = i * k, (i + 1) * k
        for j in range(k):
            jn = (j + 1) % k
            faces.append((a + j, a + jn, b + jn, b + j))
    if caps:
        faces.append(tuple(range(k - 1, -1, -1)))
        last = (len(sections) - 1) * k
        faces.append(tuple(range(last, last + k)))
    return verts, faces


def extrude_x(outline_yz, x0, x1):
    """A flat plate: outline in the YZ plane, from x0 to x1."""
    return loft([[(x0, y, z) for y, z in outline_yz], [(x1, y, z) for y, z in outline_yz]])


def merge(*parts):
    verts, faces = [], []
    for v, f in parts:
        o = len(verts)
        verts += list(v)
        faces += [tuple(i + o for i in face) for face in f]
    return verts, faces


def mirror_x(part):
    v, f = part
    return [(-x, y, z) for x, y, z in v], [tuple(reversed(face)) for face in f]


def make_obj(name, part, mat, uv, parent, sharp_deg=35.0):
    """Mesh object in world coordinates under `parent` (kept in place); outward normals; faces smooth with
    edges sharper than sharp_deg split; every corner on the single texel `uv`; material `mat`."""
    old = bpy.data.objects.get(name)
    if old is not None:
        bpy.data.objects.remove(old)
    me = bpy.data.meshes.get(name)
    if me is not None:
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(name)
    verts, faces = part
    me.from_pydata(verts, [], faces)
    me.validate(clean_customdata=False)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        if not e.is_manifold or (len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(sharp_deg)):
            e.smooth = False
    bm.to_mesh(me); bm.free()
    uvl = me.uv_layers.new(name="UVMap")
    uvl.data.foreach_set("uv", [c for _ in range(len(me.loops)) for c in uv])
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    col = bpy.data.collections.get(COLLECTION)
    if col is None:
        col = bpy.data.collections.new(COLLECTION)
        main_scene().collection.children.link(col)
    col.objects.link(ob)
    ob.parent = parent
    ob.matrix_parent_inverse = parent.matrix_world.inverted()
    ob["aero_part"] = True
    return ob


# ---- rear wing -----------------------------------------------------------------------------------------------
def wing_section():
    """Inverted NACA 4-digit section (camber down = downforce), TE raised by the incidence. Returns the closed
    loop [(y, z)] (TE upper -> LE -> TE lower) and its lower surface as a callable z(y)."""
    w = WING
    c, a = w["chord"], math.radians(w["incidence"])
    m, p, t = w["camber"], w["camber_pos"], w["thickness"]
    xc = (1 - np.cos(np.linspace(0, math.pi, w["stations"]))) / 2
    yt = 5 * t * (0.2969 * np.sqrt(xc) - 0.1260 * xc - 0.3516 * xc ** 2 + 0.2843 * xc ** 3 - 0.1015 * xc ** 4)
    yc = np.where(xc < p, m / p ** 2 * (2 * p * xc - xc ** 2), m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * xc - xc ** 2))
    dyc = np.where(xc < p, 2 * m / p ** 2 * (p - xc), 2 * m / (1 - p) ** 2 * (p - xc))
    th = np.arctan(dyc)
    up = np.stack([xc - yt * np.sin(th), yc + yt * np.cos(th)], 1)
    lo = np.stack([xc + yt * np.sin(th), yc - yt * np.cos(th)], 1)
    loop = np.vstack([up[::-1], lo[1:]]) * c
    loop[:, 1] *= -1                                         # invert: camber downwards
    z_le = w["mid_z"] - c / 2 * math.sin(a)
    ys = w["le_y"] + loop[:, 0] * math.cos(a) - loop[:, 1] * math.sin(a)
    zs = z_le + loop[:, 0] * math.sin(a) + loop[:, 1] * math.cos(a)
    pts = list(zip(ys, zs))
    n = w["stations"]
    halves = [pts[:n], pts[n - 1:]]
    lower = min(halves, key=lambda h: np.mean([q[1] for q in h]))
    lower = sorted(lower)
    ly, lz = np.array([q[0] for q in lower]), np.array([q[1] for q in lower])
    return pts, (lambda y: float(np.interp(y, ly, lz))), (c, a, z_le)


def build_wing(lid_bvh, trim, uv, lid_node):
    w, e, s = WING, ENDPLATE, STALK
    sec, z_lower, (c, a, z_le) = wing_section()
    hs = w["half_span"]
    main = loft([[(-hs, y, z) for y, z in sec], [(hs, y, z) for y, z in sec]])
    # Gurney: perpendicular to the chord at the trailing edge, on the pressure (upper) side
    te = Vector((0, w["le_y"] + c * math.cos(a), z_le + c * math.sin(a)))
    perp = Vector((0, -math.sin(a), math.cos(a))); along = Vector((0, math.cos(a), math.sin(a)))
    g0 = te - along * w["gurney_t"] - perp * 0.002
    gq = [g0, g0 + along * w["gurney_t"], g0 + along * w["gurney_t"] + perp * (w["gurney"] + 0.002),
          g0 + perp * (w["gurney"] + 0.002)]
    gurney = extrude_x([(q.y, q.z) for q in gq], -hs, hs)
    wing = make_obj("AERO_wing", merge(main, gurney), trim, uv, lid_node)

    ys, zs = [q[0] for q in sec], [q[1] for q in sec]
    y0, y1 = min(ys) - e["ahead"], max(ys) + e["behind"]
    zt, zb = max(zs) + w["gurney"] + e["above"] - 0.03, min(zs) - e["below"]
    outline = [(y0, zt), (y1, zt), (y1, zb), (y0 + 0.07, zb), (y0, zb + 0.05)]
    plate = extrude_x(outline, hs - 0.001, hs + e["t"])
    plates = make_obj("AERO_endplates", merge(plate, mirror_x(plate)), trim, uv, lid_node)

    # pedestal stalks: top sunk 4 mm into the wing's lower surface, base 3 mm into the boot lid
    def lid_z(x, y):
        hit = lid_bvh.ray_cast(Vector((x, y, 2.0)), Vector((0, 0, -1)), 3.0)
        if hit[0] is None:
            raise RuntimeError(f"stalk base off the boot lid at x {x:.3f} y {y:.3f}")
        return hit[0].z
    x = s["x"]
    ty = [w["le_y"] + c * f * math.cos(a) for f in np.linspace(s["top"][0], s["top"][1], 8)]
    top = [(y, z_lower(y) + 0.004) for y in ty]
    b0, b1 = s["base"]
    outline = [(b0, lid_z(x, b0) - s["sink"]), (b1, lid_z(x, b1) - s["sink"])] + top[::-1]
    stalk = extrude_x(outline, x - s["t"] / 2, x + s["t"] / 2)
    stalks = make_obj("AERO_wing_stalks", merge(stalk, mirror_x(stalk)), trim, uv, lid_node)
    return {"wing": wing, "endplates": plates, "stalks": stalks,
            "te": (round(te.y, 3), round(te.z, 3)), "le_y": w["le_y"], "lowest": round(min(zs), 3),
            "highest": round(max(zs), 3), "stalk_base_z": [round(outline[0][1], 3), round(outline[1][1], 3)]}


# ---- front air dam + splitter --------------------------------------------------------------------------------
def boundary_points(o, test):
    bm = bmesh.new(); bm.from_mesh(o.data)
    m = o.matrix_world
    pts = set()
    for e in bm.edges:
        if len(e.link_faces) == 1:
            for v in e.verts:
                c = m @ v.co
                if test(c):
                    pts.add((round(abs(c.x), 4), round(c.y, 4), round(c.z, 4)))
    bm.free()
    return np.array(sorted(pts))


def smooth_path(a, xs, pick, window=0.02):
    """Robust path through boundary points a (|x|, y, z): per station the median of the points within
    `window` chosen by pick ('min_z' for a lower edge, 'max_y' for a rear edge), then a light 3-tap smooth."""
    ys, zs = [], []
    for x in xs:
        s = a[np.abs(a[:, 0] - x) < window]
        if len(s) == 0:
            ys.append(np.nan); zs.append(np.nan); continue
        if pick == "max_y":
            s = s[s[:, 1] >= s[:, 1].max() - 0.004]
        else:
            s = s[s[:, 2] <= s[:, 2].min() + 0.002]
        ys.append(np.median(s[:, 1])); zs.append(np.median(s[:, 2]))
    ys, zs = np.array(ys), np.array(zs)
    ok = ~np.isnan(ys)
    ys, zs = np.interp(xs, xs[ok], ys[ok]), np.interp(xs, xs[ok], zs[ok])
    k = np.array([0.25, 0.5, 0.25])
    ys[1:-1] = np.convolve(ys, k, "valid"); zs[1:-1] = np.convolve(zs, k, "valid")
    return ys, zs


def full_path(xs_half, ys, zs):
    """Mirror a half path (x >= 0) to the full width, ordered by x, with plan normals n = (t.y, -t.x)."""
    x = np.concatenate([-xs_half[:0:-1], xs_half]); y = np.concatenate([ys[:0:-1], ys]); z = np.concatenate([zs[:0:-1], zs])
    t = np.stack([np.gradient(x), np.gradient(y)], 1)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    n = np.stack([t[:, 1], -t[:, 0]], 1)
    return x, y, z, n


def front_edge():
    a = boundary_points(kn5_obj("fenders_a_SUB2"),
                        lambda c: c.y < -1.5 and ((c.z < 0.013 and abs(c.x) < 0.668) or (abs(c.x) >= 0.668 and c.z < 0.08)))
    xs = np.concatenate([np.linspace(0, 0.60, 31), np.linspace(0.61, DAM["x_end"], 9)])
    ys, zs = smooth_path(a, xs, "min_z", window=0.012)
    return full_path(xs, ys, zs)


def edge_lip(x, y, z, n, f, drop, lean, t, pin):
    """Sections of a lip hanging from a panel's lower edge: attach point pinned into the paint, front face from
    the edge down `drop`*f leaning `lean`*f along n, thickness t, back face returning up behind the panel."""
    secs = []
    for i in range(len(x)):
        P = Vector((x[i], y[i], z[i])); N = Vector((n[i][0], n[i][1], 0.0)); U = Vector((0, 0, 1))
        a = P + U * pin - N * 0.001
        a2 = P + N * 0.0005
        b = P + N * (0.0005 + lean * f[i]) - U * (drop * f[i] + 0.0005)
        c = b - N * t
        d = P - N * (t + 0.004) + U * 0.010
        secs.append([a, a2, b, c, d])
    return loft(secs)


def build_front(paint, puv, trim, tuv, parent):
    x, y, z, n = front_edge()
    f = smoothstep_down(x, DAM["x_full"], DAM["x_end"])
    dam = make_obj("AERO_air_dam", edge_lip(x, y, z, n, f, DAM["drop"], DAM["lean"], DAM["t"], DAM["pin"]),
                   paint, puv, parent)
    sp = SPLITTER
    keep = np.abs(x) <= sp["x_end"] + 1e-9
    fs = smoothstep_down(x[keep], sp["x_full"], sp["x_end"])
    z_top = float(np.max(z[keep])) - DAM["drop"] + 0.0005          # pinned into the dam's bottom
    secs = []
    for xi, yi, ni, fi in zip(x[keep], y[keep], n[keep], fs):
        N = Vector((ni[0], ni[1], 0)); P = Vector((xi, yi, 0))
        front = P + N * (DAM["lean"] + 0.0005 + sp["proud"] * fi)
        back = P - N * (DAM["t"] + sp["under"])
        secs.append([Vector((front.x, front.y, z_top)), Vector((front.x, front.y, z_top - sp["t"])),
                     Vector((back.x, back.y, z_top - sp["t"])), Vector((back.x, back.y, z_top))])
    blade = make_obj("AERO_splitter", loft(secs), trim, tuv, parent)
    return {"air_dam": dam, "splitter": blade, "edge_y_centre": round(float(y[len(y) // 2]), 3),
            "dam_bottom_z": round(float(z[len(z) // 2]) - DAM["drop"], 3), "splitter_bottom_z": round(z_top - sp["t"], 3)}


# ---- side skirts ---------------------------------------------------------------------------------------------
def build_skirts(bvh, paint, puv, parent):
    s = SKIRT
    ys = np.linspace(s["y_start"], s["y_end"], 61)
    d = s.get("end_dense", 0.0)
    if d:                                         # the flares kick out fast near the arches: sample every 5 mm there
        ys = np.unique(np.round(np.concatenate([ys, np.arange(s["y_start"], s["y_start"] + d, 0.005),
                                                np.arange(s["y_end"] - d, s["y_end"], 0.005), [s["y_end"]]]), 5))
    if s["taper"] > 0:
        f = smoothstep_down(ys - (s["y_start"] + s["y_end"]) / 2, (s["y_end"] - s["y_start"]) / 2 - s["taper"],
                            (s["y_end"] - s["y_start"]) / 2)
    else:
        f = np.ones_like(ys)
    za = s["attach_z"]
    hits = []
    for y in ys:      # sill surface x; the odd ray slips through a seam between panels - interpolated
        hs = [bvh.ray_cast(Vector((1.5, y + dy, za)), Vector((-1, 0, 0)), 1.2)[0] for dy in (0.0, -0.004, 0.004)]
        hs = [h.x for h in hs if h is not None]
        hits.append(max(hs) if hs else np.nan)
    hits = np.array(hits); ok = ~np.isnan(hits)
    if ok.sum() < len(ys) * 0.8:
        raise RuntimeError("sill not found along most of the skirt")
    xs = np.interp(ys, ys[ok], hits[ok])
    secs = []
    for y, fi, xa in zip(ys, f, xs):
        zb = za - (za - s["bottom_z"]) * fi
        pr = s["proud"] * fi
        secs.append([(xa - 0.0015, y, za + 0.004), (xa + 0.0005, y, za), (xa + 0.0005 + pr, y, zb + 0.004 * fi),
                     (xa + 0.0005 + pr * 0.5, y, zb), (xa - s["depth"], y, zb), (xa - s["depth"], y, zb + 0.002 + 0.03 * fi)])
    side = loft(secs)
    ob = make_obj("AERO_skirts", merge(side, mirror_x(side)), paint, puv, parent)
    return {"skirts": ob, "sill_x": (round(min(xs), 3), round(max(xs), 3)), "bottom_z": s["bottom_z"]}


# ---- rear lip + strakes --------------------------------------------------------------------------------------
def rear_edge():
    a = boundary_points(kn5_obj("body_a_SUB1"), lambda c: c.y > 1.99 and c.z < 0.1 and abs(c.x) < 0.64)
    xs = np.linspace(0, REAR_LIP["x_end"], 31)
    ys, zs = smooth_path(a, xs, "max_y", window=0.03)
    x, y, z, n = full_path(xs, ys, zs)
    return x, y, z, -n                       # outward = rearwards


def build_rear(trim, tuv, parent):
    r, st = REAR_LIP, STRAKES
    x, y, z, n = rear_edge()
    f = smoothstep_down(x, r["x_full"], r["x_end"])
    lo, hi = r["notch"]
    parts, segs = [], [(x < lo), (x > hi)]
    for seg in segs:
        # each side of the exhaust notch tapers to nothing at the notch
        g = np.clip(np.minimum(np.abs(x - lo), np.abs(x - hi)) / r["notch_ramp"], 0, 1)
        g = np.where((x > lo) & (x < hi), 0.0, 3 * g ** 2 - 2 * g ** 3)
        idx = np.where(seg)[0]
        parts.append(edge_lip(x[idx], y[idx], z[idx], n[idx], (f * g)[idx], r["drop"], r["kick"], r["t"], 0.004))
    lip = make_obj("AERO_rear_lip", merge(*parts), trim, tuv, parent)
    fins = []
    for xi in st["x"]:
        ye = float(np.interp(xi, x, y)); ze = float(np.interp(xi, x, z))
        yb = ye - r["t"] - 0.002
        zb = ze - r["drop"] * float(smoothstep_down(np.array([xi]), r["x_full"], r["x_end"])[0]) + 0.002
        outline = [(st["y_front"], st["top_z"]), (yb, st["top_z"]), (yb, zb), (st["y_front"] + 0.04, st["top_z"] - 0.025)]
        fins.append(extrude_x(outline, xi - st["t"] / 2, xi + st["t"] / 2))
    strakes = make_obj("AERO_strakes", merge(*fins), trim, tuv, parent)
    mid = len(x) // 2
    return {"rear_lip": lip, "strakes": strakes, "edge": (round(float(y[mid]), 3), round(float(z[mid]), 3)),
            "lip_bottom_z": round(float(z[mid]) - r["drop"], 3)}


# ---- build + checks ------------------------------------------------------------------------------------------
FRONT_TYRE = dict(x=1.3345 / 2, y=-1.218, hub_z=0.148 + 0.025, r=0.268, w=0.245, lock=30.0)   # v20 physics


def build():
    sc = main_scene()
    bpy.context.window.scene = sc
    for o in [o for o in bpy.data.objects if o.get("aero_part")]:
        bpy.data.objects.remove(o)
    paint, trim = material(PAINT), material(TRIM)
    puv = pick_uv(paint, (0.0, 1.90, 0.67))          # boot lid centre: open, fully lit paint
    tuv = pick_uv(trim, (0.70, 0.30, 0.75))          # window surround trim
    bvh = paint_bvh()
    out = {"paint_uv": puv, "trim_uv": tuv}
    rt = root()
    out["wing"] = build_wing(bvh, trim, tuv[1], kn5_obj("hood_trunk", "EMPTY"))
    out["front"] = build_front(paint, puv[1], trim, tuv[1], rt)
    out["skirts"] = build_skirts(bvh, paint, puv[1], rt)
    out["rear"] = build_rear(trim, tuv[1], rt)
    bpy.context.view_layer.update()
    bpy.ops.wm.save_mainfile()
    clean = lambda d: {k: (clean(v) if isinstance(v, dict) else v) for k, v in d.items()
                       if not isinstance(v, bpy.types.Object)}
    return clean(out)


def parts():
    return [o for o in main_scene().objects if o.get("aero_part")]


def check():
    """Numbers to judge the parts by: size, lowest point vs estimated ground, symmetry, front tyre clearance at
    full lock, and how far each part sits from the paint it is attached to."""
    rep = {}
    bvh = paint_bvh()
    ft = FRONT_TYRE
    for o in parts():
        v = world_verts(o)
        mn, mx = v.min(0), v.max(0)
        ground = np.interp(v[:, 1], [-1.8, 0.0, 2.05], [GROUND_FRONT, GROUND_MID, GROUND_REAR])
        clear = float((v[:, 2] - ground).min())
        sym = float(abs(mn[0] + mx[0]))
        # front tyre: plan rectangle at each vertex height, swept -lock..+lock, inflated 10 mm
        tyre_gap = None
        near = v[(np.abs(np.abs(v[:, 0]) - ft["x"]) < 0.35) & (np.abs(v[:, 1] - ft["y"]) < 0.6)]
        if len(near):
            gaps = []
            for p in near:
                dz = p[2] - ft["hub_z"]
                if abs(dz) >= ft["r"]:
                    continue
                half_len = math.sqrt(ft["r"] ** 2 - dz ** 2)
                for ang in np.radians(np.arange(-ft["lock"], ft["lock"] + 0.1, 5)):
                    dx, dy = abs(p[0]) - ft["x"], p[1] - ft["y"]
                    u = dx * math.sin(ang) + dy * math.cos(ang)        # along the wheel's heading
                    w = dx * math.cos(ang) - dy * math.sin(ang)        # across
                    gaps.append(max(abs(u) - half_len, abs(w) - ft["w"] / 2))
            tyre_gap = round(min(gaps), 3) if gaps else None
        # attachment: distance of the part's closest vertex from the paint (should be ~0 for attached parts)
        d = min((bvh.find_nearest(Vector(p))[3] for p in v[:: max(1, len(v) // 400)]), default=None)
        rep[o.name] = {"tris": sum(len(p.vertices) - 2 for p in o.data.polygons), "min": [round(float(a), 3) for a in mn],
                       "max": [round(float(a), 3) for a in mx], "ground_clear": round(clear, 3), "asym": round(sym, 4),
                       "front_tyre_gap": tyre_gap, "nearest_paint": round(d, 4) if d is not None else None}
    return rep

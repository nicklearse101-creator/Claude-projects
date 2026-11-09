"""v25 model work (Nik, 6 Oct) - see docs/plans/2026-10-06-v25-plan.md. Runs inside Blender on blender/escort_aero.blend
after the v24 steps (README). Blender: +X = car's left, +Y = rear, Z up.

    import v25
    v25.treadplate_material()           # textures -> blender/textures_v25, kn5 material "treadplate_steel"
    v25.door_boxes()                    # door ends closed (body colour), inner skins in treadplate, handles
"""
import json
import math
import os
import struct

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

import build_aero as ba
import build_rear_dwb as r

TEX_DIR = os.path.join(os.path.dirname(bpy.data.filepath), "textures_v25")
TREAD = dict(name="treadplate_steel", size=512, cells=4, tile=0.10,    # 4 x 4 lentil cells per 0.10 m tile (25 mm pitch)
             lentil_len=0.80, lentil_w=0.20, bump_px=7.0,
             steel=0.47, tops=0.13, valleys=-0.07, noise=0.025,
             props=dict(ksAmbient=0.40, ksDiffuse=0.42, ksSpecular=0.18, ksSpecularEXP=16.0))   # dull, not polished
PAINT_UV = (0.857, 0.398)                                       # build_aero's body-colour texel


# ---- treadplate --------------------------------------------------------------------------------------------------
def _dds(levels):
    """Uncompressed BGRA DDS with a full mip chain. levels: list of HxWx4 uint8 (RGBA), largest first."""
    h, w = levels[0].shape[:2]
    flags = 0x1 | 0x2 | 0x4 | 0x8 | 0x1000 | 0x20000
    head = struct.pack("<4s7I44s", b"DDS ", 124, flags, h, w, w * 4, 0, len(levels), b"\0" * 44)
    pf = struct.pack("<8I", 32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    caps = struct.pack("<5I", 0x1000 | 0x8 | 0x400000, 0, 0, 0, 0)
    body = b"".join(np.ascontiguousarray(l[..., [2, 1, 0, 3]]).tobytes() for l in levels)
    return head + pf + caps + body


def _mips(img):
    out = [img]
    a = img.astype(np.float64)
    while a.shape[0] > 1:
        a = (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]) / 4
        out.append(np.clip(np.round(a), 0, 255).astype(np.uint8))
    return out


def treadplate_textures():
    """Tileable checker plate: elliptical lentils at +/-45 deg on a square grid (alternating), as steel floor plate."""
    t = TREAD
    n, cells = t["size"], t["cells"]
    p = n / cells
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64) + 0.5
    h = np.zeros((n, n))
    for i in range(-1, cells + 1):
        for j in range(-1, cells + 1):
            ang = math.pi / 4 if (i + j) % 2 == 0 else -math.pi / 4
            ca, sa = math.cos(ang), math.sin(ang)
            dx, dy = xx - (i + 0.5) * p, yy - (j + 0.5) * p
            u = (dx * ca + dy * sa) / (t["lentil_len"] * p / 2)
            v = (-dx * sa + dy * ca) / (t["lentil_w"] * p / 2)
            h = np.maximum(h, np.sqrt(np.clip(1.0 - u * u - v * v, 0.0, 1.0)))
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / 2 * t["bump_px"]
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / 2 * t["bump_px"]
    nrm = np.stack([-gx, gy, np.ones_like(h)], -1)                 # DirectX-style green (AC/3ds Max convention)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    nm = np.concatenate([np.round((nrm + 1) * 127.5), np.full((n, n, 1), 255)], -1).astype(np.uint8)
    rng = np.random.default_rng(7)
    noise = rng.normal(0, 1, (n, n))
    for _ in range(3):                                              # soften to a mottled, used look
        noise = (noise + np.roll(noise, 1, 0) + np.roll(noise, 1, 1) + np.roll(noise, -1, 0) + np.roll(noise, -1, 1)) / 5
    noise /= max(noise.std(), 1e-9)
    slope = np.clip(np.hypot(gx, gy) / t["bump_px"], 0, 1)
    val = t["steel"] + t["tops"] * (h > 0.6) * (1 - slope) + t["valleys"] * (h < 0.05) + t["noise"] * noise
    col = np.clip(np.stack([val, val * 1.01, val * 1.03], -1), 0, 1)
    diff = np.concatenate([np.round(col * 255), np.full((n, n, 1), 255)], -1).astype(np.uint8)
    os.makedirs(TEX_DIR, exist_ok=True)
    files = {}
    for kind, img in (("d", diff), ("nm", nm)):
        name = f"{t['name']}_{kind}.dds"
        with open(os.path.join(TEX_DIR, name), "wb") as f:
            f.write(_dds(_mips(img)))
        files[kind] = name
    return files


def treadplate_material():
    """kn5 material (ksPerPixelNM, props copied from the car's own INT_Cinture and made dull). The exporter embeds
    the textures from tex_dir; LODs fall back to the black trim material (lod_fallback)."""
    files = treadplate_textures()
    base = json.loads(bpy.data.materials["INT_Cinture"]["kn5_def"])
    props = []
    for p in base["props"]:
        q = list(p)
        if q[0] in TREAD["props"]:
            q[1] = TREAD["props"][q[0]]
        if q[0] in ("fresnelC", "fresnelMaxLevel", "isAdditive"):
            q[1] = 0.0
        props.append(q)
    d = dict(name=TREAD["name"], shader="ksPerPixelNM", blend=0, alphaTested=0, depth=0, props=props,
             samplers=[["txDiffuse", 0, files["d"]], ["txNormal", 1, files["nm"]]], tex_dir=TEX_DIR)
    m = bpy.data.materials.get(TREAD["name"]) or bpy.data.materials.new(TREAD["name"])
    m["kn5_def"] = json.dumps(d)
    m["lod_fallback"] = ba.TRIM
    m.diffuse_color = (0.42, 0.43, 0.45, 1.0)
    m.use_fake_user = True
    return m


def planar_uv(ob, axes=(1, 2), tile=None, offset=(0.0, 0.0)):
    """World-space planar UVs (axes: 0 x, 1 y, 2 z) in tiles of TREAD['tile'] metres."""
    tile = tile or TREAD["tile"]
    me = ob.data
    mw = ob.matrix_world
    uvl = me.uv_layers.active or me.uv_layers.new(name="UVMap")
    co = [mw @ v.co for v in me.vertices]
    for li, loop in enumerate(me.loops):
        p = co[loop.vertex_index]
        uvl.data[li].uv = (p[axes[0]] / tile + offset[0], p[axes[1]] / tile + offset[1])


# ---- door boxes --------------------------------------------------------------------------------------------------
def _skin_selection(src, side, below_z=0.68, depth=0.060):
    """The outer-skin faces the v24 inner skin was offset from, their per-vertex offset normals."""
    bm = bmesh.new(); bm.from_mesh(src.data); bm.transform(src.matrix_world); bm.normal_update()
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    sel = [f for f in bm.faces if f.normal.x * side > 0.3 and all(v.co.z < below_z and v.co.x * side > 0.6 for v in f.verts)]
    vn = {}
    for f in sel:
        for v in f.verts:
            vn[v.index] = vn.get(v.index, Vector()) + f.normal
    return bm, sel, {k: n.normalized() for k, n in vn.items()}, depth


def door_end_caps(side):
    """Quads from every open edge of the outer skin's selection to the matching inner-skin edge: closes the door box
    (front, rear and bottom ends and the top under the window slot)."""
    tag = "L" if side > 0 else "R"
    src = ba.kn5_obj(f"DOOR_{tag}_doorhandlelf_a_SUB2")
    bm, sel, vn, depth = _skin_selection(src, side)
    inset = set(f.index for f in sel)
    verts, faces = [], []
    for f in sel:
        c = f.calc_center_median()
        for loop in f.loops:
            e = loop.edge
            if sum(1 for lf in e.link_faces if lf.index in inset) != 1:
                continue
            a, b = loop.vert, loop.link_loop_next.vert
            pa, pb = a.co.copy(), b.co.copy()
            qa, qb = pa - vn[a.index] * depth, pb - vn[b.index] * depth
            out = (pb - pa).cross(f.normal)
            if out.dot((pa + pb) / 2 - c) < 0:
                out = -out
            quad = [pa, pb, qb, qa]
            qn = (quad[1] - quad[0]).cross(quad[3] - quad[0])
            if qn.dot(out) < 0:
                quad.reverse()
            k = len(verts)
            verts += [tuple(p) for p in quad]
            faces.append((k, k + 1, k + 2, k + 3))
    bm.free()
    door = bpy.data.objects[f"DOOR_{tag}"]
    ob = ba.make_obj(f"AERO_door_ends_{tag}", (verts, faces), ba.material(ba.PAINT), PAINT_UV, door, sharp_deg=50.0)
    # make_obj recalculates normals; keep ours (outward) - rebuild faces as given
    me = ob.data
    bm2 = bmesh.new(); bm2.from_mesh(me); bm2.normal_update()
    # re-orient each face away from the door's centre plane (inner skin <-> outer skin)
    cen = Vector(np.mean(np.array([list(v) for v in verts]), 0))
    for fc in bm2.faces:
        d = fc.calc_center_median() - cen
        d.x = 0.0
        if fc.normal.dot(d) < 0 and abs(fc.normal.x) < 0.7:
            fc.normal_flip()
    bm2.to_mesh(me); bm2.free(); me.update()
    ob["door_part"] = tag
    return ob


def treadplate_inner_skins():
    m = treadplate_material()
    out = {}
    for tag in "LR":
        ob = bpy.data.objects[f"AERO_door_inner_{tag}"]
        ob.data.materials.clear(); ob.data.materials.append(m)
        planar_uv(ob, axes=(1, 2))
        out[tag] = ob.name
    return out


HANDLE = dict(grab_y=(0.18, 0.36), grab_z=0.43, standoff=0.045, grab_r=0.011,
              lever_y=-0.30, lever_z=0.50, lever_len=0.11, lever_r=0.007)


def _inner_surface(tag, y, z):
    """Point + cabin-facing normal of the inner skin at (y, z)."""
    ob = bpy.data.objects[f"AERO_door_inner_{tag}"]
    mw = ob.matrix_world
    vs = [mw @ v.co for v in ob.data.vertices]
    tree = BVHTree.FromPolygons(vs, [list(p.vertices) for p in ob.data.polygons])
    side = 1 if tag == "L" else -1
    hit = tree.ray_cast(Vector((0.0, y, z)), Vector((side, 0, 0)), 2.0)
    n = hit[1] if hit[1].x * side < 0 else -hit[1]
    return hit[0], n


def door_handles():
    """Per door: black grab handle (closing) and a steel release lever where the original release was."""
    trim, metal = ba.material(ba.TRIM), ba.material("Material #503ds")
    tuv = ba.pick_uv(trim, (0.70, 0.30, 0.75))[1]
    muv = ba.pick_uv(metal, (0.30, 1.00, 0.00))[1]
    h = HANDLE
    out = {}
    for tag in "LR":
        door = bpy.data.objects[f"DOOR_{tag}"]
        y0, y1 = h["grab_y"]
        p0, n0 = _inner_surface(tag, y0, h["grab_z"])
        p1, n1 = _inner_surface(tag, y1, h["grab_z"])
        a0, a1 = p0 + n0 * h["standoff"], p1 + n1 * h["standoff"]
        black = [r.tube(p0 - n0 * 0.002, a0, h["grab_r"]), r.tube(p1 - n1 * 0.002, a1, h["grab_r"]),
                 r.tube(a0, a1, h["grab_r"]),
                 r.tube(p0 - n0 * 0.002, p0 + n0 * 0.006, 0.020), r.tube(p1 - n1 * 0.002, p1 + n1 * 0.006, 0.020)]
        q, nq = _inner_surface(tag, h["lever_y"], h["lever_z"])
        piv = q + nq * 0.012
        tip = piv + Vector((0, h["lever_len"], 0))
        steel = [r.tube(q - nq * 0.002, q + nq * 0.004, 0.024, n=16),        # escutcheon
                 r.tube(q, piv, 0.006), r.tube(piv, tip, h["lever_r"]), r.sphere(tip, 0.010)]
        for name, parts, mat, uv in ((f"AERO_door_grab_{tag}", black, trim, tuv), (f"AERO_door_release_{tag}", steel, metal, muv)):
            ob = ba.make_obj(name, ba.merge(*parts), mat, uv, door)
            ob["door_part"] = tag
            out[name] = len(ob.data.polygons)
    return out


# ---- passenger footrest ------------------------------------------------------------------------------------------
FOOTREST = dict(x=(-0.505, -0.195), low=(-0.700, 0.024), high=(-0.884, 0.214), t=0.004, lip=0.025, bolt_r=0.006)


def footrest():
    """Treadplate plate on the passenger toe board (car's right = -X): floor at y -0.76 up to the toe board, ~48 deg,
    folded heel lip, two support legs and four bolts."""
    f = FOOTREST
    x0, x1 = f["x"]
    (ya, za), (yb, zb) = f["low"], f["high"]
    sl = Vector((0, yb - ya, zb - za)); L = sl.length; s = sl.normalized()
    n = Vector((0, -s.z, s.y))                                  # plate normal (up and rearward, towards the feet)
    if n.z < 0:
        n = -n
    def plate_pt(x, d, h=0.0):
        return Vector((x, ya, za)) + s * d + n * h
    t = f["t"]
    v = [plate_pt(x, d, h) for h in (0, t) for d in (0, L) for x in (x0, x1)]
    plate = ([tuple(p) for p in v], [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    lip_top = plate_pt(0, 0, 0) + n * f["lip"]
    lv = [Vector((x, ya, za)) + s * dd + nn for nn in (Vector(), n * f["lip"]) for dd in (0, -t) for x in (x0, x1)]
    lip = ([tuple(p) for p in lv], [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    m = treadplate_material()
    ob = ba.make_obj("AERO_footrest", ba.merge(plate, lip), m, (0.0, 0.0), ba.root())
    # UVs in the plate's own frame (u across, v up the slope)
    me = ob.data; uvl = me.uv_layers.active
    for li, loop in enumerate(me.loops):
        p = ob.matrix_world @ me.vertices[loop.vertex_index].co
        d = (p - Vector((0, ya, za))).dot(s)
        uvl.data[li].uv = (p.x / TREAD["tile"], d / TREAD["tile"])
    trim, metal = ba.material(ba.TRIM), ba.material("Material #503ds")
    tuv = ba.pick_uv(trim, (0.70, 0.30, 0.75))[1]; muv = ba.pick_uv(metal, (0.30, 1.00, 0.00))[1]
    legs, bolts = [], []
    world = r._scene_bvh(exclude_prefix=("AERO", "M_Tire", "for_5_escort", "for_rotor", "for_caliper", "TMP"))
    for x in (x0 + 0.03, x1 - 0.03):
        top = plate_pt(x, L * 0.62, -0.002)
        hit = world.ray_cast(top - Vector((0, 0, 0.003)), Vector((0, 0, -1)), 0.4)[0]
        foot = hit if hit is not None else Vector((x, top.y, za))
        legs.append(r.box((top + foot) / 2, Vector((0.010, 0, 0)), Vector((0, 0.010, 0)), Vector((0, 0, (top - foot).length / 2))))
        for d in (0.03, L - 0.03):
            c = plate_pt(x, d, t)
            bolts.append(r.tube(c - n * 0.001, c + n * 0.003, f["bolt_r"], n=8))
    for name, parts, mat, uv in (("AERO_footrest_legs", legs, trim, tuv), ("AERO_footrest_bolts", bolts, metal, muv)):
        ba.make_obj(name, ba.merge(*parts), mat, uv, ba.root())
    return dict(length=round(L, 3), angle_deg=round(math.degrees(math.atan2(sl.z, -sl.y)), 1))


# ---- rear anti-roll bar --------------------------------------------------------------------------------------------
ARB = dict(y=1.378, z=0.072, half=0.46, r=0.0125, bush_x=0.24, bush_r=0.022, bush_len=0.040, arm_to_y=1.279,
           link_r=0.006, rod_end=0.011, floor=0.105)


def rear_arb():
    """Physics: ARB REAR 15000 (adjustable 0-35000). Bar across behind the lower wishbones' rear pivots (clear of the
    silencer by ~2 cm), two floor bushes, blade arms forward, drop links to the lower wishbones' rear legs."""
    a = ARB
    trim, metal = ba.material(ba.TRIM), ba.material("Material #503ds")
    tuv = ba.pick_uv(trim, (0.70, 0.30, 0.75))[1]; muv = ba.pick_uv(metal, (0.30, 1.00, 0.00))[1]
    black, steel = [], []
    y, z, hx = a["y"], a["z"], a["half"]
    black.append(r.tube((-hx, y, z), (hx, y, z), a["r"]))
    g = r.dtm.REAR_DWB
    out = {}
    for side in (1, -1):
        c = r.corner_points(side)
        lr, lbj = c["WBCAR_BOTTOM_REAR"], c["WBTYRE_BOTTOM"]
        xe = side * hx
        tt = (abs(xe) - abs(lr.x)) / (abs(lbj.x) - abs(lr.x))
        on_arm = lr + (lbj - lr) * tt
        bx = side * a["bush_x"]
        black.append(r.tube((bx - a["bush_len"] / 2, y, z), (bx + a["bush_len"] / 2, y, z), a["bush_r"]))
        black.append(r.box((bx, y, (z + a["floor"]) / 2 + 0.005), Vector((0.016, 0, 0)), Vector((0, 0.018, 0)),
                           Vector((0, 0, (a["floor"] - z) / 2 + 0.006))))
        arm_end = Vector((xe, a["arm_to_y"], z))
        black.append(r.box(((Vector((xe, y, z)) + arm_end) / 2), Vector((0.006, 0, 0)), Vector((0, (y - a["arm_to_y"]) / 2 + 0.012, 0)),
                           Vector((0, 0, 0.016))))                       # blade arm
        low = Vector((xe, on_arm.y, on_arm.z + r.SIZES["lower_r"] + 0.004))
        steel.append(r.tube(arm_end, low, a["link_r"]))
        steel.append(r.sphere(arm_end, a["rod_end"])); steel.append(r.sphere(low, a["rod_end"]))
        out["link_" + ("L" if side > 0 else "R")] = [round(v, 3) for v in low]
    for name, parts, mat, uv in (("AERO_rsus_arb", black, trim, tuv), ("AERO_rsus_arb_links", steel, metal, muv)):
        ob = ba.make_obj(name, ba.merge(*parts), mat, uv, ba.root())
        ob["rsus_part"] = True
        out[name] = len(ob.data.polygons)
    return out


# ---- boot: battery back, tank on the floor ---------------------------------------------------------------------------
BOOT_CLEAR = [   # (label, world box, keep these kn5 materials, keep islands reaching past x) - main model only (closed boot in LODs)
    ("old fuel pumps + lines", ((-0.60, 1.38, 0.11), (-0.05, 1.70, 0.45)), ("gascap_001", "sensor_001"), None),
    ("floor tie-down straps + old fuel line", ((-0.36, 1.40, 0.11), (0.33, 1.92, 0.20)), (), 0.29),
]
# Battery box (0.21 x 0.31, on the left raised floor) moves out + back + up so the tank's 0.76 m width clears it by ~1 cm
# (tested against the boot without the battery: 2 marginal contacts, bottom 0-3 cm over the sloping floor - the
# original sat 1-2 cm INTO it). Only islands wholly inside move; cables leaving the box stretch (falloff); floor panels
# that merely reach into the box never move (the first try dragged 43 floor-pan verts - restored from the v24 blend).
BATTERY = dict(box=((0.28, 1.45, 0.10), (0.62, 1.95, 0.40)), move=(0.08, 0.10, 0.035), falloff=0.15,
               cable_max_dim=0.25, cable_min_dz=0.03, cable_min_inside=0.25)


def _islands_world(ob):
    mw = ob.matrix_world
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
    W = np.array([list(mw @ v.co) for v in bm.verts]) if len(bm.verts) else np.zeros((0, 3))
    comps = [[u.index for u in c] for c in r._islands(bm)]
    return bm, W, comps


def clear_boot():
    from model_fixes import _kn5_mat
    rep = {}
    for ob in list(ba.main_scene().objects):
        if ob.type != "MESH" or str(ob.get("kn5_name") or ob.name).startswith(("AERO", "DOOR", "TMP")) or not len(ob.data.vertices):
            continue
        mat = _kn5_mat(ob)
        bm, W, comps = _islands_world(ob)
        kill = []
        for c in comps:
            P = W[c]
            for label, (lo, hi), keep_mats, max_x in BOOT_CLEAR:
                if mat in keep_mats:
                    continue
                if ((P >= np.array(lo)) & (P <= np.array(hi))).all() and (max_x is None or P[:, 0].max() <= max_x):
                    kill += c; rep[label] = rep.get(label, 0) + len(c)
                    break
        if kill:
            bmesh.ops.delete(bm, geom=[bm.verts[i] for i in kill], context="VERTS"); bm.to_mesh(ob.data); ob.data.update()
        bm.free()
    return rep


def move_battery():
    """Battery + tray + clamp move back 0.10 and out 0.04 (clear of the tank); cables leaving the box bend with a
    falloff so they stay attached."""
    lo, hi = (np.array(b) for b in BATTERY["box"])
    mv = np.array(BATTERY["move"]); fall = BATTERY["falloff"]
    rep = {}
    for ob in list(ba.main_scene().objects):
        nm = str(ob.get("kn5_name") or ob.name)
        # boot equipment meshes only: never the floor pan (SUB1) or the underbody shell (grille_a)
        if ob.type != "MESH" or not nm.startswith("trunkbay_a__slod_SUB") or nm.startswith("trunkbay_a__slod_SUB1_") \
                or nm in ("trunkbay_a__slod_SUB1",) or not len(ob.data.vertices):
            continue
        bm, W, comps = _islands_world(ob)
        inv = ob.matrix_world.inverted()
        n = 0
        b = BATTERY
        for c in comps:
            P = W[c]
            inside = ((P >= lo) & (P <= hi)).all(1)
            if not inside.any():
                continue
            if not inside.all():
                ext = P.max(0) - P.min(0)
                cable = (inside.mean() >= b["cable_min_inside"] and ext.max() < b["cable_max_dim"]
                         and ext[2] > b["cable_min_dz"])
                if not cable:
                    continue                                     # floor panels / tub reaching into the box stay put
            for i, p in zip(c, P):
                d = np.linalg.norm(np.maximum(np.maximum(lo - p, p - hi), 0))
                w = 1.0 if d == 0 else max(0.0, 1.0 - d / fall)
                if w > 0:
                    bm.verts[i].co = inv @ Vector(p + mv * w); n += 1
        if n:
            bm.to_mesh(ob.data); ob.data.update()                # a pure shift: the stored kn5 normals stay valid
            rep[ob.name] = n
        bm.free()
    return rep


def restore_from_blend(blend, names, mode="positions"):
    """Put objects' meshes back as they are in another .blend (e.g. the BACKUP v24 one). mode "positions": copy vertex
    positions (same topology), "mesh": swap the whole mesh in. Appended helpers, duplicate materials etc. are removed,
    restored meshes keep pointing at this file's materials."""
    sc_mats = {}
    for s in bpy.data.scenes:
        if "kn5_materials" in s:
            for n in json.loads(s["kn5_materials"]):
                sc_mats.setdefault(json.loads(bpy.data.materials[n]["kn5_def"])["name"], {})[s.name] = bpy.data.materials[n]
    before_mats = set(bpy.data.materials.keys())
    with bpy.data.libraries.load(blend, link=False) as (src, dst):
        have = set(src.objects)
        dst.objects = [n for n in names if n in have]
    done = {}
    for n, old in zip([n for n in names if n in have], dst.objects):
        live = bpy.data.objects[n]
        if mode == "positions":
            assert len(old.data.vertices) == len(live.data.vertices), n
            co = np.empty(len(old.data.vertices) * 3); old.data.vertices.foreach_get("co", co)
            live.data.vertices.foreach_set("co", co); live.data.update()
        else:
            new = old.data
            old.data = bpy.data.meshes.new("tmp_swap")
            scene = live.users_scene[0].name
            for i, m in enumerate(new.materials):
                if m is not None and "kn5_def" in m:
                    new.materials[i] = sc_mats[json.loads(m["kn5_def"])["name"]][scene]
            oldme = live.data; live.data = new; new.name = oldme.name; bpy.data.meshes.remove(oldme)
        done[n] = len(live.data.vertices)
    for o in [o for o in bpy.data.objects if not o.users_scene]:
        bpy.data.objects.remove(o)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for d in [d for d in coll if d.users == 0 and not getattr(d, "use_fake_user", False)]:
            if coll is not bpy.data.materials or d.name not in before_mats:
                coll.remove(d)
    return done


WINDOW_TRIM = [   # (source mesh in the v23 blend, keep islands removed in v24 that start above this z) -> door nodes
    ("doorcardlf_a__slod_SUB4", 0.55),     # inner window sill trim (Material #400312)
    ("doorcardlf_a__slod_SUB2", 0.55),     # the card's top capping strip under it (Material #385T34)
]


def restore_window_trim(v23_blend):
    """Nik, 6 Oct: "You seem to have removed the inside window trim" - v24's door-card removal took the sill trim too.
    The islands v24 removed (present in the v23 blend, gone now) above the glass line come back, split per side,
    as DOOR_L/R_window_trim_* meshes on the door nodes (original geometry, UVs and normals)."""
    from mathutils.kdtree import KDTree
    sc = ba.main_scene()
    mats = {json.loads(bpy.data.materials[n]["kn5_def"])["name"]: bpy.data.materials[n] for n in json.loads(sc["kn5_materials"])}
    with bpy.data.libraries.load(v23_blend, link=False) as (src, dst):
        dst.objects = [ba.kn5_obj(n).name for n, _ in WINDOW_TRIM]
    out = {}
    for (node, zmin), old in zip(WINDOW_TRIM, dst.objects):
        live = ba.kn5_obj(node)
        mw = live.matrix_world
        kd = KDTree(max(1, len(live.data.vertices)))
        for i, v in enumerate(live.data.vertices):
            kd.insert(v.co, i)
        kd.balance()
        bm = bmesh.new(); bm.from_mesh(old.data); bm.verts.ensure_lookup_table()
        keep = {"L": set(), "R": set()}
        for comp in r._islands(bm):
            if not all(kd.find(u.co)[2] > 1e-6 for u in comp[:3]):
                continue                                         # still in the live mesh
            P = np.array([list(mw @ u.co) for u in comp])
            if P[:, 2].min() < zmin or P[:, 1].max() > 0.56 or abs(P[:, 0]).min() < 0.55:
                continue
            keep["L" if P[:, 0].mean() > 0 else "R"].update(u.index for u in comp)
        bm.free()
        for tag, idx in keep.items():
            if not idx:
                continue
            name = f"DOOR_{tag}_window_trim_{node.split('_')[-1]}"
            for o in [o for o in bpy.data.objects if o.name == name]:
                bpy.data.objects.remove(o)
            me = old.data.copy(); me.name = name
            b2 = bmesh.new(); b2.from_mesh(me); b2.verts.ensure_lookup_table()
            bmesh.ops.delete(b2, geom=[v for v in b2.verts if v.index not in idx], context="VERTS")
            b2.to_mesh(me); b2.free()
            for i, m in enumerate(me.materials):
                me.materials[i] = mats[json.loads(m["kn5_def"])["name"]]
            ob = bpy.data.objects.new(name, me)
            for k in ("kn5_class", "kn5_flags", "kn5_pristine"):
                if k in live:
                    ob[k] = live[k]
            ob["kn5_name"] = name
            for col in bpy.data.objects[f"DOOR_{tag}_doorhandlelf_a_SUB2"].users_collection:
                col.objects.link(ob)
            door = bpy.data.objects[f"DOOR_{tag}"]
            ob.parent = door
            ob.matrix_world = mw.copy()
            out[name] = len(me.vertices)
    for o in [o for o in bpy.data.objects if not o.users_scene]:
        bpy.data.objects.remove(o)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for d in [d for d in coll if d.users == 0 and not getattr(d, "use_fake_user", False)]:
            coll.remove(d)
    return out


GAITER_BOX = ((-0.047, -0.354, 0.278), (0.047, -0.261, 0.395))   # model_fixes.GEAR_REGIONS' gaiter box
LEVER = dict(base=(0.0, -0.299, 0.372), knob_bot=(0.0, -0.287, 0.471), knob_top=0.511, r=0.0075, knob_r=0.017,
             collar_r=0.012)


def _join_islands(live, old_me, idx, mats):
    """Copy the vertices idx (whole islands) of old_me into the live object (bpy join: UVs, custom normals and the
    kn5 corner attributes travel); the copy uses this file's materials."""
    me = old_me.copy()
    b2 = bmesh.new(); b2.from_mesh(me); b2.verts.ensure_lookup_table()
    bmesh.ops.delete(b2, geom=[v for v in b2.verts if v.index not in idx], context="VERTS")
    b2.to_mesh(me); b2.free()
    for i, m in enumerate(me.materials):
        me.materials[i] = mats[json.loads(m["kn5_def"])["name"]]
    tmp = bpy.data.objects.new("TMP_join", me)
    for col in live.users_collection:
        col.objects.link(tmp)
    tmp.matrix_world = live.matrix_world.copy()
    n_before = len(live.data.vertices)
    with bpy.context.temp_override(active_object=live, object=live, selected_objects=[live, tmp],
                                   selected_editable_objects=[live, tmp]):
        bpy.ops.object.join()
    return len(live.data.vertices) - n_before


def blend_shifter(v23_blend):
    """Nik, 6 Oct: "the placement of the gear stick is good, but it looks like a bolted on afterthought, blend it into the
    original area" - the v24 housing box, gate plate and rod go; the original rubber gaiter (removed in v24) comes back
    from the v23 blend (main + COCKPIT_LR copy + LOD B); the lever rises out of it along the old stick's line."""
    from mathutils.kdtree import KDTree
    for n in ("AERO_seq_shifter", "AERO_seq_shifter_black"):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o)
    lo, hi = (np.array(b) for b in GAITER_BOX)
    targets = {}
    for tag in ("Scene", "LOD_B"):
        for ob in bpy.data.scenes[tag].objects:
            if ob.type == "MESH" and str(ob.get("kn5_name") or "").startswith("overheadconsole_a_SUB9"):
                targets[ob.name] = (tag, ob)
    with bpy.data.libraries.load(v23_blend, link=False) as (src, dst):
        have = set(src.objects)
        dst.objects = [n for n in targets if n in have]
    rep = {}
    for old in dst.objects:
        live_name = next(n for n in targets if old.name.startswith(n.rsplit(".", 1)[0]) and n in have
                         and len(bpy.data.objects[n].data.vertices) <= len(old.data.vertices)
                         and n not in rep and str(bpy.data.objects[n].get("kn5_name")) == str(old.get("kn5_name")))
        tag, live = targets[live_name]
        sc = bpy.data.scenes[tag]
        mats = {json.loads(bpy.data.materials[n]["kn5_def"])["name"]: bpy.data.materials[n] for n in json.loads(sc["kn5_materials"])}
        mw = live.matrix_world
        kd = KDTree(max(1, len(live.data.vertices)))
        for i, v in enumerate(live.data.vertices):
            kd.insert(v.co, i)
        kd.balance()
        bm = bmesh.new(); bm.from_mesh(old.data); bm.verts.ensure_lookup_table()
        idx = set()
        for comp in r._islands(bm):
            P = np.array([list(mw @ u.co) for u in comp])
            if ((P >= lo) & (P <= hi)).all() and all(kd.find(u.co)[2] > 1e-6 for u in comp[:3]):
                idx.update(u.index for u in comp)
        bm.free()
        rep[live_name] = _join_islands(live, old.data, idx, mats) if idx else 0
    for o in [o for o in bpy.data.objects if not o.users_scene]:
        bpy.data.objects.remove(o)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for d in [d for d in coll if d.users == 0 and not getattr(d, "use_fake_user", False)]:
            coll.remove(d)
    # the lever: from inside the gaiter along the old stick's line, the v24 sequential knob on top
    L = LEVER
    trim, metal = ba.material(ba.TRIM), ba.material("Material #503ds")
    tuv = ba.pick_uv(trim, (0.70, 0.30, 0.75))[1]; muv = ba.pick_uv(metal, (0.30, 1.00, 0.00))[1]
    base, kb = Vector(L["base"]), Vector(L["knob_bot"])
    ax = (kb - base).normalized()
    kt = kb + ax * (L["knob_top"] - kb.z) / ax.z
    steel = [r.tube(base, kb + ax * 0.006, L["r"])]
    black = [r.tube(kb, kt - ax * 0.004, L["knob_r"], n=16), r.tube(kt - ax * 0.004, kt, L["knob_r"], L["knob_r"] - 0.004, n=16),
             r.tube(base + ax * 0.020, base + ax * 0.034, L["collar_r"], n=12)]          # collar at the gaiter's mouth
    for name, parts, mat, uv in (("AERO_seq_shifter", steel, metal, muv), ("AERO_seq_shifter_black", black, trim, tuv)):
        ob = ba.make_obj(name, ba.merge(*parts), mat, uv, ba.root())
        ob["interior_part"] = True
    return rep


# ---- door mirrors ----------------------------------------------------------------------------------------------------
# Mk2 Escort factory door mirror: black rounded housing on a short stem from a pad on the door's top front corner (the
# door skin ends at z 0.65 there, ahead of the window frame at y -0.49). Glass normals = bisector of "to the driver's
# eye" (DRIVEREYES 0.286, 0.884, -0.345 -> Blender (0.29, 0.345, 0.88)) and "straight back": 14 deg in on the left,
# 24 deg on the right, ~4 deg up. Glass UVs as Kunos' 190 DTM (u rises towards the car's left: left glass 0.54-0.90,
# right 0.46-0.10 inner->outer, v 0.06-0.94 bottom->top) - AC paints the rear view across that strip; mirrors.ini lists
# the two glass meshes after the interior mirror (dtm_build.MIRRORS).
EYE = Vector((0.29, 0.345, 0.88))
MIRROR = dict(pad=(0.716, -0.598, 0.627), head=(0.862, -0.586, 0.716), a=0.074, b=0.046, depth=0.064, rim=0.006,
              recess=0.004, sides=40, exp=4.0, out_bias=0.05, mat="ID20_mirrorcenter|rearviewmirror_a",
              u=dict(L=(0.54, 0.90), R=(0.46, 0.10)), v=(0.06, 0.94))


def _superellipse(a, b, n, exp):
    pts = []
    for k in range(n):
        t = 2 * math.pi * k / n
        c, s = math.cos(t), math.sin(t)
        pts.append((a * math.copysign(abs(c) ** (2 / exp), c), b * math.copysign(abs(s) ** (2 / exp), s)))
    return pts


def mirror_frame(side):
    m = MIRROR
    head = Vector(m["head"]); head.x *= side
    to_eye = (EYE - head).normalized()
    back = Vector((side * m["out_bias"], 1.0, 0.0)).normalized()
    n = (to_eye + back).normalized()                               # glass normal (faces the driver / rear)
    up = (Vector((0, 0, 1)) - n * n.z).normalized()
    out = n.cross(up) * side                                      # towards the outer edge
    return head, n, up, out


def build_mirrors():
    m = MIRROR
    trim = ba.material(ba.TRIM); tuv = ba.pick_uv(trim, (0.70, 0.30, 0.75))[1]
    glass_mat = ba.material(m["mat"])
    res = {}
    for side, tag in ((1, "L"), (-1, "R")):
        head, n, up, out = mirror_frame(side)
        door = bpy.data.objects[f"DOOR_{tag}"]

        def ring(sa, sb, d):
            return [tuple(head + out * x + up * y - n * d) for x, y in _superellipse(sa, sb, m["sides"], m["exp"])]
        a, b, rim = m["a"], m["b"], m["rim"]
        secs = [ring(a - rim, b - rim, m["recess"]), ring(a - rim, b - rim, 0.0), ring(a, b, 0.0), ring(a, b, 0.012),
                ring(0.985 * a, 0.985 * b, 0.030), ring(0.90 * a, 0.88 * b, 0.048), ring(0.70 * a, 0.65 * b, 0.058),
                ring(0.35 * a, 0.30 * b, m["depth"])]
        housing = ba.loft(secs)
        # pad on the door skin + tapered stem into the housing's inner lower part
        pad = Vector(m["pad"]); pad.x *= side
        skin_n = Vector((side * 0.93, 0.0, 0.37)).normalized()
        pu = Vector((0, 1, 0)); pv = skin_n.cross(pu).normalized()
        pad_secs = [[tuple(pad + skin_n * h + pu * x + pv * y) for x, y in _superellipse(0.040 * s, 0.024 * s, 24, 3.0)]
                    for h, s in ((-0.003, 1.0), (0.008, 1.0), (0.014, 0.8))]
        stem_top = head - out * (a * 0.55) - up * (b * 0.25) - n * 0.035
        stem_bot = pad + skin_n * 0.010
        stem = r.tube(stem_bot, stem_top, 0.013, 0.009, n=12)
        ob = ba.make_obj(f"AERO_mirror_{tag}", ba.merge(housing, ba.loft(pad_secs), stem), trim, tuv, door)
        ob["door_part"] = tag
        # glass: flat, 1.5 mm proud of the recess floor, UV strip as Kunos'
        g2 = _superellipse(a - rim - 0.002, b - rim - 0.002, m["sides"], m["exp"])
        centre = head - n * (m["recess"] - 0.0015)
        verts = [tuple(centre)] + [tuple(centre + out * x + up * y) for x, y in g2]
        k = len(g2)
        faces = [(0, 1 + i, 1 + (i + 1) % k) for i in range(k)]
        fn = (Vector(verts[1]) - Vector(verts[0])).cross(Vector(verts[2]) - Vector(verts[0]))
        if fn.dot(n) < 0:
            faces = [tuple(reversed(f)) for f in faces]
        g = ba.make_obj(f"AERO_mirror_glass_{tag}", (verts, faces), glass_mat, (0.5, 0.5), door)
        me = g.data
        if sum((p.normal for p in me.polygons), Vector()).dot(n) < 0:
            bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
        u0, u1 = m["u"][tag]; v0, v1 = m["v"]
        sa, sb = a - rim - 0.002, b - rim - 0.002
        uvl = me.uv_layers.active
        for li, loop in enumerate(me.loops):
            p = g.matrix_world @ me.vertices[loop.vertex_index].co - centre
            s = (p.dot(out) + sa) / (2 * sa); t = (p.dot(up) + sb) / (2 * sb)
            uvl.data[li].uv = (u0 + (u1 - u0) * s, v0 + (v1 - v0) * t)
        for p in me.polygons:
            p.use_smooth = False
        g["door_part"] = tag
        res[tag] = dict(normal=[round(c, 3) for c in n], inward_deg=round(math.degrees(math.atan2(-side * n.x, n.y)), 1),
                        up_deg=round(math.degrees(math.asin(n.z)), 1), housing_faces=len(ob.data.polygons))
    return res


# ---- engine swap housekeeping: the old 4-cylinder stays in the blend, hidden and not exported --------------------
ENGINE_ZONE = ((-0.47, -1.64, 0.05), (0.47, -0.84, 0.62))   # between the inner wings, radiator and bulkhead, under the brace
OLD_ENGINE_PREFIX = "OLDENG_"


def engine_tree():
    bm = bmesh.new()
    for o in ba.main_scene().objects:
        nm = str(o.get("kn5_name") or o.name)
        if o.type == "MESH" and nm.startswith("engine_a") and not nm.endswith("__lr") and len(o.data.vertices):
            t = o.data.copy(); t.transform(o.matrix_world); bm.from_mesh(t); bpy.data.meshes.remove(t)
    tree = BVHTree.FromBMesh(bm); bm.free()
    return tree


def stow_old_engine(touch=0.006, min_inside=0.8):
    """engine_a* (main model incl. COCKPIT_LR copies) -> no_export + hidden; the bay islands that touch the old engine
    (hoses, intake, HT leads, loom, pulleys) and sit in ENGINE_ZONE -> split into OLDENG_<mesh> objects next to their
    source, no_export + hidden. swap_engine_back() undoes both."""
    sc = ba.main_scene()
    tree = engine_tree()
    lo, hi = (np.array(b) for b in ENGINE_ZONE)
    rep = {"engine meshes": 0, "bay islands": {}}
    for o in list(sc.objects):
        nm = str(o.get("kn5_name") or o.name)
        if o.type == "MESH" and nm.startswith("engine_a"):
            o["no_export"] = True; o.hide_viewport = True; rep["engine meshes"] += 1
    for o in list(sc.objects):
        nm = str(o.get("kn5_name") or o.name)
        if o.type != "MESH" or not nm.startswith("enginebay") or not len(o.data.vertices):
            continue
        bm, W, comps = _islands_world(o)
        take = set()
        lr = nm.endswith("__lr")
        for c in comps:
            P = W[c]
            if ((P >= lo) & (P <= hi)).all(1).mean() < min_inside:
                continue
            step = max(1, len(c) // 60)
            lim = 0.02 if lr else touch              # low-res copies sit coarser around the (high-res) engine
            if any(tree.find_nearest(Vector(p), lim)[0] is not None for p in P[::step]):
                take.update(c)
        bm.free()
        if not take:
            continue
        name = OLD_ENGINE_PREFIX + o.name
        me = o.data.copy(); me.name = name
        b2 = bmesh.new(); b2.from_mesh(me); b2.verts.ensure_lookup_table()
        bmesh.ops.delete(b2, geom=[v for v in b2.verts if v.index not in take], context="VERTS"); b2.to_mesh(me); b2.free()
        b3 = bmesh.new(); b3.from_mesh(o.data); b3.verts.ensure_lookup_table()
        bmesh.ops.delete(b3, geom=[b3.verts[i] for i in take], context="VERTS"); b3.to_mesh(o.data); b3.free(); o.data.update()
        ob = o.copy(); ob.data = me; ob.name = name
        for col in o.users_collection:
            col.objects.link(ob)
        ob.parent = o.parent; ob.matrix_world = o.matrix_world.copy()
        ob["no_export"] = True; ob["oldeng_source"] = o.name; ob.hide_viewport = True
        rep["bay islands"][o.name] = len(take)
    return rep


def swap_engine_back():
    """The backup path: re-join the OLDENG_ islands into their meshes, re-enable engine_a, drop the new engine."""
    sc = ba.main_scene()
    for ob in [o for o in sc.objects if o.name.startswith(OLD_ENGINE_PREFIX)]:
        src = bpy.data.objects[ob["oldeng_source"]]
        ob.hide_viewport = False; del ob["no_export"]
        with bpy.context.temp_override(active_object=src, object=src, selected_objects=[src, ob],
                                       selected_editable_objects=[src, ob]):
            bpy.ops.object.join()
    for o in sc.objects:
        if o.type == "MESH" and str(o.get("kn5_name") or o.name).startswith("engine_a"):
            o.hide_viewport = False
            if "no_export" in o:
                del o["no_export"]
    for o in [o for o in sc.objects if o.get("v8_part")]:
        bpy.data.objects.remove(o)


def door_boxes():
    rep = {"inner skins": treadplate_inner_skins()}
    for side in (1, -1):
        ob = door_end_caps(side)
        rep[ob.name] = len(ob.data.polygons)
    rep.update(door_handles())
    return rep

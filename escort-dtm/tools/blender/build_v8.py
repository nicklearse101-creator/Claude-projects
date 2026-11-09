"""v25: the engine bay gets an engine to the physics' spec - a compact 4.0 l 90-degree V8 (DTM Class 1 inspired, 400 bhp,
8500 rpm, dry sump). Nik, 6 Oct: "The engine probably doesn't match spec anymore, how confident are you in replacing it
to equally high detail? - make sure there's a backup available if it doesn't look right afterwards and build that."

    import v25, build_v8
    v25.stow_old_engine()     # the 4-cylinder + the bay parts bolted to it -> hidden, not exported (v25.swap_engine_back())
    build_v8.build()          # V8_* parts (main model only; LODs keep the closed-bonnet engine)
    build_v8.clear_bay()      # bay islands the V8 runs through -> OLDENG_ objects as well

Packaging (measured in the bay): radiator back face y -1.58, bulkhead/tunnel y -0.86..-0.90, subframe top z 0.105,
strut towers leave +-0.37 m between y -1.30 and -1.12, the strut brace's underside is at z 0.535 (y -1.32..-1.27) and
the bonnet 0.62-0.69. Hence: crank at z 0.20 with a shallow dry-sump pan, short-deck DOHC heads whose cam covers top
out at ~0.51, a log plenum in the valley (no trumpets - there is no room above the brace), throttle body + cone filter
at the front, 4-into-1 headers dropping outside the subframe and running back under the floor into the existing pipe
(0.232, 0.825, -0.021). Mounts land on the subframe's four mount pads (x +-0.26, y -1.37 / -1.07).
Blender: +X = car's left, +Y = rear, Z up.
"""
import json
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

import build_aero as ba
import build_rear_dwb as r
import v25

TEX_DIR = v25.TEX_DIR
C = Vector((0.0, 0.0, 0.200))           # crank axis height (x 0, z) - y along the crank
BLOCK = dict(y0=-1.440, y1=-0.990, skirt=0.215, pan_z=0.118, pan_top=0.135, deck=0.195, deck_half=0.105,
             valley_z=0.375, bank_deg=45.0)
HEAD = dict(h=0.118, half=0.104, cover_h=0.034, cover_half=0.096, y0=-1.428, y1=-0.990, offset=0.020)   # right bank +offset
CYL = dict(n=4, pitch=0.105, first=-1.385)      # left-bank cylinder centres along y (right bank + offset)
SIDES = 16


# ---- materials ---------------------------------------------------------------------------------------------------
def _noise(n, rng, blur):
    a = rng.normal(0, 1, (n, n))
    for _ in range(blur):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5
    return a / max(a.std(), 1e-9)


def _normal_from_height(h, strength):
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / 2 * strength
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / 2 * strength
    nrm = np.stack([-gx, gy, np.ones_like(h)], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    return np.concatenate([np.round((nrm + 1) * 127.5), np.full(h.shape + (1,), 255)], -1).astype(np.uint8)


def _rgba(col):
    return np.concatenate([np.round(np.clip(col, 0, 1) * 255), np.full(col.shape[:2] + (1,), 255)], -1).astype(np.uint8)


def textures():
    """Sand-cast aluminium, black crinkle paint, anodised red/blue (tileable, 512 px, with mips)."""
    os.makedirs(TEX_DIR, exist_ok=True)
    n = 512
    rng = np.random.default_rng(11)
    files = {}
    # cast aluminium: soft mottling + fine sand grain, gentle bump
    mott = _noise(n, rng, 40); grain = _noise(n, rng, 1); grain2 = _noise(n, rng, 3)
    v = 0.62 + 0.010 * mott + 0.005 * grain                  # v25 first pass (0.035/0.022) read as sandpaper up close
    files["alu"] = (_rgba(np.stack([v, v * 1.005, v * 1.02], -1)), _normal_from_height(0.7 * grain2 + 0.3 * grain, 0.5))
    # black crinkle: wrinkle ridges from |noise| bands
    w = np.abs(_noise(n, rng, 4)) + 0.6 * np.abs(_noise(n, rng, 2))
    w = 1.0 - np.clip(w / w.max(), 0, 1) ** 0.5
    c = 0.055 + 0.03 * w + 0.01 * grain
    files["crinkle"] = (_rgba(np.stack([c, c, c * 1.05], -1)), _normal_from_height(w, 6.0))
    flat = np.full((4, 4, 3), 0.5)
    files["red"] = (_rgba(np.broadcast_to(np.array([0.62, 0.05, 0.04]), (16, 16, 3)).copy()), None)
    files["blue"] = (_rgba(np.broadcast_to(np.array([0.06, 0.20, 0.72]), (16, 16, 3)).copy()), None)
    out = {}
    for k, (d, nm) in files.items():
        dn = f"v8_{k}_d.dds"
        with open(os.path.join(TEX_DIR, dn), "wb") as f:
            f.write(v25._dds(v25._mips(d)))
        out[k] = [dn]
        if nm is not None:
            nn = f"v8_{k}_nm.dds"
            with open(os.path.join(TEX_DIR, nn), "wb") as f:
                f.write(v25._dds(v25._mips(nm)))
            out[k].append(nn)
    return out


MATS = {   # kn5 name: (texture key, shader, props, viewport colour)
    "v8_cast_alu": ("alu", "ksPerPixelNM", dict(ksAmbient=0.42, ksDiffuse=0.45, ksSpecular=0.22, ksSpecularEXP=18.0), (0.62, 0.63, 0.65)),
    "v8_crinkle_black": ("crinkle", "ksPerPixelNM", dict(ksAmbient=0.35, ksDiffuse=0.45, ksSpecular=0.12, ksSpecularEXP=12.0), (0.06, 0.06, 0.065)),
    "v8_anodised_red": ("red", "ksPerPixel", dict(ksAmbient=0.45, ksDiffuse=0.55, ksSpecular=0.45, ksSpecularEXP=40.0), (0.62, 0.05, 0.04)),
    "v8_anodised_blue": ("blue", "ksPerPixel", dict(ksAmbient=0.45, ksDiffuse=0.55, ksSpecular=0.45, ksSpecularEXP=40.0), (0.06, 0.2, 0.72)),
}


def materials():
    files = textures()
    nm_base = json.loads(bpy.data.materials["INT_Cinture"]["kn5_def"])
    plain_base = json.loads(ba.material(ba.TRIM)["kn5_def"]) if False else None
    out = {}
    for name, (key, shader, props, vc) in MATS.items():
        if shader == "ksPerPixelNM":
            pr = []
            for p in nm_base["props"]:
                q = list(p)
                if q[0] in props:
                    q[1] = props[q[0]]
                if q[0] in ("fresnelC", "fresnelMaxLevel", "isAdditive"):
                    q[1] = 0.0
                pr.append(q)
            samp = [["txDiffuse", 0, files[key][0]], ["txNormal", 1, files[key][1]]]
        else:
            pr = [[k, float(v)] + [0.0] * 9 for k, v in dict(ksAmbient=props["ksAmbient"], ksDiffuse=props["ksDiffuse"],
                                                              ksSpecular=props["ksSpecular"], ksSpecularEXP=props["ksSpecularEXP"],
                                                              ksEmissive=0.0, ksAlphaRef=0.0).items()]
            samp = [["txDiffuse", 0, files[key][0]]]
        d = dict(name=name, shader=shader, blend=0, alphaTested=0, depth=0, props=pr, samplers=samp, tex_dir=TEX_DIR)
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m["kn5_def"] = json.dumps(d); m["lod_fallback"] = ba.TRIM
        m.diffuse_color = (*vc, 1.0); m.use_fake_user = True
        out[name] = m
    return out


# ---- geometry helpers (world space, return (verts, faces)) -------------------------------------------------------
def sweep(points, radius, n=SIDES, caps=True, r_end=None):
    """Tube along a polyline with parallel-transport frames (no twisting where the path turns vertical)."""
    P = [Vector(p) for p in points]
    T = []
    for i in range(len(P)):
        a, b = P[max(i - 1, 0)], P[min(i + 1, len(P) - 1)]
        T.append((b - a).normalized())
    ref = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    u = T[0].cross(ref).normalized()
    secs = []
    for i, p in enumerate(P):
        if i:
            axis = T[i - 1].cross(T[i])
            if axis.length > 1e-9:
                ang = T[i - 1].angle(T[i])
                u = (Matrix.Rotation(ang, 3, axis.normalized()) @ u)
            u = (u - T[i] * u.dot(T[i])).normalized()
        v = T[i].cross(u)
        rr = radius if r_end is None else radius + (r_end - radius) * i / (len(P) - 1)
        secs.append([tuple(p + (u * math.cos(2 * math.pi * k / n) + v * math.sin(2 * math.pi * k / n)) * rr) for k in range(n)])
    return ba.loft(secs, caps=caps)


def bezier(p0, p1, p2, p3, steps=16):
    p0, p1, p2, p3 = (Vector(p) for p in (p0, p1, p2, p3))
    return [((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + (t ** 3) * p3
            for t in [k / steps for k in range(steps + 1)]]


def path_through(points, steps=8, tension=0.5):
    """Smooth curve through control points (Catmull-Rom)."""
    P = [Vector(p) for p in points]
    out = []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
        m1, m2 = (p2 - p0) * tension, (p3 - p1) * tension
        for k in range(steps):
            t = k / steps
            h00, h10, h01, h11 = 2*t**3 - 3*t**2 + 1, t**3 - 2*t**2 + t, -2*t**3 + 3*t**2, t**3 - t**2
            out.append(p1 * h00 + m1 * h10 + p2 * h01 + m2 * h11)
    out.append(P[-1])
    return out


def lathe(profile, centre, axis, n=SIDES, caps=True):
    """Revolve [(radius, distance along axis)] around axis through centre."""
    c, a = Vector(centre), Vector(axis).normalized()
    ref = Vector((0, 0, 1)) if abs(a.z) < 0.9 else Vector((1, 0, 0))
    u = a.cross(ref).normalized(); v = a.cross(u)
    secs = [[tuple(c + a * d + (u * math.cos(2 * math.pi * k / n) + v * math.sin(2 * math.pi * k / n)) * max(rad, 1e-4))
             for k in range(n)] for rad, d in profile]
    return ba.loft(secs, caps=caps)


def prism_y(outline_xz, y0, y1, chamfer=0.0):
    """2D outline in x-z (CCW) extruded along y; optional chamfer = the end outlines shrink towards their centroid."""
    cx = sum(p[0] for p in outline_xz) / len(outline_xz); cz = sum(p[1] for p in outline_xz) / len(outline_xz)
    def sec(y, s):
        return [(cx + (x - cx) * s, y, cz + (z - cz) * s) for x, z in outline_xz]
    if chamfer:
        return ba.loft([sec(y0, 1 - chamfer), sec(y0 + 0.006, 1.0), sec(y1 - 0.006, 1.0), sec(y1, 1 - chamfer)])
    return ba.loft([sec(y0, 1.0), sec(y1, 1.0)])


def rbox(centre, ax, ay, az, bevel=0.004, segs=2):
    """Box with bevelled edges; ax/ay/az are half-extent vectors."""
    c, ax, ay, az = Vector(centre), Vector(ax), Vector(ay), Vector(az)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel / max(min(ax.length, ay.length, az.length), 1e-6),
                        segments=segs, affect="EDGES", profile=0.5)
    M = Matrix((ax, ay, az)).transposed()
    verts = [tuple(c + M @ v.co) for v in bm.verts]
    faces = [tuple(v.index for v in f.verts) for f in bm.faces]
    bm.free()
    return verts, faces


def bank_axes(side):
    """side +1 = left bank (+x). a = cylinder axis (out of the V), b = across the head towards the outside."""
    s = math.radians(BLOCK["bank_deg"])
    a = Vector((side * math.sin(s), 0, math.cos(s)))
    b = Vector((side * math.cos(s), 0, -math.sin(s)))
    return a, b


def bank_point(side, along, across, y):
    a, b = bank_axes(side)
    return Vector((0, y, C.z)) + a * along + b * across


def cyl_ys(side):
    off = 0.0 if side > 0 else HEAD["offset"]
    return [CYL["first"] + off + CYL["pitch"] * k for k in range(CYL["n"])]


def hexbolt(p, axis, r=0.0055, h=0.006):
    return lathe([(r * 0.98, -0.001), (r, 0.0), (r, h * 0.85), (r * 0.75, h)], p, axis, n=6)


# ---- the engine ----------------------------------------------------------------------------------------------------
def block_outline(top_extra=0.0):
    """Front-view outline (x, z), CCW: skirt, deck corners (or head tops with top_extra), valley."""
    B = BLOCK
    pts = [(-B["skirt"], B["pan_top"]), (B["skirt"], B["pan_top"]), (B["skirt"], 0.245)]
    for side in (1, -1):
        outer = bank_point(side, B["deck"] + top_extra, B["deck_half"] if not top_extra else HEAD["half"], 0)
        inner = bank_point(side, B["deck"] + top_extra, -(B["deck_half"] if not top_extra else HEAD["half"]), 0)
        seq = [(outer.x, outer.z), (inner.x, inner.z)] if side > 0 else [(inner.x, inner.z), (outer.x, outer.z)]
        if side > 0:
            pts += seq + [(0.035, B["valley_z"])]
        else:
            pts += [(-0.035, B["valley_z"])] + seq
    pts.append((-B["skirt"], 0.245))
    return pts


def parts_block():
    B = BLOCK
    alu, dark = [], []
    alu.append(prism_y(block_outline(), B["y0"], B["y1"], chamfer=0.02))
    # side ribs between the cylinders, freeze plugs, mount brackets
    for sx in (1, -1):
        for k in range(CYL["n"] + 1):
            y = CYL["first"] - CYL["pitch"] / 2 + CYL["pitch"] * k + (0 if sx > 0 else HEAD["offset"] / 2)
            alu.append(rbox((sx * (B["skirt"] + 0.004), y, 0.19), (0.006, 0, 0), (0, 0.007, 0), (0, 0, 0.052), bevel=0.002))
        for y in (-1.33, -1.12):
            alu.append(lathe([(0.0, 0.0), (0.017, 0.0), (0.017, 0.004), (0.014, 0.006), (0.0, 0.006)],
                             (sx * B["skirt"], y, 0.205), (sx, 0, 0), n=16))
        for y in (-1.373, -1.070):                       # the subframe's mount pads (x +-0.26, top 0.19)
            alu.append(rbox((sx * 0.236, y, 0.222), (0.024, 0, 0), (0, 0.024, 0), (0, 0, 0.016), bevel=0.003))
            dark.append(lathe([(0.020, -0.02), (0.022, -0.016), (0.022, 0.016), (0.020, 0.02)], (sx * 0.262, y, 0.208), (0, 1, 0), n=16))
    # dry-sump pan with a flange and bolts
    ym = (B["y0"] + B["y1"]) / 2; hl = (B["y1"] - B["y0"]) / 2
    alu.append(rbox((0, ym, (B["pan_z"] + B["pan_top"]) / 2), (B["skirt"] - 0.012, 0, 0), (0, hl - 0.012, 0),
                    (0, 0, (B["pan_top"] - B["pan_z"]) / 2), bevel=0.005))
    alu.append(rbox((0, ym, B["pan_top"] + 0.002), (B["skirt"] + 0.004, 0, 0), (0, hl, 0), (0, 0, 0.003), bevel=0.0015))
    bolts = []
    for k in range(9):
        y = B["y0"] + 0.02 + k * (hl * 2 - 0.04) / 8
        for sx in (1, -1):
            bolts.append(hexbolt((sx * (B["skirt"] - 0.006), y, B["pan_top"] - 0.004), (0, 0, -1), r=0.0045, h=0.005))
    return alu, dark, bolts


def parts_heads():
    H, B = HEAD, BLOCK
    alu, crinkle, black, steel, blue, red = [], [], [], [], [], []
    for side in (1, -1):
        a, b = bank_axes(side)
        off = 0.0 if side > 0 else H["offset"]
        y0, y1 = H["y0"] + off, H["y1"] + off
        yl = (y1 - y0) / 2; ym = (y0 + y1) / 2
        base = Vector((0, ym, C.z))
        alu.append(rbox(base + a * (B["deck"] + H["h"] / 2), b * H["half"], (0, yl, 0), a * (H["h"] / 2), bevel=0.006))
        top = B["deck"] + H["h"]
        crinkle.append(rbox(base + a * (top + H["cover_h"] / 2), b * H["cover_half"], (0, yl - 0.008, 0), a * (H["cover_h"] / 2),
                            bevel=0.012, segs=3))
        ctop = top + H["cover_h"]
        for k in range(CYL["n"] + 1):                    # cast ribs across the cover between the coils
            y = CYL["first"] + off - CYL["pitch"] / 2 + CYL["pitch"] * k
            if y0 + 0.02 < y < y1 - 0.02:
                crinkle.append(rbox(base + a * (ctop - 0.002) + Vector((0, y - ym, 0)), b * 0.080, (0, 0.004, 0), a * 0.005, bevel=0.0018))
        for k in range(7):                               # cover bolts along both long edges + ends
            y = y0 + 0.03 + k * (2 * yl - 0.06) / 6
            for s2 in (1, -1):
                p = base + a * (ctop - 0.006) + b * (s2 * (H["cover_half"] - 0.012)) + Vector((0, y - ym, 0))
                steel.append(hexbolt(p, a, r=0.005, h=0.007))
        for y in cyl_ys(side):                           # coil-on-plug packs + connectors
            p = base + a * (ctop + 0.020) + Vector((0, y - ym, 0))
            black.append(rbox(p, b * 0.017, (0, 0.022, 0), a * 0.020, bevel=0.004))
            black.append(rbox(p + a * 0.020 - b * 0.012, b * 0.008, (0, 0.010, 0), a * 0.008, bevel=0.002))
        loom = [base + a * (ctop + 0.046) - b * 0.012 + Vector((0, y - ym, 0)) for y in np.linspace(y0 + 0.02, y1 + 0.06, 8)]
        loom += [Vector((side * 0.06, -0.90, 0.52)), Vector((side * 0.05, -0.86, 0.50))]
        black.append(sweep(path_through(loom, steps=4), 0.008, n=10))
        # cam-drive housings at the head fronts (blend into the timing cover)
        alu.append(rbox(base + a * (B["deck"] + H["h"] / 2 + 0.01) + Vector((0, y0 - ym - 0.012, 0)), b * (H["half"] - 0.004),
                        (0, 0.016, 0), a * (H["h"] / 2 + 0.012), bevel=0.008))
        # exhaust-side port flanges
        for y in cyl_ys(side):
            p = base + a * (B["deck"] + H["h"] * 0.48) + b * (H["half"] + 0.004) + Vector((0, y - ym, 0))
            steel.append(rbox(p, b * 0.005, (0, 0.025, 0), a * 0.026, bevel=0.002))
        # breather (blue anodised) at the rear of each cover, oil filler (red) on the left cover's front
        bp = base + a * ctop + Vector((0, y1 - 0.045 - ym, 0)) - b * 0.05
        blue.append(lathe([(0.0, 0.0), (0.013, 0.0), (0.013, 0.012), (0.010, 0.014), (0.010, 0.026), (0.0, 0.026)], bp, a, n=12))
        if side > 0:
            fp = base + a * ctop + Vector((0, y0 + 0.05 - ym, 0)) + b * 0.04
            red.append(lathe([(0.0, 0.0), (0.024, 0.0), (0.024, 0.010), (0.020, 0.014), (0.0, 0.014)], fp, a, n=20))
    return alu, crinkle, black, steel, blue, red


def intake_port(side, y):
    return bank_point(side, BLOCK["deck"] + HEAD["h"] * 0.55, -HEAD["half"] - 0.002, y)


def parts_intake():
    alu, black, blue, red, steel = [], [], [], [], []
    PL = dict(y0=-1.415, y1=-1.005, half=0.060, z0=0.402, z1=0.503)
    ym = (PL["y0"] + PL["y1"]) / 2
    alu.append(rbox((0, ym, (PL["z0"] + PL["z1"]) / 2), (PL["half"], 0, 0), (0, (PL["y1"] - PL["y0"]) / 2, 0),
                    (0, 0, (PL["z1"] - PL["z0"]) / 2), bevel=0.022, segs=3))
    for k in range(5):                                   # top ribs
        y = PL["y0"] + 0.05 + k * 0.077
        alu.append(rbox((0, y, PL["z1"] - 0.001), (PL["half"] - 0.02, 0, 0), (0, 0.004, 0), (0, 0, 0.004), bevel=0.0015))
    for side in (1, -1):
        for y in cyl_ys(side):
            port = intake_port(side, y)
            start = Vector((side * (PL["half"] - 0.012), y, port.z + 0.012))
            alu.append(sweep([start, start.lerp(port, 0.5) + Vector((0, 0, 0.004)), port], 0.019, n=14))
            a, b = bank_axes(side)
            alu.append(lathe([(0.0, 0.0), (0.026, 0.0), (0.026, 0.006), (0.0, 0.006)], port - b * 0.002, b, n=14))
            inj = start.lerp(port, 0.55) + Vector((0, 0, 0.022))
            black.append(sweep([inj + Vector((side * 0.018, 0, 0.040)), inj], 0.0065, n=10))
            blue.append(lathe([(0.0, 0.0), (0.0085, 0.0), (0.0085, 0.010), (0.0, 0.010)], inj + Vector((side * 0.018, 0, 0.040)),
                              Vector((side * 0.41, 0, 0.91)), n=10))
        rail = [Vector((side * 0.090, PL["y0"] - 0.012, 0.497)), Vector((side * 0.090, PL["y1"] + 0.025, 0.497))]
        alu.append(sweep(rail, 0.0095, n=12))
        for end in rail:
            red.append(lathe([(0.0, -0.012), (0.012, -0.012), (0.012, 0.012), (0.0, 0.012)], end, (0, 1, 0), n=12))
        feed = [rail[1], rail[1] + Vector((0, 0.06, 0.004)), Vector((side * 0.10, -0.90, 0.47)), Vector((side * 0.12, -0.86, 0.44))]
        black.append(sweep(path_through(feed, steps=6), 0.0065, n=10))
    # throttle body + linkage + cone filter at the front
    tb0, tb1 = Vector((0, PL["y0"] + 0.004, 0.462)), Vector((0, PL["y0"] - 0.050, 0.462))
    alu.append(lathe([(0.044, 0.0), (0.044, 0.050), (0.040, 0.054)], tb0, (0, -1, 0), n=24))
    red.append(lathe([(0.0465, 0.016), (0.0465, 0.026)], tb0, (0, -1, 0), n=24, caps=False))
    black.append(rbox(tb0 + Vector((-0.050, -0.026, 0.0)), (0.009, 0, 0), (0, 0.016, 0), (0, 0, 0.018), bevel=0.003))   # TPS
    steel.append(rbox(tb0 + Vector((0.050, -0.026, 0.010)), (0.003, 0, 0), (0, 0.010, 0), (0, 0, 0.026), bevel=0.0015))  # lever
    fil = tb1
    black.append(lathe([(0.046, 0.0), (0.046, 0.010), (0.055, 0.016), (0.055, 0.060), (0.048, 0.068), (0.030, 0.071), (0.0, 0.071)],
                       fil, (0, -1, 0), n=28))
    red.append(lathe([(0.0485, 0.0), (0.0485, 0.009)], fil, (0, -1, 0), n=28, caps=False))      # clamp band
    return alu, black, blue, red, steel


def _belt_path(pulleys, n_arc=10):
    """Closed belt around circles (x, z, r) listed anticlockwise in the x-z plane (front view)."""
    pts = []
    m = len(pulleys)
    tang = []
    for i in range(m):
        (x1, z1, r1), (x2, z2, r2) = pulleys[i], pulleys[(i + 1) % m]
        d = Vector((x2 - x1, z2 - z1)); L = d.length; dn = d / L
        ang = math.acos(max(-1, min(1, (r1 - r2) / L)))
        base = math.atan2(dn.y, dn.x)
        th = base - ang                              # outer tangent on the right of the travel direction
        n = Vector((math.cos(th), math.sin(th)))
        tang.append((Vector((x1, z1)) + n * r1, Vector((x2, z2)) + n * r2, th))
    for i in range(m):
        x, z, rr = pulleys[(i + 1) % m]
        a0 = tang[i][2]; a1 = tang[(i + 1) % m][2]
        da = (a1 - a0) % (2 * math.pi)
        if da > math.pi * 1.98:
            da -= 2 * math.pi
        pts.append(tang[i][0])
        pts += [Vector((x + rr * math.cos(a0 + da * k / n_arc), z + rr * math.sin(a0 + da * k / n_arc))) for k in range(n_arc + 1)]
    return pts


def parts_front():
    alu, black, steel, red = [], [], [], []
    yf = BLOCK["y0"]                                  # block front face
    tc0, tc1 = yf - 0.035, yf + 0.002
    alu.append(prism_y(block_outline(top_extra=HEAD["h"] - 0.004), tc0, tc1, chamfer=0.03))
    outline = block_outline(top_extra=HEAD["h"] - 0.004)
    for k, (x, z) in enumerate(outline):                # perimeter bolts
        nx, nz = outline[(k + 1) % len(outline)]
        for t in (0.25, 0.75):
            px, pz = x + (nx - x) * t, z + (nz - z) * t
            cx = sum(p[0] for p in outline) / len(outline); cz = sum(p[1] for p in outline) / len(outline)
            q = Vector((px + (cx - px) * 0.06, tc0, pz + (cz - pz) * 0.06))
            steel.append(hexbolt(q, (0, -1, 0), r=0.0045, h=0.005))
    yb = tc0 - 0.024                                  # belt plane
    crank = (0.0, C.z, 0.072); wp = (0.0, 0.330, 0.050); alt = (-0.270, 0.268, 0.030); idl = (0.105, 0.290, 0.026)
    for (x, z, rr), d in ((crank, 0.032), (wp, 0.028), (alt, 0.026), (idl, 0.022)):
        alu.append(lathe([(0.0, -0.002), (rr - 0.004, -0.002), (rr, 0.002), (rr, d - 0.004), (rr - 0.004, d), (0.0, d)],
                         (x, tc0 + 0.004, z), (0, -1, 0), n=28))
        steel.append(lathe([(0.0, 0.0), (0.011, 0.0), (0.011, 0.006), (0.0, 0.006)], (x, tc0 + 0.004 - d, z), (0, -1, 0), n=6))
    alu.append(lathe([(0.0, 0.0), (0.080, 0.0), (0.080, 0.012), (0.0, 0.012)], (0, tc0 + 0.004, C.z), (0, -1, 0), n=32))  # damper
    alu.append(lathe([(0.046, 0.0), (0.046, 0.022)], (0, tc0 + 0.004, 0.330), (0, 1, 0), n=20))               # pump body
    belt2 = _belt_path([crank, idl, wp, alt])
    sec_w, sec_t = 0.018, 0.004
    b_out = []
    for i, p in enumerate(belt2):
        q = belt2[(i + 1) % len(belt2)] - belt2[i - 1]
        nn = Vector((q.y, -q.x)).normalized()
        b_out.append((p, nn))
    loops = []
    for p, nn in b_out:
        o = p + nn * sec_t
        loops.append([(p.x, yb - sec_w / 2, p.y), (o.x, yb - sec_w / 2, o.y), (o.x, yb + sec_w / 2, o.y), (p.x, yb + sec_w / 2, p.y)])
    bv, bf = [], []
    k = len(loops)
    for l in loops:
        bv += l
    for i in range(k):
        a0, a1 = i * 4, ((i + 1) % k) * 4
        for j in range(4):
            bf.append((a0 + j, a0 + (j + 1) % 4, a1 + (j + 1) % 4, a1 + j))
    black.append((bv, bf))
    # alternator (outboard of the block front, in the belt plane) + bracket
    ax0 = Vector((alt[0], tc0 + 0.004 - 0.026 + 0.026, alt[1]))
    alu.append(lathe([(0.020, 0.0), (0.050, 0.004), (0.052, 0.012), (0.052, 0.070), (0.046, 0.080), (0.030, 0.084), (0.0, 0.084)],
                     Vector((alt[0], tc0 + 0.006, alt[1])), (0, 1, 0), n=24))
    for k in range(6):
        y = tc0 + 0.02 + k * 0.01
        alu.append(lathe([(0.0535, 0.0), (0.0535, 0.003)], Vector((alt[0], y, alt[1])), (0, 1, 0), n=24, caps=False))
    alu.append(rbox((alt[0] + 0.040, tc0 + 0.040, alt[1] - 0.030), (0.035, 0, 0), (0, 0.008, 0), (0, 0, 0.012), bevel=0.003))
    return alu, black, steel, red


def parts_aux():
    """Dry-sump pump + lines, starter, bellhousing, oil tank."""
    alu, black, blue, steel = [], [], [], []
    # scavenge/pressure pump stack on the left, between the mounts
    for k in range(4):
        y = -1.31 + k * 0.047
        alu.append(lathe([(0.032, 0.0), (0.034, 0.004), (0.034, 0.039), (0.032, 0.043)], (0.232, y, 0.162), (0, 1, 0), n=20))
        alu.append(lathe([(0.037, 0.0), (0.037, 0.004)], (0.232, y + 0.043, 0.162), (0, 1, 0), n=20))
        blue.append(lathe([(0.0, 0.0), (0.011, 0.0), (0.011, 0.012), (0.0, 0.012)], (0.232, y + 0.021, 0.128), (0, 0, -1), n=8))
        line = [Vector((0.232, y + 0.021, 0.118)), Vector((0.226, y + 0.021, 0.108)), Vector((0.205, y + 0.010, 0.116)),
                Vector((0.180, y + 0.010, 0.124))]
        black.append(sweep(path_through(line, steps=4), 0.0075, n=10))
    alu.append(lathe([(0.0, 0.0), (0.030, 0.0), (0.030, 0.010), (0.0, 0.010)], (0.232, -1.32, 0.162), (0, -1, 0), n=20))
    # pressure line pump -> block, and to the tank in the bay's left-front corner
    black.append(sweep(path_through([Vector((0.232, -1.32, 0.19)), Vector((0.235, -1.40, 0.235)), Vector((0.200, -1.43, 0.27))], 6), 0.0085, n=10))
    tank = Vector((0.325, -1.470, 0.160))           # left front corner, clear of the inner wing (x 0.393)
    alu.append(lathe([(0.0, 0.0), (0.046, 0.0), (0.052, 0.008), (0.052, 0.200), (0.046, 0.210), (0.020, 0.217), (0.0, 0.217)], tank, (0, 0, 1), n=28))
    blue.append(lathe([(0.0, 0.0), (0.022, 0.0), (0.022, 0.014), (0.0, 0.014)], tank + Vector((0, 0, 0.217)), (0, 0, 1), n=16))
    black.append(sweep(path_through([tank + Vector((-0.04, 0.03, 0.03)), Vector((0.29, -1.40, 0.15)), Vector((0.25, -1.33, 0.17))], 6), 0.0085, n=10))
    black.append(sweep(path_through([tank + Vector((-0.045, 0.02, 0.19)), Vector((0.27, -1.42, 0.33)), Vector((0.20, -1.42, 0.36))], 6), 0.0075, n=10))
    # starter on the right, ahead of the bellhousing
    alu.append(lathe([(0.0, 0.0), (0.040, 0.0), (0.042, 0.006), (0.042, 0.100), (0.036, 0.110), (0.030, 0.140), (0.0, 0.142)],
                     (-0.200, -1.040, 0.150), (0, 1, 0), n=20))
    black.append(lathe([(0.0, 0.0), (0.022, 0.0), (0.022, 0.050), (0.0, 0.050)], (-0.200, -1.000, 0.200), (0, 1, 0), n=14))   # solenoid
    # bellhousing tapering into the tunnel mouth
    def sec(y, hw, top, bot):
        cz, hh = (top + bot) / 2, (top - bot) / 2
        return [(x, y, cz + z) for x, z in v25._superellipse(hw, hh, 32, 3.0)]
    # ends at the bulkhead (y -0.875) inside the tunnel's line: the cabin tunnel's ceiling is at z ~0.21 from y -0.80
    alu.append(ba.loft([sec(-0.990, 0.205, 0.400, 0.122), sec(-0.960, 0.192, 0.380, 0.125), sec(-0.930, 0.160, 0.330, 0.128),
                        sec(-0.900, 0.120, 0.265, 0.130), sec(-0.875, 0.090, 0.212, 0.132)]))
    for k in range(10):
        t = 2 * math.pi * k / 10
        steel.append(hexbolt((0.205 * math.cos(t) * 0.98, -0.993, 0.261 + 0.139 * math.sin(t) * 0.98), (0, 1, 0), r=0.0045, h=0.006))
    return alu, black, blue, steel


# Exhaust: 4-into-1 per bank into vertical collectors just ahead of the bulkhead (y -0.99, clear of the crossmember at
# -1.038). The left collector drops into the ORIGINAL front pipe (it is part of the underbody mesh, x 0.24 from its open
# front end (0.244, -0.936, 0.036) back to the silencer pipe at y 0.825); the right one drops under the floor, runs
# back along the right side and crosses under the gearbox tail (tunnel underside -0.02) into the same pipe at y ~0.
COLLECTOR = dict(y=-0.990, top=0.215, bot=0.120, r_top=0.040, r_bot=0.026, x=0.318)
ORIG_PIPE_FRONT = Vector((0.244, -0.936, 0.036))


def _header_path(side, i, y):
    """One primary: port -> out and down -> along the block side at ~0.27 -> down into a 2x2 slot on the collector top."""
    a, b = bank_axes(side)
    base = Vector((0, y, C.z))
    port = base + a * (BLOCK["deck"] + HEAD["h"] * 0.48) + b * (HEAD["half"] + 0.008)
    lane_x = [0.300, 0.336, 0.300, 0.336][i]
    sx = COLLECTOR["x"] + (0.016 if lane_x > 0.31 else -0.016)
    sy = COLLECTOR["y"] + (-0.016 if i < 2 else 0.016)
    slot = Vector((side * sx, sy, COLLECTOR["top"]))
    p1 = port + b * 0.030
    p2 = Vector((side * lane_x, y + 0.030, 0.272))
    p3 = Vector((side * (lane_x + sx) / 2, sy - 0.030 if y < sy - 0.06 else (y + sy) / 2, 0.268))
    p4 = slot + Vector((0, 0, 0.030))
    return path_through([port, p1, p2, p3, p4, slot], steps=6)


def parts_exhaust():
    steel = []
    R = 0.0175
    paths = {}
    co = COLLECTOR
    for side in (1, -1):
        for i, y in enumerate(cyl_ys(side)):
            pth = _header_path(side, i, y)
            paths[(side, i)] = pth
            steel.append(sweep(pth, R, n=14))
            steel.append(rbox(pth[0], bank_axes(side)[1] * 0.004, (0, 0.025, 0), bank_axes(side)[0] * 0.026, bevel=0.002))
        top = Vector((side * co["x"], co["y"], co["top"] + 0.006))
        steel.append(lathe([(co["r_top"], 0.0), (co["r_top"], 0.012), (co["r_bot"] + 0.004, 0.070),
                            (co["r_bot"], co["top"] - co["bot"])], top, (0, 0, -1), n=20))
        bot = Vector((side * co["x"], co["y"], co["bot"]))
        if side > 0:
            down = [bot, Vector((0.318, -0.988, 0.075)), Vector((0.300, -0.972, 0.048)), Vector((0.272, -0.952, 0.040)),
                    ORIG_PIPE_FRONT + Vector((0.004, 0.006, 0.0))]
            steel.append(sweep(path_through(down, steps=6), co["r_bot"], n=16, r_end=0.024))
        else:
            down = [bot, Vector((-0.318, -0.989, 0.050)), Vector((-0.314, -0.965, 0.000)), Vector((-0.306, -0.905, -0.030)),
                    Vector((-0.296, -0.700, -0.033)), Vector((-0.280, -0.420, -0.034)), Vector((-0.245, -0.200, -0.038)),
                    Vector((-0.150, -0.090, -0.048)), Vector((0.000, -0.055, -0.052)), Vector((0.120, -0.030, -0.046)),
                    Vector((0.196, 0.000, -0.024)), Vector((0.222, 0.020, -0.010))]
            steel.append(sweep(path_through(down, steps=6), co["r_bot"], n=16, r_end=0.022))
    return steel, paths


def build():
    sc = ba.main_scene()
    bpy.context.window.scene = sc
    for o in [o for o in bpy.data.objects if o.get("v8_part")]:
        bpy.data.objects.remove(o)
    M = materials()
    trim, steel_m = ba.material(ba.TRIM), ba.material("Material #503ds")
    tuv = ba.pick_uv(trim, (0.70, 0.30, 0.75))[1]; suv = ba.pick_uv(steel_m, (0.30, 1.00, 0.00))[1]
    groups = {"alu": [], "crinkle": [], "black": [], "steel": [], "blue": [], "red": [], "headers": []}
    a, d, bolts = parts_block(); groups["alu"] += a; groups["black"] += d; groups["steel"] += bolts
    a, cr, bl, st, blu, rd = parts_heads(); groups["alu"] += a; groups["crinkle"] += cr; groups["black"] += bl
    groups["steel"] += st; groups["blue"] += blu; groups["red"] += rd
    a, bl, blu, rd, st = parts_intake(); groups["alu"] += a; groups["black"] += bl; groups["blue"] += blu; groups["red"] += rd; groups["steel"] += st
    a, bl, st, rd = parts_front(); groups["alu"] += a; groups["black"] += bl; groups["steel"] += st; groups["red"] += rd
    a, bl, blu, st = parts_aux(); groups["alu"] += a; groups["black"] += bl; groups["blue"] += blu; groups["steel"] += st
    hd, paths = parts_exhaust(); groups["headers"] += hd
    spec = {"alu": ("V8_alloy", M["v8_cast_alu"], None), "crinkle": ("V8_cam_covers", M["v8_crinkle_black"], None),
            "black": ("V8_black", trim, tuv), "steel": ("V8_steel", steel_m, suv), "blue": ("V8_anodised_blue", M["v8_anodised_blue"], (0.5, 0.5)),
            "red": ("V8_anodised_red", M["v8_anodised_red"], (0.5, 0.5)), "headers": ("V8_exhaust", steel_m, suv)}
    out = {}
    for key, parts in groups.items():
        if not parts:
            continue
        name, mat, uv = spec[key]
        ob = ba.make_obj(name, ba.merge(*parts), mat, uv if uv else (0.0, 0.0), ba.root(), sharp_deg=40.0)
        if uv is None:
            box_uv(ob, tile=0.30 if key == "alu" else 0.07)
        ob["v8_part"] = True; ob["lod_skip"] = True
        out[name] = len(ob.data.polygons)
    bpy.context.view_layer.update()
    return out


def v8_tree():
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    for o in [o for o in ba.main_scene().objects if o.get("v8_part")]:
        t = o.data.copy(); t.transform(o.matrix_world); bm.from_mesh(t); bpy.data.meshes.remove(t)
    tree = BVHTree.FromBMesh(bm); bm.free()
    return tree


def clear_lr(dry=False):
    """COCKPIT_LR (__lr) copies of the bay: their coarse islands inside ENGINE_ZONE that the V8 occupies go too
    (shown beyond 7 m - with the bonnet open they would poke through the V8)."""
    tree = v8_tree()
    lo, hi = (np.array(b) for b in v25.ENGINE_ZONE)
    rep = {}
    for o in list(ba.main_scene().objects):
        nm = str(o.get("kn5_name") or o.name)
        if o.type != "MESH" or not nm.startswith("enginebay") or not nm.endswith("__lr") or o.name.startswith(v25.OLD_ENGINE_PREFIX):
            continue
        bm, W, comps = v25._islands_world(o)
        take = set()
        for c in comps:
            P = W[c]
            if ((P >= lo) & (P <= hi)).all(1).mean() < 0.5:
                continue
            for p in P:
                loc, nrm, idx, d = tree.find_nearest(Vector(p), 0.25)
                if loc is not None and (d < 0.02 or nrm.dot(Vector(p) - loc) < 0):
                    take.update(c); break
        bm.free()
        if take:
            rep[o.name] = len(take)
            if not dry:
                _stow(o, take)
    return rep


def _stow(o, take):
    name = v25.OLD_ENGINE_PREFIX + o.name
    old = bpy.data.objects.get(name)
    me = o.data.copy()
    b2 = bmesh.new(); b2.from_mesh(me); b2.verts.ensure_lookup_table()
    bmesh.ops.delete(b2, geom=[v for v in b2.verts if v.index not in take], context="VERTS"); b2.to_mesh(me); b2.free()
    b3 = bmesh.new(); b3.from_mesh(o.data); b3.verts.ensure_lookup_table()
    bmesh.ops.delete(b3, geom=[b3.verts[i] for i in take], context="VERTS"); b3.to_mesh(o.data); b3.free(); o.data.update()
    if old is not None:
        tmp = o.copy(); tmp.data = me
        for col in old.users_collection:
            col.objects.link(tmp)
        tmp.matrix_world = old.matrix_world.copy()
        old.hide_viewport = False
        with bpy.context.temp_override(active_object=old, object=old, selected_objects=[old, tmp], selected_editable_objects=[old, tmp]):
            bpy.ops.object.join()
        old.hide_viewport = True
    else:
        ob = o.copy(); ob.data = me; ob.name = name; me.name = name
        for col in o.users_collection:
            col.objects.link(ob)
        ob.parent = o.parent; ob.matrix_world = o.matrix_world.copy()
        ob["no_export"] = True; ob["oldeng_source"] = o.name; ob.hide_viewport = True


def clear_bay(gap=0.006, prefixes=("enginebay",), dry=False):
    """Bay islands (enginebay meshes incl. COCKPIT_LR copies) that the V8 runs through or touches -> OLDENG_ objects
    (hidden, not exported; v25.swap_engine_back() restores them)."""
    tree = v8_tree()
    sc = ba.main_scene()
    rep = {}
    for o in list(sc.objects):
        nm = str(o.get("kn5_name") or o.name)
        if o.type != "MESH" or not nm.startswith(prefixes) or o.name.startswith(v25.OLD_ENGINE_PREFIX) or not len(o.data.vertices):
            continue
        bm, W, comps = v25._islands_world(o)
        take = set()
        for c in comps:
            P = W[c]
            if P[:, 1].min() > -0.80 or P[:, 1].max() < -1.66:
                continue
            step = max(1, len(c) // 80)
            for p in P[::step]:
                loc, nrm, idx, d = tree.find_nearest(Vector(p), 0.25)
                if loc is not None and (d < gap or nrm.dot(Vector(p) - loc) < 0):
                    take.update(c); break
        bm.free()
        if not take:
            continue
        rep[o.name] = len(take)
        if dry:
            continue
        name = v25.OLD_ENGINE_PREFIX + o.name
        old = bpy.data.objects.get(name)
        me = o.data.copy()
        b2 = bmesh.new(); b2.from_mesh(me); b2.verts.ensure_lookup_table()
        bmesh.ops.delete(b2, geom=[v for v in b2.verts if v.index not in take], context="VERTS"); b2.to_mesh(me); b2.free()
        b3 = bmesh.new(); b3.from_mesh(o.data); b3.verts.ensure_lookup_table()
        bmesh.ops.delete(b3, geom=[b3.verts[i] for i in take], context="VERTS"); b3.to_mesh(o.data); b3.free(); o.data.update()
        if old is not None:                                  # add to the existing stow object
            tmp = o.copy(); tmp.data = me
            for col in old.users_collection:
                col.objects.link(tmp)
            tmp.matrix_world = old.matrix_world.copy()
            old.hide_viewport = False
            with bpy.context.temp_override(active_object=old, object=old, selected_objects=[old, tmp], selected_editable_objects=[old, tmp]):
                bpy.ops.object.join()
            old.hide_viewport = True
        else:
            ob = o.copy(); ob.data = me; ob.name = name; me.name = name
            for col in o.users_collection:
                col.objects.link(ob)
            ob.parent = o.parent; ob.matrix_world = o.matrix_world.copy()
            ob["no_export"] = True; ob["oldeng_source"] = o.name; ob.hide_viewport = True
    return rep


def box_uv(ob, tile=0.12):
    """Triplanar-style UVs: each face projected on its dominant axis plane (world metres / tile)."""
    me = ob.data; mw = ob.matrix_world; rot = mw.to_3x3()
    uvl = me.uv_layers.active or me.uv_layers.new(name="UVMap")
    co = [mw @ v.co for v in me.vertices]
    for poly in me.polygons:
        nrm = rot @ poly.normal
        k = max(range(3), key=lambda i: abs(nrm[i]))
        a1, a2 = [(1, 2), (0, 2), (0, 1)][k]
        for li in poly.loop_indices:
            p = co[me.loops[li].vertex_index]
            uvl.data[li].uv = (p[a1] / tile, p[a2] / tile)

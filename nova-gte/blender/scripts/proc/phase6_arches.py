"""Phase 6 - procedural Nova GTE: boxed wheel arches, flared lower body and wheel wells (left side, mirrored).

Builds the side panels that carry the arches: Fender_Front_Left (front bumper side -> door front shut line) and
Quarter_Rear_Left (door rear shut line -> tail), each its own object with a Mirror modifier (X, clipping, merge).
Frame: metres, x+ = car's left, y- = front, z up.

- Axles: read from the Axle_Front / Axle_Rear locators (Phase 1); tyre 175/65 R14 (dims wheel_radius).
- Arch openings: the photo-traced arch outlines of Phase 2 (Arch_Profile_*), centred on the axles, ends carried
  straight down to the sill / bumper line; checked against the tyre with a clearance.
- Flare ("boxed"): a lens-shaped blister over each arch - below the crease the body bulges out from the upper panel,
  deepest (STEP) over the wheel and fading to nothing at the lens ends, the step being the light band in Nik's
  pictures (data/proc/side_features.json: straight crease line + lens height, traced on the grey side picture).
  Blister at the factory width at the axle (FIA 1522 / 1529 mm); crease rows marked sharp. (Nik 2026-10-20: the
  first build had it inside out - upper panel pushed in instead of the blister pushed out.) The front fender also takes the hood block's taper.
- Panel outline: top = Side_Profile_Hood (front) / rear beltline + Side_Profile_Tailgate (rear); bottom = sill line
  of Side_Profile_Chassis and the bumper lower edges.
- Wheel wells: the arch lip is extruded straight inward (boxed edge) to WELL_CLEAR inside the tyre's inner face.
Audit raises NovaSpecError on any failure.
Run: blender -b blender/nova_proc.blend --python blender/scripts/proc/phase6_arches.py   (saves)"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phase4_front_block as p4      # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FEAT = os.path.join(ROOT, "data", "proc", "side_features.json")
TOL = 0.001
STEP = 0.030                 # upper panel inset at the full ledge (old body scan: 0.75 lower vs 0.72 upper)
TYRE_HALF_W = 0.175 / 2
WELL_CLEAR = 0.030           # well wall this far inside the tyre's inner face
ARCH_CLEAR = 0.005           # arch lip must clear the tyre by this much (radially)
DY = 0.04                    # column spacing away from the arches
NovaSpecError = p4.NovaSpecError


def dims_ext():
    D = p4.dims()
    sc = bpy.context.scene
    if "width_front_axle" not in D:                       # FIA body widths at the axles (docs/SPEC_SHEET.md)
        d = dict(sc["nova_gte_dimensions"]); d["width_front_axle"] = 1.522; d["width_rear_axle"] = 1.529
        sc["nova_gte_dimensions"] = d
        D = p4.dims()
    return D


def chain_pts(name, only=None):
    out = []
    for c in p4.template_chain(name, only=only):
        out += [(p[1], p[2], p[0]) for p in c]
    return out


def polyline_interp(P, y):
    P = sorted(P)
    ys = [p[0] for p in P]; zs = [p[1] for p in P]
    return float(np.interp(y, ys, zs))


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


class Side:
    """One side panel: outline, arch, flare data and the x rule."""
    def __init__(self, D, key, feats, axle_obj):
        self.D, self.key = D, key
        self.ax = axle_obj.matrix_world.translation.copy()
        self.r = D["wheel_radius"]
        self.track = D["track_front"] if key == "front" else D["track_rear"]
        self.x_flare = (D["width_front_axle"] if key == "front" else D["width_rear_axle"]) / 2
        self.x_well = self.track / 2 - TYRE_HALF_W - WELL_CLEAR
        f = feats["fits"][key]
        self.crease, self.lens, self.lens_y = f["crease"], f["lens"], f["y_range"]
        hood = chain_pts("Side_Profile_Hood")
        sill = [p for p in chain_pts("Side_Profile_Chassis")
                if p[2] in ("sill_front", "sill_rear", "front_bumper_lower_edge", "rear_bumper_lower_edge")]
        tail = chain_pts("Side_Profile_Tailgate")
        P = {p[2]: (p[0], p[1]) for p in hood + sill + tail}
        if key == "front":
            self.y0 = -D["length"] / 2
            self.y1 = float(np.mean(feats["features"]["door_front_y"]))
            self.upper = [P[n] for n in ("front_bumper_upper_edge", "front_bumper_top", "headlamp_top", "hood_nose",
                                         "hood_mid", "scuttle", "windshield_base")] + [(-D["length"] / 2, P["front_bumper_upper_edge"][1])]
            self.lower = [P["front_bumper_face"], (-D["length"] / 2, P["front_bumper_face"][1]),
                          P["front_bumper_lower_edge"], P["sill_front"], P["sill_rear"]]
        else:
            self.y0 = float(np.mean(feats["features"]["door_rear_y"]))
            self.y1 = D["length"] / 2
            belt = [tuple(p) for p in feats["features"]["beltline_rear"]]
            zb = float(np.mean([p[1] for p in belt]))
            self.upper = [(self.y0, zb), (P["tailgate_lower"][0] - 0.02, zb), P["tailgate_lower"], P["rear_bumper_top"],
                          P["rear_bumper_upper_edge"], (D["length"] / 2, P["rear_bumper_upper_edge"][1])]
            self.lower = [P["sill_front"], P["sill_rear"], P["rear_bumper_lower_edge"],
                          (D["length"] / 2, P["rear_bumper_face"][1]), P["rear_bumper_face"]]
        arch = [(v.co.y, v.co.z) for v in bpy.data.objects["Arch_Profile_" + key.title()].data.vertices]
        arch.sort()
        self.arch = self.resample_arch(arch, 0.012)
        self.taper = (lambda y: p4.TAPER * smoothstep(D["length"] / -2 + D["overhang_front"], -D["length"] / 2, y)) \
            if key == "front" else (lambda y: 0.0)

    @staticmethod
    def resample_arch(arch, step):
        A = np.array(arch)
        seg = np.hypot(np.diff(A[:, 0]), np.diff(A[:, 1])); s = np.r_[0, np.cumsum(seg)]
        t = np.linspace(0, s[-1], int(s[-1] / step) + 1)
        return np.c_[np.interp(t, s, A[:, 0]), np.interp(t, s, A[:, 1])]

    def z_low(self, y):
        return polyline_interp(self.lower, y)

    def z_top(self, y):
        return polyline_interp(self.upper, y)

    def z_arch(self, y):
        """Top of the arch opening at y (None outside the arch); the arch's ends drop straight to the sill line."""
        A = self.arch
        if y < A[0, 0] or y > A[-1, 0]:
            return None
        return float(np.interp(y, A[:, 0], A[:, 1]))

    def ledge(self, y):
        zl = float(np.polyval(self.crease, y))
        h = float(np.polyval(self.lens, y)) if self.lens_y[0] <= y <= self.lens_y[1] else 0.0
        return zl, max(0.0, h)

    def x_at(self, y, z, z_top):
        """Blister flare: the upper panel is the base surface (factory axle width - STEP); below the crease the body
        bulges OUT by the lens depth (full STEP over the wheel, fading to nothing at the lens ends)."""
        zl, h = self.ledge(y)
        depth = STEP * min(1.0, h / 0.03)
        xu = self.x_flare - STEP - self.taper(y)
        xf = xu + depth
        if z <= zl:
            return xf
        if z <= zl + max(h, 1e-4):
            t = (z - zl) / max(h, 1e-4)
            return xf + (xu - xf) * t
        if self.key == "front":                       # upper panel meets the hood block's outer edge at the top
            xh = p4.wing_half_width(self.D, y, z_top)
            t = (z - zl - h) / max(z_top - zl - h, 1e-4)
            return xu + (xh - xu) * min(1.0, max(0.0, t))
        return xu

    def stations(self):
        ys = set(np.round(np.arange(self.y0, self.y1 + 1e-9, DY), 5))
        ys |= set(np.round(self.arch[:, 0], 5))
        ys |= {round(self.y0, 5), round(self.y1, 5)}
        for p in self.upper + self.lower:
            if self.y0 <= p[0] <= self.y1:
                ys.add(round(p[0], 5))
        ys = sorted(ys)
        out = [ys[0]]
        for y in ys[1:]:
            if y - out[-1] > 0.002:
                out.append(y)
        return out


def build_panel(name, S, coll):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old)
    bm = bmesh.new()
    tag = bm.verts.layers.int.new("kind")         # 0 panel, 1 arch lip, 2 well wall inner, 3 crease row
    NL, NU = 6, 6
    cols = []
    for y in S.stations():
        za = S.z_arch(y)
        zb = za if za is not None else S.z_low(y)
        zt = S.z_top(y)
        zl, h = S.ledge(y)
        c1 = min(max(zl, zb), zt); c2 = min(max(zl + h, c1), zt)
        zs = list(np.linspace(zb, c1, NL + 1)) + [c2] + list(np.linspace(c2, zt, NU + 1))[1:]
        col = []
        for k, z in enumerate(zs):
            v = bm.verts.new((S.x_at(y, z, zt), y, z))
            v[tag] = 1 if (k == 0 and za is not None) else (3 if k in (NL, NL + 1) and h > 0.004 else 0)
            col.append(v)
        cols.append((y, za is not None, col))
    for (ya, _, A), (yb, _, B) in zip(cols[:-1], cols[1:]):
        for k in range(len(A) - 1):
            q = (A[k], B[k], B[k + 1], A[k + 1])
            if len({v for v in q}) == 4:
                bm.faces.new(q)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.0001)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=0.0001)
    # arch lip loop: the bottom vertices of the arch columns, plus the drops at both ends to the sill line
    lip = [col[0] for y, inarch, col in cols if inarch and col[0].is_valid]
    first = next(i for i, c in enumerate(cols) if c[1]); last = len(cols) - 1 - next(i for i, c in enumerate(reversed(cols)) if c[1])
    lip = [cols[first - 1][2][0]] + lip + [cols[last + 1][2][0]] if first > 0 and last + 1 < len(cols) else lip
    lip = [v for v in lip if v.is_valid]
    # wells: lip extruded straight inward (boxed edge) to x_well
    inner = []
    for v in lip:
        w = bm.verts.new((S.x_well, v.co.y, v.co.z)); w[tag] = 2
        inner.append(w)
    for a, b, c, d in zip(lip[:-1], lip[1:], inner[1:], inner[:-1]):
        if len({a, b, c, d}) == 4:
            try:
                bm.faces.new((a, b, c, d))
            except ValueError:
                pass
    # crease rows sharp
    for e in bm.edges:
        if all(v[tag] == 3 for v in e.verts):
            e.smooth = False
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for e in me.edges:
        pass
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    ob.location = (0, 0, 0)
    p4.clean_mesh(ob)
    me.update()
    # outward: panel faces point +x (away from the centre line); well walls point into the wheel opening
    s = sum(p.normal.x * p.area for p in me.polygons if abs(p.normal.x) > 0.5)
    if s < 0:
        me.flip_normals()
    m = ob.modifiers.new("Mirror_X", "MIRROR")
    m.use_axis = (True, False, False); m.use_clip = True; m.use_mirror_merge = True; m.merge_threshold = 0.0001
    return ob


def audit(D, sides, objs):
    rows, bad = [], []

    def check(label, meas, spec, tol=TOL, cmp="eq"):
        ok = abs(meas - spec) < tol if cmp == "eq" else (meas >= spec if cmp == "ge" else meas <= spec)
        rows.append("%-62s %9.4f %9.4f %s" % (label, meas, spec, "" if ok else " <-- FAIL"))
        if not ok:
            bad.append(label)

    dg = bpy.context.evaluated_depsgraph_get()
    for key, ob in objs.items():
        S = sides[key]
        me = ob.data
        kind = me.attributes["kind"].data
        V = np.array([tuple(v.co) for v in me.vertices]); K = np.array([d.value for d in kind])
        name = ob.name
        check("%s: origin at world centre" % name, float(ob.location.length), 0.0, tol=1e-9)
        check("%s: axle locator y (read from %s)" % (name, "Axle_" + key.title()), float(S.ax.y),
              -D["length"] / 2 + D["overhang_front"] + (D["wheelbase"] if key == "rear" else 0.0))
        lip = V[K == 1]
        check("%s: arch lip vertices" % name, float(len(lip)), 20.0, cmp="ge")
        dz = np.hypot(lip[:, 1] - S.ax.y, lip[:, 2] - S.ax.z)
        check("%s: arch lip radial clearance to the tyre (min, m)" % name, float(dz.min() - S.r), ARCH_CLEAR, cmp="ge")
        cen = []
        for zz in np.linspace(S.ax.z + 0.04, S.ax.z + 0.15, 12):
            band = lip[np.abs(lip[:, 2] - zz) < 0.012]
            if len(band) >= 2 and band[:, 1].min() < S.ax.y < band[:, 1].max():
                cen.append((band[:, 1].min() + band[:, 1].max()) / 2)
        check("%s: arch opening centred on the axle (y)" % name, float(np.mean(cen)), float(S.ax.y), tol=0.006)
        check("%s: arch top above the axle (z)" % name, float(lip[:, 2].max()), float(S.ax.z + S.r + ARCH_CLEAR), cmp="ge")
        pan = V[K != 2]
        inside = np.hypot(pan[:, 1] - S.ax.y, pan[:, 2] - S.ax.z) < S.r + ARCH_CLEAR
        check("%s: panel vertices inside the tyre envelope" % name, float(inside.sum()), 0.0)
        at_axle = V[(np.abs(V[:, 1] - S.ax.y) < DY) & (K == 0)]
        lower = at_axle[at_axle[:, 2] < S.ledge(S.ax.y)[0] - 1e-4]
        check("%s: lower-body flare at the axle = FIA width / 2" % name, float(lower[:, 0].max()), S.x_flare - S.taper(S.ax.y))
        check("%s: nothing beyond the factory width / 2 (max x)" % name, float(V[:, 0].max()), D["width"] / 2 + 1e-6, cmp="le")
        well = V[K == 2]
        check("%s: well wall x (inner face of tyre - clearance)" % name, float(well[:, 0].mean()), S.x_well)
        check("%s: well wall inside the tyre's inner face" % name, float(well[:, 0].max()),
              S.track / 2 - TYRE_HALF_W - 0.02, cmp="le")
        yl, hl = None, -1
        for y in np.linspace(*S.lens_y, 40):
            if S.ledge(y)[1] > hl:
                yl, hl = y, S.ledge(y)[1]
        zl, h = S.ledge(yl)
        col = V[(np.abs(V[:, 1] - yl) < DY / 2) & (K != 2)]
        top_row = col[np.argmin(np.abs(col[:, 2] - (zl + h)))]               # first row at the top of the ledge
        step = float(col[col[:, 2] <= zl + 1e-4][:, 0].max() - top_row[0]) if len(col) else 0.0
        check("%s: flare step at the lens peak (m)" % name, step, STEP * min(1.0, h / 0.03), tol=0.004)
        nd = sum(1 for p in me.polygons if p.area < 1e-9)
        check("%s: degenerate faces" % name, float(nd), 0.0)
        m = ob.modifiers.get("Mirror_X")
        check("%s: mirror X + clipping + merge" % name, float(bool(m) and m.use_axis[0] and m.use_clip and m.use_mirror_merge), 1.0)
        ev = ob.evaluated_get(dg).to_mesh()
        EX = np.array([v.co.x for v in ev.vertices])
        check("%s: mirrored symmetric (max x + min x)" % name, float(EX.max() + EX.min()), 0.0, tol=1e-6)
        check("%s: mirrored = 2 x half (no seam)" % name, float(len(ev.vertices)), float(2 * len(me.vertices)))
        ob.evaluated_get(dg).to_mesh_clear()
        rows.append("    %s: %d verts, %d faces; arch lip %d verts, top z %.4f; crease at the lens peak y %.3f z %.3f, "
                    "ledge %.1f mm" % (name, len(me.vertices), len(me.polygons), len(lip), lip[:, 2].max(), yl, zl, h * 1000))
    print("NOVA GTE PHASE 6 - BOXED ARCHES VERIFICATION")
    print("%-62s %9s %9s" % ("check", "measured", "spec/limit"))
    print("\n".join(rows))
    if bad:
        raise NovaSpecError("failed: " + "; ".join(bad))
    print("RESULT: PASS")


def main():
    D = dims_ext()
    feats = json.load(open(FEAT))
    coll = bpy.data.collections["NOVA_PROC"]
    sides = {"front": Side(D, "front", feats, bpy.data.objects["Axle_Front"]),
             "rear": Side(D, "rear", feats, bpy.data.objects["Axle_Rear"])}
    objs = {"front": build_panel("Fender_Front_Left", sides["front"], coll),
            "rear": build_panel("Quarter_Rear_Left", sides["rear"], coll)}
    audit(D, sides, objs)
    bpy.ops.wm.save_mainfile()
    print("saved", bpy.data.filepath)


if __name__ == "__main__":
    main()

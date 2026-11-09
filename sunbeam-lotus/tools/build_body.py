"""Build the Sunbeam bodyshell (left half + Mirror) from measured profiles. Runs in Blender.

Loft of cross-sections along Y (car faces -Y, Z up, +X = car's left, origin at ground
midway between the axles). Every station uses the same point count so the rings
bridge into clean quads:

  * lower body: floor -> tucked sill -> flat side -> shoulder -> belt crease
  * greenhouse: glass base on the belt, tumblehome from the blueprint front view,
    crowned roof
  * everything above the side-view top line at a station is clamped onto it with a
    gentle crown (bonnet, windscreen, hatch), which keeps rings continuous

Inputs: tools/features_side.json (lines read off the blueprint) + the traced plan
width. Output: BODY_shell (smooth shaded, sharp edges above SHARP_DEG) with the
wheel-arch Boolean from CUT_wheel_arches.
"""
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(r"D:\Claude\talbot_sunbeam_lotus\tools")
F = json.loads((HERE / "features_side.json").read_text())

W_BODY = 0.8015                       # stock body half-width (1603 mm), door area
BELT = F["belt_z"]
SHARP_DEG = 38.0


def interp(pts, y):
    if y <= pts[0][0]:
        return pts[0][1]
    for (y0, v0), (y1, v1) in zip(pts, pts[1:]):
        if y0 <= y <= y1:
            return v0 + (v1 - v0) * (y - y0) / (y1 - y0) if y1 > y0 else v1
    return pts[-1][1]


# side-view top line: bonnet, windscreen (A-pillar), roof, hatch, rear corner
fr, ws, hs = F["front"], F["windscreen"], F["hatch_silhouette"]
TOP = ([(-1.915, 0.735)] + fr["bonnet_line"][1:-1] + [tuple(ws["base"]), tuple(ws["top"])]
       + [tuple(p) for p in F["roof"]] + [tuple(hs[0]), (1.30, 1.23), (1.45, 1.12), (1.60, 1.00), (1.72, 0.90),
                                           tuple(hs[1]), (1.88, 0.845), (1.935, 0.84)])
# underside: sill between the arches, valances at the ends (front/rear views: ~0.29 / ~0.34)
FLOOR = [(-1.915, 0.29), (-1.84, 0.25), (-1.62, 0.20), (-1.45, 0.18), (1.55, 0.18), (1.74, 0.25), (1.935, 0.34)]
# plan half-width of the shell (flares are separate); nose/tail nearly square in plan - the front
# panel spans +-0.72 and the tail lights reach +-0.77 in the blueprint front/rear views
HALFW = [(-1.915, 0.705), (-1.909, 0.735), (-1.896, 0.752), (-1.87, 0.760), (-1.75, 0.766), (-1.50, 0.776),
         (-1.00, 0.795), (-0.75, W_BODY), (0.75, W_BODY), (1.50, 0.797), (1.80, 0.790), (1.90, 0.784),
         (1.924, 0.772), (1.931, 0.755), (1.935, 0.73)]

LOWER = [(0.00, "f"), (0.36, "f"), (0.72, "f"), (0.955, "f+0.004"), (0.99, "f+0.03"), (1.0, "f+0.085"),
         (1.0, 0.40), (1.0, 0.62), (0.993, 0.78), (0.978, 0.855), (0.962, BELT)]
# greenhouse x at the stock body width, from the blueprint front view (half-width vs height)
GREEN = [(0.738, BELT + 0.006), (0.724, 0.95), (0.708, 1.00), (0.690, 1.05), (0.671, 1.10), (0.650, 1.15),
         (0.625, 1.20), (0.598, 1.25), (0.575, 1.295), (0.550, 1.325), (0.500, 1.345), (0.400, 1.357),
         (0.260, 1.362), (0.120, 1.365), (0.0, 1.366)]
ROOF_T = GREEN[-1][1]
CANT = 8                                   # GREEN index of the cant rail (window top / roof edge)
N_GH, N_TOP = CANT + 1, 10                 # greenhouse points up to the cant; top-surface points after the corner
PILE = 0.12                                # curve-index spacing of points stacked under a low corner


def poly_point(poly, t):
    """Point at fractional index t along a polyline."""
    i = min(int(t), len(poly) - 2)
    f = t - i
    (x0, z0), (x1, z1) = poly[i], poly[i + 1]
    return (x0 + (x1 - x0) * f, z0 + (z1 - z0) * f)


def crossing(poly, z):
    """Fractional index where a polyline rising in z first reaches height z."""
    for i in range(len(poly) - 1):
        z0, z1 = poly[i][1], poly[i + 1][1]
        if z0 <= z <= z1 and z1 > z0:
            return i + (z - z0) / (z1 - z0)
    return float(len(poly) - 1) if z > poly[-1][1] else 0.0


# roof cross-camber: 0 at the cant rail, 1 on the centreline, as a function of x / x_corner
_R = [(x / GREEN[CANT][0], (z - GREEN[CANT][1]) / (ROOF_T - GREEN[CANT][1])) for x, z in GREEN[CANT:]]
def camber(u):
    pts = sorted(_R)
    return interp(pts, u)


def crown(y, zt):
    """Height drop from the centreline to the edge of the top surface at this station."""
    ws0, ws1 = F["windscreen"]["base"][0], F["windscreen"]["top"][0]
    h0, h1 = F["hatch_silhouette"][0][0], F["hatch_silhouette"][1][0]
    roof = (zt - BELT) * (ROOF_T - GREEN[CANT][1]) / (ROOF_T - BELT)
    if ws0 <= y <= ws1:
        return 0.035 + (roof - 0.035) * (y - ws0) / (ws1 - ws0)
    if h0 <= y <= h1:
        return roof + (0.035 - roof) * (y - h0) / (h1 - h0)
    return roof if ws1 < y < h0 else 0.018


def section(y):
    """Half cross-section, bottom centre -> top centre; always len(LOWER) + N_GH + N_TOP points."""
    w, zt, zf = interp(HALFW, y), interp(TOP, y), interp(FLOOR, y)
    k = w / W_BODY
    low = []
    for fx, z in LOWER:
        if isinstance(z, str):
            z = zf + (float(z[2:]) if len(z) > 1 else 0.0)
        low.append((fx * w, z))
    green = [(gx * k, gz) for gx, gz in GREEN]
    c = crown(y, zt)
    z_edge = zt - c
    # stretch the greenhouse to this station's roof height - blended in over the top of the
    # windscreen / tailgate so there's no step where the screen meets the roof
    blend = min(1.0, max(0.0, (zt - 1.18) / (1.30 - 1.18)))
    s = 1.0 + ((zt - BELT) / (ROOF_T - BELT) - 1.0) * blend
    green = [(x, BELT + (z - BELT) * s) for x, z in green]
    # one side curve, floor -> corner, always sampled at the same fractions: on a roof station the
    # corner is the cant rail and the samples land exactly on LOWER + GREEN; elsewhere they compress
    # smoothly, so neighbouring rings never jump
    curve = low + green
    n_side = len(LOWER) + N_GH
    t_c = crossing(curve, z_edge)
    # keep every curve vertex that fits under the corner exactly where it is (so creases like the
    # window sill never slide), and stack the ones that don't just below the corner - continuous in t_c
    last = n_side - 1
    pts = [poly_point(curve, max(0.0, min(i, t_c - (last - i) * PILE))) for i in range(n_side)]
    x_c = pts[-1][0]
    for j in range(1, N_TOP + 1):
        u = 1.0 - j / N_TOP
        pts.append((x_c * u, z_edge + c * camber(u)))
    return [list(p) for p in pts]


def stations():
    ys = {round(-1.915 + 0.035 * i, 4) for i in range(0, 111)}
    feats = [-1.915, -1.909, -1.896, -1.87, -1.85, -0.74, -0.73, -0.60, -0.23, -0.20, 0.40, 0.41, 0.46,
             0.52, 0.97, 1.15, 1.20, 1.80, 1.88, 1.90, 1.924, 1.931, 1.935]
    ys |= set(feats)
    return sorted(y for y in ys if -1.915 <= y <= 1.935)


L = len(LOWER)
N_SIDE = L + N_GH
TOP_COLS = range(N_SIDE, N_SIDE + N_TOP - 1)    # top surface, leaving a frame row at the corner
GLASS_INSET = 0.012
SILL, FRAME = 0.018, 0.035                      # side-glass margins above the belt / below the corner
WINDOW_TOP = 1.245                              # side-glass top edge (roof corner is ~1.28-1.29)


def material(name, rgb, shader=None, preset=None):
    """Blender material + its AC export settings (ac_shader / ac_preset, see ac_kn5_export.PRESETS)."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    m.diffuse_color = (*rgb, 1.0)
    if preset and not shader:
        shader = "ksPerPixelMultiMap"
    if shader:
        m["ac_shader"] = shader
    if preset:
        m["ac_preset"] = preset
    return m


def a_pillar_z(y):
    """Straight A-pillar frame line - the SAME line the bisect cuts, so face classification
    and the cut edges agree (classifying against the curved corner line made a sawtooth)."""
    ws = F["windscreen"]
    ya, yb = ws["base"][0], ws["top"][0]
    zc = lambda yy: interp(TOP, yy) - crown(yy, interp(TOP, yy)) - FRAME
    za, zb = zc(ya), zc(yb)
    return za + (zb - za) * (y - ya) / (yb - ya)


def black_frame(f):
    """Window surrounds the real car has in black: belt strip, frame, B-pillar, strip behind the quarter light."""
    # every boundary here is an exactly-cut line (belt+sill, window top, A-pillar frame line,
    # quarter-light rear edge) or a loft ring (the roof corner), so the black edge stays clean
    c, n = f.calc_center_median(), f.normal
    if n.x < 0.1 or not (BELT - 0.004 < c.z < WINDOW_TOP + FRAME + 0.006):
        return False
    ws = F["windscreen"]
    if c.y < ws["top"][0] and c.z > a_pillar_z(c.y):
        return False                                            # A-pillar stays body colour
    (y0, z0), (y1, z1) = F["quarter_window"]["rear_edge"]
    y_edge = y0 + (c.z - z0) * (y1 - y0) / (z1 - z0)
    return ws["glass_inset_base"][0] - 0.02 <= c.y <= y_edge


def window_of(y, z, col, normal):
    """Which window a face belongs to (None = bodywork): top glass by loft column, side glass by
    position between the belt and the roof corner, on faces that look sideways."""
    ws, qw = F["windscreen"], F["quarter_window"]
    if col in TOP_COLS:
        if ws["base"][0] + 0.04 <= y <= ws["top"][0] - 0.04:
            return "windscreen"
        if F["hatch_silhouette"][0][0] + 0.04 <= y <= F["hatch_silhouette"][1][0] - 0.05:
            return "hatch"
        return None
    # the z limits are all exactly-cut lines; the normal test only has to keep out faces that
    # face forwards/backwards (a stricter test chops through the twisted faces by the A-pillar)
    z_top = min(a_pillar_z(y), WINDOW_TOP) if y < ws["top"][0] else WINDOW_TOP
    if normal.x < 0.1 or not (BELT + SILL <= z <= z_top):
        return None
    if ws["glass_inset_base"][0] <= y <= F["front_side_window"]["rear_edge_y"]:
        return "door_window"
    (y0, z0), (y1, z1) = qw["rear_edge"]
    y_edge = y0 + (z - z0) * (y1 - y0) / (z1 - z0)
    if qw["front_y"] + 0.01 <= y <= y_edge:
        return "quarter_window"
    return None


D = F["door"]
BONNET_X, BONNET_REAR_Y, GATE_X, GATE_TOP_Y = 0.70, -0.80, 0.62, 1.15
# panel shut lines: (plane point, plane normal, face filter, edge-midpoint filter)
GROOVES = [
    ("door front", (0, D["front_y"], 0), (0, 1, 0), lambda f: f.normal.x > 0.35,
     lambda m: D["bottom_z"] - 0.005 <= m.z <= BELT - 0.004),
    ("door rear", (0, D["rear_y"], 0), (0, 1, 0), lambda f: f.normal.x > 0.35,
     lambda m: D["bottom_z"] - 0.005 <= m.z <= BELT - 0.004),
    ("door bottom", (0, 0, D["bottom_z"]), (0, 0, 1), lambda f: f.normal.x > 0.35,
     lambda m: D["front_y"] <= m.y <= D["rear_y"]),
    ("bonnet side", (BONNET_X, 0, 0), (1, 0, 0), lambda f: f.normal.z > 0.45,
     lambda m: -1.905 <= m.y <= BONNET_REAR_Y),
    ("bonnet rear", (0, BONNET_REAR_Y, 0), (0, 1, 0), lambda f: f.normal.z > 0.45,
     lambda m: m.x <= BONNET_X),
    ("tailgate side", (GATE_X, 0, 0), (1, 0, 0), lambda f: f.normal.z > 0.2 or f.normal.y > 0.5,
     lambda m: GATE_TOP_Y <= m.y <= 1.93),
    ("tailgate top", (0, GATE_TOP_Y, 0), (0, 1, 0), lambda f: f.normal.z > 0.45,
     lambda m: m.x <= GATE_X),
]
GROOVE_W, GROOVE_D = 0.0022, 0.004


def cut_grooves(bm):
    """Cut each shut line into the surface, then bevel it and push the middle down into a V."""
    for name, co, no, face_ok, mid_ok in GROOVES:
        faces = [f for f in bm.faces if face_ok(f)]
        geom = list({v for f in faces for v in f.verts}) + list({e for f in faces for e in f.edges}) + faces
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, dist=0.0003)
        plane_co, plane_no = Vector(co), Vector(no)
        edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)
                 and all(abs((v.co - plane_co).dot(plane_no)) < 0.0005 for v in e.verts)
                 and mid_ok((e.verts[0].co + e.verts[1].co) / 2)
                 and all(face_ok(f) for f in e.link_faces) and len(e.link_faces) == 2]
        if not edges:
            continue
        bm.normal_update()
        normals = {v: v.normal.copy() for e in edges for v in e.verts}
        out = bmesh.ops.bevel(bm, geom=edges, offset=GROOVE_W, offset_type="OFFSET", segments=2,
                              profile=0.5, affect="EDGES", clamp_overlap=True)
        for v in out.get("verts", []):
            if abs((v.co - plane_co).dot(plane_no)) < 0.0006:
                n = normals.get(v) or v.normal
                v.co -= n * GROOVE_D


def build():
    col = bpy.data.collections["BODY"]
    old = bpy.data.objects.get("BODY_shell")
    if old:
        me_old = old.data
        bpy.data.objects.remove(old)
        if me_old.users == 0:
            bpy.data.meshes.remove(me_old)
    me = bpy.data.meshes.new("BODY_shell")
    bm = bmesh.new()
    cell = bm.faces.layers.int.new("cell")        # column index of each loft quad, survives the bisect
    rings = [[bm.verts.new((x, y, z)) for x, z in section(y)] for y in stations()]
    n = len(rings[0])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n - 1):
            f = bm.faces.new((r0[i], r0[i + 1], r1[i + 1], r1[i]))
            f[cell] = i
    for cap in (bm.faces.new(list(reversed(rings[0]))), bm.faces.new(rings[-1])):
        cap[cell] = -1

    # cut every side-glass edge in exactly: planes through lines in the side view, extruded in X,
    # applied only to the greenhouse side faces
    def side_region():
        out = []
        for f in bm.faces:
            c = f.calc_center_median()
            if 0 <= f[cell] < N_SIDE and c.z > BELT - 0.01 and -0.80 <= c.y <= 1.30:
                out.append(f)
        return out

    def cut(p0, p1):
        (ya, za), (yb, zb) = p0, p1
        region = side_region()
        geom = list({v for f in region for v in f.verts}) + list({e for f in region for e in f.edges}) + region
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0.0, ya, za), plane_no=(0.0, za - zb, yb - ya))

    ws = F["windscreen"]
    ya, yb = ws["base"][0], ws["top"][0]
    cut((-1.0, BELT + SILL), (1.3, BELT + SILL))                            # window bottom
    cut((-1.0, WINDOW_TOP), (1.3, WINDOW_TOP))                              # window top
    cut((ya, a_pillar_z(ya)), (yb, a_pillar_z(yb)))                         # front edge along the A-pillar
    cut((-1.0, BELT - 0.004), (1.3, BELT - 0.004))                          # bottom of the black belt strip
    for z in (0.43, 0.445):                                                 # valance tops, hidden by the bumpers
        ends = [f for f in bm.faces if abs(f.normal.y) > 0.55]
        g = list({v for f in ends for v in f.verts}) + list({e for f in ends for e in f.edges}) + ends
        bmesh.ops.bisect_plane(bm, geom=g, plane_co=(0.0, 0.0, z), plane_no=(0.0, 0.0, 1.0))
    cut(*[tuple(p) for p in F["quarter_window"]["rear_edge"]])              # quarter window rear edge

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0004)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=0.0004)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cut_grooves(bm)

    # windows: inset each glass area 12 mm; the new walls become the rubber seal
    groups = {}
    for f in bm.faces:
        c = f.calc_center_median()
        win = window_of(c.y, c.z, f[cell], f.normal) if f[cell] >= 0 else None
        if win:
            groups.setdefault(win, []).append(f)
    glass_faces, seal_faces = set(), set()
    for win, faces in groups.items():
        before = set(bm.faces)
        bmesh.ops.inset_region(bm, faces=faces, thickness=0.0, depth=-GLASS_INSET,
                               use_even_offset=True, use_boundary=False)
        seal_faces |= set(bm.faces) - before
        glass_faces |= set(faces)

    for f in bm.faces:
        f.smooth = True
        c = f.calc_center_median()
        valance = abs(f.normal.y) > 0.55 and c.z < (0.43 if c.y < 0 else 0.445)   # black lower valances
        f.material_index = (1 if f in glass_faces else 2 if f in seal_faces
                            else 3 if (black_frame(f) or valance) else 0)
    sharp = math.radians(SHARP_DEG)
    for e in bm.edges:
        if len(e.link_faces) == 2 and (e.calc_face_angle(0.0) > sharp
                                       or len({f.material_index for f in e.link_faces}) > 1):
            e.smooth = False
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("BODY_shell", me)
    col.objects.link(ob)
    m = ob.modifiers.new("Mirror", "MIRROR")
    m.use_axis = (True, False, False); m.use_clip = True; m.use_mirror_merge = True; m.merge_threshold = 0.0005
    cut = bpy.data.objects.get("CUT_wheel_arches")
    if cut:
        b = ob.modifiers.new("WheelArches", "BOOLEAN")
        b.operation = "DIFFERENCE"; b.object = cut; b.solver = "EXACT"
    for mat in (material("EXT_body_white", (0.85, 0.85, 0.83), preset="paint"),
                material("EXT_glass", (0.035, 0.05, 0.065), preset="glass"),
                material("EXT_rubber", (0.02, 0.02, 0.02), preset="trim"),
                material("EXT_black_trim", (0.03, 0.03, 0.03), preset="trim")):
        me.materials.append(mat)
    return ob, {k: len(v) for k, v in groups.items()}


if __name__ == "__main__":
    build()

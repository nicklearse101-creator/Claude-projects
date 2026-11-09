"""Engine swap for the rally Sunbeam's bay (runs in Blender on sunbeam_rally_on_stock_model.blend; called at the end
of build_rally_parts.build()). Plan: docs/plans/2026-10-06-belts-splitters-engine.md.

Nik 2026-10-06: "Will the old Escort 4 cylinder engine you just replaced fit in the engine bay? Plan and build" and
"replace the Ford badge stamped on the top with a Lotus badge".

ENGINE = "escort4": the Escort Mk2 tuned mod's twin-cam four (101Creative / graveltrap - personal use only),
exported from the Escort blend with the bay parts bolted to it into refs/donor_escort4/escort4_engine.kn5
(gitignored), imported as collection DONOR_ESC4 (prefix ESC4_). The two cars' bays line up within millimetres
(front axles y -1.218 / -1.212, radiators -1.66 / -1.69), so the engine goes in at the Escort's own position:
  * the Sunbeam's stock engine (engine_a_*) and its hoses/leads that touched it are taken out of the export via
    mod_ copies (restore_modified() at the start of every build brings them back - ENGINE = "stock" keeps them)
  * donor islands are left out when they are wholly under the Sunbeam's false bay floor (z ~0.30 - its modder only
    built the top of the engine), mostly inside Sunbeam parts, or behind the firewall
  * the raised FORD letters on the cam cover go; a Lotus roundel badge (generated texture) sits in their place
Not in the distance LODs (closed bonnet; names don't start RALLY_).
"""
import importlib.util
import json
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

TOOLS = r"D:\Claude\talbot_sunbeam_lotus\tools"
REFS = r"D:\Claude\talbot_sunbeam_lotus\refs"
ENGINE = "escort4"                               # "stock" = the stock mod's engine (nothing swapped)
DONOR_KN5 = os.path.join(REFS, "donor_escort4", "escort4_engine.kn5")
DONOR_TEX = os.path.join(REFS, "donor_escort4_textures")
DONOR = "DONOR_ESC4"
PREFIX = "esc4_"
BAY_FLOOR_Z = 0.318        # the stock bay's false floor (z 0.301-0.316 under the engine)
UNDERTRAY_Z = 0.12         # engine geometry below this is cut off (hidden between false floor and undertray)
FIREWALL_Y = -0.875        # anything visible behind this would be in the cabin
INSIDE_MAX = 0.15          # an island more than this share inside Sunbeam parts is left out
TOUCH = 0.006              # stock bay islands this close to the stock engine belonged to it
FORD_LETTERS = ((0.058, -1.268, 0.512), (0.099, -1.152, 0.524))
# on the 40 mm raised pad the FORD letters stood on (pad top z 0.521); 36 mm over the bezel, clear of the cover bolts
LOTUS = dict(centre=(0.0775, -1.212, 0.5212), r=0.016, t=0.0014, bezel=0.002, tex="RALLY_lotus_badge.png")
SHELL_MATS = ("carPaint", "carPaint_2", "backfacinggeo", "blackHole", "zeroBlack", "engine_low")


def load(name):
    spec = importlib.util.spec_from_file_location(name, rf"{TOOLS}\{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def _world(o):
    n = len(o.data.vertices)
    c = np.empty(n * 3); o.data.vertices.foreach_get("co", c)
    m = np.array(o.matrix_world)
    return c.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]


def _islands(me):
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    seen, out = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        st, comp = [v], []
        seen.add(v.index)
        while st:
            u = st.pop(); comp.append(u.index)
            for e in u.link_edges:
                w = e.other_vert(u)
                if w.index not in seen:
                    seen.add(w.index); st.append(w)
        out.append(comp)
    bm.free()
    return out


def _keep_only(me, keep):
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context="VERTS")
    bm.to_mesh(me); bm.free(); me.update()


def _mat_name(o):
    return o.data.materials[0].name if o.type == "MESH" and o.data.materials and o.data.materials[0] else ""


def stock_objects():
    return [o for o in bpy.data.collections["STOCK_MODEL"].all_objects if o.type == "MESH" and len(o.data.vertices)]


def import_donor():
    if DONOR not in bpy.data.collections:
        load("kn5_import").import_kn5(DONOR_KN5, DONOR_TEX, collection_name=DONOR, prefix="ESC4_", primary=False)
    lc = bpy.context.view_layer.layer_collection.children.get(DONOR)
    if lc:
        lc.exclude = True
    return [o for o in bpy.data.collections[DONOR].all_objects if o.type == "MESH"]


def bvh(objs):
    bm = bmesh.new()
    for o in objs:
        t = o.data.copy(); t.transform(o.matrix_world); bm.from_mesh(t); bpy.data.meshes.remove(t)
    tree = BVHTree.FromBMesh(bm); bm.free()
    return tree


def stow_stock_engine():
    """Stock engine meshes + bay islands touching them -> out of the export (mod_ copies, undone next build)."""
    ex = load("build_extras")
    live = [o for o in stock_objects() if not o.get("no_export")]
    eng = [o for o in live if str(o.get("kn5_name") or "").startswith("engine_a")]
    tree = bvh(eng)
    rep = {"engine meshes": 0, "bay islands": {}}
    for o in eng:
        cp = o if o.get("mod_of") else ex.modified_copy(o)
        cp["no_export"] = True
        cp.hide_set(True)
        rep["engine meshes"] += 1
    for o in live:
        nm = str(o.get("kn5_name") or o.name)
        if not nm.startswith("enginebay") or _mat_name(o) in SHELL_MATS or o in eng:
            continue
        W = _world(o)
        take = set()
        for comp in _islands(o.data):
            P = W[comp]
            if np.ptp(P, axis=0).max() > 0.5:                 # bay-sized pieces are structure, not engine parts
                continue
            step = max(1, len(comp) // 60)
            if any(tree.find_nearest(Vector(p), TOUCH)[0] is not None for p in P[::step]):
                take.update(comp)
        if take:
            cp = o if o.get("mod_of") else ex.modified_copy(o)
            keep = set(range(len(cp.data.vertices))) - take
            _keep_only(cp.data, keep)
            rep["bay islands"][nm] = len(take)
    return rep


def place_donor(donor):
    """Copies of the donor engine in the Sunbeam, island by island filtered (see the module docstring)."""
    ex = load("build_extras")
    for o in [o for o in bpy.data.objects if o.get("rally_engine")]:
        ex.remove(o)
    # the Sunbeam as solid parts: its black "backfacing" box round the old engine and the hole fillers are not
    # parts anything could clash with
    live = [o for o in stock_objects() if not o.get("no_export") and not o.get("rally_engine")
            and not o.name.startswith(("RALLY_", "harness_"))
            and _mat_name(o) not in ("backfacinggeo", "blackHole", "zeroBlack", "engine_low")]
    sun = bvh(live)
    univers = next(o for o in bpy.data.collections["STOCK_MODEL"].all_objects if o.get("kn5_name") == "UNIVERS")
    lo, hi = (np.array(b) for b in FORD_LETTERS)
    rep = {"kept": {}, "dropped": {"under floor": 0, "inside Sunbeam parts": 0, "behind firewall": 0, "FORD": 0}}
    for i, src in enumerate(sorted(donor, key=lambda o: o.name)):
        kn = str(src.get("kn5_name") or src.name)
        ob = ex.graft(src, f"{PREFIX}{kn}", Matrix.Identity(4), univers, rally_engine=True, no_lod=True,
                      kn5_order=3 * 10 ** 6 + 200 + i)
        W = _world(ob)
        keep = set()
        for comp in _islands(ob.data):
            P = W[comp]
            if P[:, 2].max() < BAY_FLOOR_Z:
                rep["dropped"]["under floor"] += len(comp); continue
            if ((P >= lo) & (P <= hi)).all():
                rep["dropped"]["FORD"] += len(comp); continue
            vis = P[P[:, 2] > BAY_FLOOR_Z]
            if (vis[:, 1] > FIREWALL_Y).mean() > 0.2:
                rep["dropped"]["behind firewall"] += len(comp); continue
            step = max(1, len(vis) // 80)
            samp = vis[vis[:, 2] > BAY_FLOOR_Z + 0.01][::step]      # under the false floor counts as hidden, not inside
            if not len(samp):
                keep.update(comp); continue
            inside = 0
            for p in samp:
                loc, nrm, idx, d = sun.find_nearest(Vector(p), 0.03)
                if loc is not None and nrm.dot(Vector(p) - loc) < 0:
                    inside += 1
            if inside / len(samp) > INSIDE_MAX:
                rep["dropped"]["inside Sunbeam parts"] += len(comp); continue
            keep.update(comp)
        if not keep:
            ex.remove(ob); continue
        _keep_only(ob.data, keep)
        # nothing below the undertray (z 0.03-0.12): a sump/manifold corner showed under the car
        bm = bmesh.new(); bm.from_mesh(ob.data)
        inv = ob.matrix_world.inverted()
        cut_co = inv @ Vector((0, 0, UNDERTRAY_Z)); cut_no = (inv.to_3x3() @ Vector((0, 0, 1))).normalized()
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=cut_co, plane_no=cut_no,
                               clear_inner=True)
        bm.to_mesh(ob.data); bm.free()
        if not len(ob.data.vertices):
            ex.remove(ob); continue
        rep["kept"][ob.name] = len(ob.data.vertices)
    return rep


# ---- Lotus badge ---------------------------------------------------------------------------------------------------
def badge_texture(path, size=512):
    """Lotus roundel: yellow disc, dark-green rounded triangle (apex up), ACBC monogram near the apex and LOTUS across
    the base cut out in yellow. Drawn with Blender's own pixels (no PIL inside Blender)."""
    n = size
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    u, v = (xx + 0.5) / n * 2 - 1, 1 - (yy + 0.5) / n * 2        # -1..1, v up
    yellow, green, rim = np.array([1.0, 0.80, 0.0]), np.array([0.0, 0.26, 0.15]), np.array([0.0, 0.18, 0.10])
    img = np.zeros((n, n, 3))
    r = np.hypot(u, v)
    img[:] = rim
    img[r < 0.97] = yellow
    # rounded triangle, apex up: exact distance to a (shrunk) triangle, minus the corner radius
    R, rr = 0.86, 0.17
    verts = [((R - 2 * rr) * math.cos(a), (R - 2 * rr) * math.sin(a) - 0.04)
             for a in (math.pi / 2, math.pi / 2 + 2 * math.pi / 3, math.pi / 2 + 4 * math.pi / 3)]
    dist = np.full(u.shape, np.inf)
    inside = np.ones(u.shape, bool)
    for (ax, ay), (bx, by) in zip(verts, verts[1:] + verts[:1]):
        ex, ey = bx - ax, by - ay
        L2 = ex * ex + ey * ey
        t = np.clip(((u - ax) * ex + (v - ay) * ey) / L2, 0, 1)
        dist = np.minimum(dist, np.hypot(u - (ax + t * ex), v - (ay + t * ey)))
        inside &= (ex * (v - ay) - ey * (u - ax)) >= 0             # counter-clockwise: inside is on the left
    sdf = np.where(inside, -dist, dist) - rr
    img[(sdf < 0) & (r < 0.97)] = green
    rgba = np.concatenate([img, np.ones((n, n, 1))], -1)
    im = bpy.data.images.new("RALLY_lotus_badge_tmp", n, n, alpha=True)
    im.pixels.foreach_set(rgba[::-1].astype(np.float32).ravel())
    return im, n


def badge_text_overlay(im, n):
    """LOTUS and the monogram in yellow over the green, using Blender's text -> mesh -> rasterised mask."""
    def mask_for(text, cx, cy, height, size_px=n):
        cu = bpy.data.curves.new("TMP_badge_text", "FONT")
        cu.body = text
        cu.size = 1.0
        cu.align_x = "CENTER"; cu.align_y = "CENTER"
        try:
            cu.font = bpy.data.fonts.load(r"C:\Windows\Fonts\arialbd.ttf", check_existing=True)
        except Exception:
            pass
        ob = bpy.data.objects.new("TMP_badge_text", cu)
        bpy.context.scene.collection.objects.link(ob)
        dg = bpy.context.evaluated_depsgraph_get()
        me = ob.evaluated_get(dg).to_mesh()
        P = [(v.co.x, v.co.y) for v in me.vertices]
        tris = []
        me.calc_loop_triangles()
        for t in me.loop_triangles:
            tris.append([P[i] for i in t.vertices])
        xs = [p[0] for p in P]; ys = [p[1] for p in P]
        h = max(ys) - min(ys) if P else 1.0
        w = max(xs) - min(xs) if P else 1.0
        ob.evaluated_get(dg).to_mesh_clear()
        bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
        sc = height / h
        cx0, cy0 = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        mask = np.zeros((size_px, size_px), bool)
        yy, xx = np.mgrid[0:size_px, 0:size_px]
        U = (xx + 0.5) / size_px * 2 - 1
        V = 1 - (yy + 0.5) / size_px * 2
        for tri in tris:
            (x1, y1), (x2, y2), (x3, y3) = [((x - cx0) * sc + cx, (y - cy0) * sc + cy) for x, y in tri]
            minx, maxx = min(x1, x2, x3), max(x1, x2, x3); miny, maxy = min(y1, y2, y3), max(y1, y2, y3)
            i0 = max(0, int((minx + 1) / 2 * size_px) - 1); i1 = min(size_px, int((maxx + 1) / 2 * size_px) + 2)
            j0 = max(0, int((1 - maxy) / 2 * size_px) - 1); j1 = min(size_px, int((1 - miny) / 2 * size_px) + 2)
            if i1 <= i0 or j1 <= j0:
                continue
            uu, vv = U[j0:j1, i0:i1], V[j0:j1, i0:i1]
            d1 = (uu - x2) * (y1 - y2) - (x1 - x2) * (vv - y2)
            d2 = (uu - x3) * (y2 - y3) - (x2 - x3) * (vv - y3)
            d3 = (uu - x1) * (y3 - y1) - (x3 - x1) * (vv - y1)
            neg = (d1 < 0) | (d2 < 0) | (d3 < 0); pos = (d1 > 0) | (d2 > 0) | (d3 > 0)
            mask[j0:j1, i0:i1] |= ~(neg & pos)
        return mask, w * sc
    px = np.array(im.pixels[:]).reshape(n, n, 4)[::-1].copy()
    yellow = np.array([1.0, 0.80, 0.0, 1.0])
    m1, w1 = mask_for("LOTUS", 0.0, -0.27, 0.16)
    m2, _ = mask_for("ACBC", 0.0, 0.12, 0.13)
    px[m1] = yellow; px[m2] = yellow
    im.pixels.foreach_set(px[::-1].astype(np.float32).ravel())
    return im


def badge_material(tex_dir):
    os.makedirs(tex_dir, exist_ok=True)
    path = os.path.join(tex_dir, LOTUS["tex"])
    im, n = badge_texture(path)
    badge_text_overlay(im, n)
    im.filepath_raw = path; im.file_format = "PNG"; im.save()
    bpy.data.images.remove(im)
    base = json.loads(bpy.data.materials["chrome"]["kn5_def"])
    props = [[p[0], {"ksAmbient": 0.45, "ksDiffuse": 0.55, "ksSpecular": 0.35, "ksSpecularEXP": 40.0}.get(p[0], p[1])]
             + list(p[2:]) for p in base["props"]]
    d = dict(name="RALLY_lotus_badge", shader="ksPerPixel", blend=0, alphaTested=0, depth=0, props=props,
             samplers=[["txDiffuse", 0, LOTUS["tex"]]], tex_dir=tex_dir)
    m = bpy.data.materials.get("RALLY_lotus_badge") or bpy.data.materials.new("RALLY_lotus_badge")
    m["kn5_def"] = json.dumps(d)
    m.use_fake_user = True
    # the kn5 only needs kn5_def; the image node is so Blender shows the badge too
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tex = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None) or nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path, check_existing=True)
    tex.image.reload()
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Metallic"].default_value, bsdf.inputs["Roughness"].default_value = 0.2, 0.3
    return m


def build_badge(tex_dir):
    """Round badge (textured top, thin edge) + polished bezel ring, on the cam cover where FORD was."""
    m = badge_material(tex_dir)
    chrome = bpy.data.materials["chrome"]
    c = Vector(LOTUS["centre"]); r, t, bz = LOTUS["r"], LOTUS["t"], LOTUS["bezel"]
    bm = bmesh.new(); uv = bm.loops.layers.uv.new("UVMap")
    segs = 48
    top = [bm.verts.new(c + Vector((r * math.cos(2 * math.pi * k / segs), r * math.sin(2 * math.pi * k / segs), t)))
           for k in range(segs)]
    bot = [bm.verts.new(c + Vector((r * math.cos(2 * math.pi * k / segs), r * math.sin(2 * math.pi * k / segs), -0.002)))
           for k in range(segs)]
    f = bm.faces.new(top); f.material_index = 0
    for lp in f.loops:
        p = lp.vert.co - c
        # reads from the front of the car (where you stand with the bonnet up): top of the badge towards the screen
        lp[uv].uv = (0.5 + p.x / (2 * r), 0.5 + p.y / (2 * r))
    for k in range(segs):
        k1 = (k + 1) % segs
        f = bm.faces.new((bot[k], bot[k1], top[k1], top[k])); f.material_index = 1
        for lp in f.loops:
            lp[uv].uv = (0.5, 0.5)
    ring_o = [bm.verts.new(c + Vector(((r + bz) * math.cos(2 * math.pi * k / segs), (r + bz) * math.sin(2 * math.pi * k / segs), t * 0.6)))
              for k in range(segs)]
    ring_b = [bm.verts.new(c + Vector(((r + bz) * math.cos(2 * math.pi * k / segs), (r + bz) * math.sin(2 * math.pi * k / segs), -0.002)))
              for k in range(segs)]
    for k in range(segs):
        k1 = (k + 1) % segs
        for q in ((top[k], top[k1], ring_o[k1], ring_o[k]), (ring_o[k], ring_o[k1], ring_b[k1], ring_b[k])):
            f = bm.faces.new(q); f.material_index = 1
            for lp in f.loops:
                lp[uv].uv = (0.5, 0.5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = f.material_index == 1
    univers = next(o for o in bpy.data.collections["STOCK_MODEL"].all_objects if o.get("kn5_name") == "UNIVERS")
    ob = load("build_cage").make_obj(f"{PREFIX}lotus_badge", bm, [m, chrome], univers)
    ob["kn5_name"] = f"{PREFIX}lotus_badge"
    ob["rally_engine"] = True; ob["no_lod"] = True
    return ob


def build():
    if ENGINE != "escort4":
        for o in [o for o in bpy.data.objects if o.get("rally_engine")]:
            load("build_extras").remove(o)
        return {"engine": ENGINE}
    donor = import_donor()
    stowed = stow_stock_engine()
    placed = place_donor(donor)
    badge = build_badge(os.path.join(REFS, "badge_textures"))
    return {"engine": ENGINE, "stowed": stowed, "placed": placed, "badge": badge.name}

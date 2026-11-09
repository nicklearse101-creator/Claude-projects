"""Distance LODs for the rally Sunbeam (runs in Blender, on sunbeam_rally_on_stock_model.blend, after
build_rally_parts.build()).

Starts from the original mod's own CM-generated LODs (b 39k, c 17k, d 3.7k triangles), imported exactly
(kn5_import) into a scene each, then:
  * leaves out their stock rims, tyres and fog lamps (as LOD0 does)
  * adds decimated copies of our rally parts from the main scene (flares, lips, blades, mud flaps, lamp bar,
    spot lamps, Escort Mk2 wheels) with materials remapped to the LOD's own same-named materials
  * wheels go under the LOD's WHEEL_xx nodes (AC moves those with the physics); LOD d has no wheel nodes, so
    its wheels sit fixed at the physics track width
Exports export/sunbeam_rally_lod_{b,c,d}.kn5 without textures (AC takes them from the main kn5 by name).
"""
import importlib.util
import json
import os

import bpy
from mathutils import Matrix, Vector

TOOLS = r"D:\Claude\talbot_sunbeam_lotus\tools"
STOCK = r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\talbot_sunbeam_lotus_lhd_stock"
OUT = r"D:\Claude\talbot_sunbeam_lotus\export"
TEX = r"D:\Claude\talbot_sunbeam_lotus\refs\stock_kn5_textures\lods"
# level: (stock file, decimate ratio, spot-lamp parts kept, keep lips/blades, wheel materials kept (None = all),
#         minimum faces per decimated part)
LEVELS = {
    "b": ("TSL_LHD_stock_lod_b.kn5", 0.22, ("SUB3", "SUB4", "SUB1", "SUB0"), True, None, 40),
    "c": ("TSL_LHD_stock_lod_c.kn5", 0.08, ("SUB3", "SUB4", "SUB1"), True,
          {"MK2_TREAD_tyres", "MK2_WALL_tyres", "MK2_OUTER_RIM", "MK2_SPOKES"}, 24),
    "d": ("TSL_LHD_stock_lod_d.kn5", 0.03, ("SUB3",), False, {"MK2_TREAD_tyres", "MK2_OUTER_RIM"}, 12),
}
STOCK_WHEEL_MATS = {"rim", "tire", "valve_cap", "valve_stem"}
AC_TYRE_X = {"LF": 0.7125, "RF": -0.7125, "LR": 0.719, "RR": -0.719}
def _belt_reel(c):
    """The stock belts' reel covers high on the B-pillars."""
    return abs(c.x) > 0.55 and 0.44 < c.y < 0.56 and c.z > 0.9


# stripped interior (build_cage) in the LODs. Their meshes are merged by material (the rear bench shares meshes with
# the front seats), so it goes by material + position: faces of these materials whose centre passes the test go ...
REAR_DROP = {"velvet_001": lambda c: True, "leather_smooth_LGL_1D1D1DFF": lambda c: True,  # stock seats + bench
             "plastic_RGH_HGL|seatR_a": lambda c: True,                                     # seat lever
             "paint_010101FF": lambda c: -0.35 < c.y < 0.45 and c.z < 0.66,                 # stock seat frames
             "carpet_006_FFFFFFFF": lambda c: True,                                          # parcel shelf
             "leather_MGL": lambda c: c.y > 1.10,                                           # back of the rear seat
             "plastic_HGL": lambda c: c.y > 1.10 or _belt_reel(c),                          # ... and belt reel trims
             "plastic_LGL": _belt_reel,
             "plastic_brillant": lambda c: 1.40 < c.y < 1.60 and 0.55 < c.z < 0.86 and abs(c.x) < 0.6,  # strings
             "seat_belt_001": lambda c: True, "seatbelt_press": lambda c: True,             # stock 3-point belts
             "fabric_001|visors_a": lambda c: True}                                          # sun visors (cage header)
# ... and the grey rear trims behind the B-pillar are repainted black like LOD a
REAR_REPAINT = {"plastic_textured_001_a", "plastic_textured_001_666666FF", "plastic_textured_003_666666FF",
                "plastic_textured_001"}
REAR_REPAINT_Y = 0.40
CAGE_SEGS = {"b": 8, "c": 6, "d": 0}     # the cage is rebuilt with fewer sides rather than decimated


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(TOOLS, name + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def kdef_name(mat):
    return json.loads(mat["kn5_def"])["name"] if mat is not None and "kn5_def" in mat else None


def tris(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles(); n = len(me.loop_triangles)
    ob.evaluated_get(dg).to_mesh_clear()
    return n


def build_level(tag, main_scene):
    stock_file, ratio, lamp_keep, keep_lips, wheel_keep, min_faces = LEVELS[tag]
    name = f"LOD_{tag.upper()}"
    old = bpy.data.scenes.get(name)
    if old:
        for ob in list(old.objects):
            bpy.data.objects.remove(ob)
        for col in list(old.collection.children_recursive):
            bpy.data.collections.remove(col)
        bpy.data.scenes.remove(old)
    sc = bpy.data.scenes.new(name)
    bpy.context.window.scene = sc
    imp = load("kn5_import")
    os.makedirs(TEX, exist_ok=True)
    stats = imp.import_kn5(os.path.join(STOCK, stock_file), TEX, f"LOD_{tag.upper()}_MODEL", primary=True)
    # the stock LOD files carry a rotated FBX root (their child transforms are Z-up), so world matrices must be
    # evaluated before our parts are parented in by world position
    bpy.context.view_layer.update()
    lod_objs = list(bpy.data.collections[f"LOD_{tag.upper()}_MODEL"].objects)
    by_name = {}
    for o in lod_objs:
        by_name.setdefault(o.get("kn5_name"), []).append(o)
    root = next(o for o in lod_objs if o.get("kn5_root"))
    univers = next((o for o in by_name.get("UNIVERS", []) if o.type == "EMPTY"), root)
    lod_mats = {}
    for o in lod_objs:
        if o.type == "MESH" and o.data.materials:
            lod_mats.setdefault(kdef_name(o.data.materials[0]), o.data.materials[0])

    # stock rims, tyres, fog lamps out
    removed = 0
    for o in lod_objs:
        if o.type != "MESH" or not o.data.materials:
            continue
        mn = kdef_name(o.data.materials[0])
        in_fog = any(p.get("kn5_name", "").startswith("EXT_FOGLIGHT_") for p in _parents(o))
        wheel_detail = mn == "detail" and "wheel" in (o.get("kn5_name") or "")
        if mn in STOCK_WHEEL_MATS or in_fog or wheel_detail:
            o["no_export"] = True; removed += 1
    stripped = strip_rear(lod_objs, lod_mats)
    stripped["plate_faces_moved"] = move_front_plate(lod_objs)
    stripped["exhaust_verts_moved"] = enlarge_exhaust(lod_objs)
    stripped["old_controls_faces"] = drop_old_controls(lod_objs)
    stripped["stripe_verts_lifted"] = lift_stripes(lod_objs, STRIPE_GAP_LOD[tag])

    # copies of our rally parts
    col = bpy.data.collections[f"LOD_{tag.upper()}_MODEL"]
    added = []
    for src in main_scene.objects:
        if src.type != "MESH" or src.get("no_export"):
            continue
        n = src.name
        if n == "RALLY_cage" or src.get("no_lod"):
            continue                   # cage: rebuilt below with fewer sides; no_lod: cockpit details (shifter)
        is_graft, is_lamp = bool(src.get("rally_graft")), bool(src.get("rally_lamp"))
        if not (is_graft or is_lamp or n.startswith("RALLY_")):
            continue
        if is_lamp and not any((src.get("kn5_name") or "").endswith(k) for k in lamp_keep):
            continue
        if not keep_lips and any(k in n for k in ("RALLY_lip_", "RALLY_blade_")):
            continue
        if is_graft and wheel_keep is not None and src.data.materials[0].name not in wheel_keep:
            continue
        ob = src.copy(); ob.data = src.data.copy()
        col.objects.link(ob)
        ob["kn5_pristine"] = False
        for i, slot in enumerate(ob.material_slots):
            m = lod_mats.get(kdef_name(slot.material))
            if m is not None:
                ob.material_slots[i].material = m
        world = src.matrix_world.copy()
        if is_graft:
            tagw = src["rally_graft"]
            wheel = next((o for o in by_name.get(f"WHEEL_{tagw}", []) if o.type == "EMPTY"), None)
            if wheel is None:          # LOD d: no wheel nodes - fixed at the physics track width
                shift = Vector((AC_TYRE_X[tagw] - src.matrix_world.translation.x * 0 - _wheel_x(src), 0, 0))
                world = Matrix.Translation(shift) @ world
                parent = root
            else:
                parent = wheel
        else:
            parent = univers
        ob.parent = parent
        ob.matrix_parent_inverse.identity()
        ob.matrix_world = world
        if ratio < 0.999 and len(ob.data.polygons) > min_faces and not src.get("no_decimate"):
            dm = ob.modifiers.new("LOD", "DECIMATE")
            dm.ratio = max(ratio, min_faces / max(len(ob.data.polygons), 1))
            dm.use_collapse_triangulate = True
        added.append(ob)

    if CAGE_SEGS[tag]:
        cb = load("build_cage")
        me = bpy.data.meshes.new(f"RALLY_cage_lod_{tag}")
        cb.cage_bmesh(cb.cabin_bvh()[0], CAGE_SEGS[tag]).to_mesh(me)
        me.materials.append(bpy.data.materials["RALLY_cage"])
        ob = bpy.data.objects.new(f"RALLY_cage_lod_{tag}", me)
        col.objects.link(ob)
        ob["kn5_name"] = "RALLY_cage"
        ob.parent = univers
        ob.matrix_parent_inverse.identity()
        ob.matrix_world = main_scene.objects["RALLY_cage"].matrix_world.copy()
        added.append(ob)

    bpy.context.view_layer.update()
    exp = load("ac_kn5_export")
    path = os.path.join(OUT, f"sunbeam_rally_lod_{tag}.kn5")
    st = exp.export_kn5(path, [root], share_textures=True)
    add_tris = sum(tris(o) for o in added)
    bpy.context.window.scene = main_scene
    return {"stock_tris": stats["tris"], "stock_meshes_removed": removed, "rally_parts": len(added),
            "rally_tris": add_tris, "rear_strip": stripped, "exported": st}


def move_front_plate(lod_objs):
    """The front number plate onto the bumper face, as in LOD a (build_extras.PLATE_LIFT / PLATE_OUT)."""
    import bmesh
    ex = load("build_extras")
    delta = Vector((0.0, -ex.PLATE_OUT, ex.PLATE_LIFT))
    n = 0
    for o in lod_objs:
        if o.type != "MESH" or o.get("no_export") or not o.data.materials:
            continue
        if not any(kdef_name(m) == "EXT_PLATE_plastic" for m in o.data.materials):
            continue
        mw = o.matrix_world
        local = mw.inverted().to_3x3() @ delta
        bm = bmesh.new(); bm.from_mesh(o.data)
        front = {v for f in bm.faces if (mw @ f.calc_center_median()).y < -1.5
                 and kdef_name(o.data.materials[f.material_index]) == "EXT_PLATE_plastic" for v in f.verts}
        for v in front:
            v.co += local
        n += len(front)
        bm.to_mesh(o.data); bm.free()
    return n


# side stripes vs the (decimated) body: 0-26 mm apart in the stock LODs, some parts touching (flicker) or under the
# paint (vanish) - lifted to at least this, growing with the distance the level is seen from (b 15-45 m, c 45-200 m,
# d beyond), so the depth buffer can always separate them (build_extras.STRIPE_GAP for LOD a)
STRIPE_GAP_LOD = {"b": 0.003, "c": 0.008, "d": 0.015}


def lift_stripes(lod_objs, gap):
    ex = load("build_extras")
    meshes = [o for o in lod_objs if o.type == "MESH" and not o.get("no_export") and o.data.materials
              and not o.name.startswith("RALLY_")]
    body = ex.paint_bvh_of(meshes)
    n = 0
    for o in meshes:
        names = [kdef_name(m) for m in o.data.materials]
        if ex.STRIPE_MAT not in names:
            continue
        mi = names.index(ex.STRIPE_MAT)
        verts = {i for p in o.data.polygons if p.material_index == mi for i in p.vertices}
        n += ex.lift_off(o, verts, body, gap)
    return n


def drop_old_controls(lod_objs):
    """The old gear stick, road handbrake and gear gaiter (build_extras.OLD_CONTROLS boxes + materials), by face
    centre."""
    import bmesh
    entries = list(load("build_extras").OLD_CONTROLS.values())
    n = 0
    for o in lod_objs:
        if o.type != "MESH" or o.get("no_export"):
            continue
        mw = o.matrix_world
        names = [kdef_name(m) for m in o.data.materials]
        bm = bmesh.new(); bm.from_mesh(o.data)
        gone = []
        for f in bm.faces:
            c = mw @ f.calc_center_median()
            mat = names[f.material_index] if f.material_index < len(names) else None
            if any((mats is None or mat in mats) and b[0][0] <= c.x <= b[0][1] and b[1][0] <= c.y <= b[1][1]
                   and b[2][0] <= c.z <= b[2][1] for b, mats in entries):
                gone.append(f)
        if gone:
            bmesh.ops.delete(bm, geom=gone, context="FACES")
            bm.to_mesh(o.data)
            n += len(gone)
        bm.free()
    return n


EXHAUST_MATS = {"metal_smooth": "tips", "exhaustHole_updated": "tips", "metal_satin_dark": "pipe"}


def enlarge_exhaust(lod_objs):
    """The exhaust tips/collector as in LOD a (build_extras.exhaust_move), by material + position."""
    import bmesh
    ex = load("build_extras")
    n = 0
    for o in lod_objs:
        if o.type != "MESH" or o.get("no_export") or not o.data.materials:
            continue
        names = [kdef_name(m) for m in o.data.materials]
        if not any(nm in EXHAUST_MATS for nm in names):
            continue
        mw = o.matrix_world
        inv = mw.inverted()
        bm = bmesh.new(); bm.from_mesh(o.data)
        moved = {}
        for f in bm.faces:
            part = EXHAUST_MATS.get(names[f.material_index]) if f.material_index < len(names) else None
            c = mw @ f.calc_center_median()
            if part and 0.40 < c.x < 0.54 and 1.70 < c.y < 1.92 and 0.145 < c.z < 0.225:
                for v in f.verts:
                    moved.setdefault(v, part)
        for v, part in moved.items():
            v.co = inv @ ex.exhaust_move(mw @ v.co, part)
        n += len(moved)
        bm.to_mesh(o.data); bm.free()
    return n


def strip_rear(lod_objs, lod_mats):
    """REAR_DROP / REAR_REPAINT on one LOD's stock meshes (faces judged by their centre's y)."""
    import bmesh
    paint = lod_mats.get("painted_metal_smooth") or next(
        m for m in bpy.data.materials if m.get("kn5_def") and kdef_name(m) == "painted_metal_smooth")
    out = {"faces_dropped": 0, "faces_repainted": 0, "meshes_dropped": 0}
    for o in lod_objs:
        if o.type != "MESH" or o.get("no_export") or not o.data.materials:
            continue
        mn = kdef_name(o.data.materials[0])
        if mn not in REAR_DROP and mn not in REAR_REPAINT:
            continue
        mw = o.matrix_world
        bm = bmesh.new(); bm.from_mesh(o.data)
        if mn in REAR_DROP:
            gone = [f for f in bm.faces if REAR_DROP[mn](mw @ f.calc_center_median())]
            if len(gone) == len(bm.faces):
                o["no_export"] = True; out["meshes_dropped"] += 1; bm.free(); continue
            bmesh.ops.delete(bm, geom=gone, context="FACES")
            out["faces_dropped"] += len(gone)
        else:
            back = [f for f in bm.faces if (mw @ f.calc_center_median()).y > REAR_REPAINT_Y]
            if not back:
                bm.free(); continue
            if paint.name not in [m.name for m in o.data.materials]:
                o.data.materials.append(paint)
            pi = [m.name for m in o.data.materials].index(paint.name)
            for f in back:
                f.material_index = pi
            out["faces_repainted"] += len(back)
        bm.to_mesh(o.data); bm.free()
    return out


def _parents(o):
    p = o.parent
    while p is not None:
        yield p
        p = p.parent


_WHEEL_CENTRE_X = {}


def _wheel_x(src):
    """x of the stock wheel centre this grafted part was placed on (LOD0 WHEEL_xx)."""
    tagw = src["rally_graft"]
    if tagw not in _WHEEL_CENTRE_X:
        w = next(o for o in bpy.data.objects if o.get("kn5_name") == f"WHEEL_{tagw}" and o.type == "EMPTY"
                 and o.users_scene and o.users_scene[0].name == "Scene")
        _WHEEL_CENTRE_X[tagw] = w.matrix_world.translation.x
    return _WHEEL_CENTRE_X[tagw]


def build_all():
    main = bpy.context.window.scene
    os.makedirs(OUT, exist_ok=True)
    out = {}
    try:
        for tag in LEVELS:
            out[tag] = build_level(tag, main)
    finally:
        bpy.context.window.scene = main
    bpy.ops.wm.save_mainfile()
    return out

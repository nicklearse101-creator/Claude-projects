"""Model fixes asked for on 5 Oct (v24), each idempotent-ish and run once on blender/escort_aero.blend:

    import model_fixes as m
    m.level_exhaust()      # silencer rolled ~17 deg / yawed ~14 deg / pitched ~4.5 deg -> level and parallel to the car

Blender: +X = car's left, +Y = rear, Z up. Exhaust exits on the car's left (x ~0.37) through the rear lip's notch.
"""
import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

import build_aero as ba
import build_rear_dwb as r

EXHAUST_REGION = ((0.12, 0.80, -0.09), (0.45, 2.16, 0.125))     # whole exhaust behind the gearbox, world
OUTLET_COLLAR = ((0.30, 1.89, -0.012), (0.38, 1.925, 0.066))     # flange where the tail pipe leaves the silencer


def _classify(W, comps):
    """islands -> 'T' tail pipe/tip/hanger plate, 'S' silencer (+ its hangers), 'F' front pipe (crosses y 1.40)."""
    out = []
    lo_c, hi_c = OUTLET_COLLAR
    for comp in comps:
        P = W[comp]
        a, b = P.min(0), P.max(0)
        if a[1] < 1.40:
            out.append("F")
        elif a[1] >= 1.985 or b[1] >= 2.10 or (all(a >= np.array(lo_c)) and all(b <= np.array(hi_c))):
            out.append("T")
        else:
            out.append("S")
    return out


def _frames(W, comps, kinds):
    """Silencer: axis front cap -> rear cap, oval long axis; outlet point O; tail direction O -> tip."""
    caps = [(len(c), c) for c, k in zip(comps, kinds) if k == "S" and len(c) >= 60]
    caps.sort(key=lambda t: W[t[1]][:, 1].mean())
    front, rear = W[caps[0][1]], W[caps[-1][1]]
    fc, rc = (front.min(0) + front.max(0)) / 2, (rear.min(0) + rear.max(0)) / 2
    a = Vector(rc - fc).normalized()
    ev, evec = np.linalg.eigh(np.cov((rear - rear.mean(0)).T))
    u = Vector(evec[:, -1])
    u = (u - a * u.dot(a)).normalized()
    if u.x < 0:
        u = -u
    v = a.cross(u)
    lo_c, hi_c = OUTLET_COLLAR
    col = np.vstack([W[c] for c in comps if all(W[c].min(0) >= np.array(lo_c)) and all(W[c].max(0) <= np.array(hi_c))])
    O = Vector((col.min(0) + col.max(0)) / 2)
    tip = max((W[c] for c, k in zip(comps, kinds) if k == "T"), key=lambda P: P[:, 1].min())   # the end ring
    tipc = Vector((tip.min(0) + tip.max(0)) / 2)
    return a, u, v, O, tipc


def exhaust_transforms(o):
    """(S matrix, T matrix) in world space, from the main scene's exhaust_a_SUB2 (the source of truth)."""
    mw = o.matrix_world
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    W = np.array([list(mw @ v.co) for v in bm.verts])
    comps = [[u.index for u in c] for c in r._islands(bm)]
    bm.free()
    kinds = _classify(W, comps)
    a, u, v, O, tipc = _frames(W, comps, kinds)
    B = Matrix((a, u, v)).transposed()                       # columns a, u, v
    B2 = Matrix(((0, 1, 0), (1, 0, 0), (0, 0, -1))).transposed()   # -> +Y, +X, -Z
    Rs = B2 @ B.transposed()
    d = (tipc - O).normalized()
    Rt = d.rotation_difference(Vector((0, 1, 0))).to_matrix()
    to4 = lambda R: Matrix.Translation(O) @ R.to_4x4() @ Matrix.Translation(-O)
    info = dict(silencer_axis=[round(c, 3) for c in a], oval_long=[round(c, 3) for c in u],
                roll_deg=round(np.degrees(np.arctan2(-u.z, u.x)), 1),
                yaw_deg=round(np.degrees(np.arctan2(a.x, a.y)), 1), pitch_deg=round(np.degrees(np.arcsin(a.z)), 1),
                outlet=[round(c, 3) for c in O], tip=[round(c, 3) for c in tipc],
                tail_yaw_deg=round(np.degrees(np.arctan2(d.x, d.y)), 1), tail_pitch_deg=round(np.degrees(np.arcsin(d.z)), 1))
    return to4(Rs), to4(Rt), info


def _kn5_mat(ob):
    import json
    m = ob.data.materials[0] if ob.data.materials else None
    return json.loads(m["kn5_def"])["name"] if m is not None and "kn5_def" in m else (m.name if m else "")


def remove_islands(regions, scenes=("Scene", "LOD_B", "LOD_C", "LOD_D")):
    """regions: [(label, materials, ((lo), (hi)), mirror_x)] - an island goes when its kn5 material is listed and ALL
    its vertices sit in the box (or its mirror in x). COCKPIT_LR (__lr) copies and LOD meshes included."""
    done = {}
    for tag in scenes:
        for ob in bpy.data.scenes[tag].objects:
            if ob.type != "MESH" or str(ob.get("kn5_name") or ob.name).startswith("AERO") or not len(ob.data.vertices):
                continue
            mat = _kn5_mat(ob)
            regs = [(lab, (np.array(lo), np.array(hi)), mir) for lab, mats, (lo, hi), mir in regions if mat in mats]
            if not regs:
                continue
            mw = ob.matrix_world
            bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
            W = np.array([list(mw @ v.co) for v in bm.verts])
            kill = []
            for comp in r._islands(bm):
                P = W[[u.index for u in comp]]
                for lab, (lo, hi), mir in regs:
                    hit = ((P >= lo) & (P <= hi)).all()
                    if not hit and mir:
                        Q = P * np.array((-1, 1, 1))
                        hit = ((Q >= lo) & (Q <= hi)).all()
                    if hit:
                        kill += comp
                        done[(tag, lab)] = done.get((tag, lab), 0) + len(comp)
                        break
            if kill:
                bmesh.ops.delete(bm, geom=kill, context="VERTS"); bm.to_mesh(ob.data); ob.data.update()
            bm.free()
    return {f"{t}: {l}": n for (t, l), n in sorted(done.items())}


CARD = ("Material #385T34", "Material #400312")
HARDWARE = ("Material #210545", "Material #625FFFQW", "Material #530dqw")
DOOR_REGIONS = [   # boxes on the car's left door (+X), mirrored to the right
    ("door cards", CARD, ((0.50, -0.62, 0.05), (0.70, 0.56, 0.72)), True),
    ("interior door release", HARDWARE, ((0.62, -0.35, 0.47), (0.65, -0.24, 0.54)), True),
    ("pull handle", HARDWARE, ((0.59, -0.07, 0.35), (0.645, 0.145, 0.42)), True),
    ("window winder", HARDWARE, ((0.60, -0.45, 0.28), (0.645, -0.395, 0.415)), True),
    ("lock knob", HARDWARE, ((0.645, 0.41, 0.635), (0.67, 0.44, 0.68)), True),
]


def strip_doors():
    """Nik, 5 Oct: "Remove the internal door cards, window winder and door handles" - the doors' inner skin
    (painted, already modelled behind the cards) is what shows now."""
    return remove_islands(DOOR_REGIONS)


GEAR_REGIONS = [   # the H-pattern stick + ball knob (dash material) and its rubber gaiter
    ("gear stick + knob", ("Material #625FFFQW",), ((-0.021, -0.316, 0.386), (0.021, -0.264, 0.513)), False),
    ("gear gaiter", ("Material #638CAS",), ((-0.047, -0.354, 0.278), (0.047, -0.261, 0.395)), False),
]
# sequential: same knob position (centre 0, -0.287, top 0.511) so the driver's shift animation still lands on it
SHIFTER = dict(x=0.0, y=-0.287, knob_top=0.511, knob_r=0.017, knob_h=0.040, lever_r=0.0075, lever_base=0.336,
               box_c=(0.0, -0.305, 0.309), box_half=(0.034, 0.066, 0.027), rod_to=(0.0, -0.47, 0.292), rod_r=0.006)


def replace_gear_lever():
    rep = remove_islands(GEAR_REGIONS)
    s = SHIFTER
    trim, metal = ba.material(ba.TRIM), ba.material("Material #503ds")
    tuv = ba.pick_uv(trim, (0.70, 0.30, 0.75))[1]
    muv = ba.pick_uv(metal, (0.30, 1.00, 0.00))[1]
    x, y = s["x"], s["y"]
    knob_bot = s["knob_top"] - s["knob_h"]
    black = [r.box(s["box_c"], Vector((s["box_half"][0], 0, 0)), Vector((0, s["box_half"][1], 0)), Vector((0, 0, s["box_half"][2]))),
             r.tube((x, y, knob_bot), (x, y, s["knob_top"] - 0.004), s["knob_r"], n=16),
             r.tube((x, y, s["knob_top"] - 0.004), (x, y, s["knob_top"]), s["knob_r"], s["knob_r"] - 0.004, n=16)]
    bt = s["box_c"][2] + s["box_half"][2]
    steel = [r.tube((x, y, s["lever_base"]), (x, y, knob_bot + 0.006), s["lever_r"]),                 # lever
             r.tube((x, y, s["lever_base"] - 0.004), (x, y, s["lever_base"] + 0.010), 0.014),         # pivot boss
             r.box((x, y - 0.004, bt + 0.0015), Vector((0.022, 0, 0)), Vector((0, 0.048, 0)), Vector((0, 0, 0.0015))),  # gate plate
             r.tube((x, s["box_c"][1] - s["box_half"][1], s["rod_to"][2]), s["rod_to"], s["rod_r"])]   # rod to the gearbox
    rt = ba.root()
    for name, parts, mat, uv in (("AERO_seq_shifter", steel, metal, muv), ("AERO_seq_shifter_black", black, trim, tuv)):
        ob = ba.make_obj(name, ba.merge(*parts), mat, uv, rt)
        ob["interior_part"] = True
    return rep


EXTINGUISHER_REGIONS = [   # Nik, 5 Oct: "remove the fire extinguisher" (the cabin one on the passenger floor; the boot
    # one went with the old fuel system in build_tank.remove_old_tanks)
    ("cabin fire extinguisher", ("Material #680DDDQW", "Material #530dqw", "Material #1175ggre", "ID06_suede_001|floor_a",
                                 "emboss|floor_a"), ((-0.62, -0.42, 0.0), (-0.17, -0.05, 0.26)), False),
]


def remove_extinguisher():
    return remove_islands(EXTINGUISHER_REGIONS)


INNER_SKIN = dict(depth=0.060, below_z=0.68, uv_near=None)   # door box depth at the hems (outer skin x 0.74-0.775)


def build_door_inner_skins():
    """The cards were the doors' only inside surface - the outer skin faces outwards, so from the cabin AC would cull
    it and you'd look straight out. Inner skin = the outer skin below the window line, 6 cm in, facing the cabin,
    body colour (one paint texel, as the aero kit). Returns {side: object} (parented to the root; the door build
    re-parents them to the door nodes)."""
    src = next(o for o in ba.main_scene().objects if o.get("kn5_name") == "doorhandlelf_a_SUB2" and o.type == "MESH")
    paint = ba.material(ba.PAINT)
    puv = (0.857, 0.398)                                     # build_aero's body-colour texel
    mw = src.matrix_world
    out = {}
    for side, tag in ((1, "L"), (-1, "R")):
        bm = bmesh.new(); bm.from_mesh(src.data); bm.transform(mw); bm.verts.ensure_lookup_table()
        bm.normal_update()
        keep = [f for f in bm.faces if f.normal.x * side > 0.3 and all(v.co.z < INNER_SKIN["below_z"] and v.co.x * side > 0.6
                                                                      for v in f.verts)]
        vids = sorted({v.index for f in keep for v in f.verts})
        remap = {i: k for k, i in enumerate(vids)}
        vn = {i: Vector() for i in vids}
        for f in keep:
            for v in f.verts:
                vn[v.index] += f.normal
        verts = [tuple(bm.verts[i].co - vn[i].normalized() * INNER_SKIN["depth"]) for i in vids]
        faces = [tuple(remap[v.index] for v in reversed(f.verts)) for f in keep]
        bm.free()
        ob = ba.make_obj(f"AERO_door_inner_{tag}", (verts, faces), paint, puv, ba.root(), sharp_deg=60.0)
        me = ob.data; me.update()
        nx = sum(p.normal.x * p.area for p in me.polygons)
        if nx * side > 0:                                    # make_obj's normal recalc can pick either side of a sheet
            b2 = bmesh.new(); b2.from_mesh(me); bmesh.ops.reverse_faces(b2, faces=b2.faces); b2.to_mesh(me); b2.free()
        ob["door_part"] = tag
        out[tag] = ob
    return out


# ---- opening doors -----------------------------------------------------------------------------------------------
# Nik, 5 Oct: "The doors don't open". The model never had door nodes - every door part was merged into car-wide meshes.
# Each door's parts are split out (all attributes kept) under DOOR_L / DOOR_R at the hinge, and
# animations/car_door_L/R.ksanim swing them (Kunos' 190 DTM convention: rotation about the vertical, -/+ 75 deg there).
HINGE = dict(x=0.745, y=-0.660, z=0.45)                 # inside the doors' front edge (skin front at y -0.669, x <= 0.759)
DOOR_OPEN_DEG = 70.0
DOOR_SLAB = ((0.52, -0.70, 0.03), (0.80, 0.57, 1.08))    # left door's volume (mirror for the right)
DOOR_GLASS = ((0.53, -0.50, 0.64), (0.72, 0.56, 1.07))
DOOR_PARTS = [   # (kn5 node, test): "side" = every island on that side; "slab"/"glass" = islands inside that box
    ("doorhandlelf_a_SUB2", "side"), ("doorhandlelf_a_SUB1", "side"), ("doorhandlelf_a_SUB0", "side"),
    ("doorhandlelf_a_SUB3", "side"), ("doorhandlelf_a_SUB4", "side"),
    ("GLASS_OUT", "glass"), ("GLASS_IN", "glass"),
    ("dashstructure_a_SUB0", "seal"),                    # the door's window channel + perimeter seal (green in the check)
]
DOOR_LR_DROP = ["dashstructure_a_SUB0__lr"]              # low-res cockpit copies of the moved seals (would z-fight)


def _split_off(ob, keep, name, parent):
    """Move the vertices `keep` of `ob` (whole islands) into a new object under `parent`; UVs, custom normals and the
    kn5 corner normals/tangents travel with them."""
    me2 = ob.data.copy(); me2.name = name
    for me, kill in ((me2, lambda i: i not in keep), (ob.data, lambda i: i in keep)):
        bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if kill(v.index)], context="VERTS")
        bm.to_mesh(me); me.update(); bm.free()
    ob2 = ob.copy(); ob2.data = me2; ob2.name = name
    for col in ob.users_collection:
        col.objects.link(ob2)
    mw = ob.matrix_world.copy()
    ob2.parent = parent; ob2.matrix_world = mw
    ob2["kn5_name"] = name
    return ob2


def _door_islands(ob, side, test):
    mw = ob.matrix_world
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
    W = np.array([list(mw @ v.co) for v in bm.verts]) if len(bm.verts) else np.zeros((0, 3))
    keep = set()
    for comp in r._islands(bm):
        idx = [u.index for u in comp]
        P = W[idx] * np.array((side, 1, 1))              # mirror the right side onto the left-door boxes
        if test == "side":
            ok = P[:, 0].mean() > 0
        else:
            lo, hi = (np.array(b) for b in (DOOR_GLASS if test == "glass" else DOOR_SLAB))
            ok = ((P >= lo) & (P <= hi)).all() and (test != "seal" or P[:, 0].min() >= 0.60)
        if ok:
            keep.update(idx)
    bm.free()
    return keep


def build_doors(skins=None):
    """DOOR_L / DOOR_R empties at the hinges with the door parts under them (main model only - LODs keep closed doors)."""
    sc = ba.main_scene()
    rt = ba.root()
    skins = skins or {t: bpy.data.objects[f"AERO_door_inner_{t}"] for t in "LR"}
    rep = {}
    for side, tag in ((1, "L"), (-1, "R")):
        name = f"DOOR_{tag}"
        door = bpy.data.objects.get(name)
        if door is None:
            door = bpy.data.objects.new(name, None)
            sc.collection.objects.link(door)
        door.empty_display_type = "ARROWS"; door.empty_display_size = 0.15
        door.parent = rt
        door.matrix_world = Matrix.Translation((side * HINGE["x"], HINGE["y"], HINGE["z"]))
        door["kn5_name"] = name
        moved = []
        for node, test in DOOR_PARTS:
            ob = next((o for o in sc.objects if o.type == "MESH" and o.get("kn5_name") == node), None)
            if ob is None:
                continue
            keep = _door_islands(ob, side, test)
            if keep:
                moved.append((_split_off(ob, keep, f"{name}_{node}", door).name, len(keep)))
        for node in DOOR_LR_DROP:
            ob = next((o for o in sc.objects if o.type == "MESH" and (o.get("kn5_name") or o.name) == node), None)
            if ob is not None:
                keep = _door_islands(ob, side, "seal")
                if keep:
                    bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
                    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in keep], context="VERTS"); bm.to_mesh(ob.data); bm.free()
                    moved.append((f"{node} (deleted)", len(keep)))
        sk = skins[tag]
        mw = sk.matrix_world.copy(); sk.parent = door; sk.matrix_world = mw
        moved.append((sk.name, len(sk.data.vertices)))
        rep[name] = moved
    return rep


def door_kn5_rest(door):
    """The door node's local matrix exactly as ac_kn5_export writes it (AC axes: x left, y up, z forward)."""
    from ac_kn5_export import TO_AC, TO_AC_INV
    local = door.parent.matrix_world.inverted() @ door.matrix_world
    return TO_AC @ local @ TO_AC_INV


def write_door_ksanim(path, door, open_deg, frames=100):
    """ksanim v2: per node and frame a quaternion (x, y, z, w), a translation and a scale, in the parent's frame."""
    import math
    import struct
    rest = door_kn5_rest(door)
    t = rest.to_translation()
    q0 = rest.to_quaternion()
    from mathutils import Quaternion
    buf = struct.pack("<ii", 2, 1)
    nm = door.get("kn5_name", door.name).encode()
    buf += struct.pack("<i", len(nm)) + nm + struct.pack("<i", frames)
    for k in range(frames):
        u = k / (frames - 1)
        u = u * u * (3 - 2 * u)                              # ease in/out
        q = q0 @ Quaternion((0, 1, 0), math.radians(open_deg) * u)
        buf += struct.pack("<10f", q.x, q.y, q.z, q.w, t.x, t.y, t.z, 1.0, 1.0, 1.0)
    with open(path, "wb") as f:
        f.write(buf)
    return dict(node=nm.decode(), translation=[round(c, 4) for c in t], open_deg=open_deg, frames=frames)


def level_exhaust(dry=False):
    """Apply the transforms to every exhaust mesh in main + LODs (islands inside EXHAUST_REGION)."""
    src = next(o for o in ba.main_scene().objects if o.get("kn5_name") == "exhaust_a_SUB2" and o.type == "MESH")
    Ms, Mt, info = exhaust_transforms(src)
    if dry or (abs(info["roll_deg"]) < 0.5 and abs(info["yaw_deg"]) < 0.5 and abs(info["pitch_deg"]) < 0.5):
        return info                                          # already level (second run) or a dry look
    lo, hi = (np.array(p) for p in EXHAUST_REGION)
    done = {}
    for tag in ("Scene", "LOD_B", "LOD_C", "LOD_D"):
        for ob in bpy.data.scenes[tag].objects:
            # exhaust meshes only (LOD D merges everything into a few meshes); a region test alone also caught bolts on
            # the boot floor and a stray LOD triangle - those were put back from the saved file on 5 Oct
            nm = str(ob.get("kn5_name") or ob.name)
            if ob.type != "MESH" or not (nm.startswith("exhaust_a") or tag == "LOD_D"):
                continue
            mw = ob.matrix_world
            inv = mw.inverted()
            bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
            W = np.array([list(mw @ v.co) for v in bm.verts]) if len(bm.verts) else np.zeros((0, 3))
            comps = [[u.index for u in c] for c in r._islands(bm)]
            comps = [c for c in comps if (W[c] >= lo).all() and (W[c] <= hi).all()]
            if not comps:
                bm.free(); continue
            n = 0
            for c, k in zip(comps, _classify(W, comps)):
                for i in c:
                    p = Vector(W[i])
                    if k == "S":
                        q = Ms @ p
                    elif k == "T":
                        q = Mt @ p
                    elif p.y > 1.40:                         # front pipe: its rear end follows the silencer inlet
                        q = Ms @ p
                    else:
                        continue
                    bm.verts[i].co = inv @ q; n += 1
            bm.to_mesh(ob.data); ob.data.update(); bm.free()
            if n:
                ob["kn5_pristine"] = False      # stored original normals no longer match the rotated parts
            done[f"{tag}:{ob.name}"] = n
    info["moved_verts"] = done
    return info

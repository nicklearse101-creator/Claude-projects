"""v40 additions on top of kk_v40.run() (Nik 22-23 Nov):
  cut_hidden_arches  original wings/quarters trimmed where the Kadett kit hides them or where they show through
                     the kit's wheel openings
  exhaust            twin side exits (Y-piece from the V8 collector, out through the sills behind the rear vents)
  remove_knob        scuttle knob Object014
  belts_to_floor     shoulder straps anchored on the floor behind the seats instead of the parcel shelf
  door_backs         back faces for the door skins (window frame was invisible from inside)
  remove_dash_box    rally tripmeter box (ZERO/TOTAL/INTERVAL + TRIPMASTER) out, original dash recess left
  racelogic          RaceLogic unit (from ks_bmw_m4_gt3) on the dash top beside the wheel, screen mesh RACE_LOGIC
  nik_wheels         Nik's WHEEL_/SUSP_ node positions (CM save 22 Nov 20:32) kept
Blender axes: x = car's left, -y = front, z up.
"""
import json
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

import kk_build as kb
import kn5_import

EXIT_Y, EXIT_Z, EXIT_X = 0.18, -0.03, 0.948        # side exits, just behind the rear sill vent (ends y 0.07)
PIPE_R, TIP_R = 0.032, 0.040
COLLECTOR = Vector((0.21, 0.0, -0.022))              # V8_exhaust collector end (0.21, 0.033, -0.019), pipe starts inside it
DRIVER_EYE = Vector((0.29, 0.05, 0.95))
RL_POS = (0.02, -0.565)                              # RaceLogic on the dash top, inboard of the wheel (wheel x 0.286, r ~0.19)
M4 = r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\ks_bmw_m4_gt3\bmw_m4_acc.kn5"
M4_TEX = r"D:\Claude\escort_mk2_dtm\blender\donor_m4_textures"
NIK_SAVE = r"D:\Claude\escort_mk2_dtm\live_cm_save_2032\ford_escort_mk2_tuned.kn5"
DASH_BOX = (np.array([-0.515, -0.63, 0.37]), np.array([-0.165, -0.38, 0.735]))


def active(o):
    while o:
        if json.loads(o.get("kn5_flags", "{}")).get("active", 1) == 0:
            return False
        o = o.parent
    return True


def bvh(objs):
    verts, polys = [], []
    for o in objs:
        co = kb.world_co(o); base = len(verts)
        verts += [Vector(c) for c in co]
        polys += [[base + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def delete_faces(o, faces_idx):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in sorted(faces_idx)], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(o.data); bm.free()


def to_local(o, world):
    inv = np.linalg.inv(np.array(o.matrix_world))
    return (np.c_[world, np.ones(len(world))] @ inv.T)[:, :3]


def clear_custom_normals(o):
    me = o.data
    if "custom_normal" in me.attributes:
        me.attributes.remove(me.attributes["custom_normal"])
    if "kn5_pristine" in o:
        o["kn5_pristine"] = False
    for p in me.polygons:
        p.use_smooth = True
    me.set_sharp_from_angle(angle=math.radians(40))


# ---------------------------------------------------------------- arches
def cut_hidden_arches(main):
    kits = [o for o in main.objects if o.type == "MESH" and o.name.startswith("KK_kit")]
    tree = bvh(kits)
    kco = np.vstack([kb.world_co(o) for o in kits if "inner" not in o.name])
    wheels = [kb.E_F, kb.E_R]
    prof = {}
    for wi, (wy, wz) in enumerate(wheels):
        for side in (1, -1):
            m = (kco[:, 0] * side > 0.80) & (np.abs(kco[:, 1] - wy) < 0.6) & (kco[:, 2] > wz - 0.25)
            d = kco[m][:, 1:] - np.array([wy, wz])
            r = np.hypot(d[:, 0], d[:, 1]); th = np.degrees(np.arctan2(d[:, 1], d[:, 0]))
            bins = {}
            for rr, tt in zip(r, th):
                b = int(np.floor(tt / 5)); bins[b] = min(bins.get(b, 9), rr)
            prof[(wi, side)] = bins
    rep = {}
    for name in ("fenders_a_SUB2", "body_a_SUB1"):
        o = kb.obk(main, name)
        co = kb.world_co(o)
        hit_cache = {}

        def covered_v(i, side):
            k = (i, side)
            if k not in hit_cache:
                c = Vector(co[i])
                hit_cache[k] = tree.ray_cast(c + Vector((side * 0.002, 0, 0)), Vector((side, 0, 0)), 0.35)[0] is not None
            return hit_cache[k]
        dele = []
        for f in o.data.polygons:
            vs = list(f.vertices)
            c = co[vs].mean(0)
            if abs(c[0]) < 0.55 or c[2] > 0.66:
                continue
            side = 1 if c[0] > 0 else -1
            wi = next((i for i, (wy, _) in enumerate(wheels) if abs(c[1] - wy) < 0.62), None)
            if wi is None:
                continue
            if all(covered_v(i, side) for i in vs):
                dele.append(f.index); continue
            if abs(c[0]) > 0.68:
                dy, dz = c[1] - wheels[wi][0], c[2] - wheels[wi][1]
                ro = prof[(wi, side)].get(int(np.floor(np.degrees(np.arctan2(dz, dy)) / 5)))
                if ro is not None and np.hypot(dy, dz) < ro + 0.005:
                    dele.append(f.index)
        delete_faces(o, dele)
        rep[name] = len(dele)
    return rep


# ---------------------------------------------------------------- exhaust
def catmull(pts, n=10):
    P = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return out


def tube(bm, path, r, seg=18, cap_end=False):
    prev = None
    rings = []
    for i, p in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        if prev is None:
            ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            nrm = t.cross(ref).normalized()
        else:
            nrm = (prev - t * prev.dot(t)).normalized()
        prev = nrm
        bi = t.cross(nrm)
        rings.append([bm.verts.new(p + (nrm * math.cos(a) + bi * math.sin(a)) * r)
                      for a in np.linspace(0, 2 * math.pi, seg, endpoint=False)])
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(seg):
            bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    if cap_end:
        bm.faces.new(list(reversed(rings[-1])))
    return rings


def exhaust(main, mats):
    root = next(o for o in main.objects if o.get("kn5_root"))
    col = bpy.data.collections["KADETT_KIT"]
    split = COLLECTOR + Vector((0, 0.09, -0.008))
    paths = {
        1: [COLLECTOR, split, Vector((0.42, 0.155, -0.035)), Vector((0.72, EXIT_Y, EXIT_Z)), Vector((0.905, EXIT_Y, EXIT_Z))],
        -1: [split + Vector((-0.02, 0.01, 0)), Vector((0.02, 0.15, -0.04)), Vector((-0.42, 0.165, -0.035)),
             Vector((-0.72, EXIT_Y, EXIT_Z)), Vector((-0.905, EXIT_Y, EXIT_Z))]}
    pipe = bmesh.new(); tips = bmesh.new(); dark = bmesh.new()
    for side, pts in paths.items():
        tube(pipe, catmull(pts, 12), PIPE_R)
        x0, x1 = side * 0.90, side * EXIT_X
        tube(tips, [Vector((x0, EXIT_Y, EXIT_Z)), Vector(((x0 + x1) / 2, EXIT_Y, EXIT_Z)), Vector((x1, EXIT_Y, EXIT_Z))], TIP_R)
        tube(tips, [Vector((x1, EXIT_Y, EXIT_Z)), Vector((x1 - side * 0.004, EXIT_Y, EXIT_Z))], TIP_R - 0.003)   # rolled lip
        # sooty inside: disc a little in from the tip, facing out
        c = Vector((x1 - side * 0.012, EXIT_Y, EXIT_Z))
        ring = [dark.verts.new(c + Vector((0, math.cos(a), math.sin(a))) * (TIP_R - 0.002))
                for a in np.linspace(0, 2 * math.pi, 18, endpoint=False)]
        f = dark.faces.new(ring); f.normal_update()
        if f.normal.x * side < 0:
            f.normal_flip()
        # trim ring on the sill face
        c = Vector((side * 0.9365, EXIT_Y, EXIT_Z))
        inner = [dark.verts.new(c + Vector((0, math.cos(a), math.sin(a))) * (TIP_R + 0.001)) for a in np.linspace(0, 2 * math.pi, 24, endpoint=False)]
        outer = [dark.verts.new(c + Vector((0, math.cos(a), math.sin(a))) * (TIP_R + 0.014)) for a in np.linspace(0, 2 * math.pi, 24, endpoint=False)]
        for k in range(24):
            f = dark.faces.new((inner[k], inner[(k + 1) % 24], outer[(k + 1) % 24], outer[k])); f.normal_update()
            if f.normal.x * side < 0:
                f.normal_flip()
    out = []
    for bmx, name, mat in ((pipe, "KK_exhaust_pipes", mats["steel"]), (tips, "KK_exhaust_tips", mats["steel"]),
                           (dark, "KK_exhaust_dark", mats["black"])):
        me = bpy.data.meshes.new(name); bmx.to_mesh(me); bmx.free()
        for p in me.polygons:
            p.use_smooth = True
        ob = bpy.data.objects.new(name, me); kb.set_material(ob, mat)
        kb.link(ob, main, root, col); out.append(ob)
    return {o.name: len(o.data.polygons) for o in out}


def flames_ini():
    lines = ["[HEADER]", "INTENSITY=45.0", "EDIT_BIG=0", "EDIT_STATE=4", "BURN_FUEL_MULT=12", "FLASH_THRESHOLD=4", ""]
    d = Vector((1, 0, -0.25)).normalized()      # out of the side, a little rearward (AC: z forward)
    for i, side in enumerate((1, -1)):
        lines += [f"[FLAME_{i}]", f"POSITION={side * (EXIT_X + 0.012):.4f},{EXIT_Z:.4f},{-EXIT_Y:.4f}",
                  f"DIRECTION={side * d.x:.4f},0,{d.z:.4f}", "VSIZE_START=0.06", "VSIZE_END=0.26",
                  f"IS_LEFT={1 if side > 0 else 0}", "SIZE_MULT=1.4", "LSIZE=0.4", "GROUP=0", ""]
    return "\r\n".join(lines)


# ---------------------------------------------------------------- small fixes
KNOB = (np.array([0.545, -0.73, 0.655]), np.array([0.60, -0.675, 0.72]))   # scuttle knob (steel stem + black cap)


def remove_islands_in(sc, lo, hi, skip=("KK_", "AERO_", "RACE_LOGIC")):
    rep = {}
    for o in list(sc.objects):
        if o.type != "MESH" or o.name.startswith(skip):
            continue
        co = kb.world_co(o)
        if not ((co > lo) & (co < hi)).all(1).any():
            continue
        r = kb.islands(o.data)
        drop = np.zeros(len(co), bool)
        for k in np.unique(r):
            m = r == k
            if ((co[m] > lo) & (co[m] < hi)).all():
                drop[m] = True
        if drop.any():
            faces = [p.index for p in o.data.polygons if any(drop[v] for v in p.vertices)]
            delete_faces(o, faces); rep[o.get("kn5_name")] = len(faces)
    return rep


def remove_knob():
    """Scuttle knob by the left wiper: islands of grille_a_SUB4_SUB0 (stem) + body_a_SUB5 (cap), every model file."""
    rep = {}
    for sc in bpy.data.scenes:
        if sc.name in ("KADETT",):
            continue
        bpy.context.window.scene = sc; bpy.context.view_layer.update()
        r = remove_islands_in(sc, *KNOB)
        if r:
            rep[sc.name] = r
    bpy.context.window.scene = bpy.data.scenes["Scene"]
    return rep


def trim_sill_lip(main):
    """The restored v25 shell's sill lip under the doors pokes through the kit's sill top (dashed line) - trim it."""
    rep = {}
    for name in ("body_a_SUB1", "fenders_a_SUB2"):
        o = kb.obk(main, name); co = kb.world_co(o)
        faces = [p.index for p in o.data.polygons
                 if all(abs(co[v][0]) > 0.62 and co[v][2] < 0.07 and -0.82 < co[v][1] < 0.62 for v in p.vertices)]
        delete_faces(o, faces); rep[name] = len(faces)
    return rep


def belts_to_floor(main):
    dg = bpy.context.evaluated_depsgraph_get()
    hit = main.ray_cast(dg, Vector((0.27, 0.95, 0.6)), Vector((0, 0, -1)), distance=1.0)
    floor_z = hit[1].z if hit[0] else 0.12
    YA, Y0 = 0.95, 0.55
    za = floor_z + 0.015
    rep = {"floor_z": round(floor_z, 3)}
    for o in main.objects:
        k = str(o.get("kn5_name", ""))
        if o.type != "MESH" or not (k.startswith("CINTURE_OFF_SUB0") and not k.startswith("CINTURE_OFF_SUB00")
                                    or k.startswith("CINTURE_OFF_SUB003")):
            continue
        co = kb.world_co(o)
        ymax = co[:, 1].max()
        if ymax < 1.0:
            continue
        z0 = co[np.abs(co[:, 1] - Y0) < 0.03][:, 2].mean()
        z1 = co[co[:, 1] > ymax - 0.03][:, 2].mean()
        m = co[:, 1] > Y0
        t = (co[m, 1] - Y0) / (ymax - Y0)
        zc = z0 + t * (z1 - z0)
        co[m, 1] = Y0 + t * (YA - Y0)
        co[m, 2] = z0 + t * (za - z0) + (co[m, 2] - zc)
        o.data.vertices.foreach_set("co", to_local(o, co).ravel())
        o.data.update(); clear_custom_normals(o)
        rep[k] = int(m.sum())
    return rep


def door_backs(main):
    rep = {}
    for L in "LR":
        src = kb.obk(main, f"DOOR_{L}_doorhandlelf_a_SUB2")
        me = src.data.copy()
        if "custom_normal" in me.attributes:
            me.attributes.remove(me.attributes["custom_normal"])
        bm = bmesh.new(); bm.from_mesh(me)
        bm.normal_update()
        nrm = [v.normal.copy() for v in bm.verts]
        for v in bm.verts:
            v.co = v.co - nrm[v.index] * 0.0015
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(f"AERO_door_back_{L}", me)
        for p in me.polygons:
            p.use_smooth = True
        next(c for c in main.collection.children_recursive if src.name in c.objects).objects.link(ob)
        ob.parent = src.parent; ob.matrix_parent_inverse = src.matrix_parent_inverse.copy()
        ob.matrix_basis = src.matrix_basis.copy()
        rep[ob.name] = len(me.polygons)
    return rep


def remove_dash_box(main):
    lo, hi = DASH_BOX
    rep = {}
    for o in list(main.objects):
        if o.type != "MESH" or not active(o) or o.name.startswith(("KK_", "AERO_", "RACE_LOGIC")):
            continue
        if str(o.get("kn5_name", "")).startswith(("DOOR", "GLASS", "body_")):
            continue
        co = kb.world_co(o)
        if not ((co > lo) & (co < hi)).all(1).any():
            continue
        r = kb.islands(o.data)
        drop = np.zeros(len(co), bool)
        for k in np.unique(r):
            m = r == k
            if ((co[m] > lo) & (co[m] < hi)).all():
                drop[m] = True
        if not drop.any():
            continue
        faces = [p.index for p in o.data.polygons if any(drop[v] for v in p.vertices)]
        delete_faces(o, faces)
        rep[o.get("kn5_name")] = len(faces)
    return rep


# ---------------------------------------------------------------- RaceLogic
def racelogic(main, mats):
    tmp = bpy.data.scenes.new("M4_DONOR"); bpy.context.window.scene = tmp
    kn5_import.import_kn5(M4, M4_TEX, "M4_DONOR", prefix="M4_", primary=False)
    bpy.context.view_layer.update()
    rl = next(o for o in tmp.objects if o.type == "MESH" and o.get("kn5_name") == "RACE_LOGIC")
    c = kb.world_co(rl)
    lo = c.min(0) - np.array([0.03, 0.05, 0.04]); hi = c.max(0) + np.array([0.03, 0.06, 0.03])
    parts = []
    for name in ("RACE_LOGIC", "Object001", "Object002", "INT_DECALS001"):
        src = next(o for o in tmp.objects if o.type == "MESH" and o.get("kn5_name") == name)
        ob = kb.extract(src, "RACE_LOGIC" if name == "RACE_LOGIC" else f"KK_racelogic_{name}",
                        keep_island=lambda cc: ((cc > lo) & (cc < hi)).all())
        if len(ob.data.polygons):
            parts.append(ob)
    # source frame: screen normal (towards the M4 driver), up
    scr = parts[0]
    ns = sum((p.normal for p in scr.data.polygons), Vector()).normalized()
    allco = np.vstack([kb.world_co(o) for o in parts])
    cen = Vector(((allco.min(0) + allco.max(0)) / 2))
    bpy.context.window.scene = main; bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    x0, y0 = RL_POS
    org = Vector((x0, y0, 0.95)); zdash = None
    for _ in range(6):
        h = main.ray_cast(dg, org, Vector((0, 0, -1)), distance=0.6)
        if not h[0]:
            break
        if "GLASS" in str(h[4].get("kn5_name", "")).upper() or "glass" in h[4].name.lower():
            org = h[1] - Vector((0, 0, 0.002)); continue
        zdash = h[1].z; break
    zdash = zdash if zdash is not None else 0.69
    height = float(allco[:, 2].max() - allco[:, 2].min())
    P = Vector((x0, y0, zdash + 0.022 + height / 2))
    nt = (DRIVER_EYE - P).normalized()

    def frame(n):
        up = Vector((0, 0, 1)); up = (up - n * up.dot(n)).normalized(); rt = up.cross(n)
        return Matrix((rt, up, n)).transposed()
    R = frame(nt) @ frame(ns).inverted()
    T = Matrix.Translation(P) @ R.to_4x4() @ Matrix.Translation(-cen)
    root = next(o for o in main.objects if o.get("kn5_root"))
    col = bpy.data.collections["KADETT_KIT"]
    for ob in parts:
        ob.data.transform(T)
        if "custom_normal" in ob.data.attributes:
            pass                                    # rigid move: keep the Kunos normals (rotated with the mesh)
        col.objects.link(ob)
        ob.parent = root; ob.matrix_parent_inverse = root.matrix_world.inverted()
        ob["kk_interior"] = True
    scr = parts[0]; scr["kn5_name"] = "RACE_LOGIC"
    # bracket from the dash top to the unit
    allco = np.vstack([kb.world_co(o) for o in parts])
    zb = float(allco[:, 2].min())
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((x0 + v.co.x * 0.035, y0 + v.co.y * 0.025, (zdash - 0.01 + zb + 0.004) / 2 + v.co.z * (zb + 0.004 - zdash + 0.01)))
    me = bpy.data.meshes.new("KK_racelogic_bracket"); bm.to_mesh(me); bm.free()
    br = bpy.data.objects.new("KK_racelogic_bracket", me); kb.set_material(br, mats["black"])
    col.objects.link(br); br.parent = root; br.matrix_parent_inverse = root.matrix_world.inverted(); br["kk_interior"] = True
    for o in list(tmp.objects):
        bpy.data.objects.remove(o)
    bpy.data.scenes.remove(tmp)
    return {"dash_z": round(zdash, 3), "pos": [round(v, 3) for v in P], "parts": [o.name for o in parts] + [br.name]}


def nik_wheels(main):
    tmp = bpy.data.scenes.new("NIK"); bpy.context.window.scene = tmp
    kn5_import.import_kn5(NIK_SAVE, r"D:\ClaudeData\tmp\kadett\livetex", "NIK", prefix="N_", primary=False)
    names = [f"{p}_{c}" for p in ("WHEEL", "SUSP") for c in ("LF", "RF", "LR", "RR")]
    src = {o.get("kn5_name"): o for o in tmp.objects if o.type == "EMPTY" and o.get("kn5_name") in names}
    dst = {o.get("kn5_name"): o for o in main.objects if o.type == "EMPTY" and o.get("kn5_name") in names}
    for n in names:
        dst[n].matrix_local = kn5_import.blender_matrix(list(src[n]["kn5_matrix"]))
        dst[n]["kn5_matrix"] = list(src[n]["kn5_matrix"])
    for o in list(tmp.objects):
        bpy.data.objects.remove(o)
    bpy.data.scenes.remove(tmp)
    bpy.context.window.scene = main
    return len(names)

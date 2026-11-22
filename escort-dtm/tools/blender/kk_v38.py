"""v38 on top of kk_build (run on "escort_v37 kadett kit 2 built.blend"):
  * KK_kit rebuilt: edges that sat on the Kadett's own body are pulled onto the Escort body and the shift is faded
    into the kit over BLEND_R (seamless join), then given THICK thickness with closed rims (solid from behind)
  * vent openings in the kit filled with fine steel mesh (ptn_grillsquare material, alpha tested) + dark backing
  * splitter support rods (Kadett Plane.009) added; floating NICK3 alloy grille at the nose removed
  * front bumper + side markers re-activated, then kk_finish (rear fixes, LODs, export)
Saves "escort_v38 kadett kit blended.blend", exports to export_staging_v38_kadett_kit.
"""
import heapq
import json
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kk_build as kb       # noqa: E402
import kk_finish as kf      # noqa: E402

OUT = r"D:\Claude\escort_mk2_dtm\blender\escort_v38 kadett kit blended.blend"
kf.STAGE = r"D:\Claude\escort_mk2_dtm\export_staging_v38_kadett_kit"
kf.OUT_BLEND = OUT
ATTACH_TOL = 0.010          # kit boundary vertex within this of the Kadett body = an attachment edge
BLEND_R = 0.070             # fade the attachment shift over this geodesic distance
MAX_SHIFT = 0.10            # leave an edge alone if the Escort body is further than this
SURF_OFF = 0.0015           # edge sits this far outside the body surface
THICK = 0.0025
MESH_IN, BACK_IN = 0.006, 0.030
MESH_UV = 120.0              # steel mesh pattern repeats per metre
SMOOTH_ZONES = ((-1.40, -0.90), (0.20, 0.65))   # Kadett y: arch <-> sill transitions, smoothed
SMOOTH_ITERS, SMOOTH_FAC = 12, 0.45
V25 = "D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ford_escort_mk2_tuned_backup_v25"
# NICK3 cut the wheel openings out of these (v25 8776 / 20547 tris -> 6104 / 19281): put the whole panels back
RESTORE_PANELS = ("fenders_a_SUB2", "body_a_SUB1")
# deleted by the NICK3 work: front bumper, its side markers, front indicators
RESTORE_PARTS = {"A": ("bumperf_a_SUB0", "bumperf_a_SUB1", "bumperfsidemarkers_a_SUB2_SUB0",
                       "bumperfsidemarkersbulbs_a_SUB0", "glassbumperfsidemarkers_a_SUB0",
                       "glassbumperfsidemarkers_a_SUB2", "Object016", "Object017"),
                 "B": ("bumperf_a_SUB0", "bumperfsidemarkers_a_SUB2_SUB0", "glassbumperfsidemarkers_a_SUB0", "Object016"),
                 "C": ("bumperf_a_SUB0", "bumperfsidemarkers_a_SUB2_SUB0", "glassbumperfsidemarkers_a_SUB0", "Object016")}
FRONT_ON = {"bumperf_a", "bumperf_a_SUB0", "bumperf_a_SUB1", "bumperfsidemarkers_a", "bumperfsidemarkers_a_SUB2",
            "bumperfsidemarkers_a_SUB2_SUB0", "bumperfsidemarkersbulbs_a", "bumperfsidemarkersbulbs_a_SUB0",
            "glassbumperfsidemarkers_a", "glassbumperfsidemarkers_a_SUB0", "glassbumperfsidemarkers_a_SUB2"}


def bvh_of(objs):
    verts, polys = [], []
    for o in objs:
        co = kb.world_co(o); base = len(verts)
        verts += [Vector(c) for c in co]
        polys += [[base + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def boundary_loops(bm):
    edges = [e for e in bm.edges if e.is_boundary]
    seen, loops = set(), []
    adj = {}
    for e in edges:
        for v in e.verts:
            adj.setdefault(v.index, []).append(e)
    for e0 in edges:
        if e0.index in seen:
            continue
        comp, st = [], [e0]
        seen.add(e0.index)
        while st:
            e = st.pop(); comp.append(e)
            for v in e.verts:
                for e2 in adj[v.index]:
                    if e2.index not in seen:
                        seen.add(e2.index); st.append(e2)
        loops.append(comp)
    return loops


def order_loop(comp):
    adj = {}
    for e in comp:
        a, b = e.verts
        adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    if any(len(n) != 2 for n in adj.values()):
        return None
    start = comp[0].verts[0]; out = [start]; prev, cur = None, start
    while True:
        nxt = [n for n in adj[cur] if n is not prev]
        nxt = nxt[0] if nxt else None
        if nxt is None or nxt is start:
            break
        out.append(nxt); prev, cur = cur, nxt
    return out if len(out) == len(adj) else None


def build_kit(main, ks):
    for o in [o for o in main.objects if o.name.startswith("KK_kit")]:
        bpy.data.objects.remove(o)
    src = kb.obk(ks, "Plane.017")
    kit = kb.extract(src, "KK_kit")
    me = kit.data
    if "custom_normal" in me.attributes:
        me.attributes.remove(me.attributes["custom_normal"])
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0002)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table()
    # attachment: boundary verts on the Kadett body (Kadett coords)
    kbody = [o for o in ks.objects if o.type == "MESH" and o.data.materials
             and o.data.materials[0].name == "K_karoseria" and o.get("kn5_name") != "Plane.017"]
    kt = bvh_of(kbody)
    bnd = {v.index for e in bm.edges if e.is_boundary for v in e.verts}
    attach = {i for i in bnd if (h := kt.find_nearest(bm.verts[i].co)) and h[0] is not None and h[3] < ATTACH_TOL}
    loops = boundary_loops(bm)
    # map to Escort space
    kco = np.array([v.co[:] for v in bm.verts])
    co = kb.kit_map(kco)
    for v, c in zip(bm.verts, co):
        v.co = c
    ky = np.array([v[1] for v in kco])
    zone = np.zeros(len(ky), bool)
    for a, b in SMOOTH_ZONES:
        zone |= (ky > a) & (ky < b)
    movable = [v for v in bm.verts if zone[v.index] and v.index not in bnd]
    for _ in range(SMOOTH_ITERS):
        new = {}
        for v in movable:
            nb = [e.other_vert(v).co for e in v.link_edges]
            new[v] = v.co + (sum(nb, Vector()) / len(nb) - v.co) * SMOOTH_FAC
        for v, c in new.items():
            v.co = c
    # pull attachment verts onto the Escort body
    ebody = [o for o in main.objects if o.type == "MESH" and o.get("kn5_name") in ("body_a_SUB1", "fenders_a_SUB2")]
    et = bvh_of(ebody)
    disp = {}
    for i in attach:
        p = bm.verts[i].co
        loc, nrm, _, d = et.find_nearest(p)
        if loc is None or d > MAX_SHIFT:
            continue
        n = nrm if (p - loc).dot(nrm) >= 0 else -nrm
        disp[i] = (loc + n * SURF_OFF) - p
    # geodesic fade (Dijkstra from the attachment verts, carrying the source's shift)
    dist = {i: 0.0 for i in disp}; srcof = {i: i for i in disp}
    pq = [(0.0, i) for i in disp]
    while pq:
        d, i = heapq.heappop(pq)
        if d > dist.get(i, 9) or d > BLEND_R:
            continue
        v = bm.verts[i]
        for e in v.link_edges:
            j = e.other_vert(v).index
            nd = d + e.calc_length()
            if nd < dist.get(j, 9) and nd <= BLEND_R:
                dist[j] = nd; srcof[j] = srcof[i]; heapq.heappush(pq, (nd, j))
    for j, d in dist.items():
        t = 1 - d / BLEND_R
        w = t * t * (3 - 2 * t)
        bm.verts[j].co += disp[srcof[j]] * w
    # vent openings: closed boundary loops with no attachment verts, small, on the outside
    vents = []
    for comp in loops:
        vs = order_loop(comp)
        if vs is None:
            continue
        idx = {v.index for v in vs}
        per = sum(e.calc_length() for e in comp)
        if idx & attach or per > 1.4 or len(vs) < 4:
            continue
        vents.append([v.co.copy() for v in vs] + [np.mean([f.normal for v in vs for f in v.link_faces], axis=0)])
    bm.to_mesh(me); bm.free()
    kb.set_material(kit, kb_mats["paint"]); kb.const_uv(kit, kb.PAINT_UV)
    # thickness (inward, rims closed)
    main.collection.objects.link(kit)
    sm = kit.modifiers.new("T", "SOLIDIFY"); sm.thickness = THICK; sm.offset = -1; sm.use_rim = True
    sm.use_even_offset = False; sm.thickness_clamp = 1.0
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(kit.evaluated_get(dg))
    kit.modifiers.clear(); old = kit.data; kit.data = new; bpy.data.meshes.remove(old)
    main.collection.objects.unlink(kit)
    for p in kit.data.polygons:
        p.use_smooth = True
    kit.data.set_sharp_from_angle(angle=np.radians(40))
    return kit, {"attach_verts": len(attach), "pulled": len(disp), "faded": len(dist), "vents": len(vents)}, vents


def vent_parts(vents, mesh_mat, back_mat):
    out = []
    for name, inset, mat, uvs in (("KK_vent_mesh", MESH_IN, mesh_mat, MESH_UV), ("KK_vent_back", BACK_IN, back_mat, 1.0)):
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        for loop in vents:
            pts, n = loop[:-1], Vector(loop[-1]).normalized()
            vs = [bm.verts.new(p - n * inset) for p in pts]
            try:
                f = bm.faces.new(vs)
            except ValueError:
                continue
            if f.normal.dot(n) < 0:
                f.normal_flip()
            for lp in f.loops:  # noqa
                c = lp.vert.co
                lp[uvl].uv = (c.y * uvs, c.z * uvs)
        bmesh.ops.triangulate(bm, faces=bm.faces, quad_method="BEAUTY", ngon_method="BEAUTY")
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(name, me); kb.set_material(ob, mat)
        for p in me.polygons:
            p.use_smooth = False
        out.append(ob)
    return out


kb_mats = {}


def restore_v25(tag, panels, parts):
    """Bring meshes back from the BACKUP v25 car: panels replace the live mesh data, parts are re-created under
    their (still present) live dummies. Materials are matched by kn5 name."""
    import kn5_import
    sc = bpy.data.scenes[kf.SCENES[tag]]
    tmp = bpy.data.scenes.new(f"V25_{tag}")
    bpy.context.window.scene = tmp
    kn5_import.import_kn5(os.path.join(V25, kf.FILES[tag]), "D:/ClaudeData/tmp/kadett/v25tex", f"V25_{tag}",
                          prefix="V25_", primary=False)
    bpy.context.view_layer.update()
    bpy.context.window.scene = sc; bpy.context.view_layer.update()
    mats = kf.mats_of(sc)
    donor = {o.get("kn5_name"): o for o in tmp.objects if o.type == "MESH"}
    live_mesh = {o.get("kn5_name"): o for o in sc.objects if o.type == "MESH"}
    live_dummy = {o.get("kn5_name"): o for o in sc.objects if o.type == "EMPTY"}
    done = []
    for name in panels + parts:
        d = donor.get(name)
        if d is None:
            continue
        me = d.data.copy()
        for i, m in enumerate(me.materials):
            me.materials[i] = mats[kf.kname(m).removeprefix("V25_")]
        if name in panels and name in live_mesh:
            lo = live_mesh[name]
            keep = [s.material for s in lo.material_slots]
            old = lo.data; lo.data = me; bpy.data.meshes.remove(old)
            for i, m in enumerate(keep[:len(lo.material_slots)]):
                lo.material_slots[i].material = m        # keep the live material (body_a_SUB1 -> #25DQW)
            done.append(name)
        elif name in parts and name not in live_mesh and name not in live_dummy and tag != "A":
            ob = bpy.data.objects.new(name, me)
            for k in d.keys():
                ob[k] = d[k]
            root = next(o for o in sc.objects if o.get("kn5_root"))
            next(c for c in sc.collection.children_recursive if root.name in c.objects).objects.link(ob)
            ob.parent = root; ob.matrix_parent_inverse.identity(); ob.matrix_world = d.matrix_world.copy()
            done.append(name)
        elif name in parts and name not in live_mesh and name in live_dummy:
            ob = bpy.data.objects.new(name, me)
            for k in d.keys():
                ob[k] = d[k]
            next(c for c in sc.collection.children_recursive if live_dummy[name].name in c.objects).objects.link(ob)
            ob.parent = live_dummy[name]; ob.matrix_parent_inverse.identity(); ob.matrix_local = d.matrix_local
            done.append(name)
    for o in list(tmp.objects):
        bpy.data.objects.remove(o)
    bpy.data.scenes.remove(tmp)
    return done


def run():
    main = bpy.data.scenes["Scene"]; ks = bpy.data.scenes["KADETT"]
    bpy.context.window.scene = ks; bpy.context.view_layer.update()
    bpy.context.window.scene = main; bpy.context.view_layer.update()
    mats = kf.mats_of(main)
    kb_mats.update(paint=mats["Material #25DQW"], carbon=mats["NICK3_carbon"], mesh=mats["Material #41dda"],
                   black=mats["Material #166GG45"], steel=mats["Material #503ds"])
    root = next(o for o in main.objects if o.get("kn5_root"))
    col = bpy.data.collections["KADETT_KIT"]
    rep = {"restored_A": restore_v25("A", RESTORE_PANELS, RESTORE_PARTS["A"])}
    bpy.context.window.scene = main; bpy.context.view_layer.update()
    kit, rep["kit"], vents = build_kit(main, ks)
    parts = [kit] + vent_parts(vents, kb_mats["mesh"], kb_mats["black"])
    # splitter support rods
    rods = kb.extract(kb.obk(ks, "Plane.009"), "KK_splitter_rods",
                      keep_island=lambda c: c[:, 1].max() < -2.1 and c[:, 1].min() > -2.45 and c[:, 2].max() < 0.5
                      and c[:, 2].max() - c[:, 2].min() > 0.25 and c[:, 0].max() - c[:, 0].min() < 0.02)
    kb.apply_map(rods, lambda p: kb.arch_map(p, kb.K_F, kb.E_F)); kb.set_material(rods, kb_mats["steel"])
    kb.renormal(rods, merge=0.0, angle=60)
    rep["rod_faces"] = len(rods.data.polygons)
    parts.append(rods)
    for ob in parts:
        kb.link(ob, main, root, col)
    # floating NICK3 alloy grille at the nose
    al = kb.obk(main, "NICK3_STATIC_MESH_NICK3_alloy")
    co = kb.world_co(al)
    bm = bmesh.new(); bm.from_mesh(al.data); bm.verts.ensure_lookup_table()
    bad = [f for f in bm.faces if any(co[v.index][1] < -1.6 for v in f.verts)]
    bmesh.ops.delete(bm, geom=bad, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(al.data); bm.free()
    rep["alloy_faces_removed"] = len(bad)
    bpy.context.view_layer.update()
    rep["parts"] = {o.name: len(o.data.polygons) for o in main.objects if o.get("kk_part") and o.type == "MESH"}
    return rep


if __name__ == "__main__":
    rep = run()
    kf.REAR_ON |= FRONT_ON
    for tag in "ABCD":
        rep[f"fix_{tag}"] = kf.rear_fixes(bpy.data.scenes[kf.SCENES[tag]])
    for tag in "BC":
        rep[f"restored_{tag}"] = restore_v25(tag, (), RESTORE_PARTS[tag])
    bpy.context.window.scene = bpy.data.scenes["Scene"]
    for tag in "BCD":
        rep[f"kit_{tag}"] = kf.lod_kit(tag)
    bpy.context.window.scene = bpy.data.scenes["Scene"]
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    rep["export"] = kf.export_all()
    print("REPORT", json.dumps(rep))

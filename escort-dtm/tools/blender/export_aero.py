"""Export the Escort with the aero kit (runs inside Blender after build_aero.build()):
  * main model  -> export/ford_escort_mk2_tuned.kn5 (the imported 101Creative tree, untouched, + AERO_* nodes)
  * LODs b/c/d  -> export/ford_escort_mk2_tuned_lod_{b,c,d}.kn5: the mod's own LODs + decimated copies of the
    aero parts (materials remapped to the LOD file's same-named ones; no hood_trunk node in the LODs, so the wing
    hangs off the LOD root - the boot doesn't open at LOD distance anyway)
"""
import json
import os

import bpy

import ac_kn5_export as ex
import escort_scene as es

# level: (decimate ratio, minimum faces per part, parts left out)
RSUS = ("AERO_rsus_wishbones", "AERO_rsus_toe_links", "AERO_rsus_dampers", "AERO_rsus_springs", "AERO_rsus_driveshafts",
        "AERO_rsus_brackets", "AERO_rsus_upright_L", "AERO_rsus_upright_R")      # build_rear_dwb.py (under the car)
TANK = ("AERO_fueltank", "AERO_fueltank_frame")                       # build_tank.py (closed boot at LOD distance)
SHIFTER = ("AERO_seq_shifter", "AERO_seq_shifter_black")              # model_fixes.replace_gear_lever
DOOR_SKINS = ("AERO_door_inner_L", "AERO_door_inner_R")               # model_fixes: LOD B/C lost their door cards too
# v25: closed doors / bonnet / boot at LOD distance - door ends, handles, footrest and the V8 stay out of the LODs;
# the door mirrors are outside, so B and C get them; the rear ARB joins the rear suspension's rules
DOOR_V25 = tuple(f"AERO_door_{p}_{s}" for p in ("ends", "grab", "release") for s in "LR")
INTERIOR_V25 = ("AERO_footrest", "AERO_footrest_legs", "AERO_footrest_bolts")
MIRRORS = ("AERO_mirror_L", "AERO_mirror_R", "AERO_mirror_glass_L", "AERO_mirror_glass_R")
ARB = ("AERO_rsus_arb", "AERO_rsus_arb_links")
V8 = ("V8_alloy", "V8_cam_covers", "V8_black", "V8_steel", "V8_anodised_blue", "V8_anodised_red", "V8_exhaust")
NEVER_IN_LODS = DOOR_V25 + INTERIOR_V25 + V8
LEVELS = {"B": (0.5, 60, TANK + NEVER_IN_LODS),
          "C": (0.25, 40, ("AERO_strakes", "AERO_rsus_springs", "AERO_rsus_toe_links", "AERO_rsus_arb_links") + TANK + SHIFTER
                + NEVER_IN_LODS),
          "D": (0.12, 24, ("AERO_strakes", "AERO_skirts", "AERO_splitter", "AERO_rear_lip") + RSUS + ARB + TANK + SHIFTER
                + DOOR_SKINS + MIRRORS + NEVER_IN_LODS)}


def kname(m):
    return json.loads(m["kn5_def"])["name"] if m is not None and "kn5_def" in m else None


def lod_level(tag, parts):
    sc = es.scene_of(tag)
    for o in [o for o in sc.objects if o.get("aero_lod")]:
        bpy.data.objects.remove(o)
    ratio, min_faces, skip = LEVELS[tag]
    root = es.root_of(tag)
    mats = {kname(bpy.data.materials[n]): bpy.data.materials[n] for n in json.loads(sc["kn5_materials"])}
    col = bpy.data.collections[f"LOD_{tag}_MODEL"]
    added = []
    for src in parts:
        if src.name in skip:
            continue
        ob = src.copy(); ob.data = src.data.copy()
        for k in ("aero_part",):
            if k in ob:
                del ob[k]
        ob["aero_lod"] = True
        ob.name = src.name                      # kn5 node name (Blender adds .001 - the exporter uses kn5_name)
        ob["kn5_name"] = src.name
        for i, slot in enumerate(ob.material_slots):
            k = kname(slot.material)
            if k not in mats:                   # v25 materials that only exist in the main file (treadplate, V8 ...)
                k = slot.material.get("lod_fallback") or json.loads(slot.material["kn5_def"])["name"]
            ob.material_slots[i].material = mats[k]
        col.objects.link(ob)
        world = src.matrix_world.copy()
        ob.parent = root
        ob.matrix_parent_inverse.identity()
        ob.matrix_world = world
        n = len(ob.data.polygons)
        if n > min_faces:
            dm = ob.modifiers.new("LOD", "DECIMATE")
            dm.ratio = max(ratio, min_faces / n)
            dm.use_collapse_triangulate = True
        added.append(ob)
    return added


def export():
    import build_aero
    main = es.scene_of("A")
    parts = build_aero.parts()
    if not parts:
        raise RuntimeError("no AERO parts - run build_aero.build() first")
    os.makedirs(es.EXPORT, exist_ok=True)
    out = {}
    try:
        bpy.context.window.scene = main
        out["A"] = ex.export_kn5(os.path.join(es.EXPORT, es.FILES["A"]), [es.root_of("A")])
        for tag in "BCD":
            added = lod_level(tag, parts)
            bpy.context.window.scene = es.scene_of(tag)
            bpy.context.view_layer.update()
            st = ex.export_kn5(os.path.join(es.EXPORT, es.FILES[tag]), [es.root_of(tag)], share_textures=True)
            st["aero_parts"] = len(added)
            out[tag] = st
    finally:
        bpy.context.window.scene = main
    bpy.ops.wm.save_mainfile()
    return out


def compare(tag):
    """Structural diff of an exported file vs the untouched source: every original node must come back
    identical and in order; returns the added node names and any original node that changed."""
    import kn5_compare as kc
    a = kc.parse(os.path.join(es.SOURCE, es.FILES[tag]))
    b = kc.parse(os.path.join(es.EXPORT, es.FILES[tag]))
    na, nb = a[3], b[3]
    ours = [n for n in nb if n[2].startswith("AERO_")]
    rest = [n for n in nb if not n[2].startswith("AERO_")]
    strip = lambda n: n[:3] + n[4:]                 # everything but the child count
    changed = [na[i][2] for i in range(min(len(na), len(rest))) if strip(na[i]) != strip(rest[i])]
    more_kids = [(p[2], p[3], q[3]) for p, q in zip(na, rest) if p[3] != q[3]]
    return {"header": a[0] == b[0], "textures": a[1] == b[1], "materials": a[2] == b[2],
            "original_nodes": (len(na), len(rest)), "original_nodes_changed": changed[:10],
            "parents_with_new_children": more_kids, "added": sorted({n[2] for n in ours if n[1] == 1}),
            "added_tris": sum(n[6] for n in ours if n[1] == 2)}

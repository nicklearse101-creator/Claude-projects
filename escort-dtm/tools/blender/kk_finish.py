"""v37 finish: rear lights + bumper back on, rear body painted, red-only tail lights, Kadett kit into the LODs,
export to a staging folder. Run on "escort_v37 kadett kit 2 built.blend" (output of kk_build.py):
    blender -b "<blend>" --python kk_finish.py
Saves "escort_v37 kadett kit 3 finished.blend" and writes export_staging_v37_kadett_kit/*.kn5.

Why the rear was missing / unpainted (found 22 Nov, live kn5 vs BACKUP v25):
  * 44 rear nodes (bumper, tail lights, lenses, bulbs, plate, rear trim) had their kn5 'active' flag set to 0
    by the NICK3 work (its replacement tail pieces were never exported) - AC skips inactive nodes.
  * body_a_SUB1 (rear half of the shell) was given a renamed copy of the paint material that samples
    STOCK_metal_detail.dds / STOCK_AO_BODY.dds; skins colour the car through metal_detail.dds, so the rear never
    took the skin colour.
"""
import json
import os
import sys

import bpy

sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import ac_kn5_export as ex          # noqa: E402

OUT_BLEND = r"D:\Claude\escort_mk2_dtm\blender\escort_v37 kadett kit 3 finished.blend"
STAGE = r"D:\Claude\escort_mk2_dtm\export_staging_v37_kadett_kit"
FILES = {"A": "ford_escort_mk2_tuned.kn5", "B": "ford_escort_mk2_tuned_lod_b.kn5",
         "C": "ford_escort_mk2_tuned_lod_c.kn5", "D": "ford_escort_mk2_tuned_lod_d.kn5"}
SCENES = {"A": "Scene", "B": "LOD_B", "C": "LOD_C", "D": "LOD_D"}

REAR_ON = {"BRAKE_GLASS", "BRAKE_IN", "FOG_GLASS", "FOG_GLASS_2", "FOG_IN", "INDICATOR_LR", "INDICATOR_LR_IN",
           "INDICATOR_RR", "INDICATOR_RR_IN", "Object008", "REVERSE_GLASS", "REVERSE_IN", "bumperr_a",
           "bumperr_a_SUB1", "glassctl_a", "glassltl_a_SUB13", "glassrtl_a_SUB13", "glassrtl_a_SUB6",
           "plateeu_a_SUB2", "taillightc_a_SUB1", "taillightl_a_SUB1", "taillightlbulbs_a_SUB2",
           "taillightlbulbs_a_SUB4", "taillightlbulbs_a_SUB6", "taillightrbulbs_a_SUB0", "taillightrbulbs_a_SUB2",
           "taillightrbulbs_a_SUB6", "trunk_a_SUB1", "trunklivery_arsw"}
RED_LENS = {"INDICATOR_LR": "BRAKE_GLASS", "INDICATOR_RR": "BRAKE_GLASS", "REVERSE_GLASS": "BRAKE_GLASS",
            "INDICATOR_LR_IN": "BRAKE_IN", "INDICATOR_RR_IN": "BRAKE_IN", "REVERSE_IN": "BRAKE_IN"}
KIT_LOD = {"B": 0.5, "C": 0.25, "D": 0.10}


def kname(m):
    return json.loads(m["kn5_def"])["name"] if m is not None and "kn5_def" in m else None


def mats_of(sc):
    return {kname(bpy.data.materials[n]): bpy.data.materials[n] for n in json.loads(sc["kn5_materials"])}


def rear_fixes(sc):
    rep = {"activated": 0, "repainted": 0, "red_lens": 0}
    mats = mats_of(sc)
    for o in sc.objects:
        k = o.get("kn5_name")
        if k in REAR_ON and "kn5_flags" in o:
            fl = json.loads(o["kn5_flags"])
            if fl.get("active") == 0:
                fl["active"] = 1; o["kn5_flags"] = json.dumps(fl); rep["activated"] += 1
        if o.type != "MESH":
            continue
        if k == "body_a_SUB1" and "Material #25DQW" in mats:
            for s in o.material_slots:
                if kname(s.material) == "STOCK_Material #25DQW":
                    s.material = mats["Material #25DQW"]; rep["repainted"] += 1
        if k in RED_LENS:
            src = next((x for x in sc.objects if x.type == "MESH" and x.get("kn5_name") == RED_LENS[k]), None)
            if src is not None:
                o.material_slots[0].material = src.material_slots[0].material; rep["red_lens"] += 1
    return rep


def lod_kit(tag):
    """Copy the KK_* parts (main scene) into LOD tag, decimated, materials remapped by kn5 name; drop NICK3 parts
    the kit replaced."""
    main, sc = bpy.data.scenes["Scene"], bpy.data.scenes[SCENES[tag]]
    gone = []
    for o in list(sc.objects):
        if o.type == "MESH" and o.get("kn5_name") in ("NICK3_front_clip",):
            gone.append(o.get("kn5_name")); bpy.data.objects.remove(o)
    mats = mats_of(sc)
    root = next(o for o in sc.objects if o.get("kn5_root"))
    col = next(c for c in sc.collection.children)
    added = []
    for src in [o for o in main.objects if o.get("kk_part")]:
        ob = src.copy(); ob.data = src.data.copy(); ob.name = src.name
        for i, s in enumerate(ob.material_slots):
            k = kname(s.material)
            if k not in mats:
                k = "Material #166GG45"          # black trim (every LOD file has it)
            ob.material_slots[i].material = mats[k]
        col.objects.link(ob)
        w = src.matrix_world.copy()
        ob.parent = root; ob.matrix_parent_inverse.identity(); ob.matrix_world = w
        if tag == "D" and src.name in ("KK_fins", "KK_splitter"):
            bpy.data.objects.remove(ob); continue
        dm = ob.modifiers.new("LOD", "DECIMATE"); dm.ratio = KIT_LOD[tag]; dm.use_collapse_triangulate = True
        added.append(ob.name)
    return {"removed": gone, "added": added}


def export_all():
    os.makedirs(STAGE, exist_ok=True)
    out = {}
    main = bpy.data.scenes["Scene"]
    try:
        for tag, fname in FILES.items():
            sc = bpy.data.scenes[SCENES[tag]]
            bpy.context.window.scene = sc; bpy.context.view_layer.update()
            root = next(o for o in sc.objects if o.get("kn5_root"))
            st = ex.export_kn5(os.path.join(STAGE, fname), [root], share_textures=(tag != "A"))
            out[tag] = {k: st[k] for k in ("tris", "materials", "textures") if k in st}
    finally:
        bpy.context.window.scene = main
    return out


if __name__ == "__main__":
    rep = {}
    for tag in "ABCD":
        rep[f"rear_{tag}"] = rear_fixes(bpy.data.scenes[SCENES[tag]])
    for tag in "BCD":
        rep[f"kit_{tag}"] = lod_kit(tag)
    bpy.context.window.scene = bpy.data.scenes["Scene"]
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    rep["export"] = export_all()
    print("REPORT", json.dumps(rep))

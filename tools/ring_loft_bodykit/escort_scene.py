"""Load the live Escort's kn5s into Blender (main model in scene "Scene", LODs in LOD_B/C/D) and check the
lossless round trip. Runs inside Blender with blender/escort_aero.blend open.

    import sys; sys.path.insert(0, r"D:\\Claude\\escort_mk2_dtm\\tools\\blender")
    import escort_scene; escort_scene.load_all(); print(escort_scene.roundtrip())
"""
import hashlib
import os

import bpy

PROJECT = r"D:\Claude\escort_mk2_dtm"
CAR = r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\ford_escort_mk2_tuned"
# the untouched 101Creative model as installed before the aero kit (the backup car holds the same files)
SOURCE = r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\ford_escort_mk2_tuned_backup_v20"
TEX = os.path.join(PROJECT, "blender", "kn5_textures")
EXPORT = os.path.join(PROJECT, "export")
FILES = {"A": "ford_escort_mk2_tuned.kn5", "B": "ford_escort_mk2_tuned_lod_b.kn5",
         "C": "ford_escort_mk2_tuned_lod_c.kn5", "D": "ford_escort_mk2_tuned_lod_d.kn5"}


def scene_of(tag):
    return bpy.data.scenes["Scene"] if tag == "A" else bpy.data.scenes.get(f"LOD_{tag}")


def clear_scene(sc):
    import json
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob)
    for col in list(sc.collection.children_recursive):
        bpy.data.collections.remove(col)
    for name in json.loads(sc.get("kn5_materials", "[]")):     # this scene's previous import
        m = bpy.data.materials.get(name)
        if m is not None:
            bpy.data.materials.remove(m)


def load_all():
    """(Re)import the source kn5s. Wipes the model scenes first - our parts are rebuilt by build_aero."""
    import kn5_import
    main = bpy.data.scenes["Scene"]
    out = {}
    try:
        for tag, fname in FILES.items():
            sc = scene_of(tag)
            if sc is None:
                sc = bpy.data.scenes.new(f"LOD_{tag}")
            clear_scene(sc)
            bpy.context.window.scene = sc
            tex = TEX if tag == "A" else os.path.join(TEX, f"lod_{tag.lower()}")
            out[tag] = kn5_import.import_kn5(os.path.join(SOURCE, fname), tex,
                                             "ESCORT" if tag == "A" else f"LOD_{tag}_MODEL")
            bpy.context.view_layer.update()
    finally:
        bpy.context.window.scene = main
    for me in [me for me in bpy.data.meshes if me.users == 0]:
        bpy.data.meshes.remove(me)
    bpy.ops.wm.save_mainfile()
    return {t: (s["tris"], s["materials"], s["textures"]) for t, s in out.items()}


def root_of(tag):
    return next(o for o in scene_of(tag).objects if o.get("kn5_root"))


def roundtrip():
    """Export every model unchanged and compare with the source files byte for byte."""
    import ac_kn5_export as ex
    h = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
    main = bpy.data.scenes["Scene"]
    res = {}
    try:
        for tag, fname in FILES.items():
            bpy.context.window.scene = scene_of(tag)
            out = os.path.join(EXPORT, f"roundtrip_{tag}.kn5")
            ex.export_kn5(out, [root_of(tag)])
            res[tag] = h(out) == h(os.path.join(SOURCE, fname))
            os.remove(out)
    finally:
        bpy.context.window.scene = main
    return res

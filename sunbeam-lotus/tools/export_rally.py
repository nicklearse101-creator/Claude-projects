"""Export the edited stock model (with rally parts) into the AC car folder. Runs in Blender on
sunbeam_rally_on_stock_model.blend. Writes <car>/sunbeam_rally.kn5; build_rally_on_stock.py
points lods.ini at it and adds the lamp lights."""
import importlib.util
import os

import bpy

OUT = r"D:\Claude\talbot_sunbeam_lotus\export\sunbeam_rally.kn5"   # build_rally_on_stock.py copies it into the car


def export():
    spec = importlib.util.spec_from_file_location("ac_kn5_export", r"D:\Claude\talbot_sunbeam_lotus\tools\ac_kn5_export.py")
    exp = importlib.util.module_from_spec(spec); spec.loader.exec_module(exp)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    root = next(o for o in bpy.data.objects if o.get("kn5_root"))
    st = exp.export_kn5(OUT, [root])
    bpy.ops.wm.save_mainfile()
    return st

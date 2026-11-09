"""Put the photo-measured rear bumper into the model: the red-striped bumper, the grey valance under it, the
number-plate lamp housing and the tail lamps.

The parts come from `tools/rear_end.py` (heights measured on anglia_rear and anglia_side through their solved
cameras, plan path from the shell's own rear sweep); this script only imports them, gives them materials and
takes the old blocky `Bumper_Rear_GTE` out. Like the front end, the JSON is in the photo frame, so every z gets
DZ to sit on the model's unloaded tyres.

The shell's own skin behind the bumper is left alone - the bumper stands proud of it and the shell's tail is
what the bumper wraps on to.

  python tools/rear_end.py ; python tools/tail_lamps.py ; python tools/rear_panel.py   (regenerate)
  blender -b blender/nova_proc.blend --python tools/gen/add_rear_end.py -- out.blend
"""
import json
import math
import os
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args and not args[0].startswith("--") else None
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = [os.path.join(ROOT, "blender", "data", f) for f in ("rear_end.json", "tail_lamps.json", "rear_panel.json")]
DZ = json.load(open(os.path.join(ROOT, "tools", "photomatch", "body_profile.json")))["dz"]
REPLACES = ("Bumper_Rear_GTE",)
MATS = {
    "plate_front": ((0.86, 0.86, 0.83, 1), 0.0, 0.35),
    "paint_gunmetal": ((0.62, 0.63, 0.64, 1), 0.0, 0.42),
    "trim_grey": ((0.17, 0.17, 0.18, 1), 0.0, 0.55),
    "trim_black": ((0.02, 0.02, 0.02, 1), 0.0, 0.60),
    "bumper_stripe": ((0.55, 0.03, 0.03, 1), 0.0, 0.40),
    "lamp_clear": ((0.85, 0.86, 0.88, 1), 0.0, 0.05),
    "lamp_amber": ((0.80, 0.35, 0.02, 1), 0.0, 0.10),
    "lamp_red": ((0.55, 0.02, 0.02, 1), 0.0, 0.10),
}


def material(name):
    rgba, met, rough = MATS.get(name, ((0.5, 0.5, 0.5, 1), 0.0, 0.5))
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = rgba
    b.inputs["Metallic"].default_value = met
    b.inputs["Roughness"].default_value = rough
    m.diffuse_color = rgba
    return m


def sharp_by_angle(me, deg):
    for name in ("set_sharp_from_angle", "set_sharpness_by_angle"):
        fn = getattr(me, name, None)
        if fn:
            fn(angle=math.radians(deg))
            return


coll = bpy.data.collections.get("NOVA_NEW") or bpy.context.scene.collection
for name in REPLACES:
    ob = bpy.data.objects.get(name)
    if ob is not None:
        print("replaced blocky part: %s (%d faces)" % (name, len(ob.data.polygons)))
        bpy.data.objects.remove(ob, do_unlink=True)

data = {}
for f in DATA:
    data.update({k: v for k, v in json.load(open(f)).items() if not k.startswith("_")})
total = 0
for name, p in data.items():
    old = bpy.data.objects.get(name)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x, y, z + DZ) for x, y, z in p["verts"]], [], p["faces"])
    for mname in p["mats"]:
        me.materials.append(material(mname))
    if "mat_idx" in p:
        me.polygons.foreach_set("material_index", p["mat_idx"])
    me.validate()
    me.update()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    sharp_by_angle(me, 40)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    zs = [v.co.z for v in me.vertices]; ys = [v.co.y for v in me.vertices]; xs = [v.co.x for v in me.vertices]
    print("%-18s %5d faces   x %+.3f..%+.3f  y %+.3f..%+.3f  z %.3f..%.3f"
          % (name, len(me.polygons), min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
    total += len(me.polygons)
print("rear end: %d parts, %d faces" % (len(data), total))

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)

"""Sort the blend into NEW (built from the drawings and measurements), OLD (blocky leftovers) and GUIDES, and
hide OLD and GUIDES - in the viewport and in every render - so what has actually been built can be seen.

Nik, 2026-10-26: it is hard to see what has been done with the old model's mess all round it.

Collection-level hiding wins over any object-level setting, so the render scripts (which switch objects on and
off by name) cannot bring the old parts back by accident. Nothing is deleted: OLD can be switched back on in the
outliner to compare.

blender -b blender/nova_proc.blend --python tools/gen/organise.py -- out.blend
"""
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args else None

# Door_Left, Rocker_Left and Roof_Panel are covered by the lofted Body_Shell (fit_shell.py), and Scuttle_Vent sat
# on the old low scuttle (rebuild_scuttle_drawn.py) - all four are OLD until rebuilt.
NEW = {"Body_Shell", "Hood_Panel", "Wing_Front_Left", "Skirt_Left", "Scuttle_Panel"}
NEW_PREFIX = ("BUMPER_F", "GRILLE_", "HEADLAMP_", "INDICATOR_", "LAMP_PANEL", "PLATE_F",   # front_end.py
               "BUMPER_R", "PLATE_LAMP_R", "TAILLAMP_", "PANEL_R", "PLATE_R", "SHUT_", "GLASS_",              # rear_end.py
               "MIRROR_", "WHEEL_", "TIRE_", "RIM_", "DISK_")                                             # add_mirrors / add_wheels
GUIDE_PREFIX = ("Arch_Profile", "Profile_Side", "Side_Profile_", "Wheel_Guide", "Chassis_Guide", "Axle_",
                "BLUEPRINT", "MATCH_", "CUT_", "GREY_CAM", "PIC_CAM", "ORTHO")


def coll(name, parent):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        parent.children.link(c)
    return c


root = bpy.context.scene.collection
c_new = coll("NOVA_NEW", root)
c_old = coll("NOVA_OLD", root)
c_guide = coll("NOVA_GUIDES", root)


def kind(o):
    if o.name in NEW or o.name.startswith(NEW_PREFIX):
        return c_new
    if o.name.startswith(GUIDE_PREFIX) or o.type != "MESH" or len(o.data.polygons) == 0:
        return c_guide
    return c_old


moved = {c_new.name: [], c_old.name: [], c_guide.name: []}
for o in list(bpy.data.objects):
    if o.type in ("CAMERA", "LIGHT"):
        continue
    target = kind(o)
    for c in list(o.users_collection):
        if c is not target:
            c.objects.unlink(o)
    if target not in o.users_collection:
        target.objects.link(o)
    moved[target.name].append(o.name)

for c in (c_old, c_guide):
    c.hide_viewport = True
    c.hide_render = True
c_new.hide_viewport = False
c_new.hide_render = False

# the old empty containers
for name in ("NOVA_PROC", "FRONT", "Collection"):
    c = bpy.data.collections.get(name)
    if c is not None and not c.objects and not c.children:
        bpy.data.collections.remove(c)

for k, v in moved.items():
    print("%-12s %2d  %s" % (k, len(v), ", ".join(sorted(v))))

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)

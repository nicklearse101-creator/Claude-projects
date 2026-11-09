"""Put the GTE wheels on the measured car: WHEEL_xx empties at the wheel centres, then blender/scripts/build_wheels.py.

The wheels themselves were measured and built on 2026-10-12/13 for the first route (nova_gte.blend) and are reused
unchanged: 5J x 14 three-arm alloy (face traced from anglia_side and the commons front photo, tools/wheel_face.py ->
blender/data/wheel_face.json), 175/65 R14 tyre, 236 mm vented front disc + caliper, 200 mm rear drum, AC naming
(WHEEL_xx -> TIRE_xx / RIM_xx / DISK_xx, see docs/EXPORT_NOTES.md). This only places them (2026-10-27 (15)):
  y  +-1.1715   the axles in the model frame (FIA wheelbase 2343 mm, origin midway)          SOURCED
  x  +-0.660 front, +-0.6535 rear: SPEC_SHEET tracks 1320 / 1307 mm (centre to centre)      SOURCED
  z  0.2916     unloaded 175/65 R14 radius (model ground is the unloaded tyre contact)        SOURCED (tyre size)
No steer, camber or toe; the empties carry identity rotation as AC expects.

blender -b in.blend --python tools/gen/add_wheels.py -- out.blend
"""
import importlib.util
import os
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args else None
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

WB_HALF = 2.343 / 2
TRACK_F, TRACK_R = 1.320, 1.307
R_TYRE = 0.0254 * 14 / 2 + 0.175 * 0.65            # 0.2916

POS = {"LF": (TRACK_F / 2, -WB_HALF), "RF": (-TRACK_F / 2, -WB_HALF),
       "LR": (TRACK_R / 2, WB_HALF), "RR": (-TRACK_R / 2, WB_HALF)}

if "WHEELS" not in bpy.data.collections:
    c = bpy.data.collections.new("WHEELS")
    bpy.context.scene.collection.children.link(c)
for tag, (x, y) in POS.items():
    name = "WHEEL_" + tag
    e = bpy.data.objects.get(name)
    if e is None:
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = "PLAIN_AXES"; e.empty_display_size = 0.08
        bpy.data.collections["WHEELS"].objects.link(e)
    e.parent = None
    e.location = (x, y, R_TYRE)
    e.rotation_euler = (0.0, 0.0, 0.0)
    e.scale = (1.0, 1.0, 1.0)

spec = importlib.util.spec_from_file_location("build_wheels", os.path.join(ROOT, "blender", "scripts", "build_wheels.py"))
bw = importlib.util.module_from_spec(spec); spec.loader.exec_module(bw)
stats = bw.build()
print("wheels: centres x +-%.4f / +-%.4f, y +-%.4f, z %.4f; rim faces per wheel %s"
      % (TRACK_F / 2, TRACK_R / 2, WB_HALF, R_TYRE, stats))

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)

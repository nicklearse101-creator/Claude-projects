"""Put the calibrated side-elevation blueprint into the blend as a viewport reference plane.

The drawing is `reference/blueprints/corsa_a_4view_blueprint.gif` (3-door side elevation), calibrated in
`reference/blueprints/side_calibration.json`: 5.3616 mm/px from the printed 2343 mm wheelbase over 437 px
between the two wheel centre-lines, ground line at py 266. The ground-to-roof check comes out at 1383 mm
against the printed 1365, the difference being the roof apex read picking up the rain gutter line.

It is an Empty of type IMAGE, so it shows in the viewport and never renders. Rotation (90, 0, 90) puts the
image's own X along the car's Y and its Y along Z; the offset is set so the image's lower-left corner lands
on the world point that pixel represents.

blender -b blender/nova_proc.blend --python tools/gen/add_blueprint.py -- out.blend [x_plane]
"""
import json
import math
import os
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args and not args[0].startswith("--") else None
XPLANE = float(args[1]) if len(args) > 1 else 0.0

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
cal = json.load(open(os.path.join(ROOT, "reference", "blueprints", "side_calibration.json")))
img_path = os.path.join(ROOT, "reference", "blueprints", "corsa_a_4view_blueprint.gif")

old = bpy.data.objects.get("BLUEPRINT_SIDE")
if old:
    bpy.data.objects.remove(old, do_unlink=True)

img = bpy.data.images.load(img_path, check_existing=True)
w_px, h_px = img.size
m_per_px = cal["mm_per_px"] / 1000.0

e = bpy.data.objects.new("BLUEPRINT_SIDE", None)
e.empty_display_type = "IMAGE"
e.data = img
e.empty_display_size = w_px * m_per_px          # image width in metres
e.empty_image_offset = (0.0, 0.0)               # origin at the image's lower-left corner
e.rotation_euler = (math.pi / 2, 0.0, math.pi / 2)
e.location = (XPLANE,
              cal["y_front_axle"] - cal["px_front_axle"] * m_per_px,     # model y of pixel column 0
              -(h_px - cal["px_ground"]) * m_per_px)                     # model z of the bottom pixel row
e.show_empty_image_perspective = True
e.show_empty_image_orthographic = True
e.use_empty_image_alpha = True
e.color[3] = 0.35
e.hide_select = True
bpy.context.scene.collection.objects.link(e)
print("BLUEPRINT_SIDE: %dx%d px, %.4f m/px, width %.3f m, at %s"
      % (w_px, h_px, m_per_px, e.empty_display_size, tuple(round(v, 4) for v in e.location)))

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)

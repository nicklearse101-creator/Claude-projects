"""Nik's grey reference pictures (reference/photos/grey_studio/{side,front,rear}.png) as see-through blueprint image
empties at true scale round the car, for matching the model to the pictures in Blender (Right view = side picture,
Front / Back views = front / rear pictures). Scale per picture from the car's overall length (side, 3622 mm) / width
incl. mirrors (front, rear, 1725 mm) in pixels; ground and centre lined up. Collection BLUEPRINTS (no_export).
Car frame: x+ = car's left, y- = front, z up."""
import os

import bpy
from mathutils import Matrix, Vector

REF = r"D:\Claude\vauxhall_nova_gte_1989\reference\photos\grey_studio"
# name: (file, image px w, h, car px extent, metres it spans, ground row, car centre column, axes (img right, img up,
#        facing), plane offset along facing)
PICS = {
    "side": ("side.png", 667, 258, 611 - 55, 3.622, 236, (55 + 611) / 2, ((0, 1, 0), (0, 0, 1), (1, 0, 0)), 1.0),
    "front": ("front.png", 329, 257, 301 - 27, 1.725, 235, (27 + 301) / 2, ((1, 0, 0), (0, 0, 1), (0, -1, 0)), 2.1),
    "rear": ("rear.png", 312, 260, 285 - 26, 1.725, 238, (26 + 285) / 2, ((-1, 0, 0), (0, 0, 1), (0, 1, 0)), 2.0),
}
CAR_Y_CENTRE = (-1.8415 + 1.7805) / 2


def build(opacity=0.5):
    coll = bpy.data.collections.get("BLUEPRINTS") or bpy.data.collections.new("BLUEPRINTS")
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    out = {}
    for name, (f, W, H, ext_px, ext_m, ground, cx, (r, u, n), off) in PICS.items():
        mpp = ext_m / ext_px
        img = bpy.data.images.load(os.path.join(REF, f), check_existing=True)
        o = bpy.data.objects.get("BP_" + name) or bpy.data.objects.new("BP_" + name, None)
        if o.name not in coll.objects:
            coll.objects.link(o)
        o.empty_display_type = "IMAGE"; o.data = img
        o.empty_display_size = W * mpp                      # image width in metres
        o.empty_image_offset = (-0.5, -0.5)
        o.empty_image_depth = "FRONT"
        o.use_empty_image_alpha = True; o.color[3] = opacity
        o.show_empty_image_only_axis_aligned = True
        o.show_empty_image_perspective = False
        o["no_export"] = 1; o.hide_render = True
        R = Matrix((r, u, n)).transposed()
        # image centre in car coordinates: horizontally the car centre column, vertically from the ground row
        dx = (W / 2 - cx) * mpp
        dz = (ground - H / 2) * mpp
        centre_along = Vector(r) * dx
        base = Vector((0.0, CAR_Y_CENTRE, 0.0)) if name == "side" else Vector((0.0, 0.0, 0.0))
        pos = base + centre_along + Vector((0, 0, dz)) + Vector(n) * off
        o.matrix_world = Matrix.Translation(pos) @ R.to_4x4()
        out[name] = {"mm_per_px": round(mpp * 1000, 2), "width_m": round(W * mpp, 3)}
    return out


if __name__ == "__main__":
    print("==", build())

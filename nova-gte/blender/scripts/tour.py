"""Close-up tour of the car for finish checks (runs inside Blender on export/ref/nova_ref_mat.blend): EEVEE renders
from 16 viewpoints round the body, neutral studio light turned to the viewed side, written to export/match/tour/ and
composed into two contact sheets (tour_sheet_1.jpg / _2.jpg). Car frame: x+ = car's left, y- = front, z up."""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = r"D:\Claude\vauxhall_nova_gte_1989"
OUT = os.path.join(ROOT, "export", "match", "tour")
sys.path.insert(0, os.path.join(ROOT, "blender", "scripts"))

VIEWS = [  # name, target, direction (target -> eye), distance
    ("01 indicator L", (0.70, -1.66, 0.60), (1, -0.45, 0.12), 0.6),
    ("02 indicator R", (-0.70, -1.66, 0.60), (-1, -0.45, 0.12), 0.6),
    ("03 front centre", (0.0, -1.78, 0.55), (0.2, -1, 0.15), 1.4),
    ("04 A-pillar L", (0.55, -0.45, 1.12), (1, -0.6, 0.5), 1.0),
    ("05 roof edge L", (0.60, 0.40, 1.22), (1, 0.1, 0.6), 1.5),
    ("06 door L", (0.74, -0.10, 0.80), (1, 0.0, 0.1), 2.0),
    ("07 quarter L", (0.68, 1.10, 1.00), (1, 0.4, 0.2), 1.1),
    ("08 rear corner L", (0.62, 1.70, 0.68), (0.9, 1, 0.15), 0.9),
    ("09 rear centre", (0.0, 1.74, 0.70), (0.25, 1, 0.15), 1.4),
    ("10 rear corner R", (-0.62, 1.70, 0.68), (-0.9, 1, 0.15), 0.9),
    ("11 quarter R", (-0.68, 1.10, 1.00), (-1, 0.4, 0.2), 1.1),
    ("12 door R", (-0.74, -0.10, 0.80), (-1, 0.0, 0.1), 2.0),
    ("13 A-pillar R", (-0.55, -0.45, 1.12), (-1, -0.6, 0.5), 1.0),
    ("14 sill L", (0.74, 0.30, 0.35), (1, 0.1, 0.05), 1.6),
    ("15 bonnet", (0.0, -1.20, 0.85), (0.25, -1, 0.9), 1.9),
    ("16 tailgate top", (0.0, 1.45, 1.22), (0.3, 1, 0.7), 1.3),
]


def main(names=None, res=(900, 560)):
    import lookdev
    lookdev.setup(hdri="studio.exr", strength=1.2)
    sc = bpy.context.scene
    nt = sc.world.node_tree
    env = next(n for n in nt.nodes if n.type == "TEX_ENVIRONMENT")
    mp = next((n for n in nt.nodes if n.type == "MAPPING"), None)
    if mp is None:
        tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
        nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
    for o in bpy.data.objects:
        if o.name.startswith(("COLLIDER", "CUT_", "MAP_", "MAPT_")):
            o.hide_render = True
    sm = bpy.data.collections.get("SHELL_MAP")
    if sm:
        sm.hide_render = True
    cam = bpy.data.objects.get("TOUR_CAM") or bpy.data.objects.new("TOUR_CAM", bpy.data.cameras.new("TOUR_CAM"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    cam["no_export"] = 1
    cam.data.lens = 50; cam.data.clip_start = 0.01
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    if hasattr(sc.eevee, "taa_render_samples"):
        sc.eevee.taa_render_samples = 24
    os.makedirs(OUT, exist_ok=True)
    out = []
    for name, tgt, d, dist in VIEWS:
        if names and name[:2] not in names:
            continue
        d = Vector(d).normalized()
        mp.inputs["Rotation"].default_value = (0, 0, 0 if d.x > 0 else math.pi)
        cam.location = Vector(tgt) + d * dist
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(OUT, name.replace(" ", "_") + ".png")
        bpy.ops.render.render(write_still=True)
        out.append(sc.render.filepath)
    return out


def sheets():
    """Contact sheets (run with the project venv: needs PIL)."""
    from PIL import Image, ImageDraw
    files = sorted(f for f in os.listdir(OUT) if f.endswith(".png") and f[:2].isdigit())
    for k in range(0, len(files), 8):
        ims = [Image.open(os.path.join(OUT, f)).convert("RGB") for f in files[k:k + 8]]
        w, h = ims[0].size
        S = Image.new("RGB", (w * 2, h * 4), "black"); d = ImageDraw.Draw(S)
        for i, (im, f) in enumerate(zip(ims, files[k:k + 8])):
            S.paste(im, ((i % 2) * w, (i // 2) * h)); d.text(((i % 2) * w + 8, (i // 2) * h + 6), f[:-4], fill=(255, 255, 0))
        S.save(os.path.join(ROOT, "export", "match", "tour_sheet_%d.jpg" % (k // 8 + 1)), quality=88)


if __name__ == "__main__":
    print("==", main())

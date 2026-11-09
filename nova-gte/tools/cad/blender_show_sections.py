"""Build the 'what we have' scene: line network coloured by fairness triage + the new v3 sections + the numpy body.

Run:  blender -b blender/nova_lines_v2.blend --python tools/cad/blender_show_sections.py
Never modifies nova_lines_v2.blend: saves blender/nova_sections_v3.blend (new) and renders to export/sections_v3_views/.
Colours - network: red = FAIL, amber = MARGINAL, blue = PASS, dim = artefact/fragment (docs/fairness_triage_2026-11-02.csv).
         section points: green = MEASURED, cyan = ENVELOPE (GA silhouette), orange = ESTIMATE, magenta = source conflict.
"""
import csv
import json
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = r"D:\Claude\vauxhall_nova_gte_1989"
OUT = os.path.join(ROOT, "export", "sections_v3_views")
os.makedirs(OUT, exist_ok=True)
S = json.load(open(os.path.join(ROOT, "blender", "data", "cad", "sections_v3.json")))
TRI = {r["curve"]: r["cls"] for r in csv.DictReader(open(os.path.join(ROOT, "docs", "fairness_triage_2026-11-02.csv")))}
COL = {"FAIL": (0.95, 0.2, 0.2, 1), "MARGINAL": (1.0, 0.72, 0.15, 1), "PASS": (0.45, 0.62, 0.92, 1),
       "ARTEFACT": (0.38, 0.4, 0.5, 1), "FRAGMENT": (0.38, 0.4, 0.5, 1)}
PCOL = {"MEASURED": (0.2, 0.9, 0.35, 1), "ENVELOPE": (0.2, 0.85, 1.0, 1), "ESTIMATE": (1.0, 0.55, 0.1, 1), "CONFLICT": (1.0, 0.2, 0.85, 1)}
scene = bpy.context.scene

# ---- network colours (objects are named L_<curve>, one object holds both halves) ------------------------------
n_col = {}
for c in bpy.data.collections:
    if not c.name.startswith("LINES_") or c.name == "LINES_model_parts":
        continue
    for o in c.objects:
        k = TRI.get(o.name[2:], "PASS")
        o.color = COL.get(k, COL["PASS"]); n_col[k] = n_col.get(k, 0) + 1
for cn in ("CAD_LINES_v1", "LINES_model_parts"):
    bpy.data.collections[cn].hide_render = True; bpy.data.collections[cn].hide_viewport = True
for o in bpy.data.collections["NOVA_NEW"].objects:
    o.color = (0.55, 0.57, 0.62, 1)
print("network colours:", n_col)

# ---- sections ---------------------------------------------------------------------------------------------------
ORDER = ["roof_centre", "crown_0.25", "crown_0.50", "crown_0.70", "crown_0.80", "crown_0.90", "crown_0.95", "crown_1.00",
         "glass_top_edge", "glass_top", "glass_base", "belt", "widest", "moulding_bot", "sill"]
col_s = bpy.data.collections.new("CAD_SECTIONS_V3"); scene.collection.children.link(col_s)
buckets = {k: bmesh.new() for k in PCOL}
for y, st in S["stations"].items():
    y = float(y); P = {p["id"]: p for p in st["points"]}
    seq = [P[i] for i in ORDER if i in P]
    cu = bpy.data.curves.new("SEC_y%+.2f" % y, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.003
    for sgn in (1, -1):
        sp = cu.splines.new("POLY"); sp.points.add(len(seq) - 1)
        for i, p in enumerate(seq):
            sp.points[i].co = (sgn * p["x"], y, p["z"], 1.0)
    ob = bpy.data.objects.new("SEC_y%+.2f" % y, cu); ob.color = (0.95, 0.95, 0.95, 1); col_s.objects.link(ob)
    for p in seq:
        if p["id"].startswith("crown_"):
            continue
        cls = "CONFLICT" if (p.get("x_minus_envelope_mm") or 0) > 16 else ("ESTIMATE" if p.get("x_cls") == "ESTIMATE" else p["cls"])
        for sgn in (1, -1):
            bmesh.ops.create_icosphere(buckets[cls], subdivisions=1, radius=0.014, matrix=Matrix.Translation((sgn * p["x"], y, p["z"])))
for k, bm in buckets.items():
    me = bpy.data.meshes.new("SECPTS_" + k); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("SECPTS_" + k, me); ob.color = PCOL[k]; col_s.objects.link(ob)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "blender", "nova_sections_v3.blend"))   # NEW file only
print("saved nova_sections_v3.blend with", len(S["stations"]), "sections")

# ---- render-only tweaks (not saved) -----------------------------------------------------------------------------
for o in bpy.data.objects:
    if o.type == "CURVE" and (o.name.startswith("L_") or o.name.startswith("SEC_")):
        o.data.bevel_depth = 0.0065 if o.name.startswith("SEC_") else 0.0055
scene.render.engine = "BLENDER_WORKBENCH"
sh = scene.display.shading; sh.light = "FLAT"; sh.color_type = "OBJECT"; sh.show_object_outline = False; sh.show_xray = False
if scene.world is None:
    scene.world = bpy.data.worlds.new("W")
scene.world.color = (0.075, 0.075, 0.085)
scene.render.resolution_x, scene.render.resolution_y, scene.render.image_settings.file_format = 1000, 620, "PNG"
scene.display.shading.background_type = "WORLD"
T = Vector((0, 0, 0.65))


def cam_at(name, ortho, d, scale=None, lens=50, dist=9.0, top=False):
    cd = bpy.data.cameras.new(name); cam = bpy.data.objects.new(name, cd); scene.collection.objects.link(cam)
    if ortho:
        cd.type, cd.ortho_scale = "ORTHO", scale
    else:
        cd.type, cd.lens = "PERSP", lens
    cd.clip_start, cd.clip_end = 0.1, 100
    d = Vector(d).normalized()
    if top:
        cam.location = (0, 0, 10); cam.rotation_euler = (0, 0, math.pi)
    else:
        cam.location = T + d * dist
        cam.rotation_euler = (T - cam.location).to_track_quat("-Z", "Y").to_euler()
    return cam


VIEWS = [("front", True, (0, -1, 0), 2.7), ("rear", True, (0, 1, 0), 2.7), ("left", True, (1, 0, 0), 4.3),
         ("right", True, (-1, 0, 0), 4.3), ("top", True, (0, 0, 1), 4.3), ("q_front_left", False, (0.8, -1, 0.45), None),
         ("q_rear_left", False, (0.8, 1, 0.45), None)]
body = bpy.data.collections["NOVA_NEW"]
for with_body in (False, True):
    body.hide_render = not with_body
    for name, ortho, d, sc in VIEWS:
        if with_body and name not in ("q_front_left", "left"):
            continue
        cam = cam_at("cam_" + name, ortho, d, scale=sc, dist=(6.2 if not ortho else 9.0), top=(name == "top"))
        scene.camera = cam
        scene.render.filepath = os.path.join(OUT, "%s%s.png" % (name, "_body" if with_body else ""))
        bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)
body.hide_render = False
# numbers for the report: body bbox vs sourced overall size, from the file (not from a picture)
mn, mx = [1e9] * 3, [-1e9] * 3
for o in body.objects:
    if o.type != "MESH" or o.name.startswith("MIR") or "MIRROR" in o.name.upper():
        continue
    for v in o.bound_box:
        w = o.matrix_world @ Vector(v)
        for i in range(3):
            mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
print("BODY bbox (no mirrors) min", [round(v, 4) for v in mn], "max", [round(v, 4) for v in mx])

# dedicated front-elevation view: sections + GA silhouettes only, large markers (the held-out check is in sections_v3.json)
for c in bpy.data.collections:
    if c.name.startswith("LINES_") and c.name != "LINES_envelope":
        c.hide_render = True
body.hide_render = True
for o in bpy.data.objects:
    if o.name.startswith("L_") and o.name[2:] in ("front_body_sil", "rear_body_sil", "front_roof_crown"):
        o.data.bevel_depth = 0.004; o.color = (0.6, 0.6, 0.65, 1)
scene.render.resolution_x, scene.render.resolution_y = 1000, 760
cam = cam_at("cam_sections_front", True, (0, -1, 0), scale=1.75, dist=9.0)
cam.location.z = 0.80; scene.camera = cam
scene.render.filepath = os.path.join(OUT, "sections_front.png"); bpy.ops.render.render(write_still=True)
print("rendered", scene.render.filepath)
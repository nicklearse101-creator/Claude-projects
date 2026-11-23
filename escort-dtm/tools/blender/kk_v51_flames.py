"""v51 on the v50 model (Nik 23 Nov): exhaust flames as meshes (CSP particle flames never draw on this car - even
ac.Particles.Flame from a car script, which demonstrably ran, showed nothing; the Supra's work, so it's car-specific).
Per side-exit tip: three flame lengths (KK_flame_L1..3 / R1..3), each 3 crossed planes along the exit direction,
own emissive alpha-blended material + generated flame texture. Hidden by default (exhaust_flames.lua shows them).
Run on "escort_v50 vfd.blend"; saves "escort_v51 flames.blend"."""
import json, math, os, sys
import bmesh, bpy, numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kk_build as kb

OUT = r"D:\Claude\escort_mk2_dtm\blender\escort_v51 flames.blend"
TEX = "KK_FLAME.png"
TIP = (0.952, 0.18, -0.03)                 # tip end (exhaust EXIT_X 0.948), blender coords (x = car left, +y = rear)
DIR = Vector((0.894, 0.447, 0.0))          # out of the side, ~27 deg rearward (AC dir 0.894,0,-0.447)
LENGTHS = (0.22, 0.34, 0.48)
main = bpy.data.scenes["Scene"]; bpy.context.window.scene = main

# ---- texture: v along the flame (0 = tip), u across; hot core near the pipe, tongue tapering out
W, H = 128, 256
u = (np.arange(W) + 0.5) / W; v = (np.arange(H) + 0.5) / H
U, V = np.meshgrid(u, v)
half = 0.48 * (1 - V) ** 0.7 * (0.55 + 0.45 * np.sin(np.pi * np.minimum(V * 2.2, 1)))   # tongue half-width
d = np.abs(U - 0.5) / np.maximum(half, 1e-3)
a = np.clip(1 - d, 0, 1) ** 1.2 * np.clip((1 - V) * 1.4, 0, 1)
core = np.clip(1 - d * 1.6, 0, 1) * np.clip(1 - V * 2.5, 0, 1)
r = np.clip(0.9 + 0.1 * core, 0, 1); g = np.clip(0.30 + 0.55 * core + 0.15 * (1 - V), 0, 1); b = np.clip(0.05 + 0.6 * core ** 2, 0, 1)
img = np.dstack([r, g, b, a]).astype(np.float32)
tex_dir = main["kn5_tex_dir"]
im = bpy.data.images.new("KK_FLAME", W, H, alpha=True)
im.pixels.foreach_set(img.ravel()); im.filepath_raw = os.path.join(tex_dir, TEX); im.file_format = "PNG"; im.save()
texs = json.loads(main["kn5_textures"])
if TEX not in [t["name"] for t in texs]:
    texs.append({"name": TEX, "active": 1}); main["kn5_textures"] = json.dumps(texs)

# ---- material: copy an alpha-blended ksPerPixel, emissive only
src = next(m for m in bpy.data.materials if m.get("kn5_def") and json.loads(m["kn5_def"]).get("name") == "digitalgauge")
mat = src.copy(); mat.name = "KK_flame"
dd = json.loads(src["kn5_def"]); dd["name"] = "KK_flame"; dd["blend"] = 1; dd["depth"] = 1     # depth 1 = no depth write
for p in dd["props"]:
    if p[0] in ("ksAmbient", "ksDiffuse", "ksSpecular"):
        p[1] = 0.0
    if p[0] == "ksEmissive":
        p[4:7] = [6.0, 6.0, 6.0]                # vec3 slot (name, float, vec2, vec3, vec4)
dd["samplers"] = [["txDiffuse", 0, TEX]]
mat["kn5_def"] = json.dumps(dd)
mats = json.loads(main["kn5_materials"])
if mat.name not in mats:
    mats.append(mat.name); main["kn5_materials"] = json.dumps(mats)

# ---- meshes
root = next(o for o in main.objects if o.get("kn5_root"))
col = bpy.data.collections["KADETT_KIT"]
for o in [o for o in main.objects if o.name.startswith("KK_flame_")]:
    bpy.data.objects.remove(o)
made = []
for side, tag in ((1, "L"), (-1, "R")):
    dirv = Vector((side * DIR.x, DIR.y, DIR.z)).normalized()
    tip = Vector((side * TIP[0], TIP[1], TIP[2]))
    a1 = Vector((0, 0, 1)); a2 = dirv.cross(a1).normalized()
    for k, L in enumerate(LENGTHS, 1):
        bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
        wid = 0.075 + 0.05 * k
        for ang in (0, 60, 120):
            ax = (a1 * math.cos(math.radians(ang)) + a2 * math.sin(math.radians(ang))).normalized()
            q = [tip - ax * wid / 2, tip + ax * wid / 2, tip + dirv * L + ax * wid / 2, tip + dirv * L - ax * wid / 2]
            vs = [bm.verts.new(p) for p in q]
            f = bm.faces.new(vs)
            for lp, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                lp[uvl].uv = uv
            f2 = bm.faces.new([bm.verts.new(p) for p in reversed(q)])   # back face, so it shows from both sides
            for lp, uv in zip(f2.loops, ((0, 1), (1, 1), (1, 0), (0, 0))):
                lp[uvl].uv = uv
        name = f"KK_flame_{tag}{k}"
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(name, me); kb.set_material(ob, mat)
        kb.link(ob, main, root, col)
        ob["kn5_flags"] = json.dumps({"active": 0, "cast": 0, "visible": 1, "transparent": 1, "renderable": 1})   # hidden unless the script shows it (CM showroom runs no scripts)
        made.append(name)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("REPORT", json.dumps({"made": made, "tex": os.path.join(tex_dir, TEX)}))

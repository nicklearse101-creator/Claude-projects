"""Character lines taken from the parts that were already built from measurements (2026-10-27 (20)).

The front end (front_end.py: bumper, lip, lamp panel, grille, headlamps, indicators, plate - all photo-measured),
the rear end (rear_end.py, rear_panel.py, tail_lamps.py: bumper, valance, tailgate panel with its glass opening,
lamps on the GA lamp heights), the sill skirts, bonnet, scuttle and wing. Their OUTLINES are measured lines the
character-line network did not have. They are read from the blend saved BEFORE roll_edges (export/tmp/r8.blend), so
an outline is the part's true edge, not the tucked-under return. Left half only (x >= -1 mm).

Also: the bonnet's two lengthwise creases (body_profile bonnet_creases: x = x0 + dxdy (y - y0)), sampled on the
bonnet's own surface.

blender -b export/tmp/r8.blend --python tools/cad/lines_from_parts.py -- blender/data/cad/lines_parts.json
"""
import json
import os
import sys
from collections import defaultdict

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0]
ROOT = r"D:\Claude\vauxhall_nova_gte_1989"
PF = json.load(open(os.path.join(ROOT, "tools", "photomatch", "body_profile.json")))

PARTS = {   # part: (group, source note)
    "BUMPER_F": ("front", "front_end.py (photo-measured swept section)"),
    "BUMPER_F_LIP": ("front", "front_end.py"),
    "LAMP_PANEL": ("front", "front_end.py"),
    "GRILLE_SURROUND": ("front", "front_end.py"),
    "HEADLAMP_GLASS_L": ("front", "front_end.py (BA HL_*)"),
    "INDICATOR_F_L": ("front", "front_end.py (BA IND_*)"),
    "PLATE_F": ("front", "front_end.py (plate 520 x 111)"),
    "Hood_Panel": ("bonnet", "rebuild_bonnet_drawn.py"),
    "Scuttle_Panel": ("bonnet", "rebuild_scuttle_drawn.py"),
    "Wing_Front_Left": ("body", "rebuild_wing_drawn.py"),
    "Skirt_Left": ("body", "rebuild_sill.py (skirt traced on cS)"),
    "PANEL_R_L": ("rear", "rear_panel.py (tailgate on the rear-face curve, BA TL_*/HG_*)"),
    "TAILLAMP_L": ("rear", "tail_lamps.py (GA heights 800/745/685/635)"),
    "BUMPER_R": ("rear", "rear_end.py"),
    "BUMPER_R_VALANCE": ("rear", "rear_end.py"),
}
MIN_LEN = 0.06          # ignore tiny loops (holes, slivers)


def loops(ob):
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me)
    M = ob.matrix_world
    be = [e for e in bm.edges if e.is_boundary]
    nb = defaultdict(list)
    for e in be:
        for v in e.verts:
            nb[v].append(e)
    seen, out = set(), []
    for e0 in be:
        if e0 in seen:
            continue
        chain = [e0.verts[0], e0.verts[1]]; seen.add(e0); cur, prev = e0.verts[1], e0
        while True:
            nxt = [e for e in nb[cur] if e is not prev and e not in seen]
            if not nxt:
                break
            prev = nxt[0]; seen.add(prev); cur = prev.other_vert(cur); chain.append(cur)
            if cur is chain[0]:
                break
        pts = [tuple(M @ v.co) for v in chain]
        L = sum((Vector(a) - Vector(b)).length for a, b in zip(pts[:-1], pts[1:]))
        if L >= MIN_LEN:
            out.append((pts, L, chain[-1] is chain[0]))
    bm.free()
    return out


def half(pts):
    """Keep the x >= 0 runs of a loop (parts with a Mirror modifier are already half; the others are whole)."""
    runs, cur = [], []
    for p in pts:
        if p[0] >= -0.001:
            cur.append(p)
        elif cur:
            runs.append(cur); cur = []
    if cur:
        runs.append(cur)
    return [r for r in runs if len(r) >= 3]


L = {}
for nm, (grp, src) in PARTS.items():
    ob = bpy.data.objects.get(nm)
    if ob is None or ob.type != "MESH":
        print("missing", nm); continue
    ls = sorted(loops(ob), key=lambda t: -t[1])
    k = 0
    for pts, length, closed in ls:
        for run in half(pts):
            k += 1
            L["%s_%d" % (nm.lower(), k)] = {"group": grp, "pts": [[round(c, 5) for c in p] for p in run],
                                           "src": src + " - outline %d (%.0f mm%s)" % (k, length * 1000,
                                                                                      ", closed" if closed else ""),
                                           "x_from": "part"}
    print("%-18s %d outline runs" % (nm, k))

# bonnet creases on the bonnet's surface
hood = bpy.data.objects["Hood_Panel"]
dg = bpy.context.evaluated_depsgraph_get()
me = hood.evaluated_get(dg).to_mesh(); M = hood.matrix_world
bvh = BVHTree.FromPolygons([tuple(M @ v.co) for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
hood.evaluated_get(dg).to_mesh_clear()
BC = PF["bonnet_creases"]
pts = []
for y in np.linspace(-1.66, -0.80, 60):
    x = BC["x0"] + BC["dxdy"] * (y - BC["y0"])
    h = bvh.ray_cast(Vector((x, y, 3.0)), Vector((0, 0, -1)), 5.0)
    if h[0]:
        pts.append([round(x, 5), round(y, 5), round(h[0].z, 5)])
L["bonnet_crease"] = {"group": "crease", "pts": pts, "src": "body_profile bonnet_creases (redgte_20) on the bonnet surface",
                      "x_from": "measured crease line"}
json.dump({"_doc": __doc__.split("\n\n")[0], "lines": L}, open(OUT, "w"), indent=1)
print("wrote %d lines to %s" % (len(L), OUT))

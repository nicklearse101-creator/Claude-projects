"""Geometric check: how far the model is from points measured on the real car.

tools/photomatch/ba_result.json holds 34 points triangulated on the car from several photographs at once - lamp,
indicator and tail-lamp corners, the door handle, the side repeater, the corners of every window, the screen and
the hatch glass. They are real positions on the real car, not values the model was built from, so the distance
from each to the model's surface is an honest measure of where the shape is wrong.

Signed: + means the real car is OUTSIDE the model there (the model is too small / too far in), - means the model
pokes out past the real car. Points on glass or lamps are measured against everything; the useful ones for the
body shell are the ones that sit on painted skin.

blender -b blender/nova_proc.blend --python tools/gen/geo_check.py -- [report.json]
"""
import json
import os
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args else None
ROOT = r"D:\Claude\vauxhall_nova_gte_1989"
PM = os.path.join(ROOT, "tools", "photomatch")
DZ = json.load(open(os.path.join(PM, "body_profile.json")))["dz"]
P = json.load(open(os.path.join(PM, "ba_result.json")))["points"]

HIDE = ("MESHY", "BLUEPRINT", "Chassis_Guide", "Wheel_Guide", "Profile_Side", "Side_Profile_Chassis",
        "Side_Profile_Hood", "Side_Profile_Tailgate", "Arch_Profile", "CUT_", "MATCH_", "Glass_")
# what each point sits on, so the right surface is judged
ON_SKIN = {"BON_F", "HANDLE_F", "HANDLE_R", "SR", "DSR_B", "PNL_B", "IND_OB", "IND_OT",
           "TL_BO", "TL_TO", "BON_F"}
ON_EDGE = {"DG_RB", "DG_RT", "QW_FB", "QW_FT", "QW_RB", "QW_RT", "WS_B", "WS_T", "HG_B", "HG_T"}

verts, tris, owner = [], [], []
edge_segs = []                                   # open (boundary) edges of the shell: window and screen apertures
for o in bpy.data.objects:
    if o.type != "MESH" or o.name.startswith(HIDE) or not len(o.data.polygons):
        continue
    if any(c.hide_render for c in o.users_collection):     # OLD and GUIDES are not part of the car
        continue
    dg = bpy.context.evaluated_depsgraph_get()
    me = o.evaluated_get(dg).to_mesh()
    m = o.matrix_world
    n0 = len(verts)
    verts += [tuple(m @ v.co) for v in me.vertices]
    for f in me.polygons:
        vs = list(f.vertices)
        for k in range(1, len(vs) - 1):
            tris.append((n0 + vs[0], n0 + vs[k], n0 + vs[k + 1]))
            owner.append(o.name)
    if o.name == "Body_Shell":
        import bmesh as _bm
        b = _bm.new(); b.from_mesh(me)
        for e in b.edges:
            if e.is_boundary:
                a_, c_ = m @ e.verts[0].co, m @ e.verts[1].co
                if abs(a_.x) > 1e-4 or abs(c_.x) > 1e-4:          # not the mirror seam
                    edge_segs.append((a_.copy(), c_.copy()))
        b.free()
    o.evaluated_get(dg).to_mesh_clear()
bvh = BVHTree.FromPolygons(verts, tris)

rows = []
for name, p in P.items():
    if not (isinstance(p, list) and len(p) == 3) or name.startswith("PL"):
        continue
    for sx in (1, -1):
        q = Vector((sx * p[0], p[1], p[2] + DZ))
        loc, nrm, idx, dist = bvh.find_nearest(q)
        if loc is None:
            continue
        signed = (q - loc).dot(nrm)
        # the normal of a mirrored half can point inwards; orient it away from the car's centre
        if nrm.x * loc.x < 0:
            signed = -signed
        if name in ON_EDGE and edge_segs:
            # a glass corner sits ON an aperture edge: what matters is how far the edge is, not the surface
            best = 1e9
            for a_, c_ in edge_segs:
                ab = c_ - a_; t = max(0.0, min(1.0, (q - a_).dot(ab) / max(ab.dot(ab), 1e-12)))
                best = min(best, (a_ + ab * t - q).length)
            dist, signed = best, best
        rows.append({"pt": name + ("" if sx > 0 else "_R"), "dist_mm": round(dist * 1000, 1),
                     "signed_mm": round(signed * 1000, 1), "on": owner[idx],
                     "kind": "skin" if name in ON_SKIN else "edge" if name in ON_EDGE else "part"})

rows.sort(key=lambda r: -r["dist_mm"])
print("%-11s %8s %9s  %-5s %s" % ("point", "dist mm", "signed", "kind", "nearest object"))
for r in rows:
    if r["pt"].endswith("_R"):
        continue
    print("%-11s %8.1f %+9.1f  %-5s %s" % (r["pt"], r["dist_mm"], r["signed_mm"], r["kind"], r["on"]))
left = [r for r in rows if not r["pt"].endswith("_R")]
for kind in ("skin", "edge", "part"):
    d = [r["dist_mm"] for r in left if r["kind"] == kind]
    if d:
        print("%-5s points: %2d, mean %.1f mm, worst %.1f mm" % (kind, len(d), sum(d) / len(d), max(d)))
asym = [abs(a["dist_mm"] - b["dist_mm"]) for a in left for b in rows
        if b["pt"] == a["pt"] + "_R"]
print("left/right asymmetry: worst %.1f mm" % (max(asym) if asym else 0.0))
if OUT:
    json.dump(rows, open(OUT, "w"), indent=1)
    print("wrote", OUT)

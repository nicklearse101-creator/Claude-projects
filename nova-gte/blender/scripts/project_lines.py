"""Project model feature lines into the reference photos through the photo-matched cameras (checking positions).
Writes export/match/proj_<cam>.json: {object: [[(px, py), ...] boundary loops]} for the glass panes and seals.
Run inside Blender: blender -b export/ref/nova_ref_mat.blend --python blender/scripts/project_lines.py"""
import json
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_matched as rm   # noqa: E402

OUT = r"D:\Claude\vauxhall_nova_gte_1989\export\match"
OBJS = ["GLASS_WINDSCREEN", "GLASS_DOOR_L", "GLASS_DOOR_R", "GLASS_VENT_L", "GLASS_VENT_R", "GLASS_QUARTER_L",
        "GLASS_QUARTER_R", "GLASS_TAILGATE", "DET_SUNROOF"]


def loops(o):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world)
    be = [e for e in bm.edges if e.is_boundary]
    adj = {}
    for e in be:
        a, b = e.verts
        adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    seen, out = set(), []
    for v0 in list(adj):
        if v0 in seen:
            continue
        loop, prev, cur = [v0], None, v0
        seen.add(v0)
        while True:
            nxt = [v for v in adj[cur] if v is not prev and v not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            seen.add(cur); loop.append(cur)
        out.append([v.co.copy() for v in loop])
    bm.free()
    return out


def project(cam, p):
    q = cam["rot"].transposed() @ (Vector(p) - Vector(cam["loc"]))
    if q.z >= 0:
        return None
    return (cam["W"] / 2 + cam["f"] * q.x / -q.z, cam["H"] / 2 - cam["f"] * q.y / -q.z)


def main(cams=("c20", "cS", "cCF", "c22", "cAR")):
    C = rm.cameras()
    for cn in cams:
        cam = C[cn]
        res = {}
        for n in OBJS:
            o = bpy.data.objects.get(n)
            if o is None:
                continue
            res[n] = [[project(cam, p) for p in lp if project(cam, p)] for lp in loops(o)]
        json.dump({"W": cam["W"], "H": cam["H"], "lines": res}, open(os.path.join(OUT, "proj_%s.json" % cn), "w"))
    return list(cams)


if __name__ == "__main__":
    print("==", main())

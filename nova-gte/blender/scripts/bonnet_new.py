"""New bonnet built from scratch (Nik 2026-10-19: replace parts with new clean geometry; dents in the old bonnet).
Surface and outline from tools/bonnet_fit.py (export/ref/bonnet_fit.json): centre panel and two outer panels meeting at
straight creases, edges 2.5 mm inside the shut-line grooves, a 14 mm turned-down flange all round. The old bonnet
skin is removed from REF_BODY. The panel hangs under the empty BONNET_HINGE on its rear (windscreen) edge so it can
open (opening animation: later step). Car frame: x+ = car's left, y- = front, z up."""
import json
import os

import bmesh
import numpy as np

import bpy
from mathutils import Vector

FIT = r"D:\Claude\vauxhall_nova_gte_1989\export\ref\bonnet_fit.json"
GAP, FLANGE = 0.0025, 0.014
NOSE_Z, NOSE_REACH, NOSE_ROWS = 0.682, 0.024, 10      # nose curls down to the grille/lamp tops (z 0.674); forward = 0.78 x drop   # front edge curls down over grille/lamps (scan: ~48 mm fwd, ~62 mm down)
NC_OUT, NC_MID, NROW = 14, 70, 90


class Bonnet:
    def __init__(self):
        J = json.load(open(FIT))
        self.J = J
        self.cf, self.cr, self.cs = np.array(J["front_x2"]), np.array(J["rear"]), np.array(J["side"])
        self.cc, self.co = np.array(J["centre"]), np.array(J["outer"])
        self.y0, self.ys = J["Yn"]

    def xc(self, y):
        return self.J["crease"][0] + self.J["crease"][1] * (y + 1.64)

    def yf(self, x):
        return np.polyval(self.cf, x * x) + GAP          # even in x: no kink at the centre

    def yr(self, x):
        return np.polyval(self.cr, x * x) - GAP

    def xside(self, y):
        return np.polyval(self.cs, y) - GAP

    def z(self, x, y):
        Y = (y + self.y0) / self.ys
        zc = sum(c * (x * x) ** i * Y ** j for c, (i, j) in zip(self.cc, [(i, j) for i in range(4) for j in range(7)]))
        u = abs(x) - self.xc(y)
        zo = sum(c * u ** i * Y ** j for c, (i, j) in zip(self.co, [(i, j) for i in range(3) for j in range(6)]))
        return float(max(zc, zo) if abs(u) < 0.03 else (zc if u < 0 else zo))

    def column_x(self, s, y):
        """Column parameter s in [-1, 1] -> x, with columns exactly on the creases."""
        xs, xc = self.xside(y), self.xc(y)
        c = NC_MID / (NC_MID + 2 * NC_OUT)
        a = abs(s)
        x = xc * a / c if a <= c else xc + (xs - xc) * (a - c) / (1 - c)
        return float(np.sign(s) * x)


def build():
    B = Bonnet()
    bm = bmesh.new()
    ncol = NC_MID + 2 * NC_OUT
    S = np.linspace(-1, 1, ncol + 1)
    T = np.linspace(0, 1, NROW + 1)
    grid = []
    for t in T:
        row = []
        for s in S:
            # y between front and rear edge at this column's x (iterate: x depends on y via the side line)
            y = -1.6 + 0.0 * t
            for _ in range(4):
                x = B.column_x(s, y)
                y = B.yf(x) + (B.yr(x) - B.yf(x)) * t
            x = B.column_x(s, y)
            row.append(bm.verts.new((x, y, B.z(x, y))))
        grid.append(row)
    nose = []
    for a in np.linspace(np.pi / 2, 0, NOSE_ROWS + 1)[:-1]:
        nose.append([bm.verts.new((v.co.x, v.co.y - NOSE_REACH * np.sin(a),
                                   v.co.z - (v.co.z - NOSE_Z) * (1 - np.cos(a)))) for v in grid[0]])
    grid = nose + grid
    NR = len(grid) - 1
    top = []
    for i in range(NR):
        for j in range(ncol):
            f = bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
            f.smooth = True; top.append(f)
    # flange: boundary loop dropped 14 mm
    ring = [grid[0][j] for j in range(ncol + 1)] + [grid[i][ncol] for i in range(1, NR + 1)] + \
           [grid[NR][j] for j in range(ncol - 1, -1, -1)] + [grid[i][0] for i in range(NR - 1, 0, -1)]
    low = [bm.verts.new(v.co - Vector((0, 0, FLANGE))) for v in ring]
    n = len(ring)
    for k in range(n):
        f = bm.faces.new((ring[k], ring[(k + 1) % n], low[(k + 1) % n], low[k])); f.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if sum(f.normal.z for f in top) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    for o in ("DET_BONNET", "BONNET_HINGE"):
        if bpy.data.objects.get(o):
            bpy.data.objects.remove(bpy.data.objects[o])
    me = bpy.data.meshes.new("DET_BONNET"); bm.to_mesh(me); bm.free()
    me.materials.append(bpy.data.materials["paint_gunmetal"])
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new("DET_BONNET", me)
    coll = bpy.data.collections["REF"]; coll.objects.link(ob)
    # hinge on the rear edge, centre
    yh = float(B.yr(0.0)); zh = B.z(0.0, yh - 0.005) - 0.01
    hinge = bpy.data.objects.new("BONNET_HINGE", None); coll.objects.link(hinge)
    hinge.location = (0.0, yh, zh); hinge.empty_display_size = 0.1
    me.transform(__import__("mathutils").Matrix.Translation((0.0, -yh, -zh)))   # mesh in hinge space
    ob.parent = hinge
    return B, len(me.polygons)


def remove_old(B):
    o = bpy.data.objects["REF_BODY"]; me = o.data
    n = len(me.polygons)
    C = np.empty(n * 3); me.polygons.foreach_get("center", C); C = C.reshape(-1, 3)
    x, y, z = C.T
    cand = np.where((np.abs(x) < 0.66) & (y > -1.78) & (y < -0.84) & (z > 0.58))[0]
    dead = []
    for i in cand:
        xi, yi, zi = x[i], y[i], z[i]
        if abs(xi) > B.xside(yi) + 0.004 or yi > B.yr(xi) + 0.004:
            continue
        yf = B.yf(xi)
        if yi >= yf - 0.004:
            if zi > B.z(xi, max(yi, yf)) - 0.03:
                dead.append(i)
        else:
            zf = B.z(xi, yf); dz = zf - NOSE_Z; dy = NOSE_REACH
            if yi < yf - dy - 0.004:
                continue
            a = np.arcsin(np.clip((yf - yi) / dy, 0, 1))
            if zi > zf - dz * (1 - np.cos(a)) - 0.012:
                dead.append(i)
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[int(i)] for i in dead], context="FACES")
    bm.to_mesh(me); bm.free(); me.update()
    return len(dead)


def main():
    B, nf = build()
    return {"faces": nf, "old_removed": remove_old(B)}


if __name__ == "__main__":
    print("==", main())

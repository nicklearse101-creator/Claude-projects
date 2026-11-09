"""Trace lines on the world-frame drawing views by snapping rough guide points onto the drawing's ink.

Guides are read off grid_view.py crops (world coordinates, +-10 mm is enough) and kept in tools/cad/trace_spec.json,
so every trace can be re-run and corrected. For each guide polyline the script resamples it every STEP px, and at
each sample searches along the polyline's normal, +-R px, for the darkest pixel of a lightly blurred copy of the
view; it is accepted only if it is clearly ink (darker than INK) - otherwise the sample is dropped rather than
invented. Output in the view's own 2D world axes (frame.json), plus the snap distance per point.

python tools/cad/trace_view.py [spec.json] [out.json] [overlay_dir]
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V = os.path.join(ROOT, "reference", "views")
F = json.load(open(os.path.join(V, "frame.json")))["views"]
SPEC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "tools", "cad", "trace_spec.json")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "blender", "data", "cad", "traces_views.json")
OVD = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, "export", "cad", "traces")
os.makedirs(OVD, exist_ok=True)
STEP, R, INK = 3.0, 7, 120


class View:
    def __init__(self, name):
        v = F[name]; self.v = v; self.ppm = v["ppm"]; self.r = v["rect"]
        self.plan = "DOWN" in v["axes"]; self.flipu = v["axes"].startswith("u = -x")
        im = Image.open(os.path.join(V, v["file"])).convert("L")
        self.im = im; self.A = np.asarray(im.filter(ImageFilter.GaussianBlur(1.0)), float)

    def px(self, u, w):
        r0, r1, c0, c1 = self.r
        i = (r1 - u) * self.ppm if self.flipu else (u - r0) * self.ppm
        j = (w - c0) * self.ppm if self.plan else (c1 - w) * self.ppm
        return np.array([i, j])

    def world(self, p):
        r0, r1, c0, c1 = self.r
        i, j = p
        u = r1 - i / self.ppm if self.flipu else r0 + i / self.ppm
        w = c0 + j / self.ppm if self.plan else c1 - j / self.ppm
        return u, w


JUMP = 12.0     # cost per px of sideways step between neighbouring samples (continuity)


def trace(view, guides):
    """Snap the guide onto the ink by dynamic programming over the sideways offset k of every sample: cost = ink
    darkness + a preference for the nearest line + JUMP x |k_i - k_(i-1)|. v1 chose each sample on its own, so where
    two drawn lines run a few px apart (spoiler, C-pillar, tail, screen rubber) it hopped between them and the
    fitted curves inherited the zigzag (fairness_v2: tail_centre, rear_lamp, front_screen_header). Samples whose
    chosen pixel is not ink are dropped, not invented."""
    G = np.array([view.px(*g) for g in guides], float)
    S, Nn = [], []
    for a, b in zip(G[:-1], G[1:]):
        L = np.linalg.norm(b - a); n = max(2, int(L / STEP))
        t = (b - a) / max(L, 1e-9); nrm = np.array([-t[1], t[0]])
        for s in np.linspace(0, 1, n, endpoint=False):
            S.append(a + s * (b - a)); Nn.append(nrm)
    S.append(G[-1]); Nn.append(Nn[-1])
    K = np.arange(-R, R + 1)
    H, W = view.A.shape
    cost = np.full((len(S), len(K)), 1e4); val = np.full((len(S), len(K)), 255.0)
    for i, (p, nrm) in enumerate(zip(S, Nn)):
        for c, k in enumerate(K):
            q = p + k * nrm; x, y = int(round(q[0])), int(round(q[1]))
            if 0 <= y < H and 0 <= x < W:
                val[i, c] = view.A[y, x]; cost[i, c] = view.A[y, x] + 0.6 * abs(k)
    acc = cost[0].copy(); back = np.zeros((len(S), len(K)), int)
    trans = JUMP * np.abs(K[:, None] - K[None, :])          # [prev, cur]
    for i in range(1, len(S)):
        tot = acc[:, None] + trans
        back[i] = np.argmin(tot, 0); acc = tot[back[i], np.arange(len(K))] + cost[i]
    path = [int(np.argmin(acc))]
    for i in range(len(S) - 1, 0, -1):
        path.append(back[i][path[-1]])
    path = path[::-1]
    out = []
    for i, c in enumerate(path):
        if val[i, c] < INK:
            out.append((S[i] + K[c] * Nn[i], abs(int(K[c]))))
    return out


spec = json.load(open(SPEC))
res, views = {}, {}
for name, s in spec["lines"].items():
    vn = s["view"]
    view = views.get(vn) or views.setdefault(vn, View(vn))
    pts = trace(view, s["guides"])
    w = [view.world(p) for p, _ in pts]
    snap = [k for _, k in pts]
    res[name] = {"view": vn, "axes": view.v["axes"], "pts": [[round(a, 5), round(b, 5)] for a, b in w],
                 "kept": len(pts), "snap_px_mean": round(float(np.mean(snap)), 2) if snap else None,
                 "note": s.get("note", "")}
    print("%-22s %-8s %4d pts kept, mean snap %.1f px (%.1f mm)" % (name, vn, len(pts), np.mean(snap) if snap else -1,
                                                                    (np.mean(snap) if snap else 0) * 2))
json.dump({"_doc": __doc__.split("\n\n")[0], "spec": os.path.basename(SPEC), "lines": res}, open(OUT, "w"), indent=1)
# overlays: traced points in red, guides in blue, one image per view
for vn, view in views.items():
    im = view.im.convert("RGB"); d = ImageDraw.Draw(im)
    for name, s in spec["lines"].items():
        if s["view"] != vn:
            continue
        g = [tuple(view.px(*q)) for q in s["guides"]]
        d.line(g, fill=(0, 120, 255), width=1)
        for u, w in res[name]["pts"]:
            i, j = view.px(u, w); d.point((i, j), fill=(255, 0, 0))
            d.ellipse([i - 1, j - 1, i + 1, j + 1], fill=(255, 0, 0))
    im.save(os.path.join(OVD, "trace_%s.png" % vn))
print("wrote", OUT, "and overlays in", OVD)

"""CAD car build, step 2 (run with FreeCAD's freecadcmd): curves -> CAD surfaces -> mesh.

    freecadcmd cad_build_freecad.py   (reads CAD_IN / CAD_OUT env vars)

Body: one loft through the body sections (sill -> roof centre), wheel arches cut with cylinders.
Nose / tail: lofts through the horizontal slices of the end panels.
All in millimetres (OpenCASCADE tolerances), AC frame, left half. Writes a STEP file and a fine
triangle mesh (npz, metres) for Blender and scoring.
"""
import os, sys, time
import numpy as np
import FreeCAD as App, Part, MeshPart

IN = os.environ['CAD_IN']; OUT = os.environ['CAD_OUT']
d = np.load(IN)
V = lambda p: App.Vector(*(float(x) * 1000 for x in p))
t0 = time.time()


def curve(pts):
    c = Part.BSplineCurve(); c.interpolate([V(p) for p in pts]); return c


NPTS = int(os.environ.get('CAD_NPTS', 60))


def resample(P, n):
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    t = np.linspace(0, s[-1], n)
    return np.c_[[np.interp(t, s, P[:, k]) for k in range(3)]].T


def loft(keys, solid=False):
    """one B-spline surface interpolating a grid: every curve resampled to NPTS points by arc length
    (light curves, like a modeller's few control points) -> fast and smooth along both directions"""
    G = [resample(np.asarray(d[k], float), NPTS) for k in keys]
    s = Part.BSplineSurface()
    s.interpolate([[V(p) for p in row] for row in G])
    return s.toShape()


shapes = {}
sec = sorted([k for k in d.files if k.startswith('sec_')], key=lambda k: int(k.split('_')[1]))
if 'body_grid' in d.files:      # feature-aligned rows (cad_feature_grid.py)
    _s = Part.BSplineSurface(); _s.interpolate([[V(p) for p in row] for row in d['body_grid']]); body = _s.toShape()
else:
    body = loft(sec)
print('body surface', round(time.time() - t0, 1), 's', flush=True)
# wheel arches: cylinders across the car (axis along x)
cut = body
for zc, yc, r in d['arches']:
    cyl = Part.makeCylinder(float(r) * 1000, 2000, App.Vector(-200, float(yc) * 1000, float(zc) * 1000), App.Vector(1, 0, 0))
    cut = cut.cut(cyl)
shapes['body'] = cut
print('arches cut', round(time.time() - t0, 1), 's', flush=True)
for end in ('nose', 'tail'):
    ks = sorted([k for k in d.files if k.startswith(end + '_')], key=lambda k: int(k.split('_')[1]))
    if len(ks) >= 2 and os.environ.get('CAD_ENDS', '0') == '1':
        shapes[end] = loft(ks)
        print(end, 'loft ok', round(time.time() - t0, 1), 's')
comp = Part.makeCompound(list(shapes.values()))
comp.exportStep(OUT + '.step')
tri = {}
def quad_grid(face, nu, nv):
    """sample an (untrimmed) surface into a quad grid: our own clean quad mesh"""
    srf = face.Surface; u0, u1, v0, v1 = srf.bounds()
    P = np.array([[tuple(srf.value(u0 + (u1 - u0) * i / (nu - 1), v0 + (v1 - v0) * j / (nv - 1))) for j in range(nv)] for i in range(nu)]) / 1000.0
    idx = np.arange(nu * nv).reshape(nu, nv)
    F = np.c_[idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()]
    return P.reshape(-1, 3), F


for k, s in shapes.items():
    if k == 'body':     # trimmed by the arch cuts -> CAD tessellation
        m = MeshPart.meshFromShape(Shape=s, LinearDeflection=float(os.environ.get("CAD_DEFL", 1.5)), AngularDeflection=0.2, Relative=False)
        pts, faces = m.Topology
        tri[k + '_P'] = np.array([[p.x, p.y, p.z] for p in pts]) / 1000.0
        tri[k + '_F'] = np.array(faces, int)
    else:
        P, F = quad_grid(s.Faces[0], 120, 120)
        tri[k + '_P'] = P; tri[k + '_F'] = F
    print(k, 'mesh', len(tri[k + '_F']), 'faces', round(time.time() - t0, 1), 's', flush=True)
np.savez(OUT + '.npz', **tri)
print('done', round(time.time() - t0, 1), 's')

"""Sew a build's faces into one shell and report what stays open (research: Bonnet surfacing.md step 13).

    PF_IN=<build dir> SEW_TOL=0.05 ./fcrun.sh sew_build.py

Reads <build>/panels_fit.step (every built face), sews it (BRepBuilderAPI_Sewing via Shape.sewShape), then lists the
free boundary as closed loops: their length, size and centre. On a finished panel the only free loops are its real
open edges (bonnet: the bottom of the returns / flange / lip); everything else is a hole between faces. Holes up to
SEW_FILL mm across are closed with a Coons patch on the loop (G0) and the shell is sewn again.
Writes <build>/sewn.step, <build>/sewn.brep and <build>/sew_report.json.
"""
import os, json, time
import numpy as np
import FreeCAD as App, Part

IN = os.environ['PF_IN']; TOL = float(os.environ.get('SEW_TOL', 0.05)); FILL = float(os.environ.get('SEW_FILL', 6.0))
t0 = time.time()
sh = Part.Shape(); sh.read(os.path.join(IN, 'panels_fit.step'))
faces = sh.Faces
print(f'{len(faces)} faces read, area {sum(f.Area for f in faces) / 1e6:.4f} m2', flush=True)


def sew(fs, tol):
    s = Part.Shell(fs) if False else Part.makeCompound(fs)
    s = s.copy(); s.sewShape(tol)
    return s


def free_loops(s):
    """free edges (used by one face only) grouped into connected loops"""
    cnt = {}
    for f in s.Faces:
        for e in f.Edges: cnt[e.hashCode()] = cnt.get(e.hashCode(), 0) + 1
    fe = []; seen = set()
    for f in s.Faces:
        for e in f.Edges:
            h = e.hashCode()
            if cnt[h] == 1 and h not in seen: fe.append(e); seen.add(h)
    groups = Part.__sortEdges__(fe) if False else None
    # connected components by shared vertices (within TOL)
    ends = [(np.array(e.Vertexes[0].Point), np.array(e.Vertexes[-1].Point)) for e in fe]
    par = list(range(len(fe)))
    def f_(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    P = np.array([p for ab in ends for p in ab]).reshape(-1, 3)
    for i in range(len(P)):
        d = np.linalg.norm(P - P[i], axis=1); j = np.where(d < max(TOL * 2, 0.02))[0]
        for k in j: a, b = f_(i // 2), f_(k // 2); par[a] = b
    comp = {}
    for i in range(len(fe)): comp.setdefault(f_(i), []).append(fe[i])
    out = []
    for es in comp.values():
        X = np.array([[v.x, v.y, v.z] for e in es for v in e.discretize(8)])
        L = sum(e.Length for e in es)
        ext = np.ptp(X, axis=0)
        out.append(dict(edges=es, length=L, size=float(np.linalg.norm(ext)), centre=X.mean(0).tolist(), n=len(es)))
    out.sort(key=lambda d: -d['length'])
    return out


def coons_loop(es, n=12):
    """Coons patch on a small closed loop of edges: the loop sampled densely, split into 4 by arc length"""
    W = Part.Wire(Part.__sortEdges__(es)) if True else None
    X = np.array([[v.x, v.y, v.z] for v in W.discretize(Distance=0.1)])
    if np.linalg.norm(X[0] - X[-1]) < 1e-6: X = X[:-1]
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.r_[X, X[:1]], axis=0), axis=1))]; L = d[-1]
    def side(a, b):
        t = np.linspace(a, b, n); return np.c_[[np.interp(t, d, np.r_[X, X[:1]][:, c]) for c in range(3)]].T
    S0, S1, S2, S3 = side(0, L / 4), side(L / 4, L / 2), side(L / 2, 3 * L / 4)[::-1], side(3 * L / 4, L)[::-1]
    u = np.linspace(0, 1, n); G = np.zeros((n, n, 3))
    for i, uu in enumerate(u):
        for j, vv in enumerate(u):
            G[i, j] = ((1 - vv) * S0[i] + vv * S2[i] + (1 - uu) * S3[j] + uu * S1[j]
                       - ((1 - uu) * (1 - vv) * S0[0] + uu * (1 - vv) * S0[-1] + (1 - uu) * vv * S2[0] + uu * vv * S2[-1]))
    srf = Part.BSplineSurface(); srf.interpolate([[App.Vector(*q) for q in row] for row in G])
    return srf.toShape()


s = sew(faces, TOL)
loops = free_loops(s)
print(f'sewn at {TOL} mm: {len(s.Shells)} shell(s), {len(s.Faces)} faces; {len(loops)} free loop(s)', flush=True)
for k, l in enumerate(loops[:30]):
    print(f'  loop {k:2d}: {l["n"]:3d} edges, length {l["length"]:8.1f} mm, size {l["size"]:7.1f} mm, centre ({", ".join(f"{c:.0f}" for c in l["centre"])})', flush=True)
fills = []
holes = [l for l in loops if l['size'] <= FILL]
for k, l in enumerate(holes):
    try:
        fills.append(coons_loop(l['edges']))
    except Exception as ex:
        print('  fill failed on a hole at', [round(c) for c in l['centre']], ex, flush=True)
if fills:
    s = sew(list(s.Faces) + fills, TOL)
    loops2 = free_loops(s)
    print(f'after {len(fills)} hole fills: {len(s.Shells)} shell(s), {len(loops2)} free loop(s)', flush=True)
    for k, l in enumerate(loops2[:12]):
        print(f'  loop {k:2d}: {l["n"]:3d} edges, length {l["length"]:8.1f} mm, size {l["size"]:7.1f} mm, centre ({", ".join(f"{c:.0f}" for c in l["centre"])})', flush=True)
    loops = loops2
s.exportStep(os.path.join(IN, 'sewn.step')); s.exportBrep(os.path.join(IN, 'sewn.brep'))
fm = {}
import MeshPart
for k, f in enumerate(fills):
    m = MeshPart.meshFromShape(Shape=f, LinearDeflection=0.01, AngularDeflection=0.1, Relative=False); p_, t_ = m.Topology
    fm[f'sewfill:{k}_P'] = np.array([[q.x, q.y, q.z] for q in p_]) / 1000.0; fm[f'sewfill:{k}_F'] = np.array(t_, int)
np.savez(os.path.join(IN, 'sew_fills_mesh.npz'), **fm)
json.dump(dict(tol=TOL, shells=len(s.Shells), faces=len(s.Faces), fills=len(fills),
               loops=[dict(length=l['length'], size=l['size'], centre=l['centre'], n=l['n']) for l in loops]),
          open(os.path.join(IN, 'sew_report.json'), 'w'), indent=1)
print('done', round(time.time() - t0, 1), 's', flush=True)

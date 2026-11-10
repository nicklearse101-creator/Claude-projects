"""FreeCAD ReverseEngineering.approxSurface on one point set (run with fcrun.sh; env RE_IN = .npz with P (n,3) mm,
NU, NV). Not a height field: it corrects each point's parameters, so it follows faces that wrap (a wing's lower
rear corner rounding under). Writes RE_IN + '.out.npz': poles (nu,nv,3), full clamped knot vectors ku, kv, and the
distances of the points to the surface."""
import os, numpy as np
import FreeCAD as App, ReverseEngineering as RE, Points, Part
src = os.environ['RE_IN']; D = np.load(src)
P = D['P']; nu, nv = int(D['NU']), int(D['NV'])
pts = Points.Points([App.Vector(*map(float, p)) for p in P])
best = None
for smooth_w in (0.1, 0.3):
    try:
        srf = RE.approxSurface(Points=pts, UDegree=3, VDegree=3, NbUPoles=nu, NbVPoles=nv, Smooth=True, Weight=smooth_w,
                               Grad=1.0, Bend=0.0, Curv=0.0, Iterations=5, Correction=True, PatchFactor=1.0)
    except Exception as ex:
        print('approxSurface failed:', ex); continue
    f = Part.Face(srf) if not hasattr(srf, 'toShape') else srf.toShape()
    d = np.array([f.distToShape(Part.Vertex(App.Vector(*map(float, p))))[0] for p in P])
    if best is None or np.percentile(d, 95) < np.percentile(best[1], 95): best = (srf, d)
srf, d = best
full = lambda k, m: np.repeat(np.array(k), np.array(m))
poles = np.array([[[q.x, q.y, q.z] for q in row] for row in srf.getPoles()])
np.savez(src + '.out.npz', poles=poles, ku=full(srf.getUKnots(), srf.getUMultiplicities()),
         kv=full(srf.getVKnots(), srf.getVMultiplicities()), d=d)
print(f'approxSurface {nu}x{nv}: p95 {np.percentile(d, 95):.2f} mm max {d.max():.2f} mm')

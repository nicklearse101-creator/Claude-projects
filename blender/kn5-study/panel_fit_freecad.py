"""Trimmed CAD faces from panel_fit.py (run with fcrun.sh / freecadcmd; env PF_IN = folder with panels_fit.json).

Each panel: B-spline surface (poles in plane mm -> AC mm via its frame), trimmed by its outline:
the outline sides are 2D B-splines in the surface's parameter space (= plane coordinates), so the
trim edges lie exactly on the surface. Writes PF_IN/panels_fit.step and panels_fit_mesh.npz (metres).
"""
import os, json, time
import numpy as np
import FreeCAD as App, Part, MeshPart

IN = os.environ['PF_IN']
res = json.load(open(os.path.join(IN, 'panels_fit.json')))
t0 = time.time()
shapes, mesh = [], {}


def to_world(fr, s, t, h):
    c, e1, e2, w = [np.array(x) for x in fr]
    return c * 1000 + s * e1 + t * e2 + h * w


def mults(kv):
    vals, cnt = np.unique(np.round(kv, 9), return_counts=True)
    return [float(v) for v in vals], [int(c) for c in cnt]


ONLY = os.environ.get('PF_ONLY')          # comma list of name substrings: build just those faces (debug)
for p in res:
    if ONLY and not any(k in p['name'] for k in ONLY.split(',')): continue
    tf = time.time()
    fr = p['frame']; P = np.array(p['poles'])                 # (nu, nv, 3) plane mm
    W = np.array([[to_world(fr, *P[i, j]) for j in range(P.shape[1])] for i in range(P.shape[0])])
    ku, mu = mults(p['ku']); kv, mv = mults(p['kv'])
    srf = Part.BSplineSurface()
    srf.buildFromPolesMultsKnots([[App.Vector(*W[i, j]) for j in range(W.shape[1])] for i in range(W.shape[0])],
                                 mu, mv, ku, kv, False, False, 3, 3)
    def build_wire(es):
        out = []
        for e in es:
            Q = np.array(e['poles'])
            c2 = Part.Geom2d.BSplineCurve2d()
            if e['periodic']:
                n = len(Q)
                c2.buildFromPolesMultsKnots([App.Base.Vector2d(*q) for q in Q], [1] * (n + 1), list(range(n + 1)), True, 3)
            else:
                k_, m_ = mults(np.array(e['knots']))
                c2.buildFromPolesMultsKnots([App.Base.Vector2d(*q) for q in Q], m_, k_, False, 3)
            out.append(c2.toShape(srf))
        return Part.Wire(Part.__sortEdges__(out))
    edges = p['wires'][0]
    own = p.get('own_plane') or p.get('band_s')      # partial-length band pieces: their surface may not cover the outline
    def prism_wire(es, lf, H=2000.0):
        """an outline (2D B-splines in frame lf) as a 3D wire on the plane h = -H of that frame"""
        out = []
        for e in es:
            Q = np.array(e['poles']); cu = Part.BSplineCurve(); V3 = [App.Vector(*to_world(lf, q[0], q[1], -H)) for q in Q]
            if e['periodic']:
                n = len(Q); cu.buildFromPolesMultsKnots(V3, [1] * (n + 1), list(range(n + 1)), True, 3)
            else:
                k_, m_ = mults(np.array(e['knots'])); cu.buildFromPolesMultsKnots(V3, m_, k_, False, 3)
            out.append(cu.toShape())
        return Part.Wire(Part.__sortEdges__(out))
    if own:
        # own-plane patch (corner blend): untrimmed surface cut by the outline prism of its region's frame
        try:
            lf = p['line_frame']; wv = np.array(lf[3]); Hh = 2000.0
            pr = [Part.Face(prism_wire(w_, lf)).extrude(App.Vector(*(wv * 2 * Hh))) for w_ in p['wires']]
            outl = pr[0]
            for h_ in pr[1:]: outl = outl.cut(h_)
            cut0 = srf.toShape().common(outl)
            face = Part.makeShell(cut0.Faces) if len(cut0.Faces) > 1 else cut0.Faces[0]
            ok = face.Area > 1
        except Exception as ex:
            print(p['name'], 'outline cut failed:', ex, flush=True); ok = False
    else:
        try:
            wires = [build_wire(w) for w in p['wires']]
            face = Part.Face(srf, wires[0])
            if len(wires) > 1:
                face = face.cutHoles(wires[1:]) or face
            fix = face.copy(); fix.fix(1e-3, 1e-4, 1e-2)
            if fix.isValid(): face = fix
            ok = face.isValid() and face.Area > 1
        except Exception as ex:
            print(p['name'], 'trim failed:', ex); ok = False
    if not ok:
        print(p['name'], 'trim invalid -> untrimmed'); face = srf.toShape()
    if ok and (p.get('band_lo') or p.get('band_hi')):
        # cut the face exactly on its character lines: prism over the band (area between the two curves)
        H = 2000.0
        lf = p.get('line_frame', fr)          # the band lines are curves t = g(s) in the REGION's frame
        c, e1, e2, w = [np.array(x) for x in lf]
        dom_s = [min(p['dom'][0], *(L['kv'][0] for L in (p.get('band_lo'), p.get('band_hi')) if L)),
                 max(p['dom'][1], *(L['kv'][-1] for L in (p.get('band_lo'), p.get('band_hi')) if L))]
        if p.get('band_s'):                   # a band patch along part of its line only (roll middle / corner)
            dom_s = [max(dom_s[0], p['band_s'][0]), min(dom_s[1], p['band_s'][1])]
        def line_edge(L, s_a, s_b, t_const):
            if L is None:
                return Part.LineSegment(App.Vector(*to_world(lf, s_a, t_const, -H)), App.Vector(*to_world(lf, s_b, t_const, -H))).toShape()
            k_, m_ = mults(np.array(L['kv'])); cu = Part.BSplineCurve()
            cu.buildFromPolesMultsKnots([App.Vector(*to_world(lf, gs, cs, -H)) for gs, cs in zip(L['g'], L['c'])], m_, k_, False, 3)
            # poles at Greville points => curve parameter = s, so the band's s range is a plain segment
            a_, b_ = max(s_a, cu.FirstParameter), min(s_b, cu.LastParameter)
            if a_ > cu.FirstParameter + 1e-6 or b_ < cu.LastParameter - 1e-6: cu.segment(a_, b_)
            return cu.toShape()
        lo = line_edge(p.get('band_lo'), dom_s[0], dom_s[1], -5000.0); hi = line_edge(p.get('band_hi'), dom_s[0], dom_s[1], 5000.0)
        a0, a1 = lo.Vertexes[0].Point, lo.Vertexes[-1].Point; b0, b1 = hi.Vertexes[0].Point, hi.Vertexes[-1].Point
        wire = Part.Wire(Part.__sortEdges__([lo, Part.LineSegment(a1, b1).toShape(), hi, Part.LineSegment(b0, a0).toShape()]))
        prism = Part.Face(wire).extrude(App.Vector(*(w * 2 * H)))
        cut_ = face.common(prism)
        if cut_.Faces and cut_.Area > 1:
            face = Part.makeShell(cut_.Faces) if len(cut_.Faces) > 1 else cut_.Faces[0]
        else:
            print(p['name'], 'band cut failed')
    shapes.append(face)
    m = MeshPart.meshFromShape(Shape=face, MaxLength=float(os.environ.get('PF_MAXLEN', 6)))   # even triangles (Mefisto)
    pts, fc = m.Topology
    mesh[p['name'] + '_P'] = np.array([[q.x, q.y, q.z] for q in pts]) / 1000.0
    mesh[p['name'] + '_F'] = np.array(fc, int)
    print(f"{p['name']:24s} area {face.Area / 1e6:.3f} m2  edges {len(edges)}  mesh {len(fc)} tris  valid {ok}  {time.time() - tf:.1f} s", flush=True)
Part.makeCompound(shapes).exportStep(os.path.join(IN, 'panels_fit.step'))
np.savez(os.path.join(IN, 'panels_fit_mesh.npz'), **mesh)
print('done', round(time.time() - t0, 1), 's')

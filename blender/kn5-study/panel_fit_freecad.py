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
shapes, mesh, normals = [], {}, {}


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
    def outline_face(w_, lf):
        f_ = Part.Face(prism_wire(w_, lf))
        if not f_.isValid():                              # a long B-spline outline can come out slightly self-touching
            g_ = f_.copy(); g_.fix(1e-3, 1e-4, 1e-2)
            if g_.isValid(): f_ = g_
        return f_
    if own:
        # own-plane patch (corner blend): untrimmed surface cut by the outline prism of its region's frame
        try:
            lf = p['line_frame']; wv = np.array(lf[3]); Hh = 2000.0
            if p.get('own_poly'):                     # its own outline, in its own plane
                V3o = [App.Vector(*to_world(fr, q[0], q[1], -Hh)) for q in p['own_poly']]
                fo_ = Part.Face(Part.makePolygon(V3o + [V3o[0]]))
                if not fo_.isValid():
                    g_ = fo_.copy(); g_.fix(1e-3, 1e-4, 1e-2); fo_ = g_ if g_.isValid() else fo_
                outl = fo_.extrude(App.Vector(*(np.array(fr[3]) * 2 * Hh)))
            else:
                pr = [outline_face(w_, lf).extrude(App.Vector(*(wv * 2 * Hh))) for w_ in p['wires']]
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
    # an area given as a 2D polygon (plane mm in its frame): band_poly keeps only that area (arch lip),
    # cut_poly removes it (the lip's area cut out of the side faces)
    def poly_prism(poly, lf, H=2000.0):
        V3 = [App.Vector(*to_world(lf, q[0], q[1], -H)) for q in poly]
        w_ = Part.makePolygon(V3 + [V3[0]]); wv = np.array(lf[3])
        return Part.Face(w_).extrude(App.Vector(*(wv * 2 * H)))
    if ok and p.get('band_poly'):
        try:
            cc = face.common(poly_prism(p['band_poly'], p.get('line_frame') or fr))
            if cc.Faces and cc.Area > 1: face = Part.makeShell(cc.Faces) if len(cc.Faces) > 1 else cc.Faces[0]
        except Exception as ex: print(p['name'], 'band_poly failed:', ex, flush=True)
    if not ok and not own:
        # parameter-space trim failed (tiny or folded outline): cut the surface with the outline's 3D prism
        try:
            wv = np.array(fr[3]); pr = [outline_face(w_, fr).extrude(App.Vector(*(wv * 4000.0))) for w_ in p['wires']]
            outl = pr[0]
            for h_ in pr[1:]: outl = outl.cut(h_)
            cut0 = srf.toShape().common(outl)
            if cut0.Faces and cut0.Area > 1:
                face = Part.makeShell(cut0.Faces) if len(cut0.Faces) > 1 else cut0.Faces[0]; ok = True
                print(p['name'], 'trimmed by prism instead', flush=True)
        except Exception as ex:
            print(p['name'], 'prism trim failed too:', ex, flush=True)
    if not ok:
        print(p['name'], 'trim invalid -> left out', flush=True); continue
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
            if a_ >= b_: raise ValueError(f'band range {s_a:.0f}..{s_b:.0f} outside its line')
            if a_ > cu.FirstParameter + 1e-6 or b_ < cu.LastParameter - 1e-6: cu.segment(a_, b_)
            return cu.toShape()
        try:
            lo = line_edge(p.get('band_lo'), dom_s[0], dom_s[1], -5000.0); hi = line_edge(p.get('band_hi'), dom_s[0], dom_s[1], 5000.0)
            a0, a1 = lo.Vertexes[0].Point, lo.Vertexes[-1].Point; b0, b1 = hi.Vertexes[0].Point, hi.Vertexes[-1].Point
            wire = Part.Wire(Part.__sortEdges__([lo, Part.LineSegment(a1, b1).toShape(), hi, Part.LineSegment(b0, a0).toShape()]))
            prism = Part.Face(wire).extrude(App.Vector(*(w * 2 * H)))
            cut_ = face.common(prism)
            if cut_.Faces and cut_.Area > 1:
                face = Part.makeShell(cut_.Faces) if len(cut_.Faces) > 1 else cut_.Faces[0]
            else:
                print(p['name'], 'band cut failed')
        except Exception as ex:
            print(p['name'], 'band cut failed:', ex, flush=True); continue
    if p.get('cut_poly'):
        try:
            cc = face.cut(poly_prism(p['cut_poly'], p['cut_frame']))
            if cc.Faces and cc.Area > 1: face = Part.makeShell(cc.Faces) if len(cc.Faces) > 1 else cc.Faces[0]
        except Exception as ex: print(p['name'], 'cut_poly failed:', ex, flush=True)
    shapes.append(face)
    m = MeshPart.meshFromShape(Shape=face, MaxLength=float(os.environ.get('PF_MAXLEN', 6)))   # even triangles (Mefisto)
    pts, fc = m.Topology
    if not fc:                                            # Mefisto can fail on slivers: standard mesher instead
        m = MeshPart.meshFromShape(Shape=face, LinearDeflection=0.05, AngularDeflection=0.2, Relative=False); pts, fc = m.Topology
    if not fc:
        print(p['name'], 'mesh failed -> left out', flush=True); continue
    mesh[p['name'] + '_P'] = np.array([[q.x, q.y, q.z] for q in pts]) / 1000.0
    # exact surface normals at every display vertex (works for height fields and general surfaces alike),
    # pointing out of the car: same side as the frame's outward axis w
    sf = face.Faces[0].Surface; wout = np.array((p.get('line_frame') or p['frame'])[3]); nn = []
    for q in pts:
        u_, v_ = sf.parameter(q); n_ = sf.normal(u_, v_); nn.append([n_.x, n_.y, n_.z])
    nn = np.array(nn); nn *= np.sign((nn @ wout).mean() or 1.0)
    normals[p['name']] = nn
    mesh[p['name'] + '_F'] = np.array(fc, int)
    print(f"{p['name']:24s} area {face.Area / 1e6:.3f} m2  edges {len(edges)}  mesh {len(fc)} tris  valid {ok}  {time.time() - tf:.1f} s", flush=True)
# ---- shut-line returns: a ruled strip turned in square to the skin along every FREE outer edge ----
# (an edge no other face shares). Kunos: ~5 mm return. PF_RETURNS = depth in mm (0 = off).
RET = float(os.environ.get('PF_RETURNS', 0))
if RET > 0 and not ONLY:
    names = [p['name'] for p in res if p['name'] + '_P' in mesh]
    allf = [(n, sh) for n, sh in zip(names, shapes)]
    def hole_polys(p):
        """the outline's openings (window) as 2D polylines in plane mm of the frame its wires live in"""
        out = []
        for w_ in p['wires'][1:]:
            for e_ in w_:
                Q = np.array(e_['poles'])
                if e_['periodic']:
                    n_ = len(Q); kv_ = np.arange(-3, n_ + 4) / n_; u_ = np.linspace(0, 1, 400, endpoint=False)
                    B = np.zeros((len(u_), n_))
                    for i in range(n_ + 3):
                        out_i = np.array([bsp(kv_, i, x) for x in u_]); B[:, i % n_] += out_i
                else:
                    kv_ = np.array(e_['knots']); n_ = len(Q); u_ = np.linspace(kv_[0], kv_[-1] - 1e-9, 200)
                    B = np.array([[bsp(kv_, i, x) for i in range(n_)] for x in u_])
                out.append(B @ Q)
        return np.concatenate(out) if out else np.zeros((0, 2))
    def bsp(kv, i, x, p=3):
        if p == 0: return 1.0 if kv[i] <= x < kv[i + 1] else 0.0
        a = 0.0 if kv[i + p] == kv[i] else (x - kv[i]) / (kv[i + p] - kv[i]) * bsp(kv, i, x, p - 1)
        b = 0.0 if kv[i + p + 1] == kv[i + 1] else (kv[i + p + 1] - x) / (kv[i + p + 1] - kv[i + 1]) * bsp(kv, i + 1, x, p - 1)
        return a + b
    k = 0
    for n, sh in allf:
        p = res[names.index(n)]
        if 'glass' in n.lower(): continue                     # glass sits in the frame: no return
        ON = os.environ.get('PF_RETURNS_ON')                  # body-panel faces only (name substrings); parts get none
        # a token matches the whole face name's end ('SUB1:r1') or a band prefix ('SUB1:r0:'); 'r1' must not match r10
        if ON and not any(n.endswith(k_) or (k_.endswith(':') and k_ in n) for k_ in ON.split(',')): continue
        H2 = hole_polys(p); lf_ = p.get('line_frame') or p['frame']
        c_, e1_, e2_, w_ = [np.array(x) for x in lf_]
        for e in sh.Edges:
            if e.Length < 20: continue
            pts = e.discretize(Distance=4.0)
            if len(H2):                                       # on the window opening: the frame channel goes there
                X = np.array([[q.x, q.y, q.z] for q in pts]) - c_ * 1000
                st = np.c_[X @ e1_, X @ e2_]
                dh = np.min(np.linalg.norm(st[:, None] - H2[None], axis=2), axis=1)
                if np.mean(dh < 3.0) > 0.5: continue
            # free = its middle 80 % is more than 1 mm from every other face
            mid = pts[len(pts) // 10: len(pts) - len(pts) // 10] or pts
            shared = False
            for n2, sh2 in allf:
                if n2 == n: continue
                if sum(sh2.distToShape(Part.Vertex(q))[0] < 1.0 for q in mid[::max(1, len(mid) // 6)]) >= 2:
                    shared = True; break
            if shared: continue
            fc = sh.Faces[0]; inner = []
            for q in pts:
                u_, v_ = fc.Surface.parameter(q); nv = fc.Surface.normal(u_, v_)
                inner.append(q - nv * RET)
            # turn in on the side AWAY from the car's outside: face normals point out (checked below)
            w_out = App.Vector(*(res[names.index(n)].get('line_frame') or res[names.index(n)]['frame'])[3])
            if sum((q2 - q1).dot(w_out) for q1, q2 in zip(pts, inner)) > 0:
                inner = [q1 - (q2 - q1) for q1, q2 in zip(pts, inner)]
            try:
                c2 = Part.BSplineCurve(); c2.approximate(Points=inner, DegMin=3, DegMax=3, Tolerance=0.05)
                c1 = Part.BSplineCurve(); c1.approximate(Points=pts, DegMin=3, DegMax=3, Tolerance=0.05)
                rs = Part.makeRuledSurface(c1.toShape(), c2.toShape())
            except Exception as ex:
                print('return failed on', n, ex, flush=True); continue
            rn = f'return{k}:{n}'; k += 1
            shapes.append(rs)
            m = MeshPart.meshFromShape(Shape=rs, MaxLength=float(os.environ.get('PF_MAXLEN', 6)))
            pts_, fc_ = m.Topology
            mesh[rn + '_P'] = np.array([[q.x, q.y, q.z] for q in pts_]) / 1000.0; mesh[rn + '_F'] = np.array(fc_, int)
            sf = rs.Faces[0].Surface; nn = []
            for q in pts_:
                u_, v_ = sf.parameter(q); n_ = sf.normal(u_, v_); nn.append([n_.x, n_.y, n_.z])
            nn = np.array(nn); ctr = np.array([sh.CenterOfMass.x, sh.CenterOfMass.y, sh.CenterOfMass.z])
            pm = np.array([[q.x, q.y, q.z] for q in pts_])
            nn *= np.sign(((pm - ctr) * nn).sum(1).mean() or 1.0)       # facing out of the panel, into the gap
            normals[rn] = nn
            print(f'{rn:40s} length {e.Length:6.0f} mm  area {rs.Area / 1e6:.4f} m2', flush=True)
Part.makeCompound(shapes).exportStep(os.path.join(IN, 'panels_fit.step'))
np.savez(os.path.join(IN, 'panels_fit_mesh.npz'), **mesh)
np.savez(os.path.join(IN, 'panels_fit_normals.npz'), **normals)   # exact normals (FreeCAD)
print('done', round(time.time() - t0, 1), 's')

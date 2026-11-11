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
built = {}                                # face name -> built shape (strips are built on these faces' edges)
# faces built by ANOTHER run (PF_FOREIGN='tag=dir;...', dirs written with PF_SAVE_FACES): only their edges are used
# (a strip on this run's side of a join takes the other build's real edge); named 'tag/<face name>'
for _fs in [x for x in os.environ.get('PF_FOREIGN', '').split(';') if x]:
    _tag, _dir = _fs.split('=', 1)
    for _n, _f in json.load(open(os.path.join(_dir, 'faces.json'))).items():
        _sh = Part.Shape(); _sh.read(os.path.join(_dir, _f)); built[f'{_tag}/{_n}'] = _sh
    print('foreign faces', _tag, len(json.load(open(os.path.join(_dir, 'faces.json')))), flush=True)
for p in res:
    if ONLY and not any(k in p['name'] for k in ONLY.split(',')): continue
    if p.get('strip'): continue           # thin strips: after every wide face (below)
    if p.get('grid'):                     # station-profile surface (blend_build.pillar_grid): through the grid points
        tf = time.time(); G_ = np.array(p['grid'])
        srf = Part.BSplineSurface()
        srf.approximate(Points=[[App.Vector(*q) for q in row] for row in G_], DegMin=3, DegMax=5, Tolerance=0.02)
        face = srf.toShape()
        dev = max(srf.toShape().distToShape(Part.Vertex(App.Vector(*q)))[0] for q in G_.reshape(-1, 3)[::7])
        if dev > 0.5:     # approximate can fail quietly on a long, unevenly spaced grid (6 poles over 54 stations, 17 mm
            srf = Part.BSplineSurface(); srf.interpolate([[App.Vector(*q) for q in row] for row in G_])   # off): interpolate it
            face = srf.toShape()
            dev = max(face.distToShape(Part.Vertex(App.Vector(*q)))[0] for q in G_.reshape(-1, 3)[::7])
        shapes.append(face); built[p['name']] = face
        m = MeshPart.meshFromShape(Shape=face, MaxLength=float(os.environ.get('PF_MAXLEN', 6)))
        pts, fc = m.Topology
        nn = []
        for q in pts:
            u_, v_ = srf.parameter(q); n_ = srf.normal(u_, v_); nn.append([n_.x, n_.y, n_.z])
        nn = np.array(nn); nn *= np.sign((nn @ np.array(p['frame'][3])).mean() or 1.0)
        mesh[p['name'] + '_P'] = np.array([[q.x, q.y, q.z] for q in pts]) / 1000.0; mesh[p['name'] + '_F'] = np.array(fc, int)
        normals[p['name']] = nn
        print(f"{p['name']:24s} GRID area {face.Area / 1e6:.3f} m2  poles {srf.NbUPoles}x{srf.NbVPoles} deg {srf.UDegree}x{srf.VDegree}  grid dev {dev:.3f} mm  mesh {len(fc)} tris  {time.time() - tf:.1f} s", flush=True)
        continue
    tf = time.time()
    fr = p['frame']; P = np.array(p['poles'])                 # (nu, nv, 3) plane mm
    W = np.array([[to_world(fr, *P[i, j]) for j in range(P.shape[1])] for i in range(P.shape[0])])
    ku, mu = mults(p['ku']); kv, mv = mults(p['kv'])
    srf = Part.BSplineSurface()
    srf.buildFromPolesMultsKnots([[App.Vector(*W[i, j]) for j in range(W.shape[1])] for i in range(W.shape[0])],
                                 mu, mv, ku, kv, False, False, p.get('du', 3), p.get('dv', 3))
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
    # partial-length band pieces and sub-panel faces: their surface may not cover the panel outline, and a
    # parameter-space trim by an outline lying off the surface gives a bogus huge face - trim by 3D prisms instead
    own = p.get('own_plane') or p.get('band_s') or p.get('band_poly')
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
            lf = p.get('line_frame') or fr; wv = np.array(lf[3]); Hh = 2000.0
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
                print(p['name'], 'band cut failed -> left out', flush=True); continue
        except Exception as ex:
            print(p['name'], 'band cut failed:', ex, flush=True); continue
    if p.get('cut_poly'):
        try:
            cc = face.cut(poly_prism(p['cut_poly'], p['cut_frame']))
            if cc.Faces and cc.Area > 1: face = Part.makeShell(cc.Faces) if len(cc.Faces) > 1 else cc.Faces[0]
        except Exception as ex: print(p['name'], 'cut_poly failed:', ex, flush=True)
    for cpl in p.get('cut_planes') or []:                # exact planar cut: remove the half-space the normal points into
        try:
            o_, n_ = App.Vector(*cpl[0]), App.Vector(*cpl[1]); n_.normalize(); Lb = 6000.0
            a_ = n_.cross(App.Vector(0, 0, 1)) if abs(n_.z) < 0.9 else n_.cross(App.Vector(1, 0, 0)); a_.normalize(); b_ = n_.cross(a_)
            corner = o_ - a_ * (Lb / 2) - b_ * (Lb / 2)
            pl = Part.Face(Part.makePolygon([corner, corner + a_ * Lb, corner + a_ * Lb + b_ * Lb, corner + b_ * Lb, corner]))
            cc = face.cut(pl.extrude(n_ * Lb))
            if cc.Faces and cc.Area > 1: face = Part.makeShell(cc.Faces) if len(cc.Faces) > 1 else cc.Faces[0]
        except Exception as ex: print(p['name'], 'plane cut failed:', ex, flush=True)
    for cp in p.get('cut_polys') or []:                  # seams of wrap sub-panels: the far side of a smooth seam curve
        try:
            cc = face.cut(poly_prism(cp['poly'], cp['frame']))
            if cc.Faces and cc.Area > 1: face = Part.makeShell(cc.Faces) if len(cc.Faces) > 1 else cc.Faces[0]
        except Exception as ex: print(p['name'], 'seam cut failed:', ex, flush=True)
    cge = p.get('cut_grid_edge')
    if cge and cge['grid'] in built:            # cut on a grid face's REAL edge (a polyline through its stations cuts
        try:                                    # chords across a curved edge: 0.5 mm cracks round the foot's corner)
            near = np.array(cge['near']); dirs = np.array(cge['dirs'])
            def edge_dist(e):
                X_ = np.array([[q.x, q.y, q.z] for q in e.discretize(40)])
                return np.mean([np.linalg.norm(X_ - q, axis=1).min() for q in near])
            eg = min(built[cge['grid']].Edges, key=edge_dist)
            X_ = np.array([[q.x, q.y, q.z] for q in eg.discretize(Distance=1.0)])
            if np.linalg.norm(X_[0] - near[0]) > np.linalg.norm(X_[-1] - near[0]): X_ = X_[::-1]
            # only the stretch along the given stations (the edge runs on up the pillar): the longest run within 15 mm
            dn_ = np.linalg.norm(X_[:, None] - near[None], axis=2).min(1); ok_ = dn_ < 15.0
            runs_, cur_ = [], []
            for i_, o_ in enumerate(ok_):
                if o_: cur_.append(i_)
                elif cur_: runs_.append(cur_); cur_ = []
            if cur_: runs_.append(cur_)
            X_ = X_[max(runs_, key=len)]
            kk_ = np.argmin(np.linalg.norm(X_[:, None] - near[None], axis=2), axis=1); D_ = dirs[kk_]
            t0_ = (X_[0] - X_[5]) / np.linalg.norm(X_[0] - X_[5]); t1_ = (X_[-1] - X_[-6]) / np.linalg.norm(X_[-1] - X_[-6])
            X_ = np.r_[[X_[0] + 30 * t0_], X_, [X_[-1] + 30 * t1_]]; D_ = np.r_[D_[:1], D_, D_[-1:]]
            band = np.r_[X_, (X_ + 300 * D_)[::-1]]
            c_, e1_, e2_, w_ = [np.array(x) for x in fr]
            poly = np.c_[(band - c_ * 1000) @ e1_, (band - c_ * 1000) @ e2_]
            cc = face.cut(poly_prism(poly.tolist(), fr))
            # the band prism can merely SPLIT the face along the edge (both pieces kept): keep the deck-side pieces only
            keep_ = []
            for fc_ in cc.Faces:
                cm_ = np.array(fc_.CenterOfMass); k_ = np.argmin(np.linalg.norm(near - cm_, axis=1))
                if (cm_ - near[k_]) @ dirs[k_] < 0: keep_.append(fc_)
            if os.environ.get('PF_DEBUG'): print(p['name'], 'edge cut: before', round(face.Area), 'after', round(cc.Area), 'faces', len(cc.Faces), 'kept', len(keep_), round(sum(x.Area for x in keep_)), flush=True)
            if keep_: face = Part.makeShell(keep_) if len(keep_) > 1 else keep_[0]
            if os.environ.get('PF_DEBUG'):
                S_ = np.array([[q.x, q.y, q.z] for e_ in face.Edges for q in e_.discretize(Distance=2.0)])
                print('  deck boundary -> nearest foot E0 point: p50 %.1f mm; foot E0 points -> deck boundary: p50 %.1f max %.1f mm; band X_ -> E0 p95 %.2f mm' % (
                    np.median(np.linalg.norm(S_[:, None] - near[None], axis=2).min(1)), np.median(np.linalg.norm(near[:, None] - S_[None], axis=2).min(1)),
                    np.linalg.norm(near[:, None] - S_[None], axis=2).min(1).max(), np.percentile(np.linalg.norm(X_[:, None] - near[None], axis=2).min(1), 95)), flush=True)
            print(p['name'], f'cut on the edge of {cge["grid"]} ({eg.Length:.0f} mm, {edge_dist(eg):.2f} mm from its stations)', flush=True)
        except Exception as ex:
            print(p['name'], 'grid edge cut failed:', ex, '-> station polyline cut', flush=True)
            for cp in cge.get('fallback') or []:
                cc = face.cut(poly_prism(cp['poly'], cp['frame']))
                if cc.Faces and cc.Area > 1: face = Part.makeShell(cc.Faces) if len(cc.Faces) > 1 else cc.Faces[0]
    shapes.append(face); built[p['name']] = face
    m = MeshPart.meshFromShape(Shape=face, MaxLength=float(os.environ.get('PF_MAXLEN') or p.get('maxlen') or 6))   # even triangles (Mefisto)
    pts, fc = m.Topology
    if not fc:                                            # Mefisto can fail on slivers: standard mesher instead
        print(p['name'], 'Mefisto mesh failed -> standard mesher (fine, slow)', flush=True)
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
# ---- thin strips (strip_build.py): ruled surfaces between shared side curves ----
# A side on a wide face = that face's own built edge, sampled every 1 mm and refitted (so the join is exact to the
# refit, ~0.02 mm); a side shared by two strips or free = fitted once to the Kunos boundary vertices and used by both.
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.environ.get('PF_SRC', r'D:\Claude\Claude-\blender\kn5-study'))
_sys.path.insert(0, r'D:\Claude\Claude-\blender\kn5-study')
import strip_build as SB
strips = [p for p in res if p.get('strip') and not (ONLY and not any(k in p['name'] for k in ONLY.split(',')))]
strips.sort(key=lambda p: p['strip'].get('mode') != 'chain')   # chain strips first: their curves are reused
dbg = {}
curves_maker = {}
curves = {}                               # curve key -> (Part.BSplineCurve, source, fit error mm)


def face_edge_points(prefix, near, tol=2.0):
    """points (mm) on the built edges of the faces named prefix (+ band/wrap suffixes) within tol of polyline near"""
    sh = [s for n, s in built.items() if n == prefix or (n.startswith(prefix) and not n[len(prefix)].isdigit())]
    if not sh: return np.zeros((0, 3))
    X, Tg, Ei = [], [], []
    ne = 0
    for s in sh:
        for e in s.Edges:
            if e.Length < 2: continue
            for q in e.discretize(Distance=1.0):
                t_ = e.tangentAt(e.Curve.parameter(q)) if hasattr(e, 'Curve') else App.Vector()
                X.append([q.x, q.y, q.z]); Tg.append([t_.x, t_.y, t_.z]); Ei.append(ne)
            ne += 1
    X, Tg, Ei = np.array(X), np.array(Tg), np.array(Ei)
    _, d = SB.spine_s(near, X)
    # only where the edge runs ALONG the side (at the strip's ends the face's outline turns the corner)
    sn, _ = SB.spine_s(near, X)
    dn = np.r_[0, np.cumsum(np.linalg.norm(np.diff(near, axis=0), axis=1))]
    tq = np.gradient(near, axis=0); tq /= np.maximum(np.linalg.norm(tq, axis=1), 1e-9)[:, None]
    tl = tq[np.clip(np.searchsorted(dn, sn), 0, len(near) - 1)]
    al = np.abs((Tg * tl).sum(1)) / np.maximum(np.linalg.norm(Tg, axis=1), 1e-9)
    m = (d < tol) & (al > 0.8) & (sn > 0.5) & (sn < dn[-1] - 0.5)
    # two built edges running side by side along the strip (roof: the crown's outline AND the side band's inner edge
    # on the side line, 4 mm apart where the drip strip ends): keep, at each position, only the edge that lies closer
    # to the Kunos side (median distance per edge); a mix of both is not one curve
    if len(np.unique(Ei[m])) > 1:
        order = sorted(np.unique(Ei[m]), key=lambda k: np.median(d[m & (Ei == k)]))
        keep = np.zeros(len(X), bool); taken = np.zeros(0)
        for k in order:
            sel = np.where(m & (Ei == k))[0]
            if len(taken): sel = sel[np.abs(sn[sel][:, None] - taken[None, :]).min(1) > 1.5]
            keep[sel] = True; taken = np.r_[taken, sn[sel]]
        m = keep
    return X[m]


def side_curve(st, sd):
    """the side's curve (cached by key: a curve shared by two strips is made once)"""
    key = sd['key']
    if key in curves: return curves[key]
    Sp = np.array(st['spine']) * 1000; Q = np.array(sd['pts']) * 1000
    X, src = np.zeros((0, 3)), 'vertices'
    if sd.get('chain'):
        # a chain side (runs along several neighbours): the built edges of every wide neighbour along it, ONE curve
        X = np.zeros((0, 3))
        for r_ in sd['runs']:
            if r_.get('nb_name') and not r_.get('nb_strip'):
                X = np.r_[X, face_edge_points(r_['nb_name'], np.array(r_['pts']) * 1000)]
    elif sd.get('nb_name') and not sd.get('nb_strip'):
        X = face_edge_points(sd['nb_name'], Q)
    s_q, _ = SB.spine_s(Sp, Q)
    if len(X) >= 20:
        s_x, _ = SB.spine_s(Sp, X)
        cover = np.mean([np.abs(s_x - v).min() < 3.0 for v in s_q])
        if cover > 0.6:
            # the face edge where it exists; the Kunos side polyline only where the face edge does not reach
            far = np.array([np.abs(s_x - v).min() > 3.0 for v in s_q])
            X = np.r_[X, Q[far]]; s_all = np.r_[s_x, s_q[far]]; src = f'face edge ({cover*100:.0f} %)'
            tol = np.r_[np.full(len(s_x), 0.02), np.full(int(far.sum()), 0.3)]
        else: X = np.zeros((0, 3))
    if src == 'vertices':
        X, s_all, tol = Q, s_q, np.full(len(Q), 0.3)
    o = np.argsort(s_all); X, s_all, tol = X[o], s_all[o], tol[o]
    dbg.setdefault('keys', []).append(key); dbg[key + '_X'] = X; dbg[key + '_s'] = s_all; dbg[key + '_Q'] = Q
    L = s_all[-1] - s_all[0]
    # face edge: dense exact samples, follow them (0.02 mm); Kunos vertices: one control per 20 mm at most (more
    # chases the chord corners of the boundary polyline)
    exact = tol.min() < 0.1
    nmax = int(np.clip(L / (8.0 if exact else 20.0), 4, 200 if sd.get('chain') else 80))
    f = SB.fit_graph(s_all, X, [s_all[0], s_all[-1]], tol=tol, nmax=nmax, mu=1e-8 if exact else 1e-6)
    if exact and f['err'] > 1.0:
        # face-edge samples that do not make one curve (a chain round a window corner picked up edges of the wrong
        # face): the Kunos side vertices alone
        print('   side', key, f"face edge fit {f['err']:.1f} mm -> Kunos vertices", flush=True)
        o = np.argsort(s_q); X, s_all, src = Q[o], s_q[o], 'vertices (fallback)'; L = s_all[-1] - s_all[0]
        f = SB.fit_graph(s_all, X, [s_all[0], s_all[-1]], tol=np.full(len(X), 0.3), nmax=int(np.clip(L / 20.0, 4, 80)), mu=1e-6)
    vals, cnt = np.unique(np.round(f['kv'], 9), return_counts=True)
    cu = Part.BSplineCurve()
    cu.buildFromPolesMultsKnots([App.Vector(*q) for q in f['C']], [int(c) for c in cnt], [float(v) for v in vals], False, 3)
    curves[key] = (cu, src, f['err']); curves_maker[key] = cur_strip[0]
    for r_ in sd.get('runs', []):          # a neighbouring strip along the chain reuses this curve (exact join)
        if r_.get('nb_strip'): curves[r_['key']] = curves[key]; curves_maker[r_['key']] = cur_strip[0]
    print('   side', key, src, f"err {f['err']:.3f} mm", f"{f['n']} controls", flush=True)
    return curves[key]


cur_strip = [None]
for p in strips:
    st = p['strip']; tf = time.time(); cur_strip[0] = p['name']
    try:
        Sp = np.array(st['spine']) * 1000
        cs = [side_curve(st, sd) for sd in st['sides']]
        # the strip's ends: square to its spine at both ends; each side curve cut where it is nearest those points
        ends = [Sp[0], Sp[-1]]
        segs = []
        # each rail runs to its OWN end corners (the side's first and last Kunos vertex), so the strip's end edges
        # go corner to corner (slanted ends kept); the ruled surface pairs the rails by normalised parameter
        for (cu, _, _), sd in zip(cs, st['sides']):
            Q_ = np.array(sd['pts']) * 1000
            if curves_maker.get(sd['key']) == p['name']:      # parameter = this strip's spine arc length
                sq_, _ = SB.spine_s(Sp, Q_[[0, -1]])
                a, b = max(sq_.min(), cu.FirstParameter), min(sq_.max(), cu.LastParameter)
            else:                                            # a curve made by the neighbouring strip: its own spine
                # nearest point by dense sampling (Geom closest-point lookups returned far local minima here)
                uu = np.linspace(cu.FirstParameter, cu.LastParameter, 2000)
                XX = np.array([[q.x, q.y, q.z] for q in (cu.value(u) for u in uu)])
                a, b = sorted(uu[np.linalg.norm(XX - e_, axis=1).argmin()] for e_ in Q_[[0, -1]])
            c2 = cu.copy()
            if b - a < 1.0: raise ValueError('side curve does not span the strip')
            c2.segment(a, b); segs.append(c2)
        # same direction for both (rulings must not cross)
        if (segs[0].StartPoint - segs[1].StartPoint).Length > (segs[0].StartPoint - segs[1].EndPoint).Length:
            segs[1].reverse()
        if os.environ.get('PF_STRIPDBG'):
            for c_ in segs: print('   rail', p['name'], [round(x, 1) for x in c_.StartPoint], [round(x, 1) for x in c_.EndPoint], 'len', round(c_.length(), 1), flush=True)
            print('   spine ends', [round(x, 1) for x in Sp[0]], [round(x, 1) for x in Sp[-1]], flush=True)
        rs = Part.makeRuledSurface(segs[0].toShape(), segs[1].toShape(), 1)   # 1 = as given (automatic can flip one rail)
        face = rs.Faces[0]
    except Exception as ex:
        print(p['name'], 'strip failed:', ex, flush=True); continue
    shapes.append(face); built[p['name']] = face
    m = MeshPart.meshFromShape(Shape=face, MaxLength=float(os.environ.get('PF_MAXLEN', 6)))
    pts, fc = m.Topology
    if not fc:
        m = MeshPart.meshFromShape(Shape=face, LinearDeflection=0.05, AngularDeflection=0.2, Relative=False); pts, fc = m.Topology
    if not fc:
        print(p['name'], 'strip mesh failed', flush=True); continue
    sf = face.Surface; nn = []
    for q in pts:
        u_, v_ = sf.parameter(q); n_ = sf.normal(u_, v_); nn.append([n_.x, n_.y, n_.z])
    nn = np.array(nn); nn *= np.sign((nn @ np.array(st['frame'][3])).mean() or 1.0)
    mesh[p['name'] + '_P'] = np.array([[q.x, q.y, q.z] for q in pts]) / 1000.0; mesh[p['name'] + '_F'] = np.array(fc, int)
    normals[p['name']] = nn
    print(f"{p['name']:24s} STRIP area {face.Area / 1e6:.4f} m2 (Kunos {st['area']:.4f})  sides " +
          ', '.join(f'{curves[sd["key"]][1]} {curves[sd["key"]][2]:.2f} mm' for sd in st['sides']) + f'  {time.time() - tf:.1f} s', flush=True)
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
# triangle winding to agree with the exact (outward) normals: a ruled strip or a reversed face meshes inward, and
# renderers shade a back-facing triangle with its normal flipped (the lamp-top wall came out dark)
for n_, nn_ in normals.items():
    P_, F_ = mesh[n_ + '_P'], mesh[n_ + '_F']
    if not len(F_) or nn_.shape != P_.shape: continue
    T_ = P_[F_]; g_ = np.cross(T_[:, 1] - T_[:, 0], T_[:, 2] - T_[:, 0])
    if (np.einsum('ij,ij->i', g_, nn_[F_].mean(1)) < 0).mean() > 0.5:
        mesh[n_ + '_F'] = F_[:, [0, 2, 1]]
if os.environ.get('PF_STRIPDBG'):
    np.savez(os.path.join(IN, 'strip_dbg.npz'), keys=np.array(dbg.get('keys', [])), **{k: v for k, v in dbg.items() if k != 'keys'})
if os.environ.get('PF_SAVE_FACES', '1') == '1':      # every built face as its own BREP (for PF_FOREIGN in other runs)
    _fd = os.path.join(IN, 'faces'); os.makedirs(_fd, exist_ok=True); _idx = {}
    for _k, (_n, _sh) in enumerate((n, sh) for n, sh in built.items() if '/' not in n):
        _f = f'f{_k:04d}.brep'; _sh.exportBrep(os.path.join(_fd, _f)); _idx[_n] = _f
    json.dump(_idx, open(os.path.join(_fd, 'faces.json'), 'w'), indent=0)
Part.makeCompound(shapes).exportStep(os.path.join(IN, 'panels_fit.step'))
np.savez(os.path.join(IN, 'panels_fit_mesh.npz'), **mesh)
np.savez(os.path.join(IN, 'panels_fit_normals.npz'), **normals)   # exact normals (FreeCAD)
print('done', round(time.time() - t0, 1), 's')

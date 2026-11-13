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


def dp_keep(X, tol):
    """Douglas-Peucker: indices of a polyline's points needed to stay within tol of it (iterative, keeps both ends)"""
    keep = np.zeros(len(X), bool); keep[0] = keep[-1] = True; stack = [(0, len(X) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1: continue
        a, b = X[i], X[j]; ab = b - a; L = np.linalg.norm(ab)
        P = X[i + 1:j] - a
        d = np.linalg.norm(P, axis=1) if L < 1e-12 else np.linalg.norm(np.cross(P, ab / L), axis=1)
        k = int(np.argmax(d))
        if d[k] > tol: keep[i + 1 + k] = True; stack += [(i, i + 1 + k), (i + 1 + k, j)]
    return np.nonzero(keep)[0]


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
    if p.get('strip') or p.get('corner_fill') or p.get('mirror_of'): continue   # thin strips / corner fills: after every wide face (below)
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
        ml_ = float(os.environ.get('PF_MAXLEN') or p.get('maxlen') or 6)
        if p.get('structured'):
            # mesh straight from the grid's own (u, v): rows of quads along the sweep, exact normals by srf.normal
            # (no srf.parameter() projection per point: the hatch U took 5 min that way)
            u0_, u1_, v0_, v1_ = srf.bounds()
            Lu_ = max(float(np.linalg.norm(np.diff(G_[:, j], axis=0), axis=1).sum()) for j in (0, G_.shape[1] // 2, -1))
            Lv_ = max(float(np.linalg.norm(np.diff(G_[i], axis=0), axis=1).sum()) for i in range(0, len(G_), max(1, len(G_) // 20)))
            nu_ = max(2, int(np.ceil(Lu_ / ml_)) + 1); nv_ = max(2, int(np.ceil(Lv_ / (ml_ * 0.5))) + 1)   # finer across (tight knee)
            us_, vs_ = np.linspace(u0_, u1_, nu_), np.linspace(v0_, v1_, nv_)
            vt_ = None
            if p.get('trim_outer'):
                # the grid runs past the panel's outer edge: trim it on the given outline (3D points on the surface).
                # The outline in (u, v) is a graph v = vt(u) (one crossing per row); mesh lines at the uniform u plus
                # extra u lines wherever the trim bends away from its chord (the sharp lower corners), each u line
                # spread from v0 to vt(u): the display mesh ends exactly on the outline.
                T3_ = np.array(p['trim_outer'])
                uvT = np.array([srf.parameter(App.Vector(*q)) for q in T3_])
                offT = np.array([(srf.value(*uv) - App.Vector(*q)).Length for uv, q in zip(uvT, T3_)])
                if uvT[-1, 0] < uvT[0, 0]: uvT, T3_, offT = uvT[::-1], T3_[::-1], offT[::-1]
                kp_ = [0]
                for i_ in range(1, len(uvT)):
                    if uvT[i_, 0] > uvT[kp_[-1], 0] + 1e-9: kp_.append(i_)
                nback_ = len(uvT) - len(kp_); uvT, T3_ = uvT[kp_], T3_[kp_]
                uvT = np.r_[[[u0_, uvT[0, 1]]], uvT, [[u1_, uvT[-1, 1]]]]
                vt_ = lambda u: np.interp(u, uvT[:, 0], uvT[:, 1])
                mmv_ = Lv_ / (v1_ - v0_)                                   # mm per unit v (rough, for the sag test)
                for _it in range(12):                                     # refine the u lines until the chords sag < 0.05 mm
                    add_ = []
                    for a_, b_ in zip(us_[:-1], us_[1:]):
                        m_ = (uvT[:, 0] > a_) & (uvT[:, 0] < b_)
                        if not m_.any(): continue
                        lin_ = vt_(a_) + (uvT[m_, 0] - a_) / (b_ - a_) * (vt_(b_) - vt_(a_))
                        dv_ = np.abs(uvT[m_, 1] - lin_) * mmv_
                        if dv_.max() > 0.05: add_.append(uvT[m_, 0][np.argmax(dv_)])
                    if not add_: break
                    us_ = np.unique(np.r_[us_, add_])
                    if p.get('sym_u'): us_ = np.unique(np.r_[us_, u0_ + u1_ - us_])      # mirror-symmetric grid: same u lines both halves
                print(f"{p['name']:24s} trim: {len(T3_)} outline points ({nback_} back-steps dropped), off the surface max {offT.max():.3f} mm, "
                      f"v {uvT[:, 1].min():.4f}..{uvT[:, 1].max():.4f} of {v0_:.4f}..{v1_:.4f}, {len(us_)} u lines", flush=True)
            # mesh lines along u also where the deck-side edge (v0) turns tightly: chords between 8 mm lines sagged
            # 0.4-0.7 mm off the deck's exact cut there (a crack in the watertight check at the hatch's glass corners)
            for _it in range(10):
                add_ = []
                for a_, b_ in zip(us_[:-1], us_[1:]):
                    m_ = 0.5 * (a_ + b_); A_, B_, M_ = srf.value(a_, v0_), srf.value(b_, v0_), srf.value(m_, v0_)
                    if ((A_ + B_) * 0.5 - M_).Length > float(os.environ.get('PF_GRID_SAG', 0.05)): add_.append(m_)
                if not add_: break
                us_ = np.unique(np.r_[us_, add_])
            pts_, nn = [], []
            for u_ in us_:
                for v_ in (vs_ if vt_ is None else v0_ + (vs_ - v0_) * (float(vt_(u_)) - v0_) / (v1_ - v0_)):
                    q = srf.value(u_, v_); n_ = srf.normal(u_, v_); pts_.append([q.x, q.y, q.z]); nn.append([n_.x, n_.y, n_.z])
            nu_ = len(us_)
            if vt_ is not None:
                # B-rep face for the STEP / neighbours: the surface trimmed by the outline in its (u, v) space (one 2D
                # B-spline per run between the outline's corners) + the three untouched sides
                try:
                    V2 = App.Base.Vector2d
                    uvc = uvT[1:-1]; cn_ = [int(np.argmin(np.linalg.norm(T3_ - np.array(c), axis=1))) for c in p.get('trim_corners') or []]
                    cut_ = sorted(set([0] + [c for c in cn_ if 0 < c < len(uvc) - 1] + [len(uvc) - 1]))
                    ed_ = []
                    pre_ = Part.Geom2d.Line2dSegment(V2(u0_, uvc[0, 1]), V2(*uvc[0])) if uvc[0, 0] > u0_ + 1e-9 else None
                    if pre_: ed_.append(pre_.toShape(srf))
                    # the trim as a polyline in (u, v) (thinned where it is straight in 3D: 0.005 mm): a 2D B-spline
                    # through it overshot where the trim drops steeply at the tab (u back-steps -> 'self-intersecting wire')
                    kq_ = dp_keep(T3_, float(os.environ.get('PF_TRIM_SAG', 0.005)))
                    kq_ = np.unique(np.r_[kq_, [c for c in cut_]])
                    for a_, b_ in zip(kq_[:-1], kq_[1:]):
                        ed_.append(Part.Geom2d.Line2dSegment(V2(*uvc[a_]), V2(*uvc[b_])).toShape(srf))
                    post_ = Part.Geom2d.Line2dSegment(V2(*uvc[-1]), V2(u1_, uvc[-1, 1])) if uvc[-1, 0] < u1_ - 1e-9 else None
                    if post_: ed_.append(post_.toShape(srf))
                    for A_, B_ in (((u1_, uvc[-1, 1]), (u1_, v0_)), ((u1_, v0_), (u0_, v0_)), ((u0_, v0_), (u0_, uvc[0, 1]))):
                        ed_.append(Part.Geom2d.Line2dSegment(V2(*A_), V2(*B_)).toShape(srf))
                    ft_ = Part.Face(srf, Part.Wire(Part.__sortEdges__(ed_)))
                    fx_ = ft_.copy(); fx_.fix(1e-3, 1e-4, 1e-2)
                    if fx_.isValid(): ft_ = fx_
                    if ft_.isValid() and 0.5 * face.Area < ft_.Area < face.Area:
                        face = ft_; shapes[-1] = face; built[p['name']] = face
                    else: print(p['name'], f'trimmed B-rep face invalid (valid {ft_.isValid()}, area {ft_.Area / 1e6:.4f} of {face.Area / 1e6:.4f} m2) -> STEP keeps the untrimmed grid face', flush=True)
                except Exception as ex: print(p['name'], 'trimmed B-rep face failed:', ex, '-> STEP keeps the untrimmed grid face', flush=True)
            idx_ = np.arange(nu_ * nv_).reshape(nu_, nv_)
            a_, b_, c_, d_ = idx_[:-1, :-1].ravel(), idx_[1:, :-1].ravel(), idx_[1:, 1:].ravel(), idx_[:-1, 1:].ravel()
            fc = np.r_[np.c_[a_, b_, c_], np.c_[a_, c_, d_]]
            Pm_ = np.array(pts_); nn = np.array(nn); nn *= np.sign((nn @ np.array(p['frame'][3])).mean() or 1.0)
            tn_ = np.cross(Pm_[fc[:, 1]] - Pm_[fc[:, 0]], Pm_[fc[:, 2]] - Pm_[fc[:, 0]])     # winding agrees with the normals
            flip_ = (tn_ * nn[fc].mean(1)).sum(1) < 0; fc[flip_] = fc[flip_][:, [0, 2, 1]]
            mesh[p['name'] + '_P'] = Pm_ / 1000.0; mesh[p['name'] + '_F'] = np.array(fc, int)
            normals[p['name']] = nn
            print(f"{p['name']:24s} GRID area {face.Area / 1e6:.3f} m2  poles {srf.NbUPoles}x{srf.NbVPoles} deg {srf.UDegree}x{srf.VDegree}  grid dev {dev:.3f} mm  structured mesh {nu_}x{nv_} ({len(fc)} tris)  {time.time() - tf:.1f} s", flush=True)
            continue
        m = MeshPart.meshFromShape(Shape=face, MaxLength=ml_)
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
            # keep only the points the chord sag needs (0.02 mm): a 1 mm polyline along a 3 m edge made Mefisto mesh
            # the hatch deck 30x too fine (155k triangles, 19 min)
            X_ = X_[dp_keep(X_, float(os.environ.get('PF_CUT_SAG', 0.02)))]
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
    nmax = int(np.clip(L / (8.0 if exact else float(st.get('vctrl_mm', 20.0))), 4, 200 if sd.get('chain') else 80))   # vctrl_mm: tight plan corners (bonnet notch R 9.3)
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
# ---- corner fills: the tiny Kunos patches where strips and faces end at a corner (bonnet r14-r27, < 50 mm2) ----
# The patch's Kunos outline (1 mm resampled) is snapped onto the nearest BUILT edge within CF_SNAP mm (so it meets its
# neighbours, G0), points further off stay Kunos (free edges); the patch = MakeFilling through that closed polygon
# (makeFilledFace, G0); the Kunos inside vertices are only checked. Too small for tangency to matter (research step 12).
CF_SNAP = float(os.environ.get('PF_CF_SNAP', 1.5))
def coons_face(X, n=14, cs=None):
    """bilinear Coons patch on a closed polyline X (mm): sides = the runs between its 4 sharpest turns (3 turns: the
    longest side split at its middle). G0 along every side by construction; B-spline through the 14 x 14 grid.
    (makeFilledFace on the same outlines ballooned 10-14 mm off the Kunos patches.)"""
    m = len(X); k = max(2, m // 16)
    if cs is not None: return _coons(X, sorted(cs), n), 4
    a = X[(np.arange(m) - k) % m] - X; b = X[(np.arange(m) + k) % m] - X
    turn = 180 - np.degrees(np.arccos(np.clip((a * b).sum(1) / np.maximum(np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1), 1e-12), -1, 1)))
    cs = []
    for i in np.argsort(-turn):
        if all(min(abs(i - j), m - abs(i - j)) > max(2, m // 10) for j in cs): cs.append(int(i))
        if len(cs) == 4: break
    if len(cs) < 3:                                       # a 3 mm2 patch with a handful of outline points
        cs = [int(round(i * m / 4)) % m for i in range(4)]
    elif len(cs) < 4 or turn[cs[3]] < 30:
        cs = sorted(cs[:3]); segs = [(cs[i], cs[(i + 1) % 3]) for i in range(3)]
        ln = [((b_ - a_) % m) for a_, b_ in segs]; j = int(np.argmax(ln)); a_, b_ = segs[j]
        cs = sorted(cs + [int((a_ + ln[j] // 2) % m)])
    return _coons(X, sorted(cs), n), len(cs)
def round_corner(X, cs, fA, fB, n=12, m=9):
    """G1 round between two strip ends (the bonnet's vertical wall corners): sides cs[0]->cs[1] (on fA) and
    cs[2]->cs[3] reversed (on fB) are the two walls' end edges; section i = cubic Hermite from A[i] to B[i], leaving
    each wall along its own surface square to the end edge (pointing into the gap), handle length of a circular arc
    through the same turn. Lofted through the n sections. Returns (face, mean turn deg) or (None, 0) if not a corner."""
    mm = len(X)
    def side(i0, i1, cnt):
        idx = [(i0 + t) % mm for t in range(((i1 - i0) % mm) + 1)]; Q = X[idx]
        d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]; t = np.linspace(0, d[-1], cnt)
        return np.c_[[np.interp(t, d, Q[:, c]) for c in range(3)]].T
    A = side(cs[0], cs[1], n); B = side(cs[2], cs[3], n)[::-1]
    def out_dir(f, P, Q):
        """unit direction in face f at P, square to the edge direction Q (tangent), pointing away from f's interior"""
        sf_ = f.Faces[0].Surface; u_, v_ = sf_.parameter(App.Vector(*P)); nn_ = sf_.normal(u_, v_); nn_ = np.array([nn_.x, nn_.y, nn_.z])
        d_ = np.cross(nn_, Q); d_ /= max(np.linalg.norm(d_), 1e-12)
        dp = f.distToShape(Part.Vertex(App.Vector(*(P + 0.5 * d_))))[0]; dm = f.distToShape(Part.Vertex(App.Vector(*(P - 0.5 * d_))))[0]
        return d_ if dp > dm else -d_
    G = np.zeros((n, m, 3)); ths = []
    if np.linalg.norm(B - A, axis=1).max() < 0.5: print('    round: no gap'); return None, 0.0
    t = np.linspace(0, 1, m)[:, None]
    h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
    for i in range(n):
        ta = A[min(i + 1, n - 1)] - A[max(i - 1, 0)]; tb = B[min(i + 1, n - 1)] - B[max(i - 1, 0)]
        dA = out_dir(fA, A[i], ta / np.linalg.norm(ta)); dB = out_dir(fB, B[i], tb / np.linalg.norm(tb))
        c = np.linalg.norm(B[i] - A[i]); th = np.arccos(np.clip(dA @ -dB, -1, 1)); ths.append(np.degrees(th))
        # a wedge (the notch corner: the walls nearly meet at the bottom): sections with no room get a plain line
        k = 3 * (4 / 3) * np.tan(th / 4) / (2 * np.sin(th / 2)) * c if th > np.radians(5) else c   # Hermite = 3 x arc handle
        G[i] = h00 * A[i] + h10 * k * dA + h01 * B[i] + h11 * k * (-dB)
    if np.mean(ths) < 15: print(f'    round: turn {np.mean(ths):.0f} deg'); return None, 0.0
    keep = np.linalg.norm(B - A, axis=1) > 0.3                # a wedge's tip (walls touching): no section there
    if keep.sum() < 4: print(f'    round: {keep.sum()} sections'); return None, 0.0
    srf = Part.BSplineSurface()
    try: srf.interpolate([[App.Vector(*q) for q in row] for row in G[keep]])
    except Exception as ex_: print('    round: interpolate', ex_); return None, 0.0
    return srf.toShape(), float(np.mean(ths))


def _coons(X, cs, n):
    m = len(X)
    def side(i0, i1, cnt):
        idx = [(i0 + t) % m for t in range(((i1 - i0) % m) + 1)]; Q = X[idx]
        d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]; t = np.linspace(0, d[-1], cnt)
        return np.c_[[np.interp(t, d, Q[:, c]) for c in range(3)]].T
    S0 = side(cs[0], cs[1], n); S1 = side(cs[1], cs[2], n); S2 = side(cs[2], cs[3], n)[::-1]; S3 = side(cs[3], cs[0], n)[::-1]
    u = np.linspace(0, 1, n)
    G = np.zeros((n, n, 3))
    for i, uu in enumerate(u):
        for j, vv in enumerate(u):
            G[i, j] = ((1 - vv) * S0[i] + vv * S2[i] + (1 - uu) * S3[j] + uu * S1[j]
                       - ((1 - uu) * (1 - vv) * S0[0] + uu * (1 - vv) * S0[-1] + (1 - uu) * vv * S2[0] + uu * vv * S2[-1]))
    srf = Part.BSplineSurface(); srf.interpolate([[App.Vector(*q) for q in row] for row in G])
    return srf.toShape()
cfs = [p for p in res if p.get('corner_fill')]
cfs.sort(key=lambda p: -p['corner_fill']['area'])          # big ones (wall rounds) first: the small chamfer corners snap onto them
for p in cfs:
    tf = time.time(); cf = p['corner_fill']
    try:
        L_ = np.array(cf['outline'])
        own = {n_: sh for n_, sh in built.items() if '/' not in n_}
        snapped, owner, nsn = [], [], 0
        for q in L_:
            best = (1e9, None, None)
            for n_, sh in own.items():
                bb = sh.BoundBox; bb.enlarge(CF_SNAP + 1)
                if not bb.isInside(App.Vector(*q)): continue
                for e in sh.Edges:
                    if e.Length < 0.2: continue
                    d_, pr_, _ = e.distToShape(Part.Vertex(App.Vector(*q)))
                    if d_ < best[0]: best = (d_, pr_[0][0], n_)
            if best[0] < CF_SNAP: snapped.append(best[1]); owner.append(best[2]); nsn += 1
            else: snapped.append(App.Vector(*q)); owner.append('free')
        runs_ = []
        for o_ in owner:
            if runs_ and runs_[-1][0] == o_: runs_[-1][1] += 1
            else: runs_.append([o_, 1])
        print('   ', p['name'], 'outline snaps:', ' '.join(f'{o_.split(":")[-1]}x{c_}' for o_, c_ in runs_), flush=True)
        # drop near-duplicates (two outline points snapped onto one corner)
        pts_, own_ = [snapped[0]], [owner[0]]
        for v_, o_ in zip(snapped[1:], owner[1:]):
            if (v_ - pts_[-1]).Length > 0.15: pts_.append(v_); own_.append(o_)
        if (pts_[0] - pts_[-1]).Length < 0.15: pts_, own_ = pts_[:-1], own_[:-1]
        X_ = np.array([[v_.x, v_.y, v_.z] for v_ in pts_]); m_ = len(X_)
        # sides from the snap runs: two long runs on two different neighbours (a wall corner between two wall ends,
        # the nose corner between the lip and the tongue wall) = two Coons sides, each the neighbour's REAL edge
        # sampled exactly; the outline between them = the other two sides
        st_ = next((i for i in range(m_) if own_[i] != own_[i - 1]), 0); rr_ = []
        for k_ in range(m_):
            i = (st_ + k_) % m_
            if rr_ and own_[i] == rr_[-1][0]: rr_[-1][1].append(i)
            else: rr_.append([own_[i], [i]])
        lng = sorted([r for r in rr_ if r[0] != 'free' and len(r[1]) >= 5], key=lambda r: -len(r[1]))[:2]   # the two longest
        cs_ = None
        if len(lng) == 2 and lng[0][0] != lng[1][0]:
            for o_, idx in lng:
                mid = X_[idx[len(idx) // 2]]
                e_ = min((e for e in own[o_].Edges if e.Length > 0.2), key=lambda e: e.distToShape(Part.Vertex(App.Vector(*mid)))[0])
                ua = e_.Curve.parameter(App.Vector(*X_[idx[0]])); ub = e_.Curve.parameter(App.Vector(*X_[idx[-1]]))
                for k_, uu in zip(idx, np.linspace(ua, ub, len(idx))):
                    q_ = e_.Curve.value(uu); X_[k_] = [q_.x, q_.y, q_.z]
            cs_ = sorted([lng[0][1][0], lng[0][1][-1], lng[1][1][0], lng[1][1][-1]])
            if len(set(cs_)) < 4: cs_ = None
        face = None
        if cs_ is not None and all(o_.startswith('hoodnb:') for o_, _ in lng):
            rA = lng[0] if cs_[0] in lng[0][1] else lng[1]; rB = lng[1] if rA is lng[0] else lng[0]
            if not ((cs_[1] - cs_[0]) % m_ == len(rA[1]) - 1 and cs_[2] in rB[1]): print('    round: runs out of order', cs_, len(rA[1]), m_)
            if (cs_[1] - cs_[0]) % m_ == len(rA[1]) - 1 and cs_[2] in rB[1]:          # both runs in index order
                face, th_ = round_corner(X_, cs_, own[rA[0]], own[rB[0]])
                if face is not None: ncorner = f'G1 round ({th_:.0f} deg)'
        if face is None: face, ncorner = coons_face(X_, cs=cs_)
        pts_ = [App.Vector(*q) for q in X_]
        if cf.get('inner'): print('   ', p['name'], f"{len(cf['inner'])} Kunos inside vertices off the patch:",
                                  ' '.join(f'{face.distToShape(Part.Vertex(App.Vector(*q)))[0]:.2f}' for q in cf['inner']), flush=True)
        gap = max(face.distToShape(Part.Vertex(v_))[0] for v_ in pts_)
    except Exception as ex:
        print(p['name'], 'corner fill failed:', ex, flush=True); continue
    shapes.append(face); built[p['name']] = face
    m = MeshPart.meshFromShape(Shape=face, MaxLength=1.0); pts, fc = m.Topology
    if not fc:
        m = MeshPart.meshFromShape(Shape=face, LinearDeflection=0.01, AngularDeflection=0.1, Relative=False); pts, fc = m.Topology
    if not fc:
        print(p['name'], 'corner fill mesh failed', flush=True); continue
    sf = face.Surface; nn = []
    for q in pts:
        u_, v_ = sf.parameter(q); n_ = sf.normal(u_, v_); nn.append([n_.x, n_.y, n_.z])
    nn = np.array(nn); nn *= np.sign((nn @ np.array(cf['normal'])).mean() or 1.0)
    mesh[p['name'] + '_P'] = np.array([[q.x, q.y, q.z] for q in pts]) / 1000.0; mesh[p['name'] + '_F'] = np.array(fc, int)
    normals[p['name']] = nn
    print(f"{p['name']:24s} CORNER area {face.Area:.1f} mm2 (Kunos {cf['area']:.1f})  outline {len(pts_)} pts, {nsn} snapped, {ncorner} sides;"
          f" boundary off the filling {gap:.3f} mm  {time.time() - tf:.1f} s", flush=True)
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
# mirrored faces (symmetric panels: the right half's returns = the left half's, mirrored x -> -x; built the same way
# from mirrored data, the two halves still came out up to 2.6 mm apart at the strip ends: the end choices depend on
# the outline's direction): shape, mesh and normals of 'mirror_of' mirrored in the plane x = 0
for p in res:
    src = p.get('mirror_of')
    if not src or src not in built or (ONLY and not any(k in p['name'] for k in ONLY.split(','))): continue
    sh_ = built[src].mirror(App.Vector(0, 0, 0), App.Vector(1, 0, 0))
    built[p['name']] = sh_; shapes.append(sh_)
    if src + '_P' in mesh:
        mesh[p['name'] + '_P'] = mesh[src + '_P'] * np.array([-1.0, 1.0, 1.0]); mesh[p['name'] + '_F'] = mesh[src + '_F'][:, [0, 2, 1]].copy()
        if src in normals: normals[p['name']] = normals[src] * np.array([-1.0, 1.0, 1.0])
    print(f"{p['name']:24s} MIRROR of {src}", flush=True)
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

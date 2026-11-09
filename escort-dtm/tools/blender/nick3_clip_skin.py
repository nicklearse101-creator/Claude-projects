"""nick3_clip_skin.py - v36.  Shoulder 'skin': carries the flare surface forward to the clip's crest line.

The flare (nick3_side) ends 33-64 mm behind the rounded crest of the front clip's shoulder.  The skin is a LOFTED STRIP in that gap:
  front boundary = the measured 1 mm crest polyline (plan error 0 by construction),
  rear boundary  = crest + (flare front edge distance + OV) along the crest normal, i.e. it runs OV under the flare,
  columns at ~2 mm along the crest, rows packed toward the crest (0.02 R ... R) so the crisp edge is well resolved.
Heights are the clip's top surface (ray cast), lifted by `offset` (1.5 mm) along the clip normal, ramping down over `feather` (8 mm) to `floor` (0.6 mm) at every free edge (floor > 0 keeps the clip's facets from poking through the crest edge), and
the clip's custom normals are interpolated onto each skin vertex (so the shading is the clip's own).  Flare material, UV (0.311, 0.26).
The CLIP IS NEVER MODIFIED.  Left = +X; the right side uses the mirrored crest (x -> -x).
Inputs (bpy.app.driver_namespace): crestP (Nx2, 1 mm), crestSs (flare-edge distance behind crest, m)."""
import bpy, bmesh, numpy as np
from mathutils import Vector
from mathutils.interpolate import poly_3d_calc

def sst(t):
    t = max(0.0, min(1.0, t)); return t*t*(3-2*t)

def gsm(A, sig):
    r = int(3*sig); w = np.exp(-0.5*(np.arange(-r, r+1)/sig)**2); w /= w.sum()
    B = np.pad(A, ((r, r), (0, 0)), mode='reflect', reflect_type='odd')
    return np.stack([np.convolve(B[:, i], w, mode='valid') for i in range(A.shape[1])], 1)

def crest_frame(P, Ss, side, sigma=8.0):
    """smooth the measured crest (removes the facet zig-zag at the wing end), return P, T, NR in the side's frame; NR points toward the flare"""
    Q = gsm(P, sigma); Q[0] = P[0]; Q[-1] = P[-1]
    dev = float(np.linalg.norm(Q-P, axis=1).max())
    T = np.gradient(Q, axis=0); T /= np.linalg.norm(T, axis=1)[:, None]
    NR = np.stack([-T[:, 1], T[:, 0]], 1)
    if side < 0:
        m = np.array([-1.0, 1.0]); Q = Q*m; T = T*m; NR = NR*m
    return Q, T, NR, dev

TFR = np.array([0, .02, .05, .10, .17, .26, .36, .47, .58, .69, .80, .90, 1.0])

def build_strip(clip, side, P, NR, Ss, T=None, env=0.0015, OV=0.014, offset=0.0015, floor=0.0006, feather=0.008, step=2, name='SKIN', mat=None, drop_miss=True, fold_drop=True):
    me = clip.data; cn = me.corner_normals
    if T is None: T = np.gradient(P, axis=0); T = T/np.linalg.norm(T, axis=1)[:, None]
    idx = list(range(0, len(P), step))
    if idx[-1] != len(P)-1: idx.append(len(P)-1)
    nc, nr = len(idx), len(TFR)
    verts = []; vn = []
    def sample(x, y):
        ok, loc, n, fi = clip.ray_cast(Vector((float(x), float(y), 1.0)), Vector((0, 0, -1)))
        if not ok: return None
        poly = me.polygons[fi]; co = [me.vertices[v].co for v in poly.vertices]
        w = poly_3d_calc(co, loc); nn = Vector((0, 0, 0))
        for wi, li in zip(w, range(poly.loop_start, poly.loop_start+poly.loop_total)): nn += wi*cn[li].vector
        nn = nn.normalized()
        if nn.z < 0: nn = -nn      # the ray came from above: a down-facing normal is a back-face hit on a thin clip rim, flip it
        return loc, nn
    S = {}
    miss = []
    for a, k in enumerate(idx):
        R = Ss[k]+OV
        for i, t in enumerate(TFR):
            q = P[k]+NR[k]*(t*R); r = sample(q[0], q[1])
            if r is None: miss.append((a, i))
            else:   # envelope: highest clip height within env mm along +-crest tangent and rearward, so steps/slivers in the clip can't poke through the skin
                zz = r[0].z
                for d in (T[k], -T[k], NR[k]):
                    r2 = sample(q[0]+d[0]*env, q[1]+d[1]*env)
                    if r2 is not None and r2[0].z > zz: zz = r2[0].z
                r = (Vector((r[0].x, r[0].y, zz)), r[1])
            S[(a, i)] = r
    missset = set(miss)
    for (a, i) in miss:   # ray missed the clip (strip edge past the clip's top surface): borrow from the nearest sampled row in the same column, else the nearest column
        for da in (0, 1, -1, 2, -2, 3, -3):
            cand = [(abs(j-i), j) for j in range(nr) if 0 <= a+da < nc and S.get((a+da, j)) is not None]
            if cand:
                j = min(cand)[1]; S[(a, i)] = S[(a+da, j)]; break
    for a, k in enumerate(idx):
        R = Ss[k]+OV
        for i, t in enumerate(TFR):
            s = t*R; q = P[k]+NR[k]*s; r = S[(a, i)]
            if r is None: loc = Vector((q[0], q[1], 0.2)); n = Vector((0, 0, 1))
            else:
                loc, n = r
                if (a, i) in missset: loc = Vector((q[0], q[1], loc.z))
            dist = min(s, R-s, k*0.001, (len(P)-1-k)*0.001)
            verts.append(loc + n*(floor+(offset-floor)*sst(dist/feather))); vn.append(n)
    faces = []
    for a in range(nc-1):
        for i in range(nr-1):
            f = [a*nr+i, (a+1)*nr+i, (a+1)*nr+i+1, a*nr+i+1]
            if drop_miss and any(((v//nr, v % nr) in missset) for v in f): continue   # cells beyond the clip's rear edge: the flare itself is there
            ff = f[::-1] if side < 0 else f
            if fold_drop:   # rows of adjacent columns cross on the inside of a tight crest bend: the quad folds over (normal points down); drop it, the flare covers that area
                p0, p1, p2 = (Vector(verts[ff[0]]), Vector(verts[ff[1]]), Vector(verts[ff[2]]))
                p3 = Vector(verts[ff[3]])
                if ((p1-p0).cross(p2-p0) + (p2-p0).cross(p3-p0)).z < 0: continue
            faces.append(ff)
    used = sorted({v for f in faces for v in f}); remap = {v: k for k, v in enumerate(used)}
    verts = [verts[v] for v in used]; vn = [vn[v] for v in used]; faces = [[remap[v] for v in f] for f in faces]
    nm = bpy.data.meshes.new(name); nm.from_pydata([tuple(v) for v in verts], [], faces); nm.update()
    uv = nm.uv_layers.new(name='UVMap')
    for l in uv.data: l.uv = (0.311, 0.26)
    nm.polygons.foreach_set('use_smooth', [True]*len(nm.polygons))
    ln = [tuple(vn[l.vertex_index]) for l in nm.loops]
    nm.normals_split_custom_set(ln)
    if mat: nm.materials.append(mat)
    return nm, dict(verts=len(verts), faces=len(faces), miss=miss)

def make_ground(clip, skin_ob, name):
    """clip + skin as one height-field object (ray_cast returns the higher of the two). Must stay visible while it is used for ray casts."""
    bm = bmesh.new(); bm.from_mesh(clip.data); bm.from_mesh(skin_ob.data)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob); return ob

def join_into(flare_ob, skin_ob, flare_cn=None):
    """append the skin shell to the flare mesh; flare loops keep their current normals (or flare_cn if given), skin loops keep the clip-interpolated normals"""
    fm = flare_ob.data; sm = skin_ob.data
    fcn = flare_cn if flare_cn is not None else [tuple(l.vector) for l in fm.corner_normals]
    cn = list(fcn) + [tuple(l.vector) for l in sm.corner_normals]
    bm = bmesh.new(); bm.from_mesh(fm); bm.from_mesh(sm); bm.to_mesh(fm); bm.free(); fm.update()
    fm.polygons.foreach_set('use_smooth', [True]*len(fm.polygons))
    fm.normals_split_custom_set(cn)

def _interp_n(ob, x, y):
    ok, loc, n, fi = ob.ray_cast(Vector((float(x), float(y), 1.0)), Vector((0, 0, -1)))
    if not ok: return None
    me = ob.data; poly = me.polygons[fi]; cn = me.corner_normals
    w = poly_3d_calc([me.vertices[v].co for v in poly.vertices], loc); nn = Vector((0, 0, 0))
    for wi, li in zip(w, range(poly.loop_start, poly.loop_start+poly.loop_total)): nn += wi*cn[li].vector
    return loc.z, nn.normalized()

def soft_normals(flare_ob, ground_ob, skin_ob, clip, dmax=0.008):
    """Return corner normals for the flare (before join): where the flare top surface is within dmax of the ground (clip+strip) its normal is
    blended toward the ground's own (strip/clip) normal, weight 1 at the ground -> 0 at dmax, so the flare/strip meeting has no dark seam."""
    me = flare_ob.data; cn = [l.vector.copy() for l in me.corner_normals]; vw = {}
    for v in me.vertices:
        gz = ground_ob.ray_cast(Vector((v.co.x, v.co.y, 1.0)), Vector((0, 0, -1)))
        if not gz[0]: continue
        d = v.co.z - gz[1].z
        if d < -0.003 or d > dmax: continue
        sk_ = _interp_n(skin_ob, v.co.x, v.co.y); cl_ = _interp_n(clip, v.co.x, v.co.y) if clip is not None else None
        g = sk_ if (sk_ and (not cl_ or sk_[0] >= cl_[0]-1e-6)) else cl_
        if g is None: continue
        vw[v.index] = (1.0 - sst(max(d, 0.0)/dmax), g[1])
    n = 0
    for l in me.loops:
        if l.vertex_index in vw:
            w, ng = vw[l.vertex_index]
            if cn[l.index].dot(Vector((0, 0, 1))) > 0.3:     # top-facing loops only
                cn[l.index] = (cn[l.index]*(1-w) + ng*w).normalized(); n += 1
    return [tuple(c) for c in cn], n

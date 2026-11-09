"""nick3_v36_flow.py - v36c.  The flare's arch surface FLOWS forward to the clip crest (no flat shelf).

v36a/b filled the gap between the flare's old edge and the crest with a strip lying on the clip's shoulder (a flat shelf, ~0.4 slope) and then eased the
steep flare ramp (slope 1.5-2) down onto it, so the arch ended in a crease and a flat smudge.  Here the surface in the gap is a cubic Hermite
(per crest station k, along the crest normal r, 0 = crest, Rb = S + 30 mm behind it):
    z(0)  = clip height at the crest,   z'(0)  = the clip's own slope just behind the crest (so the flare leaves the crest tangent to the clip's shoulder),
    z(Rb) = the pristine flare's height, z'(Rb) = the pristine flare's slope (so it joins the arch with no kink).
It is a concave-up sweep that never goes below the clip.  The same surface drives (a) the lofted strip (r 0..S+14 mm) and (b) a vertical displacement of the
flare's top-surface vertices for r in 0..Rb (weighted by depth below the top, so the shell keeps its thickness), then a z-Laplacian pass removes the curvature
jump at Rb.  The clip is never modified.  Needs FLARE_V36pre_* (nick3_lip_warp.make_pre) and crest data (crest_L_1mm_ext.json)."""
import bpy, bmesh, sys, numpy as np
from mathutils import Vector
sys.path.insert(0, r'D:\Claude\escort_mk2_dtm\tools\blender')
import nick3_clip_skin as sk, nick3_clip_blend as cb, nick3_v36_build as bd

DRB = 0.030      # Rb = S + 30 mm
OV = 0.014
FLOOR = 0.0006
TUCK = 0.0025
MARGIN = 0.0012

def _ray(ob, x, y):
    ok, l, n, i = ob.ray_cast(Vector((float(x), float(y), 1.0)), Vector((0, 0, -1)))
    return l.z if ok else None

def _rmax(ob, x, y, T=None, NRv=None, d=0.0015):
    """clip height at (x,y) raised to the local max within d (plan, 4 neighbours): covers ridge/chord dips of the 2-5 mm facets"""
    zs = [_ray(ob, x, y)]
    for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d)): zs.append(_ray(ob, x+dx, y+dy))
    zs = [z for z in zs if z is not None]
    return max(zs) if zs else None

def herm(zc, sc, zf, sf, Rb, r):
    t = np.clip(r/Rb, 0.0, 1.0)
    return (2*t**3-3*t**2+1)*zc + (t**3-2*t**2+t)*Rb*sc + (-2*t**3+3*t**2)*zf + (t**3-t**2)*Rb*sf

def _fill(a):
    a = np.array(a, float); bad = np.isnan(a)
    if bad.all(): return a
    a[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), a[~bad]); return a

def _medg(a, w, sig):
    h = w//2; p = np.pad(a, (h, h), mode='edge'); m = np.array([np.median(p[i:i+w]) for i in range(len(a))])
    return sk.gsm(m[:, None], sig)[:, 0]

def stations(clip, pre, Q, NR, S):
    """per crest station: zc, sc (clip slope behind the crest), Rb, zf, sf (pristine flare height/slope at Rb)"""
    n = len(Q); zc = np.full(n, np.nan); sc = np.full(n, np.nan); zf = np.full(n, np.nan); sf = np.full(n, np.nan); Rb = S+DRB
    rs = np.arange(0.002, 0.0121, 0.002)
    for k in range(n):
        z0 = _ray(clip, *Q[k])
        if z0 is None: continue
        zc[k] = z0
        zz = [_ray(clip, *(Q[k]+NR[k]*r)) for r in rs]
        if all(z is not None for z in zz): sc[k] = np.polyfit(rs, np.array(zz)-z0, 1)[0]
        for dr in range(0, 11):                        # if the pristine flare is missing at Rb, back off 2 mm steps
            R = Rb[k]-dr*0.002
            za = _ray(pre, *(Q[k]+NR[k]*R)); zb = _ray(pre, *(Q[k]+NR[k]*(R-0.004))); zc2 = _ray(pre, *(Q[k]+NR[k]*(R+0.004)))
            if za is not None and zb is not None and zc2 is not None:
                Rb[k] = R; zf[k] = za; sf[k] = (zc2-zb)/0.008; break
    zc = _fill(zc); zf = _fill(zf)
    sc = np.clip(_medg(_fill(sc), 9, 4), 0.2, 1.5); sf = np.clip(_medg(_fill(sf), 9, 4), 0.2, 3.0)
    df = np.full(n, np.nan); sdf = np.full(n, np.nan)
    for k in range(n):
        p = Q[k]+NR[k]*Rb[k]; z0 = _ray(clip, *p); za = _ray(clip, *(p-NR[k]*0.004)); zb = _ray(clip, *(p+NR[k]*0.004))
        if z0 is not None and za is not None and zb is not None: df[k] = zf[k]-z0; sdf[k] = sf[k]-(zb-za)/0.008
    df = np.maximum(_medg(_fill(df), 9, 3), 0.004); sdf = np.clip(_medg(_fill(sdf), 9, 4), 0.0, 3.0)
    return dict(zc=zc, sc=sc, zf=zf, sf=sf, Rb=Rb, df=df, sdf=sdf)

TRIM = {}
CORN_R = 0.014
CORN_COLS = 8
R0 = 0.014      # the sweep leaves the clip's own surface 14 mm behind the crest (after the crest's rounded roll-off), tangent to it

def dfun(st, k, r):
    """height of the flowing surface ABOVE the clip at distance r behind the crest: cubic Hermite d(R0)=0, d'(R0)=0 (tangent to the clip) -> d(Rb)=df, d'(Rb)=sdf (the pristine flare's own ramp slope relative to the clip)"""
    Rb = st['Rb'][k]; L = max(Rb-R0, 0.02); t = float(np.clip((r-R0)/L, 0.0, 1.0))
    return (-2*t**3+3*t**2)*st['df'][k] + (t**3-t**2)*L*st['sdf'][k]

def strip_flow(clip, side, Q, NR, S, st, mat, name, step=2, a0_fixed=None):
    n = len(Q); idx = list(range(0, n, step))
    if idx[-1] != n-1: idx.append(n-1)
    nc, nr = len(idx), len(sk.TFR); verts = []
    for k in idx:
        R = S[k]+OV; a_ = idx.index(k); dl = 0.0
        if a0_fixed is not None and a_ >= a0_fixed:
            u = max(0.0, 1.0-(a_-a0_fixed)/CORN_COLS)          # rounded start corner: the crest edge retreats along the normal by a quarter-ellipse (radius CORN_R)
            dl = CORN_R*(1.0-np.sqrt(max(0.0, 1.0-u*u))) if u > 0 else 0.0
        elif a0_fixed is not None: dl = CORN_R
        for t in sk.TFR:
            r = dl+t*(R-dl); p = Q[k]+NR[k]*r
            zr = _ray(clip, p[0], p[1]); zm = _rmax(clip, p[0], p[1])
            if zr is None: zr = st['zc'][k]; zm = zr
            z = zr+max(dfun(st, k, r), 0.0)+FLOOR*(1.0-sk.sst(r/st['Rb'][k]))
            z = max(z, zm+FLOOR*(1.0-sk.sst(r/0.04)))
            z -= TUCK*sk.sst((r-(S[k]+OV-0.012))/0.012)       # last 12 mm of the strip dive 2.5 mm so its free rear edge is buried under the flare (no hairline)
            z = max(z, zr+0.0002)
            verts.append((p[0], p[1], z))
    faces = []
    for a in range(nc-1):
        for i in range(nr-1):
            f = [a*nr+i, (a+1)*nr+i, (a+1)*nr+i+1, a*nr+i+1]
            f = f[::-1] if side < 0 else f
            p0, p1, p2, p3 = (Vector(verts[j]) for j in f)
            if ((p1-p0).cross(p2-p0)+(p2-p0).cross(p3-p0)).z < 0: continue
            faces.append(f)
    # wing-end tail: the first columns are a thin (a few mm wide) sliver where the crest meets the clip's rear edge at an acute angle.
    # Cut columns until the strip is >= 60 % of its full width, and fade the next 6 columns (12 mm) down flush onto the clip (no thorn, no lump).
    cnt = np.zeros(nc-1)
    for f in faces: cnt[f[0]//nr] += 1
    a0 = int(np.argmax(cnt >= 0.6*cnt.max())) if cnt.max() > 0 else 0
    FADE = 6
    faces = [f for f in faces if f[0]//nr >= a0]
    for a in range(a0, min(a0+FADE+1, nc)):
        e = sk.sst((a-a0)/FADE)
        for i in range(nr):
            x, y, z = verts[a*nr+i]; zr = _ray(clip, x, y)
            if zr is not None: verts[a*nr+i] = (x, y, zr+FLOOR+(z-zr-FLOOR)*e)
    TRIM[side] = a0
    used = sorted({v for f in faces for v in f}); rm = {v: k for k, v in enumerate(used)}
    me = bpy.data.meshes.new(name); me.from_pydata([verts[v] for v in used], [], [[rm[v] for v in f] for f in faces]); me.update()
    uv = me.uv_layers.new(name='UVMap')
    for l in uv.data: l.uv = (0.311, 0.26)
    me.polygons.foreach_set('use_smooth', [True]*len(me.polygons))
    if mat: me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob); return ob

def blend_flare(fo, pre, clip, side, Q, T, NR, S, st):
    me = fo.data; n = len(Q); moved = 0; dzs = {}
    for v in me.vertices:
        x, y, z = v.co.x, v.co.y, v.co.z
        if x*side <= 0 or not (0.60 <= abs(x) <= 0.97 and -1.86 <= y <= -1.40): continue
        p = np.array([x, y]); k = int(np.argmin(np.linalg.norm(Q-p, axis=1))); dv = p-Q[k]
        along = float(dv@T[k]); r = float(dv@NR[k])
        if r < 0 or r > st['Rb'][k]: continue
        if (k == 0 or k == n-1) and abs(along) > 0.004: continue
        zt = _ray(pre, x, y)
        if zt is None or z > zt+0.002: continue
        wd = sk.sst(1.0-(zt-z)/0.02)
        if wd <= 0: continue
        zr = _ray(clip, x, y)
        if zr is None: continue
        u = sk.sst((r-(S[k]+0.002))/0.010)                  # flare sits 1.5 mm UNDER the strip in front of S+2 (its old front edge is buried), crossing up to +1.2 mm over it by S+12
        off = (-0.0015+(MARGIN+0.0015)*u)*sk.sst((st['Rb'][k]-r)/0.015)
        tgt = zr+max(dfun(st, k, r), 0.0)+off
        zm = _rmax(clip, x, y)
        if zm is not None: tgt = max(tgt, zm+0.0005)
        dzs[v.index] = wd*(tgt-zt)
    for i, d in dzs.items(): me.vertices[i].co.z += d
    me.update(); return len(dzs), (max(abs(d) for d in dzs.values()) if dzs else 0.0)

def run_flow(C, S_mm, smooth_iters=3):
    bd.cleanup(('SKIN_', 'GROUND_', 'FL_PRE_')); bd.reset36()
    clip = bpy.data.objects['NICK3_front_clip']; mat = bpy.data.materials['Material #25DQW']; S = bd.smooth_S(S_mm); info = {}
    out = {}
    for side, nm, sn in ((1, 'NICK3_side_L', 'L'), (-1, 'NICK3_side_R', 'R')):
        pre = bpy.data.objects.new('FL_PRE_'+sn, bpy.data.meshes['FLARE_V36pre_'+nm].copy()); bpy.context.scene.collection.objects.link(pre)
        bpy.context.view_layer.update()
        Q, T, NR, dev = sk.crest_frame(C, S, side, sigma=3.0)
        st = stations(clip, pre, Q, NR, S)
        skin = strip_flow(clip, side, Q, NR, S, st, mat, 'SKIN_'+sn)
        a0 = TRIM[side]; bpy.data.objects.remove(skin, do_unlink=True)
        skin = strip_flow(clip, side, Q, NR, S, st, mat, 'SKIN_'+sn, a0_fixed=a0)
        fo = bpy.data.objects[nm]; info['subdiv_'+sn] = cb.subdiv(fo)
        info['blend_'+sn] = blend_flare(fo, pre, clip, side, Q, T, NR, S, st)
        cb.smooth_flare(fo, side, smooth_iters)
        bpy.context.view_layer.update()
        info['cover_'+sn] = cb.cover(fo, side, clip, 0.0005)
        out[side] = (fo, skin, pre, st); GEO[side] = (Q, NR, S); GEO_ST[side] = st; GEO_T[side] = T
    for side, (fo, skin, pre, st) in out.items():
        cnl, nn = sk.soft_normals(fo, skin, skin, None); info.setdefault('softn', []).append(nn)
        sk.join_into(fo, skin, flare_cn=cnl)
    for o in list(bpy.data.objects):
        if o.name.startswith('GROUND_'): o.hide_viewport = True
        if o.name.startswith(('SKIN_', 'FL_PRE_')): bpy.data.objects.remove(o, do_unlink=True)
    return info, out


GEO = {}
GEO_ST = {}
GEO_T = {}

def check(side, step=2):
    """count plan points r = 2 mm .. S+10 mm behind the crest (2 mm grid) where the joined flare's top is not above the clip (hole) or is >6 mm above it"""
    clip = bpy.data.objects['NICK3_front_clip']; fo = bpy.data.objects['NICK3_side_L' if side > 0 else 'NICK3_side_R']
    Q, NR, S = GEO[side]; holes = 0; tot = 0; hi = 0; worst = []
    for k in range(0, len(Q), step):
        for r in np.arange(0.002, S[k]+0.010, 0.002):
            p = Q[k]+NR[k]*r; zc = _ray(clip, *p); zf = _ray(fo, *p)
            if zc is None: continue
            tot += 1
            if zf is None or zf < zc+0.0002: holes += 1; worst.append((k, round(r*1000), None if zf is None else round((zf-zc)*1000, 2)))
            elif zf-zc > 0.006: hi += 1
    return tot, holes, hi, worst[:10]


def _top_weight(fo, side, Q, T, NR, S, st, wing_box=(0.64, 0.84, -1.83, -1.62)):
    """per-vertex smoothing weight: 1 inside the blend (r in 0..Rb+10 mm) fading out, 0 at/near the crest boundary; wing-end box gets extra"""
    me = fo.data; n = len(Q); w = {}; wb = {}; wg = {}
    for v in me.vertices:
        x, y, z = v.co.x, v.co.y, v.co.z
        if x*side <= 0 or not (0.60 <= abs(x) <= 0.97 and -1.86 <= y <= -1.40): continue
        p = np.array([x, y]); k = int(np.argmin(np.linalg.norm(Q-p, axis=1))); dv = p-Q[k]; r = float(dv@NR[k])
        if r < 0.003 or r > st['Rb'][k]+0.012: continue
        if cb.wdepth(fo, x, y, z) < 0.5: continue
        w[v.index] = sk.sst(r/0.008)*sk.sst((st['Rb'][k]+0.012-r)/0.02)
        wg[v.index] = sk.sst((r-0.014)/0.016)*sk.sst((st['Rb'][k]+0.012-r)/0.02)
        bx0, bx1, by0, by1 = wing_box
        if bx0 <= abs(x) <= bx1 and by0 <= y <= by1:
            wb[v.index] = sk.sst((r-0.014)/0.016)*sk.sst((abs(x)-bx0)/0.02)*sk.sst((bx1-abs(x))/0.02)*sk.sst((y-by0)/0.02)*sk.sst((by1-y)/0.02)
    return w, wb, wg

def finish(side, clip, iters=10, wing_iters=30, fac=0.5):
    """smooth the arch->crest surface behind the crest roll-off (r > 14 mm; the crest boundary and the first 14 mm stay exactly on the clip), extra
    passes in the wing-end box, re-cover the clip, then derive normals from the smoothed geometry (weight = wg) so the clip-normal noise
    (the streaks) is gone while the crest edge keeps the clip's own normals."""
    nm = 'NICK3_side_L' if side > 0 else 'NICK3_side_R'; fo = bpy.data.objects[nm]; Q, NR, S = GEO[side]; st = GEO_ST[side]; T = GEO_T[side]
    w, wb, wg = _top_weight(fo, side, Q, T, NR, S, st)
    bm = bmesh.new(); bm.from_mesh(fo.data); bm.verts.ensure_lookup_table()
    bnd = {v.index for e in bm.edges if e.is_boundary for v in e.verts}
    for it in range(iters+wing_iters):
        new = {}
        for i, wi in wg.items():
            if i in bnd: continue
            ww = wi if it < iters else min(wb.get(i, 0.0), wi)
            if ww <= 0: continue
            v = bm.verts[i]; nb = [e.other_vert(v) for e in v.link_edges if e.other_vert(v).index in wg]
            if nb: new[i] = v.co.z+fac*ww*(sum(q.co.z for q in nb)/len(nb)-v.co.z)
        for i, z in new.items(): bm.verts[i].co.z = z
    bm.to_mesh(fo.data); bm.free(); fo.data.update(); bpy.context.view_layer.update()
    ncov = cb.cover(fo, side, clip, 0.0005)
    me = fo.data
    cn = [Vector(n.vector) for n in me.corner_normals]; vn = [v.normal.copy() for v in me.vertices]
    for l in me.loops:
        wi = wg.get(l.vertex_index, 0.0)
        if wi <= 0: continue
        g = vn[l.vertex_index]
        if g.z < 0: continue
        cn[l.index] = (cn[l.index]*(1-wi)+g*wi).normalized()
    me.normals_split_custom_set([tuple(c) for c in cn]); me.update()
    return dict(smoothed=len(wg), wing=len(wb), cover=ncov)


def fin_smooth(side, clip, box=(0.686, 0.742, -1.750, -1.668), iters=14, fac=0.5):
    """full 3-D Laplacian on the small fin at the flare's wing end (vertices > 3 mm over the clip inside box; boundary pinned), then re-cover the clip"""
    nm = 'NICK3_side_L' if side > 0 else 'NICK3_side_R'; fo = bpy.data.objects[nm]
    bm = bmesh.new(); bm.from_mesh(fo.data); bm.verts.ensure_lookup_table()
    bnd = {v.index for e in bm.edges if e.is_boundary for v in e.verts}; w = {}
    for v in bm.verts:
        x = abs(v.co.x); y = v.co.y
        if box[0] <= x <= box[1] and box[2] <= y <= box[3] and v.co.z > 0.2 and v.index not in bnd:
            zc = _ray(clip, v.co.x, y)
            if zc is not None and v.co.z-zc > 0.003:
                w[v.index] = sk.sst((x-box[0])/0.012)*sk.sst((box[1]-x)/0.012)*sk.sst((y-box[2])/0.012)*sk.sst((box[3]-y)/0.012)
    for it in range(iters):
        new = {}
        for i, wi in w.items():
            v = bm.verts[i]; nb = [e.other_vert(v) for e in v.link_edges]
            if nb: new[i] = v.co+fac*wi*(sum((q.co for q in nb), v.co*0)/len(nb)-v.co)
        for i, c in new.items(): bm.verts[i].co = c
    bm.to_mesh(fo.data); bm.free(); fo.data.update(); bpy.context.view_layer.update()
    return len(w)


def merge_pinch(side, dist=0.0008):
    """weld strip-island vertices closer than 0.8 mm (cells pinched to nothing where the crest curves; they showed as a hairline crease), then drop any extra face on a non-manifold edge"""
    fo = bpy.data.objects['NICK3_side_L' if side > 0 else 'NICK3_side_R']; bm = bmesh.new(); bm.from_mesh(fo.data); bm.verts.ensure_lookup_table()
    isl = set(); stack = list({v.index for e in bm.edges if e.is_boundary for v in e.verts})
    while stack:
        i = stack.pop()
        if i in isl: continue
        isl.add(i); stack += [e.other_vert(bm.verts[i]).index for e in bm.verts[i].link_edges if e.other_vert(bm.verts[i]).index not in isl]
    bmesh.ops.remove_doubles(bm, verts=[bm.verts[i] for i in isl], dist=dist)
    for e in list(bm.edges):
        if e.is_valid and len(e.link_faces) > 2:
            bmesh.ops.delete(bm, geom=[sorted(e.link_faces, key=lambda f: f.calc_area())[0]], context='FACES_ONLY')
    bm.to_mesh(fo.data); fo.data.update(); n = len(bm.verts); bm.free(); return n


def build_all(C, S_mm):
    """v36d: run_flow -> finish (smooth + normals) -> fin_smooth -> cover(1.2 mm) on both sides.  Returns info."""
    info, out = run_flow(C, S_mm, smooth_iters=3)
    clip = bpy.data.objects['NICK3_front_clip']; bpy.context.view_layer.update()
    for s in (1, -1):
        info['finish_%d' % s] = finish(s, clip)
        info['fin_%d' % s] = fin_smooth(s, clip)
        info['merge_%d' % s] = merge_pinch(s)
        info['cover12_%d' % s] = cb.cover(bpy.data.objects['NICK3_side_L' if s > 0 else 'NICK3_side_R'], s, clip, 0.0012)
    return info

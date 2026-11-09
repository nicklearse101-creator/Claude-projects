"""nick3_v36e_lip.py - v36e (run in Blender).  Front arch lip lower line: make the visible lip edge a true circle about the front wheel axis down to the clip bottom.

Measured on v36d (both sides identical): visible lip edge radius (verts with |x| .86-.915) = 295-298 mm for th<70 (th from straight up, forward positive),
jumps to 348 mm over th 70-80, is a perfect circle 348.3 mm for th 80-100, then TAPERS 348->358 mm to a pointed tip at th 112 where the flare is cut flat at z=.014.
The clip's own arch cut-out is an exact circle r=356.3 mm (z -0.07..+0.31).  Fix: no taper (edge stays on 348.3), and the lip is carried on down along the circle to the clip's
bottom (ZFLOOR) so it ends in line with the clip."""
import bpy, bmesh, math, numpy as np
from mathutils import Vector
YC, ZC = -1.2177, 0.1481
TH_T = [100, 104, 108, 112, 140]; R_T = [.3483, .3532, .3561, .3580, .3580]   # old lip edge radius vs th (measured)
RLIP = 0.3483
ZFLOOR = -0.068; NCUT = 20; RFULL = 0.372; RZERO = 0.430
def ss(t): t = max(0.0, min(1.0, t)); return t*t*(3-2*t)
def polar(y, z): dy = y-YC; dz = z-ZC; return math.hypot(dy, dz), math.degrees(math.atan2(-dy, dz))
def from_polar(r, th): t = math.radians(th); return YC - r*math.sin(t), ZC + r*math.cos(t)
def redge(th): return float(np.interp(th, TH_T, R_T))

def fix_side(ob, s):
    me = ob.data
    old = {}
    cn = [l.vector.copy() for l in me.corner_normals]
    for p in me.polygons:
        cen = tuple(round(c, 5) for c in p.center)
        for li in p.loop_indices: old[(me.loops[li].vertex_index, cen)] = cn[li]
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    # bottom polygon (the big flat cap at z=.014)
    cap = [f for f in bm.faces if len(f.verts) > 8 and all(v.co.z < 0.0165 and v.co.y < -1.5 for v in f.verts)]
    assert len(cap) == 1, len(cap)
    capf = cap[0]; bot = list(capf.verts)
    # step A: radial shift (theta fixed): lip edge r -> RLIP for th>=100
    nA = 0
    for v in bm.verts:
        x = v.co.x*s
        if x < 0.6 or v.co.y > -1.5 or v.co.z > 0.095: continue
        r, th = polar(v.co.y, v.co.z)
        if th < 100: continue
        re = redge(th); d = RLIP-re
        phi = 1.0-ss((r-(re+0.030))/0.05)
        if abs(d*phi) < 1e-6: continue
        r2 = r+d*phi; y, z = from_polar(r2, th); v.co.y = y; v.co.z = z; nA += 1
    # step B: stretch bottom verts down along their circles
    info = {}
    for b in bot:
        r, th = polar(b.co.y, b.co.z)
        w = 1.0 if r <= RFULL else 1.0-ss((r-RFULL)/(RZERO-RFULL))
        zb = b.co.z+w*(ZFLOOR-b.co.z)
        info[b] = (r, th, w, zb)
    # record upper partners (vertical edges from bottom verts to non-cap verts), BEFORE moving bottoms
    bs = set(bot); vedges = []
    for b in bot:
        for e in b.link_edges:
            o = e.other_vert(b)
            if o in bs: continue
            vedges.append((e, b, o))
    # triangulate cap first
    bmesh.ops.triangulate(bm, faces=[capf], quad_method='BEAUTY', ngon_method='EAR_CLIP')
    segs = []
    for e, b, o in vedges:
        r, th, w, zb = info[b]
        if w <= 0.0: continue
        cr = max(min((zb-ZC)/r, 1.0), -1.0); thn = math.degrees(math.acos(cr)); yb, zb2 = from_polar(r, thn)
        segs.append((e, b, o, (b.co.x, yb, zb2), r, thn))
    n0 = len(bm.verts)
    ed = [t[0] for t in segs]
    # move bottoms
    for e, b, o, pos, r, thn in segs: b.co.y = pos[1]; b.co.z = pos[2]
    # bottoms with w==0 untouched; those with w>0 but not in segs (no vertical edge) -> move too
    for b in bot:
        r, th, w, zb = info[b]
        if w > 0 and not any(t[1] is b for t in segs):
            cr = max(min((zb-ZC)/r, 1.0), -1.0); thn = math.degrees(math.acos(cr)); b.co.y, b.co.z = from_polar(r, thn)
    # segments for projection
    A = np.array([[o.co.x, o.co.y, o.co.z] for e, b, o, p, r, t in segs]); B = np.array([[b.co.x, b.co.y, b.co.z] for e, b, o, p, r, t in segs])
    res = bmesh.ops.subdivide_edges(bm, edges=ed, cuts=NCUT, use_grid_fill=True)
    bm.verts.index_update(); bm.verts.ensure_lookup_table(); new = [v for v in bm.verts if v.index >= n0]
    P = np.array([[v.co.x, v.co.y, v.co.z] for v in new])
    AB = B-A; L2 = (AB**2).sum(1)
    moved = 0; worst = 0.0
    for i, v in enumerate(new):
        p = P[i]; t = np.clip(((p-A)*AB).sum(1)/L2, 0, 1); q = A+t[:, None]*AB; d = np.linalg.norm(p-q, axis=1); k = int(d.argmin())
        if d[k] > 0.0006: continue
        f = float(t[k]); ra, tha = polar(A[k][1], A[k][2]); rb, thb = polar(B[k][1], B[k][2])
        r = ra+f*(rb-ra); th = tha+f*(thb-tha); y, z = from_polar(r, th); x = A[k][0]+f*(B[k][0]-A[k][0])
        worst = max(worst, abs(y-v.co.y)+abs(z-v.co.z)); v.co.x = x; v.co.y = y; v.co.z = z; moved += 1
    bm.normal_update()
    bm.to_mesh(me); bm.free(); me.update()
    return dict(shifted=nA, stretched=len(segs), new_verts=len(new), repositioned=moved, max_move_mm=round(worst*1000, 2)), old

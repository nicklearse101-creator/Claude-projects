"""nick3_lip_warp.py - v36 (WIP, run in Blender).  Moves the front arch lip of the NICK3 flare so its OUTER FACE ends exactly on the clip's
rear vertical edge ("corner line") and lies in the clip's side-wall plane, for th = 70..112 deg of the front arch (z .02-.225).

Why: measured at 1 mm, the flare lip front sat 30 mm behind the clip's rear vertical edge (rl .308-.326 vs the corner at r .357) and its outer x fell from
.916 to .870 toward the bottom (clip wall x .9233 -> .9158).  The ring loft's outer face ends at v=.04 of the lip->far segment (7.6 mm forward of the lip
circle), so the lip circle is aimed at corner_y + .04*(E.y - lip_y)  (LIPV).  Result (left side, 1 mm): flare outer x - clip wall x = 0.0 mm at the edge
(z=.12, .18), -1.1 mm at 2 mm in front, rolling inboard over the next 8 mm behind the edge (the lip rounding).

Needs corner_rows = array of (z, wall_x, corner_y) at 1 mm for z .020-.225 (clip wall x and the y where the clip's rear edge ends), measured from
NICK3_front_clip (ray casts: rear edge = last clip hit going -y along x=.915; wall x = first hit along -x at that y).  The in-session table was lost
when Blender died; re-measure with measure_corner() (UNTESTED until re-run) before using.
Operates on the pre-blend flare meshes 'FLARE_V34pre_NICK3_side_L/R' -> writes 'FLARE_V36pre_NICK3_side_L/R' (fake user); nick3_clip_blend.reset() must then
restore from those (v36)."""
import bpy, numpy as np, math
from mathutils import Vector

yc, zc, EY = -1.2177, 0.1481, -1.765      # front wheel axis (y,z); flare tip E.y
XO = [(-112,.740),(-110,.780),(-108,.850),(-105,.885),(-100,.905),(-95,.924),(-90,.926),(-85,.926),(-80,.926),(-75,.926),(-70,.926),(70,.925),(75,.921),(80,.918),(85,.917),(90,.916),(100,.912),(105,.900),(110,.880),(112,.870)]
RL = [(-112,.335),(-110,.307),(-105,.295),(55,.295),(60,.298),(70,.298),(75,.303),(80,.308),(85,.318),(90,.326),(95,.338),(100,.345),(105,.354),(110,.357),(112,.358)]
LIPV = 0.04      # ring_pts: outer face's rear end sits at v=.04 of the lip -> far segment
XREF = 0.74      # ring scale pivot (far edge x ~ .72-.75)

def itp(tab, th):
    if th <= tab[0][0]: return tab[0][1]
    for (a, va), (b, vb) in zip(tab[:-1], tab[1:]):
        if a <= th <= b: return va+(vb-va)*(th-a)/(b-a)
    return tab[-1][1]
def sst(t): t = max(0, min(1, t)); return t*t*(3-2*t)

def measure_corner(clip, z0=0.020, z1=0.225):
    """per 1 mm of z: the clip's outer side wall x and the y where the wall ends (its rear vertical edge, the corner line).
    Rays along -x at x=1.3 hit the wall; the last y that still hits is found by bisection to 0.01 mm.  (Verified: .9234,-1.5502 at z=.02 ... .9176,-1.5666 at z=.22.)
    The clip is mirror-exact here (L-R difference 0.0 mm), so the same table serves the right side."""
    def wall(y, z):
        ok, l, n, i = clip.ray_cast(Vector((1.3, y, z)), Vector((-1, 0, 0))); return l.x if ok else None
    rows = []
    for k in range(int(round((z1-z0)*1000))+1):
        z = z0+k*0.001; yh = -1.65; ym = -1.45
        if wall(yh, z) is None: continue
        for _ in range(16):
            m = (yh+ym)/2
            if wall(m, z) is None: ym = m
            else: yh = m
        rows.append((z, wall(yh, z), yh))
    return np.array(rows)

class Warp:
    def __init__(self, corner_rows):
        self.cr = np.asarray(corner_rows)
        self.cy = lambda z: float(np.interp(z, self.cr[:, 0], self.cr[:, 2]))
        self.wx = lambda z: float(np.interp(z, self.cr[:, 0], self.cr[:, 1]))
        self.THS = np.arange(60, 112.01, 0.5)
        self.RLN = np.array([max(itp(RL, t), itp(RL, t)+sst((t-70)/10.0)*(self.rl_corner(t)-itp(RL, t))) if t >= 70 else itp(RL, t) for t in self.THS])
    def rl_corner(self, th):
        s = math.sin(math.radians(th)); c = math.cos(math.radians(th)); lo, hi = 0.25, 0.45
        def f(r):
            yl = yc-r*s; return (yl+LIPV*(EY-yl))-self.cy(zc+r*c)
        for _ in range(60):
            m = (lo+hi)/2
            if f(m) > 0: lo = m
            else: hi = m
        return (lo+hi)/2
    @staticmethod
    def th_from_z(z):
        lo, hi = 62.0, 112.0; gf = lambda t: zc+itp(RL, t)*math.cos(math.radians(t))
        if z >= gf(lo): return lo
        if z <= gf(hi): return hi
        for _ in range(50):
            m = (lo+hi)/2
            if gf(m) > z: lo = m
            else: hi = m
        return (lo+hi)/2
    def apply(self, me, side):
        n = 0; st = [0, 0]
        for v in me.vertices:
            x = v.co.x*side; y = v.co.y; z = v.co.z
            if x <= XREF+0.01 or y > -1.40 or y < EY-0.002: continue
            th = self.th_from_z(z)
            if th < 70.0: continue
            rl_o = itp(RL, th); rl_n = float(np.interp(th, self.THS, self.RLN))
            yl_o = yc-rl_o*math.sin(math.radians(th)); zl_o = zc+rl_o*math.cos(math.radians(th))
            vv = (y-yl_o)/(EY-yl_o)
            if vv < -0.12 or vv > 1.0: continue
            yl_n = yc-rl_n*math.sin(math.radians(th)); zl_n = zc+rl_n*math.cos(math.radians(th))
            ny = yl_n+vv*(EY-yl_n); nz = zl_n+(z-zl_o)
            thc = min(th, 112.0); xo_o = itp(XO, thc); xo_n = max(xo_o, self.wx(zl_n)); k = (xo_n-XREF)/(xo_o-XREF)
            v.co.x = (XREF+(x-XREF)*k)*side; v.co.y = ny; v.co.z = nz; n += 1
            st[0] = max(st[0], abs(ny-y)); st[1] = max(st[1], abs(nz-z))
        me.update(); return n, [round(s*1000, 1) for s in st]

def make_pre(corner_rows):
    w = Warp(corner_rows); out = {}
    for side, nm in ((1, 'L'), (-1, 'R')):
        src = bpy.data.meshes['FLARE_V34pre_NICK3_side_'+nm]; name = 'FLARE_V36pre_NICK3_side_'+nm
        if name in bpy.data.meshes: bpy.data.meshes.remove(bpy.data.meshes[name])
        new = src.copy(); new.name = name; new.use_fake_user = True; out[nm] = w.apply(new, side)
    return out

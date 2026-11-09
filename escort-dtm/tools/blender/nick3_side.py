
"""nick3_side.py - NICK3 one-piece flared side (sill + both arches) built with the sill's ring-loft technique.
Arches = surface of revolution about the wheel axis: one 16-pt wedge ring (same family as the sill's MID ring) per angle step,
tapering to the tip at the ends. Measured from the previous arches: front r_lip .295 / r_far .42 / x_out .926 (centre -1.2177,.1481);
rear r_lip .305 / r_far .427 / x_out .939 (centre 1.1924,.0921). Left = +X, right mirrored.  UV = single body-paint texel."""
import bpy, bmesh, math
from mathutils import Vector
import nick3_sill as ns

MID = ns.MID
UVT = (0.311, 0.26)   # a flat paint texel of the BODY texture AO_BODY.dds (same material as the body: 'Material #25DQW'); was (0.21657872,0.12241337) in NICK3_KIT_ATLAS
def sstep(t):
    t=max(0.0,min(1.0,t)); return t*t*(3-2*t)
def lerp(a,b,t): return a+(b-a)*t

# Arch tables measured from the previous (v30) arches in 5-degree bins (theta deg, value). rl = lip radius (min r), rf = far radius,
# xo = outer x.  Interior values are the flat levels of the old arch (old surface was wavy +-5 mm, levelled here).
ARCH = {
 'front': dict(yc=-1.2177, zc=0.1481, sg=-1, th0=-112.0, th1=112.0,
   xo=[(-112,.740),(-110,.780),(-108,.850),(-105,.885),(-100,.905),(-95,.924),(-90,.926),(-85,.926),(-80,.926),(-75,.926),(-70,.926),(70,.925),
       (75,.921),(80,.918),(85,.917),(90,.916),(100,.912),(105,.900),(110,.880),(112,.870)],
   rl=[(-112,.335),(-110,.307),(-105,.295),(55,.295),(60,.298),(70,.298),(75,.303),(80,.308),(85,.318),(90,.326),(95,.338),(100,.345),(105,.354),(110,.357),(112,.358)],
   rf=[(-112,.360),(-110,.390),(-105,.417),(-100,.419),(-95,.421),(70,.421),(75,.420),(80,.418),(85,.407),(90,.395),(95,.381),(100,.373),(105,.365),(110,.362),(112,.360)]),
 'rear':  dict(yc=1.1924, zc=0.0921, sg=1, th0=-112.0, th1=100.0, tail=(10.0,0.012,0.02),
   xo=[(-112,.735),(-110,.760),(-108,.800),(-105,.850),(-100,.890),(-95,.915),(-90,.925),(-85,.926),(-80,.927),(-75,.928),(-70,.930),(-65,.931),(-60,.932),
       (-55,.935),(-50,.937),(-45,.939),(-20,.939),(-10,.936),(0,.935),(10,.933),(30,.932),(45,.930),(50,.926),(55,.922),(60,.915),(65,.912),
       (70,.908),(75,.904),(80,.899),(85,.894),(90,.874),(95,.833),(100,.762)],
   rl=[(-112,.340),(-110,.318),(-105,.305),(100,.305)],   # old arch dipped to .265 at the tail = touching the tyre (r .272); held at .305 here
   rf=[(-112,.365),(-110,.401),(-105,.427),(90,.427),(95,.412),(100,.382)]),
}
def interp_tab(tab,th):
    if th<=tab[0][0]: return tab[0][1]
    for (a,va),(b,vb) in zip(tab[:-1],tab[1:]):
        if a<=th<=b: return lerp(va,vb,(th-a)/(b-a))
    return tab[-1][1]

def ring_params(A,th):
    """returns r_lip, r_far, x_out at angle th (deg) from the measured tables"""
    return interp_tab(A['rl'],th), interp_tab(A['rf'],th), interp_tab(A['xo'],th)

# FIT ring (u along x from far edge xf to lip xo, v radial 0=lip r .. 1=far r). Fitted to the measured old arch:
# top slope falls linearly from r_far at the body to ~.31 (v~.12) at the lip, flat soffit at r_lip, 15 mm rounded lip tip.
FIT_TOP=[(0.00,1.00),(0.15,0.870),(0.35,0.690),(0.55,0.515),(0.75,0.340),(0.88,0.228),(0.96,0.135),(1.00,0.040)]
FIT_SOF=[(0.975,0.0),(0.85,0.0),(0.60,0.0),(0.35,0.0),(0.08,0.0)]
FIT_BUR=[(-0.07,0.333),(-0.05,0.733),(-0.02,0.947)]   # buried part: x offset from xf (m), v
def ring_pts(rl,rf,xo,xf,bs=1.0):
    """16 (x,r) points (same topology as the sill MID ring): 8 top, 5 soffit, 3 buried"""
    dx=xo-xf; out=[]
    for u,v in FIT_TOP: out.append((xf+u*dx, rl+v*(rf-rl)))
    for u,v in FIT_SOF: out.append((xf+u*dx, rl+v*(rf-rl)))
    for ox,v in FIT_BUR: out.append((xf+ox*bs, rl+v*(rf-rl)))   # bs<1 shortens the buried part (front blend: nothing must hang free behind the fender)
    return out

# Front-end blend (front arch only, +theta side): the far (top) line leaves the r_far circle at thb, sweeps forward and lands on the clip's top
# edge height by thm, then runs down inside the clip rear face at y=yt. Ring points run along lip->far segment, so the band closes the gap to
# the clip and replaces the old filler plate/strip.
FB = dict(thb=30.0, E=(-1.765,0.268), P1=(-1.558,0.4377), P2=(-1.665,0.359))   # far line = Bezier from the r_far circle (tangent) to the tip E, then runs forward at lip height. v34: E moved forward to the wing's lower front corner (y -1.765, z .268, measured) so the flare tip meets the wing/clip corner flush

FARX = None    # f(side,y,z)->body surface |x| at the flare far edge (set by the builder)
DRAPE = None   # set to f(x,y,z)->z by the builder: eases flare points that hover above the front clip's top down onto it (flush)
def make_drape(cliptop, off=0.004, fall=0.10, off_front=0.001, y_front=-1.77, ramp=0.06):
    """eases flare points that hover above the clip top down onto it. v34: the clearance above the clip is FEATHERED:
    off_front (1 mm) at the flare's front tip y_front, rising to off (4 mm) over `ramp` m, so the tip runs out flush with the clip (no ledge)."""
    def f(x,y,z):
        ct=cliptop(x,y)
        if ct is None: return z
        o=off_front+(off-off_front)*sstep((y-y_front)/ramp)
        d=z-(ct+o)
        if d<=0: return z
        return z-(1.0-sstep(d/fall))*d
    return f

def build_arch_bm(which, side, xfar_fn, step_deg=2.5, fb=None):
    A=ARCH[which]; bm=bmesh.new(); uv=bm.loops.layers.uv.new("UVMap")
    n=int(round((A['th1']-A['th0'])/step_deg)); ths=[A['th0']+(A['th1']-A['th0'])*i/n for i in range(n+1)]
    rings=[]
    if fb:
        rl0,rf0,_=ring_params(A,fb['thb']); sb=math.sin(math.radians(fb['thb'])); cb=math.cos(math.radians(fb['thb']))
        P0=(A['yc']+A['sg']*rf0*sb, A['zc']+rf0*cb)
        lo,hi=fb['thb'],110.0          # thm: angle where the lip height equals E.z
        for _ in range(60):
            mid=(lo+hi)/2
            if A['zc']+ring_params(A,mid)[0]*math.cos(math.radians(mid))>fb['E'][1]: lo=mid
            else: hi=mid
        thm=(lo+hi)/2
    for th in ths:
        rl,rf,xo=ring_params(A,th)
        tk=1.0
        if A.get('tail') and th<A['th0']+A['tail'][0]:
            tk=sstep((th-A['th0'])/A['tail'][0]); rf=lerp(rl+A['tail'][1],rf,tk)   # tail tapers to a small closed tip instead of a flat cap
        s=math.sin(math.radians(th)); c=math.cos(math.radians(th))
        Ly=A['yc']+A['sg']*rl*s; Lz=A['zc']+rl*c
        Fy=A['yc']+A['sg']*rf*s; Fz=A['zc']+rf*c
        if fb and th>fb['thb']:
            if th<=thm:
                t=(th-fb['thb'])/(thm-fb['thb']); a=(1-t)**3; b=3*(1-t)**2*t; c=3*(1-t)*t*t; e=t**3
                Fy=a*P0[0]+b*fb['P1'][0]+c*fb['P2'][0]+e*fb['E'][0]; Fz=a*P0[1]+b*fb['P1'][1]+c*fb['P2'][1]+e*fb['E'][1]
            else:
                Fy=fb['E'][0]; Fz=Lz
        xf=xfar_fn(Fy,Fz,th)
        if fb and FARX is not None and th>fb['thb']:
            fx=FARX(side,Fy,Fz)            # actual body (fender) surface x at the far point -> far edge sits just inside the body
            if fx is not None: xf=lerp(xf,fx-0.006,sstep((th-fb['thb'])/15.0))
        xo=max(xo,xf+0.012)
        if A.get('tail') and tk<1.0: xo=lerp(xf+A['tail'][2],xo,tk)
        bs=1.0
        if fb and th>fb['thb']: bs=1.0-0.8*sstep((th-fb['thb'])/15.0)
        pts=ring_pts(rl,rf,xo,xf,bs)          # (x, r) ; v = (r-rl)/(rf-rl)
        ring=[]
        for x,r in pts:
            v=(r-rl)/(rf-rl)
            Py=Ly+v*(Fy-Ly); Pz=Lz+v*(Fz-Lz)
            if fb and DRAPE is not None: Pz=DRAPE(side*x,Py,Pz)
            ring.append(bm.verts.new((side*x, Py, Pz)))
        rings.append(ring)
    m=len(MID)
    for a,b in zip(rings[:-1],rings[1:]):
        for i in range(m):
            j=(i+1)%m; bm.faces.new([a[i],a[j],b[j],b[i]])
    bm.faces.new(rings[0]); bm.faces.new(rings[-1][::-1])
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:])
    for f in bm.faces:
        for l in f.loops: l[uv].uv=UVT
    return bm

"""NICK3 exhaust: solid closed silencer + angled tailpipe (parametric, Blender).
World coordinates (m): car faces -Y, +Z up. Tailpipe is raked UP toward the rear by THETA
(= rear diffuser end-plate slope, 8.6 deg) so it follows the diffuser flow line.
"""
import math, bmesh, bpy
from mathutils import Vector

SEG = 24
AX, AZ = 0.0915, 0.0515          # barrel semi-axes (x, z)
CX, CZ = 0.3435, 0.0255          # barrel centre
Y_B0, Y_B1, Y_C1 = 1.433, 1.845, 1.915   # barrel start, barrel end / cone start, cone end
DOME = 0.028                      # front dome depth
PIPE_C = (0.340, 0.030)           # tailpipe centre at cone end
COLLAR_R = 0.0335
PIPE_R, PIPE_RI = 0.030, 0.0265
PIPE_END_Y = 2.085
RIM_DEPTH = 0.060
THETA = math.radians(8.6)

def sstep(t):
    t = max(0.0, min(1.0, t)); return t*t*(3-2*t)

def lerp(a, b, t): return a + (b-a)*t

def ring_pts(c, th, rx, rz):
    u = Vector((1, 0, 0)); w = Vector((0, -math.sin(th), math.cos(th)))
    return [c + u*(rx*math.cos(2*math.pi*k/SEG)) + w*(rz*math.sin(2*math.pi*k/SEG)) for k in range(SEG)]

def silencer_rings():
    """list of (centre, theta, rx, rz) from front dome to cone end; plus end centre/theta."""
    rings = []
    for deg in (80, 62, 44, 26, 10):
        p = math.radians(deg); f = math.cos(p)
        rings.append((Vector((CX, Y_B0 - DOME*math.sin(p), CZ)), 0.0, AX*f, AZ*f))
    rings.append((Vector((CX, Y_B0, CZ)), 0.0, AX, AZ))
    rings.append((Vector((CX, Y_B1, CZ)), 0.0, AX, AZ))
    N = 9; pos = Vector((CX, Y_B1, CZ)); prev_th = 0.0
    for i in range(1, N+1):
        t = i/N; th = THETA*sstep(t); e = sstep(t)
        dy = (Y_C1 - Y_B1)/N
        d = (th+prev_th)/2; pos = pos + Vector((0, dy, dy*math.tan(d)))
        prev_th = th
        # lateral blend of the centre onto the tailpipe centre
        cc = Vector((lerp(CX, PIPE_C[0], e), pos.y, pos.z + (lerp(0, 0, e))))
        rings.append((cc, th, lerp(AX, COLLAR_R, e), lerp(AZ, COLLAR_R, e)))
    return rings

def _loop(bm, pts): return [bm.verts.new(p) for p in pts]

def _bridge(bm, a, b):
    n = len(a)
    for k in range(n):
        bm.faces.new((a[k], a[(k+1) % n], b[(k+1) % n], b[k]))

def _fan(bm, loop, centre_vert, flip=False):
    n = len(loop)
    for k in range(n):
        f = (centre_vert, loop[(k+1) % n], loop[k]) if not flip else (centre_vert, loop[k], loop[(k+1) % n])
        bm.faces.new(f)

def _finish(bm, split_deg=50):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ang = math.radians(split_deg)
    sharp = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > ang]
    bmesh.ops.split_edges(bm, edges=sharp)
    # cylindrical UVs
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for l in f.loops:
            v = l.vert.co; l[uv].uv = (0.5 + 0.0*v.x, 0.5)
    for f in bm.faces: f.smooth = True

def build_silencer():
    bm = bmesh.new(); R = silencer_rings()
    tip = bm.verts.new((CX, Y_B0 - DOME, CZ))
    loops = [_loop(bm, ring_pts(*r)) for r in R]
    _fan(bm, loops[0], tip, flip=True)
    for a, b in zip(loops, loops[1:]): _bridge(bm, a, b)
    c, th, rx, rz = R[-1]
    endc = bm.verts.new(c); _fan(bm, loops[-1], endc)
    _finish(bm); return bm

def pipe_axis():
    c, th, rx, rz = silencer_rings()[-1]
    return Vector((PIPE_C[0], c.y, c.z)), THETA

def build_pipe():
    bm = bmesh.new(); P0, th = pipe_axis(); d = Vector((0, math.cos(th), math.sin(th)))
    L = (PIPE_END_Y - P0.y)/math.cos(th)
    def at(s): return P0 + d*s
    spec = [(-0.012, PIPE_R), (0.0, PIPE_R), (L*0.5, PIPE_R), (L, PIPE_R)]
    loops = [_loop(bm, ring_pts(at(s), th, r, r)) for s, r in spec]
    for a, b in zip(loops, loops[1:]): _bridge(bm, a, b)
    # rim + inner wall + inner cap
    rim_in = _loop(bm, ring_pts(at(L), th, PIPE_RI, PIPE_RI)); _bridge(bm, loops[-1], rim_in)
    inner_back = _loop(bm, ring_pts(at(L-RIM_DEPTH), th, PIPE_RI, PIPE_RI)); _bridge(bm, rim_in, inner_back)
    cap = bm.verts.new(at(L-RIM_DEPTH)); _fan(bm, inner_back, cap)
    st = bm.verts.new(at(-0.012)); _fan(bm, loops[0], st, flip=True)
    _finish(bm); return bm

"""Extend the front clip side walls rearward so the front moulding meets the wheel arch.

Starts from mesh data `OLD_NICK3_front_clip_pre_rearcap` (clip with an open rear edge at y = -1.68).
 1. the rear boundary loop on each side is extruded rearward in N rows, x unchanged (the wall keeps its
    profile), y running out to a circle of radius R_W about the wheel centre (so the opening edge follows the tyre)
 2. bottom edge is lowered/raised row by row so it keeps sitting on the sloping splitter top
 3. the new rear loop is closed with a fill so the shell is watertight
"""
import bpy, bmesh, math, collections
from mathutils import Vector

CY, CZ = -1.218, 0.148
R_W = 0.356
Y0 = -1.68
ROWS = 10
BLEND = True          # bulge the wall's rear end outward so it meets the arch flare surface
S_U0 = 0.0           # blend starts this far along the extension (0..1)
TH_W0, TH_W1 = -26.0, -14.0
Z_F0, Z_F1 = 0.0, 0.335       # original wall height over which the blend fades out (top edge keeps its own x)   # below TH_W0 no blend; full blend above TH_W1 (deg)


def smooth(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def arch_table(arch_obj):
    """x of the arch's outer flare face where it crosses radius R_W, per 1-degree bin of arch angle."""
    mw = arch_obj.matrix_world
    bins = collections.defaultdict(list)
    for v in arch_obj.data.vertices:
        p = mw @ v.co
        th = math.degrees(math.atan2(p.z - CZ, -(p.y - CY))); r = math.hypot(p.y - CY, p.z - CZ)
        bins[round(th)].append((abs(p.x), r))
    tab = {}
    for k, pts in bins.items():
        pts.sort()
        best = None
        for (x0, r0), (x1, r1) in zip(pts, pts[1:]):
            if (r0 - R_W) * (r1 - R_W) <= 0 and r0 != r1 and x1 > 0.75:
                x = x0 + (x1 - x0) * (R_W - r0) / (r1 - r0)
                best = x if best is None else max(best, x)
        if best is not None: tab[k] = best
    return tab


def x_target(tab, th):
    ks = sorted(tab)
    if not ks: return None
    if th <= ks[0]: return tab[ks[0]]
    if th >= ks[-1]: return tab[ks[-1]]
    for a, b in zip(ks, ks[1:]):
        if a <= th <= b: return tab[a] + (tab[b] - tab[a]) * (th - a) / (b - a)


def zt(y):  # splitter top surface
    return -0.053 - 0.0232 * (y + 2.128)


def yt(z):
    d = R_W * R_W - (z - CZ) ** 2
    return CY - math.sqrt(max(d, 1e-6))


def build(obj, old_mesh, skirt_clear=0.003, arch_obj=None):
    tab = arch_table(arch_obj) if (BLEND and arch_obj is not None) else {}
    mw = obj.matrix_world; mwi = mw.inverted()
    bm = bmesh.new(); bm.from_mesh(old_mesh)
    rear = [e for e in bm.edges if e.is_boundary and all(abs((mw @ v.co).y - Y0) < 0.006 for v in e.verts)]
    # split into connected loops (one per side)
    adj = collections.defaultdict(list)
    for e in rear:
        for v in e.verts: adj[v].append(e)
    seen = set(); loops = []
    for e in rear:
        if e in seen: continue
        st = [e]; seen.add(e); comp = []
        while st:
            c = st.pop(); comp.append(c)
            for v in c.verts:
                for n in adj[v]:
                    if n not in seen: seen.add(n); st.append(n)
        loops.append(comp)
    assert len(loops) == 2, len(loops)
    capfaces = []
    for comp in loops:
        cur = comp
        verts0 = {v: (mw @ v.co) for e in comp for v in e.verts}
        for i in range(1, ROWS + 1):
            u = i / ROWS
            res = bmesh.ops.extrude_edge_only(bm, edges=cur)
            geom = res['geom']
            nv = set(g for g in geom if isinstance(g, bmesh.types.BMVert))
            ne = [g for g in geom if isinstance(g, bmesh.types.BMEdge)]
            newedges = [e for e in ne if all(v in nv for v in e.verts)]
            # map new vert -> origin position via link to old vert
            origin = {}
            for v in nv:
                for e in v.link_edges:
                    w = e.other_vert(v)
                    if w not in nv: origin[v] = w
            for v in nv:
                w = origin[v]
                p = verts0.get(w)
                if p is None: p = verts0[w] = mw @ w.co  # (shouldn't happen)
                verts0[v] = p
            for v in nv:
                p = verts0[v]
                y = Y0 + (yt(p.z) - Y0) * u
                z = p.z
                if p.z < -0.03:  # keep bottom edge on the splitter
                    z = zt(y) - skirt_clear
                x = p.x
                if tab:
                    th = math.degrees(math.atan2(z - CZ, -(y - CY)))
                    xt = x_target(tab, th)
                    w = smooth((th - TH_W0) / (TH_W1 - TH_W0)) * smooth((u - S_U0) / (1 - S_U0)) * (1 - smooth((p.z - Z_F0) / (Z_F1 - Z_F0)))
                    if xt is not None:
                        sg = 1.0 if p.x >= 0 else -1.0
                        x = p.x + sg * max(0.0, xt - abs(p.x)) * w   # only ever add material (never dent the wall inward)
                v.co = mwi @ Vector((x, y, z))
            cur = newedges
        r = bmesh.ops.holes_fill(bm, edges=cur, sides=1000)
        capfaces += r['faces']
    for f in capfaces:
        nb = [g for e in f.edges for g in e.link_faces if g not in capfaces]
        if nb: f.material_index = nb[0].material_index
    bm.normal_update()
    # cap faces should face rearward (+y)
    flip = [f for f in capfaces if f.normal.y < 0]
    if flip: bmesh.ops.reverse_faces(bm, faces=flip)
    bmesh.ops.triangulate(bm, faces=capfaces)
    bm.normal_update()
    me = bpy.data.meshes.new("NICK3_front_clip_mesh_extended")
    bm.to_mesh(me); bm.free()
    for m in old_mesh.materials: me.materials.append(m)
    return me

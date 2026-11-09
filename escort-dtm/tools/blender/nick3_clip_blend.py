"""nick3_clip_blend.py - v35.  Makes the NICK3 flare (nick3_side) flow into the top of the FRONT CLIP (NICK3_front_clip) with no step.

The CLIP IS NEVER MODIFIED (it keeps its exact look and custom normals).  Only the main-model flare meshes are reshaped, inside ZONE:
  1. subdiv():  the flare's edges inside ZONE are cut 2x (3x density, ~5 mm) so the flare can follow the clip surface without chord error.
  2. ease():    every flare top-surface vertex whose height above the clip top is d (0 < d < W) is lowered to
                    clip + margin + (d - margin) * smoothstep(d / W)
                so the flare LEAVES the clip surface tangentially (ease-in) instead of ramping up ~55 deg right at the crossing.
                Vertices up to 6 mm below the clip are raised to clip + margin (flare always covers the clip by `margin`, no z-fight).
  3. smooth_flare(): a few z-only Laplacian passes on the flare top vertices in the zone (removes the ripples step 2 leaves).
  4. cover():   re-assert flare >= clip + margin (vertices only; uses ray_cast down onto the clip).
Vertices are selected softly by depth below the object's own top surface (wdepth), not by vertex normal (normals on the clip/flare are noisy
and gave folds), and faded in/out by zone_w().
Pristine inputs are kept as meshes 'CLIP_ORIG_v34' (fake user), 'FLARE_V34pre_NICK3_side_L/R': reset() restores them, then run pipeline().
Left = +X, right = -X.  Tried and rejected (see git/notes): smax fillet of both height fields (too weak), Gaussian concave-corner fillet that
lifts the clip (wrinkles/blisters on the clip), feathering the flare onto the clip with no margin (jagged intersection)."""
import bpy, bmesh, math
from mathutils import Vector

ZONE = dict(x0=0.62, x1=0.96, y0=-1.84, y1=-1.46)   # v36: widened to take in the shoulder skin (wing end y -1.793, corner x .912)

def sst(t):
    t = max(0.0, min(1.0, t)); return t*t*(3-2*t)

def zone_w(x, y, Z=ZONE):
    ax = abs(x)
    wx = sst((ax-Z['x0'])/0.04) * sst((Z['x1']-ax)/0.03)
    wy = sst((y-Z['y0'])/0.03) * sst((Z['y1']-y)/0.05)
    return wx*wy

def _inbox(v):
    return ZONE['x0'] <= abs(v.co.x) <= ZONE['x1'] and ZONE['y0'] <= v.co.y <= ZONE['y1']

def wdepth(ob, x, y, z, fall=0.02):
    """1 on the object's visible top surface at (x,y), fading to 0 `fall` m below it; 0 if above/no hit"""
    ok, l, n, i = ob.ray_cast(Vector((x, y, 1.0)), Vector((0, 0, -1)))
    if not ok: return 0.0
    d = l.z - z
    if d < -0.002: return 0.0
    return sst(1.0 - max(d, 0.0)/fall)

def reset():
    bpy.data.objects['NICK3_front_clip'].data = bpy.data.meshes['CLIP_ORIG_v34'].copy()
    for n in ('NICK3_side_L', 'NICK3_side_R'):
        bpy.data.objects[n].data = bpy.data.meshes['FLARE_V34pre_' + n].copy()

def subdiv(fo, cuts=2):
    me = fo.data; bm = bmesh.new(); bm.from_mesh(me)
    ed = [e for e in bm.edges if _inbox(e.verts[0]) and _inbox(e.verts[1])]
    bmesh.ops.subdivide_edges(bm, edges=ed, cuts=cuts, use_grid_fill=True, use_smooth_even=False)
    bm.to_mesh(me); bm.free(); me.update(); return len(me.vertices)

def ease(fo, side, clip, W=0.035, margin=0.0010, under=0.006):
    me = fo.data; plan = {}
    for v in me.vertices:
        x, y, b = v.co.x, v.co.y, v.co.z
        if x*side <= 0: continue
        w = zone_w(x, y)
        if w <= 0: continue
        wd = wdepth(fo, x, y, b)
        if wd <= 0: continue
        ok, l, n, i = clip.ray_cast(Vector((x, y, 1.0)), Vector((0, 0, -1)))
        if not ok: continue
        a = l.z; d = b - a
        if d < -under or d >= W: continue
        tgt = a + margin + (max(d, margin)-margin)*sst(max(d, 0.0)/W)
        wt = 1.0 if d >= margin else sst((d+under)/(margin+under))
        plan[v.index] = b + w*wd*wt*(tgt-b)
    for i, z in plan.items(): me.vertices[i].co.z = z
    me.update(); return len(plan)

def smooth_flare(fo, side, iters=3, fac=0.5):
    me = fo.data; bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); act = {}
    for v in bm.verts:
        if v.co.x*side > 0:
            w = zone_w(v.co.x, v.co.y)
            if w > 0.05:
                w *= wdepth(fo, v.co.x, v.co.y, v.co.z)
                if w > 0.05: act[v.index] = w
    for _ in range(iters):
        new = {}
        for i, w in act.items():
            v = bm.verts[i]; nb = [e.other_vert(v) for e in v.link_edges]
            if nb: new[i] = v.co.z + fac*w*(sum(n.co.z for n in nb)/len(nb) - v.co.z)
        for i, z in new.items(): bm.verts[i].co.z = z
    bm.to_mesh(me); me.update(); bm.free()

def cover(fo, side, clip, margin=0.0010, band=0.012, ramp=0.008):
    me = fo.data; plan = {}
    for v in me.vertices:
        x, y, b = v.co.x, v.co.y, v.co.z
        if x*side <= 0: continue
        w = zone_w(x, y)
        if w <= 0: continue
        w *= wdepth(fo, x, y, b)
        if w <= 0: continue
        ok, l, n, i = clip.ray_cast(Vector((x, y, 1.0)), Vector((0, 0, -1)))
        if not ok: continue
        a = l.z; tgt = a + margin
        if b >= tgt: continue
        wt = sst((b-(a-band))/ramp)*w
        if wt > 0: plan[v.index] = b + wt*(tgt-b)
    for i, z in plan.items(): me.vertices[i].co.z = z
    me.update(); return len(plan)

def pipeline(W=0.035, margin=0.0010, smooth_iters=3, grounds=None):
    """grounds: optional {1: obj, -1: obj} height-field objects to ease/cover over (v36: clip + shoulder skin joined). Default: the clip."""
    reset()
    clip = bpy.data.objects['NICK3_front_clip']
    G = grounds or {1: clip, -1: clip}
    F = {1: bpy.data.objects['NICK3_side_L'], -1: bpy.data.objects['NICK3_side_R']}
    for s in F: subdiv(F[s])
    info = {'ease': [ease(F[s], s, G[s], W, margin) for s in F]}
    for s in F: smooth_flare(F[s], s, smooth_iters)
    info['cover'] = [cover(F[s], s, G[s], margin) for s in F]
    return info

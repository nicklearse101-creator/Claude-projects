"""nick3_v36_build.py - v36 driver: crest strips -> grounds -> flare ease/cover against clip+strip -> join strips into the flares.
Inputs (bpy.app.driver_namespace or D:\\Claude\\escort_mk2_dtm\\tools\\blender\\data\\crest_L_1mm.json):  crestP (Nx2, 1 mm, left side), S_raw (mm, flare edge distance behind crest).
The CLIP is never modified.  Flare pristine meshes: FLARE_V36pre_* if present, else FLARE_V34pre_*."""
import bpy, sys, json, importlib, numpy as np
sys.path.insert(0, r'D:\Claude\escort_mk2_dtm\tools\blender')
import nick3_clip_skin as sk, nick3_clip_blend as cb
importlib.reload(sk); importlib.reload(cb)

STRIP = dict(env=0.0, offset=0.0015, floor=0.0006, feather=0.008)   # env=0: no height envelope (the 1.5 mm envelope lifted the steep crest face 3-4 mm proud)
DATA = r'D:\Claude\escort_mk2_dtm\tools\blender\data'

def medf(a, w):
    h = w//2; p = np.pad(a, (h, h), mode='edge'); return np.array([np.median(p[i:i+w]) for i in range(len(a))])

def smooth_S(S_raw_mm):
    S = sk.gsm(medf(np.asarray(S_raw_mm)/1000.0, 15)[:, None], 6)[:, 0]
    return np.maximum(S, 0.03)

def reset36():
    for n in ('NICK3_side_L', 'NICK3_side_R'):
        src = 'FLARE_V36pre_' + n
        if src not in bpy.data.meshes: src = 'FLARE_V34pre_' + n
        bpy.data.objects[n].data = bpy.data.meshes[src].copy()
    bpy.data.objects['NICK3_front_clip'].data = bpy.data.meshes['CLIP_ORIG_v34'].copy()

def cleanup(prefixes=('SKIN_', 'GROUND_')):
    for o in list(bpy.data.objects):
        if o.name.startswith(prefixes): bpy.data.objects.remove(o, do_unlink=True)

def make_strips(C, S):
    clip = bpy.data.objects['NICK3_front_clip']; mat = bpy.data.materials['Material #25DQW']; out = {}
    for side, n in ((1, 'SKIN_L'), (-1, 'SKIN_R')):
        Q, T, NR, dev = sk.crest_frame(C, S, side, sigma=3.0)
        me, info = sk.build_strip(clip, side, Q, NR, S, T=T, name=n, mat=mat, **STRIP)
        ob = bpy.data.objects.new(n, me); bpy.context.scene.collection.objects.link(ob); out[side] = ob
    return out

def make_grounds(strips):
    clip = bpy.data.objects['NICK3_front_clip']
    return {s: sk.make_ground(clip, strips[s], 'GROUND_' + ('L' if s > 0 else 'R')) for s in strips}

def run(C, S_raw_mm, join=True, margin=0.0003):
    cleanup(); reset36()
    S = smooth_S(S_raw_mm); strips = make_strips(C, S); grounds = make_grounds(strips)
    bpy.context.view_layer.update()
    info = _pipeline(grounds, margin=margin)
    if join:
        clip = bpy.data.objects['NICK3_front_clip']
        info['slivers'] = [drop_slivers(bpy.data.objects[n], grounds[s]) for s, n in ((1, 'NICK3_side_L'), (-1, 'NICK3_side_R'))]
        for s, n in ((1, 'NICK3_side_L'), (-1, 'NICK3_side_R')):
            f = bpy.data.objects[n]; cnl, nn = sk.soft_normals(f, grounds[s], strips[s], clip); info.setdefault('softn', []).append(nn)
            sk.join_into(f, strips[s], flare_cn=cnl)
    for o in list(grounds.values()): o.hide_viewport = True
    return info, strips, grounds


def drop_slivers(flare_ob, ground_ob, amax=4e-6, aspect=8.0, dmax=0.004, box=(0.62, 0.96, -1.84, -1.46)):
    """delete needle faces (area < amax m^2 and longest-edge^2/area > aspect) that lie within dmax of the ground (clip+strip) in the zone:
    the strip beneath already covers them; they are what showed as a hairline dark wedge near the old flare tip."""
    import bmesh
    from mathutils import Vector
    me = flare_ob.data; bm = bmesh.new(); bm.from_mesh(me); kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        if not (box[0] <= abs(c.x) <= box[1] and box[2] <= c.y <= box[3]): continue
        a = f.calc_area()
        if a <= 0: continue
        L = max(e.calc_length() for e in f.edges)
        if not (a < amax and L*L/a > aspect): continue
        ok = True
        for v in f.verts:
            h = ground_ob.ray_cast(Vector((v.co.x, v.co.y, 1.0)), Vector((0, 0, -1)))
            if not h[0] or not (-0.003 <= v.co.z-h[1].z <= dmax): ok = False; break
        if ok: kill.append(f)
    n = len(kill); bmesh.ops.delete(bm, geom=kill, context='FACES'); bm.to_mesh(me); bm.free(); me.update(); return n

def _pipeline(grounds, W=0.035, margin=0.0010, smooth_iters=3):
    G = grounds; F = {1: bpy.data.objects['NICK3_side_L'], -1: bpy.data.objects['NICK3_side_R']}
    for s in F: cb.subdiv(F[s])
    info = {'ease': [cb.ease(F[s], s, G[s], W, margin) for s in F]}
    for s in F: cb.smooth_flare(F[s], s, smooth_iters)
    info['cover'] = [cb.cover(F[s], s, G[s], margin) for s in F]
    return info

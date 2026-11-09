"""Batch survey: how each car is built. One row per car, comparable across cars.

    python survey.py OUT.json CAR_DIR [CAR_DIR ...]

Per car:
  paint shell   - which meshes carry the car paint, their triangles, grid size, hard-edge %, quad %,
                  slivers, symmetry, unique-per-side UVs, texel density, paint texture size
  shape rules   - bend per smooth edge (p90), density on flat vs bent areas, normal weighting
  techniques    - alpha-tested cut-outs (grilles, meshes), real normal maps, tiling detail maps, AO-as-diffuse,
                  emissive lamps, skinned parts, glass layers, damage glass, rim blur, LOD ratios,
                  standard AC dummies present
"""
import sys, os, json, glob, re
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kn5full import KN5, dds_info
from analyze import mesh_stats
from shape_rules import analyse as bend_rules

PAINT_RE = re.compile(r'(car.?paint|carpaint|body|paint|ext_body|livery|skin)', re.I)
STD_DUMMIES = ['WHEEL_LF', 'SUSP_LF', 'DISC_LF', 'RIM_BLUR_LF', 'COCKPIT_HR', 'COCKPIT_LR', 'STEER_HR', 'STEER_LR',
               'DOOR_L', 'DOOR_R', 'MOTORHOOD', 'FRONT_BUMPER', 'REAR_BUMPER', 'REAR_WING', 'LIGHT_L', 'WIPER',
               'FLYCAM', 'DAMAGE_GLASS', 'SHIFT_HD', 'HANDBRAKE', 'DRIVER']


def quad_fraction(m, face_deg=30, shape_deg=60):
    """How much of a triangulated mesh pairs back into quads, like Blender's Tris to Quads:
    every shared edge is a candidate; score = coplanarity + how square the 4 corners are; greedy best-first."""
    P, I = m.pos, m.idx
    q = np.round(P / 1e-5).astype(np.int64)
    _, inv = np.unique(q, axis=0, return_inverse=True); T = inv.ravel()[I]
    V = np.zeros((T.max() + 1, 3)); V[T.ravel()] = P[I.ravel()]
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    cr = np.cross(b - a, c - a); fn = cr / np.maximum(np.linalg.norm(cr, axis=1), 1e-12)[:, None]
    edges = {}
    for f in range(len(T)):
        for k in range(3):
            u, v = T[f, k], T[f, (k + 1) % 3]
            edges.setdefault((min(u, v), max(u, v)), []).append((f, T[f, (k + 2) % 3]))
    cand = []
    for (u, v), fs in edges.items():
        if len(fs) != 2: continue
        (f1, w1), (f2, w2) = fs
        d = np.degrees(np.arccos(np.clip(fn[f1] @ fn[f2], -1, 1)))
        if d > face_deg: continue
        quad = [V[u], V[w1], V[v], V[w2]]
        dev = 0; ok = True
        for i in range(4):
            e1 = quad[i - 1] - quad[i]; e2 = quad[(i + 1) % 4] - quad[i]
            ang = np.degrees(np.arccos(np.clip(e1 @ e2 / max(np.linalg.norm(e1) * np.linalg.norm(e2), 1e-12), -1, 1)))
            if ang > 175: ok = False
            dev = max(dev, abs(ang - 90))
        if ok and dev < shape_deg: cand.append((d / face_deg + dev / shape_deg, f1, f2))
    cand.sort()
    used = np.zeros(len(T), bool); pairs = 0
    for _, f1, f2 in cand:
        if not used[f1] and not used[f2]:
            used[f1] = used[f2] = True; pairs += 1
    return 2 * pairs / max(len(T), 1)


def survey(car_dir):
    kn5s = sorted(glob.glob(os.path.join(car_dir, '*.kn5')), key=os.path.getsize, reverse=True)
    k = KN5(kn5s[0])
    tex = {n: dds_info(b) for n, b in k.textures.items()}
    car = os.path.basename(os.path.normpath(car_dir))
    r = dict(car=car, tris=int(sum(len(m.idx) for m in k.meshes)), meshes=len(k.meshes), materials=len(k.materials),
             textures=len(k.textures), texture_mb=round(sum(k.texture_sizes.values()) / 1e6, 1),
             root=k.nodes[0].name if k.nodes else '')
    # paint shell: damage_dirt shader is AC's car-paint shader; fall back on names
    def area(m):
        a, b, c = m.pos[m.idx[:, 0]], m.pos[m.idx[:, 1]], m.pos[m.idx[:, 2]]
        return 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1).sum()
    INSIDE = ('engine', 'bay', 'int_', 'interior', 'cockpit', 'under', 'dmg', 'damage', 'blur', 'shadow', 'boot_in')
    ext_m = [m for m in k.meshes if m.mat and 'COCKPIT' not in k.path_of(m.node)
             and not any(s in m.name.lower() for s in INSIDE)]
    mat_area = {}
    for m in ext_m: mat_area[m.mat.name] = mat_area.get(m.mat.name, 0) + area(m)
    # car paint = AC's damage_dirt paint shader, if it really covers the shell; else paint/body-named materials
    paint_mats = {n for n in mat_area if k.materials[[x.name for x in k.materials].index(n)].shader.endswith('damage_dirt')
                  and mat_area[n] > 0.5}
    if sum(mat_area.get(n, 0) for n in paint_mats) < 2:
        paint_mats = {n for n in mat_area if PAINT_RE.search(n) and mat_area[n] > 1.0}
    pm = [m for m in ext_m if m.mat.name in paint_mats]
    r['paint_materials'] = sorted(paint_mats)
    if pm:
        st = []
        for m in pm:
            t = m.mat.samplers.get('txDiffuse')
            st.append((m, mesh_stats(m, tex[t[1]][:2] if t and tex.get(t[1]) else None)))
        tris = np.array([s['tris'] for _, s in st]); w = tris / tris.sum()
        wavg = lambda key: float(np.nansum([w[i] * (s[key] if s.get(key) is not None else np.nan) for i, (_, s) in enumerate(st)]))
        r['paint_tris'] = int(tris.sum()); r['paint_meshes'] = len(pm)
        r['paint_area_m2'] = round(sum(s['area_m2'] for _, s in st), 2)
        r['paint_tri_per_m2'] = round(r['paint_tris'] / r['paint_area_m2']) if r['paint_area_m2'] > 0 else None
        r['paint_edge_mm'] = round(wavg('edge_mm_med'), 1)
        r['paint_hard_pct'] = round(100 * sum(s['hard_edge_verts'] for _, s in st) / max(sum(s['welded_verts'] for _, s in st), 1), 1)
        r['paint_slivers_pct'] = round(100 * sum(s['sliver_tris'] for _, s in st) / tris.sum(), 2)
        r['paint_texel_px_m'] = round(wavg('texel_px_per_m'))
        r['paint_split_ratio'] = round(wavg('split_ratio'), 3)
        big = max(pm, key=area)
        r['paint_main_mesh'] = big.name
        r['quad_pct_main'] = round(100 * quad_fraction(big), 1)
        br = bend_rules(big)
        r['bend_p90_deg'] = round(br['bend_p90'], 1)
        r['edge_flat_mm'] = br['len_mm@0-1deg'][0]; r['edge_bent_mm'] = br['len_mm@8-20deg'][0]
        r['normals'] = 'plain' if br['normal_dev_plain_med'] <= br['normal_dev_area_med'] else 'area-weighted'
        r['normal_dev_med'] = round(min(br['normal_dev_plain_med'], br['normal_dev_area_med']), 2)
        sym = [s['mirror_sym'] for _, s in st if s.get('mirror_sym') is not None]
        uvs = [s['mirror_uv_shared'] for _, s in st if s.get('mirror_uv_shared') is not None]
        r['paint_uv_shared_lr'] = round(float(np.mean(uvs)), 2) if uvs else None
        t = big.mat.samplers.get('txDiffuse')
        r['paint_texture'] = f"{t[1]} {tex[t[1]][0]}x{tex[t[1]][1]} {tex[t[1]][3]}" if t and tex.get(t[1]) else None
        r['paint_samplers'] = sorted(big.mat.samplers)
    # techniques inventory
    def tris_where(cond): return int(sum(len(m.idx) for m in k.meshes if m.mat and cond(m)))
    at = [m for m in k.meshes if m.mat and ('_AT' in m.mat.shader or m.mat.shader.endswith('AT') or m.mat.alpha_tested)]
    r['alpha_test_tris'] = tris_where(lambda m: m in at)
    r['alpha_test_meshes'] = sorted({m.name for m in at})[:25]
    def real_nm(m):
        t = m.mat.samplers.get('txNormal')
        return bool(t and tex.get(t[1]) and tex[t[1]][0] >= 128)
    r['normal_mapped_tris'] = tris_where(real_nm)
    r['normal_mapped_mats'] = sorted({m.mat.name for m in k.meshes if m.mat and real_nm(m)})[:25]
    r['detail_tiling_mats'] = sorted({m.mat.name for m in k.meshes if m.mat and 'txDetail' in m.mat.samplers
                                      and m.mat.props.get('detailUVMultiplier', (0,))[0] > 1})[:25]
    r['ao_like_textures'] = sorted({t for t in k.textures if re.search(r'(^|_)ao|occlu|shadow|bake', t, re.I)})
    r['emissive_mats'] = sorted({m.name for m in k.materials if m.props.get('ksEmissive', (0,))[0] > 0})[:20]
    r['skinned_meshes'] = sorted({m.name for m in k.meshes if m.skinned})
    shaders = {}
    for m in k.meshes:
        if m.mat: shaders[m.mat.shader] = shaders.get(m.mat.shader, 0) + len(m.idx)
    r['shaders'] = dict(sorted(shaders.items(), key=lambda x: -x[1]))
    r['windscreen_shader'] = 'ksWindscreen' in shaders
    r['broken_glass'] = 'ksBrokenGlass' in shaders
    names = [n.name for n in k.nodes]
    r['dummies'] = [d for d in STD_DUMMIES if any(n.startswith(d) for n in names)]
    r['rim_blur'] = any(n.startswith('RIM_BLUR') for n in names)
    r['lods'] = {os.path.basename(p): int(sum(len(m.idx) for m in KN5(p, load_textures=False).meshes))
                 for p in kn5s[1:] if 'collider' not in p.lower()}
    r['textures_top'] = sorted(((n, f'{t[0]}x{t[1]} {t[3]}') for n, t in tex.items() if t),
                               key=lambda x: -int(x[1].split('x')[0]))[:8]
    anims = os.path.join(car_dir, 'animations')
    r['animations'] = sorted(os.listdir(anims)) if os.path.isdir(anims) else []
    return r


if __name__ == '__main__':
    out = sys.argv[1]; res = []
    for c in sys.argv[2:]:
        try:
            res.append(survey(c)); print('ok', c, res[-1].get('paint_tris'), res[-1].get('quad_pct_main'))
        except Exception as e:
            import traceback; traceback.print_exc(); res.append({'car': os.path.basename(c), 'error': repr(e)})
    json.dump(res, open(out, 'w'), indent=1)

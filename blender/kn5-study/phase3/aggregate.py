"""Aggregate the 112-car study: groups, construction medians, technique frequency, spec accuracy per group."""
import json, re, os
import numpy as np
C = 'D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/'
M = {r['car']: r for r in json.load(open('measures_all3.json'))}
S = {r['car']: r for r in json.load(open('survey_all.json'))}
SP = json.load(open('specs_all.json'))
OPEN = set(open('open12.txt').read().split())

def author(car):
    try:
        t = open(C + car + '/ui/ui_car.json', encoding='utf-8', errors='ignore').read()
        m = re.search(r'"author"\s*:\s*"([^"]*)"', t); return m.group(1) if m else ''
    except Exception: return ''

def group(car):
    a = author(car)
    if car.startswith(('traffic_', 'nohesi_traffic')): return 'traffic'
    if car == 'vauxhall_nova_gte_1989': return 'ours'
    if car in OPEN: return 'open'
    if a == '' or 'kunos' in a.lower(): return 'kunos'
    return 'mod'

G = {c: group(c) for c in M}
out = {'groups': {}, 'spec': {}, 'tech': {}}
num = ['tris', 'paint_tris', 'paint_edge_mm', 'quad_pct_main', 'paint_hard_pct', 'paint_texel_px_m', 'bend_p90_deg', 'texture_mb']
for g in ('kunos', 'mod', 'open', 'traffic', 'ours'):
    cars = [c for c in M if G[c] == g]
    d = {'n': len(cars), 'cars': cars}
    for k in num:
        v = [S[c][k] for c in cars if isinstance(S[c].get(k), (int, float))]
        if v: d[k] = [round(float(np.percentile(v, p)), 1) for p in (25, 50, 75)]
    def frac(f):
        return round(100 * np.mean([bool(f(S[c])) for c in cars]), 0) if cars else None
    d['pct_plain_normals'] = frac(lambda s: s.get('normals') == 'plain')
    d['pct_unique_uv_lr'] = frac(lambda s: s.get('paint_uv_shared_lr') is not None and s['paint_uv_shared_lr'] < 0.2)
    d['pct_lods'] = frac(lambda s: s.get('lods'))
    d['pct_windscreen'] = frac(lambda s: s.get('windscreen_shader'))
    d['pct_broken_glass'] = frac(lambda s: s.get('broken_glass'))
    d['pct_rim_blur'] = frac(lambda s: s.get('rim_blur'))
    d['pct_alpha'] = frac(lambda s: s.get('alpha_test_tris', 0) > 0)
    d['pct_paint_nm'] = frac(lambda s: 'txNormal' in (s.get('paint_samplers') or []))
    d['pct_skin_1024'] = frac(lambda s: '1024x1024' in str(s.get('paint_texture')))
    d['pct_skin_2048'] = frac(lambda s: '2048x2048' in str(s.get('paint_texture')))
    d['dummies_med'] = float(np.median([len(S[c].get('dummies') or []) for c in cars])) if cars else None
    roots = {}
    for c in cars:
        r = str(S[c].get('root', '')).split(':')[0]; roots[r] = roots.get(r, 0) + 1
    d['root_kind'] = roots
    out['groups'][g] = d
    # spec accuracy
    acc = {}
    for k in ('length', 'width', 'height', 'wheelbase', 'track_f', 'track_r'):
        diffs = [M[c][k] - SP[c][k] for c in cars if c in SP and k in SP[c] and k in M[c]
                 and (k not in ('width', 'track_f', 'track_r') or 'road' in SP[c].get('var', ''))]
        if diffs: acc[k] = dict(n=len(diffs), median_abs=round(float(np.median(np.abs(diffs))), 0),
                                p90_abs=round(float(np.percentile(np.abs(diffs), 90)), 0), bias=round(float(np.median(diffs)), 0))
    out['spec'][g] = acc
json.dump(out, open('aggregate.json', 'w'), indent=1)
for g, d in out['groups'].items():
    print(f"\n== {g} n={d['n']}")
    for k, v in d.items():
        if k not in ('cars', 'n'): print(f'  {k}: {v}')
    print('  spec:', out['spec'][g])

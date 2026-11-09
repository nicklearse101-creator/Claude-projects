"""Car measurement template: pull the standard dimensions and body landmarks out of a kn5,
so any model (Kunos, mod, or ours) can be checked against published specs and against each other.

    python measure.py CAR_DIR [CAR_DIR ...] --out measures.json

Measured (AC axes: +x left, +y up, +z forward; reported in mm):
  wheelbase, track_f, track_r          from WHEEL_xx node centres
  tyre_d_f/r, rim_d_f/r                tyre / rim mesh radius about the wheel axis (x)
  ground                               wheel centre y - tyre radius (should be ~0)
  length, width, height                exterior meshes, spike-filtered: narrow things (mirrors, antenna,
                                       tow hooks) are removed with a 300 mm running median on the profile
  width_incl_mirrors, height_raw       unfiltered values
  overhang_f / overhang_r              bumper to axle
  windscreen_rake, backlight_rake      degrees from vertical, plane fit to centre glass
  belt_h                               lowest point of the side glass at the B-pillar station
  arch_gap_f/r                         arch lip top minus tyre top, at the wheel centre station
"""
import sys, os, json, glob, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kn5full import KN5

SKIP = ('shadow', 'flycam', 'damage_glass', 'dmg', 'collider', 'blur', 'driver', 'beam', 'flame', 'smoke')


def running_max_filtered(coord, val, step=0.02, win=0.30):
    """Profile of max(val) per bin of coord, then running median over win (removes narrow spikes)."""
    lo, hi = coord.min(), coord.max()
    nb = max(int((hi - lo) / step) + 1, 1)
    b = np.clip(((coord - lo) / step).astype(int), 0, nb - 1)
    prof = np.full(nb, -np.inf)
    np.maximum.at(prof, b, val)
    prof[np.isinf(prof)] = np.nan
    w = max(int(win / step) // 2, 1)
    filt = np.array([np.nanmedian(prof[max(0, i - w):i + w + 1]) for i in range(nb)])
    return prof, filt


def measure(car_dir):
    kn5s = sorted(glob.glob(os.path.join(car_dir, '*.kn5')), key=os.path.getsize, reverse=True)
    k = KN5(kn5s[0], load_textures=False)
    out = {'car': os.path.basename(os.path.normpath(car_dir)), 'tris': int(sum(len(m.idx) for m in k.meshes))}
    wheels = {}
    for n in k.nodes:
        if n.name in ('WHEEL_LF', 'WHEEL_RF', 'WHEEL_LR', 'WHEEL_RR'):
            wheels[n.name[-2:]] = n.world[3, :3].copy()
    if len(wheels) == 4:
        out['wheelbase'] = (wheels['LF'][2] + wheels['RF'][2] - wheels['LR'][2] - wheels['RR'][2]) / 2
        out['track_f'] = abs(wheels['LF'][0] - wheels['RF'][0]); out['track_r'] = abs(wheels['LR'][0] - wheels['RR'][0])
    # tyre and rim radii: meshes under each WHEEL_ node
    def under(m, tag):
        return any(p == tag for p in k.path_of(m.node).split('/'))
    tyre_bottom = []
    for ax in ('F', 'R'):
        rt, rr = [], []
        for side in ('L', 'R'):
            tag = f'WHEEL_{side}{ax}'
            if side + ax not in wheels: continue
            c = wheels[side + ax]
            radii = []
            for m in k.meshes:
                if not under(m, tag) or 'blur' in m.name.lower() or 'blur' in k.path_of(m.node).lower(): continue
                rad = np.sqrt((m.pos[:, 1] - c[1]) ** 2 + (m.pos[:, 2] - c[2]) ** 2)
                radii.append((rad.max(), m))
            if not radii: continue
            # the tyre is the outermost mesh on the wheel; the rim is the biggest mesh clearly inside it
            rmax, tm = max(radii, key=lambda x: x[0])
            rt.append(rmax); tyre_bottom.append(tm.pos[:, 1].min())
            inner = [r for r, m in radii if r < 0.9 * rmax and (not m.mat or m.mat.shader != 'ksTyres')]
            if inner: rr.append(max(inner))
        if rt: out[f'tyre_d_{ax.lower()}'] = 2 * float(np.median(rt))
        if rr: out[f'rim_d_{ax.lower()}'] = 2 * float(np.median(rr))
    # exterior point cloud
    ext = [m for m in k.meshes if not any(s in (m.name + k.path_of(m.node)).lower() for s in SKIP)
           and 'COCKPIT' not in k.path_of(m.node) and not any(w in k.path_of(m.node) for w in ('WHEEL_',))]
    if not ext:   # some mods hang everything under one node whose name trips the skip list
        ext = [m for m in k.meshes if not any(w in k.path_of(m.node) for w in ('WHEEL_',))
               and not any(s in m.name.lower() for s in SKIP)]
    P = np.concatenate([m.pos for m in ext])
    if tyre_bottom:
        out['ground'] = float(np.mean(tyre_bottom))     # contact patch height in the kn5 frame
    g = out.get('ground', P[:, 1].min())
    _, wz = running_max_filtered(P[:, 2], np.abs(P[:, 0]))
    out['width_filtered'] = 2 * float(np.nanmax(wz)); out['width_incl_mirrors'] = 2 * float(np.abs(P[:, 0]).max())
    _, hx = running_max_filtered(P[:, 0], P[:, 1])
    out['height_filtered'] = float(np.nanmax(hx) - g); out['height_raw'] = float(P[:, 1].max() - g)
    # antenna / roof-mounted junk shows as raw >> filtered; otherwise raw is the honest roof height
    out['height'] = out['height_raw'] if out['height_raw'] - out['height_filtered'] < 0.06 else out['height_filtered']
    _, zf = running_max_filtered(P[:, 0], P[:, 2]); _, zr = running_max_filtered(P[:, 0], -P[:, 2])
    zmax, zmin = float(np.nanmax(zf)), -float(np.nanmax(zr))
    out['length_filtered'] = zmax - zmin
    Pl = np.concatenate([m.pos for m in ext if 'plate' not in m.name.lower() and 'targa' not in m.name.lower()])
    out['length'] = float(Pl[:, 2].max() - Pl[:, 2].min())   # raw extent without number plates: best vs specs
    zmax, zmin = float(Pl[:, 2].max()), float(Pl[:, 2].min())
    if len(wheels) == 4:
        zf_ax = (wheels['LF'][2] + wheels['RF'][2]) / 2; zr_ax = (wheels['LR'][2] + wheels['RR'][2]) / 2
        out['overhang_f'] = zmax - zf_ax; out['overhang_r'] = zr_ax - zmin
    # glass landmarks
    glass = [m for m in ext if m.mat and (('glass' in m.mat.name.lower() or 'window' in m.mat.name.lower()
             or m.mat.shader == 'ksWindscreen') and not any(s in m.mat.name.lower() for s in ('light', 'lamp', 'head', 'tail', 'lens')))]
    if glass:
        G = np.concatenate([m.pos for m in glass])
        G = G[G[:, 1] - g > 0.6]
        cen = G[np.abs(G[:, 0]) < 0.15]
        if len(cen) > 10:
            zmid = (cen[:, 2].max() + cen[:, 2].min()) / 2
            for nm, sel in (('windscreen_rake', cen[cen[:, 2] > zmid]), ('backlight_rake', cen[cen[:, 2] < zmid])):
                if len(sel) > 5 and np.ptp(sel[:, 1]) > 0.1:
                    a, _ = np.polyfit(sel[:, 1], sel[:, 2], 1)   # z = a*y + b
                    out[nm] = float(np.degrees(np.arctan(abs(a))))
        side = G[np.abs(G[:, 0]) > 0.45]
        if len(side) and len(wheels) == 4:
            zb = np.median(side[:, 2])      # middle of the side glass ~ B-pillar region
            s = side[np.abs(side[:, 2] - zb) < 0.15]
            if len(s): out['belt_h'] = float(s[:, 1].min() - g)
    if 'belt_h' in out:
        MIR = ('mirror', 'specchi', 'retro', 'spiegel', 'wing_m', 'wingm')
        Pn = np.concatenate([m.pos for m in ext if not any(t in m.name.lower() for t in MIR)])
        lowb = Pn[(Pn[:, 1] - g) < out['belt_h'] - 0.04]
        out['width_belt_raw'] = 2 * float(np.abs(lowb[:, 0]).max())
        # spike filter along the car: mirrors, aerials and flares shorter than ~0.3 m drop out
        _, wb = running_max_filtered(lowb[:, 2], np.abs(lowb[:, 0]), win=0.60)
        out['width'] = 2 * float(np.nanmax(wb))
        wm = max(((float(np.abs(m.pos[:, 0]).max()), m.name) for m in ext), default=(0, ''))
        out['widest_mesh'] = wm[1]
    else:
        out['width'] = out['width_filtered']
    # arch gap: lowest exterior point above each tyre, at the wheel station, outboard half
    if len(wheels) == 4 and 'tyre_d_f' in out:
        for ax in ('F', 'R'):
            gaps = []
            for side in ('L', 'R'):
                c = wheels[side + ax]; r = out[f'tyre_d_{ax.lower()}'] / 2
                sel = P[(np.abs(P[:, 2] - c[2]) < 0.03) & (np.sign(P[:, 0]) == np.sign(c[0])) &
                        (np.abs(P[:, 0]) > abs(c[0]) - 0.08) & (P[:, 1] > c[1] + r * 0.6)]
                if len(sel): gaps.append(sel[:, 1].min() - (c[1] + r))
            if gaps: out[f'arch_gap_{ax.lower()}'] = float(np.mean(gaps))
    for kk, v in list(out.items()):
        if isinstance(v, float) and kk not in ('windscreen_rake', 'backlight_rake'): out[kk] = round(v * 1000, 1)
        elif isinstance(v, float): out[kk] = round(v, 1)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cars', nargs='+'); ap.add_argument('--out', default='')
    a = ap.parse_args()
    res = []
    for c in a.cars:
        try:
            r = measure(c)
        except Exception as e:
            r = {'car': os.path.basename(c), 'error': repr(e)}
        res.append(r); print(json.dumps(r))
    if a.out: json.dump(res, open(a.out, 'w'), indent=1)

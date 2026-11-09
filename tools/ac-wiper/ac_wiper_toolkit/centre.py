"""Centre a wiper at the bottom middle of the windscreen (same depth below the edge as its original pivot), choose the
park turn so it lies along the bottom edge, fit the axis, and find the mirror sweep. Prints the rigid command args.
usage: centre.py CAR.kn5.bak_wiper wiper GLASS glass_zmin pivot_end [park_rot]
  park_rot (optional) forces the park turn in degrees when the automatic choice looks wrong (Toledo needed 3)."""
import sys, argparse, contextlib, io
import os as _os; exec(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ac_wiper.py")).read().split("ap = argparse.ArgumentParser()")[0])
K, w, G, zmin, end = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), sys.argv[5]
quiet = contextlib.redirect_stdout
def S(**kw):
    base = dict(kn5=K, wiper=w, glass=G, pivot=None, pivot_end=end, hub_radius=0.05, glass_zmin=zmin, offset='', park_rot=0, park_axis='')
    base.update(kw)
    with quiet(io.StringIO()): return setup(argparse.Namespace(**base))
k, wn, W, P0, tip0, glass = S()
g = np.vstack([m[6] for m in k.meshes_under(G)]); g = g[g[:, 2] > zmin]
def edge_at(x):                                  # windscreen bottom edge: frontmost glass vertex near this x
    c = g[np.abs(g[:, 0] - x) < 0.07]; return c[np.argmax(c[:, 2])]
e0, ec = edge_at(P0[0]), edge_at(0.0)
rel = P0 - np.array([P0[0], e0[1], e0[2]])
pivot = np.array([0.0, ec[1], ec[2]]) + rel; off = pivot - P0
offs = ':'.join(f'{v:.4f}' for v in off)
print(f'original pivot {np.round(P0, 4).tolist()} sits {np.round(rel, 4).tolist()} from the edge; centred pivot {np.round(pivot, 4).tolist()}')
behind0 = edge_at(tip0[0])[2] - tip0[2]
best = None
for pr in np.arange(-30, 31, 1.0):              # park: tip the same distance up from the bottom edge as originally
    k, wn, W, P, tip, glass = S(offset=offs, park_rot=pr, park_axis='57.5:0')
    d = abs((edge_at(tip[0])[2] - tip[2]) - behind0)
    if best is None or d < best[0]: best = (d, pr, tip)
_, pr, tip = best
if len(sys.argv) > 6: pr = float(sys.argv[6]); k, wn, W, P, tip, glass = S(offset=offs, park_rot=pr, park_axis='57.5:0')
print(f'park-rot {pr:+.0f}: tip {np.round(tip, 3).tolist()} ({behind0 * 100:.1f} cm up from the edge, like the original)')
# axis: keep the rigid blade near the glass over a ~160 deg sweep; then the sweep that mirrors the parked tip
k, wn, W, P, tip, glass = S(offset=offs, park_rot=pr, park_axis='57.5:0')
raw = k.raw[k.meshes_under(w)[0][2]]; idx = np.array(raw['idx']).reshape(-1, 3)
isl = islands(W, raw['idx']); rr = np.linalg.norm(W - P, axis=1)
bid = max(set(isl), key=lambda j: np.ptp(rr[isl == j]) - (1 if rr[isl == j].min() < 0.05 else 0))
X = surface_samples(W[idx[np.all(isl[idx] == bid, axis=1)]], 4)
target = np.array([-tip[0], tip[1], tip[2]]); best = None
for tilt in np.arange(35, 75, 2.5):
    ax = axis_lean(tilt, 0); sign = 1 if (rot(ax, 0.3) @ (tip - P))[1] > (tip - P)[1] else -1
    for deg in np.arange(140, 181, 1.0):
        endp = rot(ax, math.radians(sign * deg)) @ (tip - P) + P; e = np.linalg.norm(endp - target)
        worst = 0
        for f in np.linspace(0.15, 0.85, 6):
            gg = gaps(glass, (X - P) @ rot(ax, math.radians(sign * deg * f)).T + P)
            if np.isfinite(gg).mean() < 0.75: worst = 9; break
            worst = max(worst, np.nanmax(np.abs(gg)))
        sc = worst + e
        if best is None or sc < best[0]: best = (sc, tilt, sign * deg, worst, e)
_, tilt, sweep, worst, e = best
print(f'axis tilt {tilt}, sweep {sweep:+.0f} deg (end {e * 1000:.0f} mm from the mirror of the parked tip), rigid blade within {worst * 1000:.0f} mm')
print(f'RIGID --wiper {w} --glass {G} --glass-zmin {zmin} --pivot-end {end} --tilt {tilt} --lean 0 --sweep {sweep:.0f} --offset {offs} --park-rot {pr:.0f} --park-axis 57.5:0')

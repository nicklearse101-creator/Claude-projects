"""Find wipers merged into bigger meshes: lists loose parts shaped like a wiper (long, thin, at the windscreen base).
usage: find_wiper.py CAR.kn5 WINDSCREEN_NODE"""
import sys
import os as _os; exec(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ac_wiper.py")).read().split("ap = argparse.ArgumentParser()")[0])
# look inside every mesh for loose parts shaped like a wiper: long (0.35-0.8 m), thin, near the windscreen base
k = KN5(sys.argv[1]); glass = sys.argv[2]
g = np.vstack([m[6] for m in k.meshes_under(glass)]); front = g[g[:, 2] > g[:, 2].max() - 0.4]
base_y, base_z = front[:, 1].min(), front[:, 2].max()
print(f'windscreen base around y {base_y:.3f}, front edge z {base_z:.3f}')
for n in k.nodes:
    if n[1] != 'M' or not len(n[6]): continue
    V = n[6]; idx = n[7]
    if len(V) > 20000: continue
    isl = islands(V, idx)
    for i in set(isl):
        P = V[isl == i]; lo, hi = P.min(0), P.max(0); ext = hi - lo
        length = max(ext[0], ext[2])
        if 0.3 < length < 0.85 and ext[1] < 0.12 and abs(lo[1] - base_y) < 0.12 and base_z - 0.35 < hi[2] < base_z + 0.25:
            print(f'  {n[2]} (mat {n[8]}): part of {np.sum(isl == i)} verts  x {lo[0]:.3f}..{hi[0]:.3f}  y {lo[1]:.3f}..{hi[1]:.3f}  z {lo[2]:.3f}..{hi[2]:.3f}')

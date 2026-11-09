"""Print the windscreen outline (open boundary edges of the front glass) so pivot/pillar positions come from real geometry."""
import sys
import os as _os; exec(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ac_wiper.py")).read().split("ap = argparse.ArgumentParser()")[0])
k = KN5(sys.argv[1]); zmin = float(sys.argv[3])
for m in k.meshes_under(sys.argv[2]):
    V, idx = m[6], np.array(m[7]).reshape(-1, 3)
    keep = V[idx].mean(1)[:, 2] > zmin; idx = idx[keep]
    key = lambda i: tuple(np.round(V[i], 4))
    cnt = {}
    for t in idx:
        for a_, b_ in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            e = tuple(sorted((key(a_), key(b_)))); cnt[e] = cnt.get(e, 0) + 1
    edges = [e for e, c in cnt.items() if c == 1]
    pts = sorted({p for e in edges for p in e}, key=lambda p: (round(p[0], 2), p[1]))
    print(f'{m[2]}: {len(edges)} outline edges')
    for p in pts:
        if p[0] > 0.3: print('  ', p)

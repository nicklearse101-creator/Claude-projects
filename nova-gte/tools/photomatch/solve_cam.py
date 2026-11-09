"""Re-solve one camera (rvec, tvec, f, k1) against the fixed BA points (ba_result.json), using all of its
observations in obs.json; writes the camera back into ba_result.json. For views that see too little of the
car to be trusted inside the global BA (telephoto 3/4 front, rear-only views)."""
import json, sys
import numpy as np, cv2
from scipy.optimize import least_squares
src = open('ba.py').read().split('# ---- initialisation')[0]
exec(src)
B = json.load(open('ba_result.json'))
P = {k: np.array(v) for k, v in B['points'].items() if isinstance(v, list) and not k.startswith('PL')}
PL = {k: np.array(v) for k, v in B['points'].items() if k.startswith('PL')}
r = B['points']['wheel_r_F400']
for c in sys.argv[1:]:
    W, H = O[c]['W'], O[c]['H']
    names = [n for n in O[c]['pts'] if not n.startswith('PLF400')]
    X = np.array([pt3(n, P, PL, r) for n in names]); I = np.array([O[c]['pts'][n] for n in names])
    best = None
    for fk in (0.8, 1.0, 1.3, 1.6, 2.0):
        cp0 = np.array(B['cams'][c], float); cp0[6] = fk * W
        def res(q):
            uv, d = project(q, X, W, H)
            return np.r_[((uv - I) / (W / 1000)).ravel(), np.minimum(d - 0.5, 0) * 100, q[7] * 50]
        s = least_squares(res, cp0, loss='soft_l1', f_scale=3.0)
        e = np.linalg.norm(project(s.x, X, W, H)[0] - I, axis=1)
        if best is None or np.sqrt(np.mean(e ** 2)) < best[0]:
            best = (np.sqrt(np.mean(e ** 2)), s.x, e)
    rms, q, e = best
    R, _ = cv2.Rodrigues(q[:3]); C = -R.T @ q[3:6]
    print(f"{c}: rms {rms:.1f}px f/W {q[6]/W:.3f} cam {C.round(3)}")
    print('  ', ' '.join(f"{n}:{e[i]:.0f}" for i, n in enumerate(names)))
    B['cams'][c] = [float(v) for v in q]
json.dump(B, open('ba_result.json', 'w'), indent=1)

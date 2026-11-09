import json, numpy as np, cv2
from scipy.optimize import least_squares
O = json.load(open('obs.json'))
TRACK = {'F': 1.320, 'R': 1.307}; WB2 = 1.1715; D_FACE = 0.035; RF = 0.195
PAIR_INIT = {'HL_OT':(0.612,-1.79,0.70),'HL_OB':(0.612,-1.79,0.56),'HL_IT':(0.425,-1.795,0.70),'HL_IB':(0.425,-1.80,0.56),
 'IND_OT':(0.69,-1.78,0.70),'IND_OB':(0.69,-1.78,0.56),'GRO_T':(0.385,-1.80,0.68),'GRO_B':(0.385,-1.80,0.575),
 'WS_T':(0.50,-0.22,1.29),'WS_B':(0.62,-0.70,0.93),'TL_TO':(0.74,1.74,0.84),'TL_TI':(0.615,1.745,0.84),
 'TL_BO':(0.735,1.75,0.575),'TL_BI':(0.615,1.755,0.575),'HG_T':(0.50,1.30,1.29),'HG_B':(0.58,1.66,0.90),
 'SR':(0.765,-0.80,0.74),'HANDLE_F':(0.77,0.41,0.77),'HANDLE_R':(0.77,0.28,0.77),'MIR':(0.86,-0.47,0.90),
 'BON_F':(0.72,-1.74,0.72),'PNL_B':(0.61,1.75,0.575),
 'DG_RT':(0.62,0.39,1.28),'DG_RB':(0.70,0.39,0.86),'QW_FT':(0.62,0.52,1.28),'QW_FB':(0.70,0.52,0.88),'QW_RB':(0.68,1.47,0.89),'QW_RT':(0.58,1.07,1.26),'DSR_B':(0.76,0.44,0.30)}
PLATES = {'PLF294':(0,-1.82,0.42),'PLF400':(0,-1.82,0.42),'PLR294':(0,1.75,0.69),'PLR400':(0,1.75,0.69)}
pairs = sorted(PAIR_INIT); plates = sorted(PLATES); cams = sorted(O)
def unpack(p):
    i = 0; P = {}; PL = {}
    for n in pairs: P[n] = p[i:i+3]; i += 3
    for n in plates: PL[n] = p[i:i+3]; i += 3
    r = p[i]; i += 1
    C = {}
    for c in cams: C[c] = p[i:i+8]; i += 8      # rvec(3) tvec(3) f k1
    return P, PL, r, C
def point(name, P, PL, r):
    if name.startswith('PL'):
        base, corner = name.split('_'); cx, cy, cz = PL[base]
        x = cx + (0.26 if corner[1] == 'L' else -0.26); z = cz + (0.0555 if corner[0] == 'T' else -0.0555)
        return np.array([x, cy, z])
    if name.startswith('WC') or name.startswith('GC'):
        tag = name.split('_')[-1]
        axle = tag[0]; side = 1 if tag[1] == 'L' else -1
        if name.startswith('WCe_'):
            axle = tag[0]
        y = WB2 if axle == 'R' else -WB2
        if name.startswith('GC'):
            return np.array([side * TRACK[axle] / 2, y, 0.0])
        x = side * (TRACK[axle] / 2 + D_FACE)
        if name.startswith('WCe_'):
            kind = name.split('_')[1] if False else name.split('_')[-1]
        return np.array([x, y, r])
    base, side = name.rsplit('_', 1); a, y, z = P[base]
    return np.array([a if side == 'L' else -a, y, z])
def wheel_edge(name, r):
    # WCe_RR_back etc (side photo, right side)
    parts = name.split('_'); tag, kind = parts[1], parts[2]
    axle = tag[0]; side = 1 if tag[1] == 'L' else -1
    y = WB2 if axle == 'R' else -WB2; x = side * (TRACK[axle] / 2 + D_FACE); z = r
    if kind == 'back': y += RF
    if kind == 'fwd': y -= RF
    if kind == 'top': z += RF
    if kind == 'bot': z -= RF
    return np.array([x, y, z])
def pt3(name, P, PL, r):
    return wheel_edge(name, r) if name.startswith('WCe_') else point(name, P, PL, r)
def project(cp, X, W, H):
    rv, tv, f, k1 = cp[0:3], cp[3:6], cp[6], cp[7]
    R, _ = cv2.Rodrigues(rv); Xc = X @ R.T + tv
    x = Xc[:, 0] / Xc[:, 2]; y = Xc[:, 1] / Xc[:, 2]
    r2 = x * x + y * y; s = 1 + k1 * r2
    return np.stack([W / 2 + f * x * s, H / 2 + f * y * s], 1), Xc[:, 2]
def residuals(p, w_k1=50.0):
    P, PL, r, C = unpack(p); out = []
    for c in cams:
        W, H = O[c]['W'], O[c]['H']; names = list(O[c]['pts'])
        X = np.array([pt3(n, P, PL, r) for n in names]); I = np.array([O[c]['pts'][n] for n in names])
        uv, depth = project(C[c], X, W, H)
        out.append(((uv - I) / (W / 1000.0)).ravel())
        out.append(np.minimum(depth - 0.5, 0) * 100)          # stay in front of the camera
        out.append([C[c][7] * w_k1])                             # mild prior: little lens distortion
        out.append([(C[c][6] / W - 0.8) * 5])                    # weak prior on focal (phone cameras)
    return np.concatenate(out)
# ---- initialisation
p = []
for n in pairs: p += list(PAIR_INIT[n])
for n in plates: p += list(PLATES[n])
p += [0.275]
P0, PL0, r0, _ = unpack(np.array(p + [0] * 8 * len(cams)))
GUESS = {'c20': ((0, -5.5, 3.2), (0, -1.0, 0.6)), 'c24': ((0, 5.5, 2.0), (0, 1.2, 0.7)),
         'c22': ((2.5, -3.5, 1.0), (0.3, -0.8, 0.6)), 'c23': ((1.6, 3.0, 0.8), (0.2, 0.8, 0.6)),
         'cS': ((-6.0, 0.0, 1.0), (0, 0, 0.6)), 'cCF': ((3.0, -5.0, 1.2), (0, -0.8, 0.6)),
         'cAR': ((3.5, 5.0, 1.5), (0, 0.5, 0.6))}
def look(pos, tgt):
    pos, tgt = np.array(pos, float), np.array(tgt, float)
    z = tgt - pos; z /= np.linalg.norm(z)
    x = np.cross(z, [0, 0, 1.0]); x /= np.linalg.norm(x)      # image x to the right
    y = np.cross(z, x)                                        # image y down
    R = np.stack([x, y, z]); rv, _ = cv2.Rodrigues(R); t = -R @ pos
    return rv.ravel(), t
for c in cams:
    W, H = O[c]['W'], O[c]['H']; names = list(O[c]['pts'])
    X = np.array([pt3(n, P0, PL0, r0) for n in names], float); I = np.array([O[c]['pts'][n] for n in names], float)
    rv, tv = look(*GUESS[c]); best = None
    for fk in (0.5, 0.7, 0.9, 1.2):
        cp = np.r_[rv, tv, fk * W]
        sol = least_squares(lambda q: np.r_[(project(np.r_[q, 0.0], X, W, H)[0] - I).ravel() / (W / 1000), (q[6] / W - 0.8) * 20], cp)
        e = np.sqrt(np.mean((project(np.r_[sol.x, 0.0], X, W, H)[0] - I) ** 2))
        if best is None or e < best[0]: best = (e, sol.x)
    print(c, 'init rms px', round(best[0], 1), 'f/W', round(best[1][6] / W, 3))
    p += list(best[1]) + [0.0]
p = np.array(p)
s = least_squares(residuals, p, x_scale='jac', max_nfev=20000)
P, PL, r, C = unpack(s.x)
print('final cost', s.cost)
for c in cams:
    W, H = O[c]['W'], O[c]['H']; names = list(O[c]['pts'])
    X = np.array([pt3(n, P, PL, r) for n in names]); I = np.array([O[c]['pts'][n] for n in names])
    uv, _ = project(C[c], X, W, H); e = np.linalg.norm(uv - I, axis=1)
    R, _ = cv2.Rodrigues(C[c][0:3]); cc = -R.T @ C[c][3:6]
    print(f"{c}: rms {np.sqrt(np.mean(e**2)):.1f}px max {e.max():.1f} ({names[int(e.argmax())]}) f/W {C[c][6]/W:.3f} k1 {C[c][7]:.3f} cam {np.round(cc,2)}")
print('r', round(r, 4))
res = {n: [round(float(v), 4) for v in P[n]] for n in pairs}
res.update({n: [round(float(v), 4) for v in PL[n]] for n in plates})
res['wheel_r_F400'] = float(r)
for n in pairs: print(f"{n:9s} |x| {P[n][0]:.3f}  y {P[n][1]:.3f}  z {P[n][2]:.3f}")
for n in plates: print(f"{n:9s}  x {PL[n][0]:.3f}  y {PL[n][1]:.3f}  z {PL[n][2]:.3f}")
json.dump({'points': res, 'cams': {c: [float(v) for v in C[c]] for c in cams}}, open('ba_result.json', 'w'), indent=1)

for c in ('cCF','cAR','cS','c20'):
    W, H = O[c]['W'], O[c]['H']; names = list(O[c]['pts'])
    X = np.array([pt3(n, P, PL, r) for n in names]); I = np.array([O[c]['pts'][n] for n in names])
    uv, _ = project(C[c], X, W, H)
    print(c, ' '.join(f"{n}:{(uv[i]-I[i]).round(0).astype(int).tolist()}" for i, n in enumerate(names)))

import json, numpy as np, cv2
B = json.load(open('ba_result.json')); O = json.load(open('obs.json'))
def cam(c):
    p = np.array(B['cams'][c]); R, _ = cv2.Rodrigues(p[0:3]); t = p[3:6]
    return R, t, p[6], p[7], O[c]['W'], O[c]['H']
def ray(c, u, v):
    R, t, f, k1, W, H = cam(c)
    x = (u - W / 2) / f; y = (v - H / 2) / f
    for _ in range(5):                      # undo k1
        r2 = x * x + y * y; x, y = (u - W / 2) / f / (1 + k1 * r2), (v - H / 2) / f / (1 + k1 * r2)
    d = R.T @ np.array([x, y, 1.0]); C = -R.T @ t
    return C, d / np.linalg.norm(d)
def hit_x(c, u, v, X):
    C, d = ray(c, u, v); s = (X - C[0]) / d[0]; return C + s * d
def hit_y(c, u, v, Y):
    C, d = ray(c, u, v); s = (Y - C[1]) / d[1]; return C + s * d

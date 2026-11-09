"""Clean bumper rib bands (Nik 2026-10-19: rear bumper bend / ragged ribs; the bought model's ribs are ragged all
round). The real bumpers have level, identical ribs all the way round (grey studio pictures). Per bumper:
- every outer-skin vertex of the rib band gets its smooth base: a quadratic fit (along its normal) to the vertices in a
  thin vertical strip through it (+-3 cm up/down, +-4 mm sideways) - the vertical section of the bumper without ribs;
- the rib profile p(z) = median, over the bumper's middle section, of (vertex - base) by height (1 mm bins);
- each vertex is set to base + p(z): the ribs keep their heights and depth, the ragged waves go. Then the base itself is
  smoothed sideways (+-3 cm) to take out the dents.
Front ribs rise towards the corners (prep_reference.FRONT_RISE): the profile is indexed by height above that rise.
Runs in fix_shape (before the materials)."""
import numpy as np

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

BANDS = {  # name: (y test, z0, z1 band, middle-section test for the profile, rise)
    "rear": (lambda y: y > 1.43, 0.395, 0.578, lambda x, y: np.abs(x) < 0.40, False),
    "front": (lambda y: y < -1.45, 0.370, 0.530, lambda x, y: np.abs(x) < 0.40, True),
}
FRONT_RISE = ((-1.80, -1.74, -1.70, -1.65, -1.60, -1.55, -1.50), (0, 0.0015, 0.0025, 0.0035, 0.005, 0.0065, 0.0085))


def _smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def clean(name, obj="REF_BODY"):
    ytest, z0, z1, mid, rise = BANDS[name]
    o = bpy.data.objects[obj]; me = o.data
    nv = len(me.vertices)
    co = np.empty(nv * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    vn = np.empty(nv * 3); me.vertices.foreach_get("normal", vn); vn = vn.reshape(-1, 3)
    x, y, z = co.T
    zr = z - (np.interp(y, *FRONT_RISE) if rise else 0.0)
    # outer skin: horizontal-ish outward normal (away from the car's centre in plan)
    out = np.stack([x, y - (1.0 if name == "rear" else -1.0), np.zeros(nv)], 1)
    out /= np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-9)
    skin = (np.sum(vn * out, 1) > 0.35) & (np.abs(vn[:, 2]) < 0.75)
    reg = np.where(ytest(y) & skin & (zr > z0 - 0.03) & (zr < z1 + 0.03))[0]
    kd = KDTree(len(reg))
    for k, i in enumerate(reg):
        kd.insert(co[i], k)
    kd.balance()
    base = np.zeros(len(reg)); ok = np.zeros(len(reg), bool)
    for k, i in enumerate(reg):
        n = vn[i]; t = np.cross([0, 0, 1.0], n); t /= max(np.linalg.norm(t), 1e-9)
        J = np.array([j for _, j, _ in kd.find_range(co[i], 0.035)])
        d = co[reg[J]] - co[i]
        sel = (np.abs(d @ t) < 0.004) & (np.abs(d @ n) < 0.02)
        dz, off = d[sel, 2], d[sel] @ n
        if len(dz) < 8 or np.ptp(dz) < 0.03:
            continue
        A = np.stack([np.ones_like(dz), dz, dz * dz], 1)
        base[k] = np.linalg.lstsq(A, off, rcond=None)[0][0]           # smooth surface offset at the vertex
        ok[k] = True
    hp = -base                                                         # vertex relative to its smooth base
    # rib profile from the middle section
    m = ok & mid(x[reg], y[reg]) & (zr[reg] > z0 - 0.01) & (zr[reg] < z1 + 0.01)
    bins = np.round(zr[reg][m] * 1000).astype(int)
    prof_z, prof = [], []
    for b in np.unique(bins):
        v = hp[m][bins == b]
        if len(v) >= 3:
            prof_z.append(b / 1000.0); prof.append(float(np.median(v)))
    prof_z, prof = np.array(prof_z), np.convolve(np.pad(np.array(prof), 1, mode="edge"), [0.25, 0.5, 0.25], "valid")
    # sideways smoothing of the base (dents): average base over neighbours at the same height (+-3 cm, |dz| < 4 mm)
    base_s = base.copy()
    for k, i in enumerate(reg):
        if not ok[k]:
            continue
        J = np.array([j for _, j, _ in kd.find_range(co[i], 0.03)])
        J = J[ok[J] & (np.abs(co[reg[J], 2] - co[i, 2]) < 0.004)]
        if len(J) >= 3:
            # neighbours' bases are offsets along their own normals; compare in this vertex's normal frame
            P = co[reg[J]] + vn[reg[J]] * base[J, None]
            base_s[k] = float(np.median((P - co[i]) @ vn[i]))
    w = _smoothstep(z0 - 0.02, z0, zr[reg]) * _smoothstep(z1 + 0.02, z1, zr[reg]) * ok
    target = base_s + np.interp(zr[reg], prof_z, prof)
    move = w * target                                                   # along the normal, from the old vertex
    co[reg] += vn[reg] * move[:, None]
    me.vertices.foreach_set("co", co.ravel()); me.update()
    return {"verts": int(w.astype(bool).sum()), "max_move_mm": round(float(np.abs(move).max() * 1000), 1),
            "profile_depth_mm": round(float(np.ptp(prof) * 1000), 1)}


if __name__ == "__main__":
    print("==", {k: clean(k) for k in BANDS})

"""Export a blind-test build and its truth as point clouds of their outer outlines (for Blender).

    python blind_export.py CAR_DIR OUT_DIR METHOD [METHOD ...]
Writes OUT_DIR/<car>_<name>_points.npy  (N x 3, AC frame, metres), name = truth or the method.
In Blender: points -> Points to Volume -> Volume to Mesh gives a surface to look at.
"""
import sys, os
import numpy as np
import blind_test as B


def outline_points(zs, get, step=2):
    pts = []
    for i in range(0, len(zs), step):
        a = get(i)
        o = B.outline(a)
        if len(o):
            pts.append(np.c_[B.X0 + o[:, 0] * B.RES, o[:, 1], np.full(len(o), zs[i])])
    return np.concatenate(pts)


if __name__ == '__main__':
    car_dir, out = sys.argv[1], sys.argv[2]
    ctx = B.setup(car_dir, out)
    zs, stack, y0 = ctx['zs'], ctx['stack'], ctx['ylim'][0]
    fix = lambda P: np.c_[P[:, 0], y0 + P[:, 1] * B.RES, P[:, 2]]
    np.save(os.path.join(out, f"{ctx['car']}_truth_points.npy"), fix(outline_points(zs, lambda i: stack[i])))
    for m in sys.argv[3:]:
        r = B.run(car_dir, out, m, save=False)
        np.save(os.path.join(out, f"{ctx['car']}_{m}_points.npy"), fix(outline_points(zs, lambda i: r['fn'](zs[i]))))
        print(m, B.short(r['rep']).split(chr(10))[0])

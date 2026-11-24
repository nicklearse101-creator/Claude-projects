"""Rear-wheel wobble fix (Nik 24 Nov): the rim parts of the original wheel model sit off the wheel axis (rears 1.8-2.6 mm
high, fronts ~1.4 mm) while the tyres are true, so the rims bob up and down against the tyres when the wheel spins.
Each rim part under WHEEL_xx whose outer ring is a clean circle (R > 0.1 m, fit error < 1 mm) is moved so that circle
is centred on the wheel node (the spin axis). Spoke/face parts are centred on their hub + wheel-nut circle (0.03-0.06 m). Tyre and brake disc are left alone.
Running it again is harmless (parts already within 0.3 mm are skipped by the face pass; ring parts move by their residual).
Usage: blender -b <in.blend> --python kk_wheel_centre.py -- <out.blend>"""
import json, sys
import bpy, numpy as np
OUT = sys.argv[-1]


def fit(y, z):
    A = np.c_[2 * y, 2 * z, np.ones(len(y))]; b = y * y + z * z; s = np.linalg.lstsq(A, b, rcond=None)[0]
    return s[0], s[1], np.sqrt(s[2] + s[0] ** 2 + s[1] ** 2)


rep = {}
for sc in bpy.data.scenes:
    for w in ("WHEEL_LF", "WHEEL_RF", "WHEEL_LR", "WHEEL_RR"):
        root = next((o for o in sc.objects if (o.get("kn5_name") or o.name) == w), None)
        if not root:
            continue
        c = np.array(root.matrix_world.translation)
        for o in root.children_recursive:
            name = o.get("kn5_name") or o.name
            if o.type != "MESH" or o.users_scene[0] != sc or "Tire" in name or "rotor" in name.lower():
                continue
            mw = np.array(o.matrix_world); inv = np.linalg.inv(mw)
            n = len(o.data.vertices); co = np.empty(n * 3); o.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
            wco = (np.c_[co, np.ones(n)] @ mw.T)[:, :3]
            rr = np.hypot(wco[:, 1] - c[1], wco[:, 2] - c[2]); m = rr > np.percentile(rr, 90)
            cy, cz, R = fit(wco[m, 1], wco[m, 2])
            err = np.abs(np.hypot(wco[m, 1] - cy, wco[m, 2] - cz) - R).mean()
            if R < 0.1 or err > 0.001:
                # spoke/face part (outer ring is spoke tips, not a circle): centre on its hub + wheel-nut circle instead
                m = (rr > 0.03) & (rr < 0.06)
                if m.sum() < 40:
                    continue
                cy, cz, R = fit(wco[m, 1], wco[m, 2])
                if abs(cy - c[1]) > 0.006 or abs(cz - c[2]) > 0.006 or abs(cy - c[1]) + abs(cz - c[2]) < 0.0003:
                    continue
            if o.data.users > 1:
                o.data = o.data.copy()
            wco[:, 1] -= cy - c[1]; wco[:, 2] -= cz - c[2]
            o.data.vertices.foreach_set("co", ((np.c_[wco, np.ones(n)] @ inv.T)[:, :3]).ravel()); o.data.update()
            if "kn5_pristine" in o:
                o["kn5_pristine"] = False
            rep.setdefault(sc.name, []).append(f"{w} {name} dy {(cy - c[1]) * 1000:+.2f} dz {(cz - c[2]) * 1000:+.2f} mm")
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("REPORT", json.dumps(rep.get("Scene"), indent=0), {k: len(v) for k, v in rep.items()})

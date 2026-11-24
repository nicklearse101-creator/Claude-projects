"""ESCORT 15" (separate car ford_escort_mk2_tuned_15, Nik 24 Nov): a garden wheel swap - 15" rims, the SAME tyres.
  rims (every mesh under WHEEL_xx except the tyre and the brake disc): scaled 15/13 in the wheel plane (radially), width unchanged
  tyres: same width, same sidewall - the whole tyre just moved out radially by the rim's growth (bead on the 15" rim,
         tread radius + half an inch)
  brake discs untouched. Physics: RIM_RADIUS 15", RADIUS +28 mm; suspension untouched (the car sits 28 mm higher).
Run on "escort_v51 flames.blend"; saves "escort15_v1.blend"."""
import json
import bpy, numpy as np
S = 15.0 / 13.0          # the model rims are 13" (lip radius 0.182 = 13" rim + flange; CM reads R13), physics file said 14"
OUT = r"D:\Claude\escort_mk2_dtm\blender\escort15_v1.blend"
RIM_LIP = 0.182                 # measured rim lip radius (front and rear)
rep = {}
for sc in bpy.data.scenes:
    for w in ("WHEEL_LF", "WHEEL_RF", "WHEEL_LR", "WHEEL_RR"):
        root = next((o for o in sc.objects if (o.get("kn5_name") or o.name) == w), None)
        if not root:
            continue
        c = np.array(root.matrix_world.translation)
        for o in root.children_recursive:
            if o.type != "MESH" or o.users_scene[0] != sc:
                continue
            name = o.get("kn5_name") or o.name
            if "rotor" in name.lower():
                continue                                          # brake disc stays
            if o.data.users > 1:
                o.data = o.data.copy()
            mw = np.array(o.matrix_world); inv = np.linalg.inv(mw)
            n = len(o.data.vertices); co = np.empty(n * 3); o.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
            wco = (np.c_[co, np.ones(n)] @ mw.T)[:, :3]
            dy, dz = wco[:, 1] - c[1], wco[:, 2] - c[2]
            r = np.hypot(dy, dz)
            if "Tire" in name:
                shift = RIM_LIP * (S - 1)                         # tyre moves out by what the rim lip grew - tyre itself unchanged
                r_new = r + shift
                kind = f"tyre r {r.min():.3f}-{r.max():.3f} -> {r.min() + shift:.3f}-{r.max() + shift:.3f}"
            else:
                r_new = r * S
                kind = "rim x15/13"
            k = np.where(r > 1e-9, r_new / np.maximum(r, 1e-9), 1.0)
            wco[:, 1] = c[1] + dy * k; wco[:, 2] = c[2] + dz * k
            o.data.vertices.foreach_set("co", ((np.c_[wco, np.ones(n)] @ inv.T)[:, :3]).ravel()); o.data.update()
            if "kn5_pristine" in o:
                o["kn5_pristine"] = False
            rep.setdefault(sc.name + ":" + w, []).append(f"{name}: {kind}")
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("REPORT", json.dumps(rep.get("Scene:WHEEL_LF")), json.dumps(rep.get("Scene:WHEEL_LR")), len(rep))

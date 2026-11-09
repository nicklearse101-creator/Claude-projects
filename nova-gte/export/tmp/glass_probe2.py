import bpy, bmesh, json, numpy as np
R = r"D:\Claude\vauxhall_nova_gte_1989"
PF = json.load(open(R + r"\tools\photomatch\body_profile.json")); BA = json.load(open(R + r"\tools\photomatch\ba_result.json"))["points"]
DZ = PF["dz"]; k = PF["scuttle_curve"]["k"]; xb = BA["WS_B"][0]
P0 = np.array([BA["WS_B"][1], BA["WS_B"][2] + DZ]); P1 = np.array([BA["WS_T"][1], BA["WS_T"][2] + DZ])
Dv = (P1 - P0) / np.linalg.norm(P1 - P0); Nv = np.array([-Dv[1], Dv[0]]); L = np.linalg.norm(P1 - P0)
print("WS_B", BA["WS_B"], "WS_T", BA["WS_T"], "L %.3f" % L)
ob = bpy.data.objects["Body_Shell"]; bm = bmesh.new(); bm.from_mesh(ob.data)
rows = []
for v in bm.verts:
    if not any(e.is_boundary for e in v.link_edges) or abs(v.co.x) > 0.6 or v.co.z < 0.9 or not (-0.9 < v.co.y < 0.0):
        continue
    for lab, kk in (("straight", 0.0), ("base-curve", k)):
        q = np.array([v.co.y - kk * (v.co.x ** 2 - xb ** 2), v.co.z]) - P0
        rows.append((lab, round(v.co.x, 3), round(v.co.y, 3), round(v.co.z, 3), round(float(q @ Dv) / L, 2), round(float(q @ Nv), 3)))
for lab in ("straight", "base-curve"):
    print(lab, "boundary verts near the screen with |x|<0.2: (x, y, z, t/L, normal-offset)")
    sel = sorted([r for r in rows if r[0] == lab and abs(r[1]) < 0.2], key=lambda r: r[4])
    for r in sel[::max(1, len(sel) // 25)]:
        print("   ", r[1:])

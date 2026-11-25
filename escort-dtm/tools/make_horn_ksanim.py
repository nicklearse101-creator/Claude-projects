"""Horn middle-finger animation for the Escort (Nik 25 Nov) - the native AC way: a .ksanim like steer/shift, played by CSP
[ANIMATION_...] INPUT = HORN.
Source pose: the installed bdb_mazda_miata_na1 'fuck.ksanim' (same driver rig, gesture with the RIGHT arm, right-hand
fingers 4-6). Our driver sits on the left, so its final pose is mirrored to the left arm / left-hand fingers 1-3:
rotation (x, y, z, w) -> (x, -y, -z, w), checked against our own steer.ksanim left/right pairs (0.96-0.99 agreement).
Frame 0 = our steer.ksanim centre frame (the normal wheel grip, no jump); last frame = mirrored gesture; slerp with
ease-in-out; translations/scales stay ours (our bone offsets). Only the left arm chain + left-hand joints are written.
Usage: python make_horn_ksanim.py <car folder>"""
import struct, sys
import numpy as np

MIATA = r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\bdb_mazda_miata_na1\animations\fuck.ksanim"
CAR = sys.argv[1] if len(sys.argv) > 1 else r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\ford_escort_mk2_tuned_15"
FRAMES = 21


def load(p):
    b = open(p, "rb").read(); o = 8; n = struct.unpack_from("<i", b, 4)[0]; nodes = {}
    for _ in range(n):
        ln, = struct.unpack_from("<i", b, o); o += 4; name = b[o:o + ln].decode("latin1"); o += ln
        fc, = struct.unpack_from("<i", b, o); o += 4
        nodes[name] = np.frombuffer(b[o:o + fc * 40], dtype="<f4").reshape(fc, 10).copy(); o += fc * 40
    return nodes


def slerp(a, b, t):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    d = float(a @ b)
    if d < 0:
        b, d = -b, -d
    if d > 0.9995:
        q = a + t * (b - a); return q / np.linalg.norm(q)
    th = np.arccos(d)
    return (np.sin((1 - t) * th) * a + np.sin(t * th) * b) / np.sin(th)


mi = load(MIATA); st = load(CAR + r"\animations\steer.ksanim")
c = len(st["DRIVER:RIG_Arm_L"]) // 2
pairs = [("RIG_Arm_L", "RIG_Arm_R"), ("RIG_ForeArm_L", "RIG_ForeArm_R"), ("RIG_ForeArm_END_L", "RIG_ForeArm_END_R"),
         ("RIG_HAND_L", "RIG_HAND_R")] + [(f"HAND_L_Thumb{i}", f"HAND_R_Thumb{i}") for i in (1, 2, 3)]
pairs += [(f"HAND_{f}{i}", f"HAND_{f}{i + 3}") for f in ("Index", "Middle", "Ring", "Pinkie") for i in (1, 2, 3)]
out = bytearray(struct.pack("<ii", 2, len(pairs)))
for ln_, rn in pairs:
    L, R = "DRIVER:" + ln_, "DRIVER:" + rn
    rest = st[L][c]
    g = mi[R][-1, :4]
    target = np.array([g[0], -g[1], -g[2], g[3]], np.float64)
    nb = L.encode("latin1")
    out += struct.pack("<i", len(nb)) + nb + struct.pack("<i", FRAMES)
    for k in range(FRAMES):
        t = k / (FRAMES - 1); t = t * t * (3 - 2 * t)                # ease in-out
        q = slerp(rest[:4].astype(np.float64), target, t)
        out += struct.pack("<10f", *q, *rest[4:7], *rest[7:10])
path = CAR + r"\animations\horn_gesture.ksanim"
open(path, "wb").write(bytes(out))
print("written", path, len(out), "bytes,", len(pairs), "bones,", FRAMES, "frames")

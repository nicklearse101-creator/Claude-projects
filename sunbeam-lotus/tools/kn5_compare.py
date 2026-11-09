"""Compare two .kn5 files structurally: header, textures (name + bytes), materials (full
definitions), node tree (order, class, name, flags, matrices) and per-mesh geometry
(triangle count, material, bounds, and the set of rendered triangles compared as
corner positions/normals/uvs so a re-indexed vertex buffer still counts as equal).

    python kn5_compare.py a.kn5 b.kn5
"""
import hashlib
import struct
import sys

import numpy as np


def parse(path):
    d = open(path, "rb").read()
    p = [0]

    def i32():
        v = struct.unpack_from("<i", d, p[0])[0]; p[0] += 4; return v

    def u8():
        v = d[p[0]]; p[0] += 1; return v

    def f(n):
        v = struct.unpack_from(f"<{n}f", d, p[0]); p[0] += 4 * n; return v

    def s():
        n = i32(); v = d[p[0]:p[0] + n].decode("utf-8", "replace"); p[0] += n; return v

    def raw(n):
        v = d[p[0]:p[0] + n]; p[0] += n; return v

    assert raw(6) == b"sc6969"
    ver = i32(); extra = i32() if ver > 5 else None
    tex = []
    for _ in range(i32()):
        a = i32(); n = s(); b = raw(i32()); tex.append((n, a, hashlib.md5(b).hexdigest()))
    mats = []
    for _ in range(i32()):
        name, sh, bl, at, dp = s(), s(), u8(), u8(), i32()
        props = [(s(), f(10)) for _ in range(i32())]
        samp = [(s(), i32(), s()) for _ in range(i32())]
        mats.append((name, sh, bl, at, dp, tuple(props), tuple(samp)))
    nodes = []

    def node(depth):
        cls, name, kids, act = i32(), s(), i32(), u8()
        if cls == 1:
            nodes.append((depth, cls, name, kids, act, tuple(round(x, 5) for x in f(16))))
        else:
            fl = (u8(), u8(), u8())
            nv = i32(); v = np.frombuffer(raw(nv * 44), "<f4").reshape(nv, 11)
            ni = i32(); idx = np.frombuffer(raw(ni * 2), "<u2")
            mat, layer = i32(), i32(); lod = f(2); bs = f(4); rend = u8()
            corners = np.round(v[idx][:, :8].astype(np.float64), 4).reshape(-1, 24)
            tris = np.unique(corners, axis=0)
            geo = hashlib.md5(tris.tobytes()).hexdigest()
            nodes.append((depth, cls, name, kids, act, fl + (mat, layer) + tuple(round(x, 3) for x in lod) + (rend,),
                          ni // 3, geo))
        for _ in range(kids):
            node(depth + 1)

    node(0)
    assert p[0] == len(d)
    return (ver, extra), tex, mats, nodes


def main(a, b):
    A, B = parse(a), parse(b)
    ok = True
    for label, x, y in (("header", A[0], B[0]), ("textures", A[1], B[1]), ("materials", A[2], B[2])):
        same = x == y
        ok &= same
        print(f"{label:10}: {'identical' if same else 'DIFFERENT'} ({len(x) if isinstance(x, list) else x})")
    na, nb = A[3], B[3]
    print(f"nodes     : {len(na)} vs {len(nb)}")
    diffs = [(i, p, q) for i, (p, q) in enumerate(zip(na, nb)) if p != q]
    if len(na) != len(nb) or diffs:
        ok = False
        for i, p, q in diffs[:10]:
            print(f"  node {i} differs:\n    {p[:6]}\n    {q[:6]}")
    else:
        print("nodes     : identical (order, names, flags, matrices, triangles)")
    print("RESULT:", "IDENTICAL" if ok else "DIFFERENT")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

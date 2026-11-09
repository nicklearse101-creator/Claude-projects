"""Inspect an Assetto Corsa .kn5: header, material definitions, node tree, and
geometry conventions (triangle winding vs stored normals, UV range).

Used to learn the format from Kunos' own files before writing our exporter -
it reports structure and numbers only, it never extracts or saves any asset.

    python kn5_inspect.py <file.kn5> [--materials N] [--meshes N] [--tree]
"""
import argparse
import struct


class R:
    def __init__(self, path):
        self.f = open(path, "rb")

    def i32(self): return struct.unpack("<i", self.f.read(4))[0]
    def u32(self): return struct.unpack("<I", self.f.read(4))[0]
    def f32(self, n=1):
        v = struct.unpack(f"<{n}f", self.f.read(4 * n))
        return v if n > 1 else v[0]
    def b(self): return self.f.read(1)[0]
    def s(self): return self.f.read(self.i32()).decode("utf-8", "replace")
    def skip(self, n): self.f.seek(n, 1)


def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--materials", type=int, default=6)
    ap.add_argument("--meshes", type=int, default=4)
    ap.add_argument("--tree", action="store_true")
    a = ap.parse_args()

    r = R(a.path)
    assert r.f.read(6) == b"sc6969", "not a kn5"
    ver = r.i32()
    extra = r.i32() if ver > 5 else None
    print(f"version {ver}, extra header int {extra}")

    ntex = r.i32()
    tex = []
    for _ in range(ntex):
        active = r.i32(); name = r.s(); size = r.i32()
        head = r.f.read(min(size, 4)); r.skip(size - len(head))
        tex.append((name, size, head))
    print(f"textures: {ntex}; first: {[(n, s, h) for n, s, h in tex[:4]]}")

    nmat = r.i32()
    print(f"materials: {nmat}")
    for i in range(nmat):
        name = r.s(); shader = r.s(); blend = r.b(); alpha_tested = r.b(); depth = r.i32()
        props = []
        for _ in range(r.i32()):
            pn = r.s(); va = r.f32(); vb = r.f32(2); vc = r.f32(3); vd = r.f32(4)
            props.append((pn, round(va, 3), tuple(round(x, 3) for x in vc)))
        samplers = [(r.s(), r.i32(), r.s()) for _ in range(r.i32())]
        if i < a.materials:
            print(f"  [{i}] {name!r} shader={shader} blend={blend} alphaTested={alpha_tested} depth={depth}")
            print(f"       props={props}")
            print(f"       samplers={samplers}")

    shown = [0]

    def node(depth):
        cls = r.i32(); name = r.s(); kids = r.i32(); active = r.b()
        if cls == 1:
            m = r.f32(16)
            if a.tree:
                print("  " * depth + f"dummy {name} t={tuple(round(x, 3) for x in m[12:15])}")
        elif cls == 2:
            cast, vis, transp = r.b(), r.b(), r.b()
            nv = r.i32()
            verts = [r.f32(11) for _ in range(nv)]
            ni = r.i32()
            idx = struct.unpack(f"<{ni}H", r.f.read(2 * ni))
            mat = r.u32(); layer = r.u32(); lod_in = r.f32(); lod_out = r.f32(); c = r.f32(3); rad = r.f32(); rend = r.b()
            if shown[0] < a.meshes and nv > 30:
                shown[0] += 1
                agree = disagree = 0
                for t in range(0, min(ni, 3000), 3):
                    p0, p1, p2 = (verts[idx[t + k]] for k in range(3))
                    fn = cross(sub(p1[:3], p0[:3]), sub(p2[:3], p0[:3]))
                    vn = tuple(p0[3 + k] + p1[3 + k] + p2[3 + k] for k in range(3))
                    d = dot(fn, vn)
                    if d > 0: agree += 1
                    elif d < 0: disagree += 1
                us = [v[6] for v in verts]; vs = [v[7] for v in verts]
                tl = [sum(x * x for x in v[8:11]) ** 0.5 for v in verts[:50]]
                print(f"  mesh {name!r}: verts {nv}, tris {ni // 3}, mat {mat}, cast/vis/transp {cast}/{vis}/{transp}, "
                      f"layer {layer}, lod {lod_in}-{lod_out}, renderable {rend}")
                print(f"       winding: cross(p1-p0,p2-p0) agrees with normal {agree}, disagrees {disagree}")
                print(f"       uv range u {min(us):.2f}..{max(us):.2f} v {min(vs):.2f}..{max(vs):.2f}; tangent lengths ~{sum(tl)/len(tl):.2f}")
        else:
            raise ValueError(f"node class {cls} ({name!r}) - skinned meshes not handled")
        for _ in range(kids):
            node(depth + 1)

    node(0)


if __name__ == "__main__":
    main()

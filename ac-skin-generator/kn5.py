"""Minimal Assetto Corsa .kn5 reader: embedded textures, materials, meshes (world space).

Format notes (from the AC wiper toolkit's reader, extended for UVs/normals/samplers):
  header 'sc6969', int version (+1 int if version > 5)
  textures: count, then (int type, str name, int size, bytes)
  materials: count, then (str name, str shader, byte blend, byte alphaTested, int depthMode,
             props: count x (str name, 10 floats), samplers: count x (str name, int slot, str texture))
  nodes (recursive): int class, str name, int children, byte active
     class 1 = transform: 16 floats (row-vector matrix, translation in row 3)
     class 2 = mesh, 3 = skinned mesh: 3 bytes flags, [class 3: bones], vertices
             (class 2: 44 bytes pos3 nrm3 uv2 tan3; class 3: 76 bytes, + weights4 + indices4),
             int index count + uint16 indices, int material, int layer, 2 floats lod,
             4 floats bounding sphere, byte renderable
"""
import struct
import numpy as np


class Mesh:
    __slots__ = ('name', 'pos', 'nrm', 'uv', 'idx', 'mat', 'parents')

    def __init__(self, **k):
        for a, v in k.items(): setattr(self, a, v)


class Material:
    __slots__ = ('name', 'shader', 'samplers', 'props')

    def __init__(self, **k):
        for a, v in k.items(): setattr(self, a, v)


class KN5:
    def __init__(self, path, load_textures=True):
        self.d = open(path, 'rb').read()
        self.p = 0
        if self.d[:6] != b'sc6969':
            raise ValueError(f'{path}: not a kn5 file')
        self.p = 6
        ver, = self.r('<i')
        if ver > 5: self.r('<i')
        self.textures = {}
        for _ in range(self.r('<i')[0]):
            self.r('<i'); name = self.s(); n, = self.r('<i')
            if load_textures: self.textures[name] = self.d[self.p:self.p + n]
            self.p += n
        self.materials = []
        for _ in range(self.r('<i')[0]):
            name = self.s(); shader = self.s(); self.r('<bbi')
            props = {}
            for _ in range(self.r('<i')[0]):
                pn = self.s(); vals = self.r('<10f'); props[pn] = vals[0]
            samplers = {}
            for _ in range(self.r('<i')[0]):
                sn = self.s(); self.r('<i'); samplers[sn] = self.s()
            self.materials.append(Material(name=name, shader=shader, samplers=samplers, props=props))
        self.meshes = []
        self._node(np.eye(4), ())
        del self.d

    def r(self, f):
        v = struct.unpack_from(f, self.d, self.p); self.p += struct.calcsize(f); return v

    def s(self):
        n, = self.r('<i'); v = self.d[self.p:self.p + n].decode('latin1'); self.p += n; return v

    def _node(self, parent, parents):
        cls, = self.r('<i'); name = self.s(); nc, = self.r('<i'); self.r('<b')
        world = parent
        if cls == 1:
            local = np.array(self.r('<16f'), dtype=np.float64).reshape(4, 4)
            world = local @ parent
        else:
            self.r('<bbb')
            if cls == 3:
                for _ in range(self.r('<i')[0]): self.s(); self.r('<16f')
            vc, = self.r('<i'); st = 44 if cls == 2 else 76
            raw = np.frombuffer(self.d, dtype=np.float32, count=vc * st // 4, offset=self.p).reshape(vc, st // 4)
            self.p += vc * st
            ic, = self.r('<i')
            idx = np.frombuffer(self.d, dtype=np.uint16, count=ic, offset=self.p).astype(np.int64)
            self.p += ic * 2
            mid, = self.r('<i'); self.r('<iff'); self.r('<4f'); self.r('<b')
            pos = raw[:, 0:3].astype(np.float64); nrm = raw[:, 3:6].astype(np.float64)
            if cls == 2:   # skinned meshes are already in model space
                pos = pos @ parent[:3, :3] + parent[3, :3]
                nrm = nrm @ parent[:3, :3]
            ln = np.linalg.norm(nrm, axis=1, keepdims=True); ln[ln == 0] = 1
            self.meshes.append(Mesh(name=name, pos=pos, nrm=nrm / ln, uv=raw[:, 6:8].astype(np.float64).copy(),
                                    idx=idx.reshape(-1, 3), mat=self.materials[mid] if mid < len(self.materials) else None,
                                    parents=parents))
        for _ in range(nc): self._node(world, parents + (name,))


if __name__ == '__main__':
    import sys
    k = KN5(sys.argv[1], load_textures=False)
    for m in k.meshes:
        lo, hi = m.pos.min(0), m.pos.max(0)
        print(f'{m.name:40s} {m.mat.name if m.mat else "?":30s} {m.mat.samplers.get("txDiffuse","") if m.mat else "":40s} '
              f'tris={len(m.idx):6d} x[{lo[0]:+.2f},{hi[0]:+.2f}] y[{lo[1]:+.2f},{hi[1]:+.2f}] z[{lo[2]:+.2f},{hi[2]:+.2f}]')

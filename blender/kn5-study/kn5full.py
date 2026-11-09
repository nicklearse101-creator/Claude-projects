"""Full Assetto Corsa .kn5 reader: keeps the node tree, local + world matrices, every mesh flag,
material properties (all 10 floats), sampler slots and embedded texture bytes.

Extends ac-skin-generator/kn5.py (which flattens to world-space meshes only).
Coordinates are AC's: +y up, +z forward, +x = car's LEFT. Matrices are row-vector (translation in row 3).

Usage as a library:
    from kn5full import KN5
    k = KN5(path)              # k.nodes (list, parent index), k.meshes, k.materials, k.textures
"""
import struct
import numpy as np


class Node:
    __slots__ = ('i', 'cls', 'name', 'parent', 'children', 'active', 'local', 'world', 'mesh')

    def __init__(self, **k):
        self.children = []; self.mesh = None
        for a, v in k.items(): setattr(self, a, v)


class Mesh:
    __slots__ = ('node', 'name', 'skinned', 'cast_shadows', 'visible', 'transparent', 'bones',
                 'pos_local', 'pos', 'nrm', 'uv', 'tan', 'weights', 'bone_idx', 'idx', 'mat_id', 'mat',
                 'layer', 'lod_in', 'lod_out', 'bsphere', 'renderable')

    def __init__(self, **k):
        for a, v in k.items(): setattr(self, a, v)


class Material:
    __slots__ = ('i', 'name', 'shader', 'blend', 'alpha_tested', 'depth_mode', 'props', 'samplers')

    def __init__(self, **k):
        for a, v in k.items(): setattr(self, a, v)


class KN5:
    def __init__(self, path, load_textures=True):
        self.path = path
        d = open(path, 'rb').read()
        if d[:6] != b'sc6969':
            raise ValueError(f'{path}: not a kn5 file')
        self.d = d; self.p = 6
        self.version, = self.r('<i')
        self.extra = self.r('<i')[0] if self.version > 5 else None
        self.textures = {}; self.texture_sizes = {}
        for _ in range(self.r('<i')[0]):
            self.r('<i'); name = self.s(); n, = self.r('<i')
            self.texture_sizes[name] = n
            if load_textures: self.textures[name] = d[self.p:self.p + n]
            self.p += n
        self.materials = []
        for mi in range(self.r('<i')[0]):
            name = self.s(); shader = self.s(); blend, at, dm = self.r('<bbi')
            props = {}
            for _ in range(self.r('<i')[0]):
                pn = self.s(); props[pn] = self.r('<10f')
            samplers = {}
            for _ in range(self.r('<i')[0]):
                sn = self.s(); slot, = self.r('<i'); samplers[sn] = (slot, self.s())
            self.materials.append(Material(i=mi, name=name, shader=shader, blend=blend, alpha_tested=at,
                                           depth_mode=dm, props=props, samplers=samplers))
        self.nodes = []; self.meshes = []
        self._node(-1, np.eye(4))
        del self.d

    def r(self, f):
        v = struct.unpack_from(f, self.d, self.p); self.p += struct.calcsize(f); return v

    def s(self):
        n, = self.r('<i'); v = self.d[self.p:self.p + n].decode('latin1'); self.p += n; return v

    def _node(self, parent, pworld):
        cls, = self.r('<i'); name = self.s(); nc, = self.r('<i'); active, = self.r('<b')
        n = Node(i=len(self.nodes), cls=cls, name=name, parent=parent, active=active,
                 local=np.eye(4), world=pworld)
        self.nodes.append(n)
        if parent >= 0: self.nodes[parent].children.append(n.i)
        if cls == 1:
            n.local = np.array(self.r('<16f'), dtype=np.float64).reshape(4, 4)
            n.world = n.local @ pworld
        else:
            cs, vis, tr = self.r('<bbb')
            bones = []
            if cls == 3:
                for _ in range(self.r('<i')[0]):
                    bn = self.s(); bones.append((bn, np.array(self.r('<16f')).reshape(4, 4)))
            vc, = self.r('<i'); st = 44 if cls == 2 else 76
            raw = np.frombuffer(self.d, dtype=np.float32, count=vc * st // 4, offset=self.p).reshape(vc, st // 4)
            self.p += vc * st
            ic, = self.r('<i')
            idx = np.frombuffer(self.d, dtype=np.uint16, count=ic, offset=self.p).astype(np.int64)
            self.p += ic * 2
            mid, = self.r('<i'); layer, lin, lout = self.r('<iff')
            if cls == 2:
                bs = self.r('<4f'); rend, = self.r('<b')
            else:   # skinned trailer is only material, layer, lod in/out (found on Kunos AE86 gear lever)
                bs = (0, 0, 0, 0); rend = 1
            pl = raw[:, 0:3].astype(np.float64)
            nl = raw[:, 3:6].astype(np.float64)
            if cls == 2:
                pos = pl @ pworld[:3, :3] + pworld[3, :3]; nrm = nl @ pworld[:3, :3]
            else:
                pos = pl; nrm = nl
            ln = np.linalg.norm(nrm, axis=1, keepdims=True); ln[ln == 0] = 1
            m = Mesh(node=n.i, name=name, skinned=(cls == 3), cast_shadows=cs, visible=vis, transparent=tr,
                     bones=bones, pos_local=pl, pos=pos, nrm=nrm / ln, uv=raw[:, 6:8].astype(np.float64).copy(),
                     tan=raw[:, 8:11].astype(np.float64).copy(),
                     weights=raw[:, 11:15].copy() if cls == 3 else None,
                     bone_idx=raw[:, 15:19].copy() if cls == 3 else None,
                     idx=idx.reshape(-1, 3), mat_id=mid,
                     mat=self.materials[mid] if 0 <= mid < len(self.materials) else None,
                     layer=layer, lod_in=lin, lod_out=lout, bsphere=bs, renderable=rend)
            n.mesh = m; self.meshes.append(m)
        for _ in range(nc): self._node(n.i, n.world)

    def path_of(self, i):
        out = []
        while i >= 0:
            out.append(self.nodes[i].name); i = self.nodes[i].parent
        return '/'.join(reversed(out))


def dds_info(b):
    """(width, height, mips, format) from DDS bytes; format is the FourCC or 'RGBA32' etc."""
    if b[:4] != b'DDS ':
        if b[:8] == b'\x89PNG\r\n\x1a\n':
            w, h = struct.unpack('>II', b[16:24]); return w, h, 1, 'PNG'
        return None
    h, w = struct.unpack_from('<II', b, 12); mips, = struct.unpack_from('<I', b, 28)
    flags, = struct.unpack_from('<I', b, 80); cc = b[84:88]
    if flags & 4:
        fmt = cc.decode('latin1')
        if fmt == 'DX10':
            dxgi, = struct.unpack_from('<I', b, 128); fmt = f'DX10:{dxgi}'
    else:
        bits, = struct.unpack_from('<I', b, 88); fmt = f'RGB{bits}'
    return w, h, mips, fmt

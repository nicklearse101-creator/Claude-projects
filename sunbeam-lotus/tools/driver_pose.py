"""The AC driver model posed as it sits in our car - a reference for fitting things round the driver (harness belts).
Runs in Blender (mathutils/numpy).

  * the driver kn5 (content/driver/<NAME from data/driver3d.ini>.kn5): its skinned body meshes (kn5 node class 3:
    bones with inverse-bind matrices, 76-byte vertices with 4 weights + 4 bone indices) and rigid meshes
  * the car's driver skeleton: animations/driver_base_pos.knh (node tree, local matrices) with the steering
    animation steer.ksanim (v2: per node and frame a quaternion, translation and scale) at its centre frame
posed vertex = sum(weight * boneWorld @ inverseBind @ v); kn5 matrices are row-vector (DirectX) - transposed here.
Result in Blender car coordinates (AC (x, y, z) -> (x, -z, y)).
"""
import struct

import bpy
import numpy as np
from mathutils import Matrix, Quaternion

AC = r"D:\SteamLibrary\steamapps\common\assettocorsa\content"


def _mat(m):
    return Matrix([m[0:4], m[4:8], m[8:12], m[12:16]]).transposed()


def read_knh(path):
    b = open(path, "rb").read(); pos = [0]

    def i32():
        v = struct.unpack_from("<i", b, pos[0])[0]; pos[0] += 4; return v

    def node(parent):
        n = i32(); name = b[pos[0]:pos[0] + n].decode(); pos[0] += n
        m = struct.unpack_from("<16f", b, pos[0]); pos[0] += 64
        out = [(name, parent, _mat(m))]
        for _ in range(i32()):
            out += node(name)
        return out
    return node(None)


def read_ksanim(path):
    b = open(path, "rb").read()
    ver, count = struct.unpack_from("<ii", b, 0); pos = 8
    anim = {}
    for _ in range(count):
        n = struct.unpack_from("<i", b, pos)[0]; pos += 4
        name = b[pos:pos + n].decode(); pos += n
        frames = struct.unpack_from("<i", b, pos)[0]; pos += 4
        anim[name] = [struct.unpack_from("<10f", b, pos + 40 * f) for f in range(frames)]
        pos += 40 * frames
    return anim


def skeleton_world(car_dir, frame=None, shift_frame=None, knh_dir=None):
    """World matrix (AC space) of every driver node for the steering animation's centre frame - or, with
    shift_frame, with the gear-change animation (shift.ksanim: shifting arm and hand) at that frame on top.
    knh_dir: another car's driver_base_pos.knh for the node tree (cars without one use the driver's default,
    which is the same driver_70 skeleton)."""
    nodes = read_knh((knh_dir or car_dir) + r"\animations\driver_base_pos.knh")
    steer = read_ksanim(car_dir + r"\animations\steer.ksanim")
    shift = read_ksanim(car_dir + r"\animations\shift.ksanim") if shift_frame is not None else {}
    # AC applies only the shift animation's MOVING nodes (the arm and hand) - the file also carries a root and
    # hips 31 cm further back and 9 cm higher than the steering animation's, which in game stay where steer puts
    # them (using them sat the Blender driver behind the seat, and the first shifter missed his hand - Nick)
    shift = {k: v for k, v in shift.items()
             if max(max(fr[i] for fr in v) - min(fr[i] for fr in v) for i in range(10)) > 1e-4}
    world = {}
    for name, parent, base in nodes:
        if name in shift or name in steer:
            fr = shift[name][shift_frame] if name in shift else steer[name][len(steer[name]) // 2 if frame is None
                                                                                else frame]
            qx, qy, qz, qw, tx, ty, tz, sx, sy, sz = fr
            loc = (Matrix.Translation((tx, ty, tz)) @ Quaternion((qw, qx, qy, qz)).to_matrix().to_4x4()
                   @ Matrix.Diagonal((sx, sy, sz, 1)))
        else:
            loc = base
        world[name] = (world[parent] if parent in world else Matrix.Identity(4)) @ loc
    return world


def read_driver_kn5(path):
    """[(name, kind, data)]: kind 'skin' -> (bone names, inverse binds, P, W, I, idx); 'mesh' -> (P, idx) with the
    node's parent chain of dummies (names) for rigid meshes."""
    f = open(path, "rb")
    rd = lambda n: f.read(n)
    i32 = lambda: struct.unpack("<i", rd(4))[0]
    s = lambda: rd(i32()).decode("utf-8", "replace")
    assert rd(6) == b"sc6969"
    ver = i32()
    if ver > 5:
        i32()
    for _ in range(i32()):                        # textures
        i32(); s(); f.seek(i32(), 1)
    for _ in range(i32()):                        # materials
        s(); s(); rd(1); rd(1); i32()
        for _ in range(i32()):
            s(); rd(4 * 10)
        for _ in range(i32()):
            s(); i32(); s()
    out = []

    def node(chain):
        cls = i32(); name = s(); kids = i32(); rd(1)
        if cls == 1:
            m = struct.unpack("<16f", rd(64))
            out.append((name, "dummy", (chain, _mat(m))))
            chain = chain + [name]
        elif cls == 2:
            rd(3)
            nv = i32(); V = np.frombuffer(rd(44 * nv), np.float32).reshape(nv, 11)
            ni = i32(); idx = np.frombuffer(rd(2 * ni), np.uint16)
            rd(4 * 4 + 16 + 1)
            out.append((name, "mesh", (chain, V[:, :3].copy(), idx.copy())))
        elif cls == 3:
            rd(3)
            bones = []
            for _ in range(i32()):
                bn = s(); bones.append((bn, _mat(struct.unpack("<16f", rd(64)))))
            nv = i32(); V = np.frombuffer(rd(76 * nv), np.float32).reshape(nv, 19)
            ni = i32(); idx = np.frombuffer(rd(2 * ni), np.uint16)
            rd(4 * 4)                             # material, layer, lod in/out
            out.append((name, "skin", (chain, bones, V[:, :3].copy(), V[:, 11:15].copy(),
                                       V[:, 15:19].astype(np.int64), idx.copy())))
        else:
            raise ValueError(f"node class {cls} ({name!r})")
        for _ in range(kids):
            node(chain)
    node([])
    return out


def posed_driver(car_id, skip=("HELMET", "FACE", "GLASS"), shift_frame=None, only=None, knh_car=None):
    """Posed driver triangles for a car: (verts Nx3, tris Mx3) in Blender car coordinates. only: part names to keep
    (e.g. ("Gloves",))."""
    car_dir = AC + rf"\cars\{car_id}"
    name = "driver_70"
    try:
        import configparser
        cp = configparser.ConfigParser(strict=False)
        cp.read(car_dir + r"\data\driver3d.ini")
        name = cp.get("MODEL", "NAME", fallback=name)
    except Exception:
        pass
    world = skeleton_world(car_dir, shift_frame=shift_frame, knh_dir=AC + rf"\cars\{knh_car}" if knh_car else None)
    bone_world = {k.split(":", 1)[-1]: v for k, v in world.items()}
    parts = read_driver_kn5(AC + rf"\driver\{name}.kn5")
    verts, tris = [], []
    for pname, kind, data in parts:
        if kind == "dummy" or any(k in pname.upper() for k in skip):
            continue
        if only and not any(k in pname for k in only):
            continue
        if kind == "skin":
            chain, bones, P, W, I, idx = data
            mats = np.array([np.array(bone_world[bn.split(":", 1)[-1]] @ inv) for bn, inv in bones])  # (nb, 4, 4)
            Ph = np.c_[P, np.ones(len(P))]
            out = np.zeros((len(P), 3))
            for k in range(4):
                M = mats[I[:, k]]                                                     # (nv, 4, 4)
                out += W[:, k:k + 1] * np.einsum("nij,nj->ni", M, Ph)[:, :3]
        else:
            chain, P, idx = data
            if not chain or chain[-1].split(":", 1)[-1] not in bone_world:
                continue
            M = np.array(bone_world[chain[-1].split(":", 1)[-1]])
            out = (np.c_[P, np.ones(len(P))] @ M.T)[:, :3]
        base = sum(len(v) for v in verts)
        verts.append(out); tris.append(idx.reshape(-1, 3).astype(np.int64) + base)
    V = np.concatenate(verts); T = np.concatenate(tris)
    return np.stack([V[:, 0], -V[:, 2], V[:, 1]], 1), T


def reference_object(car_id="talbot_sunbeam_lotus_81_works", name="REF_driver", **kw):
    """The posed driver as a mesh in a REFERENCE collection (outside the car's kn5 tree - never exported)."""
    V, T = posed_driver(car_id, **kw)
    col = bpy.data.collections.get("REFERENCE") or bpy.data.collections.new("REFERENCE")
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old)
    me = bpy.data.meshes.new(name)
    me.from_pydata(V.tolist(), [], T.tolist())
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob

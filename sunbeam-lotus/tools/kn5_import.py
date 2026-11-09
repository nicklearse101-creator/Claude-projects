"""Import an Assetto Corsa .kn5 into Blender for editing - lossless round-trip with ac_kn5_export.

Keeps everything the exporter needs to write the file back unchanged:
  * every texture's original bytes -> <tex_dir>/<name>, listed in order on the scene (kn5_textures)
  * every material's full definition (shader, flags, all properties with their vec2/3/4, samplers)
    -> JSON in the material's "kn5_def" (plus a viewport image node from txDiffuse)
  * node tree: dummies -> empties (local matrix), meshes -> mesh objects parented to their dummy,
    original names in "kn5_name", child order in "kn5_order", flags in "kn5_flags"
  * vertices: position, normal (as custom split normals), UV (v un-negated)
AC space (Y up, +Z front) -> Blender (Z up, -Y front): (x, y, z) -> (x, -z, y).
"""
import json
import os
import struct

import bpy
import numpy as np
from mathutils import Matrix

TO_AC = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))
TO_AC_INV = TO_AC.inverted()


class Reader:
    def __init__(self, data):
        self.d, self.p = data, 0

    def i32(self):
        v = struct.unpack_from("<i", self.d, self.p)[0]; self.p += 4; return v

    def u32(self):
        v = struct.unpack_from("<I", self.d, self.p)[0]; self.p += 4; return v

    def u8(self):
        v = self.d[self.p]; self.p += 1; return v

    def f32(self, n=1):
        v = struct.unpack_from(f"<{n}f", self.d, self.p); self.p += 4 * n
        return v if n > 1 else v[0]

    def s(self):
        n = self.i32(); v = self.d[self.p:self.p + n].decode("utf-8", "replace"); self.p += n; return v

    def raw(self, n):
        v = self.d[self.p:self.p + n]; self.p += n; return v


def blender_matrix(f16):
    a = Matrix([[f16[r * 4 + c] for r in range(4)] for c in range(4)])   # kn5 stores the transpose
    return TO_AC_INV @ a @ TO_AC


def import_kn5(path, tex_dir, collection_name="KN5", prefix="", primary=True):
    """primary=True: the file being edited (its texture list/header go on the scene and are written back
    first, in order). primary=False: a donor file to take parts from - its materials and textures get
    `prefix` so they can't clash with the primary file's, and each material remembers its tex_dir."""
    d = open(path, "rb").read()
    r = Reader(d)
    assert r.raw(6) == b"sc6969", "not a kn5"
    version = r.i32()
    extra = r.i32() if version > 5 else None
    scene = bpy.context.scene
    col = bpy.data.collections.get(collection_name) or bpy.data.collections.new(collection_name)
    if col.name not in scene.collection.children:
        scene.collection.children.link(col)

    os.makedirs(tex_dir, exist_ok=True)
    textures = []
    for _ in range(r.i32()):
        active = r.i32(); name = prefix + r.s(); size = r.i32(); data = r.raw(size)
        with open(os.path.join(tex_dir, name), "wb") as f:
            f.write(data)
        textures.append({"name": name, "active": active})
    if primary:
        scene["kn5_textures"] = json.dumps(textures)
        scene["kn5_tex_dir"] = tex_dir
        scene["kn5_header"] = json.dumps({"version": version, "extra": extra})

    images = {}
    mats = []
    for _ in range(r.i32()):
        name = prefix + r.s(); shader = r.s(); blend = r.u8(); alpha = r.u8(); depth = r.i32()
        props = []
        for _ in range(r.i32()):
            pn = r.s(); vals = r.f32(10); props.append([pn] + list(vals))
        samplers = [[r.s(), r.i32(), prefix + r.s()] for _ in range(r.i32())]
        m = bpy.data.materials.new(name)
        definition = {"name": name, "shader": shader, "blend": blend, "alphaTested": alpha,
                      "depth": depth, "props": props, "samplers": samplers}
        if not primary:
            definition["tex_dir"] = tex_dir
        m["kn5_def"] = json.dumps(definition)
        m.use_nodes = True
        diff = next((s[2] for s in samplers if s[0] == "txDiffuse"), None)
        if diff:
            fp = os.path.join(tex_dir, diff)
            try:
                img = images.get(diff) or bpy.data.images.load(fp, check_existing=True)
                images[diff] = img
                nt = m.node_tree
                bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
                tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
                nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
            except RuntimeError:
                pass
        mats.append(m)

    order = [0]
    stats = {"dummies": 0, "meshes": 0, "verts": 0, "tris": 0}

    def node(parent):
        cls = r.i32(); name = r.s(); kids = r.i32(); active = r.u8()
        if cls == 1:
            ob = bpy.data.objects.new(name, None)
            ob.empty_display_size = 0.02
            f16 = r.f32(16)
            ob.matrix_basis = blender_matrix(f16)
            ob["kn5_matrix"] = list(f16)          # exact originals, reused while the empty isn't moved
            ob["kn5_flags"] = json.dumps({"active": active})
            stats["dummies"] += 1
        elif cls == 2:
            cast, vis, transp = r.u8(), r.u8(), r.u8()
            nv = r.i32()
            v = np.frombuffer(r.raw(nv * 44), dtype="<f4").reshape(nv, 11)
            ni = r.i32()
            idx = np.frombuffer(r.raw(ni * 2), dtype="<u2").astype(np.int64)
            mat_id = r.u32(); layer = r.u32(); lod_in, lod_out = r.f32(2)
            bs = list(r.f32(4))                              # bounding sphere - kept for untouched parts
            rend = r.u8()
            pos = np.stack([v[:, 0], -v[:, 2], v[:, 1]], axis=1)
            nrm = np.stack([v[:, 3], -v[:, 5], v[:, 4]], axis=1)
            me = bpy.data.meshes.new(name)
            me.vertices.add(nv)
            me.vertices.foreach_set("co", pos.ravel())
            nt_ = ni // 3
            me.loops.add(nt_ * 3)
            me.loops.foreach_set("vertex_index", idx[:nt_ * 3])
            me.polygons.add(nt_)
            me.polygons.foreach_set("loop_start", np.arange(0, nt_ * 3, 3))
            me.update(calc_edges=True)
            uv = me.uv_layers.new(name="UVMap")
            uvs = np.stack([v[:, 6], -v[:, 7]], axis=1)[idx[:nt_ * 3]]
            uv.data.foreach_set("uv", uvs.ravel())
            me.normals_split_custom_set_from_vertices([tuple(n) for n in nrm])
            # exact originals per corner - Blender re-derives a few normals and all tangents,
            # so an untouched part is written back from these (see ac_kn5_export, kn5_pristine)
            tan = np.stack([v[:, 8], -v[:, 10], v[:, 9]], axis=1)
            for aname, arr in (("kn5_nrm", nrm), ("kn5_tan", tan)):
                at = me.attributes.new(aname, "FLOAT_VECTOR", "CORNER")
                at.data.foreach_set("vector", arr[idx[:nt_ * 3]].ravel())
            if mat_id < len(mats):
                me.materials.append(mats[mat_id])
            ob = bpy.data.objects.new(name, me)
            ob["kn5_pristine"] = True        # clear this after editing the mesh's shape
            ob["kn5_flags"] = json.dumps({"active": active, "cast": cast, "visible": vis, "transparent": transp,
                                          "layer": layer, "lod_in": lod_in, "lod_out": lod_out, "renderable": rend,
                                          "bs": bs})
            stats["meshes"] += 1; stats["verts"] += nv; stats["tris"] += nt_
        else:
            raise ValueError(f"node class {cls} ({name!r}): skinned meshes are not supported")
        ob["kn5_class"] = cls
        ob["kn5_name"] = name
        ob["kn5_order"] = order[0]; order[0] += 1
        col.objects.link(ob)
        if parent is not None:
            ob.parent = parent
            ob.matrix_parent_inverse.identity()
        for _ in range(kids):
            node(ob)
        return ob

    root = node(None)
    root["kn5_root" if primary else "kn5_donor_root"] = True
    assert r.p == len(d), f"trailing data: read {r.p} of {len(d)} bytes"
    stats.update(textures=len(textures), materials=len(mats), root=root.name)
    return stats

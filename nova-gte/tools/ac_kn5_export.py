"""Blender -> Assetto Corsa .kn5 writer (runs inside Blender).

Format as read back from Kunos' own files with kn5_inspect.py:
  * "sc6969", version 6 + one extra header int (Kunos files carry 781233)
  * textures: embedded file bytes (we write tiny uncompressed DDS swatches)
  * materials: name, shader, blend, alphaTested, depthMode, float properties
    (name, value, then 36 bytes of vec2/vec3/vec4), texture samplers
  * nodes: class 1 dummy (4x4 row-major, translation in [12:15]) or class 2
    mesh (44-byte verts: pos, normal, uv, tangent; ushort indices; material id;
    layer; lod in/out; bounding sphere; renderable) followed by children
  * AC space is Y up, front +Z, car's left +X; triangles wind counter-clockwise
    around the stored normal (same as Blender); UV v is stored negated

Blender layout used by this project: car faces -Y, Z up, +X = car's left.
The axis change (x, y, z) -> (x, z, -y) is a proper rotation, so it keeps
handedness and winding.

Each Blender object becomes a dummy node carrying its local transform; a mesh
object gets child mesh nodes (one per material, split at 65535 vertices) with
vertices in the object's own space, so pivots such as wheel centres survive.
"""
import json
import math
import os
import struct

import bpy
import numpy as np
from mathutils import Matrix

TO_AC = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))
TO_AC_INV = TO_AC.inverted()
KN5_VERSION, KN5_EXTRA = 6, 781233

# Shader definitions copied from Kunos materials (property names/defaults and sampler
# slots as read from ks_ford_escort_mk1 with kn5_inspect.py). Pick one per Blender
# material with the custom property ac_shader; default ksPerPixel. "DIFFUSE" means
# the material's own colour swatch, "FLAT_NM" a flat normal map.
SHADERS = {
    "ksPerPixel": {
        "props": [("ksAmbient", 0.35), ("ksDiffuse", 0.35), ("ksSpecular", 0.25), ("ksSpecularEXP", 30.0),
                  ("ksEmissive", 0.0), ("ksAlphaRef", 0.0)],
        "samplers": [("txDiffuse", "DIFFUSE")],
    },
    # AC and CSP find a car's tyres by this shader (log: "No tyre meshes found" / GRAPHICS RADIUS 0 without it)
    "ksTyres": {
        "props": [("ksAmbient", 0.45), ("ksDiffuse", 0.42), ("ksSpecular", 0.15), ("ksSpecularEXP", 25.0),
                  ("ksEmissive", 0.0), ("ksAlphaRef", 0.0), ("blurLevel", 0.0), ("dirtyLevel", 0.0),
                  ("fresnelC", 0.0), ("fresnelEXP", 5.0), ("isAdditive", 0.0), ("fresnelMaxLevel", 0.025)],
        "samplers": [("txDiffuse", "DIFFUSE"), ("txNormal", "FLAT_NM"), ("txDirty", "DIFFUSE"),
                     ("txBlur", "DIFFUSE"), ("txNormalBlur", "FLAT_NM")],
    },
    # Kunos' reflective workhorse (fresnel reflections, txMaps = specular/gloss/reflection mask).
    # Property set as on ks_ford_escort_mk1's EXT_metal_flat_color; values come from ac_preset.
    "ksPerPixelMultiMap": {
        "props": [("ksAmbient", 0.33), ("ksDiffuse", 0.33), ("ksSpecular", 0.15), ("ksSpecularEXP", 60.0),
                  ("ksEmissive", 0.0), ("ksAlphaRef", 0.0), ("fresnelC", 0.0), ("fresnelEXP", 2.0),
                  ("fresnelMaxLevel", 0.2), ("nmObjectSpace", 0.0), ("isAdditive", 1.0), ("useDetail", 0.0),
                  ("detailUVMultiplier", 0.0), ("shadowBiasMult", 0.0), ("damageZones", 0.0), ("dirt", 0.0),
                  ("sunSpecular", 0.0), ("sunSpecularEXP", 0.0)],
        "samplers": [("txDiffuse", "DIFFUSE"), ("txNormal", "FLAT_NM"), ("txMaps", "MAPS"), ("txDetail", "WHITE")],
    },
}
FLAT_NM = ("flat_nm.dds", (0.5, 0.5, 1.0, 1.0))
WHITE = ("white.dds", (1.0, 1.0, 1.0, 1.0))
# ac_preset -> property overrides (+ txMaps swatch: R specular, G gloss, B reflection)
PRESETS = {
    "paint":  ({"ksAmbient": 0.30, "ksDiffuse": 0.32, "ksSpecular": 0.55, "ksSpecularEXP": 140.0,
                "fresnelC": 0.06, "fresnelEXP": 3.5, "fresnelMaxLevel": 0.45, "isAdditive": 1.0}, (1.0, 1.0, 1.0)),
    "chrome": ({"ksAmbient": 0.25, "ksDiffuse": 0.20, "ksSpecular": 1.20, "ksSpecularEXP": 300.0,
                "fresnelC": 0.55, "fresnelEXP": 1.5, "fresnelMaxLevel": 1.0, "isAdditive": 1.0}, (1.0, 1.0, 1.0)),
    "glass":  ({"ksAmbient": 0.10, "ksDiffuse": 0.08, "ksSpecular": 1.00, "ksSpecularEXP": 400.0,
                "fresnelC": 0.12, "fresnelEXP": 3.0, "fresnelMaxLevel": 0.85, "isAdditive": 1.0}, (1.0, 1.0, 1.0)),
    "trim":   ({"ksAmbient": 0.28, "ksDiffuse": 0.25, "ksSpecular": 0.20, "ksSpecularEXP": 30.0,
                "fresnelC": 0.02, "fresnelEXP": 3.0, "fresnelMaxLevel": 0.10, "isAdditive": 0.0}, (0.6, 0.4, 0.3)),
    "lens":   ({"ksAmbient": 0.40, "ksDiffuse": 0.40, "ksSpecular": 0.80, "ksSpecularEXP": 200.0,
                "fresnelC": 0.10, "fresnelEXP": 3.0, "fresnelMaxLevel": 0.60, "isAdditive": 1.0}, (1.0, 1.0, 1.0)),
}


class Writer:
    def __init__(self):
        self.buf = bytearray()

    def i32(self, v): self.buf += struct.pack("<i", v)
    def u32(self, v): self.buf += struct.pack("<I", v)
    def f32(self, *v): self.buf += struct.pack(f"<{len(v)}f", *v)
    def u8(self, v): self.buf += struct.pack("<B", v)
    def s(self, text):
        d = text.encode("utf-8")
        self.i32(len(d)); self.buf += d


def dds_solid(rgba, size=4):
    """Uncompressed 32-bit BGRA DDS of one flat colour."""
    w = h = size
    head = struct.pack("<4s7I44s", b"DDS ", 124, 0x100F, h, w, w * 4, 0, 0, b"\0" * 44)
    pf = struct.pack("<8I", 32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    caps = struct.pack("<5I", 0x1000, 0, 0, 0, 0)
    r, g, b, a = (max(0, min(255, round(c * 255))) for c in rgba)
    return head + pf + caps + bytes((b, g, r, a)) * (w * h)


def base_colour(mat):
    if mat is None:
        return (0.6, 0.6, 0.6, 1.0)
    if mat.use_nodes and mat.node_tree:
        bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            return tuple(bsdf.inputs["Base Color"].default_value)
    return tuple(mat.diffuse_color)


def kn5_matrix(m):
    """Blender local matrix -> the 16 floats a kn5 dummy stores."""
    a = TO_AC @ m @ TO_AC_INV
    return [a[c][r] for r in range(4) for c in range(4)]   # row-vector layout: translation lands in [12:15]


def to_ac(v):
    return (v[0], v[2], -v[1])


def mesh_groups(obj, depsgraph, matrix=None):
    """Triangles of the evaluated mesh grouped by material slot -> {slot: [(verts Nx11 float32, idx uint16)]}.
    Vertices are unique per (vertex, normal, uv) and in AC space; `matrix` (Blender 4x4) is baked in first.
    Numpy throughout - an imported car has hundreds of thousands of corners."""
    ev = obj.evaluated_get(depsgraph)
    me = ev.to_mesh()
    try:
        me.calc_loop_triangles()
        nl, nt = len(me.loops), len(me.loop_triangles)
        if nt == 0:
            return {}
        uv = me.uv_layers.active
        have_tangents = False
        if uv:
            try:
                me.calc_tangents(uvmap=uv.name)
                have_tangents = True
            except RuntimeError:
                pass    # n-gons: keep the UVs anyway (dropping them made every vertex UV 0,0 - black paint in AC)
        co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        lvi = np.empty(nl, np.int64); me.loops.foreach_get("vertex_index", lvi)
        nrm = np.empty(nl * 3, np.float32); me.corner_normals.foreach_get("vector", nrm); nrm = nrm.reshape(-1, 3)
        uvs = np.zeros((nl, 2), np.float32)
        tan = np.tile(np.array([1.0, 0.0, 0.0], np.float32), (nl, 1))
        if uv:
            a = np.empty(nl * 2, np.float32); uv.data.foreach_get("uv", a); uvs = a.reshape(-1, 2)
        if have_tangents:
            a = np.empty(nl * 3, np.float32); me.loops.foreach_get("tangent", a); tan = a.reshape(-1, 3)
        else:
            # any unit vector perpendicular to the normal (fine with a flat normal map)
            ref = np.where(np.abs(nrm[:, 2:3]) < 0.9, np.array([[0.0, 0.0, 1.0]]), np.array([[1.0, 0.0, 0.0]]))
            t = np.cross(ref, nrm)
            tan = (t / np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-12)).astype(np.float32)
        tl = np.empty(nt * 3, np.int64); me.loop_triangles.foreach_get("loops", tl); tl = tl.reshape(-1, 3)
        tm = np.empty(nt, np.int64); me.loop_triangles.foreach_get("material_index", tm)
        if obj.get("kn5_pristine") and "kn5_nrm" in me.attributes and "kn5_tan" in me.attributes:
            a = np.empty(nl * 3, np.float32); me.attributes["kn5_nrm"].data.foreach_get("vector", a); nrm = a.reshape(-1, 3)
            a = np.empty(nl * 3, np.float32); me.attributes["kn5_tan"].data.foreach_get("vector", a); tan = a.reshape(-1, 3)
    finally:
        ev.to_mesh_clear()

    pos = co[lvi]
    if matrix is not None:
        m = np.array(matrix, np.float64)
        r = m[:3, :3]
        pos = pos @ r.T + m[:3, 3]
        unit = lambda a: a / np.maximum(np.linalg.norm(a, axis=1, keepdims=True), 1e-12)
        nrm = unit(nrm @ np.linalg.inv(r))    # inverse-transpose, then back to unit length (scaled parts)
        tan = unit(tan @ r.T)
    ac = lambda a: np.stack([a[:, 0], a[:, 2], -a[:, 1]], axis=1)
    attrs = np.concatenate([ac(pos), ac(nrm), np.stack([uvs[:, 0], -uvs[:, 1]], 1), ac(tan)], axis=1).astype(np.float32)
    key_all = np.concatenate([lvi[:, None].astype(np.float64), np.round(nrm, 4), np.round(uvs, 5)], axis=1)

    def pack(tris):
        loops = tris.ravel()
        uniq, first, inv = np.unique(key_all[loops], axis=0, return_index=True, return_inverse=True)
        if len(uniq) > 65535:
            h = len(tris) // 2
            return pack(tris[:h]) + pack(tris[h:])
        # number vertices in order of first use (np.unique sorts them) - keeps the original order
        # for an untouched imported part and is friendlier to the GPU's vertex cache
        order = np.argsort(first, kind="stable")
        rank = np.empty_like(order); rank[order] = np.arange(len(order))
        return [(attrs[loops[first[order]]], rank[inv.ravel()].astype(np.uint16))]

    return {int(mi): pack(tl[tm == mi]) for mi in np.unique(tm)}


def export_kn5(path, top_objects, shader="ksPerPixel", collider=False, share_textures=False):
    # share_textures=True (LOD files): don't embed donor textures - AC resolves a LOD's textures by name from
    # the car's main kn5, which already holds them (the stock CM-generated LODs carry no textures at all)
    """Write top_objects (and their children) to path. collider=True writes the plain 'GL' material Kunos colliders use.

    Objects brought in by kn5_import.py round-trip unchanged: a single top object marked kn5_root is
    written as the file's root, kn5 dummies/meshes keep their original names, flags and child order,
    and materials carrying a kn5_def are written verbatim with the original texture files."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    materials, mat_index = [], {}

    def material_id(mat):
        key = "GL" if collider else (mat.name if mat else "default_grey")
        if key not in mat_index:
            mat_index[key] = len(materials)
            materials.append((key, mat))
        return mat_index[key]

    def ordered(children):
        return sorted((c for c in children if not c.get("no_export")),
                      key=lambda o: (o.get("kn5_order", 10 ** 9), o.name))

    def flags(obj):
        return json.loads(obj["kn5_flags"]) if "kn5_flags" in obj else {}

    def build(obj, parent_world):
        local = parent_world.inverted() @ obj.matrix_world
        name = obj.get("kn5_name", obj.name)
        if obj.get("kn5_class") == 2:
            # imported mesh node: written as-is (no wrapper dummy); any move in Blender is baked in
            # (local comes out of parent-inverse maths with float noise - treat near-identity as identity,
            # otherwise every vertex gets re-rounded through the matrix)
            ident = all(abs(local[r][c] - (r == c)) < 1e-6 for r in range(4) for c in range(4))
            groups = mesh_groups(obj, depsgraph, matrix=None if ident else local)
            slots = [s.material for s in obj.material_slots] or [None]
            parts = [(mi, v, i) for mi, chunks in sorted(groups.items()) for v, i in chunks]
            nodes = []
            for k, (mi, verts, idx) in enumerate(parts):
                nodes.append({"cls": 2, "name": name if k == 0 else f"{name}_SUB{k}", "verts": verts, "idx": idx,
                              "mat": material_id(slots[mi] if mi < len(slots) else None),
                              "flags": flags(obj), "children": [],
                              "pristine": bool(obj.get("kn5_pristine")) and ident and len(parts) == 1})
            if nodes:
                nodes[0]["children"] = [build(c, obj.matrix_world) for c in ordered(obj.children)]
            return nodes
        mat16 = kn5_matrix(local)
        if "kn5_matrix" in obj and max(abs(x - y) for x, y in zip(mat16, obj["kn5_matrix"])) < 1e-5:
            mat16 = list(obj["kn5_matrix"])    # unmoved imported dummy: original floats, no rounding drift
        # kn5_dummy_name: a different name for the wrapper node, so a one-part mesh node keeps the object's name to
        # itself (lights.ini finds lamps by mesh name)
        node = {"cls": 1, "name": obj.get("kn5_dummy_name", name), "matrix": mat16, "flags": flags(obj), "children": []}
        if obj.type == "MESH":
            groups = mesh_groups(obj, depsgraph)
            slots = [s.material for s in obj.material_slots] or [None]
            n_parts = sum(len(c) for c in groups.values())
            k = 0
            for mi, chunks in sorted(groups.items()):
                mat = slots[mi] if mi < len(slots) else None
                for verts, idx in chunks:
                    part = name if n_parts == 1 else f"{name}_SUB{k}"
                    node["children"].append({"cls": 2, "name": part, "verts": verts, "idx": idx,
                                             "mat": material_id(mat), "flags": {}, "children": []})
                    k += 1
        for child in ordered(obj.children):
            built = build(child, obj.matrix_world)
            node["children"].extend(built if isinstance(built, list) else [built])
        return node

    if len(top_objects) == 1 and top_objects[0].get("kn5_root"):
        root = build(top_objects[0], Matrix.Identity(4))
        header = json.loads(scene.get("kn5_header", "{}"))
    else:
        root = {"cls": 1, "name": "ROOT", "matrix": kn5_matrix(Matrix.Identity(4)), "flags": {}, "children": []}
        for o in top_objects:
            built = build(o, Matrix.Identity(4))
            root["children"].extend(built if isinstance(built, list) else [built])
        header = {}

    w = Writer()
    w.buf += b"sc6969"; w.i32(header.get("version", KN5_VERSION)); w.i32(header.get("extra", KN5_EXTRA))

    def shader_of(mat):
        name = (mat.get("ac_shader") if mat else None) or shader
        if name not in SHADERS:
            raise ValueError(f"material {mat.name if mat else None!r}: unknown ac_shader {name!r}")
        return name

    def preset_of(mat):
        p = mat.get("ac_preset") if mat else None
        if p and p not in PRESETS:
            raise ValueError(f"material {mat.name!r}: unknown ac_preset {p!r}")
        return p

    textures, tex_names = [], {}

    def texture(name, rgba):
        if name not in tex_names:
            tex_names[name] = name
            textures.append((name, dds_solid(rgba), 1))
        return name

    def file_texture(path):
        """Image file on disk (DDS/PNG), embedded with its own bytes (generated-body textures)."""
        name = os.path.basename(path)
        if name not in tex_names:
            tex_names[name] = name
            with open(path, "rb") as f:
                textures.append((name, f.read(), 1))
        return name

    kn5_defs = {name: json.loads(mat["kn5_def"]) for name, mat in materials if mat is not None and "kn5_def" in mat}
    if not collider and kn5_defs:
        # the imported file's own textures, original bytes, original order
        tex_dir = scene["kn5_tex_dir"]
        for t in json.loads(scene["kn5_textures"]):
            with open(os.path.join(tex_dir, t["name"]), "rb") as f:
                textures.append((t["name"], f.read(), t["active"]))
            tex_names[t["name"]] = t["name"]

    if not collider and not share_textures:
        # textures of parts taken from other kn5 files (donor imports: their defs carry tex_dir)
        for name, d in kn5_defs.items():
            for _, _, tex in d["samplers"]:
                if tex not in tex_names and "tex_dir" in d:
                    with open(os.path.join(d["tex_dir"], tex), "rb") as f:
                        textures.append((tex, f.read(), 1))
                    tex_names[tex] = tex

    mat_tex = []   # per material: sampler kind -> texture name
    if not collider:
        for name, mat in materials:
            if name in kn5_defs:
                mat_tex.append({})
                continue
            rgba = list(base_colour(mat))
            if mat is not None and "ac_alpha" in mat:          # Nova: see-through glass swatch alpha
                rgba[3] = float(mat["ac_alpha"])
            files = json.loads(mat["ac_tex"]) if mat is not None and "ac_tex" in mat else {}   # kind -> image file
            t = {"DIFFUSE": file_texture(files["DIFFUSE"]) if "DIFFUSE" in files else texture(f"{name}_col.dds", tuple(rgba))}
            kinds = {k for _, k in SHADERS[shader_of(mat)]["samplers"]}
            if "FLAT_NM" in kinds:
                t["FLAT_NM"] = texture(*FLAT_NM)
            if "WHITE" in kinds:
                t["WHITE"] = texture(*WHITE)
            if "MAPS" in kinds and "MAPS" in files:
                t["MAPS"] = file_texture(files["MAPS"])
            elif "MAPS" in kinds:
                rgb = PRESETS[preset_of(mat)][1] if preset_of(mat) else (1.0, 1.0, 1.0)
                t["MAPS"] = texture(f"{name}_maps.dds", (*rgb, 1.0))
            mat_tex.append(t)
    w.i32(len(textures))
    for name, data, active in textures:
        w.i32(active); w.s(name); w.i32(len(data)); w.buf += data

    w.i32(len(materials))
    for i, (name, mat) in enumerate(materials):
        if collider:
            w.s(name); w.s("GL"); w.u8(0); w.u8(0); w.i32(0); w.i32(0); w.i32(0)
            continue
        if name in kn5_defs:
            d = kn5_defs[name]
            w.s(d["name"]); w.s(d["shader"]); w.u8(d["blend"]); w.u8(d["alphaTested"]); w.i32(d["depth"])
            w.i32(len(d["props"]))
            for p in d["props"]:
                w.s(p[0]); w.f32(*p[1:11])
            w.i32(len(d["samplers"]))
            for sname, slot, tex in d["samplers"]:
                w.s(sname); w.i32(slot); w.s(tex)
            continue
        spec = SHADERS[shader_of(mat)]
        over = PRESETS[preset_of(mat)][0] if preset_of(mat) else {}
        # Nova: ac_blend 1 = alpha blend (glass), ac_depth 1 = no depth write
        blend = int(mat.get("ac_blend", 0)) if mat is not None else 0
        depth = int(mat.get("ac_depth", 0)) if mat is not None else 0
        w.s(name); w.s(shader_of(mat)); w.u8(blend); w.u8(0); w.i32(depth)
        w.i32(len(spec["props"]))
        for pn, val in spec["props"]:
            w.s(pn); w.f32(over.get(pn, val)); w.f32(*([0.0] * 9))
        w.i32(len(spec["samplers"]))
        for slot, (sampler, kind) in enumerate(spec["samplers"]):
            w.s(sampler); w.i32(slot); w.s(mat_tex[i][kind])

    stats = {"meshes": 0, "verts": 0, "tris": 0}

    def write(node):
        fl = node.get("flags", {})
        w.i32(node["cls"]); w.s(node["name"]); w.i32(len(node["children"])); w.u8(fl.get("active", 1))
        if node["cls"] == 1:
            w.f32(*node["matrix"])
        else:
            verts, idx = node["verts"], node["idx"]
            w.u8(fl.get("cast", 1)); w.u8(fl.get("visible", 1)); w.u8(fl.get("transparent", 0))
            w.i32(len(verts)); w.buf += np.ascontiguousarray(verts, dtype="<f4").tobytes()
            w.i32(len(idx)); w.buf += np.ascontiguousarray(idx, dtype="<u2").tobytes()
            if "bs" in fl and node.get("pristine"):
                c, rad = fl["bs"][:3], fl["bs"][3]
            else:
                p = verts[:, :3].astype(np.float64)
                c = (p.min(0) + p.max(0)) / 2
                rad = float(np.sqrt(((p - c) ** 2).sum(1)).max())
            w.u32(node["mat"]); w.u32(fl.get("layer", 0)); w.f32(fl.get("lod_in", 0.0), fl.get("lod_out", 0.0))
            w.f32(*c); w.f32(rad); w.u8(fl.get("renderable", 1))
            stats["meshes"] += 1; stats["verts"] += len(verts); stats["tris"] += len(idx) // 3
        for ch in node["children"]:
            write(ch)

    write(root)
    with open(path, "wb") as f:
        f.write(w.buf)
    stats.update(materials=len(materials), textures=len(textures), bytes=len(w.buf))
    return stats

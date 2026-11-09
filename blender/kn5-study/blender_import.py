"""Import an Assetto Corsa .kn5 into Blender for study (Blender 5.2, run inside Blender).

    import sys; sys.path.insert(0, r'D:\\Claude\\Claude-\\blender\\kn5-study')
    import blender_import as bi; bi.load(r'...\\car.kn5', r'...\\out_dir', prefix='AE86')

What it does
- Rebuilds every mesh with WELDED vertices (kn5 stores split vertices per normal/UV), so Blender sees the
  real connected surface; per-corner UVs and the kn5's own normals are kept as custom split normals.
- Axis: Blender X = AC x (car's left = +X), Blender Y = -AC z (car faces -Y), Blender Z = AC y.
- Node tree kept as empties (names = kn5 transform nodes, e.g. WHEEL_LF, DOOR_L), meshes parented to them
  with world transforms preserved.
- One Blender material per kn5 material, with the txDiffuse texture wired (DDS loads natively); the shader
  name, blend mode and every ksXXX property are stored as custom properties.
- Optional `quads=True` runs tris-to-quads per mesh so the original quad edge flow can be read.
"""
import os, sys
import bpy, bmesh
import numpy as np
from mathutils import Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kn5full

AX = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=np.float64)   # row-vector: ac @ AX -> blender
#   (x, y, z)_ac -> (x, -z, y)_blender


def _mat(k, m, tex_dir, cache):
    if m.name in cache: return cache[m.name]
    bm = bpy.data.materials.new(m.name)
    bm['ks_shader'] = m.shader; bm['ks_blend'] = m.blend; bm['ks_alpha_tested'] = m.alpha_tested
    for p, v in m.props.items(): bm['ks_' + p] = float(v[0])
    for s, (slot, t) in m.samplers.items(): bm['tex_' + s] = t
    bm.use_nodes = True
    nt = bm.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    s = m.samplers.get('txDiffuse')
    if s and s[1] in k.textures:
        fn = os.path.join(tex_dir, s[1])
        if not os.path.exists(fn):
            open(fn, 'wb').write(k.textures[s[1]])
        try:
            img = bpy.data.images.load(fn, check_existing=True)
            tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = img; tn.location = (-400, 200)
            nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])
        except RuntimeError as e:
            print('texture failed', fn, e)
    if m.blend == 1 or 'Glass' in m.shader or 'Windscreen' in m.shader:
        bsdf.inputs['Alpha'].default_value = 0.3
    cache[m.name] = bm
    return bm


def load(path, out_dir, prefix='', quads=False, weld_tol=1e-5, skip=('collider',)):
    k = kn5full.KN5(path)
    tex_dir = os.path.join(out_dir, 'textures'); os.makedirs(tex_dir, exist_ok=True)
    col = bpy.data.collections.new(prefix or os.path.basename(path)); bpy.context.scene.collection.children.link(col)
    cache = {}; objs = {}
    C = np.eye(4); C[:3, :3] = AX            # basis change, row-vector
    Ci = np.linalg.inv(C)
    for n in k.nodes:
        world_b = Ci @ n.world @ C           # same transform, expressed in Blender axes (row-vector)
        Mw = Matrix(world_b.T.tolist())      # Blender uses column-vector matrices
        if n.cls == 1:
            o = bpy.data.objects.new(n.name, None); o.empty_display_size = 0.05
        else:
            m = n.mesh
            P = m.pos @ AX; N = m.nrm @ AX
            q = np.round(P / weld_tol).astype(np.int64)
            uq, first, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
            inv = inv.ravel()
            tri = inv[m.idx]
            keep = (tri[:, 0] != tri[:, 1]) & (tri[:, 1] != tri[:, 2]) & (tri[:, 0] != tri[:, 2])
            me = bpy.data.meshes.new(n.name)
            bmh = bmesh.new()
            vs = [bmh.verts.new(v) for v in P[first]]
            uvl = bmh.loops.layers.uv.new('UVMap')
            corner_src = []
            dup = 0
            for t, (a, b, c), ok in zip(m.idx, tri, keep):
                if not ok: continue
                try:
                    f = bmh.faces.new((vs[a], vs[b], vs[c]))
                except ValueError:
                    dup += 1; continue           # same face twice (double-sided copy): skip, counted
                for lp, src in zip(f.loops, t):
                    lp[uvl].uv = (m.uv[src, 0], -m.uv[src, 1])
                    corner_src.append(src)
            bmh.to_mesh(me); bmh.free()
            # custom normals, in loop order
            me.normals_split_custom_set([tuple(N[s]) for s in corner_src])
            if m.mat:
                me.materials.append(_mat(k, m.mat, tex_dir, cache))
            o = bpy.data.objects.new(n.name, me)
            o['ks_material'] = m.mat.name if m.mat else ''
            o['ks_shader'] = m.mat.shader if m.mat else ''
            o['ks_layer'] = m.layer; o['ks_lod_out'] = m.lod_out
            o['ks_cast_shadows'] = m.cast_shadows; o['ks_transparent'] = m.transparent
            o['kn5_split_verts'] = len(m.pos); o['kn5_tris'] = len(m.idx); o['dup_faces_skipped'] = dup
            Mw = Matrix.Identity(4)              # mesh data is already in world space
        col.objects.link(o)
        objs[n.i] = o
        o.matrix_world = Mw                      # pass 1: everything unparented, at its world place
    bpy.context.view_layer.update()
    worlds = {i: o.matrix_world.copy() for i, o in objs.items()}
    for n in k.nodes:                            # pass 2: parent, keeping world transforms
        if n.parent >= 0:
            o = objs[n.i]; o.parent = objs[n.parent]
            o.matrix_parent_inverse = worlds[n.parent].inverted()
    bpy.context.view_layer.update()
    if quads:
        for o in col.objects:
            if o.type != 'MESH': continue
            bmh = bmesh.new(); bmh.from_mesh(o.data)
            bmesh.ops.join_triangles(bmh, faces=bmh.faces, angle_face_threshold=np.radians(40),
                                     angle_shape_threshold=np.radians(40), cmp_uvs=True, cmp_seam=False,
                                     cmp_sharp=False, cmp_materials=True)
            bmh.to_mesh(o.data); bmh.free()
    print(f'imported {len(k.meshes)} meshes, {len(k.nodes)} nodes, {len(cache)} materials into {col.name}')
    return col, k

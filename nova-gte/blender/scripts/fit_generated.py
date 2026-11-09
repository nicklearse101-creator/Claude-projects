"""Fit an AI-generated body mesh (GLB from TRELLIS / Hunyuan3D, see tools/gen) into the car frame.

Car frame (same as the procedural build): ground z = 0, nose towards -y, car's left = +x, wheel centres from the
WHEEL_xx empties (y +-1.1715, z 0.2916 = tyre radius).  Steps:
  1. import, join into one mesh, put the length along y with the nose at -y (yaw arg if the generator turned it);
  2. find the four tyre contact patches (lowest vertices per quadrant) -> yaw, centreline, wheelbase;
  3. scale y so the wheelbase = 2.343 (FIA), x so the body width at the axles = 1.522 / 1.529 (FIA), z so the roof =
     1.365 (brochure), all about the ground; move the axle midpoint onto the empties;
  4. keep the better half (arg keep=+x|-x), mirror it (generators texture the unseen side badly).
Result object GEN_BODY in collection GEN. Run headless on a COPY of the blend:
  blender -b nova_gen.blend --python fit_generated.py -- in.glb [keep=+x] [yaw=0]
"""
import math
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

WB, H_ROOF = 2.343, 1.365
W_AXLE = {"front": 1.522, "rear": 1.529}


def args():
    a = sys.argv[sys.argv.index("--") + 1:]
    opt = dict(s.split("=", 1) for s in a[1:] if "=" in s)
    return a[0], opt.get("keep", "+x"), float(opt.get("yaw", 0))


def bounds(vs):
    return (Vector((min(v[i] for v in vs) for i in range(3))), Vector((max(v[i] for v in vs) for i in range(3))))


def contacts(vs, frac=0.012):
    """Tyre contact patch centres per quadrant (x sign, y sign) from the lowest vertices."""
    mn, mx = bounds(vs)
    c = (mn + mx) / 2
    zlim = mn.z + frac * (mx.z - mn.z)
    out = {}
    for sx in (1, -1):
        for sy in (1, -1):
            q = [v for v in vs if v.z < zlim and (v.x - c.x) * sx > 0.15 * (mx.x - mn.x) and (v.y - c.y) * sy > 0.15 * (mx.y - mn.y)]
            if q:
                out[(sx, sy)] = sum(q, Vector()) / len(q)
    return out


def width_at(vs, y0, z0, z1, dy=0.06):
    xs = [v.x for v in vs if abs(v.y - y0) < dy and z0 < v.z < z1]
    return (max(xs) - min(xs)) if xs else None


def main():
    src, keep, yaw = args()
    coll = bpy.data.collections.get("GEN") or bpy.data.collections.new("GEN")
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    for o in list(coll.objects):
        bpy.data.objects.remove(o)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=src)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    # bake world transforms into the meshes, drop the empties
    for o in meshes:
        o.data.transform(o.matrix_world)
        o.parent = None
        o.matrix_world = Matrix()
    for o in new:
        if o.type != "MESH":
            bpy.data.objects.remove(o)
    for o in meshes:
        for c in o.users_collection:
            c.objects.unlink(o)
        coll.objects.link(o)
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = ob.data.name = "GEN_BODY"
    me = ob.data

    vs = [v.co.copy() for v in me.vertices]
    mn, mx = bounds(vs)
    size = mx - mn
    rot = Matrix.Rotation(math.radians((90.0 if size.x > size.y else 0.0) + yaw), 4, "Z")
    me.transform(rot)
    vs = [v.co.copy() for v in me.vertices]
    mn, mx = bounds(vs)
    s0 = 3.622 / (mx.y - mn.y)                                   # rough uniform scale first (units become metres)
    me.transform(Matrix.Scale(s0, 4) @ Matrix.Translation(-Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))))

    for it in range(2):                                           # contacts -> yaw/centre, twice
        vs = [v.co.copy() for v in me.vertices]
        cp = contacts(vs)
        assert len(cp) == 4, "tyre contacts not found: %s" % list(cp)
        fm = (cp[(1, -1)] + cp[(-1, -1)]) / 2
        rm = (cp[(1, 1)] + cp[(-1, 1)]) / 2
        d = rm - fm
        ang = math.atan2(d.x, d.y)
        mid = (fm + rm) / 2
        me.transform(Matrix.Rotation(ang, 4, "Z") @ Matrix.Translation(-Vector((mid.x, mid.y, 0))))
    vs = [v.co.copy() for v in me.vertices]
    cp = contacts(vs)
    wb = ((cp[(1, 1)] + cp[(-1, 1)]) / 2 - (cp[(1, -1)] + cp[(-1, -1)]) / 2).y
    mn, mx = bounds(vs)
    zt = mx.z - mn.z
    yf, yr = (cp[(1, -1)].y + cp[(-1, -1)].y) / 2, (cp[(1, 1)].y + cp[(-1, 1)].y) / 2
    wf = width_at(vs, yf, mn.z + 0.30 * zt, mn.z + 0.55 * zt)
    wr = width_at(vs, yr, mn.z + 0.30 * zt, mn.z + 0.55 * zt)
    sy = WB / wb
    sx = (W_AXLE["front"] / wf + W_AXLE["rear"] / wr) / 2
    sz = H_ROOF / zt
    print("GEN raw: wheelbase %.3f  width F/R %.3f/%.3f  height %.3f  length %.3f" % (wb, wf, wr, zt, mx.y - mn.y))
    print("GEN scale x %.3f y %.3f z %.3f" % (sx, sy, sz))
    me.transform(Matrix.Diagonal((sx, sy, sz, 1)) @ Matrix.Translation(Vector((0, 0, -mn.z))))

    # axle midpoint onto the empties
    wf_ = bpy.data.objects.get("WHEEL_LF")
    wr_ = bpy.data.objects.get("WHEEL_LR")
    ymid = (wf_.matrix_world.translation.y + wr_.matrix_world.translation.y) / 2 if wf_ and wr_ else 0.0
    me.transform(Matrix.Translation(Vector((0, ymid, 0))))

    # symmetrise: keep one half, mirror it
    bm = bmesh.new()
    bm.from_mesh(me)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    sgn = 1 if keep == "+x" else -1
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0), plane_no=(sgn, 0, 0), clear_inner=True)
    bm.to_mesh(me)
    bm.free()
    mod = ob.modifiers.new("Mirror", "MIRROR")
    mod.use_axis[0] = True
    mod.use_mirror_merge = True
    mod.merge_threshold = 0.002
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in me.polygons:
        p.use_smooth = True

    vs = [v.co.copy() for v in me.vertices]
    mn, mx = bounds(vs)
    cp = contacts(vs)
    print("GEN fitted: size %.3f x %.3f x %.3f, y %.3f..%.3f, tris %d" % (mx.x - mn.x, mx.y - mn.y, mx.z - mn.z, mn.y, mx.y,
                                                                      sum(len(p.vertices) - 2 for p in me.polygons)))
    print("GEN contacts", {k: tuple(round(c, 3) for c in v) for k, v in cp.items()})
    return ob.name


if __name__ == "__main__":
    print("==", main())

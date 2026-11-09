"""Cut the two doors out of the Meshy body as separate objects that can open.
Door outline (y, z) read off the model's own shut lines (door_view.py, ortho side render with a 0.1 m grid):
front edge vertical at y -0.700 up to the belt, then along the A-pillar to the roof rail; top along the rail
(z 1.265); rear edge y 0.475 below the belt, 0.415 (window frame rear edge) above it; bottom z 0.305 (above the sill).
The body is bisected along the outline (on the side skin only, |x| > X_MIN), the faces inside become DOOR_L / DOOR_R
(+x = car's left). Each door gets an inner skin (Solidify, inward) and its origin on the front hinge line; the body
opening gets a jamb returning inward. blender -b nova_meshy.blend --python cut_doors.py"""
import bpy, bmesh
from mathutils import Vector
POLY = [(-0.700, 0.305), (0.475, 0.305), (0.475, 0.865), (0.415, 0.865), (0.415, 1.265), (-0.195, 1.265),
        (-0.690, 0.860)]
X_MIN = 0.45            # side skin only (interior bits sit further in)
JAMB = 0.05             # body opening returns inward this far
DOOR_THICK = 0.035      # door inner skin offset


def inside(a, b):
    ins = False
    for (a0, b0), (a1, b1) in zip(POLY, POLY[1:] + POLY[:1]):
        if (b0 > b) != (b1 > b) and a < a0 + (a1 - a0) * (b - b0) / (b1 - b0):
            ins = not ins
    return ins


def side_faces(bm, s):
    ys = [p[0] for p in POLY]; zs = [p[1] for p in POLY]
    return [f for f in bm.faces if s * f.calc_center_median().x > X_MIN and
            min(ys) - 0.05 < f.calc_center_median().y < max(ys) + 0.05 and
            min(zs) - 0.05 < f.calc_center_median().z < max(zs) + 0.05]


body = bpy.data.objects["Meshy_Body"]
bm = bmesh.new(); bm.from_mesh(body.data)
coll = body.users_collection[0]
made = {}
for s, name in ((1, "DOOR_L"), (-1, "DOOR_R")):
    faces = side_faces(bm, s)
    geom = set(faces) | {e for f in faces for e in f.edges} | {v for f in faces for v in f.verts}
    for (a0, b0), (a1, b1) in zip(POLY, POLY[1:] + POLY[:1]):
        no = Vector((0.0, -(b1 - b0), a1 - a0)).normalized()
        r = bmesh.ops.bisect_plane(bm, geom=[g for g in geom if g.is_valid], plane_co=(0, a0, b0), plane_no=no, dist=1e-6)
        geom = {g for g in geom if g.is_valid} | set(r["geom"])
    bm.normal_update()
    door = [f for f in bm.faces if s * f.calc_center_median().x > X_MIN and
            inside(f.calc_center_median().y, f.calc_center_median().z)]
    # copy door faces (with UVs) to a new mesh, delete from the body
    dm = bmesh.new()
    uv_src = bm.loops.layers.uv.active; uv_dst = dm.loops.layers.uv.new("UVMap")
    vmap = {}
    for f in door:
        nf = dm.faces.new([vmap.setdefault(v, dm.verts.new(v.co)) for v in f.verts])
        nf.material_index = f.material_index
        for la, lb in zip(f.loops, nf.loops):
            lb[uv_dst].uv = la[uv_src].uv
    rim = {e for f in door for e in f.edges if any(g not in door for g in e.link_faces)}
    bmesh.ops.delete(bm, geom=door, context="FACES_ONLY")
    # body jamb: the opening's edge returns inward (towards the centre)
    rim = [e for e in rim if e.is_valid]
    r = bmesh.ops.extrude_edge_only(bm, edges=rim)
    for v in [g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)]:
        v.co.x -= s * JAMB
    # inner skin: a copy of the door skin moved straight inward by DOOR_THICK, normals reversed (Solidify spikes on
    # the generated triangles), rim faces closing the edge
    src_faces = list(dm.faces)
    rim_e = [e for e in dm.edges if e.is_boundary]
    ret = bmesh.ops.duplicate(dm, geom=src_faces)
    newv = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
    for v in newv:
        v.co.x -= s * DOOR_THICK
    bmesh.ops.reverse_faces(dm, faces=[g for g in ret["geom"] if isinstance(g, bmesh.types.BMFace)])
    vm = ret["vert_map"]
    for e in rim_e:
        a, b = e.verts
        try:
            dm.faces.new((b, a, vm[a], vm[b]))
        except ValueError:
            pass
    me = bpy.data.meshes.new(name); dm.to_mesh(me); dm.free()
    for m in body.data.materials:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    # hinge: front edge of the door, at its outer skin
    V = [v.co for v in me.vertices]
    yf = min(v.y for v in V)
    front = [v for v in V if v.y < yf + 0.03 and v.z < 0.86]
    hx = max(s * v.x for v in front) * s
    pivot = Vector((hx, yf + 0.01, 0.58))
    me.transform(__import__("mathutils").Matrix.Translation(-pivot)); ob.location = pivot
    ob["hinge_axis"] = (0.0, 0.0, 1.0)
    made[name] = (len(door), tuple(round(c, 3) for c in pivot))
bm.normal_update()
bm.to_mesh(body.data); bm.free(); body.data.update()
for n, (nf, pv) in made.items():
    print("%s: %d faces, hinge pivot %s" % (n, nf, pv))
bpy.ops.wm.save_mainfile()
print("saved")

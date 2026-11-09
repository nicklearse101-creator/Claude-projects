"""Front of one generated body + rear of another (each fitted on its own tyre contacts), cut at the door's rear
shut line (DOOR_BAR_L), then prep_generated + export_gen.  -- front.glb rear.glb"""
import os, sys
import bmesh, bpy
import fit_generated as fg, prep_generated as pg, export_gen as eg, lookdev, smooth_generated as sg

front, rear = sys.argv[sys.argv.index("--") + 1:][:2]


def fit(path, name):
    sys.argv[sys.argv.index("--") + 1:] = [path, "keep=+x"]
    fg.main()
    o = bpy.data.objects["GEN_BODY"]; o.name = o.data.name = name
    bpy.data.collections["GEN"].objects.unlink(o); bpy.context.scene.collection.objects.link(o)
    return o


bar = bpy.data.objects["DOOR_BAR_L"]
ys = sum((bar.matrix_world @ v.co).y for v in bar.data.vertices) / len(bar.data.vertices)
A, B = fit(front, "GEN_A"), fit(rear, "GEN_B")
for o, keep_front in ((A, True), (B, False)):
    bm = bmesh.new(); bm.from_mesh(o.data)
    g = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=g, plane_co=(0, ys, 0), plane_no=(0, 1, 0),
                           clear_outer=keep_front, clear_inner=not keep_front)
    bm.to_mesh(o.data); bm.free()
bpy.ops.object.select_all(action="DESELECT")
A.select_set(True); B.select_set(True); bpy.context.view_layer.objects.active = A
bpy.ops.object.join()
A.name = A.data.name = "GEN_BODY"
bpy.context.scene.collection.objects.unlink(A); bpy.data.collections["GEN"].objects.link(A)
print("== splice at y %.3f" % ys)
print("== prep", pg.build())
print("== smooth", sg.smooth(iters=10, crease=30.0))
print("== export", eg.export())
lookdev.OUT = os.path.join(pg.ROOT, "export", "match_splice"); os.makedirs(lookdev.OUT, exist_ok=True)
lookdev.render(["cS", "cAR", "c20", "c23"])
bpy.ops.wm.save_mainfile()

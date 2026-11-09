"""Headless benchmark/verification of normal clean-up tools on a ~1.3M-triangle mesh (Blender 5.x).
Run: blender --background --factory-startup --python bench_normals.py"""
import bpy, bmesh, time, math
import numpy as np

T = time.perf_counter
log = []
def say(*a):
    s = " ".join(str(x) for x in a); print("BENCH", s, flush=True); log.append(s)

say("blender", bpy.app.version_string)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def cn_info(me):
    a = me.attributes.get("custom_normal")
    return (a.data_type, a.domain) if a else None

def corner_normals(me):
    a = np.empty(len(me.loops) * 3, np.float32); me.corner_normals.foreach_get("vector", a); return a.reshape(-1, 3)

def eval_mod(obj, label):
    """time a depsgraph evaluation of obj's current stack and return a numpy copy of its corner normals"""
    obj.data.update()
    t = T(); dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    ev = obj.evaluated_get(dg); m = ev.to_mesh(); t1 = T() - t
    t = T(); n = corner_normals(m); t2 = T() - t
    info = (cn_info(m), m.normals_domain, m.has_custom_normals)
    ev.to_mesh_clear()
    say(f"{label}: eval {t1:.2f}s, corner_normals read {t2:.2f}s, custom_normal={info}")
    return n

# ---------- build a ~1.3M-tri noisy 'body' ----------
t = T()
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=9, radius=1.0)
body = bpy.context.active_object; body.name = "body"; me = body.data
say(f"ico sphere: {len(me.vertices)} verts, {len(me.polygons)} tris, build {T()-t:.2f}s")
co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
co[:, 0] *= 2.0; co[:, 2] *= 0.7                                 # car-ish proportions (4 m x 2 m x 1.4 m)
rng = np.random.default_rng(1)
co += (rng.normal(0, 0.0004, (len(co), 1)) * (co / np.linalg.norm(co, axis=1, keepdims=True))).astype(np.float32)  # 0.4 mm noise
me.vertices.foreach_set("co", co.ravel()); me.update()
me.shade_smooth()
# spherical UVs so calc_tangents works
lvi = np.empty(len(me.loops), np.int64); me.loops.foreach_get("vertex_index", lvi)
p = co[lvi]; u = (np.arctan2(p[:, 1], p[:, 0]) / (2 * math.pi)) + 0.5; v = (p[:, 2] / 1.4) + 0.5
uvl = me.uv_layers.new(name="UVMap"); uvl.data.foreach_set("uv", np.stack([u, v], 1).astype(np.float32).ravel())

t = T(); vn = np.empty(len(me.vertices) * 3, np.float32); me.vertex_normals.foreach_get("vector", vn)
say(f"vertex_normals read {T()-t:.2f}s")
t = T(); me.normals_split_custom_set_from_vertices(vn.reshape(-1, 3))
say(f"normals_split_custom_set_from_vertices {T()-t:.2f}s -> custom_normal {cn_info(me)}, has_custom_normals={me.has_custom_normals}, normals_domain={me.normals_domain}")
t = T(); n0 = corner_normals(me); say(f"corner_normals foreach_get {T()-t:.2f}s ({len(n0)} corners)")
t = T(); me.normals_split_custom_set(n0); say(f"normals_split_custom_set (per corner) {T()-t:.2f}s")
t = T(); me.calc_tangents(uvmap="UVMap"); say(f"calc_tangents {T()-t:.2f}s")
t = T(); a = np.empty(len(me.loops) * 3, np.float32); me.loops.foreach_get("tangent", a)
b = np.empty(len(me.loops), np.float32); me.loops.foreach_get("bitangent_sign", b); say(f"tangent+bitangent_sign read {T()-t:.2f}s, signs {np.unique(b)}")
me.free_tangents()

# ---------- smoothed proxy: four ways ----------
def dup(name):
    o = body.copy(); o.data = body.data.copy(); o.name = name; scene.collection.objects.link(o); return o

def apply_stack(obj):
    """apply the whole modifier stack without bpy.ops (depsgraph + new_from_object)"""
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    ev = obj.evaluated_get(dg)
    new = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    old = obj.data; obj.modifiers.clear(); obj.data = new; bpy.data.meshes.remove(old)

def roughness(obj):
    """mean angle (deg) between each corner normal and the analytic ellipsoid normal: noise metric"""
    m = obj.data; n = corner_normals(m)
    c = np.empty(len(m.vertices) * 3, np.float32); m.vertices.foreach_get("co", c); c = c.reshape(-1, 3)
    l = np.empty(len(m.loops), np.int64); m.loops.foreach_get("vertex_index", l)
    g = c[l] / np.array([2.0 ** 2, 1.0, 0.7 ** 2], np.float32); g /= np.linalg.norm(g, axis=1, keepdims=True)
    return float(np.degrees(np.arccos(np.clip((n * g).sum(1), -1, 1))).mean())

say(f"body roughness (custom normals = noisy vertex normals): {roughness(body):.3f} deg")

px = dup("proxy_laplacian")
m = px.modifiers.new("lap", "LAPLACIANSMOOTH"); m.iterations = 2; m.lambda_factor = 1.0; m.use_volume_preserve = True
t = T(); apply_stack(px); say(f"LaplacianSmooth x2 applied (new_from_object) {T()-t:.2f}s")

pc = dup("proxy_corrective")
m = pc.modifiers.new("cs", "CORRECTIVE_SMOOTH"); m.iterations = 20; m.factor = 0.5; m.use_only_smooth = True; m.smooth_type = "LENGTH_WEIGHTED"
t = T(); apply_stack(pc); say(f"CorrectiveSmooth x20 only_smooth applied {T()-t:.2f}s")

pb = dup("proxy_bmesh")
t = T(); bm = bmesh.new(); bm.from_mesh(pb.data); say(f"bmesh from_mesh {T()-t:.2f}s")
t = T()
for _ in range(10):
    bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
say(f"bmesh.ops.smooth_vert x10 {T()-t:.2f}s")
t = T(); bm.to_mesh(pb.data); bm.free(); pb.data.update(); say(f"bmesh to_mesh {T()-t:.2f}s, custom_normal after bmesh: {cn_info(pb.data)}")

# proxy normals: drop custom normals so the proxy's own smooth vertex normals are what gets transferred
for o in (px, pc, pb):
    if o.data.has_custom_normals:
        o.data.attributes.remove(o.data.attributes["custom_normal"])
    say(f"{o.name} roughness of its own normals: {roughness(o):.3f} deg")

# ---------- Data Transfer (custom normals) ----------
for mapping in ("NEAREST_POLYNOR", "POLYINTERP_NEAREST", "POLYINTERP_LNORPROJ", "NEAREST_NORMAL"):
    d = body.modifiers.new("dt", "DATA_TRANSFER")
    if mapping == "NEAREST_POLYNOR":
        say(f"DT defaults: mix_mode={d.mix_mode} mix_factor={d.mix_factor} loop_mapping={d.loop_mapping} use_object_transform={d.use_object_transform}")
    d.object = pc; d.use_loop_data = True; d.data_types_loops = {"CUSTOM_NORMAL"}; d.loop_mapping = mapping
    n = eval_mod(body, f"DataTransfer {mapping}")
    # roughness of the evaluated result
    tmp = dup("tmp"); tmp.modifiers.clear()
    dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg)
    nm = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg); old = tmp.data; tmp.data = nm; bpy.data.meshes.remove(old)
    say(f"   result roughness {roughness(tmp):.3f} deg")
    bpy.data.objects.remove(tmp); body.modifiers.remove(d)

# DT limited by vertex group + mix factor
vg = body.vertex_groups.new(name="paint"); idx = np.nonzero(co[:, 2] > 0)[0].tolist(); vg.add(idx, 1.0, "REPLACE")
d = body.modifiers.new("dt", "DATA_TRANSFER"); d.object = pc; d.use_loop_data = True; d.data_types_loops = {"CUSTOM_NORMAL"}
d.loop_mapping = "POLYINTERP_NEAREST"; d.vertex_group = "paint"; d.mix_factor = 1.0
eval_mod(body, "DataTransfer POLYINTERP_NEAREST + vertex group (top half)")

# apply with bpy.ops in background via temp_override
t = T()
with bpy.context.temp_override(object=body, active_object=body, selected_objects=[body], selected_editable_objects=[body]):
    r = bpy.ops.object.modifier_apply(modifier=d.name, merge_customdata=False)
say(f"bpy.ops.object.modifier_apply via temp_override -> {r} in {T()-t:.2f}s; custom_normal {cn_info(body.data)}; roughness {roughness(body):.3f} deg")

# ---------- Weighted Normal ----------
w = body.modifiers.new("wn", "WEIGHTED_NORMAL")
say(f"WN defaults: mode={w.mode} weight={w.weight} thresh={w.thresh} keep_sharp={w.keep_sharp}")
w.mode = "FACE_AREA"; w.keep_sharp = True
eval_mod(body, "WeightedNormal FACE_AREA keep_sharp")
w.mode = "CORNER_ANGLE"; eval_mod(body, "WeightedNormal CORNER_ANGLE keep_sharp")
body.modifiers.remove(w)

# ---------- Shrinkwrap ----------
for meth in ("NEAREST_SURFACEPOINT", "PROJECT", "TARGET_PROJECT"):
    s = pc.modifiers.new("sw", "SHRINKWRAP"); s.target = body; s.wrap_method = meth; s.wrap_mode = "ON_SURFACE"
    if meth == "PROJECT":
        s.use_project_x = s.use_project_y = s.use_project_z = False   # no axis = along vertex normals
        s.use_negative_direction = True; s.use_positive_direction = True
    t = T(); dg = bpy.context.evaluated_depsgraph_get(); dg.update(); ev = pc.evaluated_get(dg); mm = ev.to_mesh()
    c2 = np.empty(len(mm.vertices) * 3, np.float32); mm.vertices.foreach_get("co", c2); el = T() - t
    c1 = np.empty(len(pc.data.vertices) * 3, np.float32); pc.data.vertices.foreach_get("co", c1)
    say(f"Shrinkwrap {meth} (proxy -> body) eval {el:.2f}s, mean move {np.abs(c2 - c1).reshape(-1,3).sum(1).mean()*1000:.3f} mm")
    ev.to_mesh_clear()
    pc.modifiers.remove(s)

# ---------- smooth by angle ----------
t = T(); body.data.set_sharp_from_angle(angle=math.radians(30)); say(f"Mesh.set_sharp_from_angle {T()-t:.2f}s; custom_normal kept: {cn_info(body.data)}")
small = bpy.data.objects.new("small", bpy.data.meshes.new("small")); scene.collection.objects.link(small)
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bm.to_mesh(small.data); bm.free()
try:
    with bpy.context.temp_override(object=small, active_object=small, selected_objects=[small], selected_editable_objects=[small]):
        r = bpy.ops.object.shade_auto_smooth(angle=math.radians(30))
    say(f"shade_auto_smooth in background -> {r}; modifiers {[ (m.name, m.type) for m in small.modifiers]}")
except Exception as e:
    say("shade_auto_smooth failed:", repr(e))

# ---------- free (float3) custom normals vs short2-only modifiers ----------
fr = bpy.data.objects.new("free", bpy.data.meshes.new("free")); scene.collection.objects.link(fr)
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.0); bm.to_mesh(fr.data); bm.free()
fr.data.shade_smooth()
att = fr.data.attributes.new("custom_normal", "FLOAT_VECTOR", "CORNER")
att.data.foreach_set("vector", np.tile(np.array([0, 0, 1], np.float32), len(fr.data.loops)))
say(f"free normals mesh: custom_normal {cn_info(fr.data)}, has_custom_normals={fr.data.has_custom_normals}, first corner normal {tuple(fr.data.corner_normals[0].vector)}")
w = fr.modifiers.new("wn", "WEIGHTED_NORMAL")
dg = bpy.context.evaluated_depsgraph_get(); dg.update(); ev = fr.evaluated_get(dg); m = ev.to_mesh()
nn = corner_normals(m); say(f"   after WeightedNormal on free normals: custom_normal {cn_info(m)}, all still +Z? {bool(np.allclose(nn, [0, 0, 1], atol=1e-4))}, modifier error: {getattr(fr.modifiers['wn'], 'is_active', None)}")
ev.to_mesh_clear()
try:
    fr.data.normals_split_custom_set_from_vertices(np.tile(np.array([1, 0, 0], np.float32), (len(fr.data.vertices), 1)))
    say(f"   normals_split_custom_set_from_vertices on free-normal mesh -> custom_normal {cn_info(fr.data)}, first {tuple(fr.data.corner_normals[0].vector)}")
except Exception as e:
    say("   normals_split_custom_set on free normals failed:", repr(e))


# ---------- triangulation vs fan-space custom normals ----------
bpy.ops.mesh.primitive_grid_add(x_subdivisions=400, y_subdivisions=400, size=2.0)
g = bpy.context.active_object; gm = g.data
gc = np.empty(len(gm.vertices) * 3, np.float32); gm.vertices.foreach_get("co", gc); gc = gc.reshape(-1, 3)
gc[:, 2] = 0.05 * np.sin(gc[:, 0] * 7) * np.cos(gc[:, 1] * 5) + rng.normal(0, 0.0004, len(gc))
gm.vertices.foreach_set("co", gc.ravel()); gm.update(); gm.shade_smooth()
target = np.tile(np.array([0.3, 0.0, 1.0], np.float32), (len(gm.vertices), 1)); target /= np.linalg.norm(target, axis=1, keepdims=True)
gm.normals_split_custom_set_from_vertices(target)
def per_vert_dev(mesh):
    n = corner_normals(mesh); l = np.empty(len(mesh.loops), np.int64); mesh.loops.foreach_get("vertex_index", l)
    return float(np.degrees(np.arccos(np.clip((n * target[l]).sum(1), -1, 1))).max())
say(f"grid quads ({len(gm.polygons)} quads): max deviation from set custom normal {per_vert_dev(gm):.4f} deg")
for keep in (False, True):
    tm = g.modifiers.new("tri", "TRIANGULATE"); tm.keep_custom_normals = keep
    dg = bpy.context.evaluated_depsgraph_get(); dg.update(); ev = g.evaluated_get(dg); mm = ev.to_mesh()
    say(f"   Triangulate modifier keep_custom_normals={keep}: max deviation {per_vert_dev(mm):.4f} deg")
    ev.to_mesh_clear(); g.modifiers.remove(tm)
bm = bmesh.new(); bm.from_mesh(gm); bmesh.ops.triangulate(bm, faces=bm.faces[:]); tmesh = bpy.data.meshes.new("t"); bm.to_mesh(tmesh); bm.free()
say(f"   bmesh.ops.triangulate: max deviation {per_vert_dev(tmesh):.4f} deg")
gm.calc_loop_triangles(); say(f"   loop_triangles (no mesh change) reuse corner_normals: deviation {per_vert_dev(gm):.4f} deg")

open(__file__.replace(".py", "_results.txt"), "w").write("\n".join(log))

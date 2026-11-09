"""Shading clean-up of REF_BODY by normal transfer (reports/Nova mesh cleanup and opening panels.md, section 1):
the shape does not move; only the shading normals change.

1. Proxy = a copy of REF_BODY (same topology) with its own custom normals removed.
2. Real creases (panel gaps, rib edges, lamp and window edges) found on the original geometry as edges sharper than
   CREASE_DEG; their vertices (+ PROTECT_RINGS edge rings) are pinned so they stay crisp.
3. Proxy smoothed hard with Corrective Smooth (Only Smooth, Length Weighted, Pin Boundaries) - takes out the ripples
   and streaks the custom normals were showing.
4. Sharp edges re-marked on the smoothed proxy and copied to REF_BODY; every face set smooth (the model had 170k
   faces flagged flat-shaded, 73k of them paint - each showed as a facet).
5. Data Transfer modifier on REF_BODY: Face Corner Data / Custom Normals from the proxy, Topology mapping, Replace,
   factor 1.0 (set explicitly: the API docs and the source disagree on its default); applied; proxy deleted.
Runs after prep_reference / polish_ref, before frames_ref / details_ref (split_lamps copies these normals).
"""
import math

import numpy as np

import bpy

CREASE_DEG = 60.0          # 38 kept the bumper rib edges sharp and their zig-zag showed
PROTECT_RINGS = 1
# bumpers (front y < -1.44, rear y > 1.45, below the bumper top): no creases kept - the model's rib grooves zig-zag
# across its triangles and showed as ragged dark lines; the red pinstripes come from the texture, not the grooves
SOFT_BOXES = [(-0.85, 0.85, -2.0, -1.44, 0.15, 0.545), (-0.85, 0.85, 1.45, 2.0, 0.15, 0.585)]
ITERATIONS, FACTOR = 30, 0.5


def _apply(obj, mod):
    with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def _sharp(me):
    a = me.attributes.get("sharp_edge")
    s = np.zeros(len(me.edges), bool)
    if a is not None:
        a.data.foreach_get("value", s)
    return s


def transfer(name="REF_BODY"):
    o = bpy.data.objects[name]
    me = o.data
    pm = me.copy(); pm.name = "NRM_PROXY"
    proxy = bpy.data.objects.new("NRM_PROXY", pm)
    bpy.context.scene.collection.objects.link(proxy)
    proxy.matrix_world = o.matrix_world
    if "custom_normal" in pm.attributes:
        pm.attributes.remove(pm.attributes["custom_normal"])
    # creases on the original shape
    pm.set_sharp_from_angle(angle=math.radians(CREASE_DEG))
    sharp = _sharp(pm)
    E = np.empty(len(pm.edges) * 2, np.int64); pm.edges.foreach_get("vertices", E); E = E.reshape(-1, 2)
    co = np.empty(len(pm.vertices) * 3); pm.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    soft = np.zeros(len(pm.vertices), bool)
    for x0, x1, y0, y1, z0, z1 in SOFT_BOXES:
        soft |= ((co[:, 0] > x0) & (co[:, 0] < x1) & (co[:, 1] > y0) & (co[:, 1] < y1) & (co[:, 2] > z0) & (co[:, 2] < z1))
    sharp &= ~(soft[E[:, 0]] & soft[E[:, 1]])
    pin = np.zeros(len(pm.vertices), bool); pin[E[sharp].ravel()] = True
    for _ in range(PROTECT_RINGS):
        e = pin[E[:, 0]] | pin[E[:, 1]]
        pin[E[e].ravel()] = True
    vg = proxy.vertex_groups.new(name="SMOOTH")
    vg.add(np.where(~pin)[0].tolist(), 1.0, "REPLACE")
    cs = proxy.modifiers.new("CS", "CORRECTIVE_SMOOTH")
    cs.use_only_smooth = True
    cs.smooth_type = "LENGTH_WEIGHTED"
    cs.use_pin_boundary = True
    cs.iterations = ITERATIONS
    cs.factor = FACTOR
    cs.vertex_group = "SMOOTH"
    _apply(proxy, cs)
    # proxy shading: smooth everywhere, sharp only along creases of the smoothed shape
    pm.set_sharp_from_angle(angle=math.radians(CREASE_DEG))
    pm.polygons.foreach_set("use_smooth", [True] * len(pm.polygons))
    sharp2 = _sharp(pm) & ~(soft[E[:, 0]] & soft[E[:, 1]])
    # destination: same sharp edges, all faces smooth, then the transfer
    if "sharp_edge" not in me.attributes:
        me.attributes.new("sharp_edge", "BOOLEAN", "EDGE")
    me.attributes["sharp_edge"].data.foreach_set("value", sharp2)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    dt = o.modifiers.new("NRM", "DATA_TRANSFER")
    dt.object = proxy
    dt.use_loop_data = True
    dt.data_types_loops = {"CUSTOM_NORMAL"}
    dt.loop_mapping = "TOPOLOGY"
    dt.mix_mode = "REPLACE"
    dt.mix_factor = 1.0
    _apply(o, dt)
    bpy.data.objects.remove(proxy)
    bpy.data.meshes.remove(pm)
    return {"pinned_verts": int(pin.sum()), "crease_edges_orig": int(sharp.sum()), "sharp_edges_final": int(sharp2.sum()),
            "custom_normals": me.has_custom_normals}


if __name__ == "__main__":
    print("==", transfer())

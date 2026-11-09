"""Phase 1 - procedural Nova GTE: master dimensions, reference bounds and axle locators.

Frame (same as the rest of the project): metres, x+ = car's left, y- = front, z up, ground at z = 0.
The bounding box is centred on the world origin in x and y and stands on z = 0.
Axle positions along y come from the FIA overhangs (front 670 mm, rear 609 mm; docs/SPEC_SHEET.md), which with
the 2343 mm wheelbase add up to the 3622 mm length - so the axles are NOT symmetric about the origin.
Axle locator height = static wheel-centre height of a 175/65 R14 tyre (0.2916 m, brochure tyre size).

Run: blender -b --factory-startup --python blender/scripts/proc/phase1_bounds.py
Writes blender/nova_proc.blend.
"""
import json
import os

import bmesh
import bpy

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "nova_proc.blend")

DIM = {                                  # metres; source tags in docs/SPEC_SHEET.md
    "wheelbase": 2.343,                  # FIA
    "length": 3.622,                     # FIA
    "width": 1.532,                      # brochure (excluding mirrors)
    "height": 1.365,                     # brochure
    "track_front": 1.320,                # SOURCED
    "track_rear": 1.300,                 # as specified by Nik for this build (spec sheet also lists 1.307)
    "overhang_front": 0.670,             # FIA
    "overhang_rear": 0.609,              # FIA
    "wheel_radius": 0.0254 * 14 / 2 + 0.175 * 0.65,   # 175/65 R14 -> 0.2916
}
TOL = 0.001                              # 1 mm


class NovaSpecError(Exception):
    """Geometry deviates from the master dimensions."""


def collection(name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


def clean_mesh(ob):
    """Hygiene block: merge by distance + consistent outward normals, then back to object mode."""
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.view_layer.objects:
        o.select_set(o is ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def chassis_guide(coll):
    L, W, H = DIM["length"], DIM["width"], DIM["height"]
    old = bpy.data.objects.get("Chassis_Guide")
    if old:
        bpy.data.objects.remove(old)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:                     # unit cube (-0.5..0.5) -> box, base on the ground
        v.co.x *= W
        v.co.y *= L
        v.co.z = (v.co.z + 0.5) * H
    me = bpy.data.meshes.new("Chassis_Guide")
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("Chassis_Guide", me)
    coll.objects.link(ob)
    ob.display_type = "WIRE"
    ob.hide_render = True
    clean_mesh(ob)
    return ob


def axle_locators(coll):
    y_front = -DIM["length"] / 2 + DIM["overhang_front"]
    y_rear = y_front + DIM["wheelbase"]
    out = {}
    for name, y, track in (("Axle_Front", y_front, DIM["track_front"]), ("Axle_Rear", y_rear, DIM["track_rear"])):
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old)
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = "ARROWS"
        e.empty_display_size = track / 2          # arrow arms reach the wheel centres along x
        e.location = (0.0, y, DIM["wheel_radius"])
        e["track"] = track
        coll.objects.link(e)
        out[name] = e
    return out


def store_dimensions():
    sc = bpy.context.scene
    sc["nova_gte_dimensions"] = {k: float(v) for k, v in DIM.items()}
    sc["nova_gte_dimensions_json"] = json.dumps({k: round(v, 6) for k, v in DIM.items()}, sort_keys=True)
    sc["nova_gte_frame"] = "metres; x+ = car left, y- = front, z up, ground z = 0"


def audit(guide, axles):
    """Measure what was built and compare with DIM; raise NovaSpecError on any deviation >= 1 mm."""
    bpy.context.view_layer.update()
    vs = [guide.matrix_world @ v.co for v in guide.data.vertices]
    xs, ys, zs = [v.x for v in vs], [v.y for v in vs], [v.z for v in vs]
    meas = {
        "length (y extent)": (max(ys) - min(ys), DIM["length"]),
        "width (x extent)": (max(xs) - min(xs), DIM["width"]),
        "height (z extent)": (max(zs) - min(zs), DIM["height"]),
        "base z": (min(zs), 0.0),
        "centre x": ((max(xs) + min(xs)) / 2, 0.0),
        "centre y": ((max(ys) + min(ys)) / 2, 0.0),
    }
    fa, ra = axles["Axle_Front"].matrix_world.translation, axles["Axle_Rear"].matrix_world.translation
    meas.update({
        "wheelbase (axle to axle)": ((ra - fa).length, DIM["wheelbase"]),
        "front overhang (nose to front axle)": (fa.y - min(ys), DIM["overhang_front"]),
        "rear overhang (rear axle to tail)": (max(ys) - ra.y, DIM["overhang_rear"]),
        "front axle x": (fa.x, 0.0), "rear axle x": (ra.x, 0.0),
        "front axle z (wheel centre)": (fa.z, DIM["wheel_radius"]),
        "rear axle z (wheel centre)": (ra.z, DIM["wheel_radius"]),
        "front track (stored)": (axles["Axle_Front"]["track"], DIM["track_front"]),
        "rear track (stored)": (axles["Axle_Rear"]["track"], DIM["track_rear"]),
        "scene dict wheelbase": (bpy.context.scene["nova_gte_dimensions"]["wheelbase"], DIM["wheelbase"]),
    })
    strays = [o.name for o in bpy.context.scene.objects if o.name in ("Cube", "Camera", "Light")]
    meas["stray startup objects"] = (float(len(strays)), 0.0)
    topo = (len(guide.data.vertices), len(guide.data.edges), len(guide.data.polygons))
    lines = ["NOVA GTE PHASE 1 - GEOMETRIC VERIFICATION", "%-38s %10s %10s %9s" % ("check", "measured", "spec", "dev mm")]
    bad = []
    for k, (m, s) in meas.items():
        dev = (m - s) * 1000
        flag = "" if abs(dev) < TOL * 1000 else "  <-- FAIL"
        lines.append("%-38s %10.4f %10.4f %9.3f%s" % (k, m, s, dev, flag))
        if flag:
            bad.append(k)
    lines.append("Chassis_Guide topology (verts, edges, faces): %s  %s" % (topo, "ok" if topo == (8, 12, 6) else "<-- FAIL"))
    if topo != (8, 12, 6):
        bad.append("topology")
    print("\n".join(lines))
    if bad:
        raise NovaSpecError("deviation >= 1 mm or bad topology: " + ", ".join(bad))
    print("RESULT: PASS (all within 1 mm)")


def clear_startup_scene():
    """--factory-startup brings the default Cube / Camera / Light: remove them (and their data) so only our objects exist."""
    for name in ("Cube", "Camera", "Light"):
        ob = bpy.data.objects.get(name)
        if ob is not None:
            bpy.data.objects.remove(ob)
    bpy.data.orphans_purge(do_recursive=True)          # their mesh / camera / light data


def main():
    clear_startup_scene()
    coll = collection("NOVA_PROC")
    guide = chassis_guide(coll)
    axles = axle_locators(coll)
    store_dimensions()
    audit(guide, axles)
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()

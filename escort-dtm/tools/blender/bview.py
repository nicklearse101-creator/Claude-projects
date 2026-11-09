"""Viewport helpers for checking work in Blender (not part of the build)."""
import bpy
from mathutils import Vector


def setview(eye, target, lens=35, cull=False):
    """Put the 3D viewport's camera at eye looking at target (Blender world coordinates)."""
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            sp = area.spaces[0]; r3 = sp.region_3d
            sp.lens = lens; sp.clip_start = 0.01
            sp.shading.type = "SOLID"; sp.shading.show_backface_culling = cull
            sp.overlay.show_relationship_lines = False
            eye = Vector(eye); d = (Vector(target) - eye).normalized()
            r3.view_perspective = "PERSP"
            r3.view_rotation = d.to_track_quat("-Z", "Y")
            r3.view_distance = 0.05
            r3.view_location = eye + d * 0.05
            r3.update()


def isolate(keep, hide_donor=True):
    """Hide every mesh in the main scene for which keep(obj) is false; returns the names hidden (for show())."""
    hidden = []
    for o in bpy.data.scenes["Scene"].objects:
        if o.type != "MESH":
            continue
        if keep(o):
            o.hide_set(False)
        elif not o.hide_get():
            o.hide_set(True); hidden.append(o.name)
    return hidden


def show(names):
    for n in names:
        o = bpy.data.objects.get(n)
        if o and not o.get("no_export"):
            o.hide_set(False)

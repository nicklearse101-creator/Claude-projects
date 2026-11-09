"""Look-development renders for checking the model against the reference photos (runs inside Blender).

Not used by the AC export (AC gets the ac_* material properties); this only sets Blender-side shading so the
matched-camera renders read like a photograph: EEVEE, a bundled daylight HDRI, metallic gun-metal paint with a
clear coat, tinted glass, matt plastics, rubber. Writes export/match/<cam>_ee.png (transparent background).
"""
import os
import runpy

import bpy

ROOT = r"D:\Claude\vauxhall_nova_gte_1989"
OUT = os.path.join(ROOT, "export", "match")

LOOK = {  # name: (base rgba, metallic, roughness, coat, alpha)
    "paint_gunmetal": ((0.10, 0.108, 0.115, 1), 0.0, 0.32, 1.0, 1.0),   # dielectric base + clear coat (no 0.55 metallic)
    "glass_tint": ((0.010, 0.012, 0.012, 1), 0.0, 0.01, 1.0, 0.55),   # light tint, reflective (photos: cabin visible)
    "glass_sunroof": ((0.02, 0.025, 0.03, 1), 0.0, 0.02, 0.0, 0.85),
    "trim_black": ((0.018, 0.018, 0.018, 1), 0.0, 0.45, 0.0, 1.0),
    "trim_grey": ((0.13, 0.13, 0.135, 1), 0.0, 0.75, 0.0, 1.0),
    "lamp_clear": ((0.90, 0.90, 0.88, 1), 0.0, 0.22, 1.0, 0.45),
    "lamp_red": ((0.50, 0.02, 0.02, 1), 0.0, 0.10, 1.0, 1.0),
    "lamp_amber": ((0.85, 0.36, 0.02, 1), 0.0, 0.10, 1.0, 1.0),
    "panel_gap": ((0.005, 0.005, 0.005, 1), 0.0, 0.9, 0.0, 1.0),
    "arch_liner": ((0.010, 0.010, 0.010, 1), 0.0, 0.9, 0.0, 1.0),
    "rubber_black": ((0.012, 0.012, 0.012, 1), 0.0, 0.7, 0.0, 1.0),
    "tyre_rubber": ((0.016, 0.016, 0.016, 1), 0.0, 0.75, 0.0, 1.0),
    "rim_alloy": ((0.62, 0.63, 0.65, 1), 1.0, 0.30, 0.3, 1.0),
    "rim_alloy_plate": ((0.62, 0.63, 0.65, 1), 1.0, 0.40, 0.0, 1.0),
    "disc_steel": ((0.30, 0.29, 0.28, 1), 1.0, 0.65, 0.0, 1.0),
    "brake_backplate": ((0.02, 0.02, 0.02, 1), 0.0, 0.6, 0.0, 1.0),
    "lamp_glass_red": ((0.42, 0.01, 0.01, 1), 0.0, 0.05, 1.0, 0.92),
    "lamp_glass_amber": ((0.85, 0.32, 0.01, 1), 0.0, 0.05, 1.0, 0.92),
    "lamp_glass_clear": ((0.75, 0.75, 0.73, 1), 0.0, 0.05, 1.0, 0.70),
    "plate_white": ((0.80, 0.80, 0.77, 1), 0.0, 0.30, 0.0, 1.0),
    "plate_yellow": ((0.80, 0.60, 0.03, 1), 0.0, 0.30, 0.0, 1.0),
}


def setup(hdri="courtyard.exr", strength=1.0):
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            continue
    world = sc.world or bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexEnvironment")
    path = os.path.join(bpy.utils.system_resource("DATAFILES", path="studiolights/world"), hdri)
    tex.image = bpy.data.images.load(path, check_existing=True)
    bg = nt.nodes.new("ShaderNodeBackground"); bg.inputs["Strength"].default_value = strength
    outn = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(tex.outputs["Color"], bg.inputs["Color"]); nt.links.new(bg.outputs["Background"], outn.inputs["Surface"])
    # occlusion so cabins / wheel wells read dark like the photos (EEVEE Next: ray tracing, fast GI, sun shadow)
    for obj_, attr, val in ((sc.eevee, "use_raytracing", True), (sc.eevee, "use_fast_gi", True),
                            (sc.eevee, "use_shadows", True), (sc.eevee, "taa_render_samples", 64),
                            (world, "use_sun_shadow", True), (world, "sun_threshold", 1.0)):
        if hasattr(obj_, attr):
            try:
                setattr(obj_, attr, val)
            except Exception:
                pass
    for name, (rgba, met, rough, coat, alpha) in LOOK.items():
        m = bpy.data.materials.get(name)
        if not m:
            continue
        m.use_nodes = True
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = rgba
        b.inputs["Metallic"].default_value = met
        b.inputs["Roughness"].default_value = rough
        for key in ("Coat Weight", "Clearcoat"):
            if key in b.inputs:
                b.inputs[key].default_value = coat
        if "Coat Roughness" in b.inputs:
            b.inputs["Coat Roughness"].default_value = 0.03
        b.inputs["Alpha"].default_value = alpha
        if alpha < 1:
            for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
                if hasattr(m, attr):
                    try:
                        setattr(m, attr, val)
                    except Exception:
                        pass
    # pinstripe paint: the paint look, its texture tinted from the export colour to the look colour
    st = bpy.data.materials.get("paint_stripes")
    if st and st.use_nodes and "stripe_bg" in st:
        rgba, met, rough, coat, _ = LOOK["paint_gunmetal"]
        nt = st.node_tree
        b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Metallic"].default_value = met; b.inputs["Roughness"].default_value = rough
        for key in ("Coat Weight", "Clearcoat"):
            if key in b.inputs:
                b.inputs[key].default_value = coat
        tx = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None)
        mul = next((n for n in nt.nodes if n.name == "LOOK_TINT"), None)
        if tx and mul is None:
            mul = nt.nodes.new("ShaderNodeMix"); mul.name = "LOOK_TINT"; mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"
            mul.inputs["Factor"].default_value = 1.0
            nt.links.new(tx.outputs["Color"], mul.inputs["A"]); nt.links.new(mul.outputs["Result"], b.inputs["Base Color"])
        if mul:
            bg = st["stripe_bg"]
            mul.inputs["B"].default_value = (*[rgba[i] / max(bg[i], 1e-4) for i in range(3)], 1)
    sc.render.film_transparent = True
    try:
        sc.view_settings.view_transform = "AgX"
    except Exception:
        sc.view_settings.view_transform = "Filmic"
    return sc.render.engine


def render(names=None):
    setup()                                  # (was never called here: matched renders used the raw build materials)
    rm = runpy.run_path(os.path.join(ROOT, "blender", "scripts", "render_matched.py"), run_name="nova_rm")
    sc = bpy.context.scene
    hidden = []
    for o in bpy.data.objects:
        if o.get("no_export") and o.type == "MESH" and not o.hide_render:
            o.hide_render = True; hidden.append(o)
    out = []
    for name, c in rm["cameras"]().items():
        if names and name not in names:
            continue
        cam = bpy.data.objects.get("MATCH_" + name)
        if cam is None:
            rm["render"]([name])
            cam = bpy.data.objects["MATCH_" + name]
        from mathutils import Matrix
        cam.matrix_world = Matrix.Translation(c["loc"]) @ c["rot"].to_4x4()
        cam.data.lens = c["f"] * 36.0 / c["W"]; cam.data.sensor_width = 36.0; cam.data.sensor_fit = "HORIZONTAL"
        sc.camera = cam
        sc.render.resolution_x, sc.render.resolution_y = c["W"], c["H"]
        sc.render.resolution_percentage = 100 if c["W"] < 2000 else 50
        sc.render.filepath = os.path.join(OUT, name + "_ee.png")
        bpy.ops.render.render(write_still=True)
        out.append(sc.render.filepath)
    for o in hidden:
        o.hide_render = False
    sc.render.resolution_percentage = 100
    return out

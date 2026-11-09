"""Feature map of the reference body (REF_BODY): coloured outlines + labels in collection SHELL_MAP.

Coordinates: car frame (metres) - x + = car's left, y - = front, z up from the ground. Measured from the depth scans
(tools/map_features.py, +-3 mm) and the gridded orthographic cavity renders (+-1 cm); see docs/SHELL_MAP.md.
Each feature: (name, kind, view plane, outline points in that plane). Planes: 'L'/'R' side (y, z) drawn just outside
the skin at x = +-0.80; 'F' front (x, z) at y = -1.90; 'B' rear (x, z) at y = 1.86; 'T' top (x, y) at z = 1.42.
"""

KIND_COL = {"glass": (0.1, 0.6, 1.0), "shut": (1.0, 0.15, 0.15), "bumper": (1.0, 0.6, 0.0), "lamp": (1.0, 0.95, 0.1),
            "detail": (0.2, 1.0, 0.3), "trim": (0.75, 0.3, 1.0), "note": (1.0, 1.0, 1.0)}


def rect(a0, b0, a1, b1):
    return [(a0, b0), (a1, b0), (a1, b1), (a0, b1), (a0, b0)]


def side(pts):            # same outline on both sides
    return [("L", pts), ("R", pts)]


def mirror_x(pts):
    return [(-a, b) for a, b in pts]


F = []
def add(name, kind, plane, pts, label_at=None):
    F.append((name, kind, plane, pts, label_at))


# ---- glass / openings
add("Windscreen (surface, striated)", "glass", "F", [(-0.65, 0.93), (0.65, 0.93), (0.54, 1.29), (-0.54, 1.29), (-0.65, 0.93)])
add("Windscreen", "glass", "T", [(-0.65, -0.69), (0.65, -0.69), (0.55, -0.27), (-0.55, -0.27), (-0.65, -0.69)])
for s in "LR":
    add("Door glass (open)", "glass", s, [(-0.22, 0.855), (0.415, 0.855), (0.415, 1.235), (-0.22, 1.235), (-0.22, 0.855)])
    add("Front vent glass (open)", "glass", s, [(-0.68, 0.86), (-0.24, 0.86), (-0.24, 1.15), (-0.68, 0.86)])
    add("Quarter glass (open)", "glass", s, [(0.62, 0.883), (1.36, 0.883), (1.10, 1.22), (0.62, 1.22), (0.62, 0.883)])
add("Tailgate glass (open)", "glass", "B", rect(-0.545, 0.92, 0.545, 1.28))
add("Tailgate glass", "glass", "T", rect(-0.545, 1.305, 0.55, 1.60))
# ---- shut lines / panels
for s in "LR":
    add("Door shut lines", "shut", s, [(-0.678, 0.288), (0.455, 0.288), (0.455, 1.27), (-0.20, 1.27), (-0.678, 0.87), (-0.678, 0.288)])
add("Bonnet (shut lines x +-0.63)", "shut", "T", [(-0.62, -1.68), (0.62, -1.68), (0.635, -1.2), (0.64, -0.87), (-0.64, -0.87), (-0.635, -1.2), (-0.62, -1.68)])
add("Bonnet creases", "trim", "T", [(0.41, -1.66), (0.476, -0.95), (0.47, -0.89)])
add("", "trim", "T", [(-0.41, -1.66), (-0.476, -0.95), (-0.47, -0.89)])
add("Transverse line y -1.27 (not on the real car)", "note", "T", [(-0.42, -1.267), (0.42, -1.267)])
add("Tailgate", "shut", "B", [(-0.565, 0.575), (0.565, 0.575), (0.565, 1.30), (-0.565, 1.30), (-0.565, 0.575)])
add("Roof spoiler", "trim", "T", rect(-0.47, 1.18, 0.47, 1.32))
add("Roof (drip rails x +-0.59, ribs x +-0.39)", "trim", "T", rect(-0.59, -0.27, 0.59, 1.18))
add("Scuttle vent + wipers", "trim", "T", rect(-0.47, -0.82, 0.47, -0.71))
# ---- bumpers / lower body
add("Front bumper (ribs z 0.50-0.56)", "bumper", "F", rect(-0.77, 0.19, 0.77, 0.53))
add("Front plate recess", "detail", "F", rect(-0.25, 0.33, 0.25, 0.45))
add("Front air slots", "detail", "F", rect(0.25, 0.36, 0.34, 0.40))
add("", "detail", "F", rect(-0.34, 0.36, -0.25, 0.40))
add("Tow-eye cover", "detail", "F", rect(-0.49, 0.30, -0.39, 0.38))
add("Rear bumper (top z 0.576, ribs 0.52-0.55)", "bumper", "B", rect(-0.78, 0.19, 0.78, 0.576))
add("Rear plate recess", "detail", "B", rect(-0.25, 0.626, 0.25, 0.748))
add("Tailgate handle bar", "trim", "B", rect(-0.31, 0.772, 0.31, 0.817))
add("GTE badge", "detail", "B", rect(0.36, 0.76, 0.54, 0.80))
add("Exhaust tip", "detail", "B", rect(0.51, 0.26, 0.60, 0.33))
add("Tailgate lock / badge", "detail", "B", rect(-0.03, 0.85, 0.03, 0.90))
add("Bumper fitting", "detail", "B", rect(0.526, 0.35, 0.569, 0.41))
add("Rear fog lamp?", "lamp", "B", rect(-0.541, 0.32, -0.474, 0.37))
for s in "LR":
    add("Front bumper side", "bumper", s, rect(-1.84, 0.19, -1.48, 0.53))
    add("Rear bumper side", "bumper", s, rect(1.47, 0.19, 1.79, 0.576))
    add("Side skirt (sill groove z 0.236)", "bumper", s, [(-0.83, 0.19), (0.81, 0.19), (0.81, 0.40), (0.50, 0.288), (-0.83, 0.288), (-0.83, 0.19)])
    add("Front arch", "shut", s, rect(-1.48, 0.23, -0.833, 0.64))
    add("Rear arch", "shut", s, rect(0.81, 0.205, 1.47, 0.585))
# ---- lamps / front
add("Headlamp", "lamp", "F", rect(0.405, 0.524, 0.624, 0.674))
add("Headlamp", "lamp", "F", rect(-0.624, 0.524, -0.405, 0.674))
add("Indicator", "lamp", "F", rect(0.624, 0.524, 0.698, 0.674))
add("Indicator", "lamp", "F", rect(-0.698, 0.524, -0.624, 0.674))
add("Grille (GTE badge)", "trim", "F", rect(-0.39, 0.53, 0.39, 0.665))
add("Bonnet front edge", "shut", "F", [(-0.62, 0.70), (0.62, 0.70)])
add("Griffin badge", "detail", "F", rect(-0.03, 0.73, 0.03, 0.755))
add("Tail lamp", "lamp", "B", rect(0.565, 0.565, 0.68, 0.82))
add("Tail lamp", "lamp", "B", rect(-0.68, 0.565, -0.565, 0.82))
# ---- side details
for s in "LR":
    add("Mirror", "detail", s, rect(-0.53, 0.88, -0.40, 0.97))
    add("Door handle + lock", "detail", s, rect(0.31, 0.69, 0.40, 0.80))
    add("GTE door decal", "detail", s, rect(-0.65, 0.43, -0.39, 0.49))
    add("Side repeater", "lamp", s, rect(-0.80, 0.725, -0.755, 0.755))
    add("Tail lamp side", "lamp", s, rect(1.60, 0.565, 1.68, 0.82))
    add("Headlamp / indicator side", "lamp", s, rect(-1.82, 0.524, -1.66, 0.674))
    add("Wing crease z 0.71 / quarter swage z 0.75", "trim", s, [(-1.60, 0.71), (-0.85, 0.71)])
    add("", "trim", s, [(0.90, 0.70), (1.25, 0.735), (1.60, 0.765)])
add("Fuel flap (model: behind the arch; real car: ahead of it)", "note", "R", rect(1.40, 0.62, 1.46, 0.68))
add("Unidentified round fitting", "note", "R", rect(0.49, 1.00, 0.53, 1.04))


def to3(plane, a, b):
    return {"L": (0.80, a, b), "R": (-0.80, a, b), "F": (a, -1.90, b), "B": (a, 1.86, b), "T": (a, b, 1.42)}[plane]


def material(kind):
    import bpy
    name = "MAP_" + kind
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs[0].default_value = (*KIND_COL[kind], 1); em.inputs[1].default_value = 2.0
    out = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(em.outputs[0], out.inputs[0])
    m.diffuse_color = (*KIND_COL[kind], 1)
    return m


def build():
    import bpy
    coll = bpy.data.collections.get("SHELL_MAP") or bpy.data.collections.new("SHELL_MAP")
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    for o in list(coll.objects):
        bpy.data.objects.remove(o)
    for i, (name, kind, plane, pts, _) in enumerate(F):
        cu = bpy.data.curves.new("MAP_%03d" % i, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.004
        sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
        for k, (a, b) in enumerate(pts):
            sp.points[k].co = (*to3(plane, a, b), 1)
        cu.materials.append(material(kind))
        o = bpy.data.objects.new("MAP_%03d_%s" % (i, name[:30] or "line"), cu); coll.objects.link(o)
        if not name:
            continue
        # label beside the outline's first point, lying in the view plane, facing the viewer
        a = min(p[0] for p in pts); b = max(p[1] for p in pts)
        tc = bpy.data.curves.new("MAPT_%03d" % i, "FONT"); tc.body = name; tc.size = 0.035
        tc.materials.append(material(kind))
        t = bpy.data.objects.new("MAPT_%03d_%s" % (i, name[:30]), tc); coll.objects.link(t)
        import math
        if plane == "L":
            t.location = (0.81, a, b + 0.012); t.rotation_euler = (math.pi / 2, 0, math.pi / 2)
        elif plane == "R":
            t.location = (-0.81, max(p[0] for p in pts), b + 0.012); t.rotation_euler = (math.pi / 2, 0, -math.pi / 2)
        elif plane == "F":
            t.location = (a, -1.91, b + 0.012); t.rotation_euler = (math.pi / 2, 0, 0)
        elif plane == "B":
            t.location = (max(p[0] for p in pts), 1.87, b + 0.012); t.rotation_euler = (math.pi / 2, 0, math.pi)
        else:
            t.location = (a, b + 0.012, 1.43); t.rotation_euler = (0, 0, 0)
    return len(F)


if __name__ == "__main__":
    print("==", build())

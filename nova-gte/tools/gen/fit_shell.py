"""Make the measured shell the side skin, and trim it under the parts that stay separate.

The door, rocker and roof panels were built on the old stretched section; the shell now carries the true one
(belt shoulder rolling in to the glass, measured glass plane, drip, roof), so it *is* the door skin, sill and
roof, and those three panels go to NOVA_OLD. The parts that stay separate - bonnet, front wing (arch flange,
measured front plane, roll into the bonnet), scuttle, sill skirt, front end - keep their own surfaces, and the
shell is trimmed where it would sit under them.

blender -b in.blend --python tools/gen/fit_shell.py -- out.blend
"""
import json
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args else None

TO_OLD = ("Door_Left", "Rocker_Left", "Roof_Panel")
# The scuttle is NOT in KEEP. Culling the shell under it opened the shell's skin between the bonnet and the
# windscreen, and that opening ran into the screen aperture, so the two became one ragged hole across the
# whole scuttle - which is what the screen base looked like. The shell keeps its surface there and the
# scuttle panel sits on it.
KEEP = ("PANEL_R_L", "PANEL_R_R", "Hood_Panel", "Wing_Front_Left", "LAMP_PANEL", "BUMPER_F", "BUMPER_F_LIP",
        "GRILLE_SURROUND")
NEAR = 0.030

old = bpy.data.collections.get("NOVA_OLD")
for n in TO_OLD:
    o = bpy.data.objects.get(n)
    if o and old:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        old.objects.link(o)
        print("moved %s to NOVA_OLD" % n)

dg = bpy.context.evaluated_depsgraph_get()
verts, tris = [], []
for n in KEEP:
    o = bpy.data.objects.get(n)
    if o is None:
        continue
    me = o.evaluated_get(dg).to_mesh(); m = o.matrix_world; n0 = len(verts)
    verts += [tuple(m @ v.co) for v in me.vertices]
    for f in me.polygons:
        vs = list(f.vertices)
        for k in range(1, len(vs) - 1):
            tris.append((n0 + vs[0], n0 + vs[k], n0 + vs[k + 1]))
    o.evaluated_get(dg).to_mesh_clear()
bvh = BVHTree.FromPolygons(verts, tris)

sh = bpy.data.objects["Body_Shell"]
bm = bmesh.new(); bm.from_mesh(sh.data); bm.faces.ensure_lookup_table()
m = sh.matrix_world
# Covered, not merely near: a face goes only if a short ray along its own normal - out or in - meets a kept
# panel. Trimming by distance also ate the strip just beyond each panel's edge, which left a see-through slit
# at the front door shut behind the wing.
bm.normal_update()
kill = []
for f in bm.faces:
    c = m @ f.calc_center_median()
    n = (m.to_3x3() @ f.normal).normalized()
    if bvh.ray_cast(c, n, 0.060)[0] is not None or bvh.ray_cast(c, -n, 0.060)[0] is not None:
        kill.append(f)
# The shut-line tube (2026-10-27 (12)). Ahead of the windscreen the shell's upper rows - glass band, drip, roof -
# have nowhere to go and collapse onto the bonnet's shut line, into a closed tube about 6 x 12 mm at x 0.600-0.606
# running from y -1.62 to -0.70, standing 1-51 mm ABOVE the shut. Its faces point sideways (+-x), so the
# normal-ray test above never meets a panel and keeps them; that tube is the silver line that sat in the
# bonnet-to-wing gap. Nothing of the shell belongs on the shut line itself - the bonnet and the wing meet there -
# so any shell face within TUBE_W of the shared shut line (blender/data/shut_bonnet_wing.json), and not below
# it, goes.
TUBE_W = 0.012
_sj = os.path.join(ROOT, "blender", "data", "shut_bonnet_wing.json")
if os.path.exists(_sj):
    _S = json.load(open(_sj))
    _yb = max(p[1] for p in _S["bonnet"])
    _P = sorted([tuple(p) for p in _S["bonnet"]] + [tuple(p) for p in _S.get("scuttle", []) if p[1] > _yb + 1e-4],
                key=lambda p: p[1])
    sy = np.array([p[1] for p in _P]); sx = np.array([p[0] for p in _P]); sz = np.array([p[2] for p in _P])
    killed = set(kill)
    tube = []
    for f in bm.faces:
        if f in killed:
            continue
        c = m @ f.calc_center_median()
        # Only along the BONNET (y <= its rear edge, -0.781). Behind it, beside the scuttle, the shell is not a
        # collapsed tube but the real side wall at the foot of the A-pillar; culling it there (2026-10-27 (12))
        # opened a 35 x 40 mm see-through hole at x 0.605, y -0.74..-0.70 - the notch at the A-pillar (13)/(14).
        if (sy[0] - 0.010 <= c.y <= _yb and abs(c.x - np.interp(c.y, sy, sx)) < TUBE_W
                and c.z > np.interp(c.y, sy, sz) - 0.005):
            tube.append(f)
    if tube:
        cs = [m @ f.calc_center_median() for f in tube]
        print("on the bonnet-to-wing shut line: %d faces, y %+.3f..%+.3f, x %.4f..%.4f"
              % (len(tube), min(c.y for c in cs), max(c.y for c in cs), min(c.x for c in cs), max(c.x for c in cs)))
    kill += tube
else:
    print("no shut_bonnet_wing.json - run rebuild_bonnet_drawn first; shut-line tube left in")
before = len(bm.faces)
bmesh.ops.delete(bm, geom=kill, context="FACES")
loose = [f for f in bm.faces if not any(len(e.link_faces) > 1 for e in f.edges)]
bmesh.ops.delete(bm, geom=loose, context="FACES")
bm.to_mesh(sh.data); bm.free(); sh.data.update()
print("Body_Shell: %d faces -> %d (%d under the separate parts, %d left floating)"
      % (before, len(sh.data.polygons), len(kill), len(loose)))

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)

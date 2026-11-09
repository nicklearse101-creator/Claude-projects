"""Rebuild the roof panel and its cant rail - the first piece of the greenhouse.

Three traced curves, one from each view, which is what a roof needs:

  **crown(y)** - the roof's centreline height along the car, off the line blueprint's side elevation
  (`roof` + `roof_b` in blender/data/side_profile.json). In a side elevation the roof's silhouette is
  its crown, so this is read directly.

  **arch(|x|)** - how the roof falls away from the crown across the car. This is already traced: above
  the belt, the front elevation's silhouette in blender/data/section_profile.json *is* the roof, and
  inverting it gives the section - flat to |x| 0.15, -17 mm at 0.30, -55 at 0.50 and -115 at the drip
  rail. (A fresh trace of the front elevation's top edge only found the windscreen header's inner line
  and the mirror, so the section is used as it stands - tools/trace_roof.py.)

  **outline(y)** - the roof's half-width along the car, off the factory sheet's plan view. That plan is
  a cutaway with the interior drawn inside it, so the roof edge is found by the symmetric-pair test, the
  same way tools/trace_plan.py finds the body's. The drip rail is drawn as a close pair of lines and the
  trace swaps between them, so it is smoothed over about 420 mm; the scale is anchored on the section's
  own shoulder rather than on the sheet, as everywhere else.

The cant rail below the roof edge comes from the photographs: tools/photomatch/body_profile.json has the
drip gutter at z 1.268 and the side glass starting at 1.212-1.236 (`cant`), at x 0.505-0.552
(`glass_top_x`). So the roof's edge rolls into a small gutter and then down a short face to the top of
the side glass, which is where the window frames will pick it up.

Left half only, with a Mirror modifier clipped on the centreline (Nik, 2026-10-26).

blender -b blender/nova_proc.blend --python tools/gen/rebuild_roof.py -- out.blend
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args and not args[0].startswith("--") else None

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "blender", "data")
RF = json.load(open(os.path.join(D, "roof_profile.json")))
PF = json.load(open(os.path.join(ROOT, "tools", "photomatch", "body_profile.json")))

DZ = 0.0193                                      # photo frame -> model frame
NU, NY = 21, 90                                  # across the roof / along it
GUTTER_IN, GUTTER_DOWN = 0.007, 0.013            # the drip groove just inboard of the roof's edge

arch = np.array(RF["arch"], float)               # (half-width, height), half ascending
crown_t = np.array(RF["crown"], float)
outline = np.array(RF["outline"], float)
Z_ARCH_CROWN = float(RF["z_crown"])

cant = np.array(PF["cant"], float); cant[:, 1] += DZ
gtx = np.array(PF["glass_top_x"], float)


def smooth(a, n):
    k = np.ones(n) / n
    return np.convolve(np.r_[np.repeat(a[0], n // 2), a, np.repeat(a[-1], n // 2)], k, "valid")


crown_y = crown_t[:, 0]
crown_z = smooth(crown_t[:, 1], 9)

# Where the roof ends: both headers are where the side-elevation line turns down off the flat. Reading
# it off the slope rather than guessing a station keeps it tied to the drawing.
SIDE = json.load(open(os.path.join(D, "side_profile.json")))["lines"]
scr = np.array(SIDE["screen"], float)
Y_F = float(scr[np.argmax(scr[:, 1]), 0])        # the screen header: the top of the windscreen line
slope = np.gradient(crown_z, crown_y)
idx = np.nonzero(np.abs(slope) < 0.22)[0]
Y_R = float(crown_y[idx[-1]])
print("roof runs y %+.3f (screen header) .. %+.3f (backlight header), crown %.4f .. %.4f"
      % (Y_F, Y_R, crown_z[idx].min(), crown_z[idx].max()))


def z_crown(y):
    return float(np.interp(y, crown_y, crown_z))


def half(y):
    return float(np.interp(y, outline[:, 0], outline[:, 1]))


def drop(x):
    """How far below the crown the roof sits at this distance from the centreline.

    Read at the real |x|, not at a fraction of the roof's width. The section's own widest reading
    (0.572 m at z 1.263) is the cant-rail band below the drip, not the roof's edge; taking the drop at
    the plan's half-width instead puts the edge at z 1.283, against the 1.287 the photographs give for
    the drip gutter (body_profile `_cant_src`). Two sources, 4 mm apart - so this is the right reading.
    """
    return Z_ARCH_CROWN - float(np.interp(min(x, float(arch[-1, 0])), arch[:, 0], arch[:, 1]))


def z_cant(y):
    return float(np.interp(y, cant[:, 0], cant[:, 1]))


def x_cant(y):
    """Top of the side glass. The photographs put it within a few mm of the roof's own edge, and the two
    traces disagree by about that much, so it is held inboard of the drip rail rather than crossing it."""
    return min(float(np.interp(y, gtx[:, 0], gtx[:, 1])), half(y) - 0.014)


print("arch: %+.1f mm at |x| 0.15, %+.1f at 0.30, %+.1f at 0.45, %+.1f at the drip rail"
      % (-drop(0.15) * 1000, -drop(0.30) * 1000, -drop(0.45) * 1000, -drop(half(0.5)) * 1000))
print("roof half-width %.4f at mid, %.4f at the screen header, %.4f at the backlight header"
      % (half(0.5), half(Y_F), half(Y_R)))

# ---- rows across the roof, outwards from the centreline -----------------------------------------
def rows(y):
    hw = half(y)
    zc = z_crown(y)
    out = [(t * hw, zc - drop(t * hw)) for t in np.linspace(0.0, 1.0, NU)]
    edge_z = out[-1][1]
    out.append((hw - GUTTER_IN, edge_z - GUTTER_DOWN))          # the drip groove
    out.append((max(x_cant(y), hw - 0.030), z_cant(y) + 0.016))  # the body-colour band above the glass
    out.append((x_cant(y), z_cant(y)))                           # the top of the side glass
    out.append((x_cant(y) - 0.012, z_cant(y) - 0.005))           # a short return inboard
    return out


ys = np.linspace(Y_F, Y_R, NY)
G = [rows(float(y)) for y in ys]
NR = len(G[0])

bm = bmesh.new()
V = [[bm.verts.new((G[i][j][0], float(ys[i]), G[i][j][1])) for j in range(NR)] for i in range(NY)]
for i in range(NY - 1):
    for j in range(NR - 1):
        bm.faces.new((V[i][j], V[i][j + 1], V[i + 1][j + 1], V[i + 1][j]))
bm.faces.ensure_lookup_table(); bm.normal_update()
if sum(f.normal.z for f in bm.faces) < 0:
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
bm.normal_update()

name = "Roof_Panel"
mesh = bpy.data.meshes.new(name)
bm.to_mesh(mesh); bm.free()
if hasattr(mesh, "shade_smooth"):
    mesh.shade_smooth()
for _n in ("set_sharp_from_angle", "set_sharpness_by_angle"):
    _f = getattr(mesh, _n, None)
    if _f:
        _f(angle=math.radians(35))
        break
paint = bpy.data.materials.get("paint_gunmetal")
if paint:
    mesh.materials.append(paint)

old = bpy.data.objects.get(name)
coll = (old.users_collection[0] if old
        else bpy.data.objects["Side_Profile_Door_Left"].users_collection[0])
if old:
    bpy.data.objects.remove(old, do_unlink=True)
ob = bpy.data.objects.new(name, mesh)
coll.objects.link(ob)
mir = ob.modifiers.new("Mirror", "MIRROR")
mir.use_axis[0] = True
mir.use_clip = True
mir.merge_threshold = 0.001
print("%s: %d verts, %d faces, mirrored on the centreline" % (name, len(mesh.vertices), len(mesh.polygons)))
print("   edge z %.4f at mid, gutter to %.4f, glass top %.4f at x %.4f"
      % (z_crown(0.5) - drop(half(0.5)), z_crown(0.5) - drop(half(0.5)) - GUTTER_DOWN,
         z_cant(0.5), x_cant(0.5)))

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)

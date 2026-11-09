"""Rebuild the reference-model car from export/ref/nova_ref.blend (fit_reference.py output): shape fixes
(fix_shape.py) -> export/ref/nova_ref_fix.blend, glass + materials (prep_reference.py), skin polish (polish_ref.py), shading normals (normals_ref.py), window frames / rubbers
(frames_ref.py), windscreen / side windows / scuttle + wipers (windscreen_ref, sidewin_ref,
scuttle_ref), GTE lettering + plates
(details_ref.py; plate textures from
tools/make_plates.py) -> export/ref/nova_ref_mat.blend.
Run: blender -b export/ref/nova_ref.blend --python blender/scripts/rebuild_ref.py   (then export_ref.py on the result)"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REF = os.path.join(os.path.dirname(os.path.dirname(HERE)), "export", "ref")

import bonnet_new
import bumper_sweep
import details_ref
import fix_shape
import front_new
import frames_ref
import normals_ref
import polish_ref
import prep_reference
import scuttle_ref
import sidewin_ref
import windscreen_ref
import wing_new

print("== shape", fix_shape.main())
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(REF, "nova_ref_fix.blend"))
print("== prep", prep_reference.main())
print("== bumpers", {k: bumper_sweep.build(k) for k in ("rear", "front")})
print("== front spoiler", bumper_sweep.spoiler_front())
print("== tow eye", bumper_sweep.tow_eye())
print("== bonnet", bonnet_new.main())
print("== polish", polish_ref.main())
print("== normals", normals_ref.transfer())
print("== frames", frames_ref.main())
print("== windscreen", windscreen_ref.main())
print("== side windows", sidewin_ref.main())
print("== details", details_ref.main())
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(REF, "nova_ref_prewing.blend"))   # quick re-runs of wings/front
print("== wings", wing_new.main())
print("== front end", front_new.main())
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(REF, "nova_ref_mat.blend"))

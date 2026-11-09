"""Side-view feature lines of the GTE (anglia_side.jpg, right side) mapped into the car frame through the
bundle-adjusted side camera cS: each traced pixel's ray is intersected with the plane x = -|x| at the depth
where that feature lives on the body (body side, glass, pillar...). Output heights are in the BA frame
(ground = F400 tyre contact, wheel centre r = 0.272); build code adds DZ for the unloaded model tyres."""
import json, sys
import numpy as np
sys.path.insert(0, '.')
from raycam import hit_x

# pixel traces from tools/trace_side.py (same photo), depth |x| per feature (ESTIMATE from BA + FIA widths)
F = {
 "belt_door": ([(530, 492), (830, 491)], 0.64),
 "belt_quarter": ([(150, 468), (480, 470)], 0.65),
 "window_top": ([(290, 336), (480, 334), (535, 335), (750, 333)], 0.55),
 "roof_drip": ([(240, 314), (750, 316)], 0.57),
 "a_pillar_base": ([(938, 468)], 0.62), "a_pillar_top": ([(757, 330)], 0.51),
 "hatch_roof_end": ([(215, 310)], 0.55), "hatch_bottom": ([(75, 482)], 0.60),
 "arch_rear": ([(140, 650), (145, 610), (165, 590), (195, 576), (230, 567), (265, 567), (300, 573), (325, 582), (350, 600), (365, 620), (375, 650)], 0.765),
 "arch_front": ([(985, 700), (990, 660), (1000, 630), (1020, 605), (1050, 590), (1080, 584), (1110, 584), (1150, 590), (1180, 603), (1200, 620), (1210, 645), (1215, 690)], 0.762),
 "sill_bottom": ([(378, 703), (600, 712), (975, 718)], 0.72),
 "body_bottom_red": ([(380, 685), (930, 690)], 0.765),
 "door_shut_rear": ([(510, 495), (510, 690)], 0.74),
 "door_shut_front": ([(928, 690), (928, 500), (905, 470)], 0.74),
 "crease_front_wing": ([(950, 540), (1250, 548)], 0.74),
 "crease_rear_quarter": ([(80, 520), (470, 530)], 0.74),
 "fuel_cap": ([(361, 575)], 0.762),
 "side_repeater": ([(972, 539)], 0.745),
 "door_handle": ([(520, 510), (572, 524)], 0.73),
 "mirror": ([(830, 455), (892, 500)], 0.80),
 "b_pillar": ([(485, 400), (527, 400)], 0.60),
 "door_glass_rear": ([(530, 400)], 0.60), "quarter_glass_front": ([(480, 400)], 0.60),
 "quarter_glass_rear_edge": ([(150, 467), (285, 338)], 0.60),
 "skirt_top": ([(375, 625), (395, 660), (430, 686), (975, 690), (985, 700)], 0.765),
 "front_bumper_side_end": ([(1213, 640)], 0.74), "rear_bumper_side_end": ([(140, 600)], 0.74),
}
out = {}
for k, (pts, d) in F.items():
    out[k] = [[round(float(v), 4) for v in hit_x('cS', u, v_, -d)[1:]] for u, v_ in pts]
for k, v in out.items():
    print(f"{k:24s}", v)
json.dump(out, open('side_lines.json', 'w'), indent=1)

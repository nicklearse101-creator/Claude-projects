# Reference-model car - things that don't match the real Nova GTE (to fix next)

State 2026-10-19 (first pass): Nik's model (scaled, arches fixed, docs/SHELL_MAP.md) with glass + materials, exported and deployed
(blender: export/ref/nova_ref_mat.blend; scripts fit_reference.py -> rebuild_ref.py [fix_shape.py + prep_reference.py]
-> export_ref.py).

## Model shape faults (from the shell map)
1. ~~Transverse bonnet line~~ DONE 2026-10-19 (fix_shape.py: ~2 mm step refitted, now within 0.2 mm of a smooth curve).
2. ~~Fuel flap~~ DONE 2026-10-19: old cap removed; new recessed flap + black cap (DET_FUEL) at the matched side photo
   position (cS ray hit: y 0.813, z 0.61, cap ~113 mm across).
3. ~~Round fitting on the right B/C-pillar~~ DONE 2026-10-19 (removed).
4. ~~No sunroof~~ DONE 2026-10-19: DET_SUNROOF, glass x +-0.345, y -0.13..0.30, 16 mm black seal (body_profile ESTIMATE),
   opaque dark glass laid on the roof.
5. ~~Lettering mirrored / garbled~~ DONE 2026-10-19 (details_ref.py): raised door lettering and rear badge flattened;
   GTE door decals as grey outline letters (photo style, cS position y -0.647..-0.376, z 0.457..0.504), chrome GTE
   badges on the grille and rear panel, flat textured plates (made-up "F160 GTE", tools/make_plates.py).
6. ~~Interior is left-hand drive~~ DONE 2026-10-19 (fix_shape.mirror_interior): cabin front (dash, footwells) replaced
   by its mirror image - instrument recess and column boss now on the right; our steering wheel, column, dials and
   needles sit in it (our box binnacle dropped).

## Found later (Nik, 2026-10-19)
16. ~~Bonnet dips~~ DONE 2026-10-19 (fix_shape.bonnet_dips): the outer panels between the creases and the edges sank
    10-19 mm from y -1.27 back to the scuttle; raised to a straight crease-to-edge slope (fit error ~1 mm).
17. ~~Front arch flare~~ DONE 2026-10-19 (fix_shape.front_arch_line): the flare above the front arch is a crescent - its
    LOWER edge is the straight line traced in the side photo (z 0.627 at y -1.57 to 0.707 at y -0.70; it had been
    lifted ~2.8 cm mid-arch by the arch morph), its TOP edge stays arched over the wheel and comes down to meet the
    straight line at the ends (Nik). Arch lip and shoulder line unchanged.

18. ~~Bump in the front arch edge at the bumper~~ DONE 2026-10-19 (fix_shape.arch_front_edge): the front edge of the arch
    between z 0.49 and 0.62 had been pulled up to 3.2 cm back by bumper_ribs; slid forward onto the photo-traced arch
    (now within 1-4 mm of it), blended into the bumper's top corner.

19. ~~Front indicator vs the model's line on the wing~~ DONE 2026-10-19: amber now wraps from the headlamp over the corner
    to the model's groove on the wing (y -1.5815), top/bottom z 0.522 / 0.6765; edges cut clean (prep_reference IND_*).
20. ~~Quarter window tail solid grey~~ DONE 2026-10-19: the solid panel at the back of each quarter window (and the
    template trim behind it) cut out along the fin line, top and bottom (clean cut, no scraps); glass fills it.
21. Finish pass 2026-10-19: colour-zone edges cut clean along 58 lines (lamps, grille, skirts, handles, repeaters,
    tail-lamp bands, rear panel, valance); outer-skin polish (polish_ref.py: feature-preserving denoise, moves capped
    at 1 mm, crease shading blended 20-60 deg); bonnet outer panels refitted to one smooth slope (wrinkles at the
    scuttle corners); ragged chrome patch on the bonnet nose dropped (real car: white griffin decal - to do).
    Left: crumpled body-colour panels at each end of the scuttle (folds in the model, deeper than a polish can take
    out); the dark wedge under the mirrors in the studio renders is the mirror's shadow, not the model.

## Dimensions still off
7. Body width at the axles 1500 / 1507 mm (FIA 1522 / 1529): about 1 cm per side narrow. **Left as is** (Nik, 2026-10-19:
   doesn't matter for now).
8. ~~Mirrors 1688 mm across~~ DONE 2026-10-19: heads scaled outward, now 1725.
9. ~~Front bumper corner~~ DONE 2026-10-19: ribs had been bent up 14 mm at the arch end by the arch morph - bumper heights
   restored (ribs straight within 6 mm); the black smudge was the wheel-well material zone reaching the skin (fixed).

## Materials and glass (first pass - check in AC)
10. ~~Bumper red pinstripes~~ DONE 2026-10-19, moved the same day (Nik: wrong place - they were on the rounded top):
    four 3 mm red lines in each bumper's own rib grooves (front z 0.418/0.433/0.453/0.476, rising up to 8.5 mm round
    the corner to the arch; rear 0.466/0.497/0.509/0.522), round to the arches. Side photo check: inside the real
    rib band. Also: black rear panel meets the bumper top, underside black off the bumpers' lower curve.
11. ~~Lamps / lights.ini~~ DONE 2026-10-19: tail lamp bands from redgte_24 (red / amber / clear reversing); lamp faces
    split into DET_LAMP_HEAD/TAIL/BRAKE/REV/FOG/IND_L/IND_R; data/lights.ini (headlights, tail = upper red band,
    brake = lower red band - vanilla AC can't drive both on one mesh) and extension/ext_config.ini (CSP indicators,
    reversing). Not yet checked in AC at night. Lenses are still solid (no glass over reflectors).
12. ~~Frame / rubber band widths~~ DONE 2026-10-19 (frames_ref.py): window frames, windscreen rubber and tailgate seal
    are strips following the measured opening outlines (face colouring was ragged); side openings re-detected (old
    depth test took the roof sides and C-pillar top: flat tops, vertical quarter-window rear edge) - now match cS.
    Grille and scuttle black taken by position.
13. ~~Tailgate glass fit~~ CHECKED 2026-10-19: no gap or overlap at the fins; seal strip on the glass edge.
14. Wheel wells, underside and interior are single dark materials.
    NEXT: interior from redgte_12-16 - mid-grey dash/trims, striped seat centre panels (front seat centres x +-0.36,
    rear +-0.49), dark carpet, light headlining.
15. Weight: 1.3 M triangles, 50 MB kn5 - LODs needed for racing with others.

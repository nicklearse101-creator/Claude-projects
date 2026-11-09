# Plan: rear suspension on the MODEL from leaf springs to double wishbone (DONE in v24, option B)

**Outcome (5 Oct, v24):** built with option B (`tools/blender/build_rear_dwb.py`). One claim below was WRONG: the
upper wishbone pivots are not "26-44 mm under the boot floor". That check measured the nearest surface from the kn5
wheel centre; ray casts showed the floor inboard of the tub wall (x 0.536) is only ~0.105-0.112 high, so the upper
inner pivots (z 0.25, 0.40 inboard) sit INSIDE the car - the front one under the rear seat back, the rear one inside
the boot's front wall - and the first brackets ran up into the parcel shelf. Fixed by mounting them tube-frame style:
turret posts DOWN to that floor plus a pivot shaft through both bushes (`TURRET`); the arms pass through the inner
wheel arch. Physics pivots unchanged. Option C (CSP animation) not started.


The physics has been a double wishbone since v20; only the 3D model still shows the original live axle on leaf
springs. This changes looks only - handling stays exactly as it is.

## What is there now (main model, all under the static `suspension_a` node - none of it ever moved, even on v19's axle)
* `suspension_a_SUB3` (3943 verts, 463 pieces): both leaf springs (front eyes ~y 0.43, rear shackles ~1.92), axle
  tube, diff housing ("pumpkin" at the centre).
* `suspension_a_SUB1` (2966 verts): U-bolts, spring plates and clamps around the axle (y 1.16-1.25).
* `suspension_a_SUB4` (328 verts): the two rear dampers.
* Render: `img/rear_now_underside.png`.

## What it becomes (per side, built in Blender by a new `tools/blender/build_rear_dwb.py`, same pattern as the aero kit)
Every pivot comes straight from the physics (`dtm_build.REAR_DWB`), so what you see is what the car simulates:
1. Lower wishbone: tubular A-arm, body pivots (0.40 m inboard of the wheel, 9-10 cm below hub) to the lower ball joint.
2. Upper wishbone: shorter A-arm, body pivots 13 cm above hub to the upper ball joint (14 cm above hub).
3. Upright / hub carrier between the two ball joints (the existing brake caliper and disc stay where they are).
4. Toe link: leading, 6 cm above the hub, body end 0.36 m inboard.
5. Coilover (spring + damper) from the lower wishbone to a turret under the boot floor - replaces leaf springs + dampers.
6. Drive shafts with CV boots from the diff output to the hub.
7. Diff: keep the centre housing (now body-mounted, as on any IRS car), cut off the axle tubes, add a subframe
   crossmember carrying the inner pivots and small brackets up to the boot floor.
8. Removed: leaf springs, shackles and hangers, U-bolts/plates, axle tubes, radius rods, old dampers.
LODs: B and C get simplified copies (thin tubes, few sides), D just loses the leaf springs. Paint: chassis black /
the model's existing suspension materials, so it matches the front.

## Clearances checked (left rear; right is a mirror)
* Lower wishbone pivots: 63-67 mm from the exhaust - clear.
* Upper wishbone pivots: 26-44 mm under the boot floor / wheel tub - fine with short floor brackets.
* Toe link inner end sits behind the wheel-well liner - hidden, fine.
* No pivot lands inside the fuel tank.

## Moving parts - the one uncertain bit
AC by itself only moves the wheel and a per-corner "suspension" node up and down; it does not swing arms. Options:
* **A. Static at ride height** - everything built in the static position. Looks right standing still and at normal
  ride; when a wheel moves +-4 cm the outer arm ends drift off the hub (visible only from under the car / close replays).
* **B. A + upright moves** - the upright, coilover bottom and drive-shaft outer end hang off the moving suspension node,
  so the hub side follows the wheel; arms still static (small gaps at the ball joints under big travel).
* **C. Fully animated** - a CSP car script (Lua, runs every frame; you have CSP) swings each wishbone, the toe link and
  the drive shafts between their body pivots and the moving hub and stretches the coilover. Correct at all times.

## Confidence
* Removing the leaf-spring rear and building the new parts at ride height: HIGH - same pipeline as the aero kit
  (lossless model export, node-by-node compare against the original, LODs handled), and every pivot is known.
* Option B: HIGH - parenting to the existing suspension nodes is standard AC.
* Option C: MEDIUM - CSP car scripts can move model parts each frame, but I haven't scripted this car before; I'd
  prototype one corner first and you (or I, with your OK to run AC) check it in game before doing the rest.
* Physics: no change at all.

## Proposed order
1. Build the new rear at ride height with option B; renders from under the car for you to approve.
2. Export + install as the next version (old one kept as BACKUP), you look in game.
3. If you want it fully moving: prototype option C on one rear corner, check it in game, then do the other side.

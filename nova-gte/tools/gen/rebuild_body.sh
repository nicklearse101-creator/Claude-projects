#!/bin/sh
# Rebuild every drawn body part, in dependency order, from blender/data + tools/photomatch data.
#   sill -> bonnet -> scuttle (meets the bonnet) -> wing (rolls into bonnet/scuttle) -> rear end (bumper,
#   lamps, rear panel) -> shell -> fit (cull
#   what the panels cover) -> apertures -> organise collections
# Intermediates go to export/tmp (C: is full). Writes blender/nova_proc.blend at the end; back it up first.
#   sh tools/gen/rebuild_body.sh
set -e
cd "$(dirname "$0")/../.."
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
T=export/tmp
mkdir -p $T
run() { echo "== $2"; "$B" -b --factory-startup "$1" --python "tools/gen/$2.py" -- "$3" 2>&1 \
        | grep -vE "^(Blender|Read blend|Info:|Warning:|$)|^[0-9:.]+ +(blend|bke)" | sed 's/^/   /' | tail -${4:-8}
        [ -f "$3" ] && [ "$3" -nt "$1" ] || { echo "   FAILED: no $3"; exit 1; }; }
run blender/nova_proc.blend rebuild_sill          $T/r1.blend
run $T/r1.blend           rebuild_bonnet_drawn    $T/r2.blend
run $T/r2.blend           rebuild_scuttle_drawn   $T/r3.blend
run $T/r3.blend           rebuild_wing_drawn      $T/r4.blend
run $T/r4.blend           add_rear_end            $T/r5.blend
run $T/r5.blend           build_shell2            $T/r6.blend
run $T/r6.blend           fit_shell               $T/r7.blend
run $T/r7.blend           cut_apertures2          $T/r8.blend
run $T/r8.blend           roll_edges              $T/r9.blend
run $T/r9.blend           shut_lines              $T/r10.blend
run $T/r10.blend          add_shut_gutter         $T/r10g.blend
run $T/r10g.blend         add_glass               $T/r11.blend
run $T/r11.blend          add_mirrors             $T/r11m.blend
run $T/r11m.blend         add_wheels              $T/r11w.blend
run $T/r11w.blend         organise                blender/nova_proc.blend

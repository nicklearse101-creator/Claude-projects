#!/usr/bin/env bash
# Regression check: rebuild the AE86 door and front wing and print their coverage (original area within 1 / 3 mm).
# Run after every change to panel_fit.py / panel_fit_freecad.py:   ./regress.sh [door|wing|quarter|roof|bonnet|all]
# Reference (2026-11-10 evening): door 87.6 % / 99.6 %; wing (all faces + hole fill) 72.4 % / 99.5 %;
# rear quarter (corner split w0, all faces, hole fill) 77.9 % / 98.7 % (2026-11-10 night).
# After seam matching, line pinning and the chord-sag rule in fill_holes (same night): door 87.9 / 99.6,
# wing 70.6 / 96.1 (vertices 92.5 / 99.3 - area drop = Kunos chords no longer patched), quarter 78.2 / 96.8.
# Thin strips (strip_build.py, 10 Nov late): door 88.4 / 99.7, wing 70.5 / 96.1, quarter 78.3 / 96.8 (vertices 86.3 / 97.9).
# Chain sides + fold flanges (11 Nov): door 88.5 / 99.7, wing 70.5 / 96.1, quarter 79.4 / 96.9 (vertices 88.2 / 98.6).
# C-pillar station-profile surface (pillar1, 11 Nov morning): quarter 84.4 / 99.5 (vertices 88.3 / 98.6).
# Pillar + foot one sweep (sweep_build.py, 11 Nov): door 88.5 / 99.7, wing 70.5 / 96.1, quarter 85.9 / 99.3 (vertices 90.1 / 98.2).
# Foot touch-ups (resampled stations, deck cut on the grid's real edge): quarter 85.8 / 99.3 (vertices 90.1 / 98.2).
# Roof (roof_build.py; score = Kunos VERTICES within 0.3 / 1 mm): first build 67.2 / 97.0; G2 rear roll (11 Nov) 67.9 / 97.0, max 1.2 mm.
# Roof neighbour strips + resampled roof outline (11 Nov noon): roof 72.4 / 97.0; door 88.5 / 99.7, wing 70.5 / 96.1, quarter 85.8 / 99.3.
# Bonnet first build (centre + outer panels + G2 step band, no nose yet; 11 Nov): Kunos skin vertices median 0.13, 99.6 % within 1 mm.
# Bonnet nose (front face + degree-7 G2 roll, 11 Nov pm): all 695 skin vertices median 0.13, 74.5 / 99.7 % within 0.3 / 1 mm; nose 0.17 / max 0.76.
# Bonnet steps 13-14 (11 Nov night): 8 pin-hole fills, underside cap (Kunos vertices median 0.9 mm), nozzles (median 0.5 mm).
# Bonnet edges (13 strips + 12 corner fills, 11 Nov evening): skin 75.7 / 100.0 %; edges r1-r13 median 0.06, 99.2 % within 1 mm. Others unchanged.
# C-pillar-top corners, one owner per surface (PF_NOROOF), roof as master (PF_MASTER), roof built first (11 Nov 13:00): door 88.5 / 99.7, wing 70.5 / 96.1, roof 72.4 / 97.0, quarter 85.6 / 99.3.
set -e
cd "$(dirname "$0")"
C=D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_toyota_ae86
R=D:/Claude/_scratch_research/kn5_study/regress
what=${1:-all}
if [ "$what" = door ] || [ "$what" = all ]; then
  python panel_fit.py $C $R/door GEO_extdoorL_SUB1:b0,2 GEO_extdoorL_SUB1:r1,5 'GEO_extdoorL_SUB1:rall!0,1,2,5' GEO_extdoorL_SUB0:rall mirrorL:rall GEO_extglassL > $R/door.log 2>&1
  PF_RETURNS=5 PF_RETURNS_ON='SUB1:r0:,SUB1:r1,SUB1:r2:,SUB1:r5' PF_IN="$(cygpath -w $R/door)" ./fcrun.sh panel_fit_freecad.py >> $R/door.log 2>&1
  echo "door: $(python score_faces.py $C $R/door GEO_extdoorL_SUB1 GEO_extdoorL_SUB0 mirrorL GEO_extglassL | tail -1)"
fi
if [ "$what" = wing ] || [ "$what" = all ]; then
  export PF_CLIP=0,1,0,2,0.62,2
  python panel_fit.py $C $R/wing GEO_body:arch0 'GEO_body:rall!0' > $R/wing.log 2>&1
  PF_IN="$(cygpath -w $R/wing)" ./fcrun.sh panel_fit_freecad.py >> $R/wing.log 2>&1
  python fill_holes.py $C $R/wing GEO_body >> $R/wing.log 2>&1                 # safety net: fill uncovered areas
  PF_IN="$(cygpath -w $R/wing/fill)" ./fcrun.sh panel_fit_freecad.py >> $R/wing.log 2>&1 && python merge.py $R/wing >> $R/wing.log
  echo "wing: $(python score_faces.py $C $R/wing GEO_body | tail -1)"
fi
if [ "$what" = roof ] || [ "$what" = all ]; then
  unset PF_CLIP                                      # the wing step exports it
  # the roof is the MASTER on top of the car (built first): its neighbour strips take a side on an unbuilt region
  # from the Kunos vertices; the quarter then snaps to the roof's edges (PF_MASTER). (PF_FOREIGN = the other way
  # round, quarter faces into the roof's strips: tried, it fed the old quarter edge error back round in a circle.)
  python roof_build.py $C $R/roof > $R/roof.log 2>&1
  PF_IN="$(cygpath -w $R/roof)" ./fcrun.sh panel_fit_freecad.py >> $R/roof.log 2>&1
  python pack_build.py $R/roof $R/roof/build.npz >> $R/roof.log
  echo "roof: $(python roof_score.py $C $R/roof/build.npz | head -1)"
fi
if [ "$what" = quarter ] || [ "$what" = all ]; then
  export PF_CLIP=0.45,1,0,1.3,-2.2,-0.5          # y up to the roof: the roof triangles are left out by PF_NOROOF
  export PF_NOROOF=1                                 # the roof build owns the roof + its strips (one owner per surface)
  [ -f $R/roof/build.npz ] && export PF_MASTER=$R/roof/build.npz   # faces along the roof are trimmed on its edges
  python panel_fit.py $C $R/quarter GEO_body:w0 GEO_body:pillar1 'GEO_body:rall!0,1' > $R/quarter.log 2>&1
  PF_IN="$(cygpath -w $R/quarter)" ./fcrun.sh panel_fit_freecad.py >> $R/quarter.log 2>&1
  python fill_holes.py $C $R/quarter GEO_body >> $R/quarter.log 2>&1
  PF_IN="$(cygpath -w $R/quarter/fill)" ./fcrun.sh panel_fit_freecad.py >> $R/quarter.log 2>&1 && python merge.py $R/quarter >> $R/quarter.log
  echo "quarter: $(python score_faces.py $C $R/quarter GEO_body | tail -1)"
  unset PF_CLIP PF_NOROOF PF_MASTER
fi
if [ "$what" = bonnet ] || [ "$what" = all ]; then
  unset PF_CLIP PF_NOROOF PF_MASTER
  python bonnet_build.py $C $R/bonnet > $R/bonnet.log 2>&1
  PF_SAVE_FACES=0 PF_IN="$(cygpath -w $R/bonnet)" ./fcrun.sh panel_fit_freecad.py >> $R/bonnet.log 2>&1 && python pack_build.py $R/bonnet $R/bonnet/build.npz >> $R/bonnet.log
  echo "bonnet: $(python bonnet_score.py $C $R/bonnet/build.npz | head -1)"
  # step 13-14: pin-hole fills (mesh level), then the underside cap + washer nozzles -> build_full.npz (the whole bonnet)
  python mesh_holes.py $R/bonnet/build.npz 0.3 --fill $R/bonnet/build_filled.npz > $R/bonnet/holes.log 2>&1
  python underside_build.py $C $R/bonnet/build_filled.npz $R/bonnet/build_full.npz > $R/bonnet/underside.log 2>&1
  echo "bonnet holes: $(grep -c 'holefill:' $R/bonnet/holes.log) filled; $(grep -E '^underside|^nozzles' $R/bonnet/underside.log | tr '
' ' ')"
fi

#!/usr/bin/env bash
# Regression check: rebuild the AE86 door and front wing and print their coverage (original area within 1 / 3 mm).
# Run after every change to panel_fit.py / panel_fit_freecad.py:   ./regress.sh [door|wing|quarter|all]
# Reference (2026-11-10 evening): door 87.6 % / 99.6 %; wing (all faces + hole fill) 72.4 % / 99.5 %;
# rear quarter (corner split w0, all faces, hole fill) 77.9 % / 98.7 % (2026-11-10 night).
# After seam matching, line pinning and the chord-sag rule in fill_holes (same night): door 87.9 / 99.6,
# wing 70.6 / 96.1 (vertices 92.5 / 99.3 - area drop = Kunos chords no longer patched), quarter 78.2 / 96.8.
# Thin strips (strip_build.py, 10 Nov late): door 88.4 / 99.7, wing 70.5 / 96.1, quarter 78.3 / 96.8 (vertices 86.3 / 97.9).
# Chain sides + fold flanges (11 Nov): door 88.5 / 99.7, wing 70.5 / 96.1, quarter 79.4 / 96.9 (vertices 88.2 / 98.6).
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
if [ "$what" = quarter ] || [ "$what" = all ]; then
  export PF_CLIP=0.45,1,0,1.235,-2.2,-0.5
  python panel_fit.py $C $R/quarter GEO_body:w0 'GEO_body:rall!0' > $R/quarter.log 2>&1
  PF_IN="$(cygpath -w $R/quarter)" ./fcrun.sh panel_fit_freecad.py >> $R/quarter.log 2>&1
  python fill_holes.py $C $R/quarter GEO_body >> $R/quarter.log 2>&1
  PF_IN="$(cygpath -w $R/quarter/fill)" ./fcrun.sh panel_fit_freecad.py >> $R/quarter.log 2>&1 && python merge.py $R/quarter >> $R/quarter.log
  echo "quarter: $(python score_faces.py $C $R/quarter GEO_body | tail -1)"
fi

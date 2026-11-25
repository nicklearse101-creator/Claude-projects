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
# Hatch first build (U sweep + header + deck, 12 Nov; hatch_score = Kunos skin VERTICES): median 0.150, p95 1.07, within 0.3 / 1 mm 69.9 / 94.4 % (lower corners open).
# Rear bumper first build (bumper_build.py, 17 Nov; Kunos VERTICES): bands 81.6 / 98.9 %, whole mesh 75.4 / 96.3 % within 0.3 / 1 mm.
# Quarter without the hatch (PF_NOHATCH, 17 Nov; scores its OWN area now, the hatch side band left it): 83.6 / 99.5; no faces on the hatch any more (13075 -> 2 overlap tris).
# Hatch lower corners (faired spine, local-frame row smoothing, corner zone smoothing + vertex offset, 13 Nov): median 0.159, p95 0.77, within 0.3 / 1 mm 71.9 / 97.5 %.
# Hatch corner tab (U extended past the outline + trimmed on the knee-aware fair outline, 13 Nov midday): median 0.154, p95 0.64, max 1.14, within 0.3 / 1 mm 73.6 / 99.4 % (tail 100 %).
# Hatch returns (ring + wall fold flanges, bottom return, tab corner fills; left halves mirrored; 13 Nov pm): skin 75.7 / 99.7 %; ring 89.9 / 100, wall 91.3 / 100, bottom 90.3 / 96.8, corners 100 / 100 %. Others unchanged.
# Front bumper (25 Nov): rows smoothed harder along the sweep (spec lam 1e-5): fewer blotches round the corner, same 94.1 % (whole mesh within 1 mm); tried and dropped (worse): rows onto vertex-row profiles, a full re-loft through vertex rows (Catmull-Rom / Hermite on Kunos normals), fair columns, band fairing, no PN lift. Face columns by arc length, not height (95.1 %). Lengthwise streaks on the side remain.
# Front band (25 Nov): the lower quarter ahead of the rear arch built curves first (frontband_build.py: Kunos's straight vertex rows -> Catmull-Rom through their vertices -> per-station profiles -> one grid trimmed on Kunos's outline); the quarter leaves it out (PF_NOBAND) and its strips there take the band's real edges (PF_BAND_FOREIGN). Kunos vertices ahead of the arch 94.0 % within 1 mm (was 90.2), no hole-fill patches; quarter 83.4 / 100.0 % (was 80.6 / 97.9).
# Partial lines (25 Nov): a short line (PF_LINE_SPAN) merges into its nearest full line beyond its ends instead of being extrapolated (it swung 370 mm: the quarter's side face b1 lay up to 13 mm OUTSIDE the car over the rear corner, a third of it > 3 mm off); quarter area 80.6 / 97.9 (was 78.4 / 97.9), b1 now 0 points > 3 mm.
# Knee rows (24 Nov late): the three real Kunos knee rows ranked by height per station (no 2B-A guess): one soft knee line by eye; sweep+end 93.3 % within 1 mm (was 95.9: a few arch-lip vertices at s end).
# Rear lower band (rearband_build.py, 24 Nov; quarter + tail with PF_NOBAND): band left 98.4 % (sweep 100 %, centre 92.5 %); quarter area 78.4 / 97.9 (its own Kunos vertices 92.6 % within 1 mm, was 92.0); tail 94.7 % (was 93.6 on the same vertices); others unchanged.
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
if [ "$what" = wingband ] || [ "$what" = all ]; then
  # the flat skin behind the front arch (frontband_build.py FB_SIDE=wing, 25 Nov): the raised band + ledge the wing's
  # band fits smoothed away (its vertices 68.8 -> 94 % within 1 mm); the wing leaves it out (PF_NOBAND)
  unset PF_CLIP PF_CLIP_EXACT PF_NOHATCH PF_NOBAND PF_NOROOF PF_MASTER
  FB_SIDE=wing python frontband_build.py $C $R/wingband > $R/wingband.log 2>&1
  PF_IN="$(cygpath -w $R/wingband)" ./fcrun.sh panel_fit_freecad.py >> $R/wingband.log 2>&1 && python pack_build.py $R/wingband $R/wingband/build.npz >> $R/wingband.log
  echo "wingband: $(FB_SIDE=wing python frontband_score.py $C $R/wingband/build.npz | head -1)"
fi
if [ "$what" = wing ] || [ "$what" = all ]; then
  export PF_CLIP=0,1,0,2,0.62,2
  # NOT YET (25 Nov): with the wing band's triangles left out (PF_NOBAND=1 PF_BAND_FOREIGN=1, PF_MASTER / PF_FOREIGN =
  # wingband) the wing's arch detection (fit_arch: arch edge, centre, lip) sees the band's hole in its outline - the
  # sub-panel split moved, r0:front:b0 went 0.95 -> 6.6 mm and its mesh hung FreeCAD. Fix the arch detection first.
  FW=""
  if [ "$WING_BAND" = 1 ]; then export PF_NOBAND=1 PF_BAND_FOREIGN=1; [ -f $R/wingband/build.npz ] && export PF_MASTER=$R/wingband/build.npz; [ -d $R/wingband/faces ] && FW="band=$(cygpath -w $R/wingband/faces)"; fi
  python panel_fit.py $C $R/wing GEO_body:arch0 'GEO_body:rall!0' > $R/wing.log 2>&1
  PF_FOREIGN="$FW" PF_IN="$(cygpath -w $R/wing)" ./fcrun.sh panel_fit_freecad.py >> $R/wing.log 2>&1
  python fill_holes.py $C $R/wing GEO_body >> $R/wing.log 2>&1                 # safety net: fill uncovered areas
  PF_IN="$(cygpath -w $R/wing/fill)" ./fcrun.sh panel_fit_freecad.py >> $R/wing.log 2>&1 && python merge.py $R/wing >> $R/wing.log
  echo "wing: $(python score_faces.py $C $R/wing GEO_body | tail -1)"
  unset PF_CLIP PF_NOBAND PF_BAND_FOREIGN PF_MASTER
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
if [ "$what" = hatch ] || [ "$what" = all ]; then
  # the hatch (tailgate) is part of GEO_body: hatch_build.py owns its skin + returns; built after the roof (its top
  # edge lies on the roof's rear header strip: PF_MASTER) and before the quarter (the drip rail takes its edges)
  unset PF_CLIP PF_NOROOF
  [ -f $R/roof/build.npz ] && export PF_MASTER=$R/roof/build.npz
  python hatch_build.py $C $R/hatch > $R/hatch.log 2>&1
  PF_IN="$(cygpath -w $R/hatch)" ./fcrun.sh panel_fit_freecad.py >> $R/hatch.log 2>&1
  python pack_build.py $R/hatch $R/hatch/build.npz >> $R/hatch.log
  HT_RETURNS=1 python hatch_score.py $C $R/hatch/build.npz | grep -E "^skin|^ring|^wall|^bottom|^corner" | sed 's/^/hatch: /'
  unset PF_MASTER
fi
if [ "$what" = rearband ] || [ "$what" = all ]; then
  # rear lower band (24 Nov): the side skin's band below the body line from the tail centre round the corner to the
  # rear arch, ONE build (rearband_build.py: sweep x 0.33 -> arch, centre strip + transition faces, arch end face);
  # the quarter and the tail leave it out (PF_NOBAND)
  unset PF_CLIP PF_CLIP_EXACT PF_NOROOF PF_MASTER PF_NOHATCH PF_HATCH_BUILD
  python rearband_build.py $C $R/rearband > $R/rearband.log 2>&1
  PF_IN="$(cygpath -w $R/rearband)" ./fcrun.sh panel_fit_freecad.py >> $R/rearband.log 2>&1 && python pack_build.py $R/rearband $R/rearband/build.npz >> $R/rearband.log
  python rearband_score.py $C $R/rearband/build.npz | grep -E "^left|sweep|centre" | sed 's/^/rearband: /'
fi
if [ "$what" = frontband ] || [ "$what" = all ]; then
  # the lower quarter AHEAD of the rear arch (frontband_build.py, 25 Nov): Kunos's vertex rows (straight along the car)
  # -> per-station Catmull-Rom profiles -> one grid, trimmed on Kunos's outline; the quarter leaves these out (PF_NOBAND)
  unset PF_CLIP PF_CLIP_EXACT PF_NOHATCH PF_NOBAND PF_NOROOF PF_MASTER
  python frontband_build.py $C $R/frontband > $R/frontband.log 2>&1
  PF_IN="$(cygpath -w $R/frontband)" ./fcrun.sh panel_fit_freecad.py >> $R/frontband.log 2>&1 && python pack_build.py $R/frontband $R/frontband/build.npz >> $R/frontband.log
  echo "frontband: $(python frontband_score.py $C $R/frontband/build.npz | head -1)"
fi
if [ "$what" = quarter ] || [ "$what" = all ]; then
  export PF_CLIP=0.45,1,0,1.3,-2.2,-0.5          # y up to the roof: the roof triangles are left out by PF_NOROOF
  export PF_CLIP_EXACT=1    # triangles cut ON the box planes: the tail (x < 0.45) and the sill (z > -0.5) are cut there too (seam gap 2.3 -> 0.3 mm, 19 Nov)
  export PF_NOROOF=1                                 # the roof build owns the roof + its strips (one owner per surface)
  [ -f $R/roof/build.npz ] && export PF_MASTER=$R/roof/build.npz   # faces along the roof are trimmed on its edges
  [ -f $R/rearband/build.npz ] && export PF_MASTER="$PF_MASTER;$R/rearband/build.npz"   # ... and along the rear band (24 Nov)
  [ -f $R/frontband/build.npz ] && export PF_MASTER="$PF_MASTER;$R/frontband/build.npz"   # ... and ahead of the arch (25 Nov)
  # the hatch build owns the hatch skin + returns (its side band = the old 'C-pillar' r1 here, the ring flange = old r6):
  # PF_NOHATCH leaves those triangles out; quarter faces next to the hatch take its real edges: wide faces snap the
  # outline points Kunos shares with the hatch onto the hatch build (PF_HATCH_BUILD), strips take the hatch's faces
  # as the neighbour of their free sides (PF_FOREIGN loads them in the FreeCAD stage)
  export PF_NOHATCH=1
  export PF_NOBAND=1 PF_LINE_SPAN=0.2   # the rear lower band is rearband's; the side's lower lines then run arch -> door only
  FH=""; [ -f $R/hatch/build.npz ] && export PF_HATCH_BUILD=$R/hatch/build.npz && FH="hatch=$(cygpath -w $R/hatch/faces)"
  # strips ending on the rear / front lower band take those builds' real edges (25 Nov)
  export PF_BAND_FOREIGN=1; for bb in rearband frontband; do [ -d $R/$bb/faces ] && FH="$FH;band=$(cygpath -w $R/$bb/faces)"; done
  python panel_fit.py $C $R/quarter GEO_body:w0 'GEO_body:rall!0' > $R/quarter.log 2>&1
  PF_FOREIGN="$FH" PF_IN="$(cygpath -w $R/quarter)" ./fcrun.sh panel_fit_freecad.py >> $R/quarter.log 2>&1
  python fill_holes.py $C $R/quarter GEO_body >> $R/quarter.log 2>&1
  PF_IN="$(cygpath -w $R/quarter/fill)" ./fcrun.sh panel_fit_freecad.py >> $R/quarter.log 2>&1 && python merge.py $R/quarter >> $R/quarter.log
  python pack_build.py $R/quarter $R/quarter/build.npz >> $R/quarter.log 2>&1   # assemble.py reads build.npz (it was a stale 17 Nov pack)
  echo "quarter: $(python score_faces.py $C $R/quarter GEO_body | tail -1)"
  unset PF_CLIP PF_CLIP_EXACT PF_NOROOF PF_MASTER PF_NOHATCH PF_HATCH_BUILD PF_NOBAND PF_LINE_SPAN PF_BAND_FOREIGN
fi
if [ "$what" = bonnet ] || [ "$what" = all ]; then
  unset PF_CLIP PF_NOROOF PF_MASTER PF_NOHATCH PF_HATCH_BUILD
  python bonnet_build.py $C $R/bonnet > $R/bonnet.log 2>&1
  PF_SAVE_FACES=0 PF_IN="$(cygpath -w $R/bonnet)" ./fcrun.sh panel_fit_freecad.py >> $R/bonnet.log 2>&1 && python pack_build.py $R/bonnet $R/bonnet/build.npz >> $R/bonnet.log
  echo "bonnet: $(python bonnet_score.py $C $R/bonnet/build.npz | head -1)"
  # step 13-14: pin-hole fills (mesh level), then the underside cap + washer nozzles -> build_full.npz (the whole bonnet)
  python mesh_holes.py $R/bonnet/build.npz 0.3 --fill $R/bonnet/build_filled.npz > $R/bonnet/holes.log 2>&1
  python underside_build.py $C $R/bonnet/build_filled.npz $R/bonnet/build_full.npz > $R/bonnet/underside.log 2>&1
  echo "bonnet holes: $(grep -c 'holefill:' $R/bonnet/holes.log) filled; $(grep -E '^underside|^nozzles' $R/bonnet/underside.log | tr '
' ' ')"
fi
if [ "$what" = sill ] || [ "$what" = all ]; then
  # sills: GEO_body between the quarter's clip (z < -0.5) and the wing's (z > 0.62), below the door opening: 3 flat
  # faces + a 4 mm strip, per piece (rall)
  unset PF_NOROOF PF_MASTER PF_NOHATCH PF_HATCH_BUILD
  export PF_CLIP=0.45,1,0,0.45,-0.5,0.62 PF_CLIP_EXACT=1     # triangles cut exactly on the box (98.5 -> 100 %)
  python panel_fit.py $C $R/sill 'GEO_body:rall' > $R/sill.log 2>&1
  PF_IN="$(cygpath -w $R/sill)" ./fcrun.sh panel_fit_freecad.py >> $R/sill.log 2>&1
  echo "sill: $(python score_faces.py $C $R/sill GEO_body | tail -1)"
  unset PF_CLIP PF_CLIP_EXACT
fi
if [ "$what" = tail ] || [ "$what" = all ]; then
  # tail panel (GEO_body behind the hatch: rail over the lamp openings, raised plate panel, lower band round the
  # corners), without the hatch's triangles: the plate panel swept along x (bumper_build.py tail), the rest per piece
  unset PF_NOROOF PF_MASTER PF_HATCH_BUILD
  export PF_CLIP_EXACT=1 PF_NOHATCH=1 PF_CLIP=-0.45,0.45,0.45,0.85,-2.2,-1.95   # x within the quarter clip (x > 0.45 is the quarter build: one owner)
  export PF_NOBAND=1         # the lower band under the plate panel / lamps is rearband's (24 Nov); the plate panel's spine = its own bottom edge
  # (PF_MASTER = the rear band tried 24 Nov: the strip under the lamp r15/r16 shrank 150 -> 20 mm, not used)
  python bumper_build.py $C $R/tail tail > $R/tail.log 2>&1
  PF_SAVE_FACES=0 PF_IN="$(cygpath -w $R/tail)" ./fcrun.sh panel_fit_freecad.py >> $R/tail.log 2>&1 && python pack_build.py $R/tail $R/tail/build.npz >> $R/tail.log
  echo "tail: $(python bumper_score.py $C $R/tail/build.npz tail | grep -E '^whole')"
  unset PF_NOHATCH PF_CLIP PF_CLIP_EXACT PF_NOBAND PF_MASTER
fi
if [ "$what" = frontbumper ] || [ "$what" = all ]; then
  # front bumper skin (GEO_frontbumper_SUB2): bands [7, 0, 1, 13] (soft piece edges merged, face columns by height),
  # the plate recess / lower intake bridged by the sweep and cut out as openings (bumper_build.py front)
  unset PF_CLIP PF_NOROOF PF_MASTER PF_NOHATCH PF_HATCH_BUILD
  python bumper_build.py $C $R/frontbumper front > $R/frontbumper.log 2>&1
  PF_SAVE_FACES=0 PF_IN="$(cygpath -w $R/frontbumper)" ./fcrun.sh panel_fit_freecad.py >> $R/frontbumper.log 2>&1 && python pack_build.py $R/frontbumper $R/frontbumper/build.npz >> $R/frontbumper.log
  echo "front bumper: $(python bumper_score.py $C $R/frontbumper/build.npz front | grep -E '^bands|^whole' | tr '
' ' ')"
fi
if [ "$what" = rearbumper ] || [ "$what" = all ]; then
  # rear bumper (its own Kunos mesh): main profile swept as 7 bands along the plan line, end faces at the arches cut on
  # the last station plane, every other piece as strips / faces on the built edges (bumper_build.py)
  unset PF_CLIP PF_NOROOF PF_MASTER PF_NOHATCH PF_HATCH_BUILD
  python bumper_build.py $C $R/rearbumper rear > $R/rearbumper.log 2>&1
  PF_SAVE_FACES=0 PF_IN="$(cygpath -w $R/rearbumper)" ./fcrun.sh panel_fit_freecad.py >> $R/rearbumper.log 2>&1 && python pack_build.py $R/rearbumper $R/rearbumper/build.npz >> $R/rearbumper.log
  echo "rear bumper: $(python bumper_score.py $C $R/rearbumper/build.npz rear | grep -E '^bands|^whole' | tr '
' ' ')"
fi

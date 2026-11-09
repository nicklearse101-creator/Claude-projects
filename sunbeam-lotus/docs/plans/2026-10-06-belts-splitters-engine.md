# Plan: harness floor anchors, front/rear splitter rework, Escort 4-cylinder in the bay (Nik, 6 Oct)

Target car: `talbot_sunbeam_lotus_81_works_backup_v6` ("our main model" - four-link axle). Only its four model files
change (`sunbeam_rally*.kn5`, old ones archived); its data/, data.acd and sfx stay as Nik left them. The v7 car can
take the same files later. Backups first: `blender/sunbeam_rally_on_stock_model BACKUP before splitter-belts-engine
work.blend`, the installed kn5s go to `archive/`.

## 1. Harness anchored to the floor (build_cage.wrap_on_bar -> anchored)
Now: the shoulder straps go over the harness bar (y 0.72, z 0.763, 38 mm tube), wrap round it and tuck under it.
New: each strap goes over the bar, leaves it on the tangent towards an anchor on the rear floor strip (y 1.10, floor
z 0.108, in front of the bulkhead at y 1.165) and drops to it (~60 deg). The strap's own cut section is extruded
along that line, so webbing width/thickness/texture carry on unbroken. At the floor: snap hook, eye bolt and a 3 mm
reinforcement plate; a 3-bar adjuster on each tail. Worn (CINTURE_ON), loose (CINTURE_OFF) and passenger sets each
get their own tails (their inner straps sit 1.5 cm apart). Checked clear of the cage (nearest tube = the bar).

## 2. Splitters (build_lips)
"Look a bit 2D", "should follow the lines of the arches", rear "rushed - blend to the arches, smooth out":
* lip cross-section: today a knife-edge wedge (point out, straight back underneath) -> a moulding with a rounded
  nose (radius ~9 mm front / 8 mm rear) and a thick underside, so it reads like the arch flares' rolled edge
* corners: longer, softer lofts from the lips into the flares (more steps, longer tangents) so the lip's edge line
  runs into the flare's edge line
* rear: the traced path is smoothed harder (the valance/quarter-panel trace is wavy), the whole rear run is
  smoothed as one (not just the join), the exhaust-notch dip eased over a wider span
* blades: rounded leading edge, ends curving back along the lip instead of square-cut; rear strakes as tapered
  fins under the blade instead of boxes hanging below

## 3. Escort Mk2 4-cylinder in the bay (new tools/build_engine_swap.py)
Fit check (measured): Escort and Sunbeam front axles are 6 mm apart in model space (y -1.218 / -1.212), radiators
y -1.66 / -1.69. The Escort engine fits between the Sunbeam's strut towers (inner wings x +-0.36..0.42 at the
cylinder head) and under its bonnet (closest: 24 mm, a hose; cam cover 52 mm). The Sunbeam bay has a false floor at
z 0.30 (the stock modder modelled only the top of its engine), so everything of the Escort engine below it is
hidden and is left out. Clashes to resolve: Escort-bay items (hoses/brackets made for the Escort's bay, its
bulkhead fittings - those reaching past the Sunbeam's firewall at y ~-0.88), and the Sunbeam's own hoses/leads that
served its stock engine.
Build: donor = the Escort engine exported from the Escort blend (`refs/donor_escort4`, gitignored), imported as
DONOR_ESC4; engine islands copied in at the Escort's own position, filtered (below the false floor / inside Sunbeam
parts / past the firewall); the Sunbeam's stock engine + the bay islands touching it kept but not exported
(`no_export`, one call swaps back). Not in the distance LODs (closed bonnet).
Confidence: high that it physically fits; the cam cover says FORD - the real works car ran the Lotus 2.2 16v, so
the stock engine stays one call away.

## Result (built and installed 6 Oct)
* Installed into `talbot_sunbeam_lotus_81_works_backup_v6` with `tools/install_models.py` (four kn5s only; the old
  ones in `archive/replaced_20261006_084840_talbot_sunbeam_lotus_81_works_backup_v6_models`). kn5 compare against
  the old install: the only changed nodes are CINTURE_ON/OFF + passenger belt, RALLY_flares, both blades and the bay
  islands that touched the stock engine; removed = the 35 stock engine meshes + one bay island; added = the belt
  anchors, the Escort engine meshes and the badge. LODs: flares/blades only. (A first compare listed 460 "changed"
  nodes - only the material indices shifted by the new materials; compared by material name they are identical.)
* Belts: tail UVs ran off the blue webbing into the black part of MK2_seats.dds - now folded inside the band
  (`STRAP_BAND`), 12 segments to the floor.
* Engine: fits (strut towers, bonnet: closest 24 mm, a hose; cam cover 52 mm). Escort parts left out: 2681 verts under
  the false floor, 8301 inside Sunbeam parts (its inner-wing items, hoses to its own bulkhead), 258 past the firewall,
  658 = the FORD letters. Lotus badge 32 mm (36 mm over the bezel) on the 40 mm pad the letters stood on, reading
  from the front of the car.
* Screenshots: `docs/screenshots/2026-10-06/` (not in git).

# Build the hatch as one U-shaped sweep plus a header and a deck

The AE86 hatch (tailgate) is **not a separate mesh** in the Kunos car: it is one smooth region of `GEO_body`
(crease piece 2 of the full mesh, 1270 triangles, 0.609 m2), plus four returns. It is a **frame round the rear glass**
whose outer edge rolls over all the way round: down the two pillars, round the two lower corners and across the
tail, where a flat **deck** under the glass rolls over into a sloped **skirt**. Our rear-quarter build already makes the
left third of it: what we called the "C-pillar" sweep (quarter `r1p`, with its pillar-top end face `r1x00` and deck
`r1d0`) is the hatch's side band, and it stops at the quarter clip box (x 0.45) on a ragged triangle edge. So the hatch
build **takes that sweep over and carries it on to the centreline**; the quarter build leaves the hatch out (one owner per
surface), as it already does for the roof.

This report is lean on purpose (no research agents, Nik 12 Nov). The method comes from the earlier reports
(`Roof surfacing.md`, `Bonnet surfacing.md`, `Narrow strip surfacing between panels.md`, `Smooth region segmentation into
faces.md`) and `PANEL_FIT_TECHNIQUE.md`; the numbers below are measured on the Kunos mesh. Two quick web searches turned
up nothing hatch-specific beyond the standard Class-A order (primaries, then transitions, then flanges) and zebra/cross-
section checks ([Autodesk Alias, Understanding Class A](https://help.autodesk.com/cloudhelp/2022/ENU/Alias-Tutorials/files/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.htm)).

## What Kunos's hatch is (measured 12 Nov)

| Piece (full `GEO_body` numbering) | What it is | Size | Built today by |
|---|---|---|---|
| 2 | hatch skin: header, two side bands (the "C-pillar"), deck, tail roll, skirt | 1270 tris, 0.609 m2, x +-673, z -2068..-941 | quarter `r1p/r1x00/r1d0` (x > 0.39 only) |
| 4 | glass-opening return: a ring round the opening, ~20 mm wide (a ~7 mm step + ~14 mm flange where measured on the pillar) | 176 tris, 532 cm2, 2 loops | quarter `r6` (fold flange, left pillar only) |
| 14 | wall at the glass's lower edge, faces forward | 88 tris, ~18 mm | quarter `r11` (part) |
| 22 | bottom-edge return under the skirt, faces down | 60 tris, ~7 mm | quarter `r16` (part) |
| 116 / 117 | 2 mm corner bits at the skirt's lower corners | 3 tris each | quarter `r35` |

Neighbours that stay with the body: the gutter / drip rail between hatch and quarter (pieces 20/21 = quarter `r7`,
1.4 m chain strip; its hatch-side rail must become the hatch's built edge), the roof's rear header strips (pieces 37/40,
roof-owned: the hatch's top edge snaps onto them, roof = master), the tail-panel lip below the gap (piece 19).

- **Exactly symmetric:** a mirrored half-model with a vertex row on x = 0 and no triangle across it (mirror miss
  <= 0.11 mm). Build x >= 0 and mirror.
- **Centreline section (x = 0):** header ~80 mm long, straight in section, sloping with the roof; glass from z -941 to
  -1790; deck nearly flat from the glass's lower edge back to a knee at z ~ -1985 (Kunos packs vertices there: a tight
  roll, ~40 deg over ~10 mm); skirt convex (about 55 -> 70 deg from horizontal) down to the bottom edge at z -2065,
  y 0.79; a ~7 mm return (piece 22) under it.
- The deck widens toward the corners (at x 0.62 it runs forward to z ~ -1.66 beside the glass corner): the same
  "flat deck, roll, skirt" profile as the sweep's foot, so the foot's `roll_profile` applies across the whole rear.

## Construction

1. **Ownership.** `hatch_owned(car)` = Kunos triangles of pieces 2, 4, 14, 22, 116, 117. `panel_fit.load_mesh` with
   `PF_NOHATCH=1` leaves them out (as `PF_NOROOF`); the quarter is rebuilt and scored without them.
2. **U sweep (side bands + tail roll), one surface.** `sweep_build.sweep_grid` on the left half of the skin (x >= 0)
   with the march running on to the centreline (`x_stop` 0) instead of the old clip at 0.46. Then mirror the stations
   (x -> -x, reversed) and join them into ONE grid from the right pillar top round the tail to the left pillar top,
   interpolated in FreeCAD: symmetric data -> symmetric surface, smooth across x = 0 by construction (no seam).
3. **Header.** One fitted face across the top between the two pillar ends, with the pillar's end rows (both sides) as
   data and cut planes at both pillar ends (as `r1x00`, now full width). Its top outline lies on the roof's rear header
   strip: roof = master (`PF_MASTER`, outline snapped on the master's open boundary and used as data).
4. **Deck.** One face over the area between the glass-bottom wall and the sweep's top edge, full width, cut on the
   grid's real edge (`cut_grid_edge`), the sweep's flat band as tangent data (as `r1d0`).
5. **Returns.** Pieces 4, 14, 22 and the corner bits with `strip_build` on the built edges (fold flange for the 20 mm
   ring; the ring is closed, so it is cut at x = 0 and built as two mirrored halves, or in pieces at the corners if the
   chain turns too hard for the 20 deg / 20 mm rule).
6. **Quarter.** Rebuilt with `PF_NOHATCH=1`; its drip rail's hatch-side rail = the hatch's built edge
   (`PF_FOREIGN='hatch=<hatch build>/faces'`). Regress order: roof -> hatch -> quarter (masters first).
7. **Checks.** `hatch_score.py`: Kunos vertices of the owned pieces -> our build (median, within 0.3 / 1 mm, max);
   watertight check (`mesh_holes.py`); grey views rear 3/4, rear, side and close-ups of every corner vs Kunos.

## Acceptance

- Skin vertices: median <= 0.2 mm, >= 97 % within 1 mm (the left-third sweep already does p95 0.5 mm).
- Symmetric: our right half = mirror of our left within 0.01 mm; no visible line at x = 0 in grey or isophotes.
- Header / roof strip join and drip rail / hatch join <= 0.05 mm median (built on the master's edges).
- No two owners anywhere (watertight check finds no flaps); quarter score drops only by the hatch area it gave up.
- By eye in grey: the tail roll reads like Kunos's (a tight knee, not a tube); corners read as one continuous roll.

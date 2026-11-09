# Panel-fit technique (CAD reverse engineering) - the method that made the crisp AE86 door

2026-11-09. Proven on the AE86 door (skin, character lines, window frame) and all of its glass.
Tools: `panel_fit.py` (plain Python: fits) -> `panel_fit_freecad.py` (FreeCAD via `fcrun.sh`, D: only:
trimmed CAD faces, STEP, display mesh) -> exact normals -> Blender. Scoring: `score_exact.py` / `exact_dist.py`.

## The idea in one line
Each panel is **one smooth B-spline surface with as few control points as it needs**, fitted to the
data and **trimmed to its real outline**; character lines are **drawn as fair curves end to end** and
the surfaces either side are **cut exactly on the same curve** - so edges are crisp and surfaces are even
by construction. No smoothing step anywhere.

## Steps
1. **Split like a modeller, not by triangles.**
   - Hard creases (dihedral > 20 deg) -> separate regions (door: upper skin, crease band, lower skin).
   - Inside a region, **character lines** from cross-sections: sharp turns (>10 deg over 12 mm arms) on
     sections every 20 mm, chained along the panel, each fitted as ONE fair curve t = g(s)
     (<= 10 controls, 1 mm tolerance). Sorting triangles by curvature does NOT work (Kunos uses long thin
     triangles -> jagged bands).
   - A strong line (>= 25 deg turn) is a rolled edge: it gets its own narrow **fillet band**, width = the
     band holding 90 % of the turning, measured from the real profile vertices.
   - Openings (window) = section runs broken where no segment covers the interval (NOT where vertices
     are far apart - Kunos vertices can be 40 mm apart on a continuous surface).
2. **Fit each surface to the VERTICES, not the facets.** Vertices lie on the designer's surface
   (lower door skin: 0.08 mm); flat facets between them are chords.
   - Cubic B-spline height field over the panel's best-fit plane, least squares + bending fairing.
   - Uniform clamped knots, poles at Greville points => surface parameter = plane coordinate, so the
     outline projected on the plane IS the trim curve in parameter space.
   - **Control count and fairing by 5-fold cross-validation** (predict vertices the fit has not seen),
     searching **both directions independently** (4..14 each); simplest model within 5 % of the best.
     Tying the counts to the panel's proportions was a bug (door lower skin: 4x4 1.7 mm -> 5x11 0.08 mm).
3. **Trim.** Outline = the mesh's boundary loops (largest = outside, others = openings); corners where
   the polygon turns > 35 deg; each side a 2D B-spline pinned to its corners (fewest poles within 0.4 mm,
   light fairing). In FreeCAD: 2D curves -> edges on the surface -> `Part.Face(srf, wire)`, `cutHoles`.
4. **Cut bands on their character lines**: prism over the area between the two line curves, extruded
   along the panel normal, `face.common(prism)`. Neighbouring bands use the identical curve -> crisp line.
5. **Display / export**: even mesh (`MeshPart MaxLength=6`, NOT the default deflection mesher - irregular
   triangles tear zebra stripes) + **exact normals from the surface** as custom normals (how Kunos gets
   smooth reflections from few triangles).
6. **Check**: zebra stripes (reflection Z x 40, emission) side by side with the original, separately
   (hide the other - objects in front of the camera pollute the view); exact two-way distances.

## Results (AE86, method test)
- Glass: 4 pieces, 20-40 controls each, areas match (door glass 0.349 = 0.349 m2), within 3 mm everywhere.
- Door: 8 faces, areas match (0.474/0.287/0.062 vs 0.469/0.286/0.061 m2); lower skin 0.08 mm,
  groove bands 0.03-0.2 mm; zebra as smooth as, or smoother than, the original.
- Still weaker: the window frame band and the shoulder roll (~1.5 mm p95) - next to refine.

## Lessons that cost time (do not repeat)
- Measure exactly: point-to-point scoring on 4 mm samples added ~1 mm of fake error to everything.
- Never trim panel edges to a global smooth fit (v4 cubic edge trim silently removed 6 % of the car).
- Glass in Kunos cars is tiny (door glass 41 tris); the black "mask" mesh is texture, not shape.
- Blender's bundled Python has no PIL: run kn5/section analysis outside Blender, load npz inside.

## For the photo phase
The inputs are exactly what photos/blueprints give: panel outlines, character lines (traced curves) and a
few sections/points per surface. The fit + trim + band-cut machinery is unchanged.

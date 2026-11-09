# Blender 3D Modelling: A Thorough, Step-by-Step Practical Guide

**A beginner-friendly reference for learning Blender, understanding its
modelling tools, and building accurate hard-surface objects such as
cars.**

> **Version note:** Blender's interface and shortcuts can change between
> releases. The workflow and principles here are stable; if a button has
> moved, use Blender's search menu (`F3`) and type the tool name. This
> guide assumes the default Blender keymap.

## Contents

1.  What Blender is and how to think about 3D
2.  First launch and interface
3.  Navigation and selection
4.  Objects, modes and transforms
5.  Mesh fundamentals
6.  Essential modelling tools
7.  Modifiers: non-destructive modelling
8.  Topology, edge flow and shading
9.  Precision, dimensions and measurement
10. Reference images and image planes
11. A reliable hard-surface workflow
12. A dedicated vehicle-body workflow
13. Interiors, mechanical parts and detail
14. Materials, UVs and basic presentation
15. Preparing a model for Assetto Corsa
16. Common problems and fixes
17. Practice exercises
18. Keyboard shortcut reference
19. A repeatable modelling checklist
20. Glossary

------------------------------------------------------------------------

## 1. What Blender is and how to think about 3D

Blender is a 3D creation application. You can build geometry, arrange
scenes, assign materials, create lighting, animate, render images and
prepare assets for games and simulators.

A 3D scene is built around three axes:

-   **X**: left and right.
-   **Y**: front and back.
-   **Z**: up and down.

In Blender's default scene, the grid lies on the X/Y plane and Z is
vertical. A car project commonly uses X for width, Y for length and Z
for height, but choose a convention and keep it consistent. Assetto
Corsa projects often use a vehicle-forward axis that must be checked
against the exporter and existing car projects.

### The three things beginners must distinguish

-   **Object**: the scene-level item. It has a name, location, rotation,
    scale and other settings.
-   **Mesh**: the actual vertices, edges and faces that make up a mesh
    object.
-   **Component**: a vertex, edge or face inside a mesh.

Moving an object in Object Mode moves the whole object. Moving a vertex
in Edit Mode changes the mesh itself.

### The most important beginner principle

Do not try to make a complicated object as one continuous blob. Break it
into logical parts. A car might have separate objects for the body
shell, doors, bonnet, bumpers, glass, lights, wheels, dashboard, seats
and suspension. Separate objects are easier to edit, name, troubleshoot
and export.

------------------------------------------------------------------------

## 2. First launch and interface

When Blender opens, the main areas are:

-   **3D Viewport**: the large central area where you inspect and edit
    the scene.
-   **Outliner**: usually top-right; lists objects and collections.
-   **Properties Editor**: usually right-hand side; contains object,
    modifier, material, render and scene settings.
-   **Timeline**: usually along the bottom.
-   **Top bar**: workspace tabs and application menus.

A workspace is a saved arrangement of editor areas. The Layout workspace
is a good place to start. Modelling, UV Editing, Shading and other
workspaces are specialised arrangements.

### The F3 search menu is your safety net

Press `F3`, type a tool or command, then select the result. For example:

-   `Add Cube`
-   `Bevel`
-   `Loop Cut`
-   `Merge by Distance`
-   `Shade Auto Smooth` (the exact wording may differ by version)
-   `Recalculate Outside`

You do not need to memorise every menu location. Learn the tool names
and use search.

### Saving properly

1.  Use **File \> Save As** for the first save.
2.  Save into a clearly named project folder.
3.  Use incremental filenames, e.g. `Nova_body_001.blend`,
    `Nova_body_002.blend`.
4.  Save before risky operations.
5.  Keep source references, textures, exports and backups organised
    beside the project.

Blender's `.blend` file is the editable project. Exported files are not
substitutes for it.

------------------------------------------------------------------------

## 3. Navigation and selection

### Viewport navigation (default keymap)

  Action                       Mouse / key
  ---------------------------- ---------------------------------
  Orbit view                   Middle Mouse Button (MMB) drag
  Pan view                     Shift + MMB drag
  Zoom                         Mouse wheel, or Ctrl + MMB drag
  Frame selected               Numpad `.`
  Front view                   Numpad `1`
  Side view                    Numpad `3`
  Top view                     Numpad `7`
  Opposite view                Ctrl + relevant numpad view
  Perspective / orthographic   Numpad `5`
  Orbit in fixed steps         Numpad `2`, `4`, `6`, `8`
  Toggle camera view           Numpad `0`

If you do not have a numpad, enable **Edit \> Preferences \> Input \>
Emulate Numpad**, or use the View menu. Emulate Numpad makes the number
row act as numpad views, so be aware of the trade-off.

**Perspective** makes distant things appear smaller, like a camera.
**Orthographic** removes perspective distortion and is essential for
comparing a model against flat front, side and top reference drawings.

### Selecting

-   Left-click an object to select it.
-   `A` selects all; `Alt+A` deselects all.
-   `Shift` + click adds/removes items from the selection.
-   `B` starts box selection.
-   `C` starts circle selection; left-drag to select and middle-click to
    deselect, then right-click or Esc to exit.
-   `L` in Edit Mode selects linked geometry under the pointer.
-   `Ctrl+L` selects linked geometry connected to the current selection.

Selection depends on the current mode and selection type. If a click
selects the wrong thing, check whether you are in Object Mode or Edit
Mode and whether vertex, edge or face selection is active.

### Hiding and isolating

-   `H`: hide selected objects/components.
-   `Alt+H`: reveal hidden items.
-   `/` on the numpad: toggle Local View, isolating selected objects.
-   Use Outliner eye/monitor controls to hide objects or disable
    viewport interaction.

Hiding reference objects or completed parts can make complex scenes much
easier to work in.

------------------------------------------------------------------------

## 4. Objects, modes and transforms

### Object Mode and Edit Mode

-   `Tab` switches between Object Mode and Edit Mode for mesh objects.
-   Object Mode changes the whole object.
-   Edit Mode changes its mesh.
-   The mode selector is at the top-left of the 3D Viewport.

Inside Edit Mode, use: - `1` for vertex selection. - `2` for edge
selection. - `3` for face selection.

These are the number keys above the letters in the default keymap. If
Emulate Numpad or a customised keymap causes confusion, use the
on-screen selection icons.

### The three transforms

-   `G` = Grab / Move.
-   `R` = Rotate.
-   `S` = Scale.

After starting a transform, press an axis to constrain it: - `G`, `X`,
type `1`, Enter: move 1 Blender unit along X. - `R`, `Z`, type `45`,
Enter: rotate 45 degrees around Z. - `S`, `Y`, type `0.5`, Enter: halve
the Y dimension.

Use `Shift+X` to constrain to the plane perpendicular to X, and
similarly for other axes. Use the mouse for free transforms, but numeric
entry is better for accuracy.

### Coordinate spaces

-   **Global**: world axes.
-   **Local**: the object's own axes.
-   **Normal**: aligned to the selected geometry's direction.
-   **View**: aligned to the current view.

The transform orientation selector is in the viewport header. Global is
usually easiest for accurate vehicle work.

### Apply transforms

Object scale and rotation can affect modifiers, bevel widths, physics
and exports. When appropriate, use **Object \> Apply \> Rotation &
Scale** or `Ctrl+A` in Object Mode.

Do not apply transforms blindly. Apply them when the modelling/export
workflow requires it, and keep a saved version beforehand. Applying
scale makes the visible dimensions stay the same while the object's
scale values return to 1.

### Pivot point

The pivot determines where rotation and scaling happen. Common choices
include: - Median Point: centre of the selected geometry. - 3D Cursor:
the cursor's position. - Individual Origins: each object's own origin. -
Active Element: the active selected element.

The pivot selector is in the viewport header. For mirroring and vehicle
symmetry, object origins and the world centre line matter.

------------------------------------------------------------------------

## 5. Mesh fundamentals

A mesh is made from:

-   **Vertices**: points in space.
-   **Edges**: lines joining two vertices.
-   **Faces**: flat surfaces bounded by edges.

A face can be triangular, quadrilateral or an n-gon. For controllable
subdivision surfaces, mostly-quad topology is generally easier to
manage. Triangles and n-gons are not automatically wrong, but can cause
shading or deformation issues in curved areas.

### Edit Mode selection types

-   Vertex mode: best for moving individual points and adjusting shape.
-   Edge mode: best for loops, creases, bevels and edge flow.
-   Face mode: best for extruding surfaces, inset faces and selecting
    panels.

### Mesh editing essentials

-   Select a face and press `E` to extrude.
-   Select a face and press `I` to inset.
-   Select edges and press `Ctrl+B` to bevel.
-   Select an edge loop and press `Ctrl+R` to add a loop cut.
-   Select geometry and press `M` for the Merge menu.
-   `F` creates an edge or face from selected vertices/edges.
-   `X` or Delete opens the delete menu.

### Normals

A face normal is the direction the face points. Incorrect normals can
make surfaces shade strangely or appear inside-out.

-   In Edit Mode, select all and use `Shift+N` to recalculate normals
    outside.
-   Use the Face Orientation overlay to inspect outward-facing surfaces.
    Blue is generally outward and red inward in the standard overlay.
-   Open surfaces, intentional internal geometry and complex meshes may
    need manual inspection.

### Manifold geometry

A closed solid mesh should generally have each ordinary edge shared by
exactly two faces. Edges with only one face are boundary edges; edges
shared by more than two faces are non-manifold. Game assets may
intentionally contain open surfaces, but unexpected holes, internal
faces and duplicate geometry can cause problems.

------------------------------------------------------------------------

## 6. Essential modelling tools

This section explains what each tool does, when to use it and the
beginner traps to avoid.

### Move, rotate and scale

Use `G`, `R`, `S` for broad shape adjustment. Add axis constraints and
numeric values for precision. In Edit Mode, these alter components; in
Object Mode, they alter the object transform.

### Extrude (`E`)

Extrusion extends selected vertices, edges or faces and creates
connecting geometry.

**Typical use:** build a box-like object, extend a panel, create a wheel
arch lip or pull a dashboard section from a base surface.

**Safe method:** 1. Select a face. 2. Press `E`. 3. Move the mouse in
the desired direction or type a distance. 4. Confirm with Enter or
left-click. 5. Right-click/Esc immediately after extrusion cancels the
movement but leaves the extrusion in place in some contexts; undo if you
created something unintentionally.

Extruding a vertex or edge behaves differently from extruding a face.
Avoid repeatedly extruding without checking the resulting topology.

### Inset (`I`)

Creates a smaller boundary inside selected faces. Useful for panel
recesses, dashboard bezels, grilles and trim.

-   Select face(s), press `I`, set thickness.
-   Press `I` again during the operation to toggle individual insets
    where supported.
-   Inset thickness is not necessarily a real-world wall thickness if
    the geometry is angled.

### Bevel (`Ctrl+B`)

Rounds or chamfers selected edges.

1.  Select edges (or faces/vertices as needed).
2.  Press `Ctrl+B`.
3.  Move the mouse or type a width.
4.  Use the wheel to increase/decrease segments.
5.  Confirm.

One segment creates a chamfer; more segments create a rounder
transition. A small bevel catches highlights and makes hard-surface
objects look real. Too much bevel makes parts look melted.

**Important:** bevel width depends on scale and settings. Apply scale
where appropriate, inspect the result, and use the modifier version for
repeatable changes.

### Loop Cut (`Ctrl+R`)

Adds a cut through a ring of faces. Hover over an edge direction to
preview the cut, click to confirm, then move or right-click to centre
it.

Use loop cuts to control curvature, support subdivision and define panel
transitions. A loop cut may stop at poles, triangles or topology
changes.

### Knife (`K`)

Cuts custom paths into mesh faces. Click points to define the cut and
confirm. Use it when a loop cut cannot follow the required path. Knife
cuts can create triangles and awkward topology, so inspect the result.

### Loop selection

-   `Alt` + left-click an edge selects an edge loop in many common
    cases.
-   `Ctrl+Alt` + left-click selects an edge ring in many common cases.
-   The exact selection depends on topology and keymap.

Loops are useful for selecting a window frame, wheel-arch perimeter or a
continuous body line.

### Merge (`M`)

Joins selected vertices. Common choices: - At Centre. - At Cursor. - By
Distance (welds nearby/duplicate vertices).

Use **Merge by Distance** carefully. A large distance can collapse
details or damage a mesh. Start with a very small threshold and inspect.

### Bridge Edge Loops

Connects two open edge loops with faces. Useful for connecting sections
of a pipe, wheel arch, body opening or interior trim. The loops should
have compatible vertex counts for clean results.

### Spin and Screw

Spin rotates geometry around a pivot/axis; Screw creates geometry by
rotating and translating a profile. Useful for circular and helical
forms such as vents, springs, bolts and turned components. For simple
round objects, a cylinder may be faster.

### Proportional Editing (`O`)

Moves selected geometry while smoothly influencing nearby geometry. Use
the mouse wheel to adjust the influence radius. Excellent for broad
organic shape corrections, but it can distort carefully controlled panel
lines. Use it on a duplicate or save first.

### LoopTools and other extensions

Some useful tools are supplied as extensions or add-ons depending on
Blender version and installation. Examples include LoopTools for
spacing/relaxing loops. Do not assume an add-on is enabled: check
Preferences \> Get Extensions / Add-ons for your Blender release. Prefer
built-in tools until you understand the mesh.

------------------------------------------------------------------------

## 7. Modifiers: non-destructive modelling

A modifier changes the evaluated result of an object without immediately
destroying the underlying base mesh. This is one of Blender's most
powerful workflows.

Modifiers are found in the Properties Editor under the wrench icon.
Their order matters: modifiers are evaluated from top to bottom.

### Mirror

Creates a mirrored copy across one or more axes.

**Ideal for:** symmetrical car bodies, dashboards, wheels and mechanical
parts.

Workflow: 1. Put the object's origin on the intended mirror plane,
commonly the vehicle centreline. 2. Delete one half of the base mesh. 3.
Add a Mirror modifier. 4. Enable the correct axis. 5. Enable Clipping
while welding the centre seam. 6. Enable Merge. 7. Keep centreline
vertices exactly on the mirror plane.

Do not model both sides independently unless there is a reason.
Mirroring saves time and keeps symmetry.

### Subdivision Surface

Smooths a mesh by subdividing faces.

-   Level 1 or 2 is often enough for a working preview.
-   Higher levels add geometry and slow the scene.
-   Support loops or crease control preserve sharper transitions.

Subdivision does not magically create accurate shape. It smooths the
topology you give it. A poor base cage produces a poor smooth result.

### Bevel modifier

Adds bevels non-destructively. Adjust width, segments, limit method and
clamp overlap. Angle limiting can bevel only edges above a chosen angle;
weight limiting allows selected edges to control bevels.

### Weighted Normal

Helps large flat faces shade more consistently when used with suitable
smoothing and bevel settings. It cannot fix bad topology or incorrect
normals.

### Solidify

Adds thickness to a surface. Useful for body panels, interior trim,
glass shells and sheet-like parts. Check offset and thickness direction.

### Array

Repeats geometry in a line or around an offset. Useful for repeated
grille slats, vents, bolts and tread-like details.

### Curve modifiers and curves

Curves are useful for pipes, window seals, trim strips, cables, body
mouldings and hoses. A curve can be given bevel depth to make it
tubular. Convert to mesh only when needed.

### Boolean

Uses one object to cut or combine another.

-   Difference: subtract cutter.
-   Union: combine volumes.
-   Intersect: keep overlapping volume.

Booleans are useful for holes, vents and openings, but can create dense
or messy topology. Use clean cutter objects, apply scale, inspect
shading and consider a remesh/retopology step for important surfaces.

### When to apply a modifier

Keep modifiers live while you may need to change them. Apply only
when: - an export format or downstream operation requires real
geometry; - another modifier or edit requires the result to be
committed; - you have saved a backup and checked the result.

------------------------------------------------------------------------

## 8. Topology, edge flow and shading

Topology is how vertices, edges and faces are arranged. Good topology
makes a model easier to edit, smoother to shade and more reliable to
export.

### Quads, triangles and n-gons

-   Quads: four-sided faces; usually easiest for subdivision and edge
    loops.
-   Triangles: three-sided faces; unavoidable in many game meshes and
    fine on flat areas.
-   N-gons: faces with more than four sides; convenient for flat
    surfaces, but can triangulate unpredictably on curved or non-planar
    areas.

For a vehicle body, keep important curved surfaces and panel transitions
clean. Put topology changes on flatter or less visible areas where
possible.

### Supporting sharp edges

Subdivision rounds everything. To preserve a sharp feature: - add
support loops close to the edge; - use a crease where appropriate; - use
a bevel modifier; - or avoid subdivision for that part.

Support loops placed too close together create very tight transitions.
Keep checking the silhouette.

### Silhouette before detail

A model can have beautiful bolts, vents and stitching but still look
wrong if its outline is wrong. Work in this order:

1.  overall proportions;
2.  major volumes;
3.  silhouette from front, side, rear and top;
4.  major panel curvature;
5.  openings and panel gaps;
6.  smaller details.

This order is especially important for cars.

### Smooth shading versus geometry

Shade Smooth changes how lighting interpolates across faces; it does not
add geometry. Shade Auto Smooth / Smooth by Angle features vary between
Blender releases. Use object shading controls and search (`F3`) for the
available command. Mark sharp edges or use angle-based smoothing when
needed.

Do not smooth every edge indiscriminately. Flat panels, bevels and
curved surfaces need deliberate shading boundaries.

------------------------------------------------------------------------

## 9. Precision, dimensions and measurement

For accurate modelling, decide on units before starting.

### Set units

Open **Scene Properties \> Units**: - Metric for metres/millimetres. -
Imperial for feet/inches. - Unit Scale controls the relationship between
Blender units and displayed units.

A common practical approach is to model one Blender unit as one metre
and use metric display. A 3.98 m long car is then about 3.98 Blender
units long. Alternatively, model in millimetres if your CAD workflow
requires it. Be consistent.

### Enter exact dimensions

Use the `N` sidebar in the 3D Viewport to inspect Location, Rotation and
Dimensions. The Item panel is useful for exact transforms.

For a cube: 1. Add a cube. 2. Press `N`. 3. Set its dimensions
numerically in the Item panel. 4. Apply scale if required by your
modifier workflow.

### Measure distances

Use the Measure tool in the toolbar or Blender's measurement overlays,
depending on version. You can also inspect vertex coordinates in the
sidebar. For complex CAD-like dimensioning, a dedicated CAD application
may be more suitable.

### Real-world reference discipline

Never scale a model from one photograph alone if you can avoid it.
Perspective, lens distortion, camera angle, suspension height and tyre
size all affect apparent proportions.

Use known dimensions to establish scale, then compare multiple
orthographic references. A trustworthy wheelbase or overall length is
more useful than guessing from a perspective photo.

------------------------------------------------------------------------

## 10. Reference images and image planes

Reference images are guides, not geometry. They need to be aligned and
scaled correctly.

### Add an image reference

Depending on Blender version, use **Add \> Image \> Reference** or
search `Add Image Reference` with `F3`.

Recommended setup: 1. Use a clean side view for the side plane. 2. Add a
front view for the front plane. 3. Add a rear view if available. 4. Add
a top view if available. 5. Rotate/position each image so it lies in the
correct plane. 6. Set opacity low enough that the mesh remains visible.
7. Lock the reference object against accidental selection where
practical. 8. Name each reference clearly.

### Aligning views

-   Side reference: view from the side in orthographic mode.
-   Front reference: front orthographic view.
-   Top reference: top orthographic view.

Ensure the images share a consistent scale and centreline. The wheel
centres, ground line, axle positions and overall length should agree
across views.

### Image limitations

A photograph is not an engineering drawing. A camera may be slightly
above, below or off-centre. Even a seemingly straight-on image can
contain perspective distortion. Do not force every detail to match a
flawed photo. Use multiple references and prioritise the most reliable
ones.

### Reference collection

For each part, record: - source and date; - view direction; - whether it
is a photograph, drawing or scan; - known dimensions; - confidence
level; - what the image can and cannot prove.

This prevents a low-quality picture from silently becoming the modelling
truth.

------------------------------------------------------------------------

## 11. A reliable hard-surface workflow

Hard-surface modelling covers manufactured objects with defined panels,
edges, openings and mechanical features.

### Step 1: Plan the object

Break it into separate parts. Decide which parts need: - a closed solid
mesh; - a thin surface with Solidify; - a curve; - a separate object; -
a boolean cut; - a mirrored construction.

### Step 2: Block out the volume

Use cubes, planes, cylinders and simple extrusions. Do not add small
details yet. Check the object from all important angles.

### Step 3: Establish dimensions

Set the overall width, height, length and major feature positions. Use
numeric transforms and reference images.

### Step 4: Create the main shape

Choose a suitable method: - box modelling for angular parts; - plane
modelling for broad body panels; - curves for trim and tubing; -
cylinders for round mechanical components; - booleans for clean openings
and recesses.

### Step 5: Add thickness and edge treatment

Use Solidify or real thickness. Add small bevels to catch light. Keep
panel gaps separate where possible rather than carving every gap into
one mesh.

### Step 6: Inspect topology and shading

Check for: - overlapping faces; - duplicate vertices; - flipped
normals; - stretched or twisted quads; - boolean artefacts; - unexpected
pinching; - excessive polygons.

### Step 7: Detail only after the shape works

Add fasteners, seams, vents, labels, knobs and trim last.

------------------------------------------------------------------------

## 12. A dedicated vehicle-body workflow

A vehicle is a difficult modelling subject because its identity depends
heavily on subtle proportions and surface curvature. Matching dimensions
is necessary but not sufficient. A body can have the correct wheelbase
and overall length yet still look like the wrong car.

### 12.1 Establish a vehicle coordinate system

Before modelling, define: - vehicle centreline; - front and rear axle
lines; - ground plane; - front and rear extremities; - roof height; -
wheel and tyre dimensions; - overall width and length.

Write down the chosen axes and units. Do not change them halfway
through.

### 12.2 Build a measurement sheet

Record the strongest known dimensions: - overall length and width; -
wheelbase; - front and rear track; - tyre diameter and width; - wheel
diameter; - roof height; - front and rear overhangs; - key glass and
door positions.

Mark each dimension as confirmed, estimated or unknown. Do not present
estimates as factory measurements.

### 12.3 Align references before modelling

Use side, front, rear and top orthographic references. Align the wheel
centres and ground line first. Then align the overall extremities and
centreline. If references disagree, investigate the source rather than
averaging blindly.

### 12.4 Block out the body

Create a low-detail body volume using planes or a structured mesh.
Mirror across the centreline. Concentrate on: - bonnet length and
slope; - windscreen angle; - roof length and crown; - rear hatch
angle; - front and rear overhang; - shoulder line; - sill depth; -
wheel-arch position and shape; - front/rear width taper.

Check front, side, rear and top silhouettes repeatedly. Use a plain
material and orthographic views so lighting does not distract from
shape.

### 12.5 Build body panels as controlled surfaces

For broad curved panels, plane modelling is often effective: 1. Start
with a small grid of quads. 2. Place boundary vertices to match the
reference silhouette. 3. Add loops only where curvature changes. 4.
Shape cross-sections using front/top views. 5. Keep the mesh evenly
distributed. 6. Use subdivision carefully, with support loops only where
required. 7. Inspect reflections or a simple glossy material to reveal
waviness.

Do not add dozens of loops to force a surface into shape. More geometry
can make a bad shape harder to control.

### 12.6 Separate panels logically

Doors, bonnet, hatch, wings, bumpers and glass should generally be
separate objects or clearly separated surface regions. This makes panel
gaps, materials and game export easier.

A realistic panel gap is a small, consistent gap or dark separation, not
a huge trench. Use reference photos to judge the width.

### 12.7 Wheel arches

Wheel arches strongly affect a car's identity. - Establish wheel centre
and tyre radius first. - Match the arch's start/end positions and
curvature. - Check the arch from side and front angles. - Ensure
left/right symmetry. - Avoid a mathematically perfect semicircle unless
the real car has one.

### 12.8 Glass, lights and trim

Create separate objects for glass, lamp lenses, grilles, seals, badges
and mouldings. Use curves for rubber seals and narrow trim. Avoid
modelling tiny surface details before the surrounding panel curvature is
correct.

### 12.9 Validate continuously

At every major stage, compare: - side orthographic silhouette; - front
orthographic width and height; - rear silhouette; - top-view plan
shape; - three-quarter view; - wheel/arch relationship; - window-to-body
proportions.

Use the same camera/view and reference alignment for each comparison.
Keep screenshots of each milestone.

### 12.10 A practical quality gate

Do not move on to detail until: - wheel centres and wheelbase match; -
overall dimensions are correct; - roof, bonnet and hatch silhouettes
look right; - front and rear widths are believable; - major glass
openings are in the right places; - the model reads as the correct
vehicle from a distance.

**Key lesson:** dimensional accuracy does not guarantee visual accuracy.
Surface curvature, cross-sections, feature placement and silhouette are
what make a specific vehicle recognisable.

------------------------------------------------------------------------

## 13. Interiors, mechanical parts and detail

### Interior modelling

Model large forms first: 1. floor and firewall; 2. dashboard volume; 3.
centre console; 4. door cards; 5. seats; 6. steering wheel and column;
7. pedals and gear lever; 8. instruments and switches; 9. trim, seams
and small details.

Use separate objects for dashboard fascia, instrument binnacle, gauges,
vents, switches and trim. This makes materials and animation easier.

### Mechanical components

Use cylinders, circles, curves, arrays and bevels for: - shafts and
rods; - suspension links; - springs; - exhaust tubing; - brake discs; -
hubs; - bolts; - hoses and cables.

Build mechanical parts around measured pivots and attachment points. For
a simulator, the location and orientation of suspension and steering
parts may matter more than hidden visual detail.

### Repeated details

Use Array for repeated slats, bolts and similar parts. Use linked
duplicates (`Alt+D`) when multiple objects should share mesh data;
editing one linked mesh updates the others. Use ordinary duplicate
(`Shift+D`) when copies must become independent.

------------------------------------------------------------------------

## 14. Materials, UVs and basic presentation

### Materials

A material controls how a surface looks. In the Material Properties or
Shader Editor, the Principled BSDF is a common starting point.

Important controls: - Base Color; - Metallic; - Roughness; -
Alpha/transmission-related controls (version and rendering engine
dependent); - Normal maps and other texture inputs.

A car's paint is not simply a bright colour. Clearcoat, roughness,
metallic flakes and lighting affect the appearance. For modelling, use
neutral clay or simple materials until the shape is right.

### UV mapping

UVs tell a 2D texture how to wrap around a 3D mesh.

Basic process: 1. Select the mesh. 2. Enter Edit Mode. 3. Select the
faces to unwrap. 4. Mark seams where the surface should split. 5. Press
`U` and choose an unwrap method. 6. Inspect in UV Editing workspace. 7.
Pack islands and avoid unnecessary stretching.

Different parts may need different UV approaches. A simple box
projection may be enough for some mechanical objects; a body shell often
needs carefully placed seams.

### Lighting and inspection

Use a large area light and a neutral material to inspect surface
quality. Long reflections reveal waviness. Rotate the lighting around
the model rather than judging the surface under one light.

------------------------------------------------------------------------

## 15. Preparing a model for Assetto Corsa

This section is a modelling/export checklist, not a substitute for the
current Assetto Corsa SDK, exporter documentation or a known-good
project template. Export requirements depend on the toolchain.

### Separate visual and functional concerns

A simulator car may need: - visual body and interior meshes; - wheels
and tyres; - steering wheel and driver-related pivots; -
suspension/steering reference objects; - collision meshes; - LOD
meshes; - materials and textures; - correctly named and oriented
objects.

Use the naming, hierarchy, origin and axis conventions required by your
actual exporter and physics configuration. Do not assume generic Blender
defaults match Assetto Corsa.

### Origins and pivots

Set origins deliberately. Wheel rotation, steering rotation, doors and
other animated components need sensible pivots. Place origins at real
rotation centres, not arbitrary mesh centres.

### Geometry budget

A high-detail Blender model may be too heavy for real-time use. Use
detail where it contributes to the player's view. Consider: - lower
polygon counts for hidden components; - normal maps for small surface
detail; - separate LOD levels; - simplified collision geometry; -
efficient material use.

### Export validation

1.  Save the `.blend` source.
2.  Check object names and hierarchy.
3.  Apply modifiers only as required by the exporter.
4.  Check normals, scale and transforms.
5.  Export a small test.
6.  Import into the target tool/game.
7.  Check orientation, materials, pivots and missing geometry.
8.  Fix the source and repeat.

Always test with a known-good car project or exporter example. A model
that looks correct in Blender can still be incorrectly oriented or
configured in the simulator.

------------------------------------------------------------------------

## 16. Common problems and fixes

  --------------------------------------------------------------------------
  Problem                 Likely cause               What to try
  ----------------------- -------------------------- -----------------------
  I cannot move the whole You are in Edit Mode       Press `Tab` to return
  model                                              to Object Mode

  I cannot edit           You are in Object Mode     Select mesh and press
  individual points                                  `Tab`

  The model disappears    View clipping, hidden      Frame selected with
                          object, wrong view or      Numpad `.`, check
                          extreme zoom               Outliner and clipping

  Bevel looks enormous    Object scale is unapplied  Inspect scale; apply
                          or width is too large      scale if appropriate;
                                                     reduce bevel

  Mirror seam splits      Centre vertices are not on Align centreline,
                          mirror plane or            enable Merge and
                          merge/clipping is off      Clipping

  Subdivision pinches     Poor topology, poles or    Simplify topology; move
                          uneven edge flow           poles; add support
                                                     loops carefully

  Faces look black or     Normals, overlapping       Recalculate normals;
  strange                 geometry or shading issue  inspect Face
                                                     Orientation; check
                                                     duplicates

  Boolean creates ugly    Poor cutter, coplanar      Apply scale, improve
  shading                 surfaces or dense topology cutter, inspect
                                                     topology, bevel
                                                     selectively

  Model looks right from  Shape was built against    Compare front, side,
  one angle only          one reference              rear and top
                                                     orthographic views

  Car has correct         Incorrect cross-sections,  Fix silhouette and
  dimensions but looks    curvature or feature       surface shape before
  wrong                   placement                  adding detail

  File becomes slow       Too many high-resolution   Lower viewport levels,
                          modifiers or dense meshes  hide objects, simplify
                                                     geometry

  Export is rotated or    Axis/units/origin/export   Check exporter
  scaled wrong            settings mismatch          conventions and test
                                                     against known-good
                                                     asset
  --------------------------------------------------------------------------

### The undo and recovery habit

-   `Ctrl+Z`: undo.
-   `Ctrl+Shift+Z`: redo in the default keymap.
-   Save milestone versions before major operations.
-   Do not rely on Undo as your only backup.
-   If an operation produces an unexpected result, stop and inspect
    before continuing.

------------------------------------------------------------------------

## 17. Practice exercises

Work through these in order. The goal is to learn tool behaviour before
tackling a complex vehicle.

### Exercise 1: Precision block

1.  Add a cube.
2.  Set exact dimensions in the `N` panel.
3.  Move it numerically along X, Y and Z.
4.  Apply scale.
5.  Save the file.

Learn: transforms, axes, units and object mode.

### Exercise 2: Bevelled hard-surface box

1.  Add a cube.
2.  Enter Edit Mode.
3.  Select all edges.
4.  Bevel with `Ctrl+B`.
5.  Add several segments.
6.  Inspect under smooth and flat shading.

Learn: bevel width, segments and shading.

### Exercise 3: Recessed panel

1.  Select a cube face.
2.  Inset with `I`.
3.  Extrude inward with `E`.
4.  Add a small bevel.
5.  Inspect from several angles.

Learn: inset, extrusion and face selection.

### Exercise 4: Mirrored part

1.  Add a cube and delete half the mesh.
2.  Set the object origin on the centre plane.
3.  Add a Mirror modifier.
4.  Enable Merge and Clipping.
5.  Move the centre vertices and observe the seam.

Learn: symmetry and modifier workflow.

### Exercise 5: Curved panel

1.  Add a plane.
2.  Subdivide it a few times.
3.  Shape it with vertex transforms and proportional editing.
4.  Add a Subdivision Surface modifier.
5.  Add support loops and compare the result.

Learn: surface flow and subdivision.

### Exercise 6: Simple wheel

1.  Add a cylinder.
2.  Rotate it so its axis matches the wheel axis in your chosen
    coordinate system.
3.  Set diameter and width numerically.
4.  Bevel the rim edges.
5.  Add a separate hub and tyre.
6.  Set the origin at the wheel centre.

Learn: cylinders, bevels, origins and component separation.

### Exercise 7: Reference-based body blockout

1.  Add aligned side and front references.
2.  Set a known overall dimension.
3.  Add a centreline and axle markers.
4.  Block out the roof, bonnet, floor and rear profile.
5.  Add wheels at measured centres.
6.  Compare front and side silhouettes before adding details.

Learn: orthographic modelling and proportion control.

------------------------------------------------------------------------

## 18. Keyboard shortcut reference

These are default-keymap shortcuts commonly used in Blender. Custom
keymaps, operating systems and version changes may alter behaviour. If
one does not work, search for the tool with `F3`.

  Shortcut                 Action
  ------------------------ ---------------------------------------------
  `F3`                     Search commands
  `Tab`                    Toggle Object/Edit Mode
  `1` / `2` / `3`          Vertex / Edge / Face selection in Edit Mode
  `A`                      Select all
  `Alt+A`                  Deselect all
  `G`                      Move
  `R`                      Rotate
  `S`                      Scale
  `X`                      Delete menu
  `E`                      Extrude
  `I`                      Inset
  `Ctrl+B`                 Bevel
  `Ctrl+R`                 Loop Cut
  `K`                      Knife
  `M`                      Merge menu
  `F`                      Make edge/face
  `Shift+N`                Recalculate normals outside
  `O`                      Toggle Proportional Editing
  `H` / `Alt+H`            Hide / reveal
  `Shift+D`                Duplicate
  `Alt+D`                  Linked duplicate
  `Ctrl+A` (Object Mode)   Apply transforms menu
  `N`                      Sidebar
  `T`                      Toolbar
  `Ctrl+Z`                 Undo
  `Ctrl+Shift+Z`           Redo
  `Numpad 1`               Front view
  `Numpad 3`               Side view
  `Numpad 7`               Top view
  `Numpad 5`               Perspective/orthographic
  `Numpad .`               Frame selected
  `Numpad 0`               Camera view

------------------------------------------------------------------------

## 19. A repeatable modelling checklist

Before modelling: - \[ \] Choose units and axis convention. - \[ \]
Gather multiple reliable references. - \[ \] Record confirmed dimensions
and estimated dimensions separately. - \[ \] Plan object breakdown and
naming. - \[ \] Save a clean starting file.

During modelling: - \[ \] Work from large forms to small details. - \[
\] Use orthographic views for proportion checks. - \[ \] Use numeric
transforms for known dimensions. - \[ \] Keep symmetry with Mirror where
suitable. - \[ \] Keep modifiers live while practical. - \[ \] Check
topology, normals and shading regularly. - \[ \] Save milestone
versions.

Before export: - \[ \] Confirm scale and orientation. - \[ \] Confirm
object names, hierarchy and origins. - \[ \] Check normals and unwanted
duplicate geometry. - \[ \] Confirm required modifiers are applied. - \[
\] Check materials and textures. - \[ \] Export a test and inspect it in
the target application.

For a vehicle: - \[ \] Wheelbase and wheel centres are correct. - \[ \]
Overall length, width and height are checked. - \[ \] Side, front, rear
and top silhouettes agree with references. - \[ \] Roof, glass, bonnet,
hatch and wheel arches are recognisable. - \[ \] Major panel boundaries
are correctly placed. - \[ \] Details have not been allowed to distract
from body shape.

------------------------------------------------------------------------

## 20. Glossary

-   **Bevel**: a chamfered or rounded transition along an edge.
-   **Boolean**: geometry operation that combines or cuts mesh volumes.
-   **Cage / base mesh**: the editable underlying geometry before
    modifiers.
-   **Edge flow**: the direction and organisation of connected edges.
-   **Extrude**: extend selected geometry while creating connecting
    faces.
-   **Face normal**: direction a face points.
-   **Manifold**: geometry with a consistent solid surface, typically
    two faces per edge.
-   **Modifier**: a procedural operation applied to an object's
    evaluated geometry.
-   **N-gon**: a face with more than four sides.
-   **Non-destructive**: a workflow that preserves editable source
    geometry.
-   **Origin**: the object's transform reference point.
-   **Orthographic view**: view without perspective size distortion.
-   **Pivot**: point around which an operation rotates or scales.
-   **Topology**: arrangement of vertices, edges and faces.
-   **UV map**: 2D coordinate layout for placing textures on a 3D mesh.
-   **Vertex**: a point in a mesh.

## Final advice

Learn a small set of tools deeply: navigation, selection, transforms,
extrude, inset, bevel, loop cut, mirror, subdivision, solidify and
curves. These cover a huge amount of practical modelling.

For accurate vehicle modelling, spend more time measuring, aligning
references and correcting the silhouette than adding detail. A simple
model with the right proportions and surface curvature will look more
convincing than a highly detailed model with the wrong shape.

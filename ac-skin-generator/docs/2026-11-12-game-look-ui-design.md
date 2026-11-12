# Ratty's4Skin Generator – game-look UI (v1.8.0) – design

Agreed with Nik on 12 Nov 2026. Mockups: `docs/mockups/E_preview_with_own_ghost.jpg` (after a preview) and
`docs/mockups/F_before_preview.jpg` (before one); made by `docs/mockups/mock*.py` (the pictures are not in git).

## What Nik asked for
- 11 Nov: "the ui itself, and the logos addition is great. we should make it look more snazzy at some point. like a
  need for speed home screen type interface."
- 12 Nov choices: **reskin, same layout** (not a new game-style flow, not a home screen); colours of style B
  (carbon + orange) with the floor of style C (hazard stripes); a **ghosted car in the background, always the car
  being edited**; build it by **restyling the current Tkinter app**; finish with the **installer and zip**.

## Out of scope
Layout changes, new features, a home/splash screen, animations, sounds. Every control, setting, label text and
position stays as it is in v1.7.2. How skins are made does not change.

## 1. The look (all tabs, same layout)
- Colours: window `#0d0d0d`, panels `#171717`, raised parts `#202020`, fields `#101010`, lines `#363636`,
  text `#f4f4f4`, hints `#8e8e8e`, accent orange `#ff6a00`, second accent white.
- Fonts: **Bahnschrift** (Windows 10/11) Bold / SemiBold Condensed, slanted, capitals, for tabs, buttons and section
  titles; **Segoe UI** for normal text and lists; Consolas for the log. If Bahnschrift is missing, Segoe UI Semibold.
- Top strip: "RATTY'S **4SKIN** GENERATOR" left; car name, skin name and version right; orange line under it.
- Tabs, buttons and view chips are slanted shapes (drawn images). Active tab, **Create skin in car** and **Add logos…**
  are filled orange with a glow; Preview has an outline; edit buttons are outlined grey.
- Lists: dark rows, alternate rows a shade lighter, selected row with an orange bar on the left and an orange fade;
  column titles in small white Bahnschrift capitals.
- Drop-downs, entries, spin boxes: dark field, orange underline, orange arrow. Tick boxes: dark square, orange tick.
- Progress bar: orange on dark with a "stage" label and percentage. Log box dark; "PREVIEW ONLY" and warnings orange.
- The app's own pop-ups (Edit text, Lens colour, yes/no, errors, info) use the same dark style. Windows file pickers
  stay as Windows draws them.
- Dark Windows title bar (Windows 11 / 10 20H1+; ignored where not supported).

## 2. The preview area
- Background drawn behind the car picture: carbon-fibre weave with a dark edge, orange spotlight from above.
- Floor (C): darker, dotted pattern getting bigger towards the front, orange-black hazard stripes along the bottom,
  orange floor line and an orange glow under the car.
- **Ghost**: the car being edited, seen from the front, drawn as orange lines with a faint fill, sized to fit above the
  floor and fading into it. Made from the car's own 3D model (untextured, so no badges) when a car is picked, in a
  background thread, and kept on disk per car (the app's data folder, `ghosts/<car>.png`) so it is made once.
- The car: preview views come with a clean cut-out (alpha from the renderer's coverage, not keyed out of the grey),
  so they sit on the floor with no grey box; a faint reflection under each side view.
- Labels: top left the side shown and the selected item; bottom right "PREVIEW ONLY · NOT SAVED" until the skin is
  created; before the first preview, "PRESS PREVIEW" over the ghost.
- Editing unchanged: click, drag, wheel, Shift+wheel, dashed boxes (now orange), Open full size. "All sides" uses the
  same background behind the sheet of views. Hit-testing of boxes uses the same picture coordinates as now.

## 3. Code
- **`theme.py`** (new, look only): palette and fonts; ttk style set-up (clam-based) for frames, labels, entries,
  combo boxes (incl. the drop-down list), spin boxes, tick boxes, tree views, scroll bars, progress bar; drawn widgets
  `SlantTabs` (tab strip that shows/hides the tab frames; `select(i)` like a Notebook), `SlantButton` (normal /
  hover / pressed / disabled, `configure(state=...)` like a ttk button), `ChipGroup` (view chips bound to the existing
  `view_var`); `garage(w, h, floor_y)` background; `ghost_image(grey_render, w, h)`; `compose_preview(...)`;
  themed dialogs with the same signatures as `tkinter.messagebox` (showerror, showwarning, showinfo, askyesno);
  `dark_title_bar(window)`.
- **`rattys4skin.py`**: builds the same widgets from `theme.py`; `messagebox` name kept (bound to the themed
  dialogs) so tests can still replace it; preview drawing composes background + ghost + car; ghost made in a thread
  when the car changes. Logic, settings and wording untouched.
- **`skingen.py`**: `render_view(..., alpha=True)` option returning RGBA (coverage before down-scaling) and
  `ghost_view(car)` (untextured front view). Nothing else changes.
- If anything in the look fails (no ghost possible, font missing, title bar call refused) the app carries on with the
  plain garage / fallback font / normal title bar, and logs nothing alarming.

## 4. Checks (before saying it works)
- Run the real app (`tests/ui_drive.py`, updated for the new tab strip) on a copy of Nik's settings with his cars:
  Talbot, Kadett, S13, Lacetti. Every tab, Preview, select / move / resize a logo, open each pop-up, Clear all, lens
  colour chart; the log must show no errors; window picture per step.
- Same design built with v1.7.2 and v1.8.0 for one car: the skin's files must be identical.
- Ghost made for each test car; picking another car changes it; second time it loads from disk.
- One screenshot per tab sent to Nik.

## 5. Release
Version 1.8.0. README (look + preview area), TODO. `python build.py` → `release/Rattys4SkinGenerator_Setup.exe` and
`release/Rattys4SkinGenerator_v1.8.0.zip`; install it once and run the installed exe as a smoke test. Commit and push.

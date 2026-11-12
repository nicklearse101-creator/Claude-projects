# Game-look UI (v1.8.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reskin Ratty's4Skin Generator in the agreed carbon/orange game look with a garage preview and a ghost of the
car being edited, with no change to layout, wording or the skins it makes, then ship v1.8.0 (installer + zip).

**Architecture:** A new `theme.py` holds every look decision: pure-PIL drawing (slanted shapes, text, garage, ghost,
preview composition) plus the Tk side (ttk style, drawn tabs/buttons/chips, header, dark dialogs, dark title bar).
`rattys4skin.py` swaps its widgets for the themed ones and composes the preview through `theme`. `skingen.py` gains an
alpha option on `render_view` and a `ghost_view` helper; skin output stays byte-identical.

**Tech Stack:** Python 3.14.7, Tk 9.0.4 (tkinter/ttk, `clam` base theme), Pillow, numpy, pytest 9.1.1, PyInstaller.

**Spec:** `ac-skin-generator/docs/2026-11-12-game-look-ui-design.md` (mockups in `docs/mockups/`, look at
`E_preview_with_own_ghost.jpg` and `F_before_preview.jpg`; `mock.py`/`mock2.py` hold the drawing recipes to reuse).

## Global Constraints

- Never write to C:. Every command runs with `TEMP=TMP=D:\ClaudeData\tmp`; PyInstaller with
  `PYINSTALLER_CONFIG_DIR=D:\ClaudeData\pyinstaller`. Do not run the Setup installer (it installs to C:); Nik does.
- App runs for tests use a copy of Nik's data: `D:\ClaudeData\tmp\r4s_appdata\Rattys4SkinGenerator` (copied from
  `%APPDATA%\Rattys4SkinGenerator`), passed as `APPDATA=D:\ClaudeData\tmp\r4s_appdata`. Never the real one.
- Test cars (in `D:\SteamLibrary\steamapps\common\assettocorsa\content\cars`): `talbot_sunbeam_lotus_81_works_backup_v6`,
  `opel_kadett_s2`, `gravygarage_oaktree_street_s13_tye`, `wtcc_chevrolet_lacetti`.
- No new pip dependencies. Fonts come from Windows: PIL `C:/Windows/Fonts/bahnschrift.ttf` with variation names
  `'Bold Condensed'` / `'SemiBold Condensed'`; Tk families `'Bahnschrift SemiBold Condensed'`, `'Bahnschrift Condensed'`.
  Fallbacks: `segoeuib.ttf` / `'Segoe UI Semibold'`.
- Colours: BG `#0d0d0d`, PANEL `#171717`, RAISED `#202020`, FIELD `#101010`, LINE `#363636`, TEXT `#f4f4f4`,
  MUTED `#8e8e8e`, ACC `#ff6a00`, ACC2 `#ffffff`.
- Every existing label, button and message keeps its words. Tabs, buttons, view chips, section titles and field labels
  may be shown in capitals; nothing else changes case.
- Skin output (all files `skingen.generate` writes, plus `generator_preview.png`) must be byte-identical to v1.7.2.
- Unit tests: `python -m pytest -p no:cacheprovider tests/test_<name>.py -q` (never bare `pytest tests/`: the older
  `tests/test_gen.py` / `test_stock.py` are argv scripts and break collection).
- Commit after each task in `D:\Claude\Claude-` on `main`, stage only `ac-skin-generator/` paths (other folders have
  another session's work), push, message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. Window at its minimum size (1000x640) or the preview area squeezed to ~200 px: composition must still draw, never
   raise on negative sizes. Test in Task 2 (`test_compose_tiny`).
2. Picking cars quickly one after another: a slow ghost from the previous car must not replace the new car's ghost.
   Test in Task 5 (`test_stale_ghost_ignored`).
3. A car mod updated after its ghost was cached: the ghost must be redrawn, not the old one shown. Test in Task 5
   (`test_ghost_cache_valid`).
4. Bahnschrift missing (older Windows): text and shapes still draw with the fallback font. Test in Task 2
   (`test_text_image_fallback`).
5. Very long car or skin names in the header: cut with "…" inside the strip, never drawn over the edge. Test in
   Task 3 (`test_header_long_name`).

---

### Task 1: Baseline and renderer alpha / ghost view

**Files:**
- Create: `tests/same_output.py`, `tests/test_render_alpha.py`
- Modify: `skingen.py:2576-2615` (`render_view`), `skingen.py:2685-2688` (`preview_views`), `skingen.py:2960` (generate's call)

**Interfaces:**
- Produces: `render_view(car, view, tex_imgs, tms=None, width=1000, bg=(235, 236, 240), layers=(), alpha=False) -> Image`
  (alpha=True: RGBA whose RGB is exactly the alpha=False image; A = coverage, drawn at the same super-sampling and
  down-scaled on its own with LANCZOS, never through an RGBA resize).
- Produces: `preview_views(car, tex_imgs, tms, width=1600, layers=(), alpha=False) -> dict[str, Image]`; `generate`
  calls it with `alpha=True` (views go to the app only; `preview_sheet` untouched).
- Produces: `ghost_view(car: Car, width: int = 1200) -> Image` = `render_view(car, 'front', {}, width=width, bg=(0, 0, 0), alpha=True)`.

- [ ] **Step 1: Write `tests/same_output.py OUT_JSON`**: for the Talbot (`backup_v6`) with `skingen.DEFAULT_DESIGN` plus
  `win_enable=True, lens_colour='#ffd21f', number='101', team='RATTY RACING', name='NICKLEARSE101'` and one logo
  (`starter_logos/ratty_racing_logo.jpg` on `doors`), run `skingen.generate(car, d, 'same_test', out_root=TMP,
  views=views, info={}, write=True, log=lambda *a: None)`; write `{relative path: sha256}` for every file written plus
  `'generator_preview.png': sha256(PNG bytes of rattys4skin.App.compose(views))` to OUT_JSON. TMP under
  `D:\ClaudeData\tmp\r4s_same`.
- [ ] **Step 2: Run it twice on the unchanged code**: `python tests/same_output.py D:\ClaudeData\tmp\r4s_same\v172_a.json`
  then `..._b.json`. Expected: the two files are equal (generation is deterministic). Keep `v172_a.json` as the baseline.
- [ ] **Step 3: Write `tests/test_render_alpha.py`** (Talbot car loaded once, module fixture):
  - `test_alpha_rgb_identical`: `np.array_equal(np.asarray(render_view(car,'left',{},width=400)), np.asarray(render_view(car,'left',{},width=400,alpha=True))[..., :3])`
  - `test_alpha_coverage`: alpha at (2, 2) == 0; alpha at the image centre-bottom third (on the body) == 255.
  - `test_ghost_view`: mode `'RGBA'`, width 1200, alpha has both 0 and 255.
- [ ] **Step 4: Run, expect FAIL** (`alpha` unknown keyword / `ghost_view` missing).
- [ ] **Step 5: Implement** the three interfaces above.
- [ ] **Step 6: Run tests, expect PASS**; rerun `same_output.py ..._new.json` and diff with `v172_a.json`: identical.
- [ ] **Step 7: Commit** `Skin generator: preview views with a clean cut-out, ghost view of a car`.

### Task 2: theme.py – drawing (pure PIL)

**Files:**
- Create: `theme.py` (top part), `tests/test_theme_draw.py`

**Interfaces:**
- Produces constants `BG, PANEL, RAISED, FIELD, LINE, TEXT, MUTED, ACC, ACC2` (hex strings above), `PAD = 6`.
- `text_image(text: str, size: int, colour: str, style: str = 'Bold Condensed', italic: float = 0.18, glow: str | None = None) -> Image` (RGBA, tight + glow margin).
- `slant_image(w: int, h: int, label: str, kind: str, state: str = 'normal', size: int = 13) -> Image` – RGBA of
  `(w + 2*PAD, h + 2*PAD)`, parallelogram leaning right (skew `h // 4`). kinds: `primary` (ACC fill + glow, white text),
  `secondary` (RAISED fill, ACC2 1.6 px outline, ACC2 text), `outline` (RAISED fill, LINE outline, TEXT text),
  `tab` (RAISED, LINE outline, MUTED text), `tab_active` (= primary), `chip` (= tab, TEXT text), `chip_active` (ACC2
  fill, `#111111` text). states: `hover` lightens fill 12 %, `pressed` darkens 15 %, `disabled` 45 % opacity.
- `garage(w: int, h: int, floor_y: int) -> Image` – opaque RGBA: B's carbon weave + vignette + ACC spotlight cone
  (alpha 22); C's floor below `floor_y`: dark (8,8,8,215), dots growing towards the bottom, ACC/black hazard stripes
  40 px high on the bottom edge, ACC 2 px floor line, ACC glow ellipse under the car (as `mock2.preview_bg_mix`).
- `ghost_image(grey: Image, max_w: int, max_h: int) -> Image` – recipe of `mock2.ghost_image`: edges + faint fill in
  ACC, fitted inside max box, alpha fading to 0 on the bottom row.
- `cutout(view: Image, bg=(235, 236, 240)) -> Image` – RGBA with the grey edge un-mixed: `rgb = (rgb - bg*(1-a)) / a`.
- `preview_background(w: int, h: int, ghost: Image | None) -> Image` – garage with the ghost fitted to
  `(w*0.98, floor_y-20)`, top 14 px, centred; `floor_y = int(h * 0.80)`.
- `compose_preview(background: Image, car: Image | None, view: str, title: str, pill: str | None, prompt: tuple[str, str] | None) -> tuple[Image, tuple[int, int, int, int] | None]`
  – returns RGB canvas image and the car's `(ox, oy, w, h)`. Side views (`left/right/front/rear`): car fitted into
  `(W-40, floor_y-70)`, bottom on `floor_y`, centred, reflection under it (flipped, alpha 0.28→0). `top`/`all`:
  fitted into `(W-40, H-90)`, centred between y 70 and H-20, no reflection. Title top-left at (18, 24) size 20;
  pill bottom-right (ACC outline, size 12); prompt centred at 0.62 H: line 1 size 46 white with ACC glow, line 2
  Segoe 15 MUTED.

- [ ] **Step 1: Write tests** – `test_slant_sizes` (every kind/state returns `(w+12, h+12)` RGBA, corner (0,0) alpha 0);
  `test_garage_opaque` (alpha all 255, pixel at `(w//2, h-5)` is ACC or black); `test_ghost_fits_and_fades` (size within
  box, last row alpha max 0); `test_cutout_unmixes` (a pixel 50 % (255,0,0) over the grey comes back ≈ (255,0,0), a=128);
  `test_compose_side_on_floor` (geom bottom == `int(H*0.80)`); `test_compose_tiny` (W=H=200 and W=H=60 do not raise,
  geom inside canvas); `test_text_image_fallback` (with `theme.BAHN` pointed at a missing file still returns a
  non-empty image).
- [ ] **Step 2: Run, expect FAIL** (no module `theme`).
- [ ] **Step 3: Implement** the interfaces (port the mockup recipes; no Tk import in this part).
- [ ] **Step 4: Run tests, expect PASS.** Save `compose_preview` output for the Talbot views from Task 1 to
  `D:\ClaudeData\tmp\r4s_shots\compose_left.png` and compare by eye with mockup E.
- [ ] **Step 5: Commit** `Skin generator: theme drawing (garage, ghost, slanted shapes)`.

### Task 3: theme.py – Tk style, widgets, dialogs, title bar

**Files:**
- Modify: `theme.py` (Tk part, below the drawing part)
- Create: `tests/test_theme_tk.py`, `tests/theme_demo.py` (window with every themed control, saves a screenshot)

**Interfaces:**
- `apply_style(root: tk.Tk) -> None` – `clam`; frames PANEL (`Window.TFrame` BG); labels TEXT on PANEL; styles
  `Note.TLabel` (MUTED, Segoe UI 9), `Field.TLabel` (Bahnschrift SemiBold Condensed 10, MUTED), `Section.TLabel`
  (Bahnschrift SemiBold Condensed 12, TEXT), `Status.TLabel` (MUTED); entries/combos/spinboxes: FIELD field, TEXT,
  ACC arrows, an image field element with a 2 px ACC bottom line (LINE border; whole border ACC on focus) – fallback if
  the layout is refused: clam `bordercolor` LINE / focus ACC; combobox drop-down list via `option_add('*TCombobox*Listbox…')`
  FIELD / TEXT / select ACC; tick boxes: image indicator (FIELD square, LINE / ACC border, ACC tick); tree views: FIELD,
  rows via an image `Treeview.Row` element (selected: 4 px ACC bar + ACC fade) – fallback solid `#3a1d08` selection with
  ACC text; headings PANEL, Bahnschrift 10 ACC2; `Orange.Horizontal.TProgressbar` (trough RAISED, bar ACC, 6 px);
  scrollbars dark; `TLabelframe` PANEL with ACC2 Bahnschrift label; `TSeparator` LINE. Images kept on `root._theme_imgs`.
- `class SlantTabs(ttk.Frame)`: `add(title: str, padding: int = 10) -> ttk.Frame` (all pages gridded in one cell, so
  the panel keeps the tallest page's size like a Notebook); `select(index: int)`; `index() -> int`; strip drawn with
  `slant_image(..., 'tab'|'tab_active')`, hover state; ACC 2 px line under the strip.
- `class SlantButton(tk.Canvas)`: `__init__(parent, text, command=None, kind='outline', size=13, width=None, height=28, bg=PANEL)`;
  `invoke()`; `state(spec=None)` ttk-compatible (`['disabled']`, `['!disabled']`, returns current states); `configure(text=…)`.
  Width defaults to text width + 26. Hand cursor.
- `class ChipGroup(tk.Canvas)`: `__init__(parent, items: list[tuple[str, str]], variable: tk.StringVar, command=None, bg=BG)`.
- `class Header(tk.Canvas)`: `__init__(parent, version: str)`, height 54, BG PANEL; `set_car(car: str, skin: str)`;
  left "RATTY'S" TEXT + "4SKIN" ACC glow + "GENERATOR" MUTED; right car (size 15) over "SKIN <skin> · v<version>"
  (size 11.5), both cut with "…" to fit half the width; bottom line ACC (left 60 %) / ACC2 (rest).
- `messagebox = types.SimpleNamespace(showerror, showwarning, showinfo, askyesno)`; each `(title, message, parent=None, icon=None, **kw)`;
  modal dark Toplevel, Section title, Segoe message, SlantButtons (`OK`, or `Yes` primary / `No` outline), Enter/Esc;
  `askyesno` returns bool, the others None.
- `dark_title_bar(win) -> bool` – `DwmSetWindowAttribute(GetParent(win.winfo_id()), 20, 1)` then attribute 19; False on failure.
- `style_toplevel(win)` – BG background + `dark_title_bar`.

- [ ] **Step 1: Write tests** (one hidden `tk.Tk()` per module): `test_tabs_select` (add 3 pages, `select(2)` →
  `index()==2`, page 2 is top of stacking order); `test_button_invoke_and_disable` (invoke calls command once;
  after `state(['disabled'])` a `<Button-1>`+`<ButtonRelease-1>` does not call it; `state()` contains `'disabled'`);
  `test_chips_set_variable` (click handler for 'left' sets var and calls command); `test_askyesno_yes`
  (`root.after(200, <invoke Yes>)`, returns True); `test_header_long_name` (200-char car name: drawn text width ≤ half
  the header); `test_apply_style_runs` (no TclError; `ttk.Style().theme_use() == 'clam'`).
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run tests, expect PASS**; run `python tests/theme_demo.py D:\ClaudeData\tmp\r4s_shots\demo.png` and check by
  eye: field underline, tick boxes, tree selection bar, drop-down list colours; note any fallback used.
- [ ] **Step 5: Commit** `Skin generator: theme widgets, dark dialogs and title bar`.

### Task 4: rattys4skin.py – controls in the new look

**Files:**
- Modify: `rattys4skin.py` (`build` 188-416, `font_image` 427-436, `edit_text` 445-498, `colour_button` 506-521,
  `swatch_picker` 523-530, `log` 645-646, `set_progress` 707-708, `run`/`done` button states), `tests/ui_drive.py`
  (`show_tab` → `app.tabbar.select(i)`; `nb` line removed)

**Interfaces:**
- Consumes: Task 3 (`apply_style`, `SlantTabs`, `SlantButton`, `ChipGroup`, `Header`, `messagebox`, `style_toplevel`).
- Produces for Task 5: `self.tabbar`, `self.header`, `self.btn_prev`, `self.btn_save` (SlantButtons), `self.canvas`
  (unchanged role), `self.view_var` (now driven by a ChipGroup), `self.pct` (percentage label).

- [ ] **Step 1:** `from tkinter import ttk, filedialog, colorchooser` + `import theme` + `messagebox = theme.messagebox`
  (module-level name kept so tests can still replace it). `build()`: `theme.apply_style(self)`, `theme.dark_title_bar(self)`,
  Header packed on top (`set_car` from the car's `ui/ui_car.json` "name", else folder name, on car pick and on
  `skin_name` change); root `Window.TFrame`; Notebook → `self.tabbar = theme.SlantTabs(left)`; `row()` labels use
  `Field.TLabel` with the text in capitals; `note()` uses `Note.TLabel`; "Pattern from a picture" and "Where to write
  them:" use `Section.TLabel` (capitals); every `ttk.Button` → `SlantButton` (Add logos…, Create skin in car: primary;
  Preview: secondary, size 19, height 44; all others outline; edit bar keeps all nine incl. Reset); view Radiobuttons →
  `ChipGroup(vb, …, self.view_var, self.on_view)`; Open full size outline; progress bar `Orange.Horizontal.TProgressbar`
  with `self.pct` (Bahnschrift, ACC) right of the status; log box FIELD / MUTED / Consolas 8, tag `warn` ACC for lines
  starting `PREVIEW ONLY` or `ERROR`; `sel_label` colours MUTED / warn ACC (replacing `#444` / `#b00020`);
  `refresh_library` / `refresh_used` tag every second row `odd` (background RAISED) – drop it if the image row element
  hides tag backgrounds; logo thumbnails on RAISED instead of `(60, 60, 66)`.
- [ ] **Step 2:** Pop-ups: `edit_text` and `swatch_picker` Toplevels call `theme.style_toplevel`, PANEL frame, OK primary /
  Cancel and Automatic outline; `font_image` draws on FIELD with default text colour TEXT; colour buttons flat with a
  LINE highlight border.
- [ ] **Step 3: Run** `python tests/ui_drive.py D:\ClaudeData\tmp\r4s_appdata D:\ClaudeData\tmp\r4s_shots\t4 talbot_sunbeam_lotus_81_works_backup_v6`.
  Expected: `PROBLEMS: none`; also add to ui_drive a shot of each of the six tabs (`tab_<n>.png`) and check them by eye
  against mockup E (left panel) – every control present, no light-grey leftovers.
- [ ] **Step 4: Commit** `Skin generator: controls in the game look`.

### Task 5: rattys4skin.py – garage preview and ghost

**Files:**
- Modify: `rattys4skin.py` (`__init__`, `refresh_skins`, `work`, `compose`, `show_views`, `redraw`, `draw_boxes`, `open_full`), `tests/ui_drive.py`
- Create: `tests/test_ghost_cache.py`

**Interfaces:**
- Consumes: Task 1 (`ghost_view`, RGBA views), Task 2 (`preview_background`, `compose_preview`, `cutout`, `text_image`).
- Produces: `ghost_cache_path(car_dir: str) -> str` (`DATA_DIR/ghosts/<car>.png`); `ghost_cache_valid(cache: str, kn5: str) -> bool`
  (exists and mtime ≥ kn5 mtime); `App.request_ghost(car_dir: str)`; `App._set_ghost(token: int, img, car: str)`;
  attributes `self.ghost` (grey RGBA or None), `self.ghost_car` (folder name), `self.saved` (bool).

- [ ] **Step 1: Write `tests/test_ghost_cache.py`**: `test_ghost_cache_valid` (temp files: cache newer → True, kn5
  touched newer → False, missing → False); `test_stale_ghost_ignored` (hidden App-free stub: call `App._set_ghost` on an
  object with `ghost_token=2` and token 1 → `ghost` unchanged; token 2 → set).
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement**: `refresh_skins` ends with `self.request_ghost(car)`; `request_ghost` bumps `self.ghost_token`,
  loads a valid cache at once, else a daemon thread runs `skingen.ghost_view(skingen.Car(car, log=lambda *a: None))`,
  saves the cache, and hands the image back with `self.after(0, self._set_ghost, token, img, car)`; any exception →
  `ghost=None`, nothing logged. `work`: `views['all'] = self.compose(views)` (RGB: every view `.convert('RGB')` first,
  so `generator_preview.png` stays identical) and `views['all_rgba'] = self.compose(views, rgba=True)`; `show_views`
  takes `saved`. `redraw`: background cached per `(W, H, id(ghost))`; car = `theme.cutout(view)` (or `all_rgba`);
  titles `ALL SIDES / LEFT SIDE / RIGHT SIDE / FRONT / REAR / TOP`; pill `PREVIEW ONLY · NOT SAVED` while views exist and
  not saved; prompt `('PRESS PREVIEW', 'to see your livery on the car')`, or `('PICK A CAR', 'on the Car tab')` with no
  car; `self.geom` from `compose_preview`. `draw_boxes`: others dashed ACC width 1, selected solid ACC width 3 with
  4 px corner squares, plus the selected decal's label as a `text_image` (size 12, ACC) at (18, 46), tag `box`.
  `open_full` saves the RGB view as before.
- [ ] **Step 4: Run tests, expect PASS.** Extend ui_drive: after each `pick_car`, wait ≤ 60 s for
  `app.ghost_car == car`, record the time, assert the cache file exists; pick the first car again and assert the ghost
  is back in < 1 s; shot `before_preview.png` once; shoot `<car>_left.png` with the Left chip after the preview.
- [ ] **Step 5: Run** ui_drive on the Talbot; check by eye against mockups E and F.
- [ ] **Step 6: Commit** `Skin generator: garage preview with the car's own ghost`.

### Task 6: Full checks

**Files:**
- Create: `tests/ui_dialogs.py` (opens each themed dialog, Edit text and the lens chart, shoots each, closes it)

- [ ] **Step 1:** `python tests/same_output.py D:\ClaudeData\tmp\r4s_same\v180.json` → identical to `v172_a.json`.
- [ ] **Step 2:** ui_drive on all four test cars → `PROBLEMS: none`, no `ERROR`/`Traceback` in any `<car>_log.txt`,
  every ghost made, previews shown.
- [ ] **Step 3:** `python tests/ui_dialogs.py …` → one picture per dialog, all dark, buttons work.
- [ ] **Step 4:** Fix anything found (back to the owning task's tests), rerun Steps 1-3.
- [ ] **Step 5:** Send Nik one picture per tab (six) plus the preview before / after, with `SendUserFile`.

### Task 7: Release 1.8.0

**Files:**
- Modify: `rattys4skin.py:11` (`VERSION = '1.8.0'`), `README.md` (look + preview area paragraph, version), `TODO.md`
  (done line), `docs/2026-11-12-game-look-ui-design.md` §5 (smoke test runs the built exe from `dist/` with the APPDATA
  copy; Nik installs)

- [ ] **Step 1:** Update the files above.
- [ ] **Step 2:** Build: `TEMP/TMP=D:\ClaudeData\tmp`, `PYINSTALLER_CONFIG_DIR=D:\ClaudeData\pyinstaller`, `python build.py`.
  Expected: `release/Rattys4SkinGenerator_Setup.exe` and `release/Rattys4SkinGenerator_v1.8.0.zip` exist.
- [ ] **Step 3:** Smoke test: start `dist/Rattys4SkinGenerator/Rattys4SkinGenerator.exe` with the APPDATA copy, wait for
  the window, screenshot, close. Expected: game look, ghost of the saved car, no error dialog.
- [ ] **Step 4:** Commit and push `Skin generator 1.8.0: game look (carbon + orange, garage preview with the car's ghost)`;
  send Nik the zip path and the smoke-test picture.

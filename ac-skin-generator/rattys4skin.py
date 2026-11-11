"""Ratty's4Skin Generator - window app.
No AI: the livery is projected onto the car from its own 3D model."""
import copy, glob, json, math, os, re, shutil, sys, tempfile, threading, traceback
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
from PIL import Image, ImageFont, ImageTk

import skingen

APP_NAME = skingen.APP_NAME
VERSION = '1.7.1'
DATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'Rattys4SkinGenerator')
LOGO_DIR = os.path.join(DATA_DIR, 'logos')
SETTINGS = os.path.join(DATA_DIR, 'settings.json')
LIBRARY = os.path.join(DATA_DIR, 'logos.json')
PLACE_NAMES = {'': 'Not used'}; PLACE_NAMES.update(skingen.PLACES)
BG_MODES = {'auto': 'Auto', 'remove': 'Remove background', 'keep': 'Keep whole picture'}
TEXT_PLACES = ['front_wings', 'lower_doors', 'doors', 'rear_quarters', 'bonnet', 'roof', 'boot', 'rear', 'front']
TEAM_DEFAULT = ['front_wings', 'boot', 'rear', 'front']
NAME_DEFAULT = ['front_wings']
NUMBER_STYLES = {'board': 'Number board', 'plain': 'Plain number', 'none': 'No number'}


DEFAULT_FONT_NAME = 'Default (Bahnschrift condensed)'
_FONTS = None


def list_fonts():
    """Fonts installed on this PC: {name shown: file}. Read once."""
    global _FONTS
    if _FONTS is None:
        found = {}
        dirs = [skingen.FONT_DIR, os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Fonts')]
        for d in dirs:
            for f in glob.glob(os.path.join(d, '*.[tToO][tT][fF]')):
                try: fam, sty = ImageFont.truetype(f, 20).getname()
                except Exception: continue
                found.setdefault(fam if sty in ('Regular', '') else f'{fam} {sty}', f)
        _FONTS = dict(sorted(found.items(), key=lambda kv: kv[0].lower()))
    return _FONTS


def work_dir(car_dir=None):
    """A scratch folder on the same drive as the game (never on C: unless the game is there):
    assettocorsa/_r4skin_work. R4S_WORK overrides it."""
    d = os.environ.get('R4S_WORK')
    if not d:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.normpath(car_dir)))) if car_dir else DATA_DIR
        d = os.path.join(base, '_r4skin_work')
    os.makedirs(d, exist_ok=True)
    return d


def resource(name):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def find_ac_cars():
    """Find assettocorsa/content/cars through Steam's registry entry and library folders."""
    roots = []
    try:
        import winreg
        for hive, key in ((winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam'),
                          (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam')):
            try:
                with winreg.OpenKey(hive, key) as k:
                    for v in ('SteamPath', 'InstallPath'):
                        try: roots.append(winreg.QueryValueEx(k, v)[0])
                        except OSError: pass
            except OSError: pass
    except ImportError: pass
    roots += [r'C:\Program Files (x86)\Steam', r'C:\Program Files\Steam']
    libs = []
    for r in roots:
        libs.append(r)
        vdf = os.path.join(r, 'steamapps', 'libraryfolders.vdf')
        try:
            libs += [p.replace('\\\\', '\\') for p in re.findall(r'"path"\s+"([^"]+)"', open(vdf, encoding='utf8', errors='ignore').read())]
        except OSError: pass
    for d in 'CDEFGHIJ':
        libs += [f'{d}:\\SteamLibrary', f'{d}:\\Steam', f'{d}:\\Games\\Steam']
    for lib in libs:
        p = os.path.join(lib, 'steamapps', 'common', 'assettocorsa', 'content', 'cars')
        if os.path.isdir(p): return os.path.normpath(p)
    return ''


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        os.makedirs(LOGO_DIR, exist_ok=True)
        self.title(f"{APP_NAME}  v{VERSION}")
        self.geometry('1320x840')
        self.minsize(1000, 640)
        try: self.iconbitmap(resource('app.ico'))
        except Exception: pass
        self.cfg = self.load_cfg()
        self.vars = {}
        self.library = self.load_library()
        self.add_starter_logos()
        self.thumbs = {}
        self.preview_img = None
        self.busy = False
        self.info = {}                                   # where the last preview put every decal
        self.adjust_by_car = self.cfg.get('adjust_by_car') or {}     # hand adjustments, per car
        self.adjust_gen = {}                             # the adjustments the last preview was made with
        self.sel = None                                  # decal picked on the preview
        self.geom = None
        self.build()
        self.refresh_cars()
        self.refresh_library()
        self.protocol('WM_DELETE_WINDOW', self.on_close)

    # ---------------------------------------------------------------- settings / library
    def load_cfg(self):
        d = dict(skingen.DEFAULT_DESIGN)
        d.update(cars_dir='', car='', skin_name='My Skin', copy_from='', use_wheels=False, wheel_colour='#7020d2', use_tyres=False, tyre_colour='#ff8000',
                 use_lens=False, lens_colour='#ffd21f', use_tint=False, win_tint_colour='#14181c', win_tint_pct='50', compress=True)
        try: d.update(json.load(open(SETTINGS, encoding='utf8')))
        except Exception: pass
        if not d.get('cars_dir') or not os.path.isdir(d['cars_dir']): d['cars_dir'] = find_ac_cars()
        return d

    def save_cfg(self):
        d = {k: v.get() for k, v in self.vars.items()}
        d['pattern'] = next((k for k, v in skingen.PATTERNS.items() if v == self.vars['pattern_name'].get()), 'sweep')
        d['number_style'] = next((k for k, v in NUMBER_STYLES.items() if v == self.vars['number_style_name'].get()), 'board')
        d['team_places'] = [p for p, v in self.tp_vars.items() if v.get()]
        d['name_places'] = [p for p, v in self.np_vars.items() if v.get()]
        d['pattern_mode'] = next((k for k, v in skingen.PICTURE_MODES.items() if v == self.vars['pattern_mode_name'].get()), 'side_left')
        d['pattern_simplify'] = next((k for k, v in skingen.SIMPLIFY.items() if v == self.vars['pattern_simplify_name'].get()), 'medium')
        d['win_side_place'] = next((k for k, v in skingen.SIDE_PLACES.items() if v == self.vars['win_side_name'].get()), 'rear')
        d['adjust_by_car'] = self.adjust_by_car
        try:
            with open(SETTINGS, 'w', encoding='utf8') as f: json.dump(d, f, indent=2)
        except Exception: pass

    def load_library(self):
        try: lib = json.load(open(LIBRARY, encoding='utf8'))
        except Exception: lib = []
        return [l for l in lib if os.path.isfile(os.path.join(LOGO_DIR, l.get('file', '')))]

    def add_starter_logos(self):
        """The logos that come with the app go into the library once. Ones the user deletes stay deleted."""
        src = resource('starter_logos')
        try: starters = json.load(open(os.path.join(src, 'starter.json'), encoding='utf8'))
        except Exception: return
        done_file = os.path.join(DATA_DIR, 'starter_logos_added.json')
        try: done = set(json.load(open(done_file, encoding='utf8')))
        except Exception: done = set()
        have = {l.get('file') for l in self.library}
        added = 0
        for st in starters:
            f = st.get('file')
            if not f or f in done or not os.path.isfile(os.path.join(src, f)): continue
            done.add(f)
            if f in have: continue
            try: shutil.copyfile(os.path.join(src, f), os.path.join(LOGO_DIR, f))
            except OSError: continue
            self.library.append(dict(file=f, name=st.get('name') or os.path.splitext(f)[0], place='', tint=False))
            added += 1
        if added: self.save_library()
        try:
            with open(done_file, 'w', encoding='utf8') as fh: json.dump(sorted(done), fh)
        except OSError: pass

    def save_library(self):
        with open(LIBRARY, 'w', encoding='utf8') as f:
            json.dump(self.library, f, indent=2)

    def var(self, key, kind=tk.StringVar):
        v = kind(value=self.cfg.get(key, False if kind is tk.BooleanVar else ''))
        self.vars[key] = v
        return v

    # ---------------------------------------------------------------- layout
    def build(self):
        style = ttk.Style(self)
        try: style.theme_use('vista')
        except tk.TclError: pass
        left = ttk.Frame(self, padding=8); left.pack(side='left', fill='y')
        right = ttk.Frame(self, padding=8); right.pack(side='left', fill='both', expand=True)

        nb = ttk.Notebook(left); nb.pack(fill='x')
        tabs = {}
        for key, title in (('car', 'Car'), ('livery', 'Livery'), ('number', 'Number & names'),
                           ('logos', 'Logos'), ('windows', 'Windows'), ('lights', 'Lights & wheels')):
            f = ttk.Frame(nb, padding=10); nb.add(f, text=title); tabs[key] = f

        def row(tab, label, widget_fn):
            f = ttk.Frame(tabs[tab]); f.pack(fill='x', pady=3)
            ttk.Label(f, text=label, width=18).pack(side='left')
            w = widget_fn(f); w.pack(side='left', fill='x', expand=True)
            return w

        def note(tab, text):
            ttk.Label(tabs[tab], text=text, foreground='#666', wraplength=380, justify='left').pack(fill='x', pady=(2, 6))

        # --- car
        def cars_dir(f):
            fr = ttk.Frame(f)
            ttk.Entry(fr, textvariable=self.var('cars_dir'), width=34).pack(side='left', fill='x', expand=True)
            ttk.Button(fr, text='…', width=3, command=self.pick_cars_dir).pack(side='left')
            return fr
        row('car', 'AC cars folder', cars_dir)
        note('car', 'Normally found automatically: …\\steamapps\\common\\assettocorsa\\content\\cars')
        self.car_box = row('car', 'Car (type to search)', lambda f: ttk.Combobox(f, textvariable=self.var('car'), width=36))
        self.car_box.bind('<<ComboboxSelected>>', lambda e: self.refresh_skins())
        self.car_box.bind('<KeyRelease>', self.filter_cars)
        row('car', 'Skin name', lambda f: ttk.Entry(f, textvariable=self.var('skin_name')))
        self.copy_box = row('car', 'Windows etc. from', lambda f: ttk.Combobox(f, textvariable=self.var('copy_from'), width=36))
        note('car', 'Optional: copies the other files (windows, interior…) from one of the car\'s skins.')
        row('car', '', lambda f: ttk.Checkbutton(f, text='Sharper textures (4K) - crisper writing and logos, bigger files',
                                                 variable=self.var('hires', tk.BooleanVar)))
        row('car', '', lambda f: ttk.Checkbutton(f, text='Smaller files (compressed textures, about a quarter of the size)',
                                                 variable=self.var('compress', tk.BooleanVar)))

        # --- livery
        for key, label in (('base', 'Base colour'), ('accent', 'Accent colour'), ('accent2', 'Highlight colour'),
                           ('text', 'Text colour')):
            row('livery', label, lambda f, k=key: self.colour_button(f, k))
        self.vars['pattern_name'] = tk.StringVar(value=skingen.PATTERNS.get(self.cfg.get('pattern'), skingen.PATTERNS['sweep']))
        row('livery', 'Pattern', lambda f: ttk.Combobox(f, textvariable=self.vars['pattern_name'], state='readonly',
                                                       values=list(skingen.PATTERNS.values()), width=32, height=16))
        self.swatch = ttk.Label(tabs['livery'])            # what the pattern looks like: side over top, front on the left
        self.swatch.pack(anchor='w', padx=(130, 0), pady=(2, 4))
        self.swatch_img = None
        note('livery', 'Patterns are inspired by classic and modern racing liveries; they use your accent, '
                       'highlight and text colours. The picture above shows the car\'s side over its top, front on the left.')
        ttk.Label(tabs['livery'], text='Pattern from a picture', font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(8, 0))
        def pic(f):
            fr = ttk.Frame(f)
            ttk.Entry(fr, textvariable=self.var('pattern_image'), width=30).pack(side='left', fill='x', expand=True)
            ttk.Button(fr, text='…', width=3, command=self.pick_pattern_image).pack(side='left')
            return fr
        row('livery', 'Picture', pic)
        self.vars['pattern_mode_name'] = tk.StringVar(value=skingen.PICTURE_MODES.get(self.cfg.get('pattern_mode'), skingen.PICTURE_MODES['side_left']))
        row('livery', 'The picture is', lambda f: ttk.Combobox(f, textvariable=self.vars['pattern_mode_name'], state='readonly',
                                                              values=list(skingen.PICTURE_MODES.values()), width=34))
        self.vars['pattern_simplify_name'] = tk.StringVar(value=skingen.SIMPLIFY.get(self.cfg.get('pattern_simplify'), skingen.SIMPLIFY['medium']))
        row('livery', 'Simplify', lambda f: ttk.Combobox(f, textvariable=self.vars['pattern_simplify_name'], state='readonly',
                                                        values=list(skingen.SIMPLIFY.values()), width=24))
        row('livery', '', lambda f: ttk.Checkbutton(f, text="Use my colours instead of the picture's",
                                                   variable=self.var('pattern_recolour', tk.BooleanVar)))
        note('livery', 'Choose "Pattern from a picture…" above, then a picture: a side view of a car (plain background '
                       'works best) or a flat pattern. Simplify melts writing and small stickers away. Your number, '
                       'names and logos are added on top as usual.')
        row('livery', '', lambda f: ttk.Checkbutton(f, text='Halftone dots', variable=self.var('halftone', tk.BooleanVar)))

        # --- number & names
        row('number', 'Racing number', lambda f: ttk.Entry(f, textvariable=self.var('number'), width=8))
        self.vars['number_style_name'] = tk.StringVar(value=NUMBER_STYLES.get(self.cfg.get('number_style'), 'Number board'))
        row('number', 'Number style', lambda f: ttk.Combobox(f, textvariable=self.vars['number_style_name'],
                                                            values=list(NUMBER_STYLES.values()), state='readonly', width=16))
        row('number', 'Show number on', lambda f: self.checks(f, (('number_doors', 'Doors'), ('number_roof', 'Roof'))))
        row('number', 'Team / wordmark', lambda f: ttk.Entry(f, textvariable=self.var('team')))
        row('number', 'Driver name', lambda f: ttk.Entry(f, textvariable=self.var('name')))
        fonts = [DEFAULT_FONT_NAME] + list(list_fonts())
        self.font_prev = {}
        for key, label, src in (('font_team_name', 'Team font', 'team'), ('font_name_name', 'Driver font', 'name'),
                                ('font_number_name', 'Number font', 'number')):
            self.vars[key] = tk.StringVar(value=self.cfg.get(key) if self.cfg.get(key) in fonts else DEFAULT_FONT_NAME)
            row('number', label, lambda f, key=key: ttk.Combobox(f, textvariable=self.vars[key], values=fonts, state='readonly', width=30))
            lab = ttk.Label(tabs['number']); lab.pack(anchor='w', padx=(130, 0))
            self.font_prev[key] = (lab, src, None)
            upd = (lambda *_, key=key: self.after_idle(lambda: self.update_font_preview(key)))
            self.vars[key].trace_add('write', upd)
            if src in self.vars: self.vars[src].trace_add('write', upd)
            self.after(250, upd)
        ttk.Label(tabs['number'], text='Where to write them:').pack(anchor='w', pady=(8, 2))
        grid = ttk.Frame(tabs['number']); grid.pack(fill='x')
        ttk.Label(grid, text='').grid(row=0, column=0)
        ttk.Label(grid, text='Team').grid(row=0, column=1, padx=6)
        ttk.Label(grid, text='Driver').grid(row=0, column=2, padx=6)
        tp = self.cfg.get('team_places') or TEAM_DEFAULT
        np_ = self.cfg.get('name_places') or NAME_DEFAULT
        self.tp_vars, self.np_vars = {}, {}
        for r, pl in enumerate(TEXT_PLACES, 1):
            ttk.Label(grid, text=skingen.PLACES[pl]).grid(row=r, column=0, sticky='w')
            self.tp_vars[pl] = tk.BooleanVar(value=pl in tp); self.np_vars[pl] = tk.BooleanVar(value=pl in np_)
            ttk.Checkbutton(grid, variable=self.tp_vars[pl]).grid(row=r, column=1)
            ttk.Checkbutton(grid, variable=self.np_vars[pl]).grid(row=r, column=2)
        note('number', 'Where both are ticked, the driver name goes under the team name. Where a logo is at the '
                       'same spot, the logo is made a little smaller and the writing goes under it.')

        # --- logos
        lt = tabs['logos']
        note('logos', 'Add your logos and pictures here; they stay in the library for next time. '
                      'Pick each one\'s place on the car. PNGs with transparency work best; a plain background is removed.')
        cols = ('place', 'bg', 'tint')
        self.tree = ttk.Treeview(lt, columns=cols, height=7, selectmode='browse')
        self.tree.heading('#0', text='Logo'); self.tree.heading('place', text='Place on car'); self.tree.heading('tint', text='Tint'); self.tree.heading('bg', text='Background')
        self.tree.column('#0', width=180); self.tree.column('place', width=120); self.tree.column('bg', width=95); self.tree.column('tint', width=50, anchor='center')
        ttk.Style(self).configure('Treeview', rowheight=44)
        self.tree.pack(fill='x')
        self.tree.bind('<<TreeviewSelect>>', self.on_logo_select)
        bf = ttk.Frame(lt); bf.pack(fill='x', pady=4)
        ttk.Button(bf, text='Add logos…', command=self.add_logos).pack(side='left')
        ttk.Button(bf, text='Remove', command=self.remove_logo).pack(side='left', padx=4)
        pf = ttk.Frame(lt); pf.pack(fill='x', pady=2)
        ttk.Label(pf, text='Place on car', width=18).pack(side='left')
        self.place_var = tk.StringVar(value='Not used')
        self.place_box = ttk.Combobox(pf, textvariable=self.place_var, values=list(PLACE_NAMES.values()), state='readonly', width=20)
        self.place_box.pack(side='left'); self.place_box.bind('<<ComboboxSelected>>', self.on_place)
        bgf = ttk.Frame(lt); bgf.pack(fill='x', pady=2)
        ttk.Label(bgf, text='Background', width=18).pack(side='left')
        self.bg_var = tk.StringVar(value='Auto')
        bgb = ttk.Combobox(bgf, textvariable=self.bg_var, values=list(BG_MODES.values()), state='readonly', width=20)
        bgb.pack(side='left'); bgb.bind('<<ComboboxSelected>>', self.on_place)
        note('logos', 'Auto removes a plain one-colour background and keeps pictures with busy backgrounds whole.')
        self.tint_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(pf, text='Tint glow to highlight colour', variable=self.tint_var, command=self.on_place).pack(side='left', padx=6)

        # --- windows
        row('windows', '', lambda f: ttk.Checkbutton(f, text='Make new window stickers', variable=self.var('win_enable', tk.BooleanVar)))
        row('windows', '', lambda f: ttk.Checkbutton(f, text='Remove the stickers already on the windows',
                                                     variable=self.var('win_clear', tk.BooleanVar)))
        row('windows', 'Banner text', lambda f: ttk.Entry(f, textvariable=self.var('win_banner')))
        row('windows', 'Banner colour', lambda f: self.colour_button(f, 'win_banner_colour'))
        self.vars['win_banner_cm'] = tk.StringVar(value=str(self.cfg.get('win_banner_cm') or 12))
        row('windows', 'Banner height (cm)', lambda f: ttk.Spinbox(f, from_=8, to=25, width=5, textvariable=self.vars['win_banner_cm']))
        row('windows', 'Sticker text colour', lambda f: self.colour_button(f, 'win_text_colour'))
        row('windows', 'Also show', lambda f: self.checks(f, (('win_number', 'Racing number'), ('win_name', 'Driver name'))))
        self.vars['win_side_name'] = tk.StringVar(value=skingen.SIDE_PLACES.get(self.cfg.get('win_side_place'), skingen.SIDE_PLACES['rear']))
        row('windows', 'Side stickers on', lambda f: ttk.Combobox(f, textvariable=self.vars['win_side_name'], state='readonly',
                                                                 values=list(skingen.SIDE_PLACES.values()), width=22))
        note('windows', 'The banner follows the top edge of the windscreen and rear window, full width, at the height '
                        'you choose (8-25 cm). Number and driver name go on the rear window and the side windows '
                        'chosen here. Logos can go on the windscreen, rear window or side windows (Logos tab). '
                        'Number and name come from the "Number & names" tab.')
        ttk.Separator(tabs['windows']).pack(fill='x', pady=6)
        row('windows', '', lambda f: ttk.Checkbutton(f, text='Tint the windows', variable=self.var('use_tint', tk.BooleanVar)))
        row('windows', 'Tint colour', lambda f: self.colour_button(f, 'win_tint_colour'))
        self.vars['win_tint_pct'] = tk.StringVar(value=str(self.cfg.get('win_tint_pct') or 50))
        row('windows', 'How dark (%)', lambda f: ttk.Spinbox(f, from_=5, to=90, increment=5, width=5, textvariable=self.vars['win_tint_pct']))
        row('windows', '', lambda f: ttk.Checkbutton(f, text='Tint the windscreen too', variable=self.var('win_tint_windscreen', tk.BooleanVar)))
        note('windows', 'Side and rear glass get the tint; the windscreen stays clear unless ticked. '
                        'Stickers sit on top of the tint and keep their colours.')

        # --- lights & wheels
        row('lights', '', lambda f: ttk.Checkbutton(f, text='Colour the headlight lenses', variable=self.var('use_lens', tk.BooleanVar)))
        row('lights', 'Lens colour', lambda f: self.colour_button(f, 'lens_colour'))
        note('lights', 'Tints the front lamp textures, so the lens and its glow take this colour.')
        ttk.Separator(tabs['lights']).pack(fill='x', pady=6)
        row('lights', '', lambda f: ttk.Checkbutton(f, text='Recolour the wheel rims', variable=self.var('use_wheels', tk.BooleanVar)))
        row('lights', 'Rim colour', lambda f: self.colour_button(f, 'wheel_colour'))
        row('lights', '', lambda f: ttk.Checkbutton(f, text='Recolour the tyres', variable=self.var('use_tyres', tk.BooleanVar)))
        row('lights', 'Tyre colour', lambda f: self.colour_button(f, 'tyre_colour'))
        note('lights', 'Rims and tyres are separate. Only cars with their own rim / tyre textures can change.')

        # --- buttons + log
        bf = ttk.Frame(left); bf.pack(fill='x', pady=(10, 0))
        self.btn_prev = ttk.Button(bf, text='Preview', command=lambda: self.run(save=False))
        self.btn_prev.pack(side='left', expand=True, fill='x', padx=2, ipady=4)
        self.btn_save = ttk.Button(bf, text='Create skin in car', command=lambda: self.run(save=True))
        self.btn_save.pack(side='left', expand=True, fill='x', padx=2, ipady=4)
        self.prog = ttk.Progressbar(left, mode='determinate', maximum=100)
        self.prog.pack(fill='x', pady=(8, 0))
        self.status = ttk.Label(left, text='Ready', foreground='#444')
        self.status.pack(anchor='w')
        self.log_box = tk.Text(left, height=10, width=60, font=('Consolas', 8))
        self.log_box.pack(fill='both', expand=True, pady=(6, 0))

        vb = ttk.Frame(right); vb.pack(fill='x', pady=(0, 6))
        ttk.Label(vb, text='View:').pack(side='left')
        self.view_var = tk.StringVar(value='all')
        for key, label in (('all', 'All sides'), ('left', 'Left'), ('right', 'Right'), ('front', 'Front'),
                           ('rear', 'Rear'), ('top', 'Top')):
            ttk.Radiobutton(vb, text=label, value=key, variable=self.view_var, command=self.on_view).pack(side='left', padx=4)
        ttk.Button(vb, text='Open full size', command=self.open_full).pack(side='right')
        # edit bar: move / size / turn / flip the logos, number and names on the preview
        eb = ttk.Frame(right); eb.pack(fill='x', pady=(0, 2))
        ttk.Label(eb, text='Edit on the preview:').pack(side='left')
        for text, cmd in (('Bigger', lambda: self.edit('scale', 1.08)), ('Smaller', lambda: self.edit('scale', 1 / 1.08)),
                          ('Turn ↺', lambda: self.edit('rot', 5)), ('Turn ↻', lambda: self.edit('rot', -5)),
                          ('Flip', lambda: self.edit('flip')), ('Edit text…', self.edit_text), ('Delete', lambda: self.edit('delete')),
                          ('Reset', lambda: self.edit('reset')),
                          ('Reset all', lambda: self.edit('reset_all'))):
            ttk.Button(eb, text=text, command=cmd, width=len(text) + 1).pack(side='left', padx=1)
        self.sel_label = ttk.Label(right, text='Pick one side (Left, Right, Front, Rear or Top), then click a logo, number or name to move it.',
                                   foreground='#444')
        self.sel_label.pack(anchor='w', pady=(0, 4))
        self.canvas = tk.Canvas(right, background='#ebecf0', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', lambda e: self.after_idle(self.redraw))
        self.canvas.bind('<Button-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<MouseWheel>', self.on_wheel)
        self.views = {}
        for key in ('pattern_name', 'base', 'accent', 'accent2', 'text', 'pattern_image', 'pattern_mode_name',
                    'pattern_simplify_name', 'halftone', 'carbon'):
            if key in self.vars: self.vars[key].trace_add('write', lambda *_: self.after_idle(self.update_swatch))
        self.after(200, self.update_swatch)

    def update_swatch(self):
        try:
            d = self.design()
            im = skingen.pattern_swatch(d, 300)
        except Exception:
            return
        self.swatch_img = ImageTk.PhotoImage(im)
        self.swatch.configure(image=self.swatch_img)

    def font_image(self, font_path, text, colour='#111111', width=300, height=40):
        """The words in that font, on a light background (for the font previews)."""
        im = Image.new('RGB', (width, height), (245, 245, 247))
        if text:
            try:
                t = skingen.text_image(text, 120, skingen.rgb(colour), font_path or skingen.DEFAULT_FONT)
                t.thumbnail((width - 10, height - 8), Image.LANCZOS)
                im.paste(t, (6, (height - t.height) // 2), t)
            except Exception: pass
        return ImageTk.PhotoImage(im)

    def update_font_preview(self, key):
        lab, src, _ = self.font_prev[key]
        text = (self.vars[src].get() if src in self.vars else '') or {'team': 'RATTY RACING', 'name': 'Driver Name', 'number': '101'}[src]
        img = self.font_image(list_fonts().get(self.vars[key].get()), text)
        self.font_prev[key] = (lab, src, img)
        lab.configure(image=img)

    def edit_text(self):
        """Change the words, font and colour of the team / driver name box picked on the preview (both sides)."""
        d = next((d for d in self.view_decals() if d['key'] == self.sel), None)
        if d is None or not (d['key'].startswith('team name') or d['key'].startswith('driver name')):
            self.sel_label.configure(text='Pick a team or driver name on the preview first (one side showing).', foreground='#b00020')
            return
        ad = self.adj(d['key'])
        is_team = d['key'].startswith('team name')
        win = tk.Toplevel(self); win.title('Edit text - ' + d['label'].split(' (')[0]); win.transient(self); win.grab_set()
        f = ttk.Frame(win, padding=12); f.pack(fill='both', expand=True)
        fonts = [DEFAULT_FONT_NAME] + list(list_fonts())
        text_v = tk.StringVar(value=ad.get('text') or self.vars['team' if is_team else 'name'].get())
        cur_font = next((n for n, pth in list_fonts().items() if pth == ad.get('font')), None)
        font_v = tk.StringVar(value=cur_font or self.vars['font_team_name' if is_team else 'font_name_name'].get())
        col_v = tk.StringVar(value=ad.get('colour') or '')
        ttk.Label(f, text='Words').grid(row=0, column=0, sticky='w')
        ttk.Entry(f, textvariable=text_v, width=34).grid(row=0, column=1, sticky='we', pady=3)
        ttk.Label(f, text='Font').grid(row=1, column=0, sticky='w')
        ttk.Combobox(f, textvariable=font_v, values=fonts, state='readonly', width=32).grid(row=1, column=1, sticky='we', pady=3)
        ttk.Label(f, text='Colour').grid(row=2, column=0, sticky='w')
        cf = ttk.Frame(f); cf.grid(row=2, column=1, sticky='w', pady=3)
        cb = tk.Button(cf, width=12, relief='groove')
        cb.pack(side='left')
        ttk.Button(cf, text='Automatic', command=lambda: col_v.set('')).pack(side='left', padx=4)
        prev = ttk.Label(f); prev.grid(row=3, column=0, columnspan=2, pady=(8, 4))
        keep = {}

        def refresh(*_):
            c = col_v.get()
            cb.configure(text=c or 'automatic', bg=c or '#f0f0f0', activebackground=c or '#f0f0f0')
            keep['img'] = self.font_image(list_fonts().get(font_v.get()), text_v.get(), c or '#111111', 360, 48)
            prev.configure(image=keep['img'])

        def pick():
            c = colorchooser.askcolor(col_v.get() or None, parent=win)[1]
            if c: col_v.set(c)
        cb.configure(command=pick)
        for v in (text_v, font_v, col_v): v.trace_add('write', refresh)
        refresh()

        def ok():
            ad['text'] = text_v.get().strip()
            fp = list_fonts().get(font_v.get())
            if fp: ad['font'] = fp
            else: ad.pop('font', None)
            if col_v.get(): ad['colour'] = col_v.get()
            else: ad.pop('colour', None)
            if not ad['text']: ad.pop('text')
            win.destroy(); self.draw_boxes(); self.save_cfg()
        bf = ttk.Frame(f); bf.grid(row=4, column=0, columnspan=2, pady=(6, 0))
        ttk.Button(bf, text='OK', command=ok).pack(side='left', padx=4)
        ttk.Button(bf, text='Cancel', command=win.destroy).pack(side='left', padx=4)
        ttk.Label(f, text='Changes this box on both sides of the car. Press Preview to see it on the car.',
                  foreground='#666').grid(row=5, column=0, columnspan=2, pady=(6, 0))

    def checks(self, parent, items):
        fr = ttk.Frame(parent)
        for key, label in items:
            ttk.Checkbutton(fr, text=label, variable=self.var(key, tk.BooleanVar)).pack(side='left', padx=(0, 10))
        return fr

    def colour_button(self, parent, key):
        v = self.var(key)
        b = tk.Button(parent, width=12, relief='groove')
        def paint(*_):
            c = v.get() or '#000000'
            try:
                r, g, bb = self.winfo_rgb(c); lum = (r * .3 + g * .59 + bb * .11) / 65535
                b.configure(bg=c, activebackground=c, text=c, fg='black' if lum > 0.5 else 'white')
            except tk.TclError: pass
        def pick():
            c = colorchooser.askcolor(v.get(), parent=self)[1]
            if c: v.set(c)
        b.configure(command=pick); v.trace_add('write', paint); paint()
        return b

    # ---------------------------------------------------------------- car pickers
    def pick_cars_dir(self):
        d = filedialog.askdirectory(initialdir=self.vars['cars_dir'].get() or None, title='Assetto Corsa content\\cars folder')
        if d: self.vars['cars_dir'].set(os.path.normpath(d)); self.refresh_cars()

    def pick_pattern_image(self):
        f = filedialog.askopenfilename(title='Picture to make the pattern from',
                                       filetypes=[('Images', '*.png *.jpg *.jpeg *.webp *.bmp'), ('All files', '*.*')])
        if f:
            self.vars['pattern_image'].set(f)
            self.vars['pattern_name'].set(skingen.PATTERNS['picture'])

    def refresh_cars(self):
        d = self.vars['cars_dir'].get()
        try: self.all_cars = sorted(c for c in os.listdir(d) if os.path.isdir(os.path.join(d, c, 'skins')))
        except OSError: self.all_cars = []
        self.car_box['values'] = self.all_cars
        self.refresh_skins()

    def filter_cars(self, e):
        t = self.vars['car'].get().lower()
        self.car_box['values'] = [c for c in self.all_cars if t in c.lower()] or self.all_cars

    def refresh_skins(self):
        car = os.path.join(self.vars['cars_dir'].get(), self.vars['car'].get())
        self.copy_box['values'] = [''] + (skingen.stock_skins(car) if os.path.isdir(car) else [])

    # ---------------------------------------------------------------- logo library
    def refresh_library(self):
        self.tree.delete(*self.tree.get_children())
        for i, lg in enumerate(self.library):
            path = os.path.join(LOGO_DIR, lg['file'])
            if path not in self.thumbs:
                try:
                    im = Image.open(path).convert('RGBA'); im.thumbnail((40, 40))
                    bg = Image.new('RGBA', (40, 40), (60, 60, 66, 255)); bg.alpha_composite(im, ((40 - im.width) // 2, (40 - im.height) // 2))
                    self.thumbs[path] = ImageTk.PhotoImage(bg)
                except Exception: self.thumbs[path] = None
            kw = {'image': self.thumbs[path]} if self.thumbs[path] else {}
            self.tree.insert('', 'end', iid=str(i), text='  ' + lg.get('name', lg['file']),
                             values=(PLACE_NAMES.get(lg.get('place', ''), 'Not used'), BG_MODES.get(lg.get('bg', 'auto'), 'Auto'),
                                     'yes' if lg.get('tint') else ''), **kw)

    def add_logos(self):
        files = filedialog.askopenfilenames(title='Add logos or pictures',
                                            filetypes=[('Images', '*.png *.jpg *.jpeg *.webp *.bmp *.tga *.dds'), ('All files', '*.*')])
        for f in files:
            try: Image.open(f).verify()
            except Exception:
                messagebox.showerror(APP_NAME, f'Cannot read {os.path.basename(f)} as an image.'); continue
            base, ext = os.path.splitext(os.path.basename(f))
            name, n = base + ext, 1
            while os.path.exists(os.path.join(LOGO_DIR, name)):
                n += 1; name = f'{base}_{n}{ext}'
            shutil.copyfile(f, os.path.join(LOGO_DIR, name))
            self.library.append(dict(file=name, name=base, place='', tint=False))
        self.save_library(); self.refresh_library()

    def selected_logo(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def remove_logo(self):
        i = self.selected_logo()
        if i is None: return
        lg = self.library.pop(i)
        try: os.remove(os.path.join(LOGO_DIR, lg['file']))
        except OSError: pass
        self.save_library(); self.refresh_library()

    def on_logo_select(self, e=None):
        i = self.selected_logo()
        if i is None: return
        self.place_var.set(PLACE_NAMES.get(self.library[i].get('place', ''), 'Not used'))
        self.tint_var.set(bool(self.library[i].get('tint')))
        self.bg_var.set(BG_MODES.get(self.library[i].get('bg', 'auto'), 'Auto'))

    def on_place(self, e=None):
        i = self.selected_logo()
        if i is None: return
        key = next((k for k, v in PLACE_NAMES.items() if v == self.place_var.get()), '')
        self.library[i]['place'] = key; self.library[i]['tint'] = bool(self.tint_var.get())
        self.library[i]['bg'] = next((k for k, v in BG_MODES.items() if v == self.bg_var.get()), 'auto')
        self.save_library(); self.refresh_library(); self.tree.selection_set(str(i))

    # ---------------------------------------------------------------- run
    def log(self, msg):
        self.after(0, lambda: (self.log_box.insert('end', msg + '\n'), self.log_box.see('end')))

    def design(self):
        d = dict(skingen.DEFAULT_DESIGN)
        for k in d:
            if k in self.vars: d[k] = self.vars[k].get()
        d['logo'] = None
        d['logos'] = [dict(path=os.path.join(LOGO_DIR, l['file']), place=l['place'], tint=l.get('tint'), bg=l.get('bg', 'auto'))
                      for l in self.library if l.get('place')]
        d['number_style'] = next((k for k, v in NUMBER_STYLES.items() if v == self.vars['number_style_name'].get()), 'board')
        d['pattern'] = next((k for k, v in skingen.PATTERNS.items() if v == self.vars['pattern_name'].get()), 'sweep')
        d['pattern_mode'] = next((k for k, v in skingen.PICTURE_MODES.items() if v == self.vars['pattern_mode_name'].get()), 'side_left')
        d['pattern_simplify'] = next((k for k, v in skingen.SIMPLIFY.items() if v == self.vars['pattern_simplify_name'].get()), 'medium')
        d['pattern_image'] = self.vars['pattern_image'].get() or None
        try: d['win_banner_height'] = min(25.0, max(8.0, float(self.vars['win_banner_cm'].get()))) / 100
        except ValueError: d['win_banner_height'] = 0.12
        d['win_side_place'] = next((k for k, v in skingen.SIDE_PLACES.items() if v == self.vars['win_side_name'].get()), 'rear')
        d['team_places'] = [p for p, v in self.tp_vars.items() if v.get()] or ['none']
        d['name_places'] = [p for p, v in self.np_vars.items() if v.get()] or ['none']
        d['wheel_colour'] = self.vars['wheel_colour'].get() if self.vars['use_wheels'].get() else None
        d['tyre_colour'] = self.vars['tyre_colour'].get() if self.vars['use_tyres'].get() else None
        d['lens_colour'] = self.vars['lens_colour'].get() if self.vars['use_lens'].get() else None
        d['win_tint'] = self.vars['win_tint_colour'].get() if self.vars['use_tint'].get() else None
        try: d['win_tint_dark'] = min(90.0, max(5.0, float(self.vars['win_tint_pct'].get()))) / 100
        except ValueError: d['win_tint_dark'] = 0.5
        d['beam_colour'] = None              # cast-light colour option removed (Nik, 11 Nov): lens colour only
        for key in ('font_team', 'font_name', 'font_number'):
            d[key] = list_fonts().get(self.vars[key + '_name'].get())          # None = the default font
        d['adjust'] = copy.deepcopy(self.adjust_by_car.get(self.vars['car'].get(), {}))
        return d

    def run(self, save):
        if self.busy: return
        car = os.path.join(self.vars['cars_dir'].get(), self.vars['car'].get())
        if not self.vars['car'].get() or not os.path.isdir(car):
            messagebox.showerror(APP_NAME, 'Pick a car first (Car tab).'); return
        name = self.vars['skin_name'].get().strip() or 'My Skin'
        replace = None
        if save:
            sid = re.sub(r'[^a-z0-9_]+', '_', name.lower()).strip('_') or 'custom'
            target = os.path.join(car, 'skins', sid)
            if os.path.exists(target) and os.listdir(target):
                if not os.path.isfile(os.path.join(target, 'generator_preview.png')):
                    # not made by this app (stock or downloaded skin): never overwrite it
                    messagebox.showerror(APP_NAME, f'The car already has a skin folder "{sid}" that was not made by '
                                                   f'{APP_NAME}.\n\nIt will not be overwritten - choose another skin name.')
                    return
                if not messagebox.askyesno(APP_NAME, f'You already made a skin called "{sid}" for this car.\n\n'
                                                     'Replace it with the new one?\n(The old one is only removed once '
                                                     'the new one has been built.)', icon='warning'):
                    return
                replace = target
        self.save_cfg()
        self.busy = True
        for b in (self.btn_prev, self.btn_save): b.state(['disabled'])
        self.log_box.delete('1.0', 'end')
        self.set_progress(0, 'Starting…')
        opts = dict(design=self.design(), resolution=4096 if self.vars['hires'].get() else None,
                    copy_from=self.vars['copy_from'].get() or None)      # read here: tk variables belong to this thread
        threading.Thread(target=self.work, args=(car, name, save, replace, opts), daemon=True).start()

    def set_progress(self, frac, text):
        self.after(0, lambda: (self.prog.configure(value=frac * 100), self.status.configure(text=text)))

    def work(self, car, name, save, replace=None, opts=None):
        views, info = {}, {}
        design = opts['design']
        try:
            # a replacement is built next to the old skin first; the old one goes only when this succeeded
            build_root = os.path.join(car, 'skins', '_r4skin_building') if replace else None
            if replace: shutil.rmtree(build_root, ignore_errors=True)
            out, sheet, *_ = skingen.generate(car, design, name, out_root=build_root,
                                              resolution=opts['resolution'],
                                              log=self.log, copy_other_from=opts['copy_from'],
                                              progress=self.set_progress, views=views, info=info, write=save)
            info['adjust'] = design.get('adjust') or {}
            views['all'] = self.compose(views)
            if save:
                views['all'].save(os.path.join(out, 'generator_preview.png'))
            if replace:
                shutil.rmtree(replace)
                shutil.move(out, replace)
                shutil.rmtree(build_root, ignore_errors=True)
                self.log(f'replaced the old skin: {replace}')
            if save:
                self.log('Done. In Content Manager pick the car and skin, then click "Update preview".')
            if not save:
                self.log('PREVIEW ONLY - the skin in the car has NOT changed. Press "Create skin in car" to save it.')
            self.set_progress(1.0, 'Done - skin saved in the car' if save else
                              'Preview only - press "Create skin in car" to save it')
            self.after(0, lambda: self.show_views(views, info))
            try:      # a list of what was found in this car (textures, glass, lights ...), kept for next time
                cat = os.path.join(work_dir(car), 'catalogue')
                skingen.car_catalogue(car, cat)
                self.log(f'catalogue of this car: {os.path.join(cat, os.path.basename(car) + ".json")}')
            except Exception: pass
        except Exception as e:
            self.log('ERROR: ' + str(e))
            self.set_progress(0, 'Stopped - see the message')
            if isinstance(e, (ValueError, FileNotFoundError, FileExistsError, RuntimeError)):
                msg = str(e)                       # a known problem: say it plainly
                self.after(0, lambda: messagebox.showerror(APP_NAME, msg))
            else:
                self.log(traceback.format_exc())
        finally:
            if replace:   # never leave a half-built folder in the car's skins
                shutil.rmtree(os.path.join(car, 'skins', '_r4skin_building'), ignore_errors=True)
            self.after(0, self.done)

    @staticmethod
    def compose(v):
        L, R, F, B, T = v['left'], v['right'], v['front'], v['rear'], v['top']
        w = L.width
        fh = int(F.height * (w / 2) / F.width)
        F2, B2 = F.resize((w // 2, fh), Image.LANCZOS), B.resize((w // 2, fh), Image.LANCZOS)
        T2 = T.resize((w, int(T.height * w / T.width)), Image.LANCZOS)
        sheet = Image.new('RGB', (w, L.height + R.height + fh + T2.height), (235, 236, 240))
        y = 0
        for im in (L, R):
            sheet.paste(im, (0, y)); y += im.height
        sheet.paste(F2, (0, y)); sheet.paste(B2, (w // 2, y)); y += fh
        sheet.paste(T2, (0, y))
        return sheet

    def done(self):
        self.busy = False
        for b in (self.btn_prev, self.btn_save): b.state(['!disabled'])

    def show_views(self, views, info=None):
        self.views = views
        self.info = info or {}
        self.adjust_gen = copy.deepcopy(self.info.get('adjust') or {})
        self.sel = None
        self.redraw()

    def on_view(self):
        self.sel = None
        self.redraw()

    # ---- decals on the preview
    def adj(self, key=None):
        """The hand adjustments for the car on screen (or for one decal of it)."""
        d = self.adjust_by_car.setdefault(self.vars['car'].get(), {})
        if key is None: return d
        if key not in d:
            d[key] = {}
            # the app slid it onto its panel (the spot asked for was an opening or ran off the panel): moving it by
            # hand starts from where it shows, not from where it was first put
            ds = [x for x in (getattr(self, 'info', None) or {}).get('decals', []) if x['key'] == key and any(x.get('slid') or ())]
            ds.sort(key=lambda x: x['view'] != self.view_var.get())
            if ds:
                sgn = -1 if ds[0]['view'] == 'right' else 1
                da, db = sgn * ds[0]['slid'][0], ds[0]['slid'][1]
                d[key].update(da=da, db=db)
                g = self.adjust_gen.setdefault(key, {})
                g['da'] = g.get('da', 0) + da; g['db'] = g.get('db', 0) + db
        return d[key]

    def decal_box(self, d):
        """A decal of the last preview as it is now (with changes made since): view axes a, b, w, h, turn."""
        ad, g = self.adj().get(d['key'], {}), self.adjust_gen.get(d['key'], {})
        sgn = -1 if d['view'] == 'right' else 1
        a = d['a'] + sgn * (ad.get('da', 0) - g.get('da', 0)); b = d['b'] + ad.get('db', 0) - g.get('db', 0)
        k = ad.get('scale', 1) / g.get('scale', 1)
        w, h = d['w'] * k, d['h'] * k
        rot = d['rot'] + sgn * (ad.get('rot', 0) - g.get('rot', 0))
        if d['view'] == 'roof_l': a, b, rot = -b, a, rot + 90      # roof number: into the top view's axes
        return a, b, w, h, rot

    def to_screen(self, view, a, b):
        ox, oy, dw, dh = self.geom
        a0, a1, b0, b1 = self.info['frames'][view]
        fx, fy = (a - a0) / (a1 - a0), (b1 - b) / (b1 - b0)
        if view == 'top': fx, fy = fy, 1 - fx                     # the top view is shown turned a quarter
        return ox + fx * dw, oy + fy * dh

    def metres_per_pixel(self, view):
        a0, a1, b0, b1 = self.info['frames'][view]
        return (b1 - b0) / self.geom[2] if view == 'top' else (a1 - a0) / self.geom[2]

    def view_decals(self):
        v = self.view_var.get()
        if v == 'all' or not self.info.get('frames') or not self.geom: return []
        return [d for d in self.info.get('decals', []) if (d['view'] == v or (v == 'top' and d['view'] == 'roof_l'))
                and not self.adj().get(d['key'], {}).get('deleted')]

    def corners(self, d):
        v = self.view_var.get()
        a, b, w, h, rot = self.decal_box(d)
        c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        pts = []
        for x, y in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
            pts += self.to_screen(v, a + x * c - y * s_, b + x * s_ + y * c)
        return pts

    def redraw(self):
        c = self.canvas
        c.delete('all')
        W, H = max(200, c.winfo_width()), max(200, c.winfo_height())
        im = self.views.get(self.view_var.get()) if self.views else None
        if im is None:
            c.create_text(W // 2, H // 2, text=f'{APP_NAME}\n\nPick a car and press Preview', font=('Segoe UI', 13), justify='center')
            self.geom = None
            return
        im = im.copy(); im.thumbnail((W - 10, H - 10), Image.LANCZOS)
        self.preview_img = ImageTk.PhotoImage(im)
        ox, oy = (W - im.width) // 2, (H - im.height) // 2
        c.create_image(ox, oy, image=self.preview_img, anchor='nw')
        self.geom = (ox, oy, im.width, im.height)
        self.draw_boxes()

    def draw_boxes(self):
        c = self.canvas
        c.delete('box')
        ds = self.view_decals()
        changed = self.adj() != self.adjust_gen
        for d in ds:
            on = self.sel == d['key']
            c.create_polygon(*self.corners(d), outline='#ff2d55' if on else '#3a7bd5', fill='', width=3 if on else 1,
                             dash=() if on else (4, 3), tags='box')
        if self.view_var.get() == 'all':
            text = 'Pick one side (Left, Right, Front, Rear or Top), then click a logo, number or name to move it.'
        elif not ds:
            text = 'No logos, number or names on this side.' if self.info else 'Press Preview first.'
        elif self.sel:
            lab = next((d['label'] for d in ds if d['key'] == self.sel), self.sel).split(' (')[0]
            text = f'{lab}: drag = move, wheel = size, Shift+wheel = turn.'
        else:
            text = 'Click a box to pick it. Drag = move, wheel = size, Shift+wheel = turn.'
        if changed and self.view_var.get() != 'all': text += '  Press Preview to redraw the car.'
        self.sel_label.configure(text=text, foreground='#b00020' if changed else '#444')

    def on_press(self, e):
        best = None
        for d in self.view_decals():
            p = self.corners(d)
            xs, ys = p[0::2], p[1::2]
            if min(xs) - 4 <= e.x <= max(xs) + 4 and min(ys) - 4 <= e.y <= max(ys) + 4:
                size = (max(xs) - min(xs)) * (max(ys) - min(ys))
                if best is None or size < best[0]: best = (size, d['key'])
        self.sel = best[1] if best else None
        self.drag = (e.x, e.y)
        self.draw_boxes()

    def on_drag(self, e):
        v = self.view_var.get()
        d = next((d for d in self.view_decals() if d['key'] == self.sel), None)
        if d is None or self.busy: return
        m = self.metres_per_pixel(v)
        dx, dy = (e.x - self.drag[0]) * m, (e.y - self.drag[1]) * m
        self.drag = (e.x, e.y)
        if v == 'top': da, db = -dy, -dx                           # screen -> the top view's own axes
        else: da, db = dx, -dy
        if d['view'] == 'roof_l': da, db = db, -da
        ad = self.adj(d['key'])
        ad['da'] = ad.get('da', 0) + (-da if d['view'] == 'right' else da)   # stored so both sides move the same way
        ad['db'] = ad.get('db', 0) + db
        self.draw_boxes()

    def on_wheel(self, e):
        if not self.sel: return
        up = e.delta > 0
        if e.state & 0x1: self.edit('rot', 5 if up else -5)        # Shift held: turn
        else: self.edit('scale', 1.06 if up else 1 / 1.06)

    def edit(self, what, amount=None):
        if what == 'reset_all':
            self.adjust_by_car.pop(self.vars['car'].get(), None)
            self.draw_boxes(); self.save_cfg(); return
        d = next((d for d in self.view_decals() if d['key'] == self.sel), None)
        if d is None:
            self.sel_label.configure(text='Click a logo, number or name on the preview first (one side showing).', foreground='#b00020')
            return
        if what == 'reset': self.adj().pop(d['key'], None)
        elif what == 'delete':
            self.adj(d['key'])['deleted'] = True
            self.sel = None
            self.sel_label.configure(text=f"{d['label'].split(' (')[0]} deleted (both sides). Press Preview to redraw - "
                                          "it is quick now. 'Reset all' brings deleted ones back.", foreground='#b00020')
            self.save_cfg()
            self.after(10, self.draw_boxes)
            return
        else:
            ad = self.adj(d['key'])
            if what == 'scale': ad['scale'] = min(4.0, max(0.2, ad.get('scale', 1) * amount))
            elif what == 'rot': ad['rot'] = (ad.get('rot', 0) + (-amount if d['view'] == 'right' else amount)) % 360
            elif what == 'flip':
                fl = set(ad.get('flip') or [])
                fl.symmetric_difference_update({d['view']})
                ad['flip'] = sorted(fl)
        self.draw_boxes()
        self.save_cfg()

    def open_full(self):
        im = self.views.get(self.view_var.get()) if self.views else None
        if im is None:
            messagebox.showinfo(APP_NAME, 'Make a preview first.'); return
        car = os.path.join(self.vars['cars_dir'].get(), self.vars['car'].get())
        path = os.path.join(work_dir(car if os.path.isdir(car) else None), f'preview_{self.view_var.get()}.png')
        im.save(path)
        os.startfile(path)

    def on_close(self):
        if self.busy and not messagebox.askyesno(APP_NAME, 'A skin is still being built.\n\nClose anyway? '
                                                 'The skin will not be finished.'):
            return
        self.destroy()


def selftest(car_dir):
    out_txt = os.path.join(work_dir(car_dir), 'selftest.txt')
    tmp = tempfile.mkdtemp(prefix='selftest_', dir=work_dir(car_dir))
    lines = []
    try:
        d = dict(skingen.DEFAULT_DESIGN); d.update(win_enable=True, lens_colour='#ffd21f')
        skingen.generate(car_dir, d, 'selftest', out_root=tmp, log=lines.append)
        lines.append('SELFTEST OK: ' + ', '.join(os.listdir(os.path.join(tmp, 'selftest'))))
    except Exception:
        lines.append('SELFTEST FAILED')
        lines.append(traceback.format_exc())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        with open(out_txt, 'w', encoding='utf8') as f:
            f.write(os.linesep.join(lines))


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--selftest':
        selftest(sys.argv[2])
    else:
        App().mainloop()

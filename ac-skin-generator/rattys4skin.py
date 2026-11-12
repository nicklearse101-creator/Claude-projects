"""Ratty's4Skin Generator - window app.
No AI: the livery is projected onto the car from its own 3D model."""
import copy, glob, json, math, os, queue, re, shutil, sys, tempfile, threading, traceback
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, colorchooser
from PIL import Image, ImageFont, ImageTk

import skingen
import theme

messagebox = theme.messagebox      # dark dialogs, same calls as tkinter.messagebox (tests replace these)

APP_NAME = skingen.APP_NAME
VERSION = '1.9.0'


def find_data_dir(exe_dir, appdata):
    """Where the logos, settings and saved ghosts live: a "data" folder next to the installed app when the installer
    made one ("keep my logos and settings in that folder too"), else %APPDATA%\\Rattys4SkinGenerator as before."""
    own = os.path.join(exe_dir, 'data') if exe_dir else None
    return own if own and os.path.isdir(own) else os.path.join(appdata, 'Rattys4SkinGenerator')


DATA_DIR = find_data_dir(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else None,
                         os.environ.get('APPDATA', os.path.expanduser('~')))
LOGO_DIR = os.path.join(DATA_DIR, 'logos')
SETTINGS = os.path.join(DATA_DIR, 'settings.json')
LIBRARY = os.path.join(DATA_DIR, 'logos.json')
PLACE_NAMES = {'': 'Not used'}; PLACE_NAMES.update(skingen.PLACES)
BG_MODES = {'auto': 'Auto', 'remove': 'Remove background', 'keep': 'Keep whole picture'}
LENS_COLOURS = ['#ff8080', '#ffff80', '#80ff80', '#00ff80', '#80ffff', '#0080ff', '#ff80c0', '#ff80ff',
                '#ff0000', '#ffff00', '#80ff00', '#00ff40', '#00ffff', '#0080c0', '#8080c0', '#ff00ff']


def nearest_lens(c):
    """The allowed lens colour nearest to c (old settings may hold a dark one)."""
    try: r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    except (ValueError, TypeError): return LENS_COLOURS[1]
    if max(r, g, b) < 128: return LENS_COLOURS[1]      # a dark one: plain pale headlight yellow
    return min(LENS_COLOURS, key=lambda x: sum((int(x[i:i + 2], 16) - v) ** 2 for i, v in zip((1, 3, 5), (r, g, b))))
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


def car_display_name(car_dir):
    """The car's name from its ui/ui_car.json (read loosely: modders' files are often not strict JSON), else its folder."""
    try:
        raw = open(os.path.join(car_dir, 'ui', 'ui_car.json'), 'rb').read().decode('utf-8', 'ignore')
        m = re.search(r'"name"\s*:\s*"([^"]*)"', raw)
        if m and m.group(1).strip(): return m.group(1).strip()
    except OSError: pass
    return os.path.basename(os.path.normpath(car_dir))


def ghost_cache_path(car_dir):
    """Where the ghost (untextured front view) of a car is kept, so it is drawn once per car."""
    return os.path.join(DATA_DIR, 'ghosts', os.path.basename(os.path.normpath(car_dir)) + '.png')


def kn5_signature(kn5):
    """The model file as it is now: size and modified time (a copied update can carry an OLDER date, so: equal or not)."""
    st = os.stat(kn5)
    return f'{st.st_size}:{st.st_mtime_ns}'


def save_ghost(img, cache, kn5):
    """Keep a car's ghost, with a note of the model it was drawn from."""
    from PIL.PngImagePlugin import PngInfo
    info = PngInfo(); info.add_text('kn5', kn5_signature(kn5))
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    img.save(cache, pnginfo=info)


def ghost_cache_valid(cache, kn5):
    """The kept ghost was drawn from the car's model exactly as it is now."""
    try:
        with Image.open(cache) as im:
            return im.text.get('kn5') == kn5_signature(kn5)
    except (OSError, ValueError, AttributeError):
        return False


VIEW_TITLES = {'all': 'ALL SIDES', 'left': 'LEFT SIDE', 'right': 'RIGHT SIDE', 'front': 'FRONT', 'rear': 'REAR', 'top': 'TOP'}


def fg_for(colour):
    """Black or white writing on a colour swatch."""
    try: r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
    except (ValueError, TypeError): return theme.TEXT
    return 'black' if (r * .3 + g * .59 + b * .11) / 255 > 0.5 else 'white'


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
        self.ghost, self.ghost_car, self.ghost_token = None, '', 0   # the car's ghost behind the preview
        self.ghost_sig = None                            # the model the ghost was drawn from (kn5_signature)
        self._ghost_q, self._ghost_pending = queue.Queue(), 0          # drawing threads hand their ghost back here
        self._bg_cache = None                            # garage + ghost for the preview's current size
        self.saved = False                               # the views on screen were saved in the car
        self.build()
        self.refresh_cars()
        self.refresh_library()
        self.protocol('WM_DELETE_WINDOW', self.on_close)

    # ---------------------------------------------------------------- settings / library
    def load_cfg(self):
        d = dict(skingen.DEFAULT_DESIGN)
        d.update(cars_dir='', car='', skin_name='My Skin', copy_from='', use_wheels=False, wheel_colour='#7020d2', use_tyres=False, tyre_colour='#ff8000',
                 use_lens=False, lens_colour='#ffd21f', use_tint=False, win_tint_colour='#14181c', win_tint_pct='50', compress=True, avoid_mirror=False)
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
        theme.apply_style(self)
        theme.dark_title_bar(self)
        self.header = theme.Header(self, VERSION); self.header.pack(side='top', fill='x')
        left = ttk.Frame(self, padding=8, style='Window.TFrame'); left.pack(side='left', fill='y')
        right = ttk.Frame(self, padding=8, style='Window.TFrame'); right.pack(side='left', fill='both', expand=True)

        self.tabbar = theme.SlantTabs(left); self.tabbar.pack(fill='x')
        ind = tkfont.Font(root=self, family=theme.HEAD, size=10).measure('0') * 21 + 2   # field label width: previews line up
        tabs = {}
        for key, title in (('car', 'Car'), ('livery', 'Livery'), ('number', 'Number & names'),
                           ('logos', 'Logos'), ('windows', 'Windows'), ('lights', 'Lights & wheels')):
            tabs[key] = self.tabbar.add(title)

        def row(tab, label, widget_fn):
            f = ttk.Frame(tabs[tab]); f.pack(fill='x', pady=3)
            ttk.Label(f, text=label.upper(), width=21, style='Field.TLabel').pack(side='left')
            w = widget_fn(f); w.pack(side='left', fill='x', expand=True)
            return w

        def note(tab, text):
            ttk.Label(tabs[tab], text=text, style='Note.TLabel', wraplength=380, justify='left').pack(fill='x', pady=(2, 6))

        # --- car
        def cars_dir(f):
            fr = ttk.Frame(f)
            ttk.Entry(fr, textvariable=self.var('cars_dir'), width=34).pack(side='left', fill='x', expand=True)
            theme.SlantButton(fr, '…', command=self.pick_cars_dir, size=22, width=32, height=26).pack(side='left')
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
        self.swatch.pack(anchor='w', padx=(ind, 0), pady=(2, 4))
        self.swatch_img = None
        note('livery', 'Patterns are inspired by classic and modern racing liveries; they use your accent, '
                       'highlight and text colours. The picture above shows the car\'s side over its top, front on the left.')
        ttk.Label(tabs['livery'], text='PATTERN FROM A PICTURE', style='Section.TLabel').pack(anchor='w', pady=(8, 0))
        def pic(f):
            fr = ttk.Frame(f)
            ttk.Entry(fr, textvariable=self.var('pattern_image'), width=30).pack(side='left', fill='x', expand=True)
            theme.SlantButton(fr, '…', command=self.pick_pattern_image, size=22, width=32, height=26).pack(side='left')
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
            lab = ttk.Label(tabs['number']); lab.pack(anchor='w', padx=(ind, 0))
            self.font_prev[key] = (lab, src, None)
            upd = (lambda *_, key=key: self.after_idle(lambda: self.update_font_preview(key)))
            self.vars[key].trace_add('write', upd)
            if src in self.vars: self.vars[src].trace_add('write', upd)
            self.after(250, upd)
        ttk.Label(tabs['number'], text='WHERE TO WRITE THEM:', style='Section.TLabel').pack(anchor='w', pady=(8, 2))
        grid = ttk.Frame(tabs['number']); grid.pack(fill='x')
        ttk.Label(grid, text='').grid(row=0, column=0)
        ttk.Label(grid, text='TEAM', style='Field.TLabel').grid(row=0, column=1, padx=6)
        ttk.Label(grid, text='DRIVER', style='Field.TLabel').grid(row=0, column=2, padx=6)
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
        self.tree.heading('#0', text='LOGO'); self.tree.heading('place', text='PLACE ON CAR'); self.tree.heading('tint', text='TINT'); self.tree.heading('bg', text='BACKGROUND')
        self.tree.column('#0', width=180); self.tree.column('place', width=120); self.tree.column('bg', width=95); self.tree.column('tint', width=50, anchor='center')
        ttk.Style(self).configure('Treeview', rowheight=44)
        self.tree.pack(fill='x')
        self.tree.bind('<<TreeviewSelect>>', self.on_logo_select)
        bf = ttk.Frame(lt); bf.pack(fill='x', pady=4)
        theme.SlantButton(bf, 'Add logos…', command=self.add_logos, kind='primary').pack(side='left')
        theme.SlantButton(bf, 'Remove', command=self.remove_logo).pack(side='left')
        theme.SlantButton(bf, 'Clear all (not used)', command=self.clear_logos).pack(side='left')
        ttk.Checkbutton(lt, text='Keep logos off areas the car mirrors (no backwards copies; a logo with nowhere else to go is left off)',
                        variable=self.var('avoid_mirror', tk.BooleanVar)).pack(anchor='w', pady=(2, 0))
        pf = ttk.Frame(lt); pf.pack(fill='x', pady=2)
        ttk.Label(pf, text='PLACE ON CAR', width=21, style='Field.TLabel').pack(side='left')
        self.place_var = tk.StringVar(value='Not used')
        self.place_box = ttk.Combobox(pf, textvariable=self.place_var, values=list(PLACE_NAMES.values()), state='readonly', width=20)
        self.place_box.pack(side='left'); self.place_box.bind('<<ComboboxSelected>>', self.on_place)
        bgf = ttk.Frame(lt); bgf.pack(fill='x', pady=2)
        ttk.Label(bgf, text='BACKGROUND', width=21, style='Field.TLabel').pack(side='left')
        self.bg_var = tk.StringVar(value='Auto')
        bgb = ttk.Combobox(bgf, textvariable=self.bg_var, values=list(BG_MODES.values()), state='readonly', width=20)
        bgb.pack(side='left'); bgb.bind('<<ComboboxSelected>>', self.on_place)
        note('logos', 'Auto removes a plain one-colour background and keeps pictures with busy backgrounds whole.')
        self.tint_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(pf, text='Tint glow to highlight colour', variable=self.tint_var, command=self.on_place).pack(side='left', padx=6)
        uf = ttk.LabelFrame(lt, text='ON THE CAR'); uf.pack(fill='x', pady=(6, 2))
        self.used_tree = ttk.Treeview(uf, columns=('place',), height=5, selectmode='browse', show='headings')
        self.used_tree.heading('place', text='PLACE'); self.used_tree.column('place', width=150)
        self.used_tree['columns'] = ('logo', 'place')
        self.used_tree.heading('logo', text='LOGO'); self.used_tree.heading('place', text='PLACE')
        self.used_tree.column('logo', width=230); self.used_tree.column('place', width=150)
        self.used_tree.pack(fill='x')
        self.used_tree.bind('<<TreeviewSelect>>', self.on_used_select)

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
        row('lights', 'Lens colour', lambda f: self.colour_button(f, 'lens_colour', LENS_COLOURS))
        note('lights', 'Lens colours are the bright ones only - darker colours would look like a dead lamp.')
        note('lights', 'Tints the front lamp textures, so the lens and its glow take this colour.')
        ttk.Separator(tabs['lights']).pack(fill='x', pady=6)
        row('lights', '', lambda f: ttk.Checkbutton(f, text='Recolour the wheel rims', variable=self.var('use_wheels', tk.BooleanVar)))
        row('lights', 'Rim colour', lambda f: self.colour_button(f, 'wheel_colour'))
        row('lights', '', lambda f: ttk.Checkbutton(f, text='Recolour the tyres', variable=self.var('use_tyres', tk.BooleanVar)))
        row('lights', 'Tyre colour', lambda f: self.colour_button(f, 'tyre_colour'))
        note('lights', 'Rims and tyres are separate. Only cars with their own rim / tyre textures can change.')

        # --- buttons + log
        # Preview / Create / progress / log always stay in the window: packed first, at the bottom; the tab pages get
        # what is left and scroll when that is not enough
        bot = ttk.Frame(left, style='Window.TFrame')
        bf = ttk.Frame(bot, style='Window.TFrame'); bf.pack(fill='x', pady=(10, 0))
        self.btn_prev = theme.SlantButton(bf, 'Preview', command=lambda: self.run(save=False), kind='secondary',
                                          size=19, height=40, width=150)
        self.btn_prev.pack(side='left')
        self.btn_save = theme.SlantButton(bf, 'Create skin in car', command=lambda: self.run(save=True), kind='primary',
                                          size=21, height=40, width=300)
        self.btn_save.pack(side='left')
        self.prog = ttk.Progressbar(bot, mode='determinate', maximum=100, style='Orange.Horizontal.TProgressbar')
        self.prog.pack(fill='x', pady=(8, 0))
        sf = ttk.Frame(bot, style='Window.TFrame'); sf.pack(fill='x')
        self.status = ttk.Label(sf, text='Ready', style='Status.TLabel')
        self.status.pack(side='left')
        self.pct = ttk.Label(sf, text='', style='Pct.TLabel')
        self.pct.pack(side='right')
        self.log_box = tk.Text(bot, height=7, width=60, font=('Consolas', 8), bg=theme.FIELD, fg=theme.MUTED,
                               insertbackground=theme.TEXT, selectbackground=theme.ACC, relief='flat', bd=0, padx=6, pady=4,
                               highlightthickness=1, highlightbackground=theme.LINE, highlightcolor=theme.LINE)
        self.log_box.tag_configure('warn', foreground=theme.ACC)
        self.log_box.pack(fill='x', pady=(6, 0))
        bot.pack(side='bottom', fill='x')
        self.tabbar.pack_forget(); self.tabbar.pack(side='top', fill='both', expand=True)

        vb = ttk.Frame(right, style='Window.TFrame'); vb.pack(fill='x', pady=(0, 2))
        ttk.Label(vb, text='VIEW', style='WField.TLabel').pack(side='left')
        self.view_var = tk.StringVar(value='all')
        theme.ChipGroup(vb, (('all', 'All sides'), ('left', 'Left'), ('right', 'Right'), ('front', 'Front'),
                             ('rear', 'Rear'), ('top', 'Top')), self.view_var, command=self.on_view).pack(side='left', padx=6)
        theme.SlantButton(vb, 'Open full size', command=self.open_full, size=14).pack(side='right')
        # edit bar: move / size / turn / flip the logos, number and names on the preview
        eb = ttk.Frame(right, style='Window.TFrame'); eb.pack(fill='x', pady=(0, 2))
        ttk.Label(eb, text='EDIT ON THE PREVIEW', style='WField.TLabel').pack(side='left', padx=(0, 6))
        self.edit_bar = theme.ButtonBar(eb, (('Bigger', lambda: self.edit('scale', 1.08)), ('Smaller', lambda: self.edit('scale', 1 / 1.08)),
                          ('Turn ↺', lambda: self.edit('rot', 5)), ('Turn ↻', lambda: self.edit('rot', -5)),
                          ('Flip', lambda: self.edit('flip')), ('Edit text…', self.edit_text), ('Delete', lambda: self.edit('delete')),
                          ('Reset', lambda: self.edit('reset')),
                          ('Reset all', lambda: self.edit('reset_all'))))
        self.edit_bar.pack(side='left', fill='x', expand=True)
        self.sel_label = ttk.Label(right, text='Pick one side (Left, Right, Front, Rear or Top), then click a logo, number or name to move it.',
                                   style='Hint.TLabel')
        self.sel_label.pack(anchor='w', pady=(0, 4))
        self.canvas = tk.Canvas(right, background=theme.BG, highlightthickness=0)
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
        self.vars['skin_name'].trace_add('write', lambda *_: self.update_header())
        self.tabbar.select(0)

    def update_header(self):
        car = os.path.join(self.vars['cars_dir'].get(), self.vars['car'].get())
        self.header.set_car(car_display_name(car) if self.vars['car'].get() and os.path.isdir(car) else '',
                            self.vars['skin_name'].get())

    def update_swatch(self):
        try:
            d = self.design()
            im = skingen.pattern_swatch(d, 300)
        except Exception:
            return
        self.swatch_img = ImageTk.PhotoImage(im)
        self.swatch.configure(image=self.swatch_img)

    def font_image(self, font_path, text, colour=theme.TEXT, width=300, height=40):
        """The words in that font, on a dark field (for the font previews)."""
        im = Image.new('RGB', (width, height), theme.hexc(theme.FIELD)[:3])
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
            self.sel_label.configure(text='Pick a team or driver name on the preview first (one side showing).', foreground=theme.ACC)
            return
        ad = self.adj(d['key'])
        is_team = d['key'].startswith('team name')
        win = tk.Toplevel(self); win.title('Edit text - ' + d['label'].split(' (')[0]); win.transient(self)
        theme.style_toplevel(win); win.grab_set()
        f = ttk.Frame(win, padding=12); f.pack(fill='both', expand=True)
        fonts = [DEFAULT_FONT_NAME] + list(list_fonts())
        text_v = tk.StringVar(value=ad.get('text') or self.vars['team' if is_team else 'name'].get())
        cur_font = next((n for n, pth in list_fonts().items() if pth == ad.get('font')), None)
        font_v = tk.StringVar(value=cur_font or self.vars['font_team_name' if is_team else 'font_name_name'].get())
        col_v = tk.StringVar(value=ad.get('colour') or '')
        ttk.Label(f, text='WORDS', style='Field.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Entry(f, textvariable=text_v, width=34).grid(row=0, column=1, sticky='we', pady=3)
        ttk.Label(f, text='FONT', style='Field.TLabel').grid(row=1, column=0, sticky='w')
        ttk.Combobox(f, textvariable=font_v, values=fonts, state='readonly', width=32).grid(row=1, column=1, sticky='we', pady=3)
        ttk.Label(f, text='COLOUR', style='Field.TLabel').grid(row=2, column=0, sticky='w')
        cf = ttk.Frame(f); cf.grid(row=2, column=1, sticky='w', pady=3)
        cb = tk.Button(cf, width=12, relief='flat', bd=0, highlightthickness=1, highlightbackground=theme.LINE, cursor='hand2')
        cb.pack(side='left')
        theme.SlantButton(cf, 'Automatic', command=lambda: col_v.set(''), size=13, height=26).pack(side='left', padx=4)
        prev = ttk.Label(f); prev.grid(row=3, column=0, columnspan=2, pady=(8, 4))
        keep = {}

        def refresh(*_):
            c = col_v.get()
            cb.configure(text=c or 'automatic', bg=c or theme.RAISED, activebackground=c or theme.RAISED,
                         fg=fg_for(c) if c else theme.TEXT)
            keep['img'] = self.font_image(list_fonts().get(font_v.get()), text_v.get(), c or theme.TEXT, 360, 48)
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
        theme.SlantButton(bf, 'OK', command=ok, kind='primary', width=86).pack(side='left', padx=2)
        theme.SlantButton(bf, 'Cancel', command=win.destroy, width=86).pack(side='left', padx=2)
        ttk.Label(f, text='Changes this box on both sides of the car. Press Preview to see it on the car.',
                  style='Note.TLabel').grid(row=5, column=0, columnspan=2, pady=(6, 0))

    def checks(self, parent, items):
        fr = ttk.Frame(parent)
        for key, label in items:
            ttk.Checkbutton(fr, text=label, variable=self.var(key, tk.BooleanVar)).pack(side='left', padx=(0, 10))
        return fr

    def colour_button(self, parent, key, choices=None):
        v = self.var(key)
        if choices and v.get().lower() not in choices: v.set(nearest_lens(v.get()))
        b = tk.Button(parent, width=12, relief='flat', bd=0, highlightthickness=1, highlightbackground=theme.LINE, cursor='hand2')
        def paint(*_):
            c = v.get() or '#000000'
            try:
                r, g, bb = self.winfo_rgb(c); lum = (r * .3 + g * .59 + bb * .11) / 65535
                b.configure(bg=c, activebackground=c, text=c, fg='black' if lum > 0.5 else 'white')
            except tk.TclError: pass
        def pick():
            if choices: return self.swatch_picker(b, v, choices)
            c = colorchooser.askcolor(v.get(), parent=self)[1]
            if c: v.set(c)
        b.configure(command=pick); v.trace_add('write', paint); paint()
        return b

    def swatch_picker(self, anchor, var, choices, cols=8):
        """A small chart of the allowed colours under the button; a click picks one."""
        top = tk.Toplevel(self); top.title('Lens colour'); top.transient(self); top.resizable(False, False)
        theme.style_toplevel(top)
        top.geometry(f'+{anchor.winfo_rootx()}+{anchor.winfo_rooty() + anchor.winfo_height()}')
        for k, c in enumerate(choices):
            tk.Button(top, bg=c, activebackground=c, width=4, height=1, relief='sunken' if c == var.get().lower() else 'raised',
                      command=lambda c=c: (var.set(c), top.destroy())).grid(row=k // cols, column=k % cols, padx=2, pady=2)
        top.grab_set(); top.focus_set()

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
        skins = skingen.stock_skins(car) if os.path.isdir(car) else []
        self.copy_box['values'] = [''] + skins
        if self.vars['copy_from'].get() not in skins: self.vars['copy_from'].set('')   # a skin of another car
        self.update_header()
        self.request_ghost(car)

    # ---------------------------------------------------------------- the ghost behind the preview
    def request_ghost(self, car_dir):
        """Show the ghost of this car: from the kept picture, or drawn from its model in the background."""
        self.ghost_token += 1
        token, name = self.ghost_token, os.path.basename(os.path.normpath(car_dir))
        if not self.vars['car'].get() or not os.path.isdir(car_dir):
            self._set_ghost(token, None, ''); return
        cache = ghost_cache_path(car_dir)
        try: kn5 = skingen.find_main_kn5(car_dir); sig = kn5_signature(kn5)
        except Exception: self._set_ghost(token, None, name); return
        if name == self.ghost_car and self.ghost is not None and self.ghost_sig == sig: return
        if ghost_cache_valid(cache, kn5):
            try:
                self._set_ghost(token, Image.open(cache).convert('RGBA'), name, sig); return
            except Exception: pass
        self._set_ghost(token, None, '')

        def work():                     # no Tk here: the ghost goes back through the queue (see _poll_ghost)
            try: img = skingen.ghost_view(skingen.Car(car_dir, log=lambda *a: None))
            except Exception: img = None
            if img is not None:
                try: save_ghost(img, cache, kn5)
                except OSError: pass
            self._ghost_q.put((token, img, name, sig))
        self._ghost_pending += 1
        threading.Thread(target=work, daemon=True).start()
        if self._ghost_pending == 1: self.after(150, self._poll_ghost)

    def _poll_ghost(self):
        """Pick up ghosts the drawing threads finished (main thread; also fine before the window's main loop runs)."""
        while True:
            try: item = self._ghost_q.get_nowait()
            except queue.Empty: break
            self._ghost_pending -= 1
            self._set_ghost(*item)
        if self._ghost_pending > 0: self.after(150, self._poll_ghost)

    def _set_ghost(self, token, img, car, sig=None):
        if token != self.ghost_token: return                  # a car picked before this one: too late
        self.ghost, self.ghost_car, self.ghost_sig, self._bg_cache = img, car, sig, None
        self.redraw()

    # ---------------------------------------------------------------- logo library
    def refresh_library(self):
        self.tree.delete(*self.tree.get_children())
        for i, lg in enumerate(self.library):
            path = os.path.join(LOGO_DIR, lg['file'])
            if path not in self.thumbs:
                try:
                    im = Image.open(path).convert('RGBA'); im.thumbnail((40, 40))
                    bg = Image.new('RGBA', (40, 40), theme.hexc(theme.RAISED)); bg.alpha_composite(im, ((40 - im.width) // 2, (40 - im.height) // 2))
                    self.thumbs[path] = ImageTk.PhotoImage(bg)
                except Exception: self.thumbs[path] = None
            kw = {'image': self.thumbs[path]} if self.thumbs[path] else {}
            self.tree.insert('', 'end', iid=str(i), text='  ' + lg.get('name', lg['file']),
                             values=(PLACE_NAMES.get(lg.get('place', ''), 'Not used'), BG_MODES.get(lg.get('bg', 'auto'), 'Auto'),
                                     'yes' if lg.get('tint') else ''), **kw)
        self.refresh_used()

    def refresh_used(self):
        """The 'On the car' list: every logo that has a place, in the order of the car's places."""
        if not hasattr(self, 'used_tree'): return
        self.used_tree.delete(*self.used_tree.get_children())
        order = list(PLACE_NAMES)
        used = sorted((i for i, lg in enumerate(self.library) if lg.get('place')),
                      key=lambda i: order.index(self.library[i]['place']) if self.library[i]['place'] in order else 99)
        for i in used:
            lg = self.library[i]
            self.used_tree.insert('', 'end', iid=str(i), values=(lg.get('name', lg['file']), PLACE_NAMES.get(lg['place'], lg['place'])))
        if not used: self.used_tree.insert('', 'end', iid='none', values=('(no logos chosen yet)', ''))

    def on_used_select(self, e=None):
        sel = self.used_tree.selection()
        if sel and sel[0] != 'none' and self.tree.exists(sel[0]):
            self.tree.selection_set(sel[0]); self.tree.see(sel[0])

    def clear_logos(self):
        if not any(lg.get('place') for lg in self.library): return
        if not messagebox.askyesno(APP_NAME, 'Take every logo off the car (all set to "Not used")?\n'
                                             'The logos stay in the library.'): return
        for lg in self.library: lg['place'] = ''
        self.save_library(); self.refresh_library(); self.on_logo_select()

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
        tag = ('warn',) if msg.startswith(('PREVIEW ONLY', 'ERROR')) else ()
        self.after(0, lambda: (self.log_box.insert('end', msg + '\n', tag), self.log_box.see('end')))

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
        d['lens_colour'] = nearest_lens(self.vars['lens_colour'].get()) if self.vars['use_lens'].get() else None
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
        self.after(0, lambda: (self.prog.configure(value=frac * 100), self.status.configure(text=text),
                               self.pct.configure(text=f'{round(frac * 100)}%' if frac > 0 else '')))

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
            views['all_rgba'] = self.compose(views, rgba=True)
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
            self.after(0, lambda: self.show_views(views, info, saved=save))
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
    def compose(v, rgba=False):
        """All five views on one sheet. Saved one (rgba=False): their RGB on light grey, as before. rgba=True: cut out,
        on a clear background, for the preview's garage."""
        keys = ('left', 'right', 'front', 'rear', 'top')
        L, R, F, B, T = (theme.cutout(v[k]) if rgba else v[k].convert('RGB') for k in keys)
        w = L.width
        fh = int(F.height * (w / 2) / F.width)
        F2, B2 = F.resize((w // 2, fh), Image.LANCZOS), B.resize((w // 2, fh), Image.LANCZOS)
        T2 = T.resize((w, int(T.height * w / T.width)), Image.LANCZOS)
        size = (w, L.height + R.height + fh + T2.height)
        sheet = Image.new('RGBA', size, (0, 0, 0, 0)) if rgba else Image.new('RGB', size, (235, 236, 240))

        def put(im, xy):
            sheet.paste(im, xy, im if rgba else None)
        y = 0
        for im in (L, R):
            put(im, (0, y)); y += im.height
        put(F2, (0, y)); put(B2, (w // 2, y)); y += fh
        put(T2, (0, y))
        return sheet

    def done(self):
        self.busy = False
        for b in (self.btn_prev, self.btn_save): b.state(['!disabled'])

    def show_views(self, views, info=None, saved=False):
        self.views = views
        self.saved = saved
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
        """The preview: the garage with the car's ghost, the car (cut out) on the floor, the labels, the boxes."""
        c = self.canvas
        c.delete('all')
        W, H = max(200, c.winfo_width()), max(200, c.winfo_height())
        key = (W, H, id(self.ghost))
        if self._bg_cache is None or self._bg_cache[0] != key:
            self._bg_cache = (key, theme.preview_background(W, H, self.ghost))
        bg = self._bg_cache[1]
        view = self.view_var.get()
        im = (self.views.get('all_rgba') if view == 'all' else self.views.get(view)) if self.views else None
        if im is None:
            car = os.path.join(self.vars['cars_dir'].get(), self.vars['car'].get())
            has_car = bool(self.vars['car'].get()) and os.path.isdir(car)
            img, _ = theme.compose_preview(bg, None, view, car_display_name(car).upper() if has_car else APP_NAME.upper(), None,
                                           ('PRESS PREVIEW', 'to see your livery on the car') if has_car else
                                           ('PICK A CAR', 'on the Car tab'))
            self.geom = None
        else:
            if view != 'all': im = theme.cutout(im)
            img, self.geom = theme.compose_preview(bg, im, view, VIEW_TITLES.get(view, ''),
                                                   None if self.saved else 'PREVIEW ONLY · NOT SAVED', None)
        self.preview_img = ImageTk.PhotoImage(img)
        c.create_image(0, 0, image=self.preview_img, anchor='nw')
        if self.geom: self.draw_boxes()

    def draw_boxes(self):
        c = self.canvas
        c.delete('box')
        ds = self.view_decals()
        changed = self.adj() != self.adjust_gen
        for d in ds:
            on = self.sel == d['key']
            pts = self.corners(d)
            c.create_polygon(*pts, outline=theme.ACC, fill='', width=3 if on else 1, dash=() if on else (4, 3), tags='box')
            if on:
                for x, y in zip(pts[0::2], pts[1::2]):
                    c.create_rectangle(x - 4, y - 4, x + 4, y + 4, fill=theme.ACC, outline='', tags='box')
                lab = d['label'].split(' (')[0].upper() + '  ·  SELECTED'
                self._sel_img = ImageTk.PhotoImage(theme.text_image(lab, 12, theme.ACC, italic=0.1))
                c.create_image(16, 40, image=self._sel_img, anchor='nw', tags='box')
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
        self.sel_label.configure(text=text, foreground=theme.ACC if changed else theme.MUTED)

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
            self.sel_label.configure(text='Click a logo, number or name on the preview first (one side showing).', foreground=theme.ACC)
            return
        if what == 'reset': self.adj().pop(d['key'], None)
        elif what == 'delete':
            self.adj(d['key'])['deleted'] = True
            self.sel = None
            self.sel_label.configure(text=f"{d['label'].split(' (')[0]} deleted (both sides). Press Preview to redraw - "
                                          "it is quick now. 'Reset all' brings deleted ones back.", foreground=theme.ACC)
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
        im = im.convert('RGB')                             # as before: the view on light grey
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

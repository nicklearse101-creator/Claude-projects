"""Ratty's4Skin Generator - window app.
No AI: the livery is projected onto the car from its own 3D model."""
import json, os, re, shutil, sys, tempfile, threading, traceback
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
from PIL import Image, ImageTk

import skingen

APP_NAME = skingen.APP_NAME
VERSION = '1.1.0'
DATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'Rattys4SkinGenerator')
LOGO_DIR = os.path.join(DATA_DIR, 'logos')
SETTINGS = os.path.join(DATA_DIR, 'settings.json')
LIBRARY = os.path.join(DATA_DIR, 'logos.json')
PLACE_NAMES = {'': 'Not used'}; PLACE_NAMES.update(skingen.PLACES)
BG_MODES = {'auto': 'Auto', 'remove': 'Remove background', 'keep': 'Keep whole picture'}
NUMBER_STYLES = {'board': 'Number board', 'plain': 'Plain number', 'none': 'No number'}


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
        self.thumbs = {}
        self.preview_img = None
        self.busy = False
        self.build()
        self.refresh_cars()
        self.refresh_library()

    # ---------------------------------------------------------------- settings / library
    def load_cfg(self):
        d = dict(skingen.DEFAULT_DESIGN)
        d.update(cars_dir='', car='', skin_name='My Skin', copy_from='', use_wheels=False, wheel_colour='#7020d2',
                 use_lens=False, lens_colour='#ffd21f', use_beam=False, beam_colour='#fff2c8')
        try: d.update(json.load(open(SETTINGS, encoding='utf8')))
        except Exception: pass
        if not d.get('cars_dir') or not os.path.isdir(d['cars_dir']): d['cars_dir'] = find_ac_cars()
        return d

    def save_cfg(self):
        try: json.dump({k: v.get() for k, v in self.vars.items()}, open(SETTINGS, 'w', encoding='utf8'), indent=2)
        except Exception: pass

    def load_library(self):
        try: lib = json.load(open(LIBRARY, encoding='utf8'))
        except Exception: lib = []
        return [l for l in lib if os.path.isfile(os.path.join(LOGO_DIR, l.get('file', '')))]

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

        # --- livery
        for key, label in (('base', 'Base colour'), ('accent', 'Accent colour'), ('accent2', 'Highlight colour'),
                           ('text', 'Text colour')):
            row('livery', label, lambda f, k=key: self.colour_button(f, k))
        row('livery', 'Pattern', lambda f: ttk.Combobox(f, textvariable=self.var('pattern'), state='readonly',
                                                       values=['sweep', 'stripes', 'split', 'none'], width=12))
        row('livery', '', lambda f: ttk.Checkbutton(f, text='Halftone dots', variable=self.var('halftone', tk.BooleanVar)))

        # --- number & names
        row('number', 'Racing number', lambda f: ttk.Entry(f, textvariable=self.var('number'), width=8))
        self.vars['number_style_name'] = tk.StringVar(value=NUMBER_STYLES.get(self.cfg.get('number_style'), 'Number board'))
        row('number', 'Number style', lambda f: ttk.Combobox(f, textvariable=self.vars['number_style_name'],
                                                            values=list(NUMBER_STYLES.values()), state='readonly', width=16))
        row('number', 'Show number on', lambda f: self.checks(f, (('number_doors', 'Doors'), ('number_roof', 'Roof'))))
        row('number', 'Team / wordmark', lambda f: ttk.Entry(f, textvariable=self.var('team')))
        row('number', 'Driver name', lambda f: ttk.Entry(f, textvariable=self.var('name')))
        note('number', 'The wordmark goes on the front wings, boot, rear and front bumper; the driver name '
                       'under it on the wings. A logo placed on the front wings moves them to the lower doors.')

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
        row('windows', 'Sticker text colour', lambda f: self.colour_button(f, 'win_text_colour'))
        row('windows', 'Also show', lambda f: self.checks(f, (('win_number', 'Racing number'), ('win_name', 'Driver name'))))
        note('windows', 'Banner across the top of the windscreen and rear window; number and driver name on the rear '
                        'window and rear side windows. Logos can go on the windscreen, rear window or side windows '
                        '(Logos tab). Number and name come from the "Number & names" tab.')

        # --- lights & wheels
        row('lights', '', lambda f: ttk.Checkbutton(f, text='Colour the headlight lenses', variable=self.var('use_lens', tk.BooleanVar)))
        row('lights', 'Lens colour', lambda f: self.colour_button(f, 'lens_colour'))
        note('lights', 'Tints the front lamp textures, so the lens and its glow take this colour.')
        row('lights', '', lambda f: ttk.Checkbutton(f, text='Colour the headlight beam (cast light)', variable=self.var('use_beam', tk.BooleanVar)))
        row('lights', 'Beam colour', lambda f: self.colour_button(f, 'beam_colour'))
        note('lights', 'Needs Custom Shaders Patch: written to the skin\'s ext_config.ini.')
        ttk.Separator(tabs['lights']).pack(fill='x', pady=6)
        row('lights', '', lambda f: ttk.Checkbutton(f, text='Recolour the wheels', variable=self.var('use_wheels', tk.BooleanVar)))
        row('lights', 'Wheel colour', lambda f: self.colour_button(f, 'wheel_colour'))

        # --- buttons + log
        bf = ttk.Frame(left); bf.pack(fill='x', pady=(10, 0))
        self.btn_prev = ttk.Button(bf, text='Preview', command=lambda: self.run(save=False))
        self.btn_prev.pack(side='left', expand=True, fill='x', padx=2, ipady=4)
        self.btn_save = ttk.Button(bf, text='Create skin in car', command=lambda: self.run(save=True))
        self.btn_save.pack(side='left', expand=True, fill='x', padx=2, ipady=4)
        self.log_box = tk.Text(left, height=12, width=60, font=('Consolas', 8))
        self.log_box.pack(fill='both', expand=True, pady=(8, 0))

        self.canvas = tk.Label(right, background='#ebecf0', anchor='center',
                               text=f'{APP_NAME}\n\nPick a car and press Preview', font=('Segoe UI', 13))
        self.canvas.pack(fill='both', expand=True)

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
        d['wheel_colour'] = self.vars['wheel_colour'].get() if self.vars['use_wheels'].get() else None
        d['lens_colour'] = self.vars['lens_colour'].get() if self.vars['use_lens'].get() else None
        d['beam_colour'] = self.vars['beam_colour'].get() if self.vars['use_beam'].get() else None
        return d

    def run(self, save):
        if self.busy: return
        car = os.path.join(self.vars['cars_dir'].get(), self.vars['car'].get())
        if not self.vars['car'].get() or not os.path.isdir(car):
            messagebox.showerror(APP_NAME, 'Pick a car first (Car tab).'); return
        name = self.vars['skin_name'].get().strip() or 'My Skin'
        if save:
            sid = re.sub(r'[^a-z0-9_]+', '_', name.lower()).strip('_')
            if os.path.exists(os.path.join(car, 'skins', sid)):
                messagebox.showerror(APP_NAME, f'The car already has a skin folder "{sid}".\nChoose another skin name.')
                return
        self.save_cfg()
        self.busy = True
        for b in (self.btn_prev, self.btn_save): b.state(['disabled'])
        self.log_box.delete('1.0', 'end')
        threading.Thread(target=self.work, args=(car, name, save), daemon=True).start()

    def work(self, car, name, save):
        tmp = tempfile.mkdtemp(prefix='r4skin_')
        try:
            out, sheet, *_ = skingen.generate(car, self.design(), name, out_root=None if save else tmp,
                                              resolution=4096 if self.vars['hires'].get() else None,
                                              log=self.log, copy_other_from=self.vars['copy_from'].get() or None)
            if save:
                sheet.save(os.path.join(out, 'generator_preview.png'))
                self.log('Done. In Content Manager pick the car and skin, then click "Update preview".')
            self.after(0, lambda: self.show(sheet))
        except Exception as e:
            self.log('ERROR: ' + str(e)); self.log(traceback.format_exc())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            self.after(0, self.done)

    def done(self):
        self.busy = False
        for b in (self.btn_prev, self.btn_save): b.state(['!disabled'])

    def show(self, sheet):
        w, h = max(200, self.canvas.winfo_width() - 10), max(200, self.canvas.winfo_height() - 10)
        im = sheet.copy(); im.thumbnail((w, h), Image.LANCZOS)
        self.preview_img = ImageTk.PhotoImage(im)
        self.canvas.configure(image=self.preview_img, text='')


def selftest(car_dir):
    out_txt = os.path.join(tempfile.gettempdir(), 'r4s_selftest.txt')
    tmp = tempfile.mkdtemp(prefix='r4s_test_')
    lines = []
    try:
        d = dict(skingen.DEFAULT_DESIGN); d.update(win_enable=True, lens_colour='#ffd21f', beam_colour='#fff2c8')
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

"""Help for first-time users (Nik 16 Nov: "nobody reads the Readme"): a tip on every control when the mouse rests on
it, and a short guided tour that walks through the app on the first start. Both can be switched off on the Car tab
("Show help"); "Show me round" starts the tour again."""
import tkinter as tk
from tkinter import ttk

import theme


class Tooltip:
    """A small note beside a control while the mouse rests on it (only while help is on)."""

    def __init__(self, widget, text, enabled):
        self.w, self.text, self.enabled = widget, text, enabled
        self.win, self.job = None, None
        widget.bind('<Enter>', self.enter, add='+')
        widget.bind('<Leave>', self.hide, add='+')
        widget.bind('<ButtonPress>', self.hide, add='+')

    def enter(self, e=None):
        if not self.enabled(): return
        self.cancel()
        self.job = self.w.after(450, self.show)

    def cancel(self):
        if self.job is not None:
            try: self.w.after_cancel(self.job)
            except tk.TclError: pass
            self.job = None

    def show(self):
        self.job = None
        if self.win is not None or not self.enabled(): return
        try:
            x, y = self.w.winfo_rootx() + 12, self.w.winfo_rooty() + self.w.winfo_height() + 4
        except tk.TclError: return
        self.win = tw = tk.Toplevel(self.w)
        tw.wm_overrideredirect(True)
        tw.configure(bg=theme.ACC)
        tk.Label(tw, text=self.text, justify='left', wraplength=320, bg=theme.RAISED, fg=theme.TEXT,
                 font=theme.UI_FONT, padx=8, pady=5).pack(padx=1, pady=1)
        tw.wm_geometry(f'+{x}+{y}')

    def hide(self, e=None):
        self.cancel()
        if self.win is not None:
            try: self.win.destroy()
            except tk.TclError: pass
            self.win = None


class Tour:
    """Steps: (tab title or None, widget or None, heading, text). Each step shows its tab, rings the widget in the
    accent colour and puts a bubble beside it with Back / Next / Skip."""

    def __init__(self, app, steps, on_end):
        self.app, self.steps, self.on_end = app, steps, on_end
        self.i = 0
        self.ring = [self._bar() for _ in range(4)]
        self.bubble = tk.Toplevel(app)
        self.bubble.wm_overrideredirect(True)
        self.bubble.configure(bg=theme.ACC)
        inner = tk.Frame(self.bubble, bg=theme.PANEL, padx=12, pady=10)
        inner.pack(padx=2, pady=2)
        self.count = tk.Label(inner, bg=theme.PANEL, fg=theme.MUTED, font=theme.UI_FONT, anchor='w')
        self.count.pack(fill='x')
        self.head = tk.Label(inner, bg=theme.PANEL, fg=theme.ACC, font=(theme.HEAD, 13), anchor='w', justify='left')
        self.head.pack(fill='x')
        self.body = tk.Label(inner, bg=theme.PANEL, fg=theme.TEXT, font=theme.UI_FONT, justify='left', wraplength=330, anchor='w')
        self.body.pack(fill='x', pady=(4, 8))
        bf = tk.Frame(inner, bg=theme.PANEL); bf.pack(fill='x')
        self.btn_skip = theme.SlantButton(bf, 'Skip tour', command=self.close, size=12, height=26)
        self.btn_skip.pack(side='left')
        self.btn_next = theme.SlantButton(bf, 'Next', command=self.next, kind='primary', size=13, height=26)
        self.btn_next.pack(side='right')
        self.btn_back = theme.SlantButton(bf, 'Back', command=self.back, size=13, height=26)
        self.btn_back.pack(side='right')
        app.bind('<Configure>', self._moved, add='+')
        app.bind('<Unmap>', self._hidden, add='+')          # the app minimised: the bubble goes with it
        app.bind('<Map>', self._moved, add='+')
        self.show()

    def _hidden(self, e=None):
        if e is not None and e.widget is not self.app: return
        for w in self.ring + [self.bubble]:
            try: w.withdraw()
            except tk.TclError: pass

    def _bar(self):
        b = tk.Toplevel(self.app)
        b.wm_overrideredirect(True)
        b.configure(bg=theme.ACC)
        return b

    def _moved(self, e=None):
        if e is None or e.widget is self.app: self.app.after_idle(self.place)

    def show(self):
        tab, widget, head, text = self.steps[self.i]
        if tab is not None and tab in self.app.tabbar.titles:
            self.app.tabbar.select(self.app.tabbar.titles.index(tab))
        self.count.configure(text=f'{self.i + 1} of {len(self.steps)}')
        self.head.configure(text=head)
        self.body.configure(text=text)
        self.btn_back.configure(text='Back' if self.i else ' ')
        self.btn_next.configure(text='Next' if self.i < len(self.steps) - 1 else 'Finish')
        self.app.update_idletasks()
        if widget is not None: self._scroll_to(widget)
        self.place()

    def _scroll_to(self, w):
        """A control on a tab page that is scrolled out of sight is scrolled into it."""
        tb = self.app.tabbar
        try:
            if not tb.needs_scroll() or not str(w).startswith(str(tb.body)): return
            y = w.winfo_rooty() - tb.body.winfo_rooty()
            total = max(1, tb.body.winfo_height())
            tb.view.yview_moveto(max(0.0, (y - 60) / total))
            self.app.update_idletasks()
        except tk.TclError:
            pass

    def place(self):
        if not self.bubble.winfo_exists(): return
        _, widget, _, _ = self.steps[self.i]
        self.bubble.update_idletasks()
        bw, bh = self.bubble.winfo_reqwidth(), self.bubble.winfo_reqheight()
        if widget is None:
            for r in self.ring: r.withdraw()
            x = self.app.winfo_rootx() + (self.app.winfo_width() - bw) // 2
            y = self.app.winfo_rooty() + (self.app.winfo_height() - bh) // 3
        else:
            x0, y0 = widget.winfo_rootx() - 4, widget.winfo_rooty() - 4
            w, h = widget.winfo_width() + 8, widget.winfo_height() + 8
            t = 3
            for r, (gx, gy, gw, gh) in zip(self.ring, ((x0, y0, w, t), (x0, y0 + h - t, w, t), (x0, y0, t, h), (x0 + w - t, y0, t, h))):
                r.wm_geometry(f'{max(gw, 1)}x{max(gh, 1)}+{gx}+{gy}'); r.deiconify(); r.lift()
            ax0, ay0 = self.app.winfo_rootx(), self.app.winfo_rooty()
            ax1, ay1 = ax0 + self.app.winfo_width(), ay0 + self.app.winfo_height()
            x = x0 + w + 12                                   # beside the control, else under it, inside the window
            if x + bw > ax1: x = max(ax0 + 8, min(x0, ax1 - bw - 8))
            y = y0 if x > x0 + w else y0 + h + 8
            if y + bh > ay1: y = max(ay0 + 8, y0 - bh - 8)
        self.bubble.wm_geometry(f'+{int(x)}+{int(y)}')
        self.bubble.deiconify(); self.bubble.lift()

    def next(self):
        if self.i < len(self.steps) - 1:
            self.i += 1; self.show()
        else:
            self.close()

    def back(self):
        if self.i:
            self.i -= 1; self.show()

    def close(self):
        for w in self.ring + [self.bubble]:
            try: w.destroy()
            except tk.TclError: pass
        self.on_end()


def tour_steps(app):
    """The tour (tab, control, heading, words). Controls the app keeps in app.help."""
    h = app.help
    return [
        (None, None, "Welcome to Ratty's4Skin Generator",
         'This quick tour shows what each part of the app does - about a minute. Rest the mouse on anything later for a '
         'tip. Help can be switched off on the Car tab.'),
        ('Car', h.get('car'), '1. Pick your car',
         'Choose the car to make a skin for. Type part of its name to find it quickly.'),
        ('Car', h.get('start_from'), 'Or change a skin you have',
         'Pick a skin already on the car to change it - it shows on the preview by itself. Skins made with this app come '
         'back as you made them; any other skin keeps its paint and is saved as a new skin.'),
        ('Car', h.get('skin_name'), '2. Name your skin',
         'The new skin gets this name in the game. Using the same name again replaces a skin you made before.'),
        ('Car', h.get('new_livery'), 'Start again any time',
         'Clears the livery back to a plain white car. The app also starts with a blank livery every time it opens.'),
        ('Livery', h.get('base'), '3. Colours',
         'Base colour = the main paint. Accent and highlight colour the pattern; text colour is for numbers and names.'),
        ('Livery', h.get('pattern'), '4. Pattern',
         'Pick a design. The arrow keys or mouse wheel step through them, and the picture under it shows the pattern '
         'on a simple car. "Gallery…" shows them all at once in your colours.'),
        ('Livery', h.get('finish'), 'Paint finish',
         'Gloss, metallic, pearl or matte paint - shown in the game by Custom Shaders Patch.'),
        ('Number & names', h.get('team'), '5. Number and names',
         'Your racing number, team name and driver name, with a choice of racing fonts. The ticks below say where on '
         'the car they go.'),
        ('Logos', h.get('add_logos'), '6. Logos',
         'Add your logos here (PNGs with see-through backgrounds work best). They stay in your library for next time.'),
        ('Logos', h.get('place'), 'Put a logo on the car',
         'Click a logo in the list, then pick where it goes. Pick more places to use the same logo on several parts.'),
        ('Windows', h.get('win_enable'), '7. Windows',
         'Window stickers (a banner across the top of the windscreen, number and name on the windows) and tinted glass.'),
        (None, h.get('preview'), '8. Preview',
         'See your livery on the car. The first preview of a car takes up to a minute; after that it is quick.'),
        (None, h.get('canvas'), '9. Move things on the car',
         'Pick one side (Left, Right, Front, Rear or Top), click a logo, number or name and drag it. Mouse wheel = '
         'bigger / smaller, Shift + wheel = turn. The car redraws itself when you let go.'),
        (None, h.get('create'), '10. Save it in the game',
         'Happy? This puts the skin into the car. In Content Manager pick the car and your skin, then click '
         '"Update preview".'),
        (None, None, "That's it!",
         'Rest the mouse on any control for a tip. "Show me round" on the Car tab starts this tour again; '
         '"Show help" there switches the tips and the tour off.'),
    ]


# the tip for each control, by the words on it or the label beside it (case does not matter)
TIPS = {
    'Start new livery': 'Clears the livery back to a plain white car: colours, pattern, number, names, logos on the car, '
                        'windows and wheels. Your car and your logo library stay.',
    'Show me round': 'Starts the guided tour of the app again.',
    'AC cars folder': "Where your Assetto Corsa cars are. Found by itself - change it only if your game is somewhere else.",
    'Car (type to search)': 'The car to make a skin for. Type part of its name to find it.',
    'Start from': 'Change a skin already on the car: one made with this app comes back as you made it; any other skin '
                  'keeps its paint and is saved as a new skin (the original is never changed).',
    'Skin name': 'The name of the new skin. Using the same name again replaces a skin you made before with this app.',
    'Windows etc. from': "Optional: the car's other files (windows, interior, plates) are copied from one of its own skins.",
    'App colours': "The app's own colours. The app restarts in them; your livery is kept.",
    'Report this car…': 'The app got this car wrong? Saves a small zip on your desktop to post on the Ratty\'s Racing Discord.',
    'Sharper textures (4K) - crisper writing and logos, bigger files': '4K textures: crisper writing and logos, but bigger '
                                                                         'files and a slower build.',
    'Smaller files (compressed textures, about a quarter of the size)': 'Compressed textures: about a quarter of the size '
                                                                         'and they look the same in the game. Leave it on.',
    'Base colour': 'The main paint colour of the car.',
    'Accent colour': "The pattern's main colour.",
    'Highlight colour': 'The thin stripes and edges in the pattern (and logo glows).',
    'Text colour': 'The colour of the number and names.',
    'Pattern': 'The livery design. Up / Down arrows or the mouse wheel step through them; the picture below shows it on a '
               'simple car.',
    'Gallery…': 'Every pattern at once, in your colours. Click one to use it.',
    'Picture': 'A picture to make the pattern from: a side view of a car or a flat pattern ("Pattern from a picture").',
    'The picture is': 'What the picture shows, so the app knows how to wrap it round the car.',
    'Simplify': 'Melts small writing and stickers in the picture away.',
    "Use my colours instead of the picture's": 'Repaints the picture in your base, accent and highlight colours.',
    'Halftone dots (comic-style dots up the lower sides)': 'Comic-style dots up the lower sides of the car, fading out '
                                                          'upwards. They go on the plain paint, not over the pattern.',
    'Paint finish': 'Gloss, metallic flakes, pearl or matte paint - shown in the game by Custom Shaders Patch '
                    '(others see it if they have CSP and your skin).',
    'Racing number': 'Your racing number (leave empty for none).',
    'Number style': 'A number on a white board, the number on its own, or no number.',
    'Show number on': 'Where the number goes.',
    'Team / wordmark': 'Your team name (or any words) - written where the ticks below say.',
    'Driver name': 'The driver name - written where the ticks below say, under the team name where both go.',
    'Team font': 'The team name\'s font. "Racing:" fonts come with the app; Up / Down arrows step through them.',
    'Driver font': 'The driver name\'s font. "Racing:" fonts come with the app; Up / Down arrows step through them.',
    'Number font': 'The number\'s font. "Racing:" fonts come with the app; Up / Down arrows step through them.',
    'Add logos…': 'Adds logos or pictures to your library (PNGs with see-through backgrounds work best).',
    'Remove': 'Removes the logo picked in the list from your library.',
    'Clear all (not used)': 'Takes every logo off the car; they stay in the library.',
    'Keep logos off areas the car mirrors (no backwards copies; a logo with nowhere else to go is left off)':
        'Some cars use one half of the texture for both sides, so a logo there shows backwards on the other side. '
        'Tick to keep logos off those parts.',
    'Place on car': 'Click a logo in the list, then pick where it goes. Pick more places to use it on several parts; '
                    '"Not used" takes it off everywhere.',
    'Background': 'Auto removes a plain background round a logo and keeps busy pictures whole.',
    'Tint glow to highlight colour': 'A soft glow round the logo in your highlight colour.',
    'Take off': 'Takes the logo picked in "On the car" off that one place.',
    'Make new window stickers': 'A banner across the top of the windscreen and rear window, plus number and name on the '
                                'windows.',
    'Remove the stickers already on the windows': "Clears the car's own window stickers first.",
    'Banner text': 'The words on the windscreen banner.',
    'Banner colour': 'The colour of the windscreen banner.',
    'Banner height (cm)': 'How tall the banner is.',
    'Sticker text colour': 'The colour of the words on the window stickers.',
    'Also show': 'Number and / or driver name on the rear window and the side windows chosen below.',
    'Side stickers on': 'Which side windows get the number and name.',
    'Tint the windows': 'Tinted glass, like a window film.',
    'Tint colour': 'The colour of the tint.',
    'How dark (%)': 'How dark the tint is.',
    'Tint the windscreen too': 'The windscreen stays clear unless this is ticked.',
    'Recolour the wheel rims': 'New colour for the rims (only cars whose rims have their own texture).',
    'Rim colour': 'The rims\' new colour.',
    'Recolour the tyres': 'New colour for the tyres (only cars whose tyres have their own texture).',
    'Tyre colour': 'The tyres\' new colour.',
    'Preview': 'Shows your livery on the car without saving anything. The first time for a car takes up to a minute.',
    'Create skin in car': 'Saves the skin into the car. In Content Manager pick the car and skin, then "Update preview".',
    'Open full size': 'Opens the view on screen as a picture.',
    'Grid': 'Lines every 25 cm and the centre line, to line things up.',
    'Show help (tips like this one, and the tour at the start)': 'Untick when you know your way round: no more tips or tour.',
}

# controls the tour points at: (words on it or beside it) -> name
HELP_KEYS = {'Car (type to search)': 'car', 'Start from': 'start_from', 'Skin name': 'skin_name', 'Start new livery': 'new_livery',
             'Base colour': 'base', 'Pattern': 'pattern', 'Paint finish': 'finish', 'Team / wordmark': 'team',
             'Add logos…': 'add_logos', 'Place on car': 'place', 'Make new window stickers': 'win_enable',
             'Preview': 'preview', 'Create skin in car': 'create'}


def attach(app, root, enabled):
    """Tips on every control whose words (or the label beside it) are in TIPS; the tour's controls into app.help.
    Returns the tooltips."""
    tips = {k.lower(): v for k, v in TIPS.items()}
    keys = {k.lower(): v for k, v in HELP_KEYS.items()}
    out, done = [], set()

    def words(w):
        try: t = w.cget('text')
        except Exception: t = getattr(w, '_text', None)
        return t.strip().lower() if isinstance(t, str) else ''

    def leaves(w):
        kids = w.winfo_children()
        if w.winfo_class() in ('TFrame', 'Frame') and kids: return [x for k in kids for x in leaves(k)]
        return [w]

    def add(w, text):
        if str(w) in done: return
        done.add(str(w)); out.append(Tooltip(w, text, enabled))

    def walk(w):
        for c in w.winfo_children():
            t = words(c)
            if t in tips or t in keys:
                is_label = c.winfo_class() == 'TLabel'
                others = [s for s in c.master.winfo_children() if s is not c] if is_label else []
                if is_label and others:                 # a field label: the control(s) beside it
                    if t in keys: app.help.setdefault(keys[t], others[0])
                    if t in tips:
                        add(c, tips[t])
                        for s in others:
                            for leaf in leaves(s):
                                if words(leaf) not in tips: add(leaf, tips[t])
                elif not is_label:
                    if t in keys: app.help.setdefault(keys[t], c)
                    if t in tips: add(c, tips[t])
            walk(c)
    walk(root)
    return out

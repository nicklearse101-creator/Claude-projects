"""theme.py Tk side: style, slanted tabs / buttons / chips, header, dark dialogs.
python -m pytest -p no:cacheprovider tests/test_theme_tk.py -q"""
import os, sys
import tkinter as tk
from tkinter import ttk
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import theme


@pytest.fixture(scope='module')
def root():
    r = tk.Tk()
    r.geometry('600x400+-2000+-2000')        # shown (events and dialogs need a viewable window), but off screen
    theme.apply_style(r)
    r.update()
    yield r
    r.destroy()


def test_apply_style_runs(root):
    assert ttk.Style(root).theme_use() == 'clam'


def test_tabs_select(root):
    tabs = theme.SlantTabs(root)
    pages = [tabs.add(t) for t in ('Car', 'Livery', 'Logos')]
    for i, p in enumerate(pages):
        ttk.Label(p, text='x' * (10 * (i + 1))).pack()
    tabs.pack()
    tabs.select(2); root.update()
    assert tabs.index() == 2
    assert pages[2].grid_info() and not pages[0].grid_info() and not pages[1].grid_info()
    tabs.destroy()


def test_button_invoke_and_disable(root):
    hits = []
    b = theme.SlantButton(root, 'Preview', command=lambda: hits.append(1))
    b.pack(); root.update()
    b.invoke()
    assert hits == [1]
    b.event_generate('<Button-1>', x=10, y=10); b.event_generate('<ButtonRelease-1>', x=10, y=10); root.update()
    assert hits == [1, 1]                                  # a click works
    b.state(['disabled'])
    assert 'disabled' in b.state()
    b.event_generate('<Button-1>', x=10, y=10); b.event_generate('<ButtonRelease-1>', x=10, y=10); root.update()
    b.invoke()
    assert hits == [1, 1]
    b.state(['!disabled'])
    assert 'disabled' not in b.state()
    b.destroy()


def test_chips_set_variable(root):
    v = tk.StringVar(value='all'); calls = []
    ch = theme.ChipGroup(root, [('all', 'All sides'), ('left', 'Left')], v, command=lambda: calls.append(v.get()))
    ch.pack(); root.update()
    ch.pick('left')
    assert v.get() == 'left' and calls == ['left']
    ch.destroy()


def test_askyesno_yes(root):
    root.after(300, lambda: theme._open_dialogs[-1].buttons['Yes'].invoke())
    assert theme.messagebox.askyesno('Title', 'Replace it?', parent=root) is True
    root.after(300, lambda: theme._open_dialogs[-1].buttons['No'].invoke())
    assert theme.messagebox.askyesno('Title', 'Replace it?', parent=root) is False


def test_header_long_name(root):
    h = theme.Header(root, '1.8.0')
    h.configure(width=1000); h.pack(); root.update()
    h.set_car('X' * 200, 'my skin ' * 30); root.update()
    car_w, skin_w = h.last_widths
    assert car_w <= 500 and skin_w <= 500
    h.destroy()


def test_buttonbar_wraps_and_invokes(root):
    hits = []
    labels = ['Bigger', 'Smaller', 'Turn ↺', 'Turn ↻', 'Flip', 'Edit text…', 'Delete', 'Reset', 'Reset all']
    bar = theme.ButtonBar(root, [(t, lambda t=t: hits.append(t)) for t in labels])
    bar.place(x=0, y=0, width=300); root.update()
    assert bar.rows > 1                                  # too narrow for one line: wraps
    bar.place(x=0, y=0, width=1400); root.update()
    assert bar.rows == 1
    bar.invoke('Flip')
    assert hits == ['Flip']
    bar.destroy()


def test_dialog_dark_title_and_width(root):
    seen = {}

    def check():
        d = theme._open_dialogs[-1]
        seen.update(dark=getattr(d, 'dark_title', None), width=d.winfo_width())
        d.buttons['OK'].invoke()
    root.after(400, check)
    theme.messagebox.showerror('Ratty\'s4Skin Generator', 'Pick a car first (Car tab).', parent=root)
    assert seen['dark'] is True                       # dark title bar set once the window is shown
    assert seen['width'] >= 360                       # wide enough for the app's name in the title


def test_buttonbar_hover_no_redraw_loop(root):
    """Hovering a button must not redraw over and over (recreated items under the pointer fire <Enter> again)."""
    bar = theme.ButtonBar(root, [('Bigger', lambda: None), ('Smaller', lambda: None)])
    bar.place(x=0, y=0, width=600); root.update()
    calls = {'n': 0}
    orig = bar._restyle if hasattr(bar, '_restyle') else bar._draw
    def counted(*a):
        calls['n'] += 1
        if calls['n'] > 50: raise RuntimeError('redraw loop')
        return orig(*a)
    if hasattr(bar, '_restyle'): bar._restyle = counted
    else: bar._draw = counted
    bar.event_generate('<Motion>', x=20, y=16); root.update()
    bar.event_generate('<Motion>', x=21, y=16); root.update()
    assert calls['n'] <= 4
    bar.destroy()


def test_tabs_scroll_when_page_too_tall(root):
    tabs = theme.SlantTabs(root)
    p = tabs.add('Logos')
    for i in range(40): ttk.Label(p, text=f'row {i}').pack()
    tabs.place(x=0, y=0, width=400, height=250); tabs.select(0); root.update()
    assert tabs.needs_scroll()                            # the page is taller than the room: it scrolls
    tabs.place(x=0, y=0, width=400, height=2000); root.update()
    assert not tabs.needs_scroll()
    tabs.destroy()

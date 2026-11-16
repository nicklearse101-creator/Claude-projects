r"""Drop-down lists (Nik 16 Nov):
 2 - arrow keys step through the fonts without opening the list, like the mouse wheel does;
 5 - the wheel over a drop-down changes its option only: the page behind it does not scroll too.
Lists where a step would do something big (App colours restarts the app, Place on car adds a place, Car loads
another car) ignore the wheel: there it scrolls the page as before.
python -m pytest -p no:cacheprovider tests/test_dropdowns.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_car_change import app          # noqa: F401  (app is a fixture)
import rattys4skin as R


def page_scrolls(app, monkeypatch):
    calls = []
    monkeypatch.setattr(app.tabbar, '_sb_on', True)
    monkeypatch.setattr(app.tabbar.view, 'yview_scroll', lambda *a: calls.append(a))
    return calls


def font_box(app):
    return next(w for w in all_widgets(app) if w.winfo_class() == 'TCombobox' and str(w.cget('textvariable')) == str(app.vars['font_team_name']))


def all_widgets(w):
    out = [w]
    for c in w.winfo_children(): out += all_widgets(c)
    return out


def wheel(w, delta=-120):
    w.event_generate('<MouseWheel>', delta=delta, x=5, y=5)
    w.update()


def test_wheel_on_font_box_changes_font_not_page(app, monkeypatch):
    calls = page_scrolls(app, monkeypatch)
    box = font_box(app)
    before = box.get()
    wheel(box)
    assert box.get() != before
    assert calls == []


def test_wheel_in_open_list_does_not_scroll_page(app, monkeypatch):
    calls = page_scrolls(app, monkeypatch)
    box = font_box(app)
    lb = box.tk.eval(f'ttk::combobox::PopdownWindow {box}') + '.f.l'      # Tk's own list (no Python widget)
    app.tabbar._wheel(type('E', (), dict(widget=type('W', (), dict(__str__=lambda s: lb))(), delta=-120))())
    assert calls == []


def test_arrow_keys_step_fonts_without_opening(app):
    box = font_box(app)
    vals = list(box['values'])
    app.geometry('+-4000+-4000'); app.deiconify()             # off screen: key presses need a window with focus
    app.tabbar.select(app.tabbar.titles.index('Number & names'))
    box.set(vals[0]); box.focus_force(); app.update()
    box.event_generate('<Down>'); app.update()
    assert box.get() == vals[1]
    box.event_generate('<Down>'); box.event_generate('<Up>'); app.update()
    assert box.get() == vals[1]
    pop = box.tk.eval(f'ttk::combobox::PopdownWindow {box}')
    assert box.tk.eval(f'winfo ismapped {pop}') == '0'
    lab = app.font_prev['font_team_name'][2]
    assert lab is not None


def test_risky_lists_ignore_the_wheel(app, monkeypatch):
    calls = page_scrolls(app, monkeypatch)
    for box in (app.place_box, app.theme_box, app.car_box):
        before = box.get()
        wheel(box)
        assert box.get() == before, box
    assert len(calls) == 3                                   # the page scrolled instead

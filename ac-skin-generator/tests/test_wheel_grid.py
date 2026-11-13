r"""Nik 13 Nov: (1) the logo list only scrolled with the mouse wheel in full screen - the tab page took the wheel;
(2) an alignment grid / centre line on the preview, not too intrusive, to place logos by hand.
python -m pytest -p no:cacheprovider tests/test_wheel_grid.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import os, sys
import pytest
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_car_change import app, pick, preview          # noqa: F401  (app is a fixture)
import rattys4skin as R


def logos(app, n=30):
    for i in range(n):
        f = f'logo{i}.png'
        Image.new('RGBA', (40, 40), (i * 8, 50, 200, 255)).save(os.path.join(R.LOGO_DIR, f))
        app.library.append(dict(file=f, name=f'Logo {i}', place='', tint=False))
    app.refresh_library()


def wheel(app, w, delta):
    w.event_generate('<MouseWheel>', delta=delta, x=5, y=5)
    app.update()


def test_logo_list_scrolls_when_the_page_scrolls(app):
    app.deiconify(); app.geometry('1000x640'); app.update()       # small window: the Logos page needs its scroll bar
    logos(app)
    tabs = app.tabbar
    tabs.select([i for i, t in enumerate(tabs.titles) if 'LOGO' in t.upper()][0]); app.update()
    assert tabs._sb_on                                            # the page itself scrolls here
    page0 = tabs.view.yview()[0]
    wheel(app, app.tree, -120)
    assert app.tree.yview()[0] > 0                                # the list moved ...
    assert tabs.view.yview()[0] == page0                          # ... and the page did not


def test_page_scrolls_once_the_list_is_at_its_end(app):
    app.deiconify(); app.geometry('1000x640'); app.update()
    logos(app)
    tabs = app.tabbar
    tabs.select([i for i, t in enumerate(tabs.titles) if 'LOGO' in t.upper()][0]); app.update()
    app.tree.yview_moveto(1.0); app.update()
    page0 = tabs.view.yview()[0]
    wheel(app, app.tree, -120)
    assert tabs.view.yview()[0] > page0


def test_dropdowns_ignore_the_wheel(app):
    box = app.car_box
    before = app.vars['car'].get()
    wheel(app, box, -120); wheel(app, box, 120)
    assert app.vars['car'].get() == before


def grid_items(app):
    return app.canvas.find_withtag('grid'), app.canvas.find_withtag('grid_centre')


def test_grid_on_a_single_view(app):
    preview(app)
    app.view_var.set('front'); app.on_view(); app.update()
    lines, centre = grid_items(app)
    assert len(lines) >= 4 and len(centre) == 1
    x0, y0, x1, y1 = app.canvas.coords(centre[0])
    assert x0 == pytest.approx(app.to_screen('front', 0.0, 0.0)[0], abs=1) and x0 == pytest.approx(x1, abs=1)


def test_grid_centre_on_the_top_view_runs_along_the_car(app):
    preview(app)
    app.view_var.set('top'); app.on_view(); app.update()
    x0, y0, x1, y1 = app.canvas.coords(grid_items(app)[1][0])
    assert y0 == pytest.approx(app.to_screen('top', 0.0, 0.0)[1], abs=1) and y0 == pytest.approx(y1, abs=1)


def test_no_grid_on_all_sides_or_when_off(app):
    preview(app)
    app.view_var.set('all'); app.on_view(); app.update()
    assert grid_items(app) == ((), ())
    app.view_var.set('left'); app.on_view(); app.vars['show_grid'].set(False); app.redraw(); app.update()
    assert grid_items(app) == ((), ())


def test_grid_under_the_boxes(app):
    preview(app)
    app.view_var.set('left'); app.on_view(); app.update()
    items = app.canvas.find_all()
    assert max(items.index(i) for i in app.canvas.find_withtag('grid')) < min(items.index(i) for i in app.canvas.find_withtag('box'))

"""Speed work 1.16 (Nik 20 Nov: "see what can be done to speed up the app"). Every faster version must give exactly the
same result as 1.15.0 - each one is checked here against the 1.15.0 code, kept below as the reference.
python -m pytest -p no:cacheprovider tests/test_speed_1160.py -q --basetemp=D:\\ClaudeData\\tmp\\pytest"""
import copy, os, sys, time
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen as S

SMALL_CAR = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\abarth500'


# ---------------------------------------------------------------- 1.15.0 reference code
def old_raster_tris(px, order, W, H, crop=False):
    x0 = y0 = 0; w, h = W, H
    if crop and len(order):
        q = px[order].reshape(-1, 2)
        x0, y0 = max(0, int(q[:, 0].min()) - 2), max(0, int(q[:, 1].min()) - 2)
        w, h = min(W, int(q[:, 0].max()) + 3) - x0, min(H, int(q[:, 1].max()) + 3) - y0
    im = Image.new('I', (max(w, 1), max(h, 1)), -1); d = ImageDraw.Draw(im)
    ed = Image.new('I', (max(w, 1), max(h, 1)), -1); de = ImageDraw.Draw(ed)
    pts = (px[order] - (x0, y0)).tolist()
    for i, t in zip(order.tolist(), pts):
        q = [tuple(t[0]), tuple(t[1]), tuple(t[2])]
        d.polygon(q, fill=i)
        de.polygon(q, outline=i)
    a = np.asarray(im, dtype=np.int64).copy(); e = np.asarray(ed, dtype=np.int64)
    a[a < 0] = e[a < 0]
    return a, x0, y0


def old_decal_hits(tm, dc, hm, wm, a_shift=0.0, inside=False, b_shift=0.0):
    vdir, fa, fb = S.VIEWS[dc.view]
    none = (np.zeros(0, np.int64), np.zeros(0), np.zeros(0))

    def ab(P):
        a, b = dc.coords(P) if dc.coords is not None else (fa(P), fb(P))
        return a - (dc.a + a_shift), b - (dc.b + b_shift)
    T, TN = tm.t_pos, tm.t_nrm
    a, b = ab(T.reshape(-1, 3)); a, b = a.reshape(-1, 3), b.reshape(-1, 3)
    f = TN.mean(1) @ vdir
    if inside: f = -f
    ok = (a.min(1) < wm / 2) & (a.max(1) > -wm / 2) & (b.min(1) < hm / 2) & (b.max(1) > -hm / 2) & (f > S.MIN_FACING)
    if dc.region is not None: ok &= dc.region(T.mean(1))
    thin = np.nonzero(ok & ~tm.t_good)[0]
    C = np.nonzero(ok & tm.t_good)[0]
    if not len(C): return none
    Sm, rep = S.sample_tris(T[C], 0.003, with_index=True)
    sa, sb = ab(Sm)
    ins = (np.abs(sa) < wm / 2) & (np.abs(sb) < hm / 2)
    Sm, rep, sa, sb = Sm[ins], rep[ins], sa[ins], sb[ins]
    if not len(Sm): return none
    sd = Sm @ vdir
    mid = (np.abs(sa) < 0.2 * wm) & (np.abs(sb) < 0.2 * hm)
    z_lim = np.percentile(sd[mid], 90) + 0.12 if mid.sum() > 20 else np.inf
    near = sd < z_lim
    ny = int(hm / S.DEPTH_CELL) + 2
    cell = lambda a_, b_: ((a_ + wm / 2) / S.DEPTH_CELL).astype(np.int64) * ny + ((b_ + hm / 2) / S.DEPTH_CELL).astype(np.int64)
    zmax = np.full((int(wm / S.DEPTH_CELL) + 2) * ny, -np.inf)
    np.maximum.at(zmax, cell(sa[near], sb[near]), sd[near])
    if len(thin):
        O = S.sample_tris(T[thin], 0.004)
        oa, ob = ab(O); od = O @ vdir
        k_ = (np.abs(oa) < wm / 2) & (np.abs(ob) < hm / 2) & (od < z_lim)
        np.maximum.at(zmax, cell(oa[k_], ob[k_]), od[k_])
    occ = getattr(tm, 'occluders', None)
    if occ is not None and len(occ) and not inside:
        oa, ob = ab(occ.reshape(-1, 3)); oa, ob = oa.reshape(-1, 3), ob.reshape(-1, 3)
        o_in = (oa.min(1) < wm / 2) & (oa.max(1) > -wm / 2) & (ob.min(1) < hm / 2) & (ob.max(1) > -hm / 2)
        if dc.region is not None and o_in.any(): o_in[o_in] = dc.region(occ[o_in].mean(1))
        if o_in.any():
            O = S.sample_tris(occ[o_in], 0.004)
            oa, ob = ab(O); od = O @ vdir
            k_ = (np.abs(oa) < wm / 2) & (np.abs(ob) < hm / 2) & (od < z_lim)
            np.maximum.at(zmax, cell(oa[k_], ob[k_]), od[k_])

    def tol(f_):
        fc = np.clip(f_, 0.05, 1.0)
        return 0.015 + np.minimum(0.04, S.DEPTH_CELL * np.sqrt(1 - fc ** 2) / fc)
    vis = near & (sd > zmax[cell(sa, sb)] - tol(f[C][rep]))
    V = C[np.unique(rep[vis])]
    if not len(V): return none
    order = V[np.argsort(T[V].mean(1) @ vdir)]
    ids, x0, y0 = old_raster_tris(tm.t_px, order, tm.W, tm.H, crop=True)
    yy, xx = np.nonzero(ids >= 0)
    t = ids[yy, xx]
    yy += y0; xx += x0
    idx = tm.index[yy, xx]
    on = idx >= 0
    yy, xx, t, idx = yy[on], xx[on], t[on], idx[on]
    P, N = S.locate_texels(tm.t_px, T, TN, t, xx, yy)
    a, b = ab(P)
    fp = N @ vdir
    if inside: fp = -fp
    d = P @ vdir
    keep = (np.abs(a) < wm / 2) & (np.abs(b) < hm / 2) & (fp > S.MIN_FACING) & (d < z_lim)
    idx, a, b, fp, d = idx[keep], a[keep], b[keep], fp[keep], d[keep]
    t = t[keep]
    keep = d > zmax[cell(a, b)] - tol(fp)
    tm.last_sharp = tm.tri_size[t[keep]] < 3.0 * tm.texel_m
    return idx[keep].astype(np.int64), a[keep], b[keep]


def old_paint_canvas(tm, cols, base, paint, shade):
    canvas = base.copy()
    sel = paint[tm.yy, tm.xx]
    yy, xx = tm.yy[sel], tm.xx[sel]
    canvas[yy, xx] = cols[sel] * shade[yy, xx, None]
    m = Image.fromarray((paint * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    mm = np.asarray(m).astype(np.float32)[..., None] / 255
    painted = np.clip(canvas, 0, 255)
    out_rgb = base * (1 - mm) + painted * mm
    out_rgb[paint] = painted[paint]
    return out_rgb


# ---------------------------------------------------------------- the car
@pytest.fixture(scope='module')
def car():
    return S.Car(SMALL_CAR, log=lambda *a: None)


@pytest.fixture(scope='module')
def tm(car):
    tex = car.body_textures[0]
    t = S.TexelMap(car.meshes_for(tex), 1024, 1024, lambda *a: None, skip_stretched=True); t.tex = tex
    occ = [m.pos[m.idx] for m in car.kn5.meshes if m.mat is not None and len(m.idx) and not S.see_through(m.mat)
           and m.mat.samplers.get('txDiffuse') != tex and 'shadow' not in m.name.lower()]
    t.occluders = np.concatenate(occ) if occ else None
    return t


def tri_soup(n, W, H, seed):
    rng = np.random.default_rng(seed)
    c = rng.random((n, 1, 2)) * (W, H)
    return c + (rng.random((n, 3, 2)) - 0.5) * rng.choice([1.5, 6, 40], (n, 1, 1))


# ---------------------------------------------------------------- 5: triangles drawn into the texture
def test_raster_tris_same_as_before(tm):
    for seed, (W, H) in enumerate(((97, 131), (512, 512), (300, 200))):
        px = tri_soup(3000, W, H, seed)
        order = np.random.default_rng(seed).permutation(len(px))[:2500]
        assert np.array_equal(S.raster_tris(px, order, W, H)[0], old_raster_tris(px, order, W, H)[0])
        new, old = S.raster_tris(px, order[:40], W, H, crop=True), old_raster_tris(px, order[:40], W, H, crop=True)
        assert np.array_equal(new[0], old[0]) and new[1:] == old[1:]
    order = np.arange(len(tm.t_px))
    assert np.array_equal(S.raster_tris(tm.t_px, order, tm.W, tm.H)[0], old_raster_tris(tm.t_px, order, tm.W, tm.H)[0])


# ---------------------------------------------------------------- 1 + 4: where a decal lands
def decals(car):
    logo = Image.new('RGBA', (300, 120), (200, 30, 30, 255))
    zf, zr = car.hi[2], car.lo[2]
    out = []
    for view, a, b, h in (('left', 0.2, 0.55, 0.3), ('right', -0.3, 0.6, 0.25), ('front', 0.0, 0.4, 0.12),
                          ('rear', 0.1, 0.7, 0.15), ('top', 0.0, -(zf - 0.4), 0.35), ('roof_l', 0.0, 0.0, 0.3),
                          ('left', 5.0, 9.0, 0.2)):                         # last one: nowhere near the car
        out.append(S.Decal(logo, view, a, b, h, region=None))
    out.append(S.Decal(logo, 'left', 0.0, 0.6, 0.3, region=lambda P: P[:, 0] > 0.1))
    out.append(S.Decal(logo, 'rear', 0.0, 0.6, 0.2, region=lambda P: P[:, 2] < zr + 0.6))
    out.append(S.Decal(logo, 'top', 0.0, -(zf - 0.4), 0.3, region=lambda P, z0=zf - 1.0: P[:, 2] > z0))
    return out


def same_hits(new, old):
    return all(np.array_equal(x, y) and x.dtype == y.dtype for x, y in zip(new, old))


def test_decal_hits_same_as_before(car, tm):
    S.clear_hit_cache()
    for dc in decals(car):
        img, hm, wm = S.decal_size(dc, tm.texel_m)
        for a_s, b_s, inside in ((0.0, 0.0, False), (0.05, -0.04, False), (0.0, 0.1, True)):
            old = old_decal_hits(tm, dc, hm, wm, a_s, inside, b_s); sharp = tm.last_sharp
            for _ in range(2):                                  # worked out, then from the cache
                new = S.decal_hits(tm, dc, hm, wm, a_s, inside, b_s)
                assert same_hits(new, old)
                assert (tm.last_sharp is sharp) if not len(old[0]) else np.array_equal(tm.last_sharp, sharp)


def test_decal_hits_kept_for_the_next_preview(car, tm, monkeypatch):
    """The second time (a logo that did not move) the hits come from the cache: no triangles drawn again."""
    S.clear_hit_cache()
    dc = decals(car)[0]
    img, hm, wm = S.decal_size(dc, tm.texel_m)
    S.decal_hits(tm, dc, hm, wm)
    drawn = []
    monkeypatch.setattr(S, 'raster_tris', lambda *a, **k: drawn.append(1) or old_raster_tris(*a, **k))
    again = copy.copy(dc)                                         # a new Decal at the same spot (the next preview)
    S.decal_hits(tm, again, hm, wm)
    assert not drawn
    again.a += 0.01                                                 # moved: worked out again
    S.decal_hits(tm, again, hm, wm)
    assert drawn


def test_decal_hits_region_values_count(car, tm):
    """Two regions from the same line of code but different numbers are different regions."""
    S.clear_hit_cache()
    logo = Image.new('RGBA', (300, 120), (200, 30, 30, 255))
    mk = lambda z0: S.Decal(logo, 'left', 0.0, 0.5, 0.3, region=lambda P, z0=z0: P[:, 2] > z0)
    for z0 in (-0.2, 0.3, -0.2, 0.3):
        dc = mk(z0)
        img, hm, wm = S.decal_size(dc, tm.texel_m)
        assert same_hits(S.decal_hits(tm, dc, hm, wm), old_decal_hits(tm, dc, hm, wm))
    zc = [0.0]
    for z in (-0.2, 0.3):                                           # a value held in a closure
        zc[0] = z
        dc = S.Decal(logo, 'left', 0.0, 0.5, 0.3, region=(lambda zz: (lambda P: P[:, 2] > zz))(z))
        img, hm, wm = S.decal_size(dc, tm.texel_m)
        assert same_hits(S.decal_hits(tm, dc, hm, wm), old_decal_hits(tm, dc, hm, wm))


def test_decal_hits_cache_cannot_be_changed(car, tm):
    S.clear_hit_cache()
    dc = decals(car)[0]
    img, hm, wm = S.decal_size(dc, tm.texel_m)
    idx, a, b = S.decal_hits(tm, dc, hm, wm)
    with pytest.raises(ValueError):
        idx[0] = 5
    idx2, _, _ = S.decal_hits(tm, dc, hm, wm)
    assert np.array_equal(idx, idx2)


def test_decal_hits_cache_stays_small(car, tm, monkeypatch):
    S.clear_hit_cache()
    monkeypatch.setattr(S, 'HIT_CACHE_BYTES', 200_000)
    dc = decals(car)[0]
    img, hm, wm = S.decal_size(dc, tm.texel_m)
    for k in range(30):
        S.decal_hits(tm, dc, hm, wm, 0.002 * k)
        assert S.hit_cache_bytes(tm) <= 200_000 or len(tm._hits) == 1


# ---------------------------------------------------------------- 2: the paint laid on the stock texture
def test_paint_canvas_same_as_before(car, tm):
    rng = np.random.default_rng(3)
    H, W = tm.H, tm.W
    base = (rng.random((H, W, 3)) * 255).astype(np.float32)
    shade = (0.6 + 0.4 * rng.random((H, W))).astype(np.float32)
    cols = rng.random((len(tm.yy), 3)) * 300 - 20                 # some outside 0..255, like a real design
    paint = np.zeros((H, W), bool); paint[tm.yy, tm.xx] = rng.random(len(tm.yy)) > 0.3
    paint2 = paint.copy(); paint2[tm.yy[:5000], tm.xx[:5000]] = True     # decals covering texels outside the paint
    paint3 = paint.copy(); paint3[::97, ::89] = True                         # (texels the texel map has none for)
    mem = {}
    for p in (paint, paint, paint2, paint, paint2, paint3, paint):
        assert np.array_equal(S._paint_canvas(tm, cols, base, p, shade, mem), old_paint_canvas(tm, cols, base, p, shade))
    assert np.array_equal(S._paint_canvas(tm, cols, base, paint, shade), old_paint_canvas(tm, cols, base, paint, shade))


# ---------------------------------------------------------------- 3: rims and tyres
def test_wheels_kept_same(car, monkeypatch):
    if not car.wheel_textures: pytest.skip('no rim texture')
    S._MEMO.clear(); S._MEMO['car'] = car
    said1, said2 = [], []
    d = dict(wheel_colour='#ff8800', tyre_colour='#202020')
    a = S.wheel_colours(car, d, said1.append)
    calls, real = [], S.recolour_wheels
    monkeypatch.setattr(S, 'recolour_wheels', lambda *a_, **k: calls.append(1) or real(*a_, **k))
    b = S.wheel_colours(car, dict(d), said2.append)
    assert not calls                                                  # not worked out again
    assert said1 == said2 and said1                                   # but the same said again
    assert a.keys() == b.keys() and all(a[k].tobytes() == b[k].tobytes() and a[k] is not b[k] for k in a)
    S._MEMO.clear()
    fresh = S.wheel_colours(car, d, lambda m: None)                   # (no car kept: worked out, same pictures)
    assert all(a[k].tobytes() == fresh[k].tobytes() for k in a)
    S._MEMO['car'] = car
    c = S.wheel_colours(car, dict(d, wheel_colour='#0088ff'), lambda m: None)
    assert calls and any(a[k].tobytes() != c[k].tobytes() for k in a)
    S._MEMO.clear()


# ---------------------------------------------------------------- 7: textures written side by side
def test_textures_written_side_by_side_same_files(tmp_path):
    rng = np.random.default_rng(5)
    imgs = {f't{k}.dds': Image.fromarray((rng.random((256, 256, 4)) * 255).astype(np.uint8), 'RGBA') for k in range(5)}
    imgs['p.png'] = Image.fromarray((rng.random((64, 64, 3)) * 255).astype(np.uint8))
    one, many = tmp_path / 'one', tmp_path / 'many'
    one.mkdir(); many.mkdir()
    for n, im in imgs.items(): S.write_texture(im, str(one / n), compress=True)
    S.write_textures([(im, str(many / n)) for n, im in imgs.items()], compress=True)
    for n in imgs:
        assert (one / n).read_bytes() == (many / n).read_bytes()


# ---------------------------------------------------------------- 7: the gaps between panels filled
def test_pad_texture_same_as_before_any_size():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from test_speed import old_pad_texture, panels
    rng = np.random.default_rng(11)
    for H, W in ((20, 13), (25, 30), (26, 26), (7, 90), (300, 257)):
        img = Image.fromarray((rng.random((H, W, 3)) * 255).astype(np.uint8))
        for m in (panels(H, W, 1), rng.random((H, W)) > 0.9, np.zeros((H, W), bool)):
            assert S.pad_texture(img, m).tobytes() == old_pad_texture(img, m).tobytes()


# ---------------------------------------------------------------- 6: the car got ready while the livery is set up
def warm_design():
    logo = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'starter_logos', 'ratty_racing_logo.jpg')
    return dict(S.DEFAULT_DESIGN, number='7', name='NIK', team='RATTY', win_enable=True, wheel_colour='#ff8800',
                logos=[dict(path=logo, place='doors', tint=False, bg='auto')])


def preview(d=None):
    said, views, info = [], {}, {}
    S.generate(SMALL_CAR, d or warm_design(), 'warm', log=said.append, views=views, info=info, write=False)
    return said, {k: v.tobytes() for k, v in views.items()}, {k: v for k, v in info.items() if k not in ('decals', 'serial')}


@pytest.fixture(scope='module')
def cold():
    S._MEMO.clear()
    return preview()


def test_warm_up_then_preview_same(cold, monkeypatch):
    S._MEMO.clear()
    assert S.warm_up(SMALL_CAR, warm_design())
    work = []
    for n in ('TexelMap', 'stock_analysis', '_view_geometry'):
        real = getattr(S, n)
        monkeypatch.setattr(S, n, (lambda r, n: lambda *a, **k: work.append(n) or r(*a, **k))(real, n))
    warm = preview()
    assert not [w for w in work if w != 'TexelMap']          # (glass texel maps may be made: not the body's)
    assert warm[0] == cold[0]                                  # it says the same, in the same order
    assert warm[1] == cold[1] and warm[2] == cold[2]           # and draws the same
    again = preview()
    assert any('same car as last time' in m for m in again[0]) and again[1] == cold[1]


def test_warm_up_stops_when_asked(cold):
    for n in (1, 2, 4):
        S._MEMO.clear()
        asked = []
        assert not S.warm_up(SMALL_CAR, warm_design(), stop=lambda: asked.append(1) or len(asked) > n)
        assert preview() == cold                               # a Preview after a half-done warm-up: the same


def test_preview_while_warming_up(cold):
    import threading
    S._MEMO.clear()
    th = threading.Thread(target=S.warm_up, args=(SMALL_CAR, warm_design()))
    th.start()
    time.sleep(0.3)
    got = preview()
    th.join()
    assert got[1] == cold[1] and got[2] == cold[2]


def test_warm_up_other_car_or_none():
    S._MEMO.clear()
    assert not S.warm_up(r'D:\ClaudeData\tmp\no_such_car', warm_design())       # never raises
    assert S.warm_up(SMALL_CAR, None)                                           # no design: model + textures only


# ---------------------------------------------------------------- the preview views drawn straight into bytes
def old_render_view(car, view, tex_imgs, tms=None, width=1000, bg=(235, 236, 240), layers=(), alpha=False):
    ss = 2 if width <= 1700 else 1
    texs = [np.asarray(im.convert('RGB')) for im in tex_imgs.values()]
    alphas = [None] * len(texs)
    for tm, arr in layers:
        texs.append(arr[..., :3]); alphas.append(arr[..., 3])
    Hp, Wp, ys, xs, Gt, tx, uv, tix, St = S._geometry(car, view, width, list(tex_imgs), S._layer_map(len(tex_imgs), layers))
    out = np.empty((Hp, Wp, 3), np.float32); out[:] = bg
    col = np.repeat(Gt[:, None].astype(np.float32), 3, 1)
    if len(tx):
        for k, tex in enumerate(texs):
            sel = np.nonzero(tix == k)[0]
            if not len(sel): continue
            H, W = tex.shape[:2]
            u = (uv[sel, 0] * W).astype(np.int64) % W; v = (uv[sel, 1] * H).astype(np.int64) % H
            c = tex[v, u].astype(np.float32) * St[sel, None].astype(np.float32)
            if alphas[k] is not None:
                al = alphas[k][v, u].astype(np.float32)[:, None] / 255
                c = col[tx[sel]] * (1 - al) + c * al
            col[tx[sel]] = c
    out[ys, xs] = col
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    if ss > 1: img = img.resize((width, Hp // ss), Image.LANCZOS)
    if alpha:
        cov = np.zeros((Hp, Wp), np.uint8); cov[ys, xs] = 255
        a = Image.fromarray(cov)
        if ss > 1: a = a.resize(img.size, Image.LANCZOS)
        img = Image.merge('RGBA', (*img.split(), a))
    return img


def test_render_view_same_as_before(car, tm):
    rng = np.random.default_rng(9)
    tex = {tm.tex: Image.fromarray((rng.random((tm.H, tm.W, 4)) * 255).astype(np.uint8), 'RGBA')}
    glass = [m for m in car.kn5.meshes if m.mat is not None and S.see_through(m.mat) and len(m.idx)][:2]
    layers = []
    if glass:
        g = S.texel_map(glass, 256, 256)
        layers = [(g, (rng.random((256, 256, 4)) * 255).astype(np.uint8))]
    for view in ('left', 'top', 'front'):
        for width, alpha, bg in ((900, True, (235, 236, 240)), (1800, False, (0, 0, 0))):
            new = S.render_view(car, view, tex, None, width, bg=bg, layers=layers, alpha=alpha)
            old = old_render_view(car, view, tex, None, width, bg=bg, layers=layers, alpha=alpha)
            assert new.mode == old.mode and new.tobytes() == old.tobytes()

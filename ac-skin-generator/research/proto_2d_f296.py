r"""Phase 0 of the 2D mode (research/Encrypted cars 2D livery painting.md): one hand-made test skin for a CSP-protected
car, painted on its 2D layout only - nothing of the protected model is read or changed.
Car: cf_ferrari_296_gt3. Uses the maker's own template skin ("Template": AO-shaded EXT_Skin_Colour + its alpha, which
keeps the carbon parts carbon) and, for where the numbers go, a real race skin (2023_GTWC_51_AF Corse).
Writes a NEW skin folder 'R4S 2D test' (refuses if it exists). Run:  python research/proto_2d_f296.py
"""
import json, os, shutil, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import skingen
import rattys4skin as R

CAR = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\cf_ferrari_296_gt3'
SK = os.path.join(CAR, 'skins')
OUT = os.path.join(SK, 'R4S 2D test')
TEX = 'EXT_Skin_Colour.dds'
BASE, ACC, ACC2, TXT = '#2a0a4a', '#9b3dff', '#ff6a00', '#ffffff'
LOGO = os.path.join(os.path.dirname(HERE), 'starter_logos', 'ratty_racing_logo.jpg')


def label(mask):
    """Islands of a mask (8-connected), via PIL's flood fill on a copy - slow-ish but simple for a one-off."""
    from collections import deque
    H, W = mask.shape
    lab = np.zeros((H, W), np.int32)
    n = 0
    small = mask[::4, ::4]                                # islands found on a quarter-size copy, then scaled up
    h, w = small.shape
    sl = np.zeros((h, w), np.int32)
    for y in range(h):
        row = small[y]
        for x in np.flatnonzero(row & (sl[y] == 0)):
            if sl[y, x]: continue
            n += 1; q = deque([(y, x)]); sl[y, x] = n
            while q:
                cy, cx = q.popleft()
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and small[ny, nx] and not sl[ny, nx]:
                            sl[ny, nx] = n; q.append((ny, nx))
    lab = np.kron(sl, np.ones((4, 4), np.int32))[:H, :W] * mask
    return lab, n


def main():
    if os.path.exists(OUT):
        sys.exit(f'{OUT} exists already - not touched')
    tpl = skingen.load_image(os.path.join(SK, 'Template', TEX)).convert('RGBA')
    race = skingen.load_image(os.path.join(SK, '2023_GTWC_51_AF Corse', TEX)).convert('RGBA')
    T = np.asarray(tpl).astype(np.float32)
    Rc = np.asarray(race).astype(np.float32)
    H, W = T.shape[:2]
    alpha = T[..., 3]
    lum = T[..., :3] @ np.array([0.299, 0.587, 0.114], np.float32)
    paint = (lum > 14) & (alpha > 8)                       # panels that take paint (alpha 0 = carbon stays carbon)
    ref = np.percentile(lum[paint], 95)
    S = np.clip(lum / ref, 0, 1.15)                        # the template's baked shading, kept

    # the livery in texture space: splinter camo (looks right whatever way a panel lies in the layout)
    v, u = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = u / W, v / H
    P = np.stack([np.full(u.size, 0.86, np.float32), (1 - v.ravel()) * 2.6, (0.5 - u.ravel()) * 5.2], 1)
    Nn = np.tile(np.array([1.0, 0, 0], np.float32), (u.size, 1))
    d = dict(skingen.DEFAULT_DESIGN, pattern='splinter_camo', base=BASE, accent=ACC, accent2=ACC2, text=TXT, halftone=False)
    col = np.zeros((H * W, 3), np.float32)
    sel = np.flatnonzero(paint.ravel())
    for c0 in range(0, len(sel), 1 << 20):
        s_ = sel[c0:c0 + (1 << 20)]
        col[s_] = skingen.pattern_colours(d, P[s_], Nn[s_], skingen.SwatchCar(), 0.15, 0.8, lambda m: None)
    col = col.reshape(H, W, 3)
    out = T.copy()
    hl = np.clip(S - 1, 0, None)[..., None]                 # highlights roll towards white a little
    painted = col * np.minimum(S, 1)[..., None] + (255 - col) * hl * 0.6
    out[..., :3] = np.where(paint[..., None], painted, T[..., :3])
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA')

    # number boards where the real race skin has its own: on both side panels (the upper one turned 180 degrees,
    # as in the race skin), plus the team name above each
    lab, n = label(lum > 14)
    areas = np.bincount(lab.ravel())
    # the race skin's two number boards (seen by eye on its texture): the upper side panel carries its board turned
    # 180 degrees, the lower one upright - refined to the board's white pixels
    boards = []
    white = Rc[..., :3].min(2) > 150                        # the boards are shaded too (about 170)
    for k, (ex0, ey0, ex1, ey1, upside) in enumerate(((687, 1250, 911, 1460, True), (687, 2255, 919, 2485, False))):
        win = white[ey0 - 30:ey1 + 30, ex0 - 30:ex1 + 30]
        ys, xs = np.nonzero(win)
        y0, y1 = (np.percentile(ys, [1, 99]) + ey0 - 30).astype(int); x0, x1 = (np.percentile(xs, [1, 99]) + ex0 - 30).astype(int)
        boards.append((k, x0, y0, x1, y1, upside))
    font_num = R.list_fonts().get('Racing: Russo One')
    font_team = R.list_fonts().get('Racing: Exo 2 Black Italic')
    for k, x0, y0, x1, y1, upside in boards:
        bw, bh = x1 - x0, y1 - y0
        b = Image.new('RGBA', (bw, bh), (0, 0, 0, 0)); bd = ImageDraw.Draw(b)
        bd.rounded_rectangle([0, 0, bw - 1, bh - 1], int(min(bw, bh) * 0.12), fill=(250, 250, 250, 255), outline=(155, 61, 255, 255),
                             width=max(4, bw // 40))
        num = skingen.text_image('101', int(bh * 0.7), (17, 17, 17), font_num)
        num.thumbnail((int(bw * 0.86), int(bh * 0.78)), Image.LANCZOS)
        b.alpha_composite(num, ((bw - num.width) // 2, (bh - num.height) // 2))
        team = skingen.text_image("RATTY'S RACING", int(bh * 0.3), (255, 255, 255), font_team, stroke=0.06, stroke_color=(20, 0, 40))
        team.thumbnail((int(bw * 1.6), int(bh * 0.32)), Image.LANCZOS)
        blk = Image.new('RGBA', (max(bw, team.width), bh + team.height + 20), (0, 0, 0, 0))
        blk.alpha_composite(team, ((blk.width - team.width) // 2, 0))
        blk.alpha_composite(b, ((blk.width - bw) // 2, team.height + 20))
        if upside: blk = blk.rotate(180)
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        oy = cy - (bh // 2 + team.height + 20) if not upside else cy - bh // 2
        img.alpha_composite(blk, (cx - blk.width // 2, oy))
        print(f'number board on island {k}: x {x0}-{x1}, y {y0}-{y1}, {"turned 180" if upside else "upright"}')

    # the Ratty logo on the roof (island 0 of the size order: the big plain panel)
    roof_k = np.argsort(areas)[::-1][1]
    ys, xs = np.nonzero(lab == roof_k)
    lg = Image.open(LOGO).convert('RGBA')
    sz = int(min(xs.max() - xs.min(), ys.max() - ys.min()) * 0.55)
    lg = lg.resize((sz, sz), Image.LANCZOS)
    m = Image.new('L', lg.size, 0); ImageDraw.Draw(m).ellipse([0, 0, sz - 1, sz - 1], fill=255); lg.putalpha(m)
    img.alpha_composite(lg, (int(xs.mean()) - sz // 2, int(ys.mean()) - sz // 2))
    img.putalpha(Image.fromarray(alpha.astype(np.uint8)))      # the template's alpha exactly (carbon parts)

    os.makedirs(OUT)
    skingen.write_dds(img, os.path.join(OUT, TEX), compress=True)
    for f in ('lumirank_font.zip',):
        shutil.copyfile(os.path.join(SK, 'Template', f), os.path.join(OUT, f))
    ini = open(os.path.join(SK, 'Template', 'ext_config.ini'), encoding='utf8', errors='ignore').read()
    open(os.path.join(OUT, 'ext_config.ini'), 'w', encoding='utf8').write(ini.replace('ROLE_0_TEXT = 296', 'ROLE_0_TEXT = 101'))
    json.dump({'skinname': 'R4S 2D test', 'drivername': 'Nicklearse101', 'country': '', 'team': "Ratty's Racing", 'number': 101},
              open(os.path.join(OUT, 'ui_skin.json'), 'w'), indent=4)
    lv = Image.new('RGBA', (64, 64), (0, 0, 0, 0)); ld = ImageDraw.Draw(lv)
    ld.ellipse([2, 2, 61, 61], fill=(42, 10, 74, 255), outline=(255, 106, 0, 255), width=3); ld.pieslice([2, 2, 61, 61], 200, 340, fill=(155, 61, 255, 255))
    lv.save(os.path.join(OUT, 'livery.png'))
    small = img.convert('RGB'); small.thumbnail((1024, 1024)); small.save(os.path.join(r'D:\ClaudeData\tmp\f296', 'r4s_2d_test_texture.png'))
    print('written:', OUT, sorted(os.listdir(OUT)))


if __name__ == '__main__':
    main()

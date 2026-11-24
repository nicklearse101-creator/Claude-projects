"""PhotoReal 'camera look' colour LUT for CSP/Pure (1024x32 strip, 32^3).

Layout (verified against Pure's Neutral.png): x = r + 32*b, y = g, value = i*255/31.
Pure applies it after tonemapping and gamma (display-space values 0..1), so all
grading below works on display values. Kept deliberately mild; strength is
controlled live by the "camera look" slider (ac.setPpColorGradingIntensity).

What it does, like a real camera/film rendering:
  - gentle film S-curve (slight toe lift so blacks are never pure 0, soft shoulder)
  - foliage greens: less saturated and nudged towards olive/yellow
  - sky blues: slightly less saturated
  - warm highlights, very slightly cool shadows
"""
import colorsys
import math
from pathlib import Path

N = 32


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def hue_weight(h_deg, centre, width):
    d = abs((h_deg - centre + 180) % 360 - 180)
    return math.exp(-(d / width) ** 2)


def grade(r, g, b):
    # 1. film curve on luminance, colour ratios kept
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    if lum > 1e-5:
        curved = lum + 0.12 * (smoothstep(0, 1, lum) - lum)  # mild S
        curved = 0.010 + curved * (0.992 - 0.010)             # toe lift / soft white
        k = curved / lum
        r, g, b = r * k, g * k, b * k
    else:
        r = g = b = 0.010

    # 2. hue-selective saturation
    h, s, v = colorsys.rgb_to_hsv(min(r, 1), min(g, 1), min(b, 1))
    hd = h * 360
    wg = hue_weight(hd, 110, 40)          # foliage greens
    wb = hue_weight(hd, 215, 30)          # sky blues
    s *= 1 - 0.15 * wg - 0.06 * wb
    hd -= 6 * wg                          # greens towards olive
    r, g, b = colorsys.hsv_to_rgb((hd % 360) / 360, s, v)

    # 3. split tone: warm highlights, slightly cool shadows
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    # peaks in bright midtones, fades out so whites stay white (white balance)
    wh = smoothstep(0.5, 0.8, lum) * (1 - smoothstep(0.9, 1.0, lum))
    ws = 1 - smoothstep(0.0, 0.25, lum)
    r *= 1 + 0.030 * wh - 0.010 * ws
    b *= 1 - 0.030 * wh + 0.020 * ws
    return tuple(min(1.0, max(0.0, c)) for c in (r, g, b))


def make_lut(path: Path):
    from PIL import Image
    im = Image.new("RGB", (N * N, N))
    px = im.load()
    for bi in range(N):
        for gi in range(N):
            for ri in range(N):
                c = grade(ri / (N - 1), gi / (N - 1), bi / (N - 1))
                px[ri + N * bi, gi] = tuple(round(v * 255) for v in c)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
    return path


if __name__ == "__main__":
    import sys
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("PhotoReal_LUT.png")
    print(make_lut(out))
    for c in [(0, 0, 0), (0.5, 0.5, 0.5), (1, 1, 1), (0.3, 0.5, 0.2), (0.5, 0.7, 0.95)]:
        print(c, "->", tuple(round(v, 3) for v in grade(*c)))

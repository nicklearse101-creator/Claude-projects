"""Number-plate textures for the car (export/ref/tex/plate_front.png, plate_rear.png), used by
blender/scripts/details_ref.py.

UK 1989 layout (BS AU 145a): plate 520 wide (made 125 mm high here to fill the car's 500 x 120 mm recesses), characters 79 mm high, 50 mm wide ("1" narrower), 11 mm apart, 33 mm
between the two groups, black on white (front) / yellow (rear). Charles Wright 1935 is not on this PC: Bahnschrift
Bold with each glyph stretched to the 50 x 79 mm cell stands in for it. The registration is made up (PLATE).
Run: .venv\\Scripts\\python.exe tools\\make_plates.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

PLATE = ("F160", "GTE")                 # made-up registration (F = Aug 1988 - Jul 1989)
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "export", "ref", "tex")
PX = 4                                  # pixels per mm
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"
# colours as the flat 4x4 swatches store them (material base colour x 255): plate_white / plate_yellow
BG = {"front": (217, 217, 210), "rear": (204, 153, 8)}
INK = (18, 18, 18)


def glyph(ch, font, h):
    """The character cropped to its ink and scaled to h pixels high (width scaled alike)."""
    im = Image.new("L", (font.size * 2, font.size * 2), 0)
    ImageDraw.Draw(im).text((font.size // 2, font.size // 4), ch, font=font, fill=255)
    im = im.crop(im.getbbox())
    return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)


def plate(kind):
    W, H = 520 * PX, 125 * PX
    im = Image.new("RGB", (W, H), BG[kind])
    font = ImageFont.truetype(FONT, 400)
    font.set_variation_by_name("Bold")
    ch_h, ch_w, gap, ggap = 79 * PX, 50 * PX, 11 * PX, 33 * PX
    x = (W - (7 * ch_w + 5 * gap + ggap)) // 2
    y = (H - ch_h) // 2
    for gi, grp in enumerate(PLATE):
        for ci, ch in enumerate(grp):
            g = glyph(ch, font, ch_h)
            if ch != "1":
                g = g.resize((ch_w, ch_h), Image.LANCZOS)
            im.paste(Image.new("RGB", g.size, INK), (x + (ch_w - g.width) // 2, y), g)
            x += ch_w + (gap if ci < len(grp) - 1 else 0)
        x += ggap
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"plate_{kind}.png")
    im.save(path)
    return path


if __name__ == "__main__":
    print([plate(k) for k in ("front", "rear")])

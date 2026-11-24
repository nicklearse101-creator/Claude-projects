"""Build the PhotoReal ppfilter for Assetto Corsa from the installed Pure filter.

PhotoReal = Pure's own `pure` ppfilter (ini + lua script) with photo-realistic
defaults. Pure's files are not redistributed here: this script reads them from
your AC install and writes the modified copies next to them, so re-run it after
a Pure update.

Writes:
  system/cfg/ppfilters/PhotoReal.ini
  system/cfg/ppfilters/pure_scripts/PhotoReal.lua

Usage:  python make_photoreal.py [AC_ROOT]
"""
import re
import sys
from pathlib import Path

AC_ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"D:\SteamLibrary\steamapps\common\assettocorsa")
PPF = AC_ROOT / "system" / "cfg" / "ppfilters"
NAME = "PhotoReal"

# ---------------------------------------------------------------- ini tweaks
# section -> {key: value}. Lens imperfections a real camera has, kept subtle.
INI_SET = {
    "ABOUT": {"AUTHOR": "PhotoReal (based on Pure by Peter Boese)"},
    "CHROMATIC_ABERRATION": {
        "ENABLED": "1",
        "LATERAL_DISPERSION": "0.0015,0.0015",
        "UNIFORM_DISPERSION": "0.0002,0.0002",
        "SAMPLES": "5",
    },
    "VIGNETTING": {"STRENGTH": "0.15", "FOV_DEPENDENCE": "0.5"},
}

# ---------------------------------------------------------------- lua tweaks
# (exact text in pure.lua, replacement). Each must match exactly once.
LUA_REPLACE = [
    # photo-realistic slider defaults to full (Pure ships 0.5)
    ('pure.script.ui.addSliderFloat("photo-realistic", 0.5, 0.0, 1.0)',
     'pure.script.ui.addSliderFloat("photo-realistic", 1.0, 0.0, 1.0)\n'
     '    pure.script.ui.addSliderFloat("photo saturation", 0.92, 0.5, 1.2)\n'
     '    pure.script.ui.addSliderFloat("photo warmth", 1.00, 0.9, 1.1)\n'
     '    pure.script.ui.addSliderFloat("haze", 0.5, 0.0, 1.0)\n'
     '    pure.script.ui.addSliderFloat("shadow depth", 0.2, 0.0, 0.6)'),
    # v2: deeper shadows in sunshine = less ambient fill relative to the sun
    ('pure.config.set("light.ambient.level",          (1-0.25*cam_sun_face) * (1 - 0.5 * photo_realistic^3), true)',
     'pure.config.set("light.ambient.level",          (1-0.25*cam_sun_face) * (1 - 0.5 * photo_realistic^3) * _shadow_k, true)'),
    ('pure.config.set("light.advanced_ambient_light", (1.0-0.90*cam_sun_face) * (1 - 0.5 * photo_realistic^2), true)',
     'pure.config.set("light.advanced_ambient_light", (1.0-0.90*cam_sun_face) * (1 - 0.5 * photo_realistic^2) * _shadow_k, true)'),
    # lens ghosts / afterimage: Pure goes very strong at photo-realistic=1
    ('pure.yebis.set("glareShapeGhostLuminance", 0.0 + 1.00*camera_effects)',
     'pure.yebis.set("glareShapeGhostLuminance", 0.0 + 0.35*camera_effects)'),
    ('pure.yebis.set("glareShapeAfterimageLuminance", 0.0 + 3.00*camera_effects)',
     'pure.yebis.set("glareShapeAfterimageLuminance", 0.0 + 1.00*camera_effects)'),
    ('pure.script.setAuthor("Peter Boese")',
     'pure.script.setAuthor("PhotoReal, based on Pure by Peter Boese")'),
    # live saturation / warmth from the sliders, every frame
    ('photo_realistic = pure.script.ui.getValue("photo-realistic")',
     'photo_realistic = pure.script.ui.getValue("photo-realistic")\n'
     '    _photo_hsb.saturation = pure.script.ui.getValue("photo saturation")\n'
     '    local w = pure.script.ui.getValue("photo warmth")\n'
     '    _photo_rgb.color = rgb(w, 1.0, 2.0 - w)\n'
     # shadow depth only applies in direct sunshine, not overcast
     '    local sunny = pure.mod.sun(0) * (1 - pure.world.getCloudShadow())\n'
     '    _shadow_k = 1 - pure.script.ui.getValue("shadow depth") * sunny\n'
     # v2 haze: Pure's clear-sky fog starts ~60 km out, so track-scale
     # distances get no aerial perspective. Pull the fog distance in
     # (log-scale towards 2.5 km); never thinner than Pure's own fog.
     '    local pfog = pure.world.getPureGammaFogTable()\n'
     '    local haze = pure.script.ui.getValue("haze")\n'
     '    if haze > 0 and pfog and pfog.distance then\n'
     '        local d = math.exp(math.lerp(math.log(math.max(1, pfog.distance)), math.log(2500), haze))\n'
     '        if d < pfog.distance then ac.setFogDistance(d) end\n'
     '    end'),
]

# Real photos are less saturated than AC's raw output; luminance is kept.
LUA_HEADER = """-- PhotoReal: generated from Pure's pure.lua by make_photoreal.py
local _photo_hsb = ac.ColorCorrectionHsb { hue = 0, saturation = 0.92, brightness = 1, keepLuminance = true }
ac.weatherColorCorrections[#ac.weatherColorCorrections + 1] = _photo_hsb
local _photo_rgb = ac.ColorCorrectionModulationRgb { color = rgb(1, 1, 1) }
ac.weatherColorCorrections[#ac.weatherColorCorrections + 1] = _photo_rgb
local _shadow_k = 1

"""


def patch_ini(text: str) -> str:
    out, section, seen = [], None, set()

    def flush():
        # add keys the section did not have
        if section in INI_SET:
            for k, v in INI_SET[section].items():
                if (section, k) not in seen:
                    out.append(f"{k}={v}")

    for line in text.splitlines():
        m = re.match(r"\s*\[([^\]]+)\]", line)
        if m:
            if out and out[-1] == "":
                out.pop()
                flush()
                out.append("")
            else:
                flush()
            section = m.group(1)
            out.append(line)
            continue
        k = line.split("=", 1)[0].strip()
        if section in INI_SET and k in INI_SET[section]:
            out.append(f"{k}={INI_SET[section][k]}")
            seen.add((section, k))
        else:
            out.append(line)
    flush()
    return "\n".join(out) + "\n"


def patch_lua(text: str) -> str:
    for old, new in LUA_REPLACE:
        n = text.count(old)
        if n != 1:
            sys.exit(f"pure.lua changed: expected 1 match, found {n}: {old!r}")
        text = text.replace(old, new)
    return LUA_HEADER + text


def main():
    src_ini = PPF / "pure.ini"
    src_lua = PPF / "pure_scripts" / "pure.lua"
    for p in (src_ini, src_lua):
        if not p.exists():
            sys.exit(f"Missing {p} - is Pure installed?")
    for src, dst, patch in ((src_ini, PPF / f"{NAME}.ini", patch_ini),
                            (src_lua, PPF / "pure_scripts" / f"{NAME}.lua", patch_lua)):
        eol = "\r\n" if b"\r\n" in src.read_bytes() else "\n"  # keep Pure's line endings
        dst.write_text(patch(src.read_text(encoding="utf-8")), encoding="utf-8", newline=eol)
    print(f"Wrote {PPF / (NAME + '.ini')}")
    print(f"Wrote {PPF / 'pure_scripts' / (NAME + '.lua')}")


if __name__ == "__main__":
    main()

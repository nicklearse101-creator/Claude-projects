"""ESCORT 16" data.acd: decrypt the 14" car's data.acd, change only what bigger wheels need, encrypt for the new folder name.
  tyres.ini   every compound: RADIUS and WIDTH x16/14, RIM_RADIUS 0.2032 (16"), ANGULAR_INERTIA x1.5 (bigger, heavier wheel)
  suspensions BASEY front -0.250 -> -0.290, rear -0.280 -> -0.345: wheel centres 40 / 65 mm lower against the body so the
              scaled tyres sit where today's do under the arches (the body ends up ~80 mm higher front, ~105 mm rear)
  lods.ini    kn5 file names -> ford_escort_mk2_tuned_16*
Everything else byte-identical."""
import re, struct, sys
from pathlib import Path
sys.path.insert(0, r"D:\Claude\setupcoach-tools\acd"); sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools")
import acd_decoder, acd_patch

S = 16.0 / 14.0
SRC = Path(r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\ford_escort_mk2_tuned")
DST = Path(r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\ford_escort_mk2_tuned_16")
d = acd_decoder.decrypt_acd(SRC / "data.acd", SRC.name)
rep = []


def sub(text, section_re, key, fn):
    out, cur = [], None
    nl = "\r\n" if "\r\n" in text else "\n"
    for line in text.split(nl):
        m = re.match(r"\s*\[([^\]]+)\]", line)
        if m:
            cur = m.group(1)
        k = re.match(rf"(\s*{key}\s*=\s*)([-0-9.]+)(.*)$", line)
        if k and cur and re.fullmatch(section_re, cur):
            new = fn(float(k.group(2)))
            rep.append(f"[{cur}] {key}: {k.group(2)} -> {new}")
            line = f"{k.group(1)}{new}{k.group(3)}"
        out.append(line)
    return nl.join(out)


T = r"(FRONT|REAR)(_\d+)?"
t = d["tyres.ini"]
t = sub(t, T, "RADIUS", lambda v: f"{v * S:.4f}")
t = sub(t, T, "RIM_RADIUS", lambda v: "0.2032")
t = sub(t, T, "WIDTH", lambda v: f"{v * S:.4f}")
t = sub(t, T, "ANGULAR_INERTIA", lambda v: f"{v * 1.5:.4f}")
d["tyres.ini"] = t
s = d["suspensions.ini"]
s = sub(s, "FRONT", "BASEY", lambda v: "-0.290")
s = sub(s, "REAR", "BASEY", lambda v: "-0.345")
d["suspensions.ini"] = s
d["lods.ini"] = d["lods.ini"].replace("ford_escort_mk2_tuned", "ford_escort_mk2_tuned_16")

# write with the original header and entry order, re-encrypted with the new folder's key
head, ents = acd_patch.entries((SRC / "data.acd").read_bytes())
key = acd_decoder.get_key(DST.name)
out = bytearray(head)
for name, _, _ in ents:
    raw = acd_patch.encrypt(d[name].encode("utf-8") if isinstance(d[name], str) else d[name], key)
    nb = name.encode("ascii")
    out += struct.pack("<i", len(nb)) + nb + struct.pack("<I", len(raw) // 4) + raw
(DST / "data.acd").write_bytes(bytes(out))
chk = acd_decoder.decrypt_acd(DST / "data.acd", DST.name)
assert set(chk) == set(d) and all(chk[n] == d[n] for n in d)
print("\n".join(rep)); print("written", DST / "data.acd", len(chk), "files")

"""Patch one file inside a car's data.acd without touching the others.

    python acd_patch.py <car_folder> <file_in_acd> <KEY>=<value>@<SECTION> ...

Every other entry is copied byte for byte. The patched entry is re-encrypted with the same per-file keystream the
decoder (setupcoach-tools/acd/acd_decoder.py) reverses; before writing, the unpatched text is re-encrypted and must
reproduce the original bytes exactly, else nothing is written. The old acd is kept as data.acd.BACKUP_<time>.
"""
import shutil
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, r"D:\Claude\setupcoach-tools\acd")
import acd_decoder  # noqa: E402


def entries(data):
    pos, out = 0, []
    head = b""
    if len(data) >= 8 and struct.unpack_from("<i", data, 0)[0] == -1111:
        head, pos = data[:8], 8
    while pos < len(data):
        start = pos
        n = struct.unpack_from("<i", data, pos)[0]; pos += 4
        name = data[pos:pos + n].decode("ascii"); pos += n
        c = struct.unpack_from("<I", data, pos)[0]; pos += 4
        raw = data[pos:pos + 4 * c]; pos += 4 * c
        out.append((name, data[start:pos], raw))
    return head, out


def encrypt(text_bytes, key):
    k = key.encode("ascii")
    raw = bytearray()
    for j, b in enumerate(text_bytes):
        raw += bytes(((b + k[j % len(k)]) % 256, 0, 0, 0))
    return bytes(raw)


def decrypt(raw, key):
    k = key.encode("ascii")
    return bytes((raw[g] - k[j % len(k)]) % 256 for j, g in enumerate(range(0, len(raw), 4)))


def set_value(text, section, key, value):
    lines = text.split("\r\n") if "\r\n" in text else text.split("\n")
    nl = "\r\n" if "\r\n" in text else "\n"
    cur, hits = None, 0
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("[") and "]" in s:
            cur = s[1:s.index("]")]
        elif cur == section and s.split("=")[0].strip() == key:
            rest = line[line.index("=") + 1:]
            comment = rest[rest.index(";"):] if ";" in rest else ""
            old = rest.split(";")[0].strip()
            lines[i] = f"{key}={value}" + ("\t" + comment if comment else "")
            hits += 1
            print(f"  [{section}] {key}: {old} -> {value}")
    assert hits == 1, f"[{section}] {key}: {hits} matches"
    return nl.join(lines)


def main(car, fname, changes):
    car = Path(car)
    key = acd_decoder.get_key(car.name)
    acd = car / "data.acd"
    data = acd.read_bytes()
    head, ents = entries(data)
    out = bytearray(head)
    done = False
    for name, blob, raw in ents:
        if name != fname:
            out += blob; continue
        plain = decrypt(raw, key)
        assert encrypt(plain, key) == raw, "re-encryption does not reproduce the original - not writing"
        text = plain.decode("utf-8")
        for ch in changes:
            kv, sec = ch.split("@"); k, v = kv.split("=")
            text = set_value(text, sec, k, v)
        new = encrypt(text.encode("utf-8"), key)
        nb = name.encode("ascii")
        out += struct.pack("<i", len(nb)) + nb + struct.pack("<I", len(new) // 4) + new
        done = True
    assert done, f"{fname} not in the acd"
    bk = car / f"data.acd.BACKUP_{time.strftime('%Y%m%d_%H%M')}"
    shutil.copy2(acd, bk)
    acd.write_bytes(bytes(out))
    check = acd_decoder.decrypt_acd(acd, car.name)
    old = acd_decoder.decrypt_acd(bk, car.name)
    assert set(check) == set(old) and all(check[n] == old[n] for n in check if n != fname)
    print("written; backup", bk.name)
    return check[fname]


def put_file(car, fname, text):
    """Add (or replace) a whole file inside the acd; every other entry copied byte for byte."""
    car = Path(car)
    key = acd_decoder.get_key(car.name)
    acd = car / "data.acd"
    head, ents = entries(acd.read_bytes())
    new = encrypt(text.encode("utf-8"), key)
    nb = fname.encode("ascii")
    blob = struct.pack("<i", len(nb)) + nb + struct.pack("<I", len(new) // 4) + new
    out = bytearray(head); done = False
    for name, b, raw in ents:
        if name == fname:
            out += blob; done = True
        else:
            out += b
    if not done:
        out += blob
    bk = car / f"data.acd.BACKUP_{time.strftime('%Y%m%d_%H%M')}"
    shutil.copy2(acd, bk)
    acd.write_bytes(bytes(out))
    check = acd_decoder.decrypt_acd(acd, car.name); old = acd_decoder.decrypt_acd(bk, car.name)
    assert check[fname] == text and all(check[n] == old[n] for n in old if n != fname)
    print("written", fname, "; backup", bk.name)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])

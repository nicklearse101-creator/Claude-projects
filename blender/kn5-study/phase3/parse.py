import re, json, os, sys
def blocks(txt):
    out = []
    for m in re.finditer(r'\{\{\s*Infobox (automobile|Formula One car|racing car|motor ?racing car)', txt, re.I):
        i = m.start(); depth = 0; j = i
        while j < len(txt):
            if txt.startswith('{{', j): depth += 1; j += 2; continue
            if txt.startswith('}}', j):
                depth -= 1; j += 2
                if depth == 0: break
                continue
            j += 1
        out.append(txt[i:j])
    return out
def field(b, name):
    m = re.search(r'\n\s*\|\s*' + name + r'\s*=(.*?)(?=\n\s*\|\s*[a-z_ ]+\s*=|\n\}\})', b, re.S | re.I)
    return m.group(1).strip() if m else ''
def mm_values(s):
    vals = []
    s = re.sub(r'<ref[^>]*/>|<ref.*?</ref>', '', s, flags=re.S)
    for m in re.finditer(r'\{\{\s*(?:convert|cvt)\s*\|\s*([\d.,]+)\s*\|\s*(mm|cm|m|in)\b', s, re.I):
        v = float(m.group(1).replace(',', '')); u = m.group(2).lower()
        vals.append(round(v * {'mm': 1, 'cm': 10, 'm': 1000, 'in': 25.4}[u]))
    if not vals:
        for m in re.finditer(r'([\d.,]{3,6})\s*(mm|in)\b', s):
            v = float(m.group(1).replace(',', '')); vals.append(round(v * (25.4 if m.group(2) == 'in' else 1)))
    return vals
res = {}
for fn in sorted(os.listdir('wiki')):
    car = fn[:-4]; txt = open('wiki/' + fn, encoding='utf-8').read()
    bl = []
    for b in blocks(txt):
        d = {'name': re.sub(r'\s+', ' ', field(b, 'name'))[:50], 'prod': re.sub(r'\s+', ' ', field(b, 'production'))[:40]}
        for k in ('length', 'width', 'height', 'wheelbase', 'front_track|track_front|track ?\(front\)|front track', 'rear_track|track_rear|rear track'):
            d[k.split('|')[0]] = mm_values(field(b, k))
        bl.append(d)
    res[car] = bl
json.dump(res, open('wiki_parsed.json', 'w'), indent=0)
for car, bl in res.items():
    print('##', car)
    for i, d in enumerate(bl):
        print(f"  [{i}] {d['name']} | {d['prod']} | L{d['length'][:6]} W{d['width'][:4]} H{d['height'][:4]} WB{d['wheelbase'][:4]} TF{d['front_track'][:3]} TR{d['rear_track'][:3]}")

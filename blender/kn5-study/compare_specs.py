"""Compare measure.py output with published specs (specs.json). Prints a markdown table of model - spec (mm).

    python compare_specs.py measures.json specs.json
"""
import sys, json
M = {r['car']: r for r in json.load(open(sys.argv[1]))}
S = json.load(open(sys.argv[2]))
keys = ['length', 'width', 'height', 'wheelbase', 'track_f', 'track_r']
print('| car | ' + ' | '.join(keys) + ' | var |')
print('|---|' + '---|' * (len(keys) + 1))
summary = {k: [] for k in keys}
for car, s in S.items():
    if car.startswith('_') or car not in M: continue
    m = M[car]; cells = []
    for k in keys:
        if k in m and k in s:
            d = m[k] - s[k]; cells.append(f'{m[k]:.0f} ({d:+.0f})'); summary[k].append((car, d))
        else:
            cells.append('-')
    print(f'| {car} | ' + ' | '.join(cells) + f" | {s.get('var', '')} |")
print()
for k in keys:
    v = [abs(d) for c, d in summary[k]]
    if v: print(f'{k}: median |diff| {sorted(v)[len(v)//2]:.0f} mm, max {max(v):.0f}')

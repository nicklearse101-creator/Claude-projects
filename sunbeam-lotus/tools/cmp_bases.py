import os, sys
sys.path.insert(0, r'D:\Claude\setupcoach-tools\acd')
import acd_decoder
CARS = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'
def norm(b):
    b = b.replace(b'\r\n', b'\n')
    return b'\n'.join(l.rstrip() for l in b.split(b'\n')).strip()
def load(car):
    d = os.path.join(CARS, car, 'data')
    if os.path.isdir(d):
        return {f.lower(): open(os.path.join(d, f), 'rb').read() for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))}, 'data folder'
    r = acd_decoder.decrypt_acd(__import__('pathlib').Path(CARS, car, 'data.acd'), car)
    if isinstance(r, dict):
        return {k.lower(): (v if isinstance(v, bytes) else v.encode('latin-1')) for k, v in r.items()}, 'data.acd'
    return {k.lower(): (v if isinstance(v, bytes) else v.encode('latin-1')) for k, v in r}, 'data.acd'
def cmp(a, b):
    A, sa = load(a); B, sb = load(b)
    same = sorted(f for f in A if f in B and norm(A[f]) == norm(B[f]))
    chg = sorted(f for f in A if f in B and f not in same)
    print(f'== {a} ({len(A)}, {sa}) vs {b} ({len(B)}, {sb})')
    print(f'  identical {len(same)}: {same}')
    print(f'  changed   {len(chg)}: {chg}')
    print(f'  added     {len(set(A)-set(B))}: {sorted(set(A)-set(B))}')
    print(f'  removed   {len(set(B)-set(A))}: {sorted(set(B)-set(A))}')
for a, b in [('talbot_sunbeam_lotus_81_works', 'ks_ford_escort_mk1'),
             ('talbot_sunbeam_lotus_81_works', 'talbot_sunbeam_lotus_lhd_stock'),
             ('talbot_sunbeam_lotus_lhd_stock', 'ks_ford_escort_mk1')]:
    try: cmp(a, b)
    except Exception as e: print('ERR', a, b, repr(e))

import os, hashlib, collections
C = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'
def h(p):
    m = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): m.update(b)
    return m.hexdigest()
def tree(car):
    r = os.path.join(C, car); out = {}
    for d, _, fs in os.walk(r):
        for f in fs:
            p = os.path.join(d, f); rel = os.path.relpath(p, r).lower()
            if rel == 'data.acd' or rel.startswith('data' + os.sep): continue
            out[rel] = h(p)
    return out
A = tree('talbot_sunbeam_lotus_81_works'); B = tree('talbot_sunbeam_lotus_lhd_stock')
top = lambda k: k.split(os.sep)[0] if os.sep in k else '(root files)'
stats = collections.defaultdict(lambda: [0, 0, 0, 0])
for k in set(A) | set(B):
    s = stats[top(k)]
    if k in A and k in B: s[0 if A[k] == B[k] else 1] += 1
    elif k in A: s[2] += 1
    else: s[3] += 1
print(f'{"folder":<16}{"same":>6}{"changed":>9}{"added":>7}{"removed":>9}')
for t in sorted(stats): print(f'{t:<16}' + ''.join(f'{v:>{w}}' for v, w in zip(stats[t], (6, 9, 7, 9))))
tot = [sum(s[i] for s in stats.values()) for i in range(4)]
print(f'{"TOTAL":<16}' + ''.join(f'{v:>{w}}' for v, w in zip(tot, (6, 9, 7, 9))))
print('root changed/added:', sorted(k for k in A if os.sep not in k and A.get(k) != B.get(k)))
print('root removed:', sorted(k for k in B if os.sep not in k and k not in A))

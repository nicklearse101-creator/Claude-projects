import numpy as np, sys
for c in sys.argv[1:]:
    L = [l.replace('<<', '').split() for l in open(f'rd_{c}.txt') if l[0] in '+-']
    v = np.array([abs(float(l[3])) for l in L]); n = np.array([int(l[-1]) for l in L])
    print(c, 'mean|err| cm', round((v * n).sum() / n.sum(), 2), 'bins>2cm', int((v > 2).sum()), '/', len(v))

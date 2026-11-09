"""Try the kn5 reader on every installed car and summarise failures.
python tests/scan_all_cars.py [CARS_DIR]"""
import glob, os, struct, sys, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kn5
from skingen import find_main_kn5

root = sys.argv[1] if len(sys.argv) > 1 else r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'
kinds = collections.defaultdict(list)
n = 0
for c in sorted(glob.glob(os.path.join(root, '*', ''))):
    car = os.path.basename(os.path.dirname(c))
    try: p = find_main_kn5(c)
    except Exception: continue
    n += 1
    try:
        kn5.KN5(p, load_textures=False)
    except Exception as e:
        head = open(p, 'rb').read(10)
        ver = struct.unpack_from('<i', head, 6)[0] if len(head) >= 10 else None
        size = os.path.getsize(p)
        kinds[f'{head[:6]!r} v{ver} {type(e).__name__}'].append(f'{car} ({size // 1024} KB)')
print(f'{n} cars, {sum(len(v) for v in kinds.values())} failed')
for k, v in kinds.items():
    print(f'\n{k}: {len(v)}')
    for x in v: print('   ', x)

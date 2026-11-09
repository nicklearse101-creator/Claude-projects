import sys, time, os, shutil
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from skingen import *
car_dir, out_root, prev = sys.argv[1], sys.argv[2], sys.argv[3]
d = dict(DEFAULT_DESIGN); d.update(wheel_colour='#7020d2', lens_colour='#ffd21f', beam_colour='#ffe066', logo=r'D:\Claude\Claude-\lacetti-ratty-skin\ratty_racing_logo.jpg', name='NICKLEARSE101')
if len(sys.argv) > 4: d['pattern'] = sys.argv[4]
t = time.time()
name = 'gen_test'
if os.path.exists(os.path.join(out_root, name)): shutil.rmtree(os.path.join(out_root, name))
generate(car_dir, d, name, out_root=out_root, preview_path=prev)
print('secs', round(time.time() - t))

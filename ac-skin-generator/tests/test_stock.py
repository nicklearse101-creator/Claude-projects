import sys, time
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from skingen import *
car_dir = sys.argv[1]; skin = sys.argv[2]; out = sys.argv[3]
t = time.time()
car = Car(car_dir)
tms, imgs = {}, {}
for tex in car.body_textures:
    im = car.stock_texture(tex, skin)
    tms[tex] = TexelMap(car.meshes_for(tex), *im.size)
    imgs[tex] = im
preview_sheet(car, imgs, tms).save(out)
print('secs', time.time() - t)

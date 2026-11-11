"""Generate with Nik's saved app settings (design + logo library) and save every preview view.
python tests/nik_test.py CAR OUT_DIR [key=value ...]     e.g. win_banner_height=0.2"""
import json, os, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings; warnings.filterwarnings('ignore')
import skingen

car, out = sys.argv[1], sys.argv[2]
root = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'
app = os.path.join(os.environ['APPDATA'], 'Rattys4SkinGenerator')
d = dict(skingen.DEFAULT_DESIGN)
try:
    s = json.load(open(os.path.join(app, 'settings.json')))
    d.update({k: v for k, v in s.items() if k in d})
    if s.get('use_wheels'): d['wheel_colour'] = s.get('wheel_colour')
    if s.get('use_lens'): d['lens_colour'] = s.get('lens_colour')
    lib = json.load(open(os.path.join(app, 'logos.json')))
    d['logos'] = [dict(path=os.path.join(app, 'logos', l['file']), place=l['place'], tint=l.get('tint'), bg=l.get('bg', 'auto'))
                  for l in lib]
    d['logos'].append(dict(path=os.path.join(app, 'logos', 'ratty_racing_logo.jpg'), place='front_wings', tint=False))
except Exception as e:
    print('settings not read:', e)
d['beam_colour'] = None     # cast-light option removed from the app
if d.get('pattern') == 'picture' and not d.get('pattern_image'): d['pattern'] = 'sweep'
d.setdefault('logos', [])
if not d['logos']:
    d['logos'] = [dict(path=os.path.join(app, 'logos', 'ratty_racing_logo.jpg'), place='front_wings', tint=False)]
for kv in sys.argv[3:]:
    k, v = kv.split('=', 1)
    try: v = json.loads(v)
    except ValueError: pass
    d[k] = v
os.makedirs(out, exist_ok=True)
dst = os.path.join(out, car)
shutil.rmtree(dst, ignore_errors=True)
t = time.time()
views = {}
res = skingen.generate(os.path.join(root, car), d, 'nik_test', out_root=dst, resolution=4096 if d.get('hires', True) else None,
                       views=views, preview_path=os.path.join(out, car + '_sheet.png'))
for k, im in views.items():
    im.save(os.path.join(out, f'{car}_{k}.png'))
if os.environ.get('ZOOM'):      # big side / front / rear views for close checks
    out_dir, sheet, car_o, tms, tex_out = res
    for v in os.environ['ZOOM'].split(','):
        skingen.render_view(car_o, v, tex_out, tms, 3200, layers=getattr(skingen, 'LAST_LAYERS', ())).save(os.path.join(out, f'{car}_{v}_big.png'))
print('secs', round(time.time() - t))

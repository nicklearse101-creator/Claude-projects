"""Make one skin with a fixed design and write a fingerprint of every file it makes, to check that a change to the
app's look leaves the skins exactly the same (the files generate() writes + the app's generator_preview.png).
python tests/same_output.py OUT_JSON      (works in D:/ClaudeData/tmp/r4s_same)"""
import hashlib, json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen
import rattys4skin

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAR = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\talbot_sunbeam_lotus_81_works_backup_v6'
TMP = r'D:\ClaudeData\tmp\r4s_same\out'

d = dict(skingen.DEFAULT_DESIGN)
d.update(win_enable=True, lens_colour='#ffd21f', number='101', team='RATTY RACING', name='NICKLEARSE101',
         logos=[dict(path=os.path.join(HERE, 'starter_logos', 'ratty_racing_logo.jpg'), place='doors', tint=False, bg='auto')])
shutil.rmtree(TMP, ignore_errors=True); os.makedirs(TMP)
views = {}
out, *_ = skingen.generate(CAR, d, 'same_test', out_root=TMP, views=views, info={}, write=True, log=lambda *a: None)
sums = {}
for root, _, files in os.walk(out):
    for f in files:
        p = os.path.join(root, f)
        sums[os.path.relpath(p, out).replace('\\', '/')] = hashlib.sha256(open(p, 'rb').read()).hexdigest()
sheet = rattys4skin.App.compose(views)
sums['generator_preview.png (pixels)'] = hashlib.sha256(sheet.mode.encode() + str(sheet.size).encode() + sheet.tobytes()).hexdigest()
json.dump(sums, open(sys.argv[1], 'w'), indent=1, sort_keys=True)
print(len(sums), 'files fingerprinted ->', sys.argv[1])

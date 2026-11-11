"""Fill starter_logos/ (the logos that come with the installer) from Nik's own logo library.
Identical files are kept once. The folder is not kept in git (brand logos); build.py bundles it.
Run:  python make_starter_logos.py"""
import hashlib, json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(os.environ['APPDATA'], 'Rattys4SkinGenerator')
OUT = os.path.join(HERE, 'starter_logos')


def main():
    lib = json.load(open(os.path.join(APP, 'logos.json'), encoding='utf8'))
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    seen, out = set(), []
    for l in lib:
        src = os.path.join(APP, 'logos', l.get('file', ''))
        if not os.path.isfile(src): continue
        h = hashlib.sha1(open(src, 'rb').read()).hexdigest()
        if h in seen: continue
        seen.add(h)
        shutil.copyfile(src, os.path.join(OUT, l['file']))
        out.append(dict(file=l['file'], name=l.get('name') or os.path.splitext(l['file'])[0]))
    json.dump(out, open(os.path.join(OUT, 'starter.json'), 'w', encoding='utf8'), indent=1)
    mb = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)) / 1e6
    print(f'{len(out)} starter logos ({mb:.0f} MB) in {OUT}')


if __name__ == '__main__':
    main()

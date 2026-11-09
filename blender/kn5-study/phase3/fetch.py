fix = {'ks_alfa_romeo_gta':'Alfa Romeo 105/115 Series Coupés','ks_maserati_quattroporte':'Maserati Quattroporte VI',
'ks_mercedes_190_evo2':'Mercedes-Benz W201','bmw_1m':'BMW 1M','bmw_m3_e92':'BMW M3 (E90)',
'streetcarpack_subaru_impreza_22b':'Subaru Impreza (first generation)','rr_phantom':'Rolls-Royce Phantom VIII',
'ks_ferrari_312_67':'Ferrari 312','bg_lotus_carlton':'Lotus Carlton'}
import subprocess, json, urllib.parse, os, time
L = []
for line in open('titles.tsv', encoding='utf-8'):
    c, t = line.rstrip('\n').split('\t'); L.append(f'{c}\t{fix.get(c, t)}')
open('titles.tsv', 'w', encoding='utf-8').write('\n'.join(L) + '\n')
for line in L:
    car, t = line.split('\t'); fn = f'wiki/{car}.txt'
    if os.path.exists(fn): continue
    url = 'https://en.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=content&rvslots=main&redirects=1&format=json&titles=' + urllib.parse.quote(t)
    for attempt in range(6):
        r = subprocess.run(['curl', '-s', '-A', 'kn5-study/1.0 (personal research)', url], capture_output=True)
        try: d = json.loads(r.stdout); break
        except Exception: time.sleep(5 * (attempt + 1))
    else: print(car, 'FAILED'); continue
    pg = next(iter(d['query']['pages'].values()))
    txt = pg.get('revisions', [{}])[0].get('slots', {}).get('main', {}).get('*', '')
    if txt: open(fn, 'w', encoding='utf-8').write(txt)
    print(car, pg.get('title').encode('ascii','replace').decode(), len(txt), flush=True); time.sleep(2)

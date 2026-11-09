import json
W = json.load(open('wiki_parsed.json'))
titles = dict(l.rstrip('\n').split('\t') for l in open('titles.tsv', encoding='utf-8'))
# car: (infobox block, {field: value index}, variant note)
pick = {
 'abarth500': (0, {}, 'Fiat 500 base body; Abarth bumpers ~110 mm longer'),
 'adc_mazda_mx5_na': (0, {}, 'road car'), 'alfa_romeo_75_gruppo_a_s1': (0, {}, 'Group A race car'),
 'alfa_romeo_giulietta_qv': (0, {}, 'road car'), 'bdb_chevrolet_corvette_c6': (0, {}, 'road car (base C6)'),
 'bdb_mazda_rx7_fc3s': (2, {}, 'road car'), 'bdb_volvo_850r': (0, {}, 'road car (saloon)'),
 'bg_lotus_carlton': (0, {}, 'road car'), 'bmw_z4': (0, {}, 'road car'),
 'chevy_belair_1957': (2, {}, '1955-57 Bel Air'), 'citroen_saxo_cup': (0, {}, 'Saxo Cup race car'),
 'cup_dacia_sandero': (2, {}, 'Sandero II cup car'), 'ddm_daihatsu_copen_street': (1, {}, 'road car'),
 'ford_anglia_1966_s1': (6, {}, '105E'), 'ford_escort_mk2_rally_spec': (2, {}, 'Mk2 rally car (arches)'),
 'ford_sierra_cosworth_rs500_dtm_90s': (0, {}, 'Group A/DTM race car'), 'j8_honda_nsx_na1_type_r': (0, {}, 'road car'),
 'j8_mitsubishi_gto_twin_turbo_91': (0, {}, 'road car'), 'ks_alfa_33_stradale': (0, {}, 'road car'),
 'ks_alfa_giulia_qv': (0, {}, 'road car (QV wider arches)'), 'ks_alfa_mito_qv': (0, {}, 'road car'),
 'ks_alfa_romeo_155_v6': (0, {}, 'DTM race car (road 155 figures)'), 'ks_alfa_romeo_4c': (0, {'width': 1}, 'road car'),
 'ks_alfa_romeo_gta': (1, {}, 'Giulia Sprint GT body'), 'ks_audi_a1s1': (1, {}, 'road car'),
 'ks_audi_r8_plus': (0, {}, 'road car'), 'ks_bmw_m4': (1, {}, 'road car'), 'ks_corvette_c7_stingray': (0, {}, 'road car'),
 'ks_ferrari_250_gto': (0, {}, 'road car'), 'ks_ferrari_288_gto': (0, {}, 'road car'), 'ks_ferrari_488_gtb': (0, {}, 'road car'),
 'ks_ferrari_812_superfast': (0, {}, 'road car'), 'ks_ford_gt40': (0, {}, 'race car'), 'ks_ford_mustang_2015': (0, {}, 'road car'),
 'ks_lamborghini_aventador_sv': (0, {}, 'road car (SV)'), 'ks_lamborghini_countach': (0, {'width': 1}, '5000 QV width'),
 'ks_lamborghini_huracan_performante': (0, {}, 'Huracan base body; Performante ~45 mm longer'),
 'ks_lamborghini_miura_sv': (0, {}, 'road car'), 'ks_maserati_levante': (0, {}, 'road car'),
 'ks_maserati_quattroporte': (6, {}, 'road car'), 'ks_mazda_miata': (0, {}, 'road car'), 'ks_mazda_rx7_spirit_r': (3, {}, 'road car'),
 'ks_mclaren_570s': (0, {}, 'road car'), 'ks_mercedes_190_evo2': (0, {}, 'W201 base; Evo II wider arches'),
 'ks_nissan_370z': (0, {}, 'road car'), 'ks_nissan_gtr': (0, {}, 'road car'), 'ks_nissan_skyline_r34': (5, {}, 'road car'),
 'ks_pagani_huayra_bc': (0, {}, 'Huayra base; BC longer'), 'ks_porsche_718_cayman_s': (0, {}, 'road car'),
 'ks_porsche_911_gt3_rs': (3, {}, '991 GT3 (RS wider: 1880)'), 'ks_porsche_917_k': (0, {'length': 1, 'width': 1, 'height': 1}, '917K'),
 'ks_porsche_991_carrera_s': (0, {}, 'road car'), 'ks_porsche_cayenne': (3, {}, 'road car'), 'ks_porsche_panamera': (2, {}, 'road car'),
 'ks_toyota_celica_st185': (5, {'length': 2, 'width': 2, 'height': 2}, 'GT-Four'), 'ks_toyota_gt86': (1, {}, 'road car'),
 'ks_toyota_supra_mkiv': (4, {}, 'road car'), 'ktm_xbow_r': (0, {}, 'open road car'), 'lotus_elise_sc': (2, {}, 'S2'),
 'lotus_esprit_race': (5, {}, 'race car on S4 body?'), 'lotus_evora_s': (0, {}, 'road car'), 'mclaren_mp412c': (0, {}, 'road car'),
 'mercedes_sls': (0, {}, 'road car'), 'opelmanta_400': (2, {}, 'Manta B (400 has wide arches)'),
 'pagani_zonda_r': (0, {}, 'Zonda family'), 'pb_shb_gt500_68': (1, {}, '1965-68 Mustang WB'), 'rr_phantom': (0, {}, 'road car (SWB)'),
 'rw_citroenbx_4tc_grb': (0, {}, 'BX base; 4TC is longer'), 'shelby_cobra_427sc': (3, {}, 'MkIII'),
 'streetcarpack_honda_s2000_ap2': (2, {}, 'road car'), 'streetcarpack_mazda_rx7_fd3s': (3, {}, 'road car'),
 'streetcarpack_mitsubishi_lancer_evo_gsr': (6, {}, 'Evo VI'), 'streetcarpack_subaru_impreza_22b': (1, {}, 'GC8 base; 22B wider (1770)'),
 'streetcarpack_toyota_mr2_sw20': (2, {}, 'road car'), 'talbot_sunbeam_lotus_lhd_stock': (0, {}, 'road car'),
 'tg_beetle_cup': (0, {}, 'Beetle Cup race car'), 'traffic_aegis_suzuki_alto_works': (9, {'height': 2}, 'Alto Works (8th gen)'),
 'traffic_volvo_v70': (2, {}, 'V70 II'), 'vaz2106club': (0, {}, 'road car'), 'volvo_745_malaska': (1, {'length': 1, 'height': 1}, '740 estate'),
}
manual = {
 'bmw_1m': dict(length=4380, width=1803, height=1420, wheelbase=2660, src='BMW press data (from memory, unverified)', var='road car'),
 'ks_porsche_918_spyder': dict(length=4643, width=1940, height=1167, wheelbase=2730, src='Wikipedia Porsche 918 Spyder', var='road car'),
 'ks_mclaren_p1': dict(length=4588, wheelbase=2670, src='Wikipedia McLaren P1', var='road car'),
 'nohesi_traffic_tesla_model_3': dict(width=1849, wheelbase=2875, src='Wikipedia Tesla Model 3', var='traffic car'),
 'ks_mazda_787b': dict(length=4782, width=1994, height=1003, wheelbase=2662, src='Wikipedia / Ultimatecarpage', var='race car'),
 'ks_mclaren_f1_gtr': dict(length=4287, width=1820, wheelbase=2718, track_f=1558, track_r=1488, src='auto-data.net / McLaren 1995 GTR spec sheet', var='1995 GTR'),
 'ks_lotus_25': dict(wheelbase=2286, track_f=1346, track_r=1372, src='supercars.net (motor-car.net says WB 2311)', var='single-seater'),
 'ks_lotus_72d': dict(wheelbase=2540, track_f=1524, track_r=1626, src='supercars.net (1970 car; 72D tracks unverified)', var='single-seater'),
 'lotus_49': dict(wheelbase=2413, track_f=1524, track_r=1549, src='Wikipedia Lotus 49', var='single-seater'),
 'lotus_98t': dict(wheelbase=2720, track_f=1816, track_r=1620, src='Wikipedia Lotus 98T', var='single-seater'),
 'ferrari_312t': dict(length=4143, width=2030, wheelbase=2518, track_f=1510, track_r=1530, src='f1technical / Ultimatecarpage', var='single-seater'),
 'ks_ferrari_312_67': dict(wheelbase=2400, src='f1technical / flyinglap (tracks disputed)', var='single-seater'),
 'ks_ferrari_f2004': dict(length=4545, src='Wikipedia Ferrari F2004', var='single-seater'),
 'ks_ferrari_sf70h': dict(length=5000, width=2000, wheelbase=3594, src='Wikipedia Ferrari SF70H (lapmeta: WB 3581)', var='single-seater'),
 'ks_maserati_250f_6cyl': dict(wheelbase=2280, src='Wikipedia Maserati 250F', var='single-seater'),
 'tatuusfa1': dict(wheelbase=2650, track_f=1490, track_r=1455, src='Wikipedia Tatuus FA010', var='single-seater'),
 'ks_lotus_3_eleven': dict(length=4120, width=1860, height=1200, src='Wikipedia Lotus 3-Eleven', var='open road/race car'),
}
S = {}
for car, (bi, idx, var) in pick.items():
    b = W[car][bi]; e = {}
    for k in ('length', 'width', 'height', 'wheelbase'):
        v = b[k]; i = idx.get(k, 0)
        if v: e[k] = v[min(i, len(v) - 1)]
    e['src'] = f'Wikipedia "{titles[car]}" infobox'; e['var'] = var
    S[car] = e
S.update(manual)
json.dump(S, open('specs_new.json', 'w'), indent=1, ensure_ascii=False)
print(len(S), 'specs;', sum(1 for e in S.values() if 'length' in e), 'with length')

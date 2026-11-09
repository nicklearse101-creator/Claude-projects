"""Reverse-engineer an AC car model from its .kn5: structure, topology, smoothing, UVs, materials, textures.

    python analyze.py CAR_DIR OUT_DIR

Writes OUT_DIR/<car>_meshes.csv, <car>_materials.csv, <car>_tree.txt, <car>_summary.json.
Numbers only: no Blender needed. The Blender side (edge flow, visual checks) is blender_import.py.
"""
import sys, os, json, csv, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kn5full import KN5, dds_info


def weld_keys(p, tol=1e-4):
    q = np.round(p / tol).astype(np.int64)
    _, inv, cnt = np.unique(q, axis=0, return_inverse=True, return_counts=True)
    return inv.ravel(), len(cnt)


def mesh_stats(m, texsize):
    P, N, UV, I = m.pos, m.nrm, m.uv, m.idx
    V, T = len(P), len(I)
    if T == 0:
        return dict(verts=V, tris=0)
    inv, nweld = weld_keys(P)
    # hard edges: same position, normals apart by > 2 degrees
    order = np.argsort(inv, kind='stable')
    groups = np.split(order, np.flatnonzero(np.diff(inv[order])) + 1)
    hard = seam = 0
    for g in groups:
        if len(g) < 2: continue
        n0 = N[g[0]]
        if np.any(N[g] @ n0 < np.cos(np.radians(2))): hard += 1
        if np.any(np.abs(UV[g] - UV[g[0]]).max(1) > 1e-4): seam += 1
    a, b, c = P[I[:, 0]], P[I[:, 1]], P[I[:, 2]]
    cr = np.cross(b - a, c - a); area3 = 0.5 * np.linalg.norm(cr, axis=1)
    ua, ub, uc = UV[I[:, 0]], UV[I[:, 1]], UV[I[:, 2]]
    uvx = (ub - ua); uvy = (uc - ua)
    area_uv = 0.5 * np.abs(uvx[:, 0] * uvy[:, 1] - uvx[:, 1] * uvy[:, 0])
    e = np.concatenate([np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1), np.linalg.norm(a - c, axis=1)])
    # face normal vs stored vertex normal: faceted (flat) or smooth?
    fn = cr / np.maximum(np.linalg.norm(cr, axis=1, keepdims=True), 1e-12)
    dev = np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i', fn, N[I[:, 0]]), -1, 1)))
    # triangle quality: smallest angle
    def ang(u, v):
        return np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i', u, v) /
                                            np.maximum(np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1), 1e-12), -1, 1)))
    amin = np.minimum(np.minimum(ang(b - a, c - a), ang(a - b, c - b)), ang(a - c, b - c))
    # mirror symmetry about x = 0 and whether mirrored halves share UV space
    side = np.abs(P[:, 0]) > 0.005
    sym = uvshare = None
    if side.sum() > 10:
        key = {tuple(k): i for i, k in enumerate(np.round(P / 5e-4).astype(np.int64))}
        mir = np.round(P * [-1, 1, 1] / 5e-4).astype(np.int64)
        hits = [(i, key.get(tuple(mir[i]))) for i in np.flatnonzero(side)]
        found = [(i, j) for i, j in hits if j is not None]
        sym = len(found) / len(hits)
        if found:
            ii, jj = np.array(found).T
            uvshare = float(np.mean(np.abs(UV[ii] - UV[jj]).max(1) < 1e-3))
    tex_w, tex_h = texsize or (0, 0)
    A = area3.sum(); AUV = area_uv.sum()
    return dict(
        verts=V, tris=T, welded_verts=nweld, split_ratio=round(V / max(nweld, 1), 3),
        hard_edge_verts=hard, uv_seam_verts=seam,
        area_m2=round(A, 4), uv_area=round(AUV, 4),
        uv_min=[round(x, 3) for x in UV.min(0)], uv_max=[round(x, 3) for x in UV.max(0)],
        texel_px_per_m=round(float(np.sqrt(AUV * tex_w * tex_h / A)), 1) if A > 0 and tex_w else None,
        edge_mm_p10=round(float(np.percentile(e, 10)) * 1000, 1), edge_mm_med=round(float(np.median(e)) * 1000, 1),
        edge_mm_p90=round(float(np.percentile(e, 90)) * 1000, 1),
        tri_per_m2=round(T / A, 0) if A > 0 else None,
        normal_dev_med_deg=round(float(np.median(dev)), 2), min_angle_med_deg=round(float(np.median(amin)), 1),
        sliver_tris=int((amin < 5).sum()), degenerate_tris=int((area3 < 1e-10).sum()),
        mirror_sym=round(sym, 3) if sym is not None else None, mirror_uv_shared=round(uvshare, 3) if uvshare is not None else None,
        bbox_min=[round(x, 3) for x in P.min(0)], bbox_max=[round(x, 3) for x in P.max(0)],
    )


def main(car_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    car = os.path.basename(os.path.normpath(car_dir))
    kn5s = sorted(glob.glob(os.path.join(car_dir, '*.kn5')), key=os.path.getsize, reverse=True)
    main_kn5 = kn5s[0]
    k = KN5(main_kn5)
    tex = {n: dds_info(b) for n, b in k.textures.items()}

    def texsize_for(mat):
        if not mat: return None
        s = mat.samplers.get('txDiffuse')
        if s and tex.get(s[1]): return tex[s[1]][:2]
        return None

    rows = []
    for m in k.meshes:
        st = mesh_stats(m, texsize_for(m.mat))
        rows.append(dict(name=m.name, path=k.path_of(m.node), material=m.mat.name if m.mat else '?',
                         shader=m.mat.shader if m.mat else '?', skinned=m.skinned, layer=m.layer,
                         cast_shadows=m.cast_shadows, transparent=m.transparent, renderable=m.renderable,
                         lod_in=m.lod_in, lod_out=m.lod_out, **st))
    keys = list(dict.fromkeys(k2 for r in rows for k2 in r))
    with open(os.path.join(out_dir, f'{car}_meshes.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, keys); w.writeheader(); w.writerows(rows)

    mrows = []
    used = {}
    for r in rows: used.setdefault(r['material'], []).append(r)
    for mat in k.materials:
        rs = used.get(mat.name, [])
        mrows.append(dict(material=mat.name, shader=mat.shader, blend=mat.blend, alpha_tested=mat.alpha_tested,
                          depth_mode=mat.depth_mode, meshes=len(rs), tris=sum(r.get('tris', 0) for r in rs),
                          samplers='; '.join(f'{s}={t}({tex.get(t, ("?",))[0] if tex.get(t) else "?"}x{tex.get(t, (0, "?"))[1] if tex.get(t) else "?"} {tex[t][3] if tex.get(t) else ""})'
                                            for s, (slot, t) in mat.samplers.items()),
                          props='; '.join(f'{p}={v[0]:g}' for p, v in mat.props.items())))
    with open(os.path.join(out_dir, f'{car}_materials.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, list(mrows[0])); w.writeheader(); w.writerows(mrows)

    with open(os.path.join(out_dir, f'{car}_tree.txt'), 'w') as f:
        def walk(i, d):
            n = k.nodes[i]
            if n.cls == 1:
                t = n.world[3, :3]
                f.write(f'{"  " * d}[T] {n.name}  world=({t[0]:+.3f},{t[1]:+.3f},{t[2]:+.3f})\n')
            else:
                m = n.mesh
                f.write(f'{"  " * d}[{"S" if m.skinned else "M"}] {n.name}  {len(m.idx)} tris  mat={m.mat.name if m.mat else "?"}\n')
            for c in n.children: walk(c, d + 1)
        walk(0, 0)

    lods = {}
    for p in kn5s:
        if 'collider' in os.path.basename(p).lower():
            kk = KN5(p, load_textures=False)
        else:
            kk = k if p == main_kn5 else KN5(p, load_textures=False)
        lods[os.path.basename(p)] = dict(meshes=len(kk.meshes), tris=int(sum(len(m.idx) for m in kk.meshes)),
                                          materials=len(kk.materials), textures=len(kk.texture_sizes),
                                          mb=round(os.path.getsize(p) / 1e6, 1))
    shaders = {}
    for r in rows: shaders[r['shader']] = shaders.get(r['shader'], 0) + r.get('tris', 0)
    fmts = {}
    for n, t in tex.items():
        if t: fmts.setdefault(f'{t[3]}', []).append(f'{n} {t[0]}x{t[1]}')
    summary = dict(car=car, kn5=os.path.basename(main_kn5), version=k.version,
                   nodes=len(k.nodes), transforms=sum(1 for n in k.nodes if n.cls == 1), meshes=len(k.meshes),
                   tris=int(sum(len(m.idx) for m in k.meshes)), verts=int(sum(len(m.pos) for m in k.meshes)),
                   materials=len(k.materials), textures=len(k.textures),
                   texture_mb=round(sum(k.texture_sizes.values()) / 1e6, 1),
                   tris_by_shader=dict(sorted(shaders.items(), key=lambda x: -x[1])), texture_formats=fmts, lods=lods)
    with open(os.path.join(out_dir, f'{car}_summary.json'), 'w') as f:
        json.dump(summary, f, indent=1)
    print(json.dumps({k2: v for k2, v in summary.items() if k2 != 'texture_formats'}, indent=1))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

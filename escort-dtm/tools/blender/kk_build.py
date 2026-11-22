"""Kadett S2 body kit on the Escort (v37) - replaces the NICK3 front clip / sides / boot wing.

Run headless on "escort_v37 kadett kit 1 with kadett ref.blend" (live Escort + Kadett in scene KADETT):
    blender -b "<that blend>" --python kk_build.py
Saves "escort_v37 kadett kit 2 built.blend" (never overwrites the input).

Parts copied from opel_kadett_s2.kn5 (personal use, Nik's call):
  KK_kit      Plane.017  - front bumper + front arches, sills, rear arches (painted: Material #25DQW)
  KK_splitter Plane.032  - front splitter blade only (cut behind the bumper)            (NICK3_carbon)
  KK_fins     Plane.032 + Plane.435/438/442 - the three fins behind each rear wheel      (NICK3_carbon)
  KK_wing     Plane.032  - wing elements, endplates, mounts; on hood_trunk (opens with the boot)
Escort kept: diffuser (inner fins made deeper like the Kadett's), bonnet vents, exhaust, badges.

Fit (Kadett coords -> Escort coords, Blender axes: x = car's left, -y = front, z up):
  arches + bumper: about each wheel centre, scale S_ARCH in y/z (Kadett tyre r 0.31 -> Escort 0.268), x unchanged
  sills: y follows the wheelbase, z squashed so the sill top sits just under the Escort door bottom edge,
         inner edge tucked under the door skin; blended into the arches over BLEND_F / BLEND_R
  wing: translated (rear end to rear end, deck to deck)
"""
import json
import math
import sys

import bmesh
import bpy
import numpy as np

sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")

SRC = r"D:\Claude\escort_mk2_dtm\blender\escort_v37 kadett kit 1 with kadett ref.blend"
OUT = r"D:\Claude\escort_mk2_dtm\blender\escort_v37 kadett kit 2 built.blend"

# measured (kk measure scripts, 22 Nov): wheel centres (y, z)
K_F, K_R = (-1.561, 0.344), (0.851, 0.344)          # Kadett WHEEL_LF / LR
E_F, E_R = (-1.222, 0.144), (1.185, 0.127)          # Escort WHEEL_LF / LR (live kn5)
S_ARCH = 0.268 / 0.310                              # tyre radius ratio
# Kadett sill box: bottom z 0.093, top face z 0.389 (outer) .. 0.404 (inner, x 0.70), outer face x 0.933
K_SILL_BOT, K_SILL_TOP, K_SILL_OUT, K_SILL_IN = 0.093, 0.404, 0.933, 0.700
# Escort door skin bottom edge: z 0.054 @ y -0.6 .. 0.047 @ y 0.5, x 0.687
DOOR_Z = lambda y: 0.0502 - 0.0064 * y
SILL_TUCK = 0.004                                    # sill top this far under the door edge
E_SILL_IN = 0.680                                    # sill inner edge under the door skin (x 0.687)
E_SILL_BOT = -0.090                                  # same ground gap as the NICK3 sides
BLEND_F = (-1.30, -1.00)                             # Kadett y: front arch -> sill
BLEND_R = (0.30, 0.55)                               # Kadett y: sill -> rear arch
WING_D = (0.0, 2.137 - 1.826, -0.183)               # rear end to rear end; boot deck to boot deck
PAINT_UV = (0.857, 0.398)                            # Material #25DQW: AO_BODY texel used by the NICK3 kit

MAIN = "Scene"


def smooth(a, b, t):
    u = np.clip((t - a) / (b - a), 0, 1)
    return u * u * (3 - 2 * u)


def arch_map(p, kc, ec):
    q = p.copy()
    q[:, 1] = ec[0] + S_ARCH * (p[:, 1] - kc[0])
    q[:, 2] = ec[1] + S_ARCH * (p[:, 2] - kc[1])
    return q


def sill_map(p):
    q = p.copy()
    q[:, 1] = E_F[0] + (p[:, 1] - K_F[0]) * (E_R[0] - E_F[0]) / (K_R[0] - K_F[0])
    top = DOOR_Z(q[:, 1]) - SILL_TUCK
    t = (p[:, 2] - K_SILL_BOT) / (K_SILL_TOP - K_SILL_BOT)
    q[:, 2] = E_SILL_BOT + t * (top - E_SILL_BOT)
    ax = np.abs(p[:, 0])
    k = (K_SILL_OUT - E_SILL_IN) / (K_SILL_OUT - K_SILL_IN)
    nx = np.where(ax < K_SILL_OUT, K_SILL_OUT - (K_SILL_OUT - ax) * k, ax)
    q[:, 0] = np.sign(p[:, 0]) * nx
    return q


def kit_map(p):
    wf = 1 - smooth(BLEND_F[0], BLEND_F[1], p[:, 1])
    wr = smooth(BLEND_R[0], BLEND_R[1], p[:, 1])
    ws = 1 - wf - wr
    return (wf[:, None] * arch_map(p, K_F, E_F) + wr[:, None] * arch_map(p, K_R, E_R)
            + ws[:, None] * sill_map(p))


# ---------------------------------------------------------------- helpers
def obk(sc, name):
    return next(o for o in sc.objects if o.type == "MESH" and o.get("kn5_name") == name)


def world_co(ob):
    me = ob.data
    co = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    m = np.array(ob.matrix_world)
    return co @ m[:3, :3].T + m[:3, 3]


def islands(me):
    n = len(me.vertices)
    e = np.zeros(len(me.edges) * 2, int); me.edges.foreach_get("vertices", e); e = e.reshape(-1, 2)
    par = np.arange(n)

    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    for a, b in e:
        ra, rb = f(a), f(b)
        if ra != rb:
            par[ra] = rb
    return np.array([f(i) for i in range(n)])


def extract(src, name, keep_vert=None, keep_island=None):
    """World-space copy of src as a new object (no parent). keep_island(co_of_island) -> bool picks islands;
    keep_vert(co) -> bool mask: faces with any vertex outside are dropped."""
    me = src.data.copy()
    co = world_co(src)
    for i, v in enumerate(me.vertices):
        v.co = co[i]
    keep = np.ones(len(co), bool)
    if keep_island is not None:
        r = islands(me)
        for k in np.unique(r):
            m = r == k
            if not keep_island(co[m]):
                keep[m] = False
    if keep_vert is not None:
        keep &= keep_vert(co)
    bm = bmesh.new(); bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bad = [f for f in bm.faces if not all(keep[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=bad, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    for k in ("kn5_name", "kn5_class", "kn5_order", "kn5_flags", "kn5_pristine", "kn5_matrix"):
        if k in ob:
            del ob[k]
    return ob


def set_material(ob, mat):
    ob.data.materials.clear(); ob.data.materials.append(mat)
    for p in ob.data.polygons:
        p.material_index = 0


def apply_map(ob, fn):
    me = ob.data
    co = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    me.vertices.foreach_set("co", fn(co).ravel())
    me.update()


def renormal(ob, merge=0.0002, angle=40):
    me = ob.data
    if "custom_normal" in me.attributes:
        me.attributes.remove(me.attributes["custom_normal"])
    assert not me.has_custom_normals, ob.name
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.set_sharp_from_angle(angle=math.radians(angle))
    me.update()


def const_uv(ob, uv):
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    a = np.tile(np.array(uv, np.float32), len(me.loops))
    me.uv_layers.active.data.foreach_set("uv", a)


def link(ob, sc, parent, col):
    col.objects.link(ob)
    w = ob.matrix_world.copy()
    ob.parent = parent
    ob.matrix_parent_inverse = parent.matrix_world.inverted()
    ob.matrix_world = w
    ob["kk_part"] = True


# ---------------------------------------------------------------- build
def remove_nick3(sc):
    gone = []
    for o in list(sc.objects):
        k = o.get("kn5_name", "")
        if o.type == "MESH" and k in ("NICK3_front_clip", "NICK3_side_L", "NICK3_side_R", "NICK3_slats_tail_L",
                                      "NICK3_slats_tail_R", "NICK3_STATIC_MESH_NICK3_recess",
                                      "NICK3_BOOT_MESH_NICK3_carbon", "NICK3_BOOT_MESH_NICK3_KIT_PAINT"):
            gone.append(k); bpy.data.objects.remove(o)
    return gone


def cut_front_carbon(sc):
    """NICK3 carbon = front splitter + diffuser in one mesh: drop the front half (the Kadett splitter replaces it)."""
    ob = obk(sc, "NICK3_STATIC_MESH_NICK3_carbon")
    co = world_co(ob)
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
    bad = [f for f in bm.faces if any(co[v.index][1] < 0.0 for v in f.verts)]
    bmesh.ops.delete(bm, geom=bad, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(ob.data); bm.free()
    return len(bad)


def deepen_diffuser_fins(sc):
    """Escort inner diffuser fins (x +-0.20, +-0.48, y 1.49..2.30) follow the diffuser ramp, 3-4 cm deep. The
    Kadett's keep an almost flat bottom edge (rises 0.03 over 0.79 m) - give the Escort's the same."""
    ob = obk(sc, "NICK3_STATIC_MESH_NICK3_carbon")
    me = ob.data
    mw = np.array(ob.matrix_world); inv = np.linalg.inv(mw)
    co = world_co(ob)
    r = islands(me)
    moved = 0
    for k in np.unique(r):
        m = r == k
        c = co[m]
        if not (c[:, 0].max() - c[:, 0].min() < 0.02 and 0.15 < abs(c[:, 0].mean()) < 0.55
                and c[:, 1].min() > 1.45 and c[:, 1].max() - c[:, 1].min() > 0.6):
            continue
        idx = np.where(m)[0]
        # bottom verts: below the fin's local mid-height at their y
        for i in idx:
            y, z = co[i, 1], co[i, 2]
            near = c[np.abs(c[:, 1] - y) < 0.03]
            if z < (near[:, 2].min() + near[:, 2].max()) / 2 - 1e-4 or near[:, 2].max() - near[:, 2].min() < 1e-3 and z <= near[:, 2].min():
                zb = -0.120 + (y - 1.49) * (0.025 / 0.81)
                if zb < z:
                    co[i, 2] = zb; moved += 1
    loc = np.c_[co, np.ones(len(co))] @ inv.T
    me.vertices.foreach_set("co", loc[:, :3].ravel()); me.update()
    return moved


def build():
    main = bpy.data.scenes[MAIN]; ks = bpy.data.scenes["KADETT"]
    bpy.context.window.scene = ks; bpy.context.view_layer.update()
    bpy.context.window.scene = main; bpy.context.view_layer.update()
    report = {"removed": remove_nick3(main), "front_carbon_faces_cut": cut_front_carbon(main)}
    report["diffuser_fin_verts_moved"] = deepen_diffuser_fins(main)

    mats = {json.loads(m["kn5_def"])["name"]: m for m in (bpy.data.materials[n] for n in json.loads(main["kn5_materials"]))}
    paint, carbon = mats["Material #25DQW"], mats["NICK3_carbon"]
    root = next(o for o in main.objects if o.get("kn5_root"))
    trunk = next(o for o in main.objects if o.get("kn5_name") == "hood_trunk")
    col = bpy.data.collections.get("KADETT_KIT") or bpy.data.collections.new("KADETT_KIT")
    if col.name not in main.collection.children:
        main.collection.children.link(col)

    k032 = obk(ks, "Plane.032")
    # kit
    kit = extract(obk(ks, "Plane.017"), "KK_kit")
    apply_map(kit, kit_map); set_material(kit, paint); const_uv(kit, PAINT_UV); renormal(kit)
    # splitter: front blade of the undertray sheets, in front of the bumper's back edge
    spl = extract(k032, "KK_splitter",
                  keep_island=lambda c: c[:, 2].max() < 0.105 and c[:, 1].min() < -2.3,
                  keep_vert=lambda c: c[:, 1] < -1.85)
    apply_map(spl, lambda p: arch_map(p, K_F, E_F)); set_material(spl, carbon); renormal(spl, merge=0.0)
    # fins behind the rear wheels
    fin_isl = lambda c: (np.abs(c[:, 0]).min() > 0.69 and c[:, 1].min() > 1.1 and c[:, 1].max() < 1.75
                         and c[:, 2].max() < 0.70)
    parts = [extract(k032, "KK_fins_a", keep_island=fin_isl),
             extract(obk(ks, "Plane.435"), "KK_fins_b"), extract(obk(ks, "Plane.438"), "KK_fins_c"),
             extract(obk(ks, "Plane.442"), "KK_fins_d", keep_island=lambda c: np.abs(c[:, 0]).min() > 0.69)]
    fins = join(parts, "KK_fins")
    apply_map(fins, lambda p: arch_map(p, K_R, E_R)); set_material(fins, carbon); renormal(fins, merge=0.0)
    # wing: elements, endplates, mounts (not the boot-lip blade at z 0.76-0.80)
    wing_isl = lambda c: (c[:, 1].min() > 1.3 and c[:, 2].min() > 0.70
                          and not (c[:, 0].max() - c[:, 0].min() > 1.2 and c[:, 2].max() < 0.81))
    wing = extract(k032, "KK_wing", keep_island=wing_isl)
    apply_map(wing, lambda p: p + np.array(WING_D)); set_material(wing, carbon)

    for ob, par in ((kit, root), (spl, root), (fins, root), (wing, trunk)):
        link(ob, main, par, col)
    bpy.context.view_layer.update()
    report["parts"] = {o.name: len(o.data.polygons) for o in (kit, spl, fins, wing)}
    return report


def join(obs, name):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    for o in obs:
        bm.from_mesh(o.data)
    bm.to_mesh(me); bm.free()
    for o in obs:
        bpy.data.meshes.remove(o.data)
    return bpy.data.objects.new(name, me)


if __name__ == "__main__":
    rep = build()
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    print("REPORT", json.dumps(rep))

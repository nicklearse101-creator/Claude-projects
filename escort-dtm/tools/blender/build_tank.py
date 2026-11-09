"""Boot: the old fuel system out, a stainless fuel tank where the physics has it (Nik, 5 Oct: "add a stainless steel
fuel tank where this box is, remove any conflicting parts/existing tanks"). Runs inside Blender on
blender/escort_aero.blend AFTER build_aero.build() (which deletes every aero_part, these included).

    import build_tank as t
    t.remove_old_tanks()   # main + LOD B/C/D: old fuel cell (right corner), pot assembly over it, front-wall cylinder,
                           #   fire extinguisher (inside the new tank), the original steel tank under the boot floor
    t.build()              # AERO_fueltank (stainless) + AERO_fueltank_frame (black cradle, straps, filler hose)

The box: Content Manager draws the physics tank as a 4:2:1 box holding MAX_FUEL (55 l): 0.76 x 0.38 x 0.19 m,
measured from Nik's screenshot (camera fitted to the colliders.ini box, 1 px). Its front face ran 5 cm into the
boot's front wall, so tank AND physics moved back together: car.ini [FUELTANK] POSITION 0,0,-1.77 (was -1.7) =
model centre (0, 1.63, 0.40) - CM's box still sits exactly on the tank. Model = physics - GRAPHICS_OFFSET.
v24 floated the tank 19 cm up on a four-legged cradle. v25 (Nik: "The battery could be moved further to the back so
the fuel tank can sit on the floor instead of legs"): battery moved back/out (v25.move_battery), old fuel lines out,
and the tank sits on the floor on rubber pads. The boot floor is flat (z 0.133) between x -0.30 and +0.30 and rises
to 0.187 over the chassis rails on both sides, so the tank's bottom is formed with a step at each end (as fabricated
tanks are); two straps over the top bolt to brackets on those raised strips. Physics FUELTANK moved down with it
(dtm_build.FUELTANK_POS), so CM's box still sits on the tank. Blender: +X = car's left, +Y = rear, Z up.
"""
import math

import bmesh
import bpy
from mathutils import Vector

import build_aero as ba
import build_rear_dwb as r

# cross-section in x-z, counter-clockwise: flat bottom on pads, 25-30 mm ramps up to the end steps over the rails
TANK = dict(cy=1.63, d=0.38, top=0.352, corner_r=0.018, end_bevel=0.012,
            section=[(-0.380, 0.192), (-0.325, 0.192), (-0.300, 0.152), (0.300, 0.152), (0.320, 0.192),
                     (0.380, 0.192), (0.380, 0.352), (-0.380, 0.352)])
TANK["cz"] = (0.152 + TANK["top"]) / 2               # main body centre = the physics point (0.252 -> y -0.148)
STAINLESS = "Material #503ds"                       # the exhaust's polished metal (multimap, fresnel)
FILLER = dict(x=-0.27, y=1.50, neck_r=0.030, neck_top=0.392, cap_r=0.040, cap_t=0.012,
              body=(-0.505, 1.455, 0.452))          # inner end of the body's filler on the right boot wall
SENDER = dict(x=0.06, y=1.70, r=0.055, t=0.005)
OUTLET = dict(x=-0.26, y=1.50, r=0.009, down=0.024)   # down through the floor to the pumps underneath
PADS = dict(x=(-0.24, 0.24), y=(1.49, 1.77), half=0.022, floor=0.133)   # rubber, floor -> tank bottom
STRAP = dict(w=0.020, t=0.0025, y=(1.50, 1.76), foot_x=0.405, rail_z=0.187, bolt_r=0.007)
HOSE_R = 0.022

REGIONS = {   # world boxes; an island goes when ALL its vertices are inside (prefix: only meshes named so)
    "old fuel cell": (((-0.76, 1.53, 0.10), (-0.45, 1.87, 0.61)), None),
    "pot assembly": (((-0.50, 1.62, 0.47), (-0.19, 1.90, 0.70)), None),
    "front-wall cylinder": (((-0.42, 1.39, 0.38), (-0.04, 1.66, 0.66)), None),
    "fire extinguisher": (((0.17, 1.39, 0.17), (0.42, 1.51, 0.62)), None),
    "under-floor tank": (((-0.50, 1.35, 0.04), (0.36, 1.95, 0.135)), ("grille_a",)),
}


# ---- removal ---------------------------------------------------------------------------------------------------
def remove_old_tanks():
    """Idempotent; per scene and region the number of vertices removed."""
    done = {}
    for tag in ("Scene", "LOD_B", "LOD_C", "LOD_D"):
        rep = {}
        for ob in bpy.data.scenes[tag].objects:
            if ob.type != "MESH" or str(ob.get("kn5_name") or ob.name).startswith("AERO"):
                continue
            nm = str(ob.get("kn5_name") or ob.name)
            mw = ob.matrix_world
            bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
            W = [mw @ v.co for v in bm.verts]
            kill = set()
            for comp in r._islands(bm):
                for label, ((lo, hi), prefix) in REGIONS.items():
                    if prefix and not nm.startswith(prefix):
                        continue
                    if all(lo[k] <= W[u.index][k] <= hi[k] for u in comp for k in range(3)):
                        kill.update(u.index for u in comp)
                        rep[label] = rep.get(label, 0) + len(comp)
                        break
            if kill:
                bmesh.ops.delete(bm, geom=[bm.verts[i] for i in kill], context="VERTS")
                bm.to_mesh(ob.data); ob.data.update()
            bm.free()
        done[tag] = rep
    return done


# ---- the tank --------------------------------------------------------------------------------------------------
def _profile(inset, seg=4):
    """Tank cross-section in x-z (CCW), corners rounded, `inset` inward (for the bevelled ends)."""
    pts = TANK["section"]
    n = len(pts)
    out = []
    for i in range(n):
        p, a, b = Vector(pts[i]), Vector(pts[i - 1]), Vector(pts[(i + 1) % n])
        d_in, d_out = (p - a).normalized(), (b - p).normalized()
        n_in, n_out = Vector((-d_in.y, d_in.x)), Vector((-d_out.y, d_out.x))   # inward (left) normals
        convex = d_in.x * d_out.y - d_in.y * d_out.x > 0
        q = p + (n_in + n_out) * inset
        rad = (TANK["corner_r"] - inset) if convex else (0.008 + inset)
        c = q + (n_in + n_out) * rad if convex else q - (n_in + n_out) * rad
        s, e = q - d_in * rad, q + d_out * rad
        a0, a1 = math.atan2(s.y - c.y, s.x - c.x), math.atan2(e.y - c.y, e.x - c.x)
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        out += [(c.x + rad * math.cos(a0 + da * k / seg), c.y + rad * math.sin(a0 + da * k / seg)) for k in range(seg + 1)]
    return out


def tank_body():
    y0, y1, e = TANK["cy"] - TANK["d"] / 2, TANK["cy"] + TANK["d"] / 2, TANK["end_bevel"]
    secs = [[(x, y, z) for x, z in _profile(ins)] for y, ins in ((y0, e), (y0 + e, 0.0), (y1 - e, 0.0), (y1, e))]
    return ba.loft(secs)


def _strap(y):
    """Flat strap over the tank at y: across the top, down both ends onto the raised rail strips, out to a bolted foot."""
    s = STRAP
    w, t, top, rail = TANK["section"][-3][0] + s["t"], s["t"], TANK["top"], s["rail_z"]
    path = [(-s["foot_x"] - 0.03, rail + t), (-w, rail + t), (-w, top + t), (w, top + t), (w, rail + t),
            (s["foot_x"] + 0.03, rail + t)]
    parts = []
    for (xa, za), (xb, zb) in zip(path, path[1:]):          # each straight run a thin box, overlapping at the bends
        c = Vector(((xa + xb) / 2, y, (za + zb) / 2))
        parts.append(r.box(c, Vector((abs(xb - xa) / 2 + t, 0, 0)), Vector((0, s["w"], 0)),
                           Vector((0, 0, abs(zb - za) / 2 + t))))
    return ba.merge(*parts)


def build():
    sc = ba.main_scene()
    bpy.context.window.scene = sc
    for o in [o for o in bpy.data.objects if o.get("tank_part")]:
        bpy.data.objects.remove(o)
    steel, trim = ba.material(STAINLESS), ba.material(ba.TRIM)
    suv = ba.pick_uv(steel, (0.30, 1.00, 0.00))[1]          # same texel as the dampers / exhaust pipe
    tuv = ba.pick_uv(trim, (0.70, 0.30, 0.75))[1]
    top = TANK["top"]
    bot = min(z for _, z in TANK["section"])
    # stainless: body, filler neck + cap, sender plate + fittings, outlet to the pumps
    st = [tank_body()]
    fx, fy = FILLER["x"], FILLER["y"]
    st.append(r.tube((fx, fy, top - 0.004), (fx, fy, FILLER["neck_top"]), FILLER["neck_r"]))
    st.append(r.tube((fx, fy, FILLER["neck_top"]), (fx, fy, FILLER["neck_top"] + FILLER["cap_t"]), FILLER["cap_r"], n=16))
    st.append(r.tube((SENDER["x"], SENDER["y"], top - 0.002), (SENDER["x"], SENDER["y"], top + SENDER["t"]), SENDER["r"], n=16))
    for dx in (-0.022, 0.022):
        st.append(r.tube((SENDER["x"] + dx, SENDER["y"], top), (SENDER["x"] + dx, SENDER["y"], top + 0.028), 0.0075))
    st.append(r.tube((OUTLET["x"], OUTLET["y"], bot + 0.004), (OUTLET["x"], OUTLET["y"], bot - OUTLET["down"]), OUTLET["r"]))
    # black: rubber pads under the flat bottom, two straps bolted to the rail strips, filler hose
    bl = []
    p = PADS
    for x in p["x"]:
        for y in p["y"]:
            bl.append(r.box((x, y, (p["floor"] + bot) / 2), Vector((p["half"], 0, 0)), Vector((0, p["half"], 0)),
                            Vector((0, 0, (bot - p["floor"]) / 2))))
    steel_bits = []
    for y in STRAP["y"]:
        bl.append(_strap(y))
        for sx in (-1, 1):
            c = Vector((sx * STRAP["foot_x"], y, STRAP["rail_z"] + 2 * STRAP["t"]))
            steel_bits.append(r.tube(c, c + Vector((0, 0, 0.007)), STRAP["bolt_r"], n=6))        # hex bolt head
            steel_bits.append(r.tube(c - Vector((0, 0, 0.001)), c + Vector((0, 0, 0.0015)), 0.012, n=12))   # washer
    st += steel_bits
    # filler hose: body filler on the right boot wall -> side of the filler neck
    p0, p3 = Vector(FILLER["body"]), Vector((fx - FILLER["neck_r"] + 0.004, fy, FILLER["neck_top"] - 0.018))
    p1, p2 = p0 + Vector((0.07, 0.015, 0.03)), p3 + Vector((-0.07, -0.01, 0.0))
    pts = [((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + (t ** 3) * p3
           for t in [k / 12 for k in range(13)]]
    bl.append(ba.loft([r.ring(pts[i], pts[min(i + 1, 12)] - pts[max(i - 1, 0)], HOSE_R, 12) for i in range(13)]))
    out = {}
    rt = ba.root()
    for name, parts, mat, uv in (("AERO_fueltank", st, steel, suv), ("AERO_fueltank_frame", bl, trim, tuv)):
        ob = ba.make_obj(name, ba.merge(*parts), mat, uv, rt)
        ob["tank_part"] = True
        out[name] = len(ob.data.polygons)
    out["physics centre z (model)"] = TANK["cz"]
    bpy.context.view_layer.update()
    return out


def check():
    """Nearest distance from each tank part's vertices to the rest of the car (feet sit on the floor on purpose)."""
    world = r._scene_bvh(exclude_prefix=("AERO", "M_Tire", "for_5_escort", "for_rotor", "for_caliper"))
    res = {}
    for o in [o for o in ba.main_scene().objects if o.get("tank_part")]:
        mw = o.matrix_world
        best = (9.0, None)
        for v in o.data.vertices:
            p = mw @ v.co
            loc, nrm, idx, dist = world.find_nearest(p, 0.2)
            if loc is not None and dist < best[0] and p.z > 0.16:
                best = (dist, tuple(round(c, 3) for c in p))
        res[o.name] = dict(faces=len(o.data.polygons), nearest_mm_above_floor=round(best[0] * 1000, 1), at=best[1])
    return res

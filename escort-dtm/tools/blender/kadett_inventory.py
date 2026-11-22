"""List every Kadett S2 mesh: name, parent dummy, material, world bbox (Blender: x=car left?, -y front, z up), tris."""
import sys, csv, bpy
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kn5_import
KN5 = r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\opel_kadett_s2\opel_kadett_s2.kn5"
for ob in list(bpy.data.objects): bpy.data.objects.remove(ob)
kn5_import.import_kn5(KN5, r"D:\ClaudeData\tmp\kadett\tex", collection_name="KADETT", prefix="K_", primary=False)
bpy.context.view_layer.update()
rows = []
for ob in bpy.data.objects:
    if ob.type != "MESH": continue
    bb = [ob.matrix_world @ __import__("mathutils").Vector(c) for c in ob.bound_box]
    mn = [min(v[i] for v in bb) for i in range(3)]; mx = [max(v[i] for v in bb) for i in range(3)]
    mat = ob.data.materials[0].name if ob.data.materials else ""
    rows.append([ob.get("kn5_name", ob.name), ob.parent.get("kn5_name", ob.parent.name) if ob.parent else "", mat,
                 *[round(v, 3) for v in mn], *[round(v, 3) for v in mx], len(ob.data.polygons)])
out = r"D:\Claude\escort_mk2_dtm\docs\kadett_mesh_inventory.csv"
with open(out, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["mesh", "parent", "material", "xmin", "ymin", "zmin", "xmax", "ymax", "zmax", "tris"]); w.writerows(rows)
bpy.ops.wm.save_as_mainfile(filepath=r"D:\Claude\escort_mk2_dtm\blender\kadett_ref.blend")
print("ROWS", len(rows))

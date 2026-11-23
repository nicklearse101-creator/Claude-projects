"""v49b: headlight lens glassrhl_a (lights.ini LIGHT_0 = the headlights) was switched off (kn5 active 0) by the NICK3 work -> on."""
import bpy, json
n = 0
for sc in bpy.data.scenes:
    for o in sc.objects:
        if o.get("kn5_name") == "glassrhl_a" and "kn5_flags" in o:
            fl = json.loads(o["kn5_flags"]); fl["active"] = 1; o["kn5_flags"] = json.dumps(fl); n += 1
print("ACTIVATED", n)
bpy.ops.wm.save_mainfile()

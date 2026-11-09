"""Run a FreeCAD script under freecadcmd with any exception printed (freecadcmd swallows them silently).

D:\\FreeCAD\\bin\\freecadcmd.exe tools/cad/run_fc.py   (script name in env FC_SCRIPT, default build_curves.py)
"""
import os
import traceback

p = os.path.join(r"D:\Claude\vauxhall_nova_gte_1989\tools\cad", os.environ.get("FC_SCRIPT", "build_curves.py"))
try:
    exec(compile(open(p).read(), p, "exec"), {"__name__": "__main__", "__file__": p})
except SystemExit:
    pass
except Exception:
    traceback.print_exc()
    print("FAILED", flush=True)

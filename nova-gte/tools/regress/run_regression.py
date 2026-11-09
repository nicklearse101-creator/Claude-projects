"""One-command regression run (master plan sections 10 and 15). Read-only on the model.

    .venv\\Scripts\\python.exe tools\\regress\\run_regression.py [--blend blender\\nova_proc.blend]

Does, in order: provenance log (git, input hashes, tool versions) -> Blender background pass (measure NOVA_NEW, 7 fixed clay
views, zebra pass) -> check every target in spec_targets.json (tolerances fixed in advance) -> contact sheet ->
diff against the previous run -> reports/regression/<run_id>/report.{json,md}; images in export/regression/<run_id>/.
Exit code 1 if a check that passed in the previous run now fails. v1 does NOT yet do: reference-drawing overlays, renders
through the solved photo cameras, curvature combs, mesh-health checks, FreeCAD surface checks (see report 'not covered').
"""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
FREECAD = r"D:\FreeCAD\bin\freecadcmd.exe"
INPUTS = ["tools/photomatch/obs.json", "tools/photomatch/ba_result.json", "reference/views/frame.json", "blender/data/cad/lines_v2_fit.json",
          "blender/data/cad/sections_v3.json", "docs/SPEC_SHEET.md", "tools/regress/spec_targets.json", "tools/regress/blender_measure_render.py",
          "tools/regress/run_regression.py"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, **kw)


def first_line(cmd):
    try:
        r = run(cmd, timeout=60); return (r.stdout or r.stderr).strip().splitlines()[0]
    except Exception as e:
        return "unavailable: %s" % e


ap = argparse.ArgumentParser(); ap.add_argument("--blend", default="blender/nova_proc.blend"); args = ap.parse_args()
blend = os.path.join(ROOT, args.blend)
commit = run(["git", "rev-parse", "HEAD"]).stdout.strip()
run_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + commit[:7]
rep_dir, img_dir = os.path.join(ROOT, "reports", "regression", run_id), os.path.join(ROOT, "export", "regression", run_id)
os.makedirs(rep_dir, exist_ok=True); os.makedirs(img_dir, exist_ok=True)
t_start = time.time()

prov = dict(run_id=run_id, started=datetime.datetime.now().isoformat(timespec="seconds"), commit=commit,
            branch=run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip(),
            tags_at_head=run(["git", "tag", "--points-at", "HEAD"]).stdout.split(),
            uncommitted=[l for l in run(["git", "status", "--porcelain"]).stdout.splitlines()],
            blend=args.blend, blend_sha256_16=sha(blend), inputs={p: (sha(os.path.join(ROOT, p)) if os.path.exists(os.path.join(ROOT, p)) else "MISSING") for p in INPUTS},
            blender=first_line([BLENDER, "--version"]), freecad=first_line([FREECAD, "--version"]), python=sys.version.split()[0])

# ---- Blender pass -----------------------------------------------------------------------------------------------------
r = run([BLENDER, "-b", blend, "--python", os.path.join(ROOT, "tools", "regress", "blender_measure_render.py"), "--", img_dir], timeout=1800)
open(os.path.join(rep_dir, "blender.log"), "w").write(r.stdout + "\n--- stderr ---\n" + r.stderr)
mpath = os.path.join(img_dir, "measure.json")
if not os.path.exists(mpath):
    print("Blender pass failed, see", os.path.join(rep_dir, "blender.log")); sys.exit(2)
M = json.load(open(mpath))
log_lines = [l for l in r.stdout.splitlines() if l.startswith(("clay views", "zebra views", "measured"))]

# ---- checks ------------------------------------------------------------------------------------------------------------
T = json.load(open(os.path.join(ROOT, "tools", "regress", "spec_targets.json")))["targets"]
checks = []
for t in T:
    m = M["derived"][t["id"]]; d = m - t["value"]
    checks.append(dict(id=t["id"], target=t["value"], measured=round(m, 1), delta=round(d, 1), tol=t["tol"], cls=t["class"],
                       status="PASS" if abs(d) <= t["tol"] else "FAIL", src=t["src"]))

# ---- previous run ------------------------------------------------------------------------------------------------------
base = os.path.join(ROOT, "reports", "regression")
prev_ids = sorted(d for d in os.listdir(base) if d != run_id and os.path.exists(os.path.join(base, d, "report.json")))
prev = json.load(open(os.path.join(base, prev_ids[-1], "report.json"))) if prev_ids else None
regress, changed = [], []
if prev:
    pc = {c["id"]: c for c in prev["checks"]}
    for c in checks:
        p = pc.get(c["id"])
        if not p:
            continue
        c["prev_measured"] = p["measured"]
        if abs(c["measured"] - p["measured"]) >= 1.0:
            changed.append("%s %.1f -> %.1f mm" % (c["id"], p["measured"], c["measured"]))
        if p["status"] == "PASS" and c["status"] == "FAIL":
            regress.append(c["id"])

# ---- contact sheet -----------------------------------------------------------------------------------------------------
def load(p):
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if im is None:
        return np.full((250, 400, 3), 60, np.uint8)
    if im.shape[2] == 4:
        a = im[:, :, 3:4] / 255.0; im = (im[:, :, :3] * a + np.array([48, 40, 40], float) * (1 - a)).astype(np.uint8)
    return cv2.resize(im, (400, 250), interpolation=cv2.INTER_AREA)


names = [("clay_front", "front"), ("clay_rear", "rear"), ("clay_left", "left"), ("clay_right", "right"), ("clay_top", "top"),
         ("clay_q_front_left", "front 3/4"), ("clay_q_rear_left", "rear 3/4"), ("zebra_left", "zebra left"), ("zebra_front", "zebra front"),
         ("zebra_q_front_left", "zebra front 3/4"), ("zebra_q_rear_left", "zebra rear 3/4")]
tiles = []
for f, label in names:
    im = load(os.path.join(img_dir, f + ".png")); cv2.putText(im, label, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA); tiles.append(im)
tiles.append(np.full((250, 400, 3), 30, np.uint8))
sheet = np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, 12, 4)])
cv2.imwrite(os.path.join(img_dir, "contact_sheet.png"), sheet)

# ---- report ------------------------------------------------------------------------------------------------------------
not_covered = ["reference-drawing overlays (tools/cad/overlay.py, render_rect.py exist separately)", "renders through the 7 solved photo cameras (match_look.py, overlay_edges.py)",
               "curvature comb / zebra on FreeCAD NURBS faces (no surfaces exist yet)", "mesh health: non-manifold, holes, self-intersection, normals",
               "feature positions (lamps, pillars, shut lines) - only overall and hard-point dimensions are checked", "wheel arch gap / ride height / AC in-game check"]
rep = dict(provenance=prov, elapsed_s=round(time.time() - t_start, 1), checks=checks, drivers=M["drivers"], blender_log=log_lines,
           vs_previous=dict(previous_run=(prev_ids[-1] if prev else None), regressions=regress, changed_1mm_or_more=changed),
           images=img_dir, not_covered=not_covered)
json.dump(rep, open(os.path.join(rep_dir, "report.json"), "w"), indent=1)
md = ["# Regression run %s" % run_id, "",
      "commit `%s` (%s)%s; blend `%s` (%s); %s; %s" % (commit[:7], prov["branch"], " + %d uncommitted/untracked" % len(prov["uncommitted"]) if prov["uncommitted"] else "", args.blend, prov["blend_sha256_16"], prov["blender"], prov["freecad"]),
      "elapsed %.0f s; images: `%s`" % (rep["elapsed_s"], img_dir), "",
      "| check | target | measured | delta | tol | status | source |", "|---|---|---|---|---|---|---|"]
md += ["| %s | %s | %s | %+.1f | %s | **%s** | %s |" % (c["id"], c["target"], c["measured"], c["delta"], c["tol"], c["status"], c["src"]) for c in checks]
md += ["", "Width set by: %s. Height set by: %s. Mirrors add: overall %s mm." % (M["drivers"]["width"][:3], M["drivers"]["height"][:2], M["drivers"]["mirror_width_mm"]),
       "%d objects, %d polygons." % (M["drivers"]["n_objects"], M["drivers"]["total_tris"]), "",
       "vs previous run (%s): regressions %s; changed >= 1 mm: %s" % (prev_ids[-1] if prev else "none - this is the baseline", regress or "none", changed or "none"), "",
       "Not covered by v1: " + "; ".join(not_covered) + ".", ""]
open(os.path.join(rep_dir, "report.md"), "w").write("\n".join(md))
open(os.path.join(base, "LATEST.txt"), "w").write(run_id)
print("\n".join(md))
sys.exit(1 if regress else 0)

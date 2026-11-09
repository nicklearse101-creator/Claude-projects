"""Copy the project's car package into Assetto Corsa (content/cars/vauxhall_nova_gte_1989).

Rule 5 (CLAUDE.md): never overwrite another car. The target is only replaced when it is our own earlier
deploy (it carries the marker file .nova_project_deploy); anything else stops the script.

Before replacing our own deploy, the installed copy is archived to export/deploy_backups/<time>_BACKUP_installed
(outside AC, so it never shows up as a car) and every installed file that differs from the project is listed:
changes made in Content Manager since the last deploy are never lost silently. AC must not be running.
Run with:  python tools\\deploy.py
"""
import filecmp
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SRC = PROJECT / "car" / "vauxhall_nova_gte_1989"
DST = Path(r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\vauxhall_nova_gte_1989")
BACKUPS = PROJECT / "export" / "deploy_backups"
MARK = ".nova_project_deploy"


def ac_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq acs.exe"], capture_output=True, text=True).stdout
        return "acs.exe" in out.lower()
    except OSError:
        return False


def differences(installed, project):
    """Installed files that are new or differ from the project copy (sfx is kept by the deploy anyway)."""
    out = []
    for p in installed.rglob("*"):
        if not p.is_file() or p.name == MARK or p.relative_to(installed).parts[0] == "sfx":
            continue
        q = project / p.relative_to(installed)
        if not q.exists():
            out.append(f"only installed: {p.relative_to(installed)}")
        elif not filecmp.cmp(p, q, shallow=False):
            out.append(f"changed:        {p.relative_to(installed)}")
    return out


def main():
    if ac_running():
        sys.exit("STOP: Assetto Corsa is running - close it first")
    tmp = None
    if DST.exists():
        if not (DST / MARK).exists():
            sys.exit(f"STOP: {DST} exists and is not our deploy - not touching it")
        diffs = differences(DST, SRC)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = BACKUPS / f"{stamp}_BACKUP_installed_before_deploy"
        shutil.copytree(DST, backup)
        print("installed copy archived to", backup)
        if diffs:
            print("WARNING - the installed car differed from the project (kept in the backup above):")
            for d in diffs:
                print("   ", d)
        keep_sfx = DST / "sfx"
        tmp = PROJECT / "export" / "_sfx_keep"
        if tmp.exists():
            shutil.rmtree(tmp)
        if keep_sfx.exists() and any(keep_sfx.iterdir()):
            shutil.copytree(keep_sfx, tmp)          # keep a sound bank added later in Content Manager
        shutil.rmtree(DST)
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns(".gitkeep"))
    if tmp and tmp.exists():
        shutil.rmtree(DST / "sfx", ignore_errors=True)
        shutil.copytree(tmp, DST / "sfx")
        shutil.rmtree(tmp)
    (DST / MARK).write_text("deployed from D:\\Claude\\vauxhall_nova_gte_1989\n", encoding="utf-8")
    missing = [p for p in ("vauxhall_nova_gte_1989.kn5", "collider.kn5", "data/car.ini", "ui/ui_car.json") if not (DST / p).exists()]
    print("deployed to", DST)
    print("missing:", missing or "none")


if __name__ == "__main__":
    main()

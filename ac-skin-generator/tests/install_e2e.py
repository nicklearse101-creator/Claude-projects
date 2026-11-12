"""Full install -> run -> update -> uninstall with the real built app (build/app.zip from build.py), all inside a test
folder: AppData and LocalAppData are pointed at the test folder, the Installed-apps entry goes to a dummy registry key
(removed again), no desktop shortcut. An old install without an Installed-apps entry (like Nik's 11 Nov one) sits in
the default place and must be moved. The real install is never touched.
python tests/install_e2e.py WORK_DIR APPDATA_COPY        (WORK_DIR on D:)"""
import os, shutil, subprocess, sys, time, winreg
work = os.path.abspath(sys.argv[1]); src_data = os.path.join(os.path.abspath(sys.argv[2]), 'Rattys4SkinGenerator')
shutil.rmtree(work, ignore_errors=True)
os.environ['APPDATA'] = os.path.join(work, 'Roaming'); os.environ['LOCALAPPDATA'] = os.path.join(work, 'Local')
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import installer as I

DUMMY = r'Software\R4S_e2e_dummy_uninstall_key'
I.UNINSTALL_KEY = DUMMY
_us = I.uninstall_script
I.uninstall_script = lambda t, links, key=None, message=True, data_dir=None: _us(t, links, key=DUMMY, message=False, data_dir=data_dir)
_res = I.res
DESK = os.path.join(work, 'Desktop')
REAL_LINK = os.path.join(I.desktop_dir(), I.APP + '.lnk')          # the user's own shortcut: must not change
_real = os.stat(REAL_LINK).st_mtime_ns if os.path.exists(REAL_LINK) else None
I.desktop_dir = lambda: DESK
I.res = lambda n: os.path.join(HERE, 'build', n) if n == 'app.zip' else _res(n)
problems = []


def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what, flush=True)
    if not ok: problems.append(what)


def reg_location():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DUMMY) as k: return winreg.QueryValueEx(k, 'InstallLocation')[0]
    except OSError: return None


# the user's logos and settings (a copy), the Start menu folder, and an old install in the default place
shutil.copytree(src_data, I.APPDATA_DIR, ignore=shutil.ignore_patterns('ghosts'))
os.makedirs(os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs'))
old = os.path.join(I.DEFAULT_PARENT, I.FOLDER)
os.makedirs(os.path.join(old, '_internal')); open(os.path.join(old, I.EXE), 'w').write('old')
open(os.path.join(old, 'uninstall.ps1'), 'w').write('# old')
os.makedirs(DESK); open(os.path.join(DESK, I.APP + '.lnk'), 'w').write('old shortcut to the old program')
print('zip:', I.res('app.zip'), round(os.path.getsize(I.res('app.zip')) / 2 ** 20), 'MB')

# 1. install into "Nik's Games" (apostrophe + space), logos kept with the app
parent = os.path.join(work, "D drive", "Nik's Games")
check(I.previous_install() == old, 'old install found without an Installed-apps entry')
t = time.time(); exe = I.install(parent, desktop=False, keep_data=True)
target = os.path.join(parent, I.FOLDER)
print(f'installed in {time.time() - t:.1f} s')
check(exe == os.path.join(target, I.EXE) and os.path.isfile(exe), 'app installed in its own folder')
check(os.path.isfile(os.path.join(target, 'data', 'settings.json')) and os.path.isdir(os.path.join(target, 'data', 'logos')),
      'logos and settings copied next to the app')
check(len(os.listdir(os.path.join(target, 'data', 'logos'))) == len(os.listdir(os.path.join(I.APPDATA_DIR, 'logos'))), 'every logo copied')
check(os.path.isdir(I.APPDATA_DIR), 'old AppData copy left alone')
check(not os.path.exists(old), 'old program folder removed')
check(not os.path.exists(os.path.join(DESK, I.APP + '.lnk')), 'old desktop shortcut (to the removed program) gone')
lnk = os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs', I.APP + '.lnk')
check(os.path.isfile(lnk), 'Start menu shortcut made')
check(reg_location() == target, 'Installed-apps entry points at the new folder')
check(os.path.isfile(os.path.join(target, 'uninstall.ps1')), 'uninstaller written')
check(I.previous_install() == target, 'next update offers this folder')

# 2. the installed app uses the data folder next to it (its AppData is empty here)
empty = os.path.join(work, 'EmptyRoaming'); os.makedirs(empty)
env = dict(os.environ, APPDATA=empty, TEMP=r'D:\ClaudeData\tmp', TMP=r'D:\ClaudeData\tmp')
p = subprocess.Popen([exe], cwd=target, env=env)
ghosts = os.path.join(target, 'data', 'ghosts')
for _ in range(60):
    if os.path.isdir(ghosts) and os.listdir(ghosts): break
    time.sleep(0.5)
time.sleep(1)
check(p.poll() is None, 'installed app is running')
check(os.path.isdir(ghosts) and bool(os.listdir(ghosts)), 'app saved its ghost in the data folder')
check(not os.listdir(empty), 'app wrote nothing to AppData')
p.kill(); p.wait()

# 3. update in place: what the user added is kept
open(os.path.join(target, 'data', 'logos', 'added_after_install.png'), 'wb').write(b'x')
open(os.path.join(target, 'stray_old_file.txt'), 'w').write('x')
I.install(parent, desktop=False, keep_data=True)
check(os.path.isfile(os.path.join(target, 'data', 'logos', 'added_after_install.png')), 'update kept the data folder')
check(not os.path.exists(os.path.join(target, 'stray_old_file.txt')) and os.path.isfile(exe), 'update replaced the program')

# 4. uninstall with the uninstaller it wrote
subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', os.path.join(target, 'uninstall.ps1')],
               check=True, creationflags=0x08000000, timeout=120)
check(not os.path.exists(lnk), 'uninstall removed the Start menu shortcut')
check(reg_location() is None, 'uninstall removed the Installed-apps entry')
check(not os.path.exists(exe) and not os.path.exists(os.path.join(target, '_internal')), 'uninstall removed the program')
check(os.path.isfile(os.path.join(target, 'data', 'logos', 'added_after_install.png')), 'uninstall kept the logos and settings')

# 5. installed WITHOUT keeping logos with the app: it uses AppData as before; desktop shortcut this time
parent2 = os.path.join(work, 'Other')
exe2 = I.install(parent2, desktop=True, keep_data=False)
target2 = os.path.join(parent2, I.FOLDER)
check(not os.path.exists(os.path.join(target2, 'data')), 'no data folder when not ticked')
check(os.path.isfile(os.path.join(DESK, I.APP + '.lnk')), 'desktop shortcut made')
shutil.rmtree(os.path.join(I.APPDATA_DIR, 'ghosts'), ignore_errors=True)
p = subprocess.Popen([exe2], cwd=target2, env=dict(os.environ, TEMP=r'D:\ClaudeData\tmp', TMP=r'D:\ClaudeData\tmp'))
g2 = os.path.join(I.APPDATA_DIR, 'ghosts')
for _ in range(60):
    if os.path.isdir(g2) and os.listdir(g2): break
    time.sleep(0.5)
check(os.path.isdir(g2) and bool(os.listdir(g2)), 'app uses AppData when not ticked')
p.kill(); p.wait()
subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', os.path.join(target2, 'uninstall.ps1')],
               check=True, creationflags=0x08000000, timeout=120)
check(not os.path.exists(target2), 'uninstall removed the whole folder (nothing kept in it)')
check(not os.path.exists(os.path.join(DESK, I.APP + '.lnk')), 'uninstall removed the desktop shortcut')
check(os.path.isfile(os.path.join(I.APPDATA_DIR, 'settings.json')), 'AppData logos and settings kept')
try: winreg.DeleteKey(winreg.HKEY_CURRENT_USER, DUMMY)
except OSError: pass
check((os.stat(REAL_LINK).st_mtime_ns if os.path.exists(REAL_LINK) else None) == _real, "the user's real desktop shortcut untouched")
print('PROBLEMS:', problems or 'none')

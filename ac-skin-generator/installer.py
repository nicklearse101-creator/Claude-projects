"""Ratty's4Skin Generator - installer.
Installs for the current user (no admin), into a folder they choose (default %LOCALAPPDATA%\\Programs); the app always
gets its own Rattys4SkinGenerator folder inside it. Optionally the logos, settings and saved ghosts are kept there too
(a "data" folder next to the app, copied from %APPDATA%\\Rattys4SkinGenerator), so nothing has to live on C:.
Adds Desktop and Start-menu shortcuts and an entry in Windows "Installed apps" for removing it.
Updates and the uninstaller never delete the data folder; moving the app to another folder removes the old program
files (not their data)."""
import os, subprocess, sys, zipfile, shutil, tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP = "Ratty's4Skin Generator"
FOLDER = 'Rattys4SkinGenerator'
EXE = 'Rattys4SkinGenerator.exe'
VERSION = '1.10.4'
DEFAULT_PARENT = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'Programs')
APPDATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), FOLDER)
UNINSTALL_KEY = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\Rattys4SkinGenerator'
DATA = 'data'


def res(name):
    return os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))), name)


def q(s):
    """A PowerShell single-quoted string."""
    return "'" + str(s).replace("'", "''") + "'"


def install_dir(parent):
    """The folder the app goes in: its own Rattys4SkinGenerator folder inside the one chosen (unless that is it)."""
    p = os.path.normpath(parent)
    return p if os.path.basename(p).lower() == FOLDER.lower() else os.path.join(p, FOLDER)


def check_target(target):
    """Refuse a folder that holds someone else's files (only an earlier install, or its kept data, may be there)."""
    if os.path.exists(target) and not os.path.isdir(target):
        raise ValueError(f'{target} is a file, not a folder. Pick another folder.')
    if os.path.isdir(target):
        others = [e for e in os.listdir(target) if e.lower() != DATA]
        if others and not os.path.isfile(os.path.join(target, EXE)):
            raise ValueError(f'{target} already has other files in it.\n\nPick another folder.')


def folder_size(d):
    return sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(d) for f in fs) if d and os.path.isdir(d) else 0


def data_source(target, appdata, old_target=None):
    """Where the logos and settings to copy come from: an earlier install's own data folder, else %APPDATA%."""
    for d in ((os.path.join(old_target, DATA) if old_target else None), appdata):
        if d and os.path.isdir(d) and os.path.normcase(os.path.abspath(d)) != os.path.normcase(os.path.join(os.path.abspath(target), DATA)):
            return d
    return None


def space_needed(zip_path, data_src, keep_data):
    with zipfile.ZipFile(zip_path) as z:
        n = sum(i.file_size for i in z.infolist())
    return n + (folder_size(data_src) if keep_data else 0) + 10 * 2 ** 20


def check_space(target, need):
    d = os.path.abspath(target)
    while not os.path.isdir(d) and os.path.dirname(d) != d:
        d = os.path.dirname(d)
    free = shutil.disk_usage(d).free
    if free < need:
        raise ValueError(f'Not enough free space on {os.path.splitdrive(d)[0] or d}: '
                         f'it needs {need / 2 ** 20:.0f} MB, {free / 2 ** 20:.0f} MB is free.')


def remove_program(folder):
    """Everything in an install folder except its data folder."""
    for e in os.listdir(folder):
        if e.lower() == DATA: continue
        p = os.path.join(folder, e)
        if os.path.isdir(p) and not os.path.islink(p): shutil.rmtree(p)
        else: os.remove(p)


def install_files(zip_path, target, keep_data, appdata, old_target=None):
    """The files part of an install (no shortcuts, no registry). Returns the app's exe."""
    check_target(target)
    data_t = os.path.join(target, DATA)
    # 1. the logos and settings first, before anything is removed
    if keep_data and not os.path.isdir(data_t):
        src = data_source(target, appdata, old_target)
        os.makedirs(target, exist_ok=True)
        if src: shutil.copytree(src, data_t)
        else: os.makedirs(data_t)
    # 2. the program: an earlier one here is replaced; the data folder stays as it is
    if os.path.isdir(target): remove_program(target)
    os.makedirs(target, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(target, [m for m in z.namelist() if m.split('/')[0].lower() != DATA])
    # 3. an earlier install in another folder: its program goes, its data folder never does
    if (old_target and os.path.normcase(os.path.abspath(old_target)) != os.path.normcase(os.path.abspath(target))
            and os.path.isfile(os.path.join(old_target, EXE))):
        remove_program(old_target)
        try: os.rmdir(old_target)                    # gone if nothing was kept there
        except OSError: pass
    return os.path.join(target, EXE)


def uninstall_script(target, links, key=UNINSTALL_KEY, message=True, data_dir=None):
    """PowerShell that removes the shortcuts, the Installed-apps entry and the program - never the data folder."""
    t = []
    t.append('$ErrorActionPreference = "SilentlyContinue"')
    t += [f'Remove-Item -LiteralPath {q(l)}' for l in links]
    t.append(f'Remove-Item -LiteralPath {q("HKCU:" + chr(92) + key)} -Recurse')
    t.append('Start-Sleep -Seconds 1')
    t.append(f'$t = {q(target)}')
    t.append("Get-ChildItem -LiteralPath $t -Force | Where-Object { $_.Name -ne 'data' } | Remove-Item -Recurse -Force")
    t.append("if (-not (Test-Path -LiteralPath (Join-Path $t 'data'))) { Remove-Item -LiteralPath $t -Recurse -Force }")
    if message:
        where = data_dir or ('%APPDATA%' + chr(92) + FOLDER)
        t.append('Add-Type -AssemblyName PresentationFramework')
        t.append(f'[System.Windows.MessageBox]::Show({q(f"{APP} has been removed. Your logos and settings stay in {where}.")}) | Out-Null')
    return '\n'.join(t) + '\n'


def shortcut(path, target, icon):
    ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut({q(path)});"
          f"$s.TargetPath={q(target)};$s.WorkingDirectory={q(os.path.dirname(target))};"
          f"$s.IconLocation={q(icon + ',0')};$s.Description={q(APP)};$s.Save()")
    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps],
                   check=True, creationflags=0x08000000)


def desktop_dir():
    """The user's desktop folder (also when OneDrive or Windows has moved it)."""
    d = os.path.join(os.path.expanduser('~'), 'Desktop')
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as k:
            d = os.path.expandvars(winreg.QueryValueEx(k, 'Desktop')[0])
    except OSError:
        pass
    return d


def registered_location():
    """The folder of the install Windows knows about (an earlier version), or None."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as k:
            v = winreg.QueryValueEx(k, 'InstallLocation')[0]
            return v or None
    except OSError:
        return None


def previous_install():
    """The folder of an earlier install: the one Windows knows about, else ours in the default place (an install whose
    Installed-apps entry has gone missing)."""
    reg = registered_location()
    if reg: return reg
    d = os.path.join(DEFAULT_PARENT, FOLDER)
    return d if os.path.isfile(os.path.join(d, EXE)) else None


def install(parent, desktop=True, keep_data=True):
    target = install_dir(parent)
    old = previous_install()
    check_target(target)
    check_space(target, space_needed(res('app.zip'), data_source(target, APPDATA_DIR, old), keep_data))
    exe = install_files(res('app.zip'), target, keep_data, APPDATA_DIR, old_target=old)
    links = [os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs', APP + '.lnk')]
    desk = os.path.join(desktop_dir(), APP + '.lnk')
    moved = old and os.path.normcase(os.path.abspath(old)) != os.path.normcase(os.path.abspath(target))
    if desktop:
        links.append(desk)
    elif moved and os.path.isfile(desk):
        os.remove(desk)                              # it pointed at the program that was just removed
    for l in links:
        shortcut(l, exe, exe)
    data_dir = os.path.join(target, DATA) if os.path.isdir(os.path.join(target, DATA)) else None
    un = os.path.join(target, 'uninstall.ps1')
    with open(un, 'w', encoding='utf8') as f:
        f.write(uninstall_script(target, links, data_dir=data_dir))
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as k:
        for n, v in (('DisplayName', APP), ('DisplayVersion', VERSION), ('Publisher', "Ratty's Racing"),
                     ('DisplayIcon', exe), ('InstallLocation', target),
                     ('UninstallString', f'powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{un}"')):
            winreg.SetValueEx(k, n, 0, winreg.REG_SZ, v)
        winreg.SetValueEx(k, 'NoModify', 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(k, 'NoRepair', 0, winreg.REG_DWORD, 1)
    return exe


class Setup(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f'Install {APP}')
        self.geometry('560x470'); self.resizable(False, False)
        try: self.iconbitmap(res('app.ico'))
        except Exception: pass
        f = ttk.Frame(self, padding=18); f.pack(fill='both', expand=True)
        try:
            from PIL import Image, ImageTk
            im = Image.open(res('app_icon.png')); im.thumbnail((84, 84))
            self.logo = ImageTk.PhotoImage(im); ttk.Label(f, image=self.logo).pack()
        except Exception: pass
        ttk.Label(f, text=APP, font=('Segoe UI', 15, 'bold')).pack(pady=(4, 0))
        ttk.Label(f, text=f'Version {VERSION} - livery maker for Assetto Corsa cars').pack()
        ttk.Label(f, text='Install to:').pack(anchor='w', pady=(14, 2))
        row = ttk.Frame(f); row.pack(fill='x')
        reg = previous_install()                        # an update goes where the last version is, unless changed
        start = os.path.dirname(os.path.normpath(reg)) if reg and os.path.basename(os.path.normpath(reg)).lower() == FOLDER.lower() \
            else (reg or DEFAULT_PARENT)
        self.parent = tk.StringVar(value=start)
        ttk.Entry(row, textvariable=self.parent).pack(side='left', fill='x', expand=True)
        ttk.Button(row, text='Change…', command=self.pick).pack(side='left', padx=(6, 0))
        self.where = ttk.Label(f, text='', foreground='#666', wraplength=520, justify='left')
        self.where.pack(anchor='w', pady=(4, 8))
        self.keep = tk.BooleanVar(value=True)
        self.keep_box = ttk.Checkbutton(f, text='Keep my logos and settings in that folder too', variable=self.keep)
        self.keep_box.pack(anchor='w')
        self.keep_note = ttk.Label(f, text='', foreground='#666', wraplength=470, justify='left')
        self.keep_note.pack(anchor='w', padx=(22, 0))
        self.desk = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text='Put a shortcut on the desktop', variable=self.desk).pack(anchor='w', pady=(6, 0))
        self.btn = ttk.Button(f, text='Install', command=self.go); self.btn.pack(pady=14, ipadx=20, ipady=3)
        self.parent.trace_add('write', lambda *a: self.refresh())
        self.refresh()

    def set_parent(self, p):
        self.parent.set(p)

    def refresh(self):
        p = self.parent.get().strip()
        if not p:
            self.where.configure(text=''); return
        t = install_dir(p)
        self.where.configure(text=f'The app goes in {t}')
        if os.path.isdir(os.path.join(t, DATA)):
            self.keep.set(True); self.keep_box.state(['disabled'])
            self.keep_note.configure(text=f'Your logos and settings are already kept in {os.path.join(t, DATA)}.')
        else:
            self.keep_box.state(['!disabled'])
            self.keep_note.configure(text=(f'Copied from {APPDATA_DIR} (the old copy is left there). ' if os.path.isdir(APPDATA_DIR)
                                           else '') + 'Updates and removing the app never delete them.')

    def pick(self):
        d = filedialog.askdirectory(parent=self, title='Where should the app go?', mustexist=False,
                                    initialdir=self.parent.get() if os.path.isdir(self.parent.get()) else DEFAULT_PARENT)
        if d: self.set_parent(os.path.normpath(d))

    def go(self):
        parent = self.parent.get().strip()
        drive = os.path.splitdrive(parent)[0]
        if not parent or not os.path.isabs(parent) or not drive or not os.path.isdir(drive + os.sep):
            messagebox.showerror(APP, f'"{parent}" is not a folder on this PC.\n\nPress Change… to pick one.'); return
        self.btn.state(['disabled']); self.btn.configure(text='Installing…'); self.update()
        try:
            exe = install(parent, self.desk.get(), self.keep.get())
        except Exception as e:
            messagebox.showerror(APP, f'Install failed:\n{e}'); self.btn.state(['!disabled']); self.btn.configure(text='Install'); return
        if messagebox.askyesno(APP, f'{APP} is installed in {os.path.dirname(exe)}.\n\nOpen it now?'):
            subprocess.Popen([exe], cwd=os.path.dirname(exe))
        self.destroy()


if __name__ == '__main__':
    Setup().mainloop()

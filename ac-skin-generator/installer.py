"""Ratty's4Skin Generator - installer.
Installs for the current user (no admin): %LOCALAPPDATA%\\Programs\\Rattys4SkinGenerator,
adds Desktop and Start-menu shortcuts and an entry in Windows "Installed apps" for removing it."""
import os, subprocess, sys, zipfile, shutil, tkinter as tk
from tkinter import ttk, messagebox

APP = "Ratty's4Skin Generator"
FOLDER = 'Rattys4SkinGenerator'
EXE = 'Rattys4SkinGenerator.exe'
VERSION = '1.3.0'
TARGET = os.path.join(os.environ['LOCALAPPDATA'], 'Programs', FOLDER)
UNINSTALL_KEY = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\Rattys4SkinGenerator'


def res(name):
    return os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))), name)


def shortcut(path, target, icon):
    ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{path}');"
          f"$s.TargetPath='{target}';$s.WorkingDirectory='{os.path.dirname(target)}';"
          f"$s.IconLocation='{icon},0';$s.Description='{APP}';$s.Save()").replace("'s4", "''s4")
    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps],
                   check=True, creationflags=0x08000000)


def install(desktop=True):
    if os.path.isdir(TARGET):
        shutil.rmtree(TARGET, ignore_errors=True)
    os.makedirs(TARGET, exist_ok=True)
    with zipfile.ZipFile(res('app.zip')) as z:
        z.extractall(TARGET)
    exe = os.path.join(TARGET, EXE)
    links = [os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs', APP + '.lnk')]
    if desktop:
        links.append(os.path.join(os.path.expanduser('~'), 'Desktop', APP + '.lnk'))
        try:   # OneDrive-redirected desktops
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as k:
                d = os.path.expandvars(winreg.QueryValueEx(k, 'Desktop')[0])
                if os.path.normcase(d) != os.path.normcase(os.path.dirname(links[-1])):
                    links[-1] = os.path.join(d, APP + '.lnk')
        except OSError:
            pass
    for l in links:
        shortcut(l, exe, exe)
    # uninstaller
    un = os.path.join(TARGET, 'uninstall.ps1')
    with open(un, 'w', encoding='utf8') as f:
        f.write('$ErrorActionPreference = "SilentlyContinue"\n')
        for l in links:
            f.write(f"Remove-Item -LiteralPath '{l.replace(chr(39), chr(39) * 2)}'\n")
        f.write(f"Remove-Item -LiteralPath 'HKCU:\\{UNINSTALL_KEY}' -Recurse\n")
        f.write(f"Start-Sleep -Seconds 1\nRemove-Item -LiteralPath '{TARGET}' -Recurse -Force\n")
        f.write(f"Add-Type -AssemblyName PresentationFramework\n"
                f"[System.Windows.MessageBox]::Show('{APP.replace(chr(39), chr(39) * 2)} has been removed. "
                f"Your logos and settings stay in %APPDATA%\\{FOLDER}.') | Out-Null\n")
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as k:
        for n, v in (('DisplayName', APP), ('DisplayVersion', VERSION), ('Publisher', "Ratty's Racing"),
                     ('DisplayIcon', exe), ('InstallLocation', TARGET),
                     ('UninstallString', f'powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{un}"')):
            winreg.SetValueEx(k, n, 0, winreg.REG_SZ, v)
        winreg.SetValueEx(k, 'NoModify', 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(k, 'NoRepair', 0, winreg.REG_DWORD, 1)
    return exe


class Setup(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f'Install {APP}')
        self.geometry('460x300'); self.resizable(False, False)
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
        ttk.Label(f, text=f'Installs to {TARGET}', foreground='#666', wraplength=420).pack(pady=8)
        self.desk = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text='Put a shortcut on the desktop', variable=self.desk).pack()
        self.btn = ttk.Button(f, text='Install', command=self.go); self.btn.pack(pady=12, ipadx=20, ipady=3)

    def go(self):
        self.btn.state(['disabled']); self.btn.configure(text='Installing…'); self.update()
        try:
            exe = install(self.desk.get())
        except Exception as e:
            messagebox.showerror(APP, f'Install failed:\n{e}'); self.btn.state(['!disabled']); self.btn.configure(text='Install'); return
        if messagebox.askyesno(APP, f'{APP} is installed.\n\nOpen it now?'):
            subprocess.Popen([exe], cwd=os.path.dirname(exe))
        self.destroy()


if __name__ == '__main__':
    Setup().mainloop()

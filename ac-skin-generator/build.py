"""Build Ratty's4Skin Generator for sharing:
  dist/Rattys4SkinGenerator/            the app (folder with Rattys4SkinGenerator.exe)
  release/Rattys4SkinGenerator_Setup.exe the one-file installer to send to people
Run:  python build.py      (needs: pip install pyinstaller pillow numpy)"""
import os, shutil, subprocess, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, 'build')
DIST = os.path.join(HERE, 'dist')
REL = os.path.join(HERE, 'release')


def pyi(*args):
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--log-level', 'WARN',
                    '--workpath', WORK, '--distpath', DIST, '--specpath', WORK, *args], check=True, cwd=HERE)


def main():
    ico = os.path.join(HERE, 'app.ico'); png = os.path.join(HERE, 'app_icon.png')
    if not os.path.isfile(png):     # PNGs are not kept in git: make it from the icon
        from PIL import Image
        Image.open(ico).convert('RGBA').save(png)
    # 1. the app (with the starter logos, if make_starter_logos.py has been run)
    st = os.path.join(HERE, 'starter_logos')
    extra = ['--add-data', f'{st};starter_logos'] if os.path.isfile(os.path.join(st, 'starter.json')) else []
    pyi('--windowed', '--name', 'Rattys4SkinGenerator', '--icon', ico,
        '--add-data', f'{ico};.', '--add-data', f'{png};.', *extra,
        '--exclude-module', 'matplotlib', '--exclude-module', 'scipy', '--exclude-module', 'pandas',
        os.path.join(HERE, 'rattys4skin.py'))
    app_dir = os.path.join(DIST, 'Rattys4SkinGenerator')
    # 2. zip it into the installer
    zpath = os.path.join(WORK, 'app.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, _, files in os.walk(app_dir):
            for f in files:
                full = os.path.join(root, f)
                z.write(full, os.path.relpath(full, app_dir))
    pyi('--onefile', '--windowed', '--name', 'Rattys4SkinGenerator_Setup', '--icon', ico,
        '--add-data', f'{zpath};.', '--add-data', f'{ico};.', '--add-data', f'{png};.',
        '--exclude-module', 'numpy', os.path.join(HERE, 'installer.py'))
    os.makedirs(REL, exist_ok=True)
    shutil.move(os.path.join(DIST, 'Rattys4SkinGenerator_Setup.exe'), os.path.join(REL, 'Rattys4SkinGenerator_Setup.exe'))
    size = os.path.getsize(os.path.join(REL, 'Rattys4SkinGenerator_Setup.exe')) / 1e6
    print(f'installer: release/Rattys4SkinGenerator_Setup.exe ({size:.0f} MB)')


if __name__ == '__main__':
    main()

"""Installer (v1.9.0): choose the folder, keep logos and settings with the app, updates and uninstall never lose them.
Only touches folders under the pytest temp folder (D:) and a dummy registry key; never installs for real.
python -m pytest -p no:cacheprovider tests/test_installer.py -q --basetemp=D:\\ClaudeData\\tmp\\pytest"""
import os, subprocess, sys, zipfile
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import installer as I


def app_zip(path, version='new'):
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr(I.EXE, version)
        z.writestr('_internal/lib.dll', version)
    return str(path)


def data(folder, logo='mine.png'):
    os.makedirs(os.path.join(folder, 'logos'), exist_ok=True)
    open(os.path.join(folder, 'settings.json'), 'w').write('{"base": "#ff6a00"}')
    open(os.path.join(folder, 'logos', logo), 'wb').write(b'png')
    return str(folder)


def test_install_dir_always_own_folder():
    assert I.install_dir('D:\\Games') == os.path.join('D:\\Games', I.FOLDER)
    assert I.install_dir('D:\\') == os.path.join('D:\\', I.FOLDER)
    assert I.install_dir(os.path.join('D:\\Games', I.FOLDER)) == os.path.join('D:\\Games', I.FOLDER)
    assert I.install_dir(os.path.join('D:\\Games', I.FOLDER.lower()) + '\\') == os.path.join('D:\\Games', I.FOLDER.lower())


def test_check_target_refuses_someone_elses_folder(tmp_path):
    I.check_target(str(tmp_path / 'new'))                     # not there yet: fine
    os.makedirs(tmp_path / 'empty'); I.check_target(str(tmp_path / 'empty'))
    os.makedirs(tmp_path / 'other'); open(tmp_path / 'other' / 'notes.txt', 'w').write('x')
    with pytest.raises(ValueError):
        I.check_target(str(tmp_path / 'other'))
    os.makedirs(tmp_path / 'ours'); open(tmp_path / 'ours' / I.EXE, 'w').write('old')
    I.check_target(str(tmp_path / 'ours'))                    # an earlier install: fine


def test_fresh_install_copies_my_data(tmp_path):
    t = str(tmp_path / 'D' / I.FOLDER)
    I.install_files(app_zip(tmp_path / 'app.zip'), t, keep_data=True, appdata=data(tmp_path / 'appdata'))
    assert open(os.path.join(t, I.EXE)).read() == 'new'
    assert os.path.isfile(os.path.join(t, 'data', 'logos', 'mine.png'))
    assert os.path.isfile(os.path.join(tmp_path, 'appdata', 'settings.json'))    # the old copy is left alone


def test_fresh_install_without_data_option(tmp_path):
    t = str(tmp_path / I.FOLDER)
    I.install_files(app_zip(tmp_path / 'app.zip'), t, keep_data=False, appdata=data(tmp_path / 'appdata'))
    assert not os.path.exists(os.path.join(t, 'data'))


def test_no_data_yet_gives_empty_data_folder(tmp_path):
    t = str(tmp_path / I.FOLDER)
    I.install_files(app_zip(tmp_path / 'app.zip'), t, keep_data=True, appdata=str(tmp_path / 'none'))
    assert os.path.isdir(os.path.join(t, 'data'))


def test_update_keeps_data_and_replaces_program(tmp_path):
    t = str(tmp_path / I.FOLDER)
    I.install_files(app_zip(tmp_path / 'a1.zip', 'v1'), t, keep_data=True, appdata=data(tmp_path / 'appdata'))
    open(os.path.join(t, 'data', 'logos', 'added_later.png'), 'wb').write(b'x')
    open(os.path.join(t, 'stale_old_file.txt'), 'w').write('x')
    I.install_files(app_zip(tmp_path / 'a2.zip', 'v2'), t, keep_data=True, appdata=data(tmp_path / 'appdata', 'other.png'))
    assert open(os.path.join(t, I.EXE)).read() == 'v2'
    assert not os.path.exists(os.path.join(t, 'stale_old_file.txt'))
    assert os.path.isfile(os.path.join(t, 'data', 'logos', 'added_later.png'))     # what was there is kept as it is
    assert not os.path.exists(os.path.join(t, 'data', 'logos', 'other.png'))


def test_moving_install_removes_old_program_keeps_old_data(tmp_path):
    old = str(tmp_path / 'C' / I.FOLDER)
    I.install_files(app_zip(tmp_path / 'a1.zip', 'v1'), old, keep_data=True, appdata=data(tmp_path / 'appdata'))
    open(os.path.join(old, 'data', 'logos', 'only_in_old_install.png'), 'wb').write(b'x')
    new = str(tmp_path / 'D' / I.FOLDER)
    I.install_files(app_zip(tmp_path / 'a2.zip', 'v2'), new, keep_data=True, appdata=str(tmp_path / 'appdata'), old_target=old)
    assert os.path.isfile(os.path.join(new, 'data', 'logos', 'only_in_old_install.png'))   # the install's own data wins
    assert not os.path.exists(os.path.join(old, I.EXE)) and not os.path.exists(os.path.join(old, '_internal'))
    assert os.path.isfile(os.path.join(old, 'data', 'logos', 'only_in_old_install.png'))   # never deleted


def test_old_location_not_ours_is_left_alone(tmp_path):
    old = tmp_path / 'somewhere'; os.makedirs(old); open(old / 'precious.txt', 'w').write('x')
    I.install_files(app_zip(tmp_path / 'a.zip'), str(tmp_path / I.FOLDER), keep_data=False, appdata=str(tmp_path / 'x'),
                    old_target=str(old))
    assert os.path.isfile(old / 'precious.txt')


def test_space_check(tmp_path):
    z = app_zip(tmp_path / 'a.zip')
    need = I.space_needed(z, data(tmp_path / 'appdata'), keep_data=True)
    assert need >= len('new') * 2 + len('png')
    with pytest.raises(ValueError):
        I.check_space(str(tmp_path), 10 ** 15)
    I.check_space(str(tmp_path / 'not' / 'made' / 'yet'), 1)


def test_uninstaller_keeps_data(tmp_path):
    t = str(tmp_path / I.FOLDER)
    I.install_files(app_zip(tmp_path / 'a.zip'), t, keep_data=True, appdata=data(tmp_path / 'appdata'))
    link = tmp_path / 'shortcut.lnk'; link.write_text('x')
    ps = I.uninstall_script(t, [str(link)], key=r'Software\R4S_pytest_dummy_key_never_real', message=False)
    open(os.path.join(t, 'uninstall.ps1'), 'w', encoding='utf8').write(ps)
    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', os.path.join(t, 'uninstall.ps1')],
                   check=True, creationflags=0x08000000, timeout=60)
    assert not link.exists() and not os.path.exists(os.path.join(t, I.EXE))
    assert os.path.isfile(os.path.join(t, 'data', 'logos', 'mine.png'))


def test_uninstaller_removes_folder_when_no_data(tmp_path):
    t = str(tmp_path / I.FOLDER)
    I.install_files(app_zip(tmp_path / 'a.zip'), t, keep_data=False, appdata=str(tmp_path / 'x'))
    ps = I.uninstall_script(t, [], key=r'Software\R4S_pytest_dummy_key_never_real', message=False)
    open(os.path.join(t, 'uninstall.ps1'), 'w', encoding='utf8').write(ps)
    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', os.path.join(t, 'uninstall.ps1')],
                   check=True, creationflags=0x08000000, timeout=60)
    assert not os.path.exists(t)


def test_uninstaller_message_names_data_place():
    ps = I.uninstall_script(r'D:\Games\Rattys4SkinGenerator', [], key='Software\\x', message=True, data_dir=r'D:\Games\Rattys4SkinGenerator\data')
    assert r'D:\Games\Rattys4SkinGenerator\data' in ps


def test_window(monkeypatch, tmp_path):
    got = []
    monkeypatch.setattr(I, 'registered_location', lambda: None)
    monkeypatch.setattr(I, 'install', lambda parent, desktop=True, keep_data=True: got.append((parent, desktop, keep_data)) or 'x.exe')
    monkeypatch.setattr(I.messagebox, 'askyesno', lambda *a, **k: False)
    w = I.Setup(); w.update()
    assert w.parent.get() == I.DEFAULT_PARENT and w.keep.get() is True
    w.set_parent(str(tmp_path)); w.update()
    assert os.path.join(str(tmp_path), I.FOLDER) in w.where.cget('text')
    os.makedirs(tmp_path / I.FOLDER / 'data')
    w.set_parent(str(tmp_path)); w.update()
    assert w.keep.get() is True and 'disabled' in w.keep_box.state()       # logos already kept there: stays on
    w.go()
    assert got == [(str(tmp_path), True, True)]


def test_window_defaults_to_registered_install(monkeypatch, tmp_path):
    monkeypatch.setattr(I, 'registered_location', lambda: str(tmp_path / 'Apps' / I.FOLDER))
    w = I.Setup(); w.update()
    assert w.parent.get() == str(tmp_path / 'Apps')
    w.destroy()


def test_app_uses_data_folder_next_to_it(tmp_path):
    import rattys4skin as R
    appdata = str(tmp_path / 'Roaming')
    assert R.find_data_dir(None, appdata) == os.path.join(appdata, I.FOLDER)            # run from source: as before
    exe_dir = tmp_path / 'D' / I.FOLDER; os.makedirs(exe_dir)
    assert R.find_data_dir(str(exe_dir), appdata) == os.path.join(appdata, I.FOLDER)   # installed without the option
    os.makedirs(exe_dir / 'data')
    assert R.find_data_dir(str(exe_dir), appdata) == str(exe_dir / 'data')


def test_previous_install_found_without_registry_entry(monkeypatch, tmp_path):
    """An install whose Installed-apps entry is gone is still found in the default place (and only if it is ours)."""
    monkeypatch.setattr(I, 'registered_location', lambda: None)
    monkeypatch.setattr(I, 'DEFAULT_PARENT', str(tmp_path / 'Programs'))
    assert I.previous_install() is None
    old = tmp_path / 'Programs' / I.FOLDER; os.makedirs(old)
    assert I.previous_install() is None                                       # a folder, but not our program
    open(old / I.EXE, 'w').write('old')
    assert I.previous_install() == str(old)
    monkeypatch.setattr(I, 'registered_location', lambda: r'D:\Elsewhere\Rattys4SkinGenerator')
    assert I.previous_install() == r'D:\Elsewhere\Rattys4SkinGenerator'      # the registered one comes first

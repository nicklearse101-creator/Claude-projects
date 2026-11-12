"""Every themed control in one window, saved as a picture (to check the look by eye).
python tests/theme_demo.py OUT.png"""
import os, sys, time
import tkinter as tk
from tkinter import ttk
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ctypes
try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception: pass
import theme
from PIL import ImageGrab

root = tk.Tk(); root.geometry('900x760+30+30'); root.attributes('-topmost', True)
theme.apply_style(root); theme.dark_title_bar(root)
hd = theme.Header(root, '1.8.0'); hd.pack(fill='x'); hd.set_car('Talbot Sunbeam Lotus', 'ratty_101')
body = ttk.Frame(root, style='Window.TFrame', padding=8); body.pack(fill='both', expand=True)
tabs = theme.SlantTabs(body); tabs.pack(fill='x', side='top')
p = tabs.add('Logos'); tabs.add('Car'); tabs.add('Lights & wheels'); tabs.select(0)
ttk.Label(p, text='Add your logos here; they stay in the library for next time.', style='Note.TLabel').pack(anchor='w')
tree = ttk.Treeview(p, columns=('place',), height=4, selectmode='browse')
tree.heading('#0', text='LOGO'); tree.heading('place', text='PLACE ON CAR')
for i, (n, pl) in enumerate((('Ratty Racing', 'Bonnet'), ('chucknorris', 'Doors (big)'), ('24h', 'Not used'), ('agip1', 'Not used'))):
    tree.insert('', 'end', iid=str(i), text='  ' + n, values=(pl,))
tree.pack(fill='x'); tree.selection_set('1')
row = ttk.Frame(p); row.pack(fill='x', pady=6)
for t, k in (('Add logos…', 'primary'), ('Remove', 'outline'), ('Clear all (not used)', 'outline')):
    theme.SlantButton(row, t, kind=k).pack(side='left', padx=1)
v1, v2 = tk.BooleanVar(value=True), tk.BooleanVar(value=False)
ttk.Checkbutton(p, text='Tint glow to highlight colour', variable=v1).pack(anchor='w')
ttk.Checkbutton(p, text='Keep logos off areas the car mirrors', variable=v2).pack(anchor='w')
f = ttk.Frame(p); f.pack(fill='x', pady=4)
ttk.Label(f, text='PLACE ON CAR', style='Field.TLabel', width=18).pack(side='left')
cb = ttk.Combobox(f, values=['Not used', 'Bonnet', 'Doors (big)'], state='readonly', width=20); cb.set('Doors (big)'); cb.pack(side='left')
f2 = ttk.Frame(p); f2.pack(fill='x', pady=4)
ttk.Label(f2, text='SKIN NAME', style='Field.TLabel', width=18).pack(side='left')
e = ttk.Entry(f2); e.insert(0, 'ratty_101'); e.pack(side='left', fill='x', expand=True)
ttk.Spinbox(f2, from_=8, to=25, width=5).pack(side='left', padx=6)
ttk.Label(p, text='ON THE CAR', style='Section.TLabel').pack(anchor='w', pady=(6, 0))
lf = ttk.LabelFrame(p, text='On the car'); lf.pack(fill='x')
ttk.Label(lf, text='chucknorris  -  Doors (big)').pack(anchor='w')
bb = ttk.Frame(body, style='Window.TFrame'); bb.pack(fill='x', pady=6)
theme.SlantButton(bb, 'Preview', kind='secondary', size=19, height=40).pack(side='left')
theme.SlantButton(bb, 'Create skin in car', kind='primary', size=21, height=40, width=330).pack(side='left')
pb = ttk.Progressbar(body, style='Orange.Horizontal.TProgressbar', value=66); pb.pack(fill='x')
ttk.Label(body, text='Stage 4 / 6 - logos', style='Status.TLabel').pack(anchor='w')
var = tk.StringVar(value='left')
theme.ChipGroup(body, [('all', 'All sides'), ('left', 'Left'), ('right', 'Right'), ('top', 'Top')], var).pack(anchor='w')
for _ in range(15): root.update(); time.sleep(0.05)
x, y, w, h = root.winfo_rootx(), root.winfo_rooty(), root.winfo_width(), root.winfo_height()
ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(sys.argv[1])
root.destroy()
print('saved', sys.argv[1])

import json, sys, numpy as np, cv2
from PIL import Image
U='/mnt/user-data/uploads/vauxhall_nova_gte_1989/'
PH={'c20':U+'reference/photos/user_red_gte/redgte_20.webp','c22':U+'reference/photos/user_red_gte/redgte_22.webp',
    'c23':U+'reference/photos/user_red_gte/redgte_23.webp','c24':U+'reference/photos/user_red_gte/redgte_24.webp',
    'cAR':U+'reference/photos/other_sources/anglia_rear.jpg','cCF':U+'reference/photos/commons/1989_Vauxhall_Nova_GTE_1.6_Front.jpg',
    'cS':U+'reference/photos/other_sources/anglia_side.jpg'}
B=json.load(open('ba_result.json')); O=json.load(open('obs.json'))
exec(open('ba.py').read().split('# ---- initialisation')[0])   # reuse point/project helpers
P={k:np.array(v) for k,v in B['points'].items() if isinstance(v,list) and not k.startswith('PL')}
PL={k:np.array(v) for k,v in B['points'].items() if k.startswith('PL')}
r=B['points']['wheel_r_F400']
for c in (sys.argv[1:] or PH):
    ph=np.array(Image.open(PH[c]).convert('RGB')).astype(np.float32)
    rd=np.array(Image.open(U+f'export/match/{c}.png').convert('RGBA')).astype(np.float32)
    a=rd[...,3:4]/255*0.45
    out=ph*(1-a)+rd[...,:3]*a
    # model silhouette/feature edges in cyan
    g=cv2.cvtColor(rd[...,:3].astype(np.uint8),cv2.COLOR_RGB2GRAY); e=cv2.Canny(g,20,60)
    e=cv2.dilate(e,np.ones((2,2),np.uint8)) if ph.shape[1]>2000 else e
    out[e>0]=[0,255,255]
    # BA points (green) and the annotated photo points (red)
    cp=np.array(B['cams'][c]); W,H=O[c]['W'],O[c]['H']
    for n,xy in O[c]['pts'].items():
        X=pt3(n,P,PL,r)[None]; uv,_=project(cp,X,W,H)
        s=max(2,W//400)
        cv2.circle(out,tuple(int(v) for v in xy),s+1,(255,0,0),-1)
        cv2.circle(out,tuple(int(v) for v in uv[0]),s,(0,255,0),-1)
    im=Image.fromarray(np.clip(out,0,255).astype(np.uint8))
    im.thumbnail((1600,1200)); im.save(f'ov_{c}.jpg',quality=88)
    print('saved',c)

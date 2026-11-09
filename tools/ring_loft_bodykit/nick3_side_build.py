"""nick3_side_build.py - builds the NICK3 one-piece flared sides (sill + front arch + rear arch, boolean-united, one closed shell per side)
for the main model and LOD B/C/D, creates the Blender objects (parent / kn5 props copied from the old sill objects) and removes nothing.
Uses nick3_side (arch ring lofts), nick3_sill (sill ring loft). Run build_all(xfar_tabs) with xfar_tabs={'front':[(theta,x)..],'rear':[..]}
(far-edge x on the body per theta, smoothed medians measured from the v30 arches)."""
import bpy, bmesh, sys, math
sys.path.append(r"D:\Claude\escort_mk2_dtm\tools\blender")
import nick3_sill as ns, nick3_side as sd

LODS=[('main','Scene',2.5,0.0245),('B','LOD_B',4.0,0.045),('C','LOD_C',7.5,0.09),('D','LOD_D',15.0,0.135)]

MATERIAL_NAME = 'Material #25DQW'   # the car body's own paint material (skin-driven AO_BODY.dds, metal_detail.dds)
def _mat(): return bpy.data.materials[MATERIAL_NAME]
def _tmp_obj(bm,name,scene):
    me=bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(_mat())
    o=bpy.data.objects.new(name,me); scene.collection.objects.link(o); return o
def _union(a,b,name):
    m=a.modifiers.new('u','BOOLEAN'); m.operation='UNION'; m.solver='EXACT'; m.operand_type='OBJECT'; m.object=b
    ev=a.evaluated_get(bpy.context.evaluated_depsgraph_get()); me=bpy.data.meshes.new_from_object(ev); me.name=name
    a.modifiers.remove(m); return me

CREASE_DEG = 40.0
def smooth_bm(bm,crease_deg):
    """smooth shading with sharp edges only where the face angle exceeds crease_deg (exporter uses corner_normals, so this is what AC shows)"""
    lim=math.radians(crease_deg)
    for f in bm.faces: f.smooth=True
    for e in bm.edges:
        if len(e.link_faces)==2:
            try: a=e.calc_face_angle()
            except Exception: a=0.0
            e.smooth = a<=lim
        else: e.smooth=False

def side_mesh(xtabs,side,step_arch,step_sill,name,scene):
    fx={k:(lambda tab: (lambda y,z,th: sd.interp_tab(tab,th)))(v) for k,v in xtabs.items()}
    tF=_tmp_obj(sd.build_arch_bm('front',side,fx['front'],step_arch,fb=sd.FB),'TMP_F',scene)
    tR=_tmp_obj(sd.build_arch_bm('rear',side,fx['rear'],step_arch),'TMP_R',scene)
    tS=_tmp_obj(ns.build_bm(side,step_sill),'TMP_S',scene)
    m1=_union(tF,tS,name+'_m1'); t1=bpy.data.objects.new('TMP_1',m1); scene.collection.objects.link(t1)
    m2=_union(t1,tR,name)
    for o in (tF,tR,tS,t1):
        me=o.data; bpy.data.objects.remove(o); bpy.data.meshes.remove(me)
    bm=bmesh.new(); bm.from_mesh(m2); uv=bm.loops.layers.uv.verify()
    for f in bm.faces:
        for l in f.loops: l[uv].uv=sd.UVT
    smooth_bm(bm,CREASE_DEG)
    bm.to_mesh(m2); bm.free()
    if not m2.materials: m2.materials.append(_mat())
    return m2

def stats(me):
    bm=bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    be=sum(1 for e in bm.edges if e.is_boundary); nm=sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
    seen=set(); sh=0
    for f in bm.faces:
        if f.index in seen: continue
        sh+=1; st=[f]; seen.add(f.index)
        while st:
            g=st.pop()
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen: seen.add(h.index); st.append(h)
    vol=sum(f.calc_area()*(f.normal.dot(f.calc_center_median())) for f in bm.faces)/3
    r=dict(verts=len(bm.verts),faces=len(bm.faces),boundary=be,nonmanifold=nm,shells=sh,volume=round(vol,5)); bm.free(); return r

def build_all(xtabs):
    """returns {(lr,tag): (mesh, stats)}"""
    main=bpy.data.scenes['Scene']; out={}
    for tag,scn,sa,ss in LODS:
        for side,lr in ((1,'L'),(-1,'R')):
            me=side_mesh(xtabs,side,sa,ss,'SIDEMESH_%s_%s'%(lr,tag),main); out[(lr,tag)]=(me,stats(me))
    return out

def create_objects(meshes):
    """link new objects into the right scene; parent + kn5 props copied from the old sill object of the same scene/LOD"""
    made=[]
    for tag,scn,sa,ss in LODS:
        for lr in 'LR':
            tmpl=bpy.data.objects['NICK3_sill_%s'%lr if tag=='main' else 'NICK3_LOD_sill_%s_%s'%(lr,tag)]
            name='NICK3_side_%s'%lr if tag=='main' else 'NICK3_LOD_side_%s_%s'%(lr,tag)
            me=meshes[(lr,tag)][0]; me.name=name
            o=bpy.data.objects.new(name,me); bpy.data.scenes[scn].collection.objects.link(o)
            o.parent=tmpl.parent; o.matrix_parent_inverse=tmpl.matrix_parent_inverse.copy()
            for k in tmpl.keys(): o[k]=tmpl[k]
            o['kn5_name']=name; made.append(name)
    return made

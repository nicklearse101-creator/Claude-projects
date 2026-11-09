
"""nick3_sill.py - parametric flared side sill for the NICK3 kit (Blender 5.x).
Builds NICK3_sill_L/R (+ LOD B/C/D versions) as lofts: each ring = 16-pt profile (x,z) at a given y.
Mid profile starts buried under the door shut line (z~0.05, x~0.687) and flares out/down.
Ends blend (smoothstep over |y| Y_BLEND..Y_END) into a small profile embedded in the arch trailing lip.
Material NICK3_KIT_PAINT (body colour).  Left side is +X; right side mirrored."""
import bpy, bmesh, json
from mathutils import Vector

MID = [(0.670,0.060),(0.687,0.050),(0.720,0.041),(0.765,0.030),(0.810,0.017),(0.840,0.004),(0.855,-0.018),(0.858,-0.045),
       (0.850,-0.070),(0.828,-0.086),(0.780,-0.090),(0.700,-0.088),(0.620,-0.080),(0.600,-0.040),(0.620,0.020),(0.650,0.052)]
# end profile (embedded in arch trailing lip); same 16 points
def end_profile(sgn_front):
    return END_F if sgn_front else END_R
# v31: END rings fitted INSIDE the arch envelope at the end station (so no flat end face is left exposed where the sill runs into the arch tail).
# Fitted by ray-casting the new arch lofts (nick3_side) at y=-0.89 (front) / y=+0.87 (rear), x <= envelope - 4 mm; originals kept in nick3_sill.py.bak_v30.
END_F = [(0.735,0.25),(0.752,0.256),(0.79,0.262),(0.835,0.268),(0.8793,0.272),(0.8816,0.268),(0.8903,0.252),(0.9075,0.2),(0.9101,0.13),(0.8692,0.075),(0.8161,0.045),(0.7581,0.032),(0.7537,0.03),(0.745,0.034),(0.735,0.06),(0.733,0.15)]
END_R = [(0.735,0.25),(0.752,0.256),(0.79,0.262),(0.835,0.268),(0.8621,0.272),(0.8653,0.268),(0.8777,0.252),(0.9087,0.2),(0.9196,0.13),(0.905,0.075),(0.87,0.045),(0.82,0.032),(0.77,0.03),(0.745,0.034),(0.735,0.06),(0.733,0.15)]
Y_BLEND = 0.62   # flat sill runs to here (door shut line spans |y|<~0.66 front / 0.53 rear)
Y_END_F = 0.905
Y_END_R = 0.882
Y_END   = Y_END_F

def sstep(t):
    t=max(0.0,min(1.0,t)); return t*t*(3-2*t)

def _ys(yend,step_end):
    ys=[0.0,0.30,Y_BLEND]; n=int(round((yend-Y_BLEND)/step_end))
    return ys+[Y_BLEND+(yend-Y_BLEND)*i/n for i in range(1,n+1)]

def ring_ys(step_end):
    return sorted(set([-y for y in _ys(Y_END_F,step_end)]+_ys(Y_END_R,step_end)))     # y<0 = front

def ring(y):
    ye = Y_END_F if y<0 else Y_END_R
    t=sstep((abs(y)-Y_BLEND)/(ye-Y_BLEND))
    E=END_F if y<0 else END_R
    return [((1-t)*m[0]+t*e[0], (1-t)*m[1]+t*e[1]) for m,e in zip(MID,E)]

def build_bm(side, step_end):
    bm=bmesh.new(); uv=bm.loops.layers.uv.new("UVMap")
    ys=ring_ys(step_end); rings=[]
    for y in ys:
        rings.append([bm.verts.new((side*x,y,z)) for x,z in ring(y)])
    n=len(MID)
    for a,b in zip(rings[:-1],rings[1:]):
        for i in range(n):
            j=(i+1)%n
            vs=[a[i],a[j],b[j],b[i]]
            if side<0: vs=vs[::-1]
            bm.faces.new(vs)
    for r,flip in ((rings[0],True),(rings[-1],False)):
        vs=list(r)
        if (side<0)!=flip: vs=vs[::-1]
        bm.faces.new(vs)
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    for f in bm.faces:
        for l in f.loops:
            l[uv].uv=(0.21657872, 0.12241337)   # single body-paint texel of NICK3_KIT_ATLAS (same as arches) - NOT spread UVs (turned black in CM)
    return bm

def make_obj(name, side, step_end, scene, parent, tmpl):
    bm=build_bm(side,step_end)
    me=bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(bpy.data.materials["NICK3_KIT_PAINT"])
    ob=bpy.data.objects.new(name,me)
    scene.collection.objects.link(ob); ob.parent=parent
    for k in tmpl.keys(): ob[k]=tmpl[k]
    ob["kn5_name"]=name
    return ob

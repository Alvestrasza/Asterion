"""Asterion, fully volumetric reconstruction of the user-approved turnaround.

All visible surface detail is modeled or shaded in three dimensions. The
reference is preserved as evidence and is never used as a billboard texture.
Coordinates: X lateral, negative Y forward, Z up; L is positive X.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
TAU = math.tau
RNG = random.Random(93051)
ASSET = []
M = {}


def color(h):
    rgb = [int(h[i:i+2], 16)/255 for i in (0,2,4)]
    return tuple(c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in rgb)+(1,)


def material(name, hexcolor, metal=0, rough=.42, emission=0):
    m = bpy.data.materials.new('AST_'+name)
    m.use_nodes = True
    m.diffuse_color = color(hexcolor)
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = m.diffuse_color
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    p.inputs['Coat Weight'].default_value = .025 if metal else 0.0
    p.inputs['Specular IOR Level'].default_value = .36 if metal else .25
    p.inputs['Coat Roughness'].default_value = .32
    if emission:
        p.inputs['Emission Color'].default_value = m.diffuse_color
        p.inputs['Emission Strength'].default_value = emission
    return m


def materials():
    specs = {
        'navy':('06132C',0,.66), 'scale':('112443',0,.62),
        'scale_light':('193157',0,.60), 'scale_dark':('0A1C39',0,.64),
        'belly':('182D50',0,.64), 'armor':('071936',.25,.46),
        'gold':('C28B2C',.72,.39), 'gold_light':('E8B84F',.65,.35),
        'gold_dark':('84521D',.62,.43), 'ivory':('CEB68B',0,.60),
        'ivory_light':('E6CEA3',0,.57), 'ivory_dark':('9E8257',0,.62),
        'black':('010614',0,.29), 'sclera':('D3C89F',0,.30),
        'cyan':('0294EC',.10,.29), 'iris_dark':('004B93',.1,.30),
        'iris_light':('08C5FB',.1,.28), 'white':('FFFFFF',0,.20),
        'gem':('0065CF',.65,.23), 'gem_light':('009DEB',.60,.20),
        'gem_dark':('0357A4',.3,.2)
    }
    for k,s in specs.items():
        M[k] = material(k,*s,emission=.20 if k in ('cyan','gem','gem_light') else 0)
        # Keep the painted ivory and gold rich under the bright studio rig.
        factor = .58 if k.startswith('ivory') else .78 if k in ('gold','gold_light') else 1
        if factor != 1:
            p = M[k].node_tree.nodes.get('Principled BSDF')
            tint = tuple(v*factor for v in M[k].diffuse_color[:3])+(1,)
            M[k].diffuse_color = tint
            p.inputs['Base Color'].default_value = tint


def register(obj, name, mat, part='body', smooth=True):
    obj.name = 'AST_'+name
    obj['ast_part'] = part
    if mat:
        obj.data.materials.append(M[mat] if isinstance(mat,str) else mat)
    if obj.type == 'MESH':
        for p in obj.data.polygons: p.use_smooth = smooth
    ASSET.append(obj)
    return obj


def mesh(name, verts, faces, mat, part='body', smooth=True):
    me = bpy.data.meshes.new('AST_'+name+'_mesh')
    me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new('AST_'+name,me)
    bpy.context.collection.objects.link(o)
    return register(o,name,mat,part,smooth)


def active(o):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True); bpy.context.view_layer.objects.active=o


def apply(o, mod):
    active(o); bpy.ops.object.modifier_apply(modifier=mod.name)


def uv(name, pos, radii, mat='navy', part='body', seg=48, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,location=pos)
    o=bpy.context.object; o.scale=radii
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return register(o,name,mat,part)


def fuse(name, parts, part='body', voxel=.028, subdiv=1):
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]
    bpy.ops.object.join(); o=bpy.context.object
    for p in parts[1:]:
        if p in ASSET: ASSET.remove(p)
    o.name='AST_'+name; o['ast_part']=part
    m=o.modifiers.new('Sculpt union','REMESH'); m.mode='VOXEL'; m.voxel_size=voxel; m.use_smooth_shade=True
    apply(o,m)
    m=o.modifiers.new('Sculpt surface relaxation','SMOOTH');m.factor=1.05;m.iterations=7;apply(o,m)
    if subdiv:
        m=o.modifiers.new('Sculpt detail tessellation','SUBSURF');m.levels=subdiv;apply(o,m)
    for p in o.data.polygons:p.use_smooth=True
    return o


def spline(points, steps):
    pts=[Vector(p) for p in points]; result=[]
    for j in range(steps+1):
        t=j/steps*(len(pts)-1); i=min(int(t),len(pts)-2); f=t-i
        a=pts[max(i-1,0)];b=pts[i];c=pts[i+1];d=pts[min(i+2,len(pts)-1)]
        result.append(.5*((2*b)+(-a+c)*f+(2*a-5*b+4*c-d)*f*f+(-a+3*b-3*c+d)*f*f*f))
    return result


def interpolate(values,t):
    f=t*(len(values)-1);i=min(int(f),len(values)-2);w=f-i
    return values[i]*(1-w)+values[i+1]*w


def sweep(name, points, widths, depths, mat, part, normal=(1,0,0), steps=44, sides=32, flute=0, ridge=0):
    cs=spline(points,steps); n0=Vector(normal).normalized();vs=[];fs=[]
    for i,c in enumerate(cs):
        tangent=(cs[min(i+1,steps)]-cs[max(i-1,0)]).normalized()
        n=(n0-tangent*n0.dot(tangent)).normalized()
        u=tangent.cross(n).normalized()
        w=max(.0004,interpolate(widths,i/steps));d=max(.0004,interpolate(depths,i/steps))
        for j in range(sides):
            a=TAU*j/sides
            # Low broad ridges and narrow valleys are surface modeling, not ribs.
            f=1+flute*math.cos(5*a+.4*i/steps)
            v=c+u*(w*math.cos(a)*f)+n*(d*math.sin(a)*f)
            if ridge and math.sin(a)>0:v+=n*(ridge*max(0,1-abs(math.cos(a))*2)*math.sin(math.pi*i/steps))
            if isinstance(mat,str) and mat.startswith('ivory'):
                # Longitudinal sculpted fur channels on the broad sides.
                channel=(.16*math.cos(3*math.pi*math.cos(a))+.055*math.cos(7*math.pi*math.cos(a)))
                v+=n*(d*channel*math.sin(a)**2*math.sin(math.pi*i/steps))
            vs.append(v)
    for i in range(steps):
        for j in range(sides):
            k=i*sides+j;n=i*sides+(j+1)%sides
            fs.append((k,k+sides,n+sides,n))
    fs.append(tuple(range(sides)));fs.append(tuple(steps*sides+j for j in reversed(range(sides))))
    o=mesh(name,vs,fs,mat,part)
    return o


def line(name, points, radius, mat, part, resolution=12):
    cu=bpy.data.curves.new('AST_'+name,'CURVE');cu.dimensions='3D';cu.resolution_u=resolution
    sp=cu.splines.new('BEZIER');sp.bezier_points.add(len(points)-1)
    for p,co in zip(sp.bezier_points,points):
        p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
    cu.bevel_depth=radius;cu.bevel_resolution=3;cu.resolution_u=resolution
    o=bpy.data.objects.new('AST_'+name,cu);bpy.context.collection.objects.link(o)
    active(o);bpy.ops.object.convert(target='MESH')
    return register(o,name,mat,part)


def loft(name, sections, mat, part, sides=64, n=96):
    # Sections are Y, center Z, horizontal half-width, vertical half-height.
    ss=spline(sections,n); vs=[];fs=[]
    for y,z,rx,rz in ss:
        for j in range(sides):
            a=TAU*j/sides; x=rx*math.cos(a); zz=rz*math.sin(a)
            # Dragon planes: subtly squared temples, broad lower cheek.
            if zz<0:x*=1.02
            vs.append((x,y,z+zz))
    for i in range(n):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides
            fs.append((a,a+sides,b+sides,b))
    fs.append(tuple(reversed(range(sides))));fs.append(tuple(n*sides+j for j in range(sides)))
    return mesh(name,vs,fs,mat,part)


def anatomy(detail=True):
    parts=[uv('ribcage',(0,.20,1.90),(.71,1.15,.69)),uv('rump',(0,1.0,1.91),(.70,.68,.68)),
           uv('brisket',(0,-.81,1.91),(.70,.65,.88)),uv('neck_low',(0,-.80,2.56),(.66,.65,.85)),
           uv('neck_high',(0,-.91,3.12),(.65,.55,.71))]
    for s in (-1,1):
        side='L' if s>0 else 'R'
        # Forelegs have a broad shoulder flowing into a vertical carpus.
        specs=[((s*.63,-.83,1.61),(.38,.43,.67)),((s*.66,-.94,1.02),(.29,.30,.62)),
               ((s*.66,-1.05,.46),(.30,.33,.33)),((s*.66,-1.18,.28),(.38,.35,.25)),
               ((s*.62,.96,1.59),(.43,.52,.68)),((s*.66,1.27,1.01),(.27,.32,.54)),
               ((s*.68,1.04,.59),(.27,.27,.37)),((s*.68,.88,.27),(.36,.33,.25))]
        for i,(p,r) in enumerate(specs):parts.append(uv('anatomy_'+side+str(i),p,r))
        for pair,y in [('fore',-1.39),('hind',.69)]:
            for k in range(4):
                parts.append(uv(pair+'_toe_'+side+str(k),(s*.66+(k-1.5)*.18,y,.23),(.117,.23,.19)))
    body=fuse('Sculpted_body',parts,voxel=.034 if detail else .055,subdiv=1)
    headparts=[loft('head_volume',[
        (-2.09,3.44,.10,.09),(-1.98,3.43,.31,.18),(-1.80,3.48,.50,.28),
        (-1.59,3.71,.69,.53),(-1.29,3.84,.84,.68),(-.96,3.89,.89,.77),
        (-.59,3.86,.77,.70),(-.35,3.76,.49,.49),(-.29,3.73,.08,.10)],'navy','head'),
        uv('muzzle_cheeks',(0,-1.72,3.37),(.60,.365,.180),'navy','head'),
        uv('lower_jaw',(0,-1.58,3.27),(.55,.465,.14),'navy','head')]
    head=fuse('Sculpted_head',headparts,'head',voxel=.019 if detail else .032,subdiv=1)
    tail=sweep('Sculpted_tail',[(0,1.35,2.08),(0,1.90,2.04),(0,2.24,1.66),(.06,2.56,1.17),(.12,2.97,.89),(.12,3.23,1.06)],
               [.34,.32,.245,.175,.08,.001],[.32,.31,.23,.16,.07,.001],'navy','tail',normal=(1,0,0),steps=108,sides=56,flute=.02)
    for s in (-1,1):
        side='L' if s>0 else 'R'
        for pair,y in [('fore',-1.49),('hind',.60)]:
            for k in range(4):
                x=s*.66+(k-1.5)*.18
                sweep(pair+'_gold_claw_'+side+str(k),[(x,y+.12,.27),(x,y-.01,.25),(x,y-.16,.16),(x,y-.19,.085)],
                      [.090,.112,.084,.017],[.095,.099,.071,.017],'gold_light',pair+'.'+side,normal=(1,0,0),steps=22,sides=24)
    return body,head,tail


def almond(name, center, normal, width, upper, lower, mat, part='head', bulge=.06):
    n=Vector(normal).normalized();u=Vector((n.y,-n.x,0)).normalized()
    # U always increases toward the outside of its own eye.
    if u.x*n.x<0:u=-u
    v=n.cross(u).normalized()
    if v.z<0:v=-v
    c=Vector(center);vs=[c+n*bulge];fs=[];rings=14;seg=72
    for r in range(1,rings+1):
        t=r/rings
        for j in range(seg):
            a=TAU*j/seg;xx=math.cos(a);zz=math.sin(a)
            z=(upper if zz>0 else lower)*zz*(.78+.22*abs(zz))
            vs.append(c+u*(width*xx*t)+v*(z*t+.052*xx*t)+n*(bulge*(1-t*t)))
    for j in range(seg):fs.append((0,1+j,1+(j+1)%seg))
    for r in range(rings-1):
        a=1+r*seg;b=a+seg
        for j in range(seg):fs.append((a+j,b+j,b+(j+1)%seg,a+(j+1)%seg))
    if u.cross(v).dot(n)<0:fs=[tuple(reversed(f)) for f in fs]
    o=mesh(name,vs,fs,mat,part);o['ast_eye_normal']=list(n)
    return o,u,v,n


def disk(name, c, u,v,n, rx,ry, mat, part='head', bulge=.016, rings=9,seg=80):
    c=Vector(c);vs=[c+n*bulge];fs=[]
    for k in range(1,rings+1):
        r=k/rings
        for j in range(seg):
            a=TAU*j/seg;vs.append(c+u*(rx*r*math.cos(a))+v*(ry*r*math.sin(a))+n*(bulge*(1-r*r)))
    for j in range(seg):fs.append((0,1+j,1+(j+1)%seg))
    for k in range(rings-1):
        a=1+k*seg;b=a+seg
        for j in range(seg):fs.append((a+j,b+j,b+(j+1)%seg,a+(j+1)%seg))
    if u.cross(v).dot(n)<0:fs=[tuple(reversed(f)) for f in fs]
    return mesh(name,vs,fs,mat,part)


def face():
    for s in (-1,1):
        side='L' if s>0 else 'R';c=Vector((s*.615,-1.62,3.79));n=Vector((s*.59,-.80,.055)).normalized()
        rim,u,v,n=almond('orbital_socket.'+side,c,n,.420,.218,.236,'navy',bulge=.037)
        eye_c=c+n*.010
        almond('ivory_eye.'+side,eye_c,n,.380,.182,.204,'sclera',bulge=.055)
        iris_c=eye_c+n*.041-u*.035-v*.014
        disk('iris_outer.'+side,iris_c,u,v,n,.210,.205,'iris_dark',bulge=.019)
        iris=disk('iris.'+side,iris_c+n*.001,u,v,n,.188,.188,'cyan',bulge=.019,seg=112)
        # Individual radial iris fibers, embedded between iris and pupil planes.
        for j in range(72):
            a=TAU*j/72;rr=.100+.012*math.sin(j*4.73)
            pts=[]
            for t in (0,.5,1):
                r=rr+(.181-rr)*t;pts.append(iris_c+n*(.017-.012*t)+u*(math.cos(a)*r)+v*(math.sin(a)*r))
            line('iris_fiber_'+side+str(j),pts,.0012 if j%3 else .0018,'iris_light' if j%3 else 'iris_dark','head',resolution=2)
        disk('pupil.'+side,iris_c+n*.017+v*.014,u,v,n,.075,.154,'black',bulge=.009)
        disk('eye_catchlight.'+side,iris_c+n*.028-u*.041+v*.106,u,v,n,.030,.034,'white',bulge=.003,rings=4,seg=32)
        disk('eye_pinlight.'+side,iris_c+n*.024+u*.046-v*.093,u,v,n,.011,.013,'white',bulge=.002,rings=3,seg=24)
        # Brow follows the upper eye contour, navy rather than a separate gold eyebrow.
        pts=[c-u*.433-v*.013+n*.015,c-u*.24+v*.179+n*.035,c+u*.07+v*.225+n*.038,c+u*.34+v*.195+n*.025,c+u*.45+v*.071]
        sweep('upper_brow.'+side,pts,[.01,.066,.073,.055,.001],[.01,.044,.051,.035,.001],'navy','head',normal=n,steps=40,sides=24)
        line('lower_eyelid.'+side,[c-u*.421-v*.015,c-u*.22-v*.174+n*.029,c+u*.12-v*.208+n*.027,c+u*.38-v*.088],.027,'scale_dark','head')
        lid,_,_,_=almond('closed_eyelid.'+side,c+n*.070,n,.398,.200,.222,'navy','lid.'+side,bulge=.020)
        lid['ast_lid_pivot']=list(c+n*.070)
        lid.hide_render=True;lid.hide_viewport=True
        # Short tapering cheek fins, following the shape of the muzzle.
        for j in range(3):
            sweep('cheek_scale_'+side+str(j),[(s*.60,-1.51+j*.15,3.45),(s*(.87+j*.01),-1.19+j*.18,3.53-j*.055),(s*(.98-j*.02),-.97+j*.16,3.62-j*.08)],
                  [.13,.14,.001],[.025,.046,.001],'scale_dark','head',normal=(s,0,.1),steps=28,sides=20,ridge=.014)
        # Real nostril recess and a restrained curved lip line.
        no=uv('nostril.'+side,(s*.233,-2.040,3.491),(.077,.022,.036),'black','head',seg=40,rings=20)
        no.rotation_euler.y=s*-.19
        line('nostril_rim.'+side,[(s*.15,-2.046,3.493),(s*.23,-2.05,3.524),(s*.31,-2.010,3.50)],.011,'scale_dark','head')
        line('smile.'+side,[(0,-2.05,3.31),(s*.21,-2.016,3.285),(s*.43,-1.87,3.31),(s*.54,-1.72,3.36)],.014,'black','head')
    # Low triangular nose, softened facets, and a central philtrum.
    nose=mesh('nose',[(0,-2.127,3.39),(-.20,-2.07,3.52),(.20,-2.07,3.52),(0,-2.17,3.48),(0,-2.015,3.50)],
              [(0,1,3),(0,3,2),(1,2,3),(0,4,1),(0,2,4),(1,4,2)],'navy','head')
    b=nose.modifiers.new('Soft nose edge','BEVEL');b.width=.025;b.segments=4;apply(nose,b)
    line('philtrum',[(0,-2.12,3.395),(0,-2.108,3.345),(0,-2.05,3.31)],.011,'black','head')


def horns_ears():
    for s in (-1,1):
        side='L' if s>0 else 'R'
        # Strong ribbon-like horn section with five subtle longitudinal facets.
        main=[(s*.57,-1.01,4.32),(s*.74,-.65,4.71),(s*.98,-.12,5.04),(s*1.07,.46,5.35),(s*.96,.70,5.80)]
        sweep('great_horn.'+side,main,[.23,.34,.31,.17,.0005],[.17,.23,.185,.098,.0005],
              'gold','head',normal=(s*.95,.05,.15),steps=100,sides=56,flute=.035,ridge=.012)
        inner=[(s*.35,-1.49,4.19),(s*.47,-1.17,4.56),(s*.51,-.79,4.86),(s*.43,-.58,5.27)]
        sweep('inner_horn.'+side,inner,[.14,.20,.17,.0005],[.11,.13,.10,.0005],'gold_light','head',normal=(s,0,0),steps=74,sides=40,flute=.025)
        # Forehead gold sweeps join the horn roots to the raised temple line.
        goldpath=[(s*.24,-1.70,4.11),(s*.43,-1.58,4.29),(s*.71,-1.18,4.52),(s*.92,-.65,4.56)]
        sweep('gold_temple.'+side,goldpath,[.055,.125,.17,.001],[.024,.05,.064,.001],'gold','head',normal=(s*.6,-.75,.2),steps=52,sides=32,ridge=.022)
        # Broad pointed ears with genuine volume and a recessed insert.
        ear=[(s*.71,-.59,4.03),(s*1.11,-.29,4.12),(s*1.39,.02,4.45),(s*1.47,.10,4.57)]
        sweep('ear.'+side,ear,[.20,.275,.105,.001],[.115,.145,.06,.001],'navy','head',normal=(s*.5,-.83,.2),steps=46,sides=36,ridge=.016)
        inset=[(s*.89,-.59,4.06),(s*1.13,-.362,4.16),(s*1.36,-.027,4.44)]
        sweep('ear_inner.'+side,inset,[.006,.17,.001],[.006,.018,.001],'black','head',normal=(s*.5,-.83,.2),steps=36,sides=26)
        line('ear_gold_lower.'+side,[(s*.82,-.68,3.99),(s*1.06,-.41,4.01),(s*1.27,-.19,4.18),(s*1.42,.065,4.49)],.022,'gold','head')
        # Light-catching narrow sculpted ridge on the main horn's leading side.
        line('horn_highlight_ridge.'+side,[(s*.70,-1.12,4.38),(s*.86,-.73,4.88),(s*1.04,-.20,5.22),(s*1.075,.37,5.50)],.009,'gold_light','head')
        for j in range(0):
            t=.2+j*.105;c=spline(main,100)[int(t*100)]
            # Sparse flowing fine horn scoring, never circumferential tubing.
            p=[c+Vector((s*.195,-.14,-.065)),c+Vector((s*.215,.00,.01)),c+Vector((s*.18,.13,.055))]
            line('horn_etch_'+side+str(j),p,.003,'gold_dark','head',resolution=7)
    # Layered navy spearhead scales between the two gold structures.
    for j in range(6):
        z=4.00+j*.105;y=-1.70+j*.105
        sweep('forehead_lance_'+str(j),[(0,y,z),(0,y+.09,z+.20),(0,y+.23,z+.42)],
              [.10+j*.008,.19-j*.012,.001],[.034,.08,.001], 'scale_dark' if j%2 else 'navy','head',normal=(0,-1,.3),steps=32,sides=24,ridge=.027)
    # Small split gold forehead diamond; no oversized central spike.
    for s in (-1,1):
        line('forehead_diadem_'+str(s),[(0,-1.783,4.074),(s*.11,-1.724,4.22),(s*.205,-1.678,4.26)],.031,'gold_light','head')


def continuous_eyes():
    """One continuous curved eye surface with authored vertex-colored irises."""
    prefixes=('AST_ivory_eye.','AST_iris','AST_pupil.','AST_eye_catchlight.','AST_eye_pinlight.')
    for o in list(ASSET):
        if o.name.startswith(prefixes):
            ASSET.remove(o);bpy.data.objects.remove(o,do_unlink=True)
    mat=material('Eye_living_azure','FFFFFF',0,.43)
    nodes=mat.node_tree.nodes;bsdf=nodes.get('Principled BSDF')
    bsdf.inputs['Specular IOR Level'].default_value=.035
    attr=nodes.new('ShaderNodeVertexColor');attr.layer_name='AST_eye_color'
    mat.node_tree.links.new(attr.outputs['Color'],bsdf.inputs['Base Color'])
    # glTF cannot multiply emissiveFactor by COLOR_0. A vertex-linked emission
    # would silently export as constant gray and wash out the iris and pupil.
    bsdf.inputs['Emission Strength'].default_value=0
    for s in (-1,1):
        side='L' if s>0 else 'R';c=Vector((s*.615,-1.62,3.79));n=Vector((s*.59,-.80,.055)).normalized()
        u=Vector((s*.805,.593,0)).normalized();v=Vector((0,0,1));c+=n*.014
        verts=[];faces=[];colors=[];rings=86;segments=192
        for ring in range(rings+1):
            t=max(.00001,ring/rings)
            for j in range(segments):
                a=TAU*j/segments;xx=math.cos(a);zz=math.sin(a)
                x=.380*xx*t;z=(.182 if zz>0 else .204)*zz*(.78+.22*abs(zz))*t+.052*xx*t
                verts.append(c+u*x+v*z+n*(.040*(1-t*t)))
                ix=(x+.052)/.253;iz=(z+.020)/.247;r=math.sqrt(ix*ix+iz*iz)
                pupil=((x+.056)/.078)**2+((z-.020)/.174)**2
                col=color('D8D1AF')
                if r<1:
                    angle=math.atan2(iz,ix)
                    fiber=(math.sin(angle*79+math.sin(angle*17)*.8)+math.sin(angle*137)*.35)*.035
                    bright=.75+.22*max(0,-iz)+fiber
                    if r>.89:col=color('005699')
                    else:
                        col=color('08B6F0');col=tuple(ch*bright for ch in col[:3])+(1,)
                    if iz>.24:col=tuple(ch*(1-.27*min(1,(iz-.24)/.55)) for ch in col[:3])+(1,)
                if pupil<1:col=color('010A1B')
                if col[2]>col[0]*2 and col[1]>col[0]*2:
                    col=tuple(ch*.25 for ch in col[:3])+(1,)
                colors.append(col)
        for r in range(rings):
            a=r*segments;b=a+segments
            for j in range(segments):faces.append((a+j,b+j,b+(j+1)%segments,a+(j+1)%segments))
        # The ring traversal is counterclockwise in the UV basis.
        if u.cross(v).dot(n)<0:faces=[tuple(reversed(f)) for f in faces]
        o=mesh('living_eye.'+side,verts,faces,mat,'eye.'+side)
        ca=o.data.color_attributes.new(name='AST_eye_color',type='FLOAT_COLOR',domain='POINT')
        for item,col in zip(ca.data,colors):item.color=col
        disk('eye_catchlight.'+side,c-u*.093+v*.106+n*.043,u,v,n,.032,.038,'white',bulge=.002,rings=5,seg=40)
        disk('eye_pinlight.'+side,c+u*.011-v*.111+n*.035,u,v,n,.012,.014,'white',bulge=.001,rings=3,seg=24)


def refine_face(head):
    # Physical eye sockets keep the living eye surface clear of skull geometry.
    for s in (-1,1):
        side='L' if s>0 else 'R'
        c=Vector((s*.615,-1.62,3.79));n=Vector((s*.59,-.80,.055)).normalized()
        u=Vector((s*.805,.593,0)).normalized();shift=Vector((-s*.077,-.028,0))
        new_n=Vector((s*.45,-.892,.03)).normalized();new_u=Vector((s*.893,.450,0)).normalized()
        ocular=('AST_orbital_socket.','AST_living_eye.','AST_upper_brow.','AST_lower_eyelid.','AST_closed_eyelid.','AST_eye_catchlight.','AST_eye_pinlight.')
        for o in ASSET:
            if not (o.name.startswith(ocular) and o.name.endswith('.'+side)):continue
            inv=o.matrix_world.inverted()
            for vert in o.data.vertices:
                p=o.matrix_world@vert.co;d=p-c;xx=d.dot(u)
                zz=d.z
                if zz>0:zz-=.053*max(0,1-(xx/.44)**2)*min(1,zz/.12)
                zz+=.035*xx/.44
                p=c+shift+new_u*(xx*.75)+Vector((0,0,zz))+new_n*d.dot(n)
                vert.co=inv@p
            if 'ast_lid_pivot' in o:
                pivot=c+shift+new_n*.070
                o['ast_lid_pivot']=list(pivot)
                for vert in o.data.vertices:
                    vert.co=inv@(pivot+(o.matrix_world@vert.co-pivot)*1.035+new_n*.008)
        cc=c+shift-new_n*.066
        cut=uv('socket_cutter.'+side,cc,(.296,.209,.190),'navy','head',seg=64,rings=40)
        vv=new_n.cross(new_u).normalized()
        cut.rotation_euler=Matrix((new_u,vv,new_n)).transposed().to_euler()
        mod=head.modifiers.new('Carved eye socket '+side,'BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
        apply(head,mod);ASSET.remove(cut);bpy.data.objects.remove(cut,do_unlink=True)
    for o in list(ASSET):
        if o.name.startswith(('AST_nostril','AST_philtrum','AST_smile.')):
            ASSET.remove(o);bpy.data.objects.remove(o,do_unlink=True)
        elif o.name.startswith('AST_cheek_scale_'):
            s=1 if 'L' in o.name else -1
            ctr=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
            for vert in o.data.vertices:vert.co=ctr+(vert.co-ctr)*.56+Vector((-s*.075,.0,-.04))
    bvh=BVHTree.FromPolygons([head.matrix_world@v.co for v in head.data.vertices],[list(p.vertices) for p in head.data.polygons])
    for s in (-1,1):
        side='L' if s>0 else 'R'
        # Lips and nares are embedded in the actual muzzle, not floating beads.
        pts=[]
        for x,z in [(0,3.293),(.19,3.278),(.38,3.302),(.51,3.35)]:
            hit,n,_,_=bvh.ray_cast(Vector((s*x,-3,z)),Vector((0,1,0)))
            if hit is not None:pts.append(hit+n*.006)
        if len(pts)>2:line('gentle_smile.'+side,pts,.007,'black','head')
        hit,n,_,_=bvh.ray_cast(Vector((s*.20,-3,3.49)),Vector((0,1,0)))
        if hit is not None:
            no=uv('recessed_nostril.'+side,hit+n*.002,(.039,.009,.019),'black','head',seg=32,rings=20)
            no.rotation_euler.y=s*-.22


def mane():
    for s in (-1,1):
        side='L' if s>0 else 'R'
        # Each lock has an individually authored arc; pointed tips clear the
        # next layer so the silhouette reads as fur rather than stacked rings.
        locks=[
            (.46,-.22,4.19,.78,.87,4.50,.19),
            (.52,-.20,3.91,.90,.91,4.13,.22),
            (.53,-.16,3.63,.94,.94,3.76,.23),
            (.50,-.12,3.36,.94,.90,3.36,.235),
            (.47,-.10,3.09,.84,.82,2.94,.21),
            (.43,-.07,2.87,.73,.70,2.55,.19),
            (.77,-.48,4.06,1.17,.66,4.38,.21),
            (.82,-.51,3.81,1.23,.64,4.00,.23),
            (.85,-.49,3.54,1.23,.63,3.62,.235),
            (.82,-.44,3.28,1.20,.59,3.24,.23),
            (.78,-.37,3.02,1.08,.59,2.82,.21),
            (.69,-.24,2.84,.90,.59,2.47,.175),
        ]
        for j,(x,y,z,tx,ty,tz,w) in enumerate(locks):
            p=[(s*x,y,z),(s*(x*.70+tx*.30),y*.72+ty*.28,z+.035),
               (s*(x*.20+tx*.80),y*.2+ty*.8,tz-.075),(s*tx,ty,tz)]
            if j in (6,7):
                p=[(px,py+.18,pz+.035) for px,py,pz in p]
            norm=Vector((s*.89,.40,.10)).normalized()
            sweep('mane_lock_'+side+str(j),p,[.040,w,w*.51,.0005],[.038,.115,.052,.0005],
                  'ivory' if j%3 else 'ivory_light','mane',normal=norm,steps=64,sides=36,flute=.035,ridge=.029)
            centers=spline(p,32)
            for g in (-.34,.34):
                pp=[]
                for k in range(4,29,4):
                    t=k/32;tan=(centers[k+1]-centers[k-1]).normalized();nn=(norm-tan*norm.dot(tan)).normalized();ac=tan.cross(nn).normalized()
                    depth=interpolate([.038,.115,.052,.0005],t)
                    width=interpolate([.025,w,w*.56,.0005],t)
                    pp.append(centers[k]+nn*(depth*.89)+ac*(g*width))
                line('mane_strand_'+side+str(j)+'_'+str(g),pp,.0035,'ivory_dark','mane',resolution=6)
        # Short cheek-facing fur overlaps the mantle roots and sharpens the face.
        for j in range(4):
            z=3.64-j*.215
            p=[(s*.77,-1.06+j*.075,z),(s*1.03,-.79+j*.07,z-.025),(s*1.27,-.38+j*.08,z-.055),(s*1.30,-.22+j*.08,z+.085-j*.035)]
            sweep('cheek_mane_'+side+str(j),p,[.020,.165,.086,.0005],[.012,.075,.038,.0005],
                  'ivory_light' if j%2==0 else 'ivory','mane',normal=(s*.95,-.18,.07),steps=50,sides=30,flute=.04,ridge=.018)
    # A varied central tail plume, flowing down the heavy blue tail.
    tc=spline([(0,1.35,2.08),(0,1.90,2.04),(0,2.24,1.66),(.06,2.56,1.17),(.12,2.97,.89),(.12,3.23,1.06)],100)
    for j in range(13):
        t=.03+j*.044;s=-1 if j%2 else 1;p=[]
        for k,dt in enumerate((0,.055,.13,.22)):
            ti=min(.96,t+dt);idx=int(ti*100);c=tc[idx];tan=(tc[min(100,idx+1)]-tc[max(0,idx-1)]).normalized()
            n=Vector((0,-tan.z,tan.y)).normalized();radius=interpolate([.32,.31,.23,.16,.07,.001],ti)
            height=(.015,.15,.13,.16)[k];x=s*(.08+.045*math.sin(j*1.3))*(1-dt*2)
            p.append(c+n*(radius+height)+Vector((x,0,0)))
        sweep('tail_plume_'+str(j),p,[.028,.17-.04*t,.085-.025*t,.0005],[.022,.075,.037,.0005],
              'ivory' if j%3 else 'ivory_light','tail',normal=(s*.45,.3,.80),steps=54,sides=32,flute=.045,ridge=.021)
    for s in (-1,1):
        # Follow the same swept tail section, including its taper. The old
        # hand-placed polyline left two detached gold rods near the tip.
        inset=[]
        for index in range(8,88,4):
            t=index/100;c=tc[index]
            tangent=(tc[index+1]-tc[index-1]).normalized()
            lateral=Vector((1,0,0));up=lateral.cross(tangent).normalized()
            width=interpolate([.34,.32,.245,.175,.08,.001],t)
            depth=interpolate([.32,.31,.23,.16,.07,.001],t)
            inset.append(c+lateral*(s*(depth+.023)*.85)+up*((width+.023)*.5268))
        line('tail_gold_inlay_'+str(s),inset,.013,'gold','tail',resolution=4)


def scales(obj, name, spacing, part, skip=None, limit=6000):
    """Lay small smooth overlapping shields on real sculpt surface samples."""
    mw=obj.matrix_world
    candidates=[]
    for v in obj.data.vertices:
        p=mw@v.co;n=(mw.to_3x3()@v.normal).normalized()
        if skip and skip(p,n):continue
        if n.z<-.73:continue
        candidates.append((p,n))
    # Deterministic stable staggered surface sampling, one scale per local cell.
    RNG.shuffle(candidates);grid={};chosen=[]
    for p,n in candidates:
        k=tuple(math.floor(float(x)/spacing) for x in p)
        if k in grid:continue
        ok=True
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                for dz in (-1,0,1):
                    q=grid.get((k[0]+dx,k[1]+dy,k[2]+dz))
                    if q is not None and (p-q).length<spacing*.83:ok=False;break
                if not ok:break
            if not ok:break
        if not ok:continue
        grid[k]=p;chosen.append((p,n))
        if len(chosen)>=limit:break
    vs=[];fs=[];mats=[];outline=[(0,.58),(.39,.37),(.53,.02),(.39,-.35),(0,-.69),(-.39,-.35),(-.53,.02),(-.39,.37)]
    for idx,(p,n) in enumerate(chosen):
        up=Vector((0,0,1));v=up-n*up.dot(n)
        if v.length<.2:v=Vector((0,1,0))-n*n.y
        v.normalize();u=v.cross(n).normalized();size=spacing*(1.22+RNG.random()*.16)
        base=len(vs);center=p+n*.020
        vs.append(center)
        rings=4
        for r in range(1,rings+1):
            t=r/rings
            for x,y in outline:
                offset=(u*x+v*y)*size*t
                # Curvature keeps edges sunk into the skin and flattens scale tips.
                height=.026*(1-t*t)-.014*t*t
                vs.append(p+offset+n*height)
        for j in range(8):fs.append((base,base+1+j,base+1+(j+1)%8));mats.append(idx%7)
        for r in range(rings-1):
            a=base+1+r*8;b=a+8
            for j in range(8):fs.append((a+j,b+j,b+(j+1)%8,a+(j+1)%8));mats.append(idx%7)
    o=mesh(name,vs,[tuple(reversed(f)) for f in fs],None,part)
    for k in ('navy','scale_dark','scale','scale_dark','navy','scale_light','scale_dark'):o.data.materials.append(M[k])
    for face,mi in zip(o.data.polygons,mats):face.material_index=mi
    # One subdivision adds curved scale rims and many actual surface samples.
    mod=o.modifiers.new('Scale sculpt smoothing','SUBSURF');mod.levels=1;apply(o,mod)
    print(name,'scales',len(chosen),flush=True)
    return o


def ordered_scales(obj, name, part):
    """Thin overlapping lamellae in anatomical rows, conformed to the skin."""
    mw=obj.matrix_world
    bvh=BVHTree.FromPolygons([mw@v.co for v in obj.data.vertices],[list(p.vertices) for p in obj.data.polygons])
    samples=[]
    def shoot(c,d,size,filter_fn=None):
        hit,n,_,_=bvh.ray_cast(Vector(c),Vector(d).normalized(),4)
        if hit is not None and (filter_fn is None or filter_fn(hit,n)):
            samples.append((hit,n.normalized(),size))
    if part=='body':
        for row in range(30):
            y=-1.1+row*.093
            for k in range(40):
                a=TAU*(k+.5*(row%2))/40
                shoot((0,y,1.90),(math.cos(a),0,math.sin(a)),.145,lambda p,n:1.10<p.z<2.48)
        for side in (-1,1):
            for limb in ('fore','hind'):
                for row in range(17):
                    z=.44+row*.078
                    y=-1.16+.18*(z/1.8) if limb=='fore' else 1.02+.16*math.sin((z-.44)/1.30*math.pi)
                    for k in range(23):
                        a=TAU*(k+.5*(row%2))/23
                        shoot((side*.65,y,z),(math.cos(a),math.sin(a),0),.116,
                              lambda p,n:abs(p.x)>.30 and abs(p.y-y)<.6 and (p.z<1.56 or abs(p.x)>.80))
        for row in range(13):
            z=2.45+row*.085;y=-.82-(z-2.45)*.11
            for k in range(39):
                a=TAU*(k+.5*(row%2))/39
                shoot((0,y,z),(math.cos(a),math.sin(a),0),.15,
                      lambda p,n:not(p.y<-1.25 and abs(p.x)<.42))
    elif part=='head':
        for row in range(12):
            y=-1.42+row*.094
            for k in range(43):
                a=TAU*(k+.5*(row%2))/43
                shoot((0,y,3.78),(math.cos(a),0,math.sin(a)),.123,
                      lambda p,n:(p.y>-.86 or p.z>4.16 or p.z<3.42) and p.z>3.26)
        for row in range(9):
            z=3.68+row*.074
            for k in range(9):
                x=-.41+(k+.5*(row%2))*.097
                if z<4.05 and abs(x)>.21:continue
                hit,nn,_,_=bvh.ray_cast(Vector((x,-3,z)),Vector((0,1,0)))
                if hit is not None:samples.append((hit,nn,.106))
    elif part=='tail':
        centers=spline([(0,1.35,2.08),(0,1.90,2.04),(0,2.24,1.66),(.06,2.56,1.17),(.12,2.97,.89),(.12,3.23,1.06)],36)
        for row,c in enumerate(centers[1:-2],1):
            t=row/36;tan=(centers[row+1]-centers[row-1]).normalized();u=Vector((1,0,0));v=tan.cross(u).normalized()
            count=max(7,int(23*(1-t)))
            for k in range(count):
                a=TAU*(k+.5*(row%2))/count;d=u*math.cos(a)+v*math.sin(a)
                shoot(c,d,.112*(1-.45*t),lambda p,n:n.z<.45)
    vs=[];fs=[];indices=[]
    outline=[(0,.62),(.35,.44),(.50,.12),(.43,-.22),(.21,-.47),(0,-.65),(-.21,-.47),(-.43,-.22),(-.50,.12),(-.35,.44)]
    # Nearby surface points never create duplicated stacks at region borders.
    seen=set();accepted=0
    for p,n,size in samples:
        key=tuple(round(float(x)/.055) for x in p)
        if key in seen:continue
        seen.add(key);up=Vector((0,0,1));v=up-n*up.dot(n)
        if v.length<.15:v=Vector((0,1,0))-n*n.y
        v.normalize();u=v.cross(n).normalized();base=len(vs);rings=6
        vs.append(p+n*.010)
        for ring in range(1,rings+1):
            t=ring/rings
            for x,y in outline:
                q=p+(u*x+v*y)*size*t
                nearest,nn,_,_=bvh.find_nearest(q)
                if nearest is None:nearest=q;nn=n
                vs.append(nearest+nn*(.009*(1-t*t)+.0025))
        mi=0 if accepted%11<5 else (1 if accepted%11<9 else 2)
        for j in range(10):fs.append((base,base+1+(j+1)%10,base+1+j));indices.append(mi)
        for ring in range(rings-1):
            a=base+1+ring*10;b=a+10
            for j in range(10):fs.append((a+j,a+(j+1)%10,b+(j+1)%10,b+j));indices.append(mi)
        accepted+=1
    o=mesh(name,vs,fs,None,part)
    for mat in ('scale_dark','navy','scale'):o.data.materials.append(M[mat])
    for p,idx in zip(o.data.polygons,indices):p.material_index=idx
    print(name,'conformed scale count',accepted,flush=True)
    return o


def large_plates():
    # V-shaped throat plates remain blue and follow the rounded neck.
    for j in range(7):
        z=3.22-j*.17;y=-1.465-(.045*math.sin(j*.45))
        outline=[(-.42,.09),(-.29,.19),(0,.12),(.29,.19),(.42,.09),(.30,-.035),(0,-.17),(-.30,-.035)]
        vs=[(0,y-.035,z)];fs=[]
        for r in range(1,7):
            t=r/6
            for x,zz in outline:vs.append((x*t,y+.58*(x*t)**2-.022*(1-t*t),z+zz*t))
        for k in range(8):fs.append((0,1+k,1+(k+1)%8))
        for r in range(5):
            a=1+r*8;b=a+8
            for k in range(8):fs.append((a+k,b+k,b+(k+1)%8,a+(k+1)%8))
        mesh('throat_plate_'+str(j),vs,[tuple(reversed(f)) for f in fs],'belly','neck')
    for j in range(14):
        z=4.35-j*.148;y=-.26+.042*j
        if j>9:y+=.07*(j-9)
        sweep('dorsal_neck_plate_'+str(j),[(0,y,z-.08),(0,y+.06,z+.04),(0,y+.10,z+.20)],
              [.10,.165,.001],[.026,.065,.001],'navy' if j%2 else 'scale_dark','neck' if j>6 else 'head',normal=(0,1,0),steps=24,sides=24,ridge=.025)
    for j in range(9):
        y=-.0+j*.16;z=2.54+.035*math.sin(j*.6)
        sweep('spine_scale_'+str(j),[(0,y-.12,z-.015),(0,y,z+.075),(0,y+.20,z+.035)],
              [.105,.14,.001],[.03,.07,.001],'navy','body',normal=(0,0,1),steps=24,sides=24,ridge=.018)


def point_at(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()


def stage(res=1000,samples=48):
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=samples;sc.cycles.use_denoising=True
    prefs=bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type='OPTIX';prefs.get_devices()
        for d in prefs.devices:d.use=d.type=='OPTIX'
        sc.cycles.device='GPU'
    except Exception:pass
    sc.render.resolution_x=res;sc.render.resolution_y=res;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA'
    sc.world.use_nodes=True;sc.world.node_tree.nodes.get('Background').inputs[0].default_value=(.60,.57,.51,1)
    sc.world.node_tree.nodes.get('Background').inputs[1].default_value=.40
    sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast'
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,.035));g=bpy.context.object;g.name='STUDIO_ground'
    gm=material('studio','DEDCD5',0,.80);g.data.materials.append(gm)
    gp=gm.node_tree.nodes.get('Principled BSDF');gp.inputs['Emission Color'].default_value=color('DEDCD5');gp.inputs['Emission Strength'].default_value=.7
    for name,p,energy,size,col in [
        ('key',(-4,-6,9),1150,5.0,(1,.90,.76)),('fill',(5,-4,5),850,5,(.78,.87,1)),
        ('rim',(2,5,7),1400,4,(1,.88,.66)),('top',(-1,1,10),700,3,(1,.96,.88))]:
        bpy.ops.object.light_add(type='AREA',location=p);o=bpy.context.object;o.name='STUDIO_'+name
        o.data.energy=energy;o.data.shape='DISK';o.data.size=size;o.data.color=col;point_at(o,(0,0,2.5))
    bpy.ops.object.camera_add(location=(8,-12,6.1));cam=bpy.context.object;cam.name='STUDIO_camera';cam.data.type='ORTHO';cam.data.ortho_scale=6.9
    point_at(cam,(0,.25,2.9));sc.camera=cam
    return cam


def render(cam,out,views):
    sc=bpy.context.scene;paths={}
    table={'hero':((8,-12,5.8),(0,.25,2.88),6.8), 'front':((0,-14,4.3),(0,-.15,2.88),6.6),
           'side':((14,0,4.0),(0,.43,2.86),6.8),'rear':((0,14,4.5),(0,.3,2.88),6.65),
           'face':((7,-12,5.6),(0,-.85,3.89),3.30)}
    for name in views:
        p,t,s=table[name];cam.location=p;cam.data.ortho_scale=s;point_at(cam,t)
        path=out/('asterion-sculpt-'+name+'.png');sc.render.filepath=str(path);bpy.ops.render.render(write_still=True);paths[name]=str(path)
    return paths


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default=str(ROOT/'draft01'));p.add_argument('--quick',action='store_true');p.add_argument('--no-scales',action='store_true');p.add_argument('--rig',action='store_true');p.add_argument('--views',default='hero,front,side,rear,face');p.add_argument('--resolution',type=int,default=1000)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    materials();print('BUILD anatomy',flush=True);body,head,tail=anatomy(not args.quick)
    print('BUILD face',flush=True);face();continuous_eyes();refine_face(head);horns_ears();print('BUILD mane',flush=True);mane();large_plates()
    try:
        import armor
        ASSET.extend(armor.build_armor(M))
    except ImportError:print('ARMOR MODULE PENDING',flush=True)
    try:
        import ears
        for o in list(ASSET):
            if o.name.startswith(('AST_ear.','AST_ear_inner.','AST_ear_gold_lower.')):
                ASSET.remove(o);bpy.data.objects.remove(o,do_unlink=True)
        ASSET.extend(ears.build_ears(M))
    except ImportError:print('EAR MODULE PENDING',flush=True)
    if not args.no_scales:
        ordered_scales(body,'body_scale_sculpt','body')
        ordered_scales(head,'head_scale_sculpt','head')
        ordered_scales(tail,'tail_scale_sculpt','tail')
    rig=None
    if args.rig:
        import rig_delivery
        for o in ASSET:
            if o.get('ast_part','').startswith('lid.'):
                o.hide_render=False;o.hide_viewport=False
        rig=rig_delivery.build_rig(ASSET)
    sc=bpy.context.scene;sc['asset']='asterion-sculpt-v001';sc['reference_authority']='user approved four-view turnaround 2026-09-05'
    ref=ROOT/'reference'/'asterion-approved-turnaround.png'
    sc['reference_sha256']=hashlib.sha256(ref.read_bytes()).hexdigest()
    sc['geometry_method']='Fully volumetric sculpted anatomy with modeled horns, mane, scales, armor and eyes; no projected reference image.'
    cam=stage(args.resolution,32 if args.quick else 64)
    sc.frame_set(1);bpy.context.view_layer.update()
    stats={'objects':len(ASSET),'vertices':sum(len(o.data.vertices) for o in ASSET if o.type=='MESH'),'triangles':0}
    for o in ASSET:
        if o.type=='MESH':o.data.calc_loop_triangles();stats['triangles']+=len(o.data.loop_triangles)
    print('STATISTICS',stats,flush=True)
    if rig:
        glb=out/'asterion-sculpt-v001.glb';report=rig_delivery.export_glb(glb,ASSET,rig)
        (out/'export-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    blend=out/'asterion-sculpt-v001.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    paths=render(cam,out,args.views.split(','))
    hero=((8,-12,5.8),(0,.25,2.88),6.8);cam.location=hero[0];point_at(cam,hero[1]);cam.data.ortho_scale=hero[2]
    active(body);bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    (out/'build-report.json').write_text(json.dumps({'reference_sha256':sc['reference_sha256'],'geometry_method':sc['geometry_method'],'stats':stats,'renders':paths,'blend':str(blend)},indent=2),encoding='utf-8')
    print('COMPLETE',blend,flush=True)


if __name__=='__main__':main()

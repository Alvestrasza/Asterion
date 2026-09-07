"""Liora's reference-led rabbit anatomy, cupped ears and expressive face.

World coordinates: X lateral, negative Y forward, Z up. No portrait projection.
"""
from __future__ import annotations
import math
import bpy
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree


def palette(g):
    for key,tint,metal,rough in (
        ('lv_fur','DFCAA7',0,.63),('lv_light','F0DCB8',0,.60),
        ('lv_shade','B79A79',0,.67),('lv_inner','9E7EB1',0,.64),
        ('lv_rose','AE755C',.55,.43),('lv_rose_light','D49C7C',.55,.41),
        ('lv_rose_dark','704537',.52,.45),('lv_nose','B87C78',0,.49),
        ('lv_mouth','79604C',0,.62),('lv_lash','3B2A23',0,.58),
        ('lv_white','FFFFFF',0,.25)):
        g.M[key]=g.material(key,tint,metal,rough)


def tree(obj):
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                               [list(p.vertices) for p in obj.data.polygons])


def find(g,name):
    return next(o for o in g.ASSET if o.name=='AST_liora_v2_'+name)


def authored_colors(g,obj,values):
    attr=obj.data.color_attributes.new(name='AST_eye_color',type='FLOAT_COLOR',domain='POINT')
    for item,value in zip(attr.data,values):item.color=value
    mat=obj.data.materials[0];nodes=mat.node_tree.nodes
    node=nodes.get('Liora authored colors') or nodes.new('ShaderNodeVertexColor')
    node.name='Liora authored colors';node.layer_name='AST_eye_color'
    mat.node_tree.links.new(node.outputs['Color'],nodes.get('Principled BSDF').inputs['Base Color'])


def ear(g,sign):
    """A thick closed ear, recessed violet bowl and genuinely broad metal rim."""
    side='L' if sign>0 else 'R';part='ear.'+side
    steps=96;across=40
    def pos(t,q,back=False):
        width=(.390 if sign>0 else .345)*math.sin(math.pi*t)**.72+.00025
        length=1.87 if sign>0 else 1.95
        x=sign*(.385+.37*t+.045*math.sin(math.pi*t))
        y=-.695+.105*t+.08*t*t
        z=2.88+length*t
        fade=math.sin(math.pi*t)**.65
        # Rim is forward of the hollow. Back wall remains visibly substantial.
        depth=(.094-.198*q*q)*fade
        if back:depth=.13*math.sqrt(max(0,1-q*q))*fade+.03*fade
        return Vector((x+q*width,y+depth,z-sign*q*.08*math.sin(math.pi*t)))
    verts=[];faces=[]
    for back in (False,True):
        for row in range(steps+1):
            for col in range(across+1):verts.append(pos(row/steps,col/across*2-1,back))
    size=(steps+1)*(across+1)
    for row in range(steps):
        for col in range(across):
            a=row*(across+1)+col;b=a+across+1
            faces.extend([(a,a+1,b+1,b),(a+size,b+size,b+size+1,a+size+1)])
    boundary=list(range(across+1))+[r*(across+1)+across for r in range(1,steps+1)]+[steps*(across+1)+c for c in range(across-1,-1,-1)]+[r*(across+1) for r in range(steps-1,0,-1)]
    faces.extend((a,b,b+size,a+size) for a,b in zip(boundary,boundary[1:]+boundary[:1]))
    g.mesh('liora_v2_cupped_ear_'+side,verts,faces,'lv_fur',part)
    # Recessed velvet-like inner surface, safely separated from outer shell.
    verts=[];faces=[];colors=[];base=g.color('7B5C94');light=g.color('BD9DCB');dark=g.color('493350')
    rows=96;cols=36
    for row in range(rows+1):
        t=.075+.875*row/rows
        for col in range(cols+1):
            q=(col/cols*2-1)*.865*math.sin(math.pi*row/rows)**.23
            p=pos(t,q);p.y-=.022
            # Fine tapered longitudinal fibers create geometry and color relief.
            fibers=math.sin(q*96+8*t+2*math.sin(t*13))*.003
            p.y+=fibers*math.sin(math.pi*t)*max(0,1-abs(q))
            verts.append(p)
            mix=max(0,min(1,.75*(1-abs(q))*(1-t)+.12))
            edge=max(0,min(1,(abs(q)-.61)/.27))
            grain=.95+.05*math.sin(q*57+math.sin(t*12)*2)*math.sin(t*83+q*11)
            colr=tuple(((base[k]*(1-mix)+light[k]*mix)*(1-edge*.39)+dark[k]*edge*.21)*grain for k in range(3))+(1,)
            colors.append(colr)
    for row in range(rows):
        for col in range(cols):
            a=row*(cols+1)+col;faces.append((a,a+1,a+cols+2,a+cols+1))
    inside=g.mesh('liora_v2_lavender_ear_bowl_'+side,verts,faces,'lv_inner',part)
    authored_colors(g,inside,colors)
    mod=inside.modifiers.new('Velvet bowl backing','SOLIDIFY');mod.thickness=.005;g.apply(inside,mod)
    for edge in (-1,1):
        verts=[];faces=[]
        for row in range(97):
            t=.018+.966*row/96
            for k in range(5):
                q=edge*(.83+.164*k/4)
                p=pos(t,q);p.y-=.022+.011*math.sin(math.pi*k/4)
                verts.append(p)
        for row in range(96):
            for k in range(4):
                a=row*5+k;faces.append((a,a+1,a+6,a+5))
        ribbon=g.mesh('liora_v2_rose_ear_guard_'+side+str(edge),verts,faces,'lv_rose_light',part)
        mod=ribbon.modifiers.new('Forged rim depth','SOLIDIFY');mod.thickness=.014;g.apply(ribbon,mod)
        # Three tapered blade accents echo the illustrated layered ear guards.
        if edge==sign:
            for j in range(3):
                t=.09+j*.095
                points=[pos(t,edge*.83),pos(t+.08,edge*.88),pos(t+.21,edge*1.08)]
                points=[p+Vector((0,-.025,0)) for p in points]
                g.sweep('liora_v2_ear_guard_blade_'+side+str(j),points,
                    [.031,.064,.0005],[.018,.022,.0004],'lv_rose',part,
                    normal=(0,-1,0),steps=36,sides=20,ridge=.009)


def face_eye(g,head,sign,color_source=None):
    side='L' if sign>0 else 'R';name='liora_v2_eye_'+side
    width=.48;height=.55
    c=Vector((sign*.425,-1.40,2.49));n=Vector((sign*.55,-.835,.03)).normalized()
    u=Vector((0,0,1)).cross(n).normalized();v=n.cross(u).normalized();bvh=tree(head)
    hit,_,_,_=bvh.ray_cast(c+n*2,-n)
    if hit is None:raise ValueError('Missing rabbit eye landmark')
    c=hit+n*.007
    def coord(a,t=1):
        x=width*.5*math.cos(a)*t
        z=height*.5*math.sin(a)*(.83+.17*abs(math.sin(a)))*t+sign*x*.13
        return x,z
    def surface(x,z,offset=0):
        p=c+u*x+v*z
        r=math.sqrt((x/(width*.5))**2+(z/(height*.5))**2)
        return p+n*(.010+offset+.007*(1-min(1,r)**2))
    # Remove the complete projected almond footprint. An ellipsoid socket can
    # leave a crescent of cheek protruding over the lower iris after remeshing.
    outline=[c+u*x+v*z for x,z in (coord(math.tau*j/160,1.16) for j in range(160))]
    cutverts=[p+n*.50 for p in outline]+[p-n*.45 for p in outline]
    cutfaces=[tuple(range(160)),tuple(reversed(range(160,320)))]
    cutfaces.extend((j,j+160,(j+1)%160+160,(j+1)%160) for j in range(160))
    cutter=g.mesh(name+'_socket',cutverts,cutfaces,'lv_fur','head')
    mod=head.modifiers.new('Sculpted almond socket','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    g.apply(head,mod);g.ASSET.remove(cutter);bpy.data.objects.remove(cutter,do_unlink=True)
    # A continuous skin annulus joins a true ocular surface to the skull. The
    # iris itself must never be stretched over the projecting muzzle/cheek.
    rimverts=[];rimfaces=[]
    for row in range(13):
        t=row/12;s=.99+.19*t
        for j in range(160):
            x,z=coord(math.tau*j/160,s);p=c+u*x+v*z
            hit,_,_,_=bvh.ray_cast(p+n*2,-n)
            if hit is None:raise ValueError('Missing orbital skin support')
            blend=t*t*(3-2*t)
            rimverts.append((p+n*.015).lerp(hit+n*.006,blend))
    for row in range(12):
        for j in range(160):
            a=row*160+j;b=row*160+(j+1)%160;rimfaces.append((a,a+160,b+160,b))
    def skin_mesh(suffix,vertices,polygons,part):
        mat='lvf_painted_coat' if color_source else 'lv_fur'
        obj=g.mesh(name+suffix,vertices,polygons,mat,part)
        if color_source:
            kd,source_colors=color_source;values=[]
            for vertex in obj.data.vertices:
                _,index,_=kd.find(obj.matrix_world@vertex.co);values.append(source_colors[index])
            authored_colors(g,obj,values)
        return obj
    skin_mesh('_sculpted_orbital_skin',rimverts,rimfaces,'head')
    verts=[];faces=[];colors=[];seg=160;rings=64
    ivory=g.color('FFF0D7');dark=g.color('1C1F35');upper=g.color('555283');lower=g.color('99DBED')
    for row in range(rings+1):
        t=max(.00001,row/rings)
        for j in range(seg):
            a=math.tau*j/seg;x,z=coord(a,t);verts.append(surface(x,z,.038*(1-t*t)))
            ir=math.sqrt((x/(width*.397))**2+((z+height*.010)/(height*.423))**2)
            pr=math.sqrt((x/(width*.227))**2+((z-height*.069)/(height*.272))**2)
            col=ivory
            if ir<1:
                f=max(0,min(1,.46-z/(height*.83)))
                stripe=.025*math.sin(a*67+ir*12)+.018*math.sin(a*107-ir*17)
                shade=.95+stripe
                if ir>.92:shade*=.40+.60*(1-ir)/.08
                col=tuple((upper[k]*(1-f)+lower[k]*f)*shade for k in range(3))+(1,)
            if pr<1:
                f=max(0,min(1,(pr-.95)/.05));col=tuple(dark[k]*(1-f)+col[k]*f for k in range(3))+(1,)
            colors.append(col)
    for row in range(rings):
        for j in range(seg):
            a=row*seg+j;b=row*seg+(j+1)%seg;faces.append((a,a+seg,b+seg,b))
    mat=g.material(name+'_living_iris','FFFFFF',0,.25)
    mat.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.20
    obj=g.mesh(name,verts,faces,mat,'head');obj['eye_side']=side;authored_colors(g,obj,colors)
    for upper_lid in (True,False):
        start,end=(0,math.pi) if upper_lid else (math.pi,math.tau)
        points=[surface(*coord(start+(end-start)*i/32),.009) for i in range(33)]
        widths=[(.003+.028*math.sin(math.pi*i/32)**.65) if upper_lid else .009 for i in range(33)]
        g.sweep(name+('_tapered_upper_lid' if upper_lid else '_lower_lid'),points,widths,
            [r*.58 for r in widths],'lv_lash' if upper_lid else 'lv_fur','head',normal=n,steps=88,sides=20)
    # Broad wing grows from the outer upper eyelid, not a separate black ring.
    x=sign*width*.475
    g.sweep(name+'_lash_wing',[surface(x,.034,.011),surface(x+sign*.046,.065,.010),surface(x+sign*.100,.122,.003)],
        [.022,.029,.0005],[.013,.013,.0005],'lv_lash','head',normal=n,steps=32,sides=20)
    for suffix,x,z,rx,rz in [('catchlight',-.070,.125,.044,.048),('pinlight',.077,-.153,.013,.019)]:
        t2=(x/(width*.5))**2+(z/(height*.5))**2
        g.disk(name+'_'+suffix,surface(x,z,.038*(1-t2)+.007),u,v,n,rx,rz,'lv_white','head',bulge=.001,rings=8,seg=48)
    lidverts=[]
    for p in verts:
        d=p-c;lidverts.append(c+u*d.dot(u)*1.075+v*d.dot(v)*1.055+n*(d.dot(n)+.031))
    lid=skin_mesh('_closed_lid',lidverts,faces,'lid.'+side);lid['ast_lid_pivot']=list(c+n*.031)
    points=[surface(width*.46*q,-height*.10*(1-q*q),.038*(1-q*q)+.037) for q in (-1,-.75,-.5,-.25,0,.25,.5,.75,1)]
    lash=g.sweep(name+'_closed_lash',points,[.002,.011,.012,.010,.002],[.001,.005,.006,.005,.001],
        'lv_lash','lid.'+side,normal=n,steps=64,sides=16);lash['ast_lid_pivot']=list(c+n*.031)


def finish_face(g):
    head=find(g,'head')
    # Boolean edge intersections do not inherit every POINT color correctly.
    # Keep the original painted field before carving, then initialize only the
    # new zero-valued socket samples from their nearest authored fur surface.
    original=head.data.color_attributes.get('AST_eye_color')
    color_tree=None;original_colors=[]
    if original is not None:
        color_tree=KDTree(len(head.data.vertices))
        for vert,item in zip(head.data.vertices,original.data):
            color_tree.insert(head.matrix_world@vert.co,vert.index);original_colors.append(tuple(item.color))
        color_tree.balance()
    for sign in (-1,1):face_eye(g,head,sign,(color_tree,original_colors) if color_tree else None)
    repaired=0
    if color_tree is not None:
        attr=head.data.color_attributes['AST_eye_color']
        for vert,item in zip(head.data.vertices,attr.data):
            if max(item.color[:3])<.02 or item.color[3]<.5:
                _,index,_=color_tree.find(head.matrix_world@vert.co)
                item.color=original_colors[index];repaired+=1
        if any(max(item.color[:3])<.02 or item.color[3]<.5 for item in attr.data):
            raise ValueError('Uninitialized fur colors after eye socket carving')
    head['initialized_socket_color_samples']=repaired
    bvh=tree(head)
    def front(x,z,off=.007):
        p,_,_,_=bvh.ray_cast(Vector((x,-4,z)),Vector((0,1,0)))
        if p is None:raise ValueError('Missing rabbit muzzle landmark')
        return p+Vector((0,-off,0))
    # A rounded heart-shaped nose on the short paired rabbit muzzle.
    outline=[(-.088,2.168),(-.057,2.194),(0,2.174),(.057,2.194),(.088,2.168),(.046,2.129),(0,2.114),(-.046,2.129)]
    center=front(0,2.156,.032);verts=[center]+[front(x,z,.013) for x,z in outline]
    faces=[(0,j+1,(j+1)%len(outline)+1) for j in range(len(outline))]
    nose=g.mesh('liora_v2_soft_rose_nose',verts,faces,'lv_nose','head')
    mod=nose.modifiers.new('Soft nose volume','SOLIDIFY');mod.thickness=.014;g.apply(nose,mod)
    mod=nose.modifiers.new('Rounded nose edge','BEVEL');mod.width=.006;mod.segments=3;g.apply(nose,mod)
    g.sweep('liora_v2_philtrum',[front(0,2.119),front(0,2.083),front(0,2.061)],
        [.004,.006,.004],[.003,.004,.003],'lv_mouth','head',normal=(0,-1,0),steps=24,sides=16)
    for sign in (-1,1):
        pts=[front(sign*x,z,.007) for x,z in [(0,2.062),(.048,2.039),(.119,2.038),(.198,2.063),(.228,2.093)]]
        g.sweep('liora_v2_gentle_smile_'+str(sign),pts,[.004,.006,.006,.005,.0007],
            [.003,.004,.004,.003,.0005],'lv_mouth','head',normal=(0,-1,0),steps=56,sides=16)
        for j in range(3):
            x=sign*(.084+.037*j);z=2.140+.016*(j%2)
            g.uv('liora_v2_whisker_pore_'+str(sign)+'_'+str(j),front(x,z,.004),(.0035,.002,.0035),'lv_shade','head',seg=16,rings=10)
    body=find(g,'body');bvh=tree(body)
    # Shallow toe separations are seated on the fused paws, never black wires.
    for sign in (-1,1):
        for end,x,y in [('F',sign*.405,-.83),('H',sign*.54,.43)]:
            for offset in (-.075,.075):
                points=[]
                for yy in (y-.265,y-.22,y-.14):
                    p,_,_,_=bvh.ray_cast(Vector((x+offset,yy,1)),Vector((0,0,-1)))
                    if p is not None:points.append(p+Vector((0,0,.003)))
                if len(points)>1:g.sweep('liora_v2_toe_crease_'+end+str(sign)+str(offset),points,
                    [.001,.004,.0005],[.001,.003,.0005],'lv_shade','leg.'+end+('L' if sign>0 else 'R'),normal=(0,0,1),steps=24,sides=12)


def build(g):
    palette(g)
    parts=[g.uv('rib',(0,.13,1.10),(.61,.85,.61),'lv_fur'),
        g.uv('rump',(0,.63,1.09),(.62,.61,.65),'lv_fur'),
        g.uv('chest',(0,-.50,1.31),(.53,.49,.65),'lv_fur'),
        g.uv('neck',(0,-.63,1.75),(.43,.42,.47),'lv_fur')]
    for sign in (-1,1):
        x=sign*.405
        parts.append(g.sweep('foreleg',[(x,-.52,1.45),(x,-.58,1.14),(x,-.65,.77),(x,-.72,.39),(x,-.78,.22)],
            [.20,.233,.194,.18,.19],[.22,.24,.21,.19,.22],'lv_fur','body',normal=(1,0,0),steps=70,sides=48))
        parts.extend([g.uv('forepaw',(x,-.83,.18),(.244,.335,.19),'lv_fur'),
            g.uv('haunch',(sign*.48,.61,1.06),(.45,.49,.61),'lv_fur'),
            g.uv('hock',(sign*.56,.75,.59),(.25,.30,.40),'lv_fur'),
            g.uv('hindpaw',(sign*.54,.43,.185),(.26,.38,.20),'lv_fur')])
        for end,xx,y in [('F',x,-1.034),('H',sign*.54,.191)]:
            for offset in (-.135,0,.135):parts.append(g.uv('soft_toe',(xx+offset,y,.17),(.092,.15,.14),'lv_fur',seg=32,rings=24))
    body=g.fuse('liora_v2_body',parts,'body',voxel=.023,subdiv=1)
    body.vertex_groups.clear()
    groups={key:body.vertex_groups.new(name=key) for key in ('body','neck','leg.FL','leg.FR','leg.HL','leg.HR')}
    for vert in body.data.vertices:
        p=body.matrix_world@vert.co
        neck=max(0,min(1,(p.z-1.62)/.48));neck=neck*neck*(3-2*neck)
        lower=max(0,min(1,(1.32-p.z)/.47));lower=lower*lower*(3-2*lower)
        lateral=max(0,min(1,(abs(p.x)-.18)/.14));limb=lower*lateral
        key='leg.'+('F' if p.y<-.03 else 'H')+('L' if p.x>0 else 'R')
        for name,weight in [('neck',neck),('body',(1-neck)*(1-limb)),(key,(1-neck)*limb)]:
            if weight>0:groups[name].add([vert.index],weight,'REPLACE')
    g.fuse('liora_v2_head',[
        g.uv('skull',(0,-.85,2.43),(.755,.65,.68),'lv_fur','head',seg=72,rings=48),
        g.uv('cheek_L',(.257,-1.323,2.191),(.34,.315,.255),'lv_fur','head'),
        g.uv('cheek_R',(-.257,-1.323,2.191),(.34,.315,.255),'lv_fur','head'),
        g.uv('chin',(0,-1.265,2.043),(.36,.285,.165),'lv_fur','head'),
        g.uv('nosebridge',(0,-1.482,2.216),(.165,.18,.151),'lv_fur','head')],
        'head',voxel=.016,subdiv=1)
    for sign in (-1,1):ear(g,sign)
    return {'name':'Liora','kind':'rabbit','family':'quadruped','bones':[
        ('body',(0,.1,1.1),(0,.1,1.60),None),('neck',(0,-.56,1.62),(0,-.64,2.08),'body'),
        ('head',(0,-.66,2.02),(0,-.82,2.91),'neck'),
        ('ear.L',(.39,-.69,2.89),(.78,-.51,4.72),'head'),('ear.R',(-.39,-.69,2.89),(-.78,-.51,4.80),'head'),
        ('leg.FL',(.405,-.56,1.26),(.405,-.78,.19),'body'),('leg.FR',(-.405,-.56,1.26),(-.405,-.78,.19),'body'),
        ('leg.HL',(.54,.63,1.2),(.54,.43,.19),'body'),('leg.HR',(-.54,.63,1.2),(-.54,.43,.19),'body'),
        ('tail',(0,1.0,1.08),(0,1.56,1.40),'body')],
        'notes':['Reference-led rabbit v002 with continuous seated anatomy, rounded paws, expressive almond eyes and deep violet ear bowls.',
            'Layered cream fur, curled cotton tail and fitted architectural rose-gold/lavender fittings preserve Liora identity.',
            'Unchanged single-view rabbit.png remains the authority. Hidden surfaces inferred; no exact 1:1 claim.']}

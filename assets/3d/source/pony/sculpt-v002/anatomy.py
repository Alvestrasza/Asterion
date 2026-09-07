"""Caelo's second, reference-led equine sculpt. X lateral, -Y front, Z up."""
from __future__ import annotations
import math
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


def palette(g):
    for key, color, metal, rough in (
        ('cv_skin','EDE1C8',0,.51),('cv_inner','D29A86',0,.58),
        ('cv_lip','946954',0,.56),('cv_ink','211B23',0,.42),
        ('cv_brow','7F9EBE',0,.61),('cv_hoof','6D8DC5',.12,.31),
        ('cv_sole','4B5B85',.10,.57),('cv_white','FFF7E8',0,.22)):
        g.M[key]=g.material(key,color,metal,rough)


def paint(g,obj,fn):
    """An authored, exportable vertex palette; no view-dependent image mapping."""
    attr=obj.data.color_attributes.new(name='AST_eye_color',type='FLOAT_COLOR',domain='POINT')
    base=obj.data.materials[0].diffuse_color
    for vertex, item in zip(obj.data.vertices,attr.data):
        item.color=fn(obj.matrix_world@vertex.co,base)
    mat=obj.data.materials[0]
    mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(1,1,1,1)
    node=mat.node_tree.nodes.get('Caelo authored colors') or mat.node_tree.nodes.new('ShaderNodeVertexColor')
    node.name='Caelo authored colors';node.layer_name='AST_eye_color'
    mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])


def skin_color(p,base):
    warm=math.exp(-((p.y+2.00)/.27)**2-((p.z-3.04)/.23)**2)
    soft=.96+.04*math.sin(p.z*5+p.y*3)*math.sin(p.x*6)
    return (base[0]*soft,base[1]*soft*(1-.095*warm),base[2]*soft*(1-.12*warm),1)


def face_eye(g, head, side, sign):
    """Recessed elongated eye, sculpted tapered eyelids, wing and living iris."""
    name='caelo_v2_eye_'+side;w=.495;h=.585
    c=Vector((sign*.405,-1.655,3.345));n=Vector((sign*.60,-.80,.035)).normalized()
    u=Vector((0,0,1)).cross(n).normalized();v=n.cross(u).normalized()
    tree=BVHTree.FromPolygons([head.matrix_world@p.co for p in head.data.vertices],
                              [list(p.vertices) for p in head.data.polygons])
    hit,_,_,_=tree.ray_cast(c+n*2,-n)
    if hit is None:raise ValueError('Missing eye landmark')
    c=hit+n*.008
    def surface(x,z,off=0):
        p=c+u*x+v*z;hit,_,_,_=tree.ray_cast(p+n*2,-n)
        r=math.sqrt((x/(w*.5))**2+(z/(h*.5))**2)
        blend=max(0,min(1,(r-.52)/.48));blend=blend*blend*(3-2*blend)
        # The iris has its own ocular curvature. Only the rim conforms to the
        # skull; otherwise the eye wraps unnaturally around the muzzle in profile.
        inset=.024*(1-min(1,r)**2)
        return (p.lerp(hit,blend) if hit is not None else p)+n*(.008+off-inset)
    cutter=g.uv(name+'_socket',c-n*.045,(w*.515,h*.515,w*.32),'cv_skin','head',seg=72,rings=48)
    cutter.rotation_euler=Matrix((u,v,n)).transposed().to_euler()
    mod=head.modifiers.new('Real almond socket','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    g.apply(head,mod);g.ASSET.remove(cutter);bpy.data.objects.remove(cutter,do_unlink=True)
    seg=160;rings=64;verts=[];faces=[];cols=[]
    ivory=g.color('FFF4DA');dark=g.color('0B142B')
    deep=g.color('273E76');blue=g.color('79C2F4')
    def coord(a,t=1):
        x=w*.5*math.cos(a)*t
        z=h*.5*math.sin(a)*(.84+.16*abs(math.sin(a)))*t+sign*x*.055
        return x,z
    for ring in range(rings+1):
        t=max(.00001,ring/rings)
        for j in range(seg):
            x,z=coord(math.tau*j/seg,t);verts.append(surface(x,z,w*.075*(1-t*t)))
            ir=math.sqrt((x/(w*.408))**2+((z+h*.035)/(h*.475))**2)
            pr=math.sqrt((x/(w*.218))**2+((z-h*.065)/(h*.282))**2)
            col=ivory
            if ir<1:
                a=math.atan2(z/h,x/w);mix=max(0,min(1,.42-.62*z/(h*.5)))
                fiber=.026*math.sin(a*67+ir*11)+.016*math.sin(a*119-ir*8)
                shade=.93+fiber
                if ir>.93:shade*=.37+.63*(1-ir)/.07
                col=tuple((deep[k]*(1-mix)+blue[k]*mix)*shade for k in range(3))+(1,)
            if pr<1:
                t2=max(0,min(1,(pr-.95)/.05))
                col=tuple(dark[k]*(1-t2)+col[k]*t2 for k in range(3))+(1,)
            cols.append(col)
    for r in range(rings):
        for j in range(seg):
            a=r*seg+j;b=r*seg+(j+1)%seg;faces.append((a,b,b+seg,a+seg))
    mat=g.material(name+'_living_iris','FFFFFF',0,.25)
    mat.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.20
    node=mat.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name='AST_eye_color'
    mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    obj=g.mesh(name,verts,faces,mat,'head');obj['eye_side']=side
    attr=obj.data.color_attributes.new(name='AST_eye_color',type='FLOAT_COLOR',domain='POINT')
    for item,col in zip(attr.data,cols):item.color=col
    # Upper lashes taper into tear duct, broaden at the outer corner.
    for upper in (True,False):
        a0,a1=(0,math.pi) if upper else (math.pi,math.tau)
        points=[surface(*coord(a0+(a1-a0)*j/28),.011) for j in range(29)]
        widths=[(.005+.022*math.sin(math.pi*j/28)**.7) if upper else .009 for j in range(29)]
        g.sweep(name+('_upper_lash' if upper else '_lower_lid'),points,widths,
                [r*.65 for r in widths],'cv_ink' if upper else 'cv_skin','head',normal=n,steps=84,sides=20)
    out=sign*w*.49
    g.sweep(name+'_outer_lash_wing',[surface(out,.035,.014),surface(out+sign*.04,.055,.011),
        surface(out+sign*.087,.098,.006)],[.024,.021,.0007],[.012,.010,.0006],'cv_ink','head',normal=n,steps=28,sides=20)
    crease=[surface(*coord(.15+(math.pi-.3)*j/24),.006)+v*.045 for j in range(25)]
    g.sweep(name+'_upper_fold',crease,[.003,.010,.003],[.003,.006,.003],'cv_skin','head',normal=n,steps=64,sides=16)
    brow=[surface(sign*q,z,.012) for q,z in ((-.11,.350),(-.025,.390),(.08,.376),(.15,.345))]
    g.sweep(name+'_blue_brow',brow,[.002,.022,.018,.001],[.002,.006,.006,.001],'cv_brow','head',normal=n,steps=44,sides=16)
    for suffix,x,z,rx,rz in (('catchlight',-.076,.133,.044,.049),('pinlight',.083,-.174,.013,.020)):
        t2=(x/(w*.5))**2+(z/(h*.5))**2
        g.disk(name+'_'+suffix,surface(x,z,w*.075*(1-t2)+.008),u,v,n,rx,rz,'cv_white','head',bulge=.002,rings=8,seg=48)
    lidverts=[]
    for p in verts:
        d=p-c;lidverts.append(c+u*d.dot(u)*1.07+v*d.dot(v)*1.045+n*(d.dot(n)+.029))
    lid=g.mesh(name+'_closed_lid',lidverts,faces,'cv_skin','lid.'+side)
    lid['ast_lid_pivot']=list(c+n*.029)
    # Closed lid crease is actually bound to the lid, not a permanent mark.
    closed=[surface(w*.45*t,-h*.10*(1-t*t),w*.09*(1-t*t)+.033) for t in (-1,-.75,-.5,-.25,0,.25,.5,.75,1)]
    line=g.sweep(name+'_sleeping_lash',closed,[.002,.011,.012,.010,.002],[.002,.006,.006,.005,.001],
                 'cv_ink','lid.'+side,normal=n,steps=60,sides=16)
    line['ast_lid_pivot']=list(c+n*.029)


def ear(g,sign):
    side='L' if sign>0 else 'R';steps=72;cols=32;verts=[];faces=[]
    for layer in (1,-1):
        for j in range(steps+1):
            t=j/steps;width=.221*math.sin(math.pi*t)**.70+.0003
            x=sign*(.438+.20*t-.024*math.sin(math.pi*t));z=3.66+1.145*t
            y=-.95+.02*math.sin(math.pi*t)-.06*t
            for k in range(cols+1):
                q=k/cols*2-1
                depth=(.016+.071*q*q)*math.sin(math.pi*t)**.6
                yy=y-depth if layer==1 else y+.125*math.sqrt(max(0,1-q*q))*math.sin(math.pi*t)
                verts.append((x+q*width,y if t==0 else yy,z+sign*q*.04))
    size=(steps+1)*(cols+1)
    for r in range(steps):
        for k in range(cols):
            a=r*(cols+1)+k;b=a+cols+1
            faces.extend([(a,a+1,b+1,b),(a+size,b+size,b+size+1,a+size+1)])
    boundary=list(range(cols+1))+[r*(cols+1)+cols for r in range(1,steps+1)]+[steps*(cols+1)+k for k in range(cols-1,-1,-1)]+[r*(cols+1) for r in range(steps-1,0,-1)]
    faces.extend((a,b,b+size,a+size) for a,b in zip(boundary,boundary[1:]+boundary[:1]))
    obj=g.mesh('caelo_v2_cupped_ear_'+side,verts,faces,'cv_skin','ear.'+side)
    # Pink inset follows the actual concavity and narrows into the sharp tip.
    pinkverts=[];pinkfaces=[]
    for j in range(65):
        t=.15+.78*j/64;x=sign*(.438+.20*t-.024*math.sin(math.pi*t));z=3.66+1.145*t
        width=.221*math.sin(math.pi*t)**.70
        for k in range(25):
            q=(k/24*2-1)*.76*math.sin(math.pi*j/64)**.35
            pinkverts.append((x+q*width,-.95+.02*math.sin(math.pi*t)-.06*t-(.031+.071*q*q)*math.sin(math.pi*t)**.6,z+sign*q*.04))
    for r in range(64):
        for k in range(24):
            a=r*25+k;pinkfaces.append((a,a+1,a+26,a+25))
    inside=g.mesh('caelo_v2_ear_inset_'+side,pinkverts,pinkfaces,'cv_inner','ear.'+side)
    m=inside.modifiers.new('Inset thickness','SOLIDIFY');m.thickness=.004;g.apply(inside,m)


def hoof(g,x,y,part):
    sides=96;steps=24;verts=[];faces=[]
    for j in range(steps+1):
        t=j/steps;z=.027+.272*t;s=1.03-.23*t+.055*math.sin(math.pi*t)
        for k in range(sides):
            a=math.tau*k/sides
            verts.append((x+.228*s*math.cos(a),y-.035+.290*s*math.sin(a)-.024*(1-t),z))
    for r in range(steps):
        for k in range(sides):
            a=r*sides+k;b=r*sides+(k+1)%sides;faces.append((a,b,b+sides,a+sides))
    faces += [tuple(reversed(range(sides))),tuple(steps*sides+k for k in range(sides))]
    obj=g.mesh('caelo_v2_blue_hoof_'+part,verts,faces,'cv_hoof',part)
    bevel=obj.modifiers.new('Soft hoof rim','BEVEL');bevel.width=.009;bevel.segments=3;g.apply(obj,bevel)
    # Jagged ivory feathering grows from fetlock and overlaps the hoof shell.
    for j in range(15):
        a=math.tau*(j+.3)/15;d=Vector((math.cos(a),math.sin(a),0))
        center=Vector((x,y,.335));length=.075+.026*math.cos(j*2.1)
        g.sweep('caelo_v2_fetlock_tuft_'+part+'_'+str(j),
            [center+d*.153,center+d*.181+Vector((0,0,-.018)),center+d*.204+Vector((0,0,-length))],
            [.030,.043,.0007],[.021,.023,.0007],'cv_skin',part,normal=d,steps=20,sides=14)


def build(g):
    palette(g)
    torso=g.fuse('caelo_v2_torso',[
        g.uv('rib',(0,.13,1.56),(.55,.94,.53),'cv_skin'),
        g.uv('rump',(0,.79,1.54),(.55,.57,.55),'cv_skin'),
        g.uv('chest',(0,-.55,1.57),(.51,.48,.62),'cv_skin'),
        g.uv('neckbase',(0,-.68,2.01),(.36,.40,.70),'cv_skin'),
        g.uv('neckarch',(0,-1,2.53),(.33,.36,.62),'cv_skin')],voxel=.024,subdiv=1)
    groups={key:torso.vertex_groups.new(name=key) for key in ('body','neck')}
    for vertex in torso.data.vertices:
        p=torso.matrix_world@vertex.co;t=max(0,min(1,(p.z-1.92)/.66));t=t*t*(3-2*t)
        if t<1:groups['body'].add([vertex.index],1-t,'REPLACE')
        if t>0:groups['neck'].add([vertex.index],t,'REPLACE')
    head=g.fuse('caelo_v2_head',[
        g.loft('refined_head_planes',[(-2.12,2.97,.045,.045),(-2.03,3.00,.30,.20),
            (-1.85,3.13,.44,.32),(-1.60,3.31,.63,.56),(-1.28,3.34,.64,.65),
            (-.85,3.35,.47,.53),(-.61,3.33,.03,.08)],'cv_skin','head',sides=96,n=120),
        g.uv('jaw',(0,-1.54,2.955),(.48,.45,.22),'cv_skin','head'),
        g.uv('muzzlelip',(0,-1.936,2.972),(.315,.235,.170),'cv_skin','head')],
        'head',voxel=.017,subdiv=1)
    limbs=[]
    for sign in (-1,1):
        side='L' if sign>0 else 'R';face_eye(g,head,side,sign);ear(g,sign)
        for end,y in (('F',-.61),('H',.79)):
            part='leg.'+end+side;x=sign*.415;foot_y=y-.13
            if end=='F':
                pts=[(x,y,1.60),(x,y-.05,1.28),(x,y-.11,.89),(x,foot_y,.43),(x,foot_y,.23)]
                widths=[.17,.24,.162,.17,.16];depths=[.21,.29,.195,.192,.16]
            else:
                pts=[(x,y,1.66),(x,y+.13,1.31),(x,y+.235,.98),(x,y+.11,.66),(x,foot_y,.36),(x,foot_y,.23)]
                widths=[.13,.254,.20,.138,.17,.16];depths=[.18,.31,.229,.16,.188,.16]
            leg=g.sweep('caelo_v2_shaped_'+part,pts,widths,depths,'cv_skin',part,normal=(1,0,0),steps=110,sides=72)
            mod=leg.modifiers.new('Continuous limb finish','SUBSURF');mod.levels=1;g.apply(leg,mod)
            limbs.append(leg)
            hoof(g,x,foot_y,part)
    torso=g.fuse('caelo_v2_torso',[torso,*limbs],'body',voxel=.024,subdiv=1)
    torso.vertex_groups.clear()
    groups={key:torso.vertex_groups.new(name=key) for key in
            ('body','neck','leg.FL','leg.FR','leg.HL','leg.HR')}
    for vertex in torso.data.vertices:
        p=torso.matrix_world@vertex.co
        neck=max(0,min(1,(p.z-1.92)/.66));neck=neck*neck*(3-2*neck)
        lower=max(0,min(1,(1.65-p.z)/.48));lower=lower*lower*(3-2*lower)
        lateral=max(0,min(1,(abs(p.x)-.18)/.12))
        limb=lower*lateral
        region='F' if p.y<.15 else 'H';side='L' if p.x>0 else 'R'
        for key,weight in (('neck',neck),('body',(1-neck)*(1-limb)),('leg.'+region+side,(1-neck)*limb)):
            if weight>0:groups[key].add([vertex.index],weight,'REPLACE')
    tree=BVHTree.FromPolygons([head.matrix_world@v.co for v in head.data.vertices],[list(p.vertices) for p in head.data.polygons])
    def front(x,z,offset=.004):
        p,_,_,_=tree.ray_cast(Vector((x,-4,z)),Vector((0,1,0)))
        if p is None:raise ValueError('Missing mouth landmark')
        return p+Vector((0,-offset,0))
    # Small recessed nostrils and a flush smiling mouth, no protruding wire.
    for sign in (-1,1):
        pts=[front(sign*x,z,.007) for x,z in ((.165,3.052),(.186,3.073),(.213,3.081),(.226,3.070))]
        g.sweep('caelo_v2_nostril_'+str(sign),pts,[.001,.011,.012,.001],[.001,.008,.009,.001],
                'cv_lip','head',normal=(0,-1,0),steps=24,sides=16)
        pts=[front(sign*x,z,.006) for x,z in ((0,2.858),(.074,2.859),(.159,2.872),(.22,2.906),(.247,2.936 if sign>0 else 2.918))]
        g.sweep('caelo_v2_smile_'+str(sign),pts,[.004,.006,.007,.008,.002],[.003,.004,.004,.005,.001],
                'cv_lip','head',normal=(0,-1,0),steps=48,sides=16)
    # All ivory meshes receive the same warm, soft spatial palette.
    for obj in g.ASSET:
        if obj.data.materials and obj.data.materials[0]==g.M['cv_skin']:paint(g,obj,skin_color)
    return {'name':'Caelo','kind':'pony','family':'quadruped','bones':[
        ('body',(0,.15,1.5),(0,.15,2),None),('neck',(0,-.65,2.0),(0,-1.01,2.85),'body'),
        ('head',(0,-1.03,2.87),(0,-1.13,3.83),'neck'),
        ('ear.L',(.44,-.98,3.68),(.63,-.99,4.80),'head'),('ear.R',(-.44,-.98,3.68),(-.63,-.99,4.80),'head'),
        ('leg.FL',(.415,-.61,1.40),(.415,-.74,.22),'body'),('leg.FR',(-.415,-.61,1.40),(-.415,-.74,.22),'body'),
        ('leg.HL',(.415,.79,1.40),(.415,.66,.22),'body'),('leg.HR',(-.415,.79,1.40),(-.415,.66,.22),'body'),
        ('tail',(0,1.20,1.85),(0,2.3,1.25),'body')],
        'notes':['Reference-led v002: elongated sculpted eyelids, recessed nostrils, refined muzzle, cupped ears, shaped limbs and feathered hooves.',
                 'Flowing modeled curls and architectural star tack replace the simplified v001 surfaces.',
                 'Original single-view artwork is unchanged. Unseen surfaces remain inferred.']}

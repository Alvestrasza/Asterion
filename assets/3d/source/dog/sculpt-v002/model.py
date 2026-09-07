"""Fenn v002: a golden, plush puppy with dark ear gradients and celestial collar.

The unchanged dog portrait remains the authority. Hidden forms are interpreted
as an editable, fully volumetric character, not projected from the illustration.
"""
import math

from mathutils import Vector
from fenn_detail import Art, Surface, path, smooth, mix


def _palette(g):
    a=Art(g,'fenn_v2',{
        'coat':('A66C22',0,.68),'ink':('241A14',0,.52),'white':('FFFFFF',0,.25),
        'nose':('44301E',0,.40),'metal':('B98137',.55,.42),
        'metal_light':('E8B969',.53,.41),'metal_dark':('775020',.52,.45),
        'navy':('122A49',.13,.44),'cream_mark':('F0D69C',0,.64),
        'gem':('214F9A',.10,.31),'gem_light':('598DD0',.10,.30),'gem_dark':('152C54',.10,.35)})
    golden=tuple(g.color(h) for h in ('743D0C','9D6118','BF8328','E1AD57'))
    cream=tuple(g.color(h) for h in ('9C7A46','B79964','D8BD87','EFDCB0'))
    brown=tuple(g.color(h) for h in ('1E140C','382313','5D3B20','875B2F'))
    return a,golden,cream,brown


def _blend_palette(a,b,t):
    return tuple(mix(x,y,t) for x,y in zip(a,b))


def _surface_lock(a,surface,name,control,width,depth,palette,part='head',normal=(0,-1,0),root_palette=None,steps=42,sides=30):
    """Follow the support along the whole strand, avoiding floating end shards."""
    controls=path(control,18);seated=[];first_normal=None
    for i,p in enumerate(controls):
        q,n=surface.contact(p,normal,-.008+.014*smooth(i/18))
        seated.append(q)
        if first_normal is None:first_normal=n
    return a.lock(name,seated,width,depth,palette,part,first_normal,steps,sides,root_palette)


def _anatomy(a):
    parts=[a.uv('ribcage',(0,.13,1.13),(.59,.89,.59)),
           a.uv('rump',(0,.72,1.11),(.59,.59,.64)),
           a.uv('chest',(0,-.49,1.36),(.54,.51,.66)),
           a.uv('neck',(0,-.64,1.84),(.46,.43,.48))]
    for sign,side in ((1,'L'),(-1,'R')):
        for end,x,y in [('F',sign*.42,-.58),('H',sign*.51,.67)]:
            if end=='F':
                points=[(x,y,1.48),(x,y-.018,1.12),(x,y-.075,.68),(x,y-.15,.27)]
                widths=[.18,.24,.20,.19];depths=[.22,.26,.20,.23]
            else:
                points=[(x,y,1.44),(x,y+.09,1.10),(x,y+.14,.71),(x,y-.17,.27)]
                widths=[.20,.30,.205,.20];depths=[.24,.32,.21,.23]
            parts.append(a.g.sweep(a.prefix+'_leg_mass_'+end+side,points,widths,depths,a.keys['coat'],'body',
                                  normal=(1,0,0),steps=72,sides=48))
            paw_y=y-.22
            parts.append(a.uv('paw_'+end+side,(x,paw_y,.17),(.275,.32,.18)))
            for j in (-1,0,1):
                parts.append(a.uv('toe_'+end+side+str(j),(x+j*.137,paw_y-.17,.155),(.116,.157,.138)))
    body=a.fuse('body',parts,voxel=.019,subdiv=1);a.weights(body)
    head=a.fuse('head',[
        a.uv('skull',(0,-.86,2.44),(.82,.66,.73),'coat','head',seg=80,rings=56),
        a.uv('muzzle_L',(.24,-1.405,2.18),(.305,.33,.245),'coat','head'),
        a.uv('muzzle_R',(-.24,-1.405,2.18),(.305,.33,.245),'coat','head'),
        a.uv('jaw',(0,-1.20,2.01),(.49,.35,.20),'coat','head'),
        a.uv('nose_bridge',(0,-1.48,2.285),(.21,.235,.17),'coat','head')],
        'head',voxel=.018,subdiv=1)
    return body,head


def _plush(a,name,control,sizes,part,palette_fn,normal=(0,-1,0),rows=168,sides=80):
    """A continuous solid volume; shallow sculpt grooves never split its shell."""
    centers=path(control,rows);profiles=path([(w,d,0) for w,d in sizes],rows)
    verts=[];faces=[];colors=[];frames=[];previous=Vector(normal).normalized()
    for i,c in enumerate(centers):
        t=i/rows;tangent=(centers[min(rows,i+1)]-centers[max(0,i-1)]).normalized()
        n=previous-tangent*previous.dot(tangent)
        if n.length<1.e-6:n=Vector((1,0,0))-tangent*tangent.x
        n.normalize();previous=n;u=tangent.cross(n).normalized();frames.append((tangent,u,n))
        for j in range(sides):
            angle=math.tau*j/sides;q=math.cos(angle);out=math.sin(angle)
            groove=(.5+.5*math.cos(11*angle+.35*math.sin(t*6)))**11
            sculpt=1-.032*groove+.009*math.cos(5*angle-t*4)
            # Coherent short fur carved into the full ear/tail shell, with
            # staggered tapered ridges rather than a collection of loose chips.
            vv=t*22+.12*math.sin(angle*4);row=math.floor(vv);tt=vv-row
            uu=angle/math.tau*18+.5*(row%2)+.12*math.sin(t*18)
            qq=uu-math.floor(uu)-.5
            ridge=max(0,1-(qq/.44)**2)**1.5*math.sin(math.pi*tt)**.70
            radial=u*q+n*out
            p=c+(u*profiles[i].x*q+n*profiles[i].y*out)*sculpt+radial*.0085*ridge*math.sin(math.pi*t)**.4;verts.append(p)
            pal=palette_fn(t,p,u*q+n*out)
            color=mix(pal[0],pal[2],.58+.045*max(0,out)-.018*groove+.010*ridge)
            colors.append(color[:3]+(1,))
    for i in range(rows):
        for j in range(sides):
            k=i*sides+j;l=i*sides+(j+1)%sides;faces.append((k,k+sides,l+sides,l))
    faces += [tuple(reversed(range(sides))),tuple(rows*sides+j for j in range(sides))]
    obj=a.mesh(name,verts,faces,'paint',part);a.colors(obj,colors)
    return obj,centers,profiles,frames


def _ears(a,golden,brown):
    for sign,side in ((1,'L'),(-1,'R')):
        palette=lambda t,p,n:_blend_palette(golden,brown,smooth((t-.08)/.54))
        core,centers,profiles,frames=_plush(a,'plush_floppy_ear_'+side,
            [(sign*.45,-.66,2.86),(sign*.69,-.58,2.98),(sign*.94,-.60,2.85),
             (sign*1.075,-.64,2.56),(sign*1.13,-.67,2.26),(sign*1.20,-.72,2.055),
             (sign*1.35,-.77,2.075)],
            [(.105,.13),(.24,.18),(.32,.20),(.345,.195),(.29,.17),(.175,.12),(.001,.001)],
            'ear.'+side,palette,rows=172,sides=88)
        support=Surface(core)
        for row in range(5):
            t=.18+row*.113
            for col in range(4):
                idx=int((t+.013*math.sin(col*2.1+row))*172);tan,u,n=frames[idx]
                lateral=(col-1.5)*.39
                root,normal=support.contact(centers[idx]+u*profiles[idx].x*lateral,n,-.019)
                length=.24+.045*math.sin(col*2.3+row*1.7);width=.073+.014*math.cos(col+row)
                direction=tan+u*(.11*math.sin(row*2+col));direction.normalize()
                pal=palette(min(1,t+.16),root,normal);rootpal=palette(t,root,normal)
                _surface_lock(a,support,'ear_flow_'+side+str(row)+'_'+str(col),[root,root+direction*.060+normal*.020,
                       root+direction*length*.67+normal*.022,root+direction*length+u*.012*math.sin(col)+normal*.007],
                       width,.016,pal,'ear.'+side,normal,root_palette=rootpal,steps=38,sides=28)
        for i in range(4):
            t=.16+i*.035;idx=int(t*172);tan,u,n=frames[idx]
            root=centers[idx]+u*profiles[idx].x*.42
            a.lock('ear_root_wisp_'+side+str(i),[root,root+Vector((sign*.08,-.02,.05)),
                   root+Vector((sign*.15,-.01,.09)),root+Vector((sign*.24,.03,.07-i*.017))],
                   .069,.025,golden,'ear.'+side,normal=(0,-1,.1),steps=44,sides=32)


def _fur(a,body,head,golden,cream):
    for sign,side in ((1,'L'),(-1,'R')):
        # Pale eyebrow wisps grow from the face instead of hanging above it.
        for i in range(5):
            root,n=head.contact((sign*(.23+i*.034),-1.43,2.885+i*.006),(0,-1,.18),-.018)
            a.lock('cream_brow_'+side+str(i),[root,root+Vector((sign*.035,-.014,.031)),
                   root+Vector((sign*(.10+i*.004),-.005,.082)),root+Vector((sign*(.17+i*.004),.035,.098-i*.014))],
                   .041,.017,cream,normal=n,steps=42,sides=30,root_palette=golden)
        for i in range(7):
            z=2.015+i*.098
            root,n=head.contact((sign*.65,-1.13,z),(sign*.62,-.78,.03),-.022)
            spread=.17+(.037 if i%3==0 else 0);vertical=(-.045,.015,-.02,.035)[i%4]
            pal=cream if i<3 else golden
            _surface_lock(a,head,'cheek_fluff_'+side+str(i),[root,root+Vector((sign*.07,-.01,-.025)),
                   root+Vector((sign*spread,.06,vertical)),root+Vector((sign*(spread+.06),.11,vertical+.023))],
                   .08+(i%3)*.01,.022,pal,normal=(sign*.62,-.78,.03),steps=44,sides=32,root_palette=golden)
        for row in range(3):
            for j in range(5):
                root,n=body.contact((sign*.82,.31+j*.145,1.53-row*.175),(sign,0,.02),-.018)
                length=.16+.035*math.sin(row*3+j)
                # Leave the shallow celestial marking's footprint clear. A
                # cream crescent should not be cut by a higher fur-lock tip.
                candidates=[root+Vector((0,length*t,-.155*t)) for t in (0,.25,.5,.75,1)]
                if any((p.y-.73)**2+(p.z-1.33)**2<.235**2 or
                       (p.y-.68)**2+(p.z-1.565)**2<.075**2 for p in candidates):continue
                _surface_lock(a,body,'haunch_flow_'+side+str(row)+'_'+str(j),[root,root+Vector((sign*.015,.045,-.032)),
                       root+Vector((sign*.026,.108,-.09)),root+Vector((sign*.035,length,-.155))],
                       .048+(j%2)*.006,.012,golden,'leg.H'+side,(sign,0,0),steps=30,sides=24)
        for end,x,y in [('F',sign*.42,-.58),('H',sign*.51,.67)]:
            for i in range(4):
                root,n=body.contact((x+sign*.24,y+.07,.48+i*.13),(sign,0,0),-.016)
                _surface_lock(a,body,'leg_fluff_'+end+side+str(i),[root,root+Vector((sign*.024,.023,-.03)),
                       root+Vector((sign*.042,.067,-.087)),root+Vector((sign*.056,.087,-.137))],
                       .046,.013,cream if i==0 else golden,'leg.'+end+side,(sign,0,0),steps=30,sides=24)
    # Crown flow is low and densely overlapping; no isolated conical spikes.
    for i in range(9):
        x=(i-4)*.106;y=-.92+.055*math.sin(i*2)
        root,n=head.contact((x,y,3.12),(0,0,1),-.025)
        _surface_lock(a,head,'crown_flick_'+str(i),[root,root+Vector((.015,.07,.045)),
               root+Vector((.06,.17,.13+(i%3)*.019)),root+Vector((.12,.32,.16+(i%3)*.028))],
               .080+(i%3)*.014,.032,golden,normal=(0,0,1),steps=54,sides=36)
    for row in range(2):
        for j in range(5):
            x=(j-2)*.19;z=2.78-row*.18;root,n=head.contact((x,-.05,z),(0,1,.04),-.024)
            _surface_lock(a,head,'nape_flow_'+str(row)+str(j),[root,root+Vector((x*.03,.026,-.04)),
                   root+Vector((x*.08,.052,-.12)),root+Vector((x*.15,.059,-.21+(j%2)*.02))],
                   .104,.015,golden,normal=(0,1,.04),steps=36,sides=28)
    # Layered bib: short curved overlapping locks with varied shoulder fans.
    for row in range(3):
        count=9 if row<2 else 7
        for j in range(count):
            x=(j-(count-1)/2)*(.091 if row<2 else .090);z=1.725-row*.235-.045*abs(x)
            if row<2 and abs(x)<.245:continue
            root,n=body.contact((x,-1.13,z),(0,-1,.025),-.013)
            length=.205+.040*(1-abs(x)/.5)+.023*math.sin(j*2.1+row)
            _surface_lock(a,body,'cream_bib_'+str(row)+'_'+str(j),[root,root+Vector((x*.055,-.024,-.055)),
                   root+Vector((x*.15,-.044,-length*.65)),root+Vector((x*.29,-.028,-length))],
                   .079+(j%3)*.009,.029,cream,'body',(0,-1,.025),steps=48,sides=36,root_palette=golden if row==0 else cream)


def _crescent(a,name,p,n,r,part,mat='cream_mark',surface=None,rotation=0):
    """Closed shallow crescent, with all vertices seated on one body surface."""
    p,n=Vector(p),Vector(n).normalized();u=Vector((0,0,1)).cross(n).normalized();v=n.cross(u)
    d=r*.37;inner=r*.84;meet=(r*r-inner*inner+d*d)/(2*d)
    outer_angle=math.asin(meet/r);inner_angle=math.asin((meet-d)/inner)
    verts=[];faces=[];seg=72
    for back in (False,True):
        for i in range(seg+1):
            t=i/seg
            for inside in (False,True):
                angle=(inner_angle-(math.pi+2*inner_angle)*t) if inside else (outer_angle-(math.pi+2*outer_angle)*t)
                radius=inner if inside else r;x=radius*math.cos(angle);z=radius*math.sin(angle)+(d if inside else 0)
                xx=x*math.cos(rotation)-z*math.sin(rotation);zz=x*math.sin(rotation)+z*math.cos(rotation)
                point=p+u*xx+v*zz
                if surface:point,no=surface.contact(point,n,.002 if back else .009)
                else:point+=n*(-.003 if back else .006)
                verts.append(point)
    layer=2*(seg+1)
    for i in range(seg):
        k=2*i;faces += [(k,k+2,k+3,k+1),(k+layer+1,k+layer+3,k+layer+2,k+layer),
                        (k,k+layer,k+layer+2,k+2),(k+1,k+3,k+3+layer,k+1+layer)]
    faces += [(0,1,layer+1,layer),(2*seg,2*seg+layer,2*seg+1+layer,2*seg+1)]
    return a.mesh(name,verts,faces,mat,part)


def _collar(a,body):
    count=180;rows=9;verts=[];faces=[];boundary=[[],[]];normals=[[],[]]
    for row in range(rows):
        band=(row/(rows-1)-.5)*.20
        for i in range(count):
            angle=math.tau*i/count;z=1.80+.195*(1-math.cos(angle))*.5+band
            n=Vector((math.sin(angle),-math.cos(angle),0))
            p,no=body.contact(Vector((0,-.64,z))+n*.65,n,.014+.011*math.sin(math.pi*row/(rows-1)))
            verts.append(p)
            if row in (0,rows-1):k=0 if row==0 else 1;boundary[k].append(p);normals[k].append(no)
    for row in range(rows-1):
        for i in range(count):
            k=row*count+i;l=row*count+(i+1)%count;faces.append((k,l,l+count,k+count))
    obj=a.mesh('navy_star_collar',verts,faces,'navy');mod=obj.modifiers.new('Leather collar depth','SOLIDIFY');mod.thickness=.012;a.g.apply(obj,mod)
    for k in (0,1):a.ribbon('collar_gold_edge_'+str(k),boundary[k],normals[k],.025,closed=True,height_scale=.5)
    for i in range(11):
        angle=math.tau*(i+.5)/11;z=1.80+.195*(1-math.cos(angle))*.5
        n=Vector((math.sin(angle),-math.cos(angle),0));p,no=body.contact(Vector((0,-.64,z))+n*.65,n,.030)
        a.star('collar_star_'+str(i),p,no,.039,stretch=1.20)


def _hardware(a,body,head):
    _collar(a,body)
    p,n=head.contact((0,-1.48,2.97),(0,-1,.13),.008)
    a.star('forehead_long_star',p,n,.155,'head',1.60)
    a.star('forehead_nested_star',p+n*.036,n,.080,'head',1.57,'metal')
    for sign,side in ((1,'L'),(-1,'R')):
        for i in range(2):
            p,n=head.contact((sign*(.48+i*.105),-1.37,2.25+i*.11),(sign*.45,-.88,.01),.005)
            a.star('cheek_spark_'+side+str(i),p,n,.038 if i else .049,'head',1.16)
        for name,y,z,r in [('shoulder',-.39,1.31,.15),('haunch',.73,1.33,.15)]:
            normal=Vector((sign,0,0));p,n=body.contact((sign*.8,y,z),normal,.002)
            part='leg.'+('F' if name=='shoulder' else 'H')+side
            _crescent(a,name+'_cream_crescent_'+side,p,normal,r,part,surface=body,rotation=-.72)
            q,no=body.contact(p+Vector((0,-.05,.235)),normal,.004);a.star(name+'_cream_spark_'+side,q,no,.045,part,1.2,'cream_mark')
        for end,x,y in [('F',sign*.42,-.73),('H',sign*.51,.50)]:
            p,n=body.contact((x,y-.22,.45),(0,-1,0),.005);a.star('ankle_gold_spark_'+end+side,p,n,.070,'leg.'+end+side,1.20)
    # Medallion rests over the bib, with a real navy disk and broad gold frame.
    normal=Vector((0,-1,-.08)).normalized();center,_=body.contact((0,-1.16,1.485),normal,.053)
    up=Vector((0,0,1));u=up.cross(normal).normalized();v=normal.cross(u)
    a.g.disk(a.prefix+'_navy_celestial_medallion',center,u,v,normal,.222,.238,a.keys['navy'],'body',bulge=.022,rings=32,seg=112)
    pts=[center+u*.225*math.cos(math.tau*i/160)+v*.241*math.sin(math.tau*i/160)+normal*.015 for i in range(160)]
    a.ribbon('medallion_gold_bezel',pts,[normal]*160,.041,closed=True,height_scale=.72)
    pts=[center+u*.193*math.cos(math.tau*i/140)+v*.209*math.sin(math.tau*i/140)+normal*.024 for i in range(140)]
    a.ribbon('medallion_inner_engraving',pts,[normal]*140,.008,closed=True,height_scale=.20)
    a.star('medallion_polar_star',center+v*.044+normal*.031,normal,.092,stretch=1.35)
    _crescent(a,'medallion_moon',center-v*.032+normal*.032,normal,.128,'body','metal_light')
    a.star('medallion_lower_point',center-v*.268+normal*.006,normal,.044,stretch=1.32)
    # Fully connected suspension ribbon and small oval gold loop.
    collar,_=body.contact((0,-1.2,1.80),(0,-1,0),.030)
    loop_center=center+v*.277;points=[]
    for i in range(100):
        angle=math.tau*i/100;points.append(loop_center+u*.042*math.cos(angle)+v*.070*math.sin(angle))
    a.ribbon('medallion_suspension_loop',points,[normal]*100,.029,closed=True,height_scale=.5)
    points=path([collar,collar+Vector((0,-.02,-.045)),loop_center+v*.044,loop_center+v*.010],44)
    a.ribbon('collar_hanging_tab',points,[normal]*45,.060,height_scale=.55)


def _tail(a,golden,cream):
    def palette(t,p,n):
        amount=smooth((t-.14)/.28)*smooth((n.z+.22)/.8)
        return _blend_palette(golden,cream,amount)
    core,centers,profiles,frames=_plush(a,'full_curled_tail',
        [(0,1.04,1.23),(0,1.55,1.28),(0,1.97,1.69),(0,2.14,2.15),
         (0,1.91,2.43),(0,1.52,2.33),(0,1.43,2.08),(0,1.61,1.98)],
        [(.22,.235),(.275,.28),(.30,.29),(.275,.275),(.25,.255),(.20,.22),(.11,.14),(.001,.001)],
        'tail',palette,(1,0,0),rows=190,sides=88)
    # The plume's fur relief is continuous with its main shell. No pale chips
    # interrupt the golden-to-cream gradient or hover around the curled tip.


def _face(a,head):
    center,n=head.contact((0,-1.86,2.30),(0,-1,0),.005)
    outline=[(-.132,.055),(-.081,.078),(.082,.073),(.134,.042),(.025,-.084),(-.027,-.082)]
    verts=[];faces=[]
    for scale,depth in ((.80,-.007),(1,.023),(.80,.066)):
        for x,z in outline:verts.append(center+Vector((x*scale,-depth,z*scale)))
    for ring in range(2):
        for j in range(6):faces.append((ring*6+j,ring*6+(j+1)%6,(ring+1)*6+(j+1)%6,(ring+1)*6+j))
    faces += [tuple(reversed(range(6))),tuple(12+j for j in range(6))]
    obj=a.mesh('soft_triangular_nose',verts,faces,'nose','head');mod=obj.modifiers.new('Soft nose bevel','BEVEL');mod.width=.014;mod.segments=4;a.g.apply(obj,mod)
    for sign,side in ((1,'L'),(-1,'R')):
        a.uv('nostril_'+side,center+Vector((sign*.070,-.063,.001)),(.025,.007,.015),'ink','head',seg=28,rings=20)
        pts=[]
        for p in path([(0,-1.79,2.215),(sign*.105,-1.77,2.07),(sign*.29,-1.62,2.092),(sign*.395,-1.50,2.18)],44):
            q,n=head.contact(p,(0,-1,0),.004);pts.append(q)
        a.g.sweep(a.prefix+'_gentle_smile_'+side,pts,[.002,.005,.006,.003],[.001,.003,.003,.001],
                  a.keys['ink'],'head',normal=(0,-1,0),steps=64,sides=16)


def build(g):
    a,golden,cream,brown=_palette(g);body,head=_anatomy(a)
    support,head_support=Surface(body),Surface(head)
    def face_palette(p):
        muzzle=smooth((-p.y-1.20)/.26)*(1-smooth((p.z-2.235)/.17))
        return _blend_palette(golden,cream,muzzle)
    def body_palette(p):
        paw=1-smooth((p.z-.31)/.14)
        bib=smooth((-p.y-.83)/.26)*smooth((p.z-1.02)/.25)*(1-smooth((p.z-1.81)/.30))
        return _blend_palette(golden,cream,max(paw,bib))
    for sign in (-1,1):a.eye(head,sign,(g.color('071A38'),g.color('105CA5')),golden,face_palette,width=.53,height=.49,z=2.515)
    a.paint(body,golden,.0045,body_palette);a.paint(head,golden,.0019,face_palette)
    _ears(a,golden,brown);_fur(a,support,head_support,golden,cream)
    _hardware(a,support,head_support);_tail(a,golden,cream);_face(a,head_support)
    return {'name':'Fenn','kind':'dog','family':'quadruped','bones':[
        ('body',(0,.13,1.0),(0,.13,1.65),None),('neck',(0,-.55,1.62),(0,-.67,2.06),'body'),
        ('head',(0,-.72,2.08),(0,-.84,3.13),'neck'),
        ('leg.FL',(.42,-.58,1.41),(.42,-.80,.17),'body'),('leg.FR',(-.42,-.58,1.41),(-.42,-.80,.17),'body'),
        ('leg.HL',(.51,.67,1.40),(.51,.45,.17),'body'),('leg.HR',(-.51,.67,1.40),(-.51,.45,.17),'body'),
        ('ear.L',(.45,-.66,2.86),(1.13,-.67,2.26),'head'),('ear.R',(-.45,-.66,2.86),(-1.13,-.67,2.26),'head'),
        ('tail',(0,1.04,1.23),(0,1.97,1.77),'body')],
        'notes':['Reference-led golden puppy: solid flowing dark-tipped ears, short layered fur, cream muzzle/bib/paws, full curled plume.',
                 'Nine presentation clips, independent recessed eyes, navy star collar and seated shallow celestial ornaments.',
                 'Hidden anatomy is interpreted; no image projection, exact likeness claim or mobile performance acceptance.']}

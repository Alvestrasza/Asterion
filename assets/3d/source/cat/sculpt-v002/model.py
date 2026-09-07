"""Nyra v002: sculpted charcoal feline, silver plume and copper/teal regalia.

The unchanged cat portrait is the visual authority. Hidden surfaces and nine
presentation gestures are coherent interpretations, never asserted exact copies.
"""
import math
import numpy as np

from mathutils import Vector
from nyra_detail import Art, Surface, path, smooth, mix


def _palette(g):
    a=Art(g,'nyra_v2',{
        'coat':('25292B',0,.66),'ink':('070D11',0,.55),'white':('FFFFFF',0,.25),
        'nose':('AE704D',.15,.43),'metal':('A96E4D',.57,.42),
        'metal_light':('D69970',.57,.39),'metal_dark':('694734',.52,.45),
        'armor':('075A57',.14,.45),'armor_line':('168981',.13,.42),
        'gem':('079E67',.17,.27),'gem_light':('72E7B2',.14,.26),
        'gem_dark':('075E45',.15,.30)})
    coat=tuple(g.color(h) for h in ('0C0F11','1C2023','353B3F','50585D'))
    silver=tuple(g.color(h) for h in ('1B2023','353D43','5B666F','85929A'))
    ear=tuple(g.color(h) for h in ('492C20','7B422C','A96740','C48C60'))
    return a,coat,silver,ear


def _anatomy(a):
    parts=[a.uv('ribcage',(0,.14,1.15),(.54,.90,.57)),
           a.uv('rump',(0,.71,1.14),(.56,.60,.61)),
           a.uv('chest',(0,-.52,1.35),(.48,.48,.63)),
           a.uv('neck',(0,-.67,1.79),(.38,.39,.44))]
    for sign in (-1,1):
        for end,x,y in [('F',sign*.405,-.59),('H',sign*.50,.65)]:
            if end=='F':
                points=[(x,y,1.45),(x,y-.025,1.10),(x,y-.10,.65),(x,y-.13,.28)]
                widths=[.16,.225,.165,.18];depths=[.20,.255,.185,.21]
            else:
                points=[(x,y,1.43),(x,y+.12,1.12),(x,y+.15,.76),(x,y-.09,.29)]
                widths=[.18,.29,.185,.19];depths=[.23,.31,.21,.23]
            parts.append(a.g.sweep(a.prefix+'_limb_'+end+str(sign),points,widths,depths,a.keys['coat'],'body',
                                  normal=(1,0,0),steps=72,sides=48))
            paw_y=y-.20
            parts.append(a.uv('paw_'+end+str(sign),(x,paw_y,.18),(.255,.32,.185)))
            for offset in (-.13,0,.13):parts.append(a.uv('toe_'+end+str(sign)+str(offset),(x+offset,paw_y-.18,.16),(.106,.16,.14)))
    body=a.fuse('body',parts,voxel=.019,subdiv=1);a.weights(body)
    head=a.fuse('head',[
        a.uv('skull',(0,-.86,2.42),(.76,.63,.67),'coat','head',seg=72,rings=48),
        a.uv('muzzle_L',(.21,-1.43,2.155),(.255,.315,.205),'coat','head'),
        a.uv('muzzle_R',(-.21,-1.43,2.155),(.255,.315,.205),'coat','head'),
        a.uv('lower_jaw',(0,-1.27,2.005),(.35,.34,.17),'coat','head'),
        a.uv('nose_bridge',(0,-1.51,2.245),(.16,.22,.15),'coat','head')],
        'head',voxel=.017,subdiv=1)
    return body,head


def _ear(a,sign,coat,inner):
    side='L' if sign>0 else 'R';rows,cols=88,36;verts=[];faces=[];colors=[]
    root=Vector((sign*.53,-.63,2.86));tip=Vector((sign*1.045,-.31,3.68))
    tangent=(tip-root).normalized();normal=Vector((sign*.12,-1,.045));normal=(normal-tangent*normal.dot(tangent)).normalized()
    lateral=tangent.cross(normal).normalized()
    for back in (False,True):
        for i in range(rows+1):
            t=i/rows;fade=math.sin(math.pi*t)**.75
            center=root.lerp(tip,t)+Vector((sign*.025,.04,0))*math.sin(math.pi*t)
            width=.30*math.sin(math.pi*t)**.72+.001
            for j in range(cols+1):
                q=2*j/cols-1
                depth=(.062*abs(q)**4-.060*(1-q*q))*fade if not back else -.105*math.sqrt(max(0,1-q*q))*fade-.018*fade
                p=center+lateral*q*width+normal*depth
                p+=normal*(.0015*math.sin(q*83+t*9)*fade*(1-q*q))
                verts.append(p)
                pal=inner if not back and abs(q)<.81 and .10<t<.96 else coat
                f=.52+.28*(1-abs(q))+.05*math.sin(t*33+q*7)
                colors.append(mix(pal[0],pal[2],f))
    layer=(rows+1)*(cols+1)
    for back in range(2):
        for i in range(rows):
            for j in range(cols):
                k=back*layer+i*(cols+1)+j;faces.append((k,k+1,k+cols+2,k+cols+1))
    boundary=list(range(cols+1))+[r*(cols+1)+cols for r in range(1,rows+1)]+[rows*(cols+1)+j for j in range(cols-1,-1,-1)]+[r*(cols+1) for r in range(rows-1,0,-1)]
    for k,l in zip(boundary,boundary[1:]+boundary[:1]):faces.append((k,l,l+layer,k+layer))
    obj=a.mesh('cupped_rust_ear_'+side,verts,faces,'paint','ear.'+side);a.colors(obj,colors)


def _fur(a,body,head,coat,silver):
    # Silver-gray locks grow from overlapping roots, not separate white blades.
    crown=[(-.31,-1.18,2.97,-.37,-.40,3.39,.16),
           (-.09,-1.23,3.00,.04,-.28,3.58,.22),
           (.13,-1.20,3.00,.29,-.21,3.48,.185),
           (.35,-1.01,2.97,.54,-.03,3.34,.145),
           (-.48,-.92,2.91,-.58,-.17,3.26,.13),
           (.06,-.89,3.04,.20,.00,3.39,.155),
           (-.22,-.74,3.01,-.19,.09,3.28,.14)]
    for i,(x,y,z,xx,yy,zz,width) in enumerate(crown):
        a.lock('silver_crest_'+str(i),[(x,y,z),(x-.035,y-.045,z+.22),
               ((x+xx)*.5,(y+yy)*.5,zz-.09),(xx,yy,zz)],width,.065,silver,steps=86,sides=56,root_palette=coat)
        a.lock('crest_undercoat_'+str(i),[(x,y+.055,z-.04),(x,y+.10,z+.19),
               (xx*.90,yy+.08,zz-.14),(xx*.94,yy+.15,zz-.03)],width*.76,.052,coat,steps=66,sides=44)
    for sign,side in ((1,'L'),(-1,'R')):
        for i,z in enumerate((2.035,2.16,2.28,2.395,2.53,2.66,2.765)):
            root=Vector((sign*(.555+(.026 if i%2 else 0)),-1.03+i*.034,z));length=(.25,.34,.31,.39,.30,.31,.21)[i]
            lift=(-.045,.035,-.01,.055,.005,.04,-.015)[i]
            points=[root,root+Vector((sign*.13,-.018,-.038)),root+Vector((sign*length,.11,lift)),root+Vector((sign*(length+.025),.27,lift+.035))]
            a.lock('cheek_fan_'+side+str(i),points,(.114,.123,.098,.116,.098,.093,.080)[i],.039,
                   silver if i in (1,3,5) else coat,normal=(sign*.68,-.73,.07),steps=62,sides=44,root_palette=coat)
            if i in (1,3,5):
                pts=[p+Vector((sign*.02,-.017,-.044)) for p in points]
                pts[-1]+=Vector((sign*.045,.02,-.02))
                a.lock('cheek_split_'+side+str(i),pts,.055,.021,silver,normal=(sign*.68,-.73,.07),steps=44,sides=32,root_palette=coat)
        for i in range(3):
            a.lock('ear_inner_brush_'+side+str(i),[(sign*(.60+i*.052),-.638,2.91+i*.038),
                   (sign*(.69+i*.045),-.656,3.00+i*.042),(sign*(.75+i*.045),-.642,3.10+i*.050),
                   (sign*(.80+i*.043),-.591,3.13+i*.072)],.065,.019,silver,'ear.'+side,normal=(0,-1,.03),steps=48,sides=32,root_palette=coat)
        for i in range(6):
            z=2.38+i*.119
            landmark=Vector((sign*.72,-.36,z));root,n=head.contact(landmark,(sign,.3,0),-.025)
            length=(.21,.25,.20,.24,.18,.15)[i]
            a.lock('outer_dark_ruff_'+side+str(i),[root,root+Vector((sign*.08,.045,-.012)),
                   root+Vector((sign*length,.14,-.01)),root+Vector((sign*(length+.03),.21,.022 if i%2 else -.033))],
                   .08+(i%3)*.013,.032,coat,normal=(sign,.25,0),steps=48,sides=36)
        for row in range(3):
            for j in range(4):
                landmark=(sign*.80,.33+j*.15,1.45-row*.19)
                root,n=body.contact(landmark,(sign,0,0),-.012)
                a.lock('haunch_coat_'+side+str(row)+str(j),[root,root+Vector((sign*.025,.035,-.05)),
                       root+Vector((sign*.035,.11,-.13)),root+Vector((sign*.055,.17,-.19))],.040,.017,coat,
                       'leg.H'+side,normal=n,steps=28,sides=24)
    # Shallow rearward bundles bridge the skull, crown and side ruff.
    for row in range(3):
        for j in range(5):
            x=(j-2)*.19;z=2.80-row*.18
            root,n=head.contact((x,-.10,z),(0,1,.10),-.026)
            a.lock('nape_bundle_'+str(row)+str(j),[root,root+Vector((x*.03,.032,-.04)),
                   root+Vector((x*.08,.063,-.13)),root+Vector((x*.16,.071,-.24+(j%2)*.025))],
                   .104+(j%2)*.014,.031,silver if row==0 and j in (1,2) else coat,
                   normal=n,steps=42,sides=32,root_palette=coat)
    for row in range(2):
        for j in range(7):
            x=(j-3)*.079;z=1.96-row*.17
            root,n=body.contact((x,-1.1,z),(0,-1,.03),-.014)
            a.lock('dark_bib_'+str(row)+str(j),[root,root+Vector((x*.08,-.026,-.045)),
                   root+Vector((x*.16,-.042,-.13)),root+Vector((x*.26,-.024,-.21))],.055,.025,coat,
                   'body',normal=n,steps=42,sides=32)


def _panel(a,surface,sign,side):
    outline=[(.39,1.94),(.76,1.85),(1.25,1.74),(1.67,1.50),
             (1.39,1.20),(.97,1.075),(.65,1.28),(.39,1.48)]
    center=Vector((.98,1.52));perimeter=[]
    for i,p in enumerate(outline):
        for j in range(16):perimeter.append(Vector(p).lerp(Vector(outline[(i+1)%len(outline)]),j/16))
    # Fit a low-order radial envelope, never reproduce each fused shoulder bump.
    # Its differential normals remain smooth across the broad metal chamfer.
    def basis(angle,z):
        h=z-1.50;c=math.cos(angle)
        return [1,h,h*h,h*h*h,c,c*c,h*c,h*h*c]
    samples=[];radii=[]
    for zi in range(15):
        z=1.075+(1.94-1.075)*zi/14
        for ai in range(17):
            angle=.39+(1.67-.39)*ai/16;n=Vector((sign*math.sin(angle),-math.cos(angle),0))
            origin=Vector((0,-.32,z));hit,_=surface.contact(origin+n*.7,n,0)
            samples.append(basis(angle,z));radii.append((hit-origin).dot(n))
    coefficients=np.linalg.lstsq(np.asarray(samples),np.asarray(radii),rcond=None)[0]
    residual=np.asarray(radii)-np.asarray(samples)@coefficients
    clearance=float(max(residual))+.011
    def position(angle,z):
        radius=float(np.dot(coefficients,basis(angle,z)))+clearance
        return Vector((sign*math.sin(angle)*radius,-.32-math.cos(angle)*radius,z))
    def sample(angle,z,offset):
        p=position(angle,z)
        du=position(angle+.0002,z)-position(angle-.0002,z)
        dv=position(angle,z+.0002)-position(angle,z-.0002)
        n=du.cross(dv).normalized()
        if n.dot(Vector((sign*math.sin(angle),-math.cos(angle),0)))<0:n=-n
        return p+n*offset,n
    rings=[(1,.007),(.98,.022),(.93,.036),(.80,.036),(.75,.019),(.69,.024),(.5,.034),(.25,.039)]
    count=len(perimeter);verts=[];faces=[];colors=[]
    for scale,offset in rings:
        for p in perimeter:
            q=center+(p-center)*scale;v,n=sample(q.x,q.y,offset+.020);verts.append(v)
    v,n=sample(center.x,center.y,.063);tip=len(verts);verts.append(v)
    for ring in range(len(rings)-1):
        for i in range(count):
            faces.append((ring*count+i,ring*count+(i+1)%count,(ring+1)*count+(i+1)%count,(ring+1)*count+i))
            colors.append(0 if ring<4 else 1)
    for i in range(count):faces.append(((len(rings)-1)*count+i,(len(rings)-1)*count+(i+1)%count,tip));colors.append(1)
    obj=a.mesh('fitted_teal_shoulder_'+side,verts,faces,'metal');obj.data.materials.append(a.g.M[a.keys['armor']])
    obj['smooth_envelope_clearance']=clearance
    for poly,color in zip(obj.data.polygons,colors):poly.material_index=color
    mod=obj.modifiers.new('Forged panel thickness','SOLIDIFY');mod.thickness=.022;a.g.apply(obj,mod)
    p,n=sample(.90,1.56,.072);a.star('shoulder_copper_star_'+side,p,n,.087)
    p,n=sample(1.28,1.63,.068);a.star('shoulder_teal_star_'+side,p,n,.083,mat='gem')


def _hardware(a,body,head):
    for sign,side in ((1,'L'),(-1,'R')):
        _panel(a,body,sign,side)
        brow=[];normals=[]
        for p in path([(sign*.24,-1.47,2.84),(sign*.35,-1.46,2.93),(sign*.49,-1.37,2.94),(sign*.63,-1.25,2.87)],48):
            hit,n=head.contact(p,(sign*.30,-.95,.08),.011);brow.append(hit);normals.append(n)
        a.ribbon('copper_brow_'+side,brow,normals,.039,'head',height_scale=.62)
        for arc in range(2):
            points=[];normals=[]
            for i in range(57):
                t=i/56;y=.69-.16+.32*t;z=1.39-arc*.055+.115*math.sin(math.pi*t)
                p,n=body.contact((sign*.86,y,z),(sign,0,0),.008);points.append(p);normals.append(n)
            a.ribbon('haunch_double_crescent_'+side+str(arc),points,normals,.018,'leg.H'+side,height_scale=.20)
        p,n=body.contact((sign*.75,.70,1.67),(sign,0,.1),.01);a.star('hip_spark_'+side,p,n,.056)
        for end,x,y in [('F',sign*.405,-.72),('H',sign*.50,.56)]:
            points=[];normals=[]
            for i in range(96):
                t=math.tau*i/96;z=.42+.052*max(0,-math.sin(t))**5
                p,n=body.outward((x,y,z),(math.cos(t),math.sin(t),0),.010,.42);points.append(p);normals.append(n)
            a.ribbon('angular_cuff_'+end+side,points,normals,.073,'leg.'+end+side)
            p,n=body.contact((x,y-.23,.46),(0,-1,0),.015);a.star('cuff_diamond_'+end+side,p,n,.083,'leg.'+end+side,1.25)
            for j in (-1,0,1):
                # Rounded copper toe sheaths, not long predatory needles.
                a.uv('rounded_copper_toe_'+end+side+str(j),(x+j*.127,y-.30,.171),(.079,.116,.123),
                     'metal_light','leg.'+end+side,seg=40,rings=28)
    p,n=head.contact((0,-1.45,2.91),(0,-1,.08),.012);a.star('forehead_copper_star',p,n,.13,'head',1.35)
    n=Vector((0,-1,-.08)).normalized();center,_=body.contact((0,-1.09,1.26),n,.022)
    a.frame('emerald_chest',center,n,[(0,.30),(.224,.145),(.22,-.17),(0,-.31),(-.22,-.17),(-.224,.145)])
    connector=center+Vector((0,.012,.423));a.frame('upper_emerald_diamond',connector,n,[(0,.133),(.104,0),(0,-.133),(-.104,0)])
    # A single fitted collar arc connects both bezel corners around the neck.
    pts=[];normals=[]
    for i in range(145):
        t=i/144;angle=.36+(math.tau-.72)*t;z=connector.z+.28*math.sin(math.pi*t)**.8
        radial=Vector((math.sin(angle),-math.cos(angle),0));p,normal=body.contact(Vector((0,-.64,z))+radial*.6,radial,.017)
        anchor=connector+Vector((.09 if t<.5 else -.09,0,0));f=smooth(min(t,1-t)/.075)
        pts.append(anchor.lerp(p,f));normals.append(n.lerp(normal,f).normalized())
    a.ribbon('continuous_copper_collar',pts,normals,.079)
    for sign,side in ((1,'L'),(-1,'R')):
        pts=[];normals=[]
        for p in path([center+Vector((sign*.17,0,-.19)),center+Vector((sign*.23,.02,-.34)),center+Vector((sign*.08,.025,-.43))],36):
            q,no=body.contact(p,(0,-1,0),.019);pts.append(q);normals.append(no)
        a.ribbon('lower_pendant_flame_'+side,pts,normals,.050,height_scale=.75)


def _tail(a,coat,silver):
    # One closed, full cross-section throughout the curl. The changing silver
    # bands are continuous vertex color, not detached light-colored ribbons.
    control=[(0,1.00,1.32),(0,1.45,1.39),(0,1.86,1.98),(0,2.02,2.65),
             (0,2.53,2.85),(0,2.97,2.54),(0,2.99,2.09),(0,2.69,1.68),
             (0,2.91,1.38),(0,3.18,1.57)]
    sizes=[(.18,.20,0),(.265,.28,0),(.29,.31,0),(.27,.31,0),(.255,.29,0),
           (.24,.28,0),(.20,.235,0),(.155,.18,0),(.09,.12,0),(.001,.001,0)]
    rows,sides=220,96;centers=path(control,rows);profiles=path(sizes,rows)
    verts=[];faces=[];colors=[]
    for i,c in enumerate(centers):
        t=i/rows;tangent=(centers[min(rows,i+1)]-centers[max(0,i-1)]).normalized()
        n=Vector((1,0,0));u=tangent.cross(n).normalized();width,depth=profiles[i].x,profiles[i].y
        for j in range(sides):
            angle=math.tau*j/sides;lateral=math.cos(angle);outward=math.sin(angle)
            groove=(.5+.5*math.cos(13*angle+.40*math.sin(t*6)))**12
            relief=1-.042*groove+.012*math.cos(5*angle+t*3)
            radial=u*lateral+n*outward;p=c+(u*width*lateral+n*depth*outward)*relief
            verts.append(p)
            shade=.59+.055*math.sin(angle*3+t*2)-.028*groove
            dark=mix(coat[0],coat[2],shade);light=mix(silver[0],silver[2],.57+.10*max(0,radial.z))
            silver_amount=smooth((t-.13)/.19)*(1-smooth((t-.76)/.17))*smooth((radial.z+.34)/.99)
            color=mix(dark,light,silver_amount);colors.append(color[:3]+(1,))
    for i in range(rows):
        for j in range(sides):
            k=i*sides+j;l=i*sides+(j+1)%sides;faces.append((k,l,l+sides,k+sides))
    faces.extend([tuple(reversed(range(sides))),tuple(rows*sides+j for j in range(sides))])
    core=a.mesh('continuous_plume_tail',verts,faces,'paint','tail');a.colors(core,colors)
    support=Surface(core)
    for sign,side in ((1,'L'),(-1,'R')):
        for i in range(4):
            t=.24+i*.115;index=int(t*rows);p=centers[index]+Vector((sign*profiles[index].y*.76,0,.04))
            root,n=support.contact(p,(sign,0,.12),-.027)
            tangent=(centers[index+5]-centers[index-5]).normalized()
            a.lock('plume_edge_bundle_'+side+str(i),[root,root+tangent*.09+n*.018,
                   root+tangent*.21+n*.027,root+tangent*.30+n*.047],.085,.030,
                   silver if i<3 else coat,'tail',n,steps=50,sides=36,root_palette=coat)
        for j in range(2):
            # Smooth analytic ornament support intentionally bridges the tiny
            # sculpt grooves. Projecting each metal vertex into those grooves
            # would reproduce a wrinkled, partially buried strip.
            def shell(t,angle,height):
                f=t*rows;k=min(rows-1,int(f));blend=f-k
                c=centers[k].lerp(centers[k+1],blend);sz=profiles[k].lerp(profiles[k+1],blend)
                tangent=(centers[min(rows,k+2)]-centers[max(0,k-1)]).normalized()
                n=Vector((1,0,0));u=tangent.cross(n).normalized()
                radial=(u*math.cos(angle)/sz.x+n*math.sin(angle)/sz.y).normalized()
                return c+u*sz.x*math.cos(angle)+n*sz.y*math.sin(angle)+radial*(.009+height)
            verts=[];faces=[];count=82
            cross=[(-.5,0),(-.5,.003),(-.32,.009),(.32,.009),(.5,.003),(.5,0)]
            for i in range(count):
                f=i/(count-1);t=.265+j*.067+f*.195
                taper=.12+.88*math.sin(math.pi*f)**.45
                angle=sign*(math.pi/2+.20-j*.20-.30*f)
                for offset,height in cross:verts.append(shell(t,angle+offset*.17*taper,height*taper))
            for i in range(count-1):
                for k in range(6):faces.append((i*6+k,(i+1)*6+k,(i+1)*6+(k+1)%6,i*6+(k+1)%6))
            faces += [tuple(reversed(range(6))),tuple((count-1)*6+k for k in range(6))]
            a.mesh('tail_copper_sweep_'+side+str(j),verts,faces,'metal','tail')


def build(g):
    a,coat,silver,inner=_palette(g);body,head=_anatomy(a)
    body_support,head_support=Surface(body),Surface(head)
    for sign in (-1,1):a.eye(head,sign,(g.color('033320'),g.color('0C9552')),coat,width=.54,height=.47,z=2.50)
    a.paint(body,coat,.0040);a.paint(head,coat,.0016)
    for sign in (-1,1):_ear(a,sign,coat,inner)
    _fur(a,body_support,head_support,coat,silver);_hardware(a,body_support,head_support);_tail(a,coat,silver)
    nose,n=head_support.contact((0,-1.81,2.235),(0,-1,0),.006)
    nose_outline=[(-.113,.042),(-.075,.061),(.075,.061),(.113,.042),(.023,-.063),(-.023,-.063)]
    verts=[];faces=[]
    for scale,depth in ((.82,-.005),(1,.019),(.77,.049)):
        for x,z in nose_outline:verts.append(nose+Vector((x*scale,-depth,z*scale)))
    for ring in range(2):
        for j in range(6):faces.append((ring*6+j,ring*6+(j+1)%6,(ring+1)*6+(j+1)%6,(ring+1)*6+j))
    faces.extend([tuple(reversed(range(6))),tuple(12+j for j in range(6))])
    obj=a.mesh('triangular_copper_nose',verts,faces,'nose','head')
    mod=obj.modifiers.new('Soft nose corners','BEVEL');mod.width=.009;mod.segments=3;g.apply(obj,mod)
    for sign,side in ((1,'L'),(-1,'R')):
        pts=[]
        for p in path([(0,-1.68,2.18),(sign*.105,-1.59,2.102),(sign*.25,-1.46,2.14),(sign*.32,-1.36,2.195)],38):
            q,n=head_support.contact(p,(0,-1,0),.003);pts.append(q)
        g.sweep(a.prefix+'_smile_'+side,pts,[.002,.004,.004,.002],[.001,.003,.003,.001],a.keys['ink'],'head',normal=(0,-1,0),steps=48,sides=14)
    return {'name':'Nyra','kind':'cat','family':'quadruped','bones':[
        ('body',(0,.12,1.0),(0,.12,1.61),None),('neck',(0,-.55,1.62),(0,-.67,2.05),'body'),
        ('head',(0,-.72,2.06),(0,-.84,3.10),'neck'),
        ('leg.FL',(.405,-.59,1.39),(.405,-.79,.18),'body'),('leg.FR',(-.405,-.59,1.39),(-.405,-.79,.18),'body'),
        ('leg.HL',(.50,.65,1.39),(.50,.45,.18),'body'),('leg.HR',(-.50,.65,1.39),(-.50,.45,.18),'body'),
        ('ear.L',(.53,-.63,2.86),(1.00,-.34,3.58),'head'),('ear.R',(-.53,-.63,2.86),(-1.00,-.34,3.58),'head'),
        ('tail',(0,1.03,1.33),(0,2.04,1.90),'body')],
        'notes':['Reference-led charcoal feline with integrated short fur, shaded silver crest/cheeks and a layered curled plume.',
                 'Recessed independent ocular surfaces, clean fitted teal/copper hardware and rounded copper toe sheaths.',
                 'Hidden anatomy and nine presentation gestures are interpretations; no projected portrait or exact likeness claim.']}

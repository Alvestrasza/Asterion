"""Selya sculpt-v002: reference-led fairy anatomy, botanical dress and hair.

The unchanged fairy.png is the single-view authority. All hidden forms are
coherent interpretations. Geometry and authored POINT colors, not projected
artwork, carry the sculpt's detail. build(g) returns the stable nine-clip spec.
"""
from __future__ import annotations

import math

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.noise import noise


TAU=math.tau


def mix(a,b,t):
    t=max(0.,min(1.,t))
    return tuple(x+(y-x)*t for x,y in zip(a,b))


def palette(g):
    for key,tint,metal,rough in (
        ('skin','C88747',0,.56),('skin_shadow','9C582E',0,.61),
        ('lip','AF5534',0,.52),('brow','67372C',0,.65),('lash','241C17',0,.55),
        ('hair','CC725F',0,.49),('coral','D77B60',.07,.44),
        ('mint','72967B',.06,.48),('ivory','DBC89A',.05,.47),
        ('wing','C4D5B5',.12,.36),('gold','B78332',.73,.34),
        ('gold_light','DFB55B',.70,.31),('gold_dark','7D5427',.68,.39),
        ('gem','438F77',.34,.23),('gem_light','8BD4AC',.30,.23),
        ('gem_dark','235E53',.35,.26),('white','FFFFFF',0,.22)):
        g.M['sv_'+key]=g.material('Selya_'+key,tint,metal,rough)
    for key in ('skin','hair','coral','mint','ivory','wing'):
        mat=g.M['sv_'+key];nodes=mat.node_tree.nodes
        node=nodes.new('ShaderNodeVertexColor');node.layer_name='AST_eye_color'
        mat.node_tree.links.new(node.outputs['Color'],nodes.get('Principled BSDF').inputs['Base Color'])
        nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.23


def paint(obj,values):
    attr=obj.data.color_attributes.get('AST_eye_color')
    if attr is None:attr=obj.data.color_attributes.new(name='AST_eye_color',type='FLOAT_COLOR',domain='POINT')
    attr.data.foreach_set('color',[c for rgba in values for c in rgba])


def skin_color(g,p):
    base=g.color('C8894B');light=g.color('DEAB70');blush=g.color('D77C57')
    col=mix(base,light,.28+.08*math.sin(p.z*2.4))
    cheek=math.exp(-((abs(p.x)-.43)/.18)**2-((p.z-3.11)/.17)**2)
    if p.y<-.22:col=mix(col,blush,.27*cheek)
    return col[:3]+(1.,)


def tree(obj):
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                                [list(p.vertices) for p in obj.data.polygons])


def bezier(points,t):
    a,b,c,d=map(Vector,points);s=1.-t
    p=a*s**3+b*(3*s*s*t)+c*(3*s*t*t)+d*t**3
    tangent=(3*s*s*(b-a)+6*s*t*(c-b)+3*t*t*(d-c)).normalized()
    return p,tangent


def spline(points,count):
    """C2 clamped B-spline, with no interpolating-knot elbows."""
    points=list(map(Vector,points));n=len(points)-1;p=min(3,n)
    knots=[0.]*(p+1)+[i/(n-p+1) for i in range(1,n-p+1)]+[1.]*(p+1)
    out=[]
    for j in range(count+1):
        t=j/count;k=n if j==count else next(k for k in range(p,n+1) if knots[k]<=t<knots[k+1])
        d=[points[k-p+i].copy() for i in range(p+1)]
        for r in range(1,p+1):
            for i in range(p,r-1,-1):
                lo=knots[i+k-p];hi=knots[i+1+k-r]
                a=(t-lo)/(hi-lo) if hi>lo else 0
                d[i]=d[i-1]*(1-a)+d[i]*a
        out.append(d[p])
    return out


def vein_line(g,name,points,radius,mat,part,resolution=4):
    """Same curved vein path, economical eight-sided subpixel cross-section."""
    curve=bpy.data.curves.new('Selya_'+name,'CURVE');curve.dimensions='3D'
    curve.resolution_u=resolution;curve.bevel_depth=radius;curve.bevel_resolution=1
    curve.use_fill_caps=True
    spline=curve.splines.new('BEZIER');spline.bezier_points.add(len(points)-1)
    for p,co in zip(spline.bezier_points,points):
        p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
    obj=bpy.data.objects.new('Selya_'+name,curve);bpy.context.collection.objects.link(obj)
    g.active(obj);bpy.ops.object.convert(target='MESH')
    return g.register(obj,name,mat,part)


def petal(g,name,points,width,material='coral',part='body',normal=(0,-1,0),
          bulge=.035,steps=52,cols=24,veins=3,wing=False,trim=True):
    """Closed bowed botanical shell, real rim depth and branching veins."""
    n0=Vector(normal).normalized()
    _,initial_tangent=bezier(points,0)
    initial_u=initial_tangent.cross(n0).normalized()
    def sample(t,q,face=1):
        c,tangent=bezier(points,t)
        # Transport the lateral axis, not a projected radial normal: the old
        # normal changed sign at a recurved tip and folded the entire blade.
        u=initial_u-tangent*initial_u.dot(tangent);u.normalize()
        n=u.cross(tangent).normalized()
        shape=(t**.60*(1-t)**1.08)/(.357143**.60*.642857**1.08)
        w=max(.00012,width*shape)
        ridge=.0028*math.cos(q*13+1.7*t)*math.sin(math.pi*t)*(1-q*q)
        height=.009+bulge*(1-q*q)*math.sin(math.pi*t)
        if face<0:height=.009+bulge*.30*(1-q*q)*math.sin(math.pi*t)
        return c+u*(w*q)+n*(face*(height+ridge)),n
    verts=[];faces=[];values=[]
    tones={'coral':('81332F','C45139','E59358'),'mint':('355644','779570','ADB88B'),
           'ivory':('8E7449','C6A770','E4C991'),'wing':('799E88','C7D9B8','ECE4BF'),
           'skin':('A56B3D','C8894B','DFAE72'),'gold':('7D5427','B78332','DFB55B')}
    dark,base,light=(g.color(h) for h in tones.get(material,tones['coral']))
    for face in (1,-1):
        for i in range(steps+1):
            t=i/steps
            for j in range(cols+1):
                q=2*j/cols-1;p,n=sample(t,q,face);verts.append(p)
                fiber=.027*math.sin(q*91+t*9)+.020*math.sin(q*137-t*13)
                cell=.045*noise(Vector((p.x*18,p.y*18,p.z*18)))
                col=mix(dark,base,.55+.25*math.sin(math.pi*t)+fiber+cell)
                col=mix(col,light,.12+.18*(1-abs(q))+.10*t)
                if wing:col=mix(col,light,.28+.09*math.sin(q*9+t*12))
                values.append(col[:3]+(1.,))
    offset=(steps+1)*(cols+1)
    for i in range(steps):
        for j in range(cols):
            a=i*(cols+1)+j;b=a+cols+1
            faces.extend(((a,a+1,b+1,b),(a+offset,b+offset,b+1+offset,a+1+offset)))
    boundary=list(range(cols+1))+[i*(cols+1)+cols for i in range(1,steps+1)]
    boundary += [steps*(cols+1)+j for j in range(cols-1,-1,-1)]+[i*(cols+1) for i in range(steps-1,0,-1)]
    faces.extend((a,b,b+offset,a+offset) for a,b in zip(boundary,boundary[1:]+boundary[:1]))
    obj=g.mesh('Selya_'+name,verts,faces,'sv_'+material,part)
    if material in ('skin','hair','coral','mint','ivory','wing'):paint(obj,values)
    if trim:
        outline=[(i/steps,-1) for i in range(steps+1)]+[(i/steps,1) for i in range(steps,-1,-1)]
        vs=[];fs=[]
        for t,q in outline:
            po,n=sample(t,q*1.018);pi,_=sample(t,q*(.91 if not wing else .967))
            vs.extend((po+n*.012,pi+n*.012,pi-n*.003,po-n*.003))
        for i in range(len(outline)):
            nxt=(i+1)%len(outline)
            for j in range(4):fs.append((i*4+j,nxt*4+j,nxt*4+(j+1)%4,i*4+(j+1)%4))
        g.mesh('Selya_'+name+'_forged_edge',vs,fs,'sv_gold_light' if wing else 'sv_gold',part)
    for face in ((1,-1) if wing else (1,)):
        if not veins:break
        centers=[]
        for i in range(2,steps-1,3):
            p,n=sample(i/steps,0,face);centers.append(p+n*(face*.006))
        vein_line(g,'Selya_'+name+'_midrib_'+str(face),centers,.006 if wing else .007,'sv_gold',part,resolution=3)
        for j in range(veins):
            t=.16+.66*(j+1)/(veins+1)
            for sign in (-1,1):
                coords=[(t,0),(t+.036,sign*.30),(min(.96,t+.10),sign*.69),(min(.98,t+.14),sign*.91)]
                pts=[p+n*(face*.006) for p,n in (sample(a,b,face) for a,b in coords)]
                vein_line(g,'Selya_'+name+'_vein_%d_%d_%d'%(face,j,sign),pts,.004 if wing else .0047,'sv_gold_light',part,resolution=4)
                if wing:
                    for k in (0,1):
                        coords=[(t+.055,sign*(.35+k*.18)),(t+.030,sign*(.53+k*.16)),(t-.013,sign*(.70+k*.12))]
                        pts=[p+n*(face*.007) for p,n in (sample(a,b,face) for a,b in coords)]
                        vein_line(g,'Selya_'+name+'_fine_branch_%d_%d_%d_%d'%(face,j,sign,k),pts,.0018,'sv_gold_light',part,resolution=3)
    return obj


def gem(g,name,c,normal,r,part):
    c=Vector(c);n=Vector(normal).normalized();u=Vector((1,0,0))-n*n.x;u.normalize();v=n.cross(u).normalized()
    shape=[(0,1.17),(.47,.64),(.73,.02),(.40,-.62),(0,-1.11),(-.40,-.62),(-.73,.02),(-.47,.64)]
    verts=[]
    for scale,depth in ((1.,0),(.72,.047)):
        verts += [c+u*(x*r*scale)+v*(z*r*scale)+n*depth for x,z in shape]
    verts.append(c+n*.072)
    faces=[tuple(reversed(range(8)))]
    faces += [(j,(j+1)%8,8+(j+1)%8,8+j) for j in range(8)]
    faces += [(16,8+j,8+(j+1)%8) for j in range(8)]
    obj=g.mesh('Selya_'+name,verts,faces,'sv_gem',part,smooth=False)
    obj.data.materials.append(g.M['sv_gem_light']);obj.data.materials.append(g.M['sv_gem_dark'])
    for p in obj.data.polygons:p.material_index=(0,0,1,0,2,0,1,2)[p.index%8]
    vs=[];fs=[]
    for x,z in shape:
        outward=c+u*x*r*1.23+v*z*r*1.16;inside=c+u*x*r*1.025+v*z*r*1.025
        vs.extend((outward+n*.028,inside+n*.028,inside-n*.025,outward-n*.025))
    for i in range(8):
        for j in range(4):fs.append((i*4+j,((i+1)%8)*4+j,((i+1)%8)*4+(j+1)%4,i*4+(j+1)%4))
    g.mesh('Selya_'+name+'_gold_bezel',vs,fs,'sv_gold',part,smooth=False)
    return obj


def ring(g,name,c,rx,ry,z,part,radius=.021):
    points=[(c[0]+rx*math.cos(TAU*j/32),c[1]+ry*math.sin(TAU*j/32),z) for j in range(33)]
    return g.line('Selya_'+name,points,radius,'sv_gold',part,resolution=3)


def eye(g,head,sign):
    side='L' if sign>0 else 'R';name='Selya_eye_'+side
    width=.405;height=.393;n=Vector((sign*.19,-.981,.025)).normalized()
    u=Vector((0,0,1)).cross(n).normalized();v=n.cross(u).normalized();bvh=tree(head)
    c=Vector((sign*.294,-.55,3.274));hit,_,_,_=bvh.ray_cast(c+n*2,-n)
    if hit is None:raise ValueError('Missing Selya eye landmark')
    c=hit+n*.006
    def coord(a,t=1):
        x=width*.5*math.cos(a)*t
        z=height*.5*math.sin(a)*(.67+.33*abs(math.sin(a)))*t+sign*x*.16
        return x,z
    def surface(x,z,offset=0):return c+u*x+v*z+n*(.013+offset)
    outline=[c+u*x+v*z for x,z in (coord(TAU*j/128,1.135) for j in range(128))]
    vs=[p+n*.35 for p in outline]+[p-n*.30 for p in outline]
    fs=[tuple(range(128)),tuple(reversed(range(128,256)))]
    fs.extend((j,j+128,(j+1)%128+128,(j+1)%128) for j in range(128))
    cutter=g.mesh(name+'_socket_cutter',vs,fs,'sv_skin','head')
    mod=head.modifiers.new('Recessed almond socket','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    g.apply(head,mod);g.ASSET.remove(cutter);bpy.data.objects.remove(cutter,do_unlink=True)
    rv=[];rf=[]
    for row in range(13):
        t=row/12
        for j in range(128):
            x,z=coord(TAU*j/128,.99+.16*t);p=c+u*x+v*z
            hit,_,_,_=bvh.ray_cast(p+n*2,-n)
            if hit is None:raise ValueError('Missing fairy orbital support')
            rv.append((p+n*.015).lerp(hit+n*.004,t*t*(3-2*t)))
    for row in range(12):
        for j in range(128):
            a=row*128+j;b=row*128+(j+1)%128;rf.append((a,a+128,b+128,b))
    g.mesh(name+'_orbital_skin',rv,rf,'sv_skin','head')
    verts=[];faces=[];colors=[];seg=128;rings=44
    ivory=g.color('D8C8A5');dark=g.color('091D19');upper=g.color('0C332B');lower=g.color('60AD86')
    for row in range(rings+1):
        t=max(.00001,row/rings)
        for j in range(seg):
            a=TAU*j/seg;x,z=coord(a,t);verts.append(surface(x,z,.029*(1-t*t)))
            ir=math.sqrt((x/(width*.422))**2+((z+height*.010)/(height*.474))**2)
            pr=math.sqrt((x/(width*.177))**2+((z-height*.055)/(width*.195))**2)
            col=ivory
            if ir<1:
                f=max(0,min(1,.35-z/(height*.64)));fiber=.037*math.sin(a*79+ir*14)+.024*math.sin(a*131-ir*19)
                shade=.96+fiber
                if ir>.91:shade*=.40+.60*(1-ir)/.09
                col=tuple((upper[k]*(1-f)+lower[k]*f)*shade for k in range(3))+(1,)
            if pr<1:col=dark
            colors.append(col)
    for row in range(rings):
        for j in range(seg):
            a=row*seg+j;b=row*seg+(j+1)%seg;faces.append((a,a+seg,b+seg,b))
    mat=g.material(name+'_living_iris','FFFFFF',0,.24)
    node=mat.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name='AST_eye_color'
    mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    obj=g.mesh(name,verts,faces,mat,'head');obj['eye_side']=side;paint(obj,colors)
    for top in (True,False):
        start,end=(0,math.pi) if top else (math.pi,TAU)
        pts=[surface(*coord(start+(end-start)*i/32),.010) for i in range(33)]
        widths=[.003+.020*math.sin(math.pi*i/32)**.65 if top else .006 for i in range(33)]
        g.sweep(name+('_upper_lash' if top else '_lower_skin_lid'),pts,widths,[w*.55 for w in widths],
                'sv_lash' if top else 'sv_skin','head',normal=n,steps=88,sides=20)
    x=sign*width*.465
    g.sweep(name+'_soft_lash_wing',[surface(x,.026,.012),surface(x+sign*.045,.061,.011),surface(x+sign*.085,.096,.004)],
            [.013,.022,.0004],[.008,.012,.0004],'sv_lash','head',normal=n,steps=36,sides=20)
    for suffix,x,z,rx,rz in [('light',-.052,.101,.030,.036),('pin',.068,-.108,.010,.014)]:
        t2=(x/(width*.5))**2+(z/(height*.5))**2
        g.disk(name+'_'+suffix,surface(x,z,.029*(1-t2)+.006),u,v,n,rx,rz,'sv_white','head',bulge=.001,rings=8,seg=48)
    lidverts=[]
    for p in verts:
        d=p-c;lidverts.append(c+u*d.dot(u)*1.075+v*d.dot(v)*1.065+n*(d.dot(n)+.031))
    lid=g.mesh(name+'_closed_lid',lidverts,faces,'sv_skin','lid.'+side);lid['ast_lid_pivot']=list(c+n*.031)
    pts=[surface(width*.46*q,-height*.08*(1-q*q),.029*(1-q*q)+.036) for q in (-1,-.75,-.5,-.25,0,.25,.5,.75,1)]
    lash=g.sweep(name+'_closed_lash',pts,[.001,.007,.009,.007,.001],[.001,.004,.005,.004,.001],
                 'sv_lash','lid.'+side,normal=n,steps=60,sides=16);lash['ast_lid_pivot']=list(c+n*.031)


def hair_lock(g,name,points,width,depth,normal=(0,-1,0),steps=88,sides=48,tone=0):
    """One scored S-wave with smooth curvature and a globally tapered volume."""
    centers=spline(points,steps);previous=Vector(normal).normalized();frames=[];radii=[]
    for i,c in enumerate(centers):
        t=i/steps;T=(centers[min(steps,i+1)]-centers[max(0,i-1)]).normalized()
        n=previous-T*previous.dot(T)
        if n.length<.0001:
            axis=Vector((0,0,1)) if abs(T.z)<.9 else Vector((0,1,0));n=axis-T*axis.dot(T)
        n.normalize();previous=n;frames.append((T,T.cross(n).normalized(),n))
        radii.append(.0018+math.sqrt(1-math.exp(-26*t))*max(0,1-t**3.7)**1.25)
    maximum=0.
    for i in range(1,steps):
        a=centers[i]-centers[i-1];b=centers[i+1]-centers[i];den=a.length*b.length*(a+b).length
        bend=b.normalized()-a.normalized()
        if den>1e-12 and bend.length>1e-7:
            bend.normalize();_,u,n=frames[i]
            support=math.sqrt((width*u.dot(bend))**2+(depth*n.dot(bend))**2)
            maximum=max(maximum,2*a.cross(b).length/den*support*radii[i])
    gain=min(1,.66/maximum) if maximum else 1.
    dark=g.color('682B30');base=g.color('B74D3E');light=g.color('E49762');gold=g.color('E9BE72')
    vs=[];fs=[];values=[]
    for i,c in enumerate(centers):
        t=i/steps;_,u,n=frames[i];r=radii[i]*gain
        for j in range(sides):
            a=TAU*j/sides;out=math.sin(a);across=math.cos(a)
            phase=a+.14*math.sin(t*4)
            channel=(.5+.5*math.cos(9*phase+.20*t))**8
            sculpt=1.+.055*math.cos(3*phase)-.095*channel*math.sin(math.pi*t)+.009*math.cos(21*phase)
            p=c+u*(width*r*across*sculpt)+n*(depth*r*out*sculpt);vs.append(p)
            face=max(0,out)
            col=mix(dark,base,.57+.34*face+tone)
            band=math.exp(-((across-.23-.08*math.sin(t*4.8))/.39)**2)*face**1.3
            col=mix(col,light,.13*face+.32*band)
            col=mix(col,gold,.22*band*math.sin(math.pi*t)**2)
            col=mix(col,dark,.20*channel)
            values.append(col[:3]+(1.,))
    for i in range(steps):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides;fs.append((a,a+sides,b+sides,b))
    root=len(vs);vs.append(centers[0]);values.append(values[0]);tip=len(vs);vs.append(centers[-1]);values.append(values[-2])
    for j in range(sides):
        fs.extend(((root,j,(j+1)%sides),(tip,steps*sides+(j+1)%sides,steps*sides+j)))
    obj=g.mesh('Selya_'+name,vs,fs,'sv_hair','head');paint(obj,values)
    obj['continuous_hair_gain']=gain
    return obj


def hair(g):
    def smooth(t):
        t=max(0.,min(1.,t));return t*t*(3-2*t)
    def foundation(t,a):
        # One continuous surface runs from the crown through the hanging back.
        # There is no sphere/lock intersection or horizontal cap termination.
        front=max(0.,-math.sin(a));back=1-front**.65
        theta=t*(2.05*(1-front**.7)+1.00*front**.7)
        grow=smooth((t-.34)/.66)*back
        wave=.050*math.sin(a*5.0+t*5.4)*grow+.020*math.sin(a*11-t*3)*math.sin(math.pi*t)
        radius=.70+.11*grow+wave
        p=Vector((radius*math.sin(theta)*math.cos(a),
                  .12+(.53+.18*grow)*math.sin(theta)*math.sin(a)+.10*grow,
                  3.42+.696*math.cos(theta)-(.82+.25*max(0.,math.sin(a)))*grow))
        n=Vector((math.sin(theta)*math.cos(a),math.sin(theta)*math.sin(a),max(0.,math.cos(theta)))).normalized()
        channel=(.5+.5*math.cos(45*a+t*8+.7*math.sin(t*4)))**8
        p+=n*(.009*math.sin(math.pi*t)-.012*channel*math.sin(math.pi*t)**.5)
        return p,n
    rows=80;seg=176;vs=[];fs=[];values=[]
    for inner in (False,True):
        for i in range(1,rows+1):
            t=i/rows
            for j in range(seg):
                a=TAU*j/seg;p,n=foundation(t,a)
                vs.append(p-n*(.035 if inner else 0))
                stripe=.5+.5*math.cos(a*9+t*6+.4*math.sin(t*5))
                col=mix(g.color('7E3333'),g.color('B64C3E'),.56+.22*stripe)
                col=mix(col,g.color('DC9566'),.16*stripe)
                values.append(col[:3]+(1.,))
    offset=rows*seg
    for i in range(rows-1):
        for j in range(seg):
            a=i*seg+j;b=i*seg+(j+1)%seg
            fs.extend(((a,b,b+seg,a+seg),(a+offset,a+seg+offset,b+seg+offset,b+offset)))
    pole=len(vs);vs.append(Vector((0,.12,4.116)));values.append(g.color('B64C3E'))
    innerpole=len(vs);vs.append(Vector((0,.12,4.081)));values.append(g.color('B64C3E'))
    for j in range(seg):
        nxt=(j+1)%seg;a=(rows-1)*seg+j;b=(rows-1)*seg+nxt
        fs.extend(((pole,nxt,j),(innerpole,offset+j,offset+nxt),(a,b,b+offset,a+offset)))
    cap=g.mesh('Selya_continuous_crown_and_flowing_underhair',vs,fs,'sv_hair','head');paint(cap,values)
    # Broad overlapping waves follow the foundation from the crown, then
    # diverge only in their tapered final quarter. The lengths are not pipes.
    for j in range(9):
        a=.025+math.pi*.985*j/8;pts=[]
        for k in range(17):
            t=.035+.965*k/16
            aa=a+.105*math.sin(t*6+j*.65)*smooth(t/.30)
            p,n=foundation(t,aa)
            p+=n*(-.010+(.075+.012*math.sin(t*5+j))*smooth(t/.22))
            if t>.78:
                curl=smooth((t-.78)/.22)
                p+=Vector((.10*math.cos(a+.45)*curl,.06*math.sin(a)*curl,.095*curl))
            pts.append(p)
        hair_lock(g,'overlapping_crown_wave_%02d'%j,pts,.194+.028*math.sin(j*.9),.080,
                  normal=(math.cos(a),math.sin(a),.25),tone=-.005,steps=100,sides=48)
    for s,side in ((-1,'R'),(1,'L')):
        for j in range(2):
            points=[(s*(.30+j*.07),-.17,4.015-j*.03),(s*(.57+j*.06),-.35,3.72-j*.055),
                    (s*(.67+j*.05),-.36,3.36-j*.08),(s*(.61+j*.065),-.41,3.02-j*.12),
                    (s*(.56+j*.11),-.45,2.82-j*.13),(s*(.78+j*.08),-.34,2.66-j*.17),
                    (s*(.86+j*.10),-.17,2.81-j*.17)]
            hair_lock(g,'flowing_face_wave_'+side+str(j),points,.132-j*.009,.072-j*.003,tone=.025)
        for j in range(2):
            hair_lock(g,'integrated_lower_curl_'+side+str(j),
                [(s*.57,.31,3.11-j*.35),(s*.74,.44,2.85-j*.28),
                 (s*.77,.55,2.57-j*.29),(s*.95,.50,2.36-j*.22),
                 (s*1.09,.33,2.51-j*.15)],.143,.072,
                normal=(s,.35,.1),steps=80,sides=44,tone=-.02)
    hair_lock(g,'scalp_fitted_swept_fringe',[(.17,-.22,4.005),(-.05,-.39,3.961),
              (-.29,-.51,3.76),(-.48,-.52,3.49),(-.54,-.43,3.29)],.129,.071,tone=.025)
    hair_lock(g,'golden_fringe_inset',[(.12,-.20,4.019),(-.13,-.40,3.92),
              (-.41,-.49,3.68),(-.58,-.39,3.44),(-.60,-.27,3.38)],.085,.045,tone=.10)
    hair_lock(g,'scalp_fitted_right_parting',[(.08,-.20,4.016),(.31,-.40,3.966),
              (.53,-.44,3.78),(.65,-.30,3.59),(.68,-.13,3.57)],.128,.067,tone=.02)
    bun=g.uv('Selya_topknot_core',(.22,.17,4.095),(.258,.232,.315),'sv_hair','head',seg=72,rings=48)
    paint(bun,[g.color('B95542')]*len(bun.data.vertices))
    for j in range(5):
        angle=TAU*j/5
        pts=[]
        for k in range(6):
            t=k/5;a=angle+t*2.1;radius=math.sin(math.pi*(.13+t*.76))
            pts.append((.22+.255*math.cos(a)*radius,.17+.23*math.sin(a)*radius,3.88+.51*t))
        hair_lock(g,'wrapped_topknot_'+str(j),pts,.090,.053,normal=(math.cos(angle),math.sin(angle),.1),steps=64,sides=40,tone=.04)
    ring(g,'topknot_collar',(.22,.17),.236,.214,3.907,'head',.024)


def anatomy(g):
    torso=g.fuse('Selya_continuous_torso',[
        g.uv('Selya_ribcage',(0,.005,2.145),(.365,.255,.46),'sv_skin'),
        g.uv('Selya_waist',(0,.018,1.90),(.31,.225,.27),'sv_skin'),
        g.uv('Selya_pelvis',(0,.035,1.735),(.385,.264,.27),'sv_skin')],voxel=.026,subdiv=1)
    g.uv('Selya_neck',(0,0,2.62),(.158,.15,.23),'sv_skin','neck',seg=64,rings=40)
    head=g.fuse('Selya_sculpted_head',[
        g.uv('Selya_cranium',(0,.018,3.315),(.641,.492,.644),'sv_skin','head'),
        g.uv('Selya_cheek_plane',(0,-.135,3.155),(.563,.372,.30),'sv_skin','head'),
        g.uv('Selya_lower_face',(0,-.092,3.01),(.455,.360,.270),'sv_skin','head'),
        g.uv('Selya_soft_chin',(0,-.10,2.916),(.300,.285,.125),'sv_skin','head'),
        g.uv('Selya_nose_bridge',(0,-.489,3.119),(.061,.068,.104),'sv_skin','head'),
        g.uv('Selya_nose_tip',(0,-.548,3.069),(.064,.055,.050),'sv_skin','head')],
        'head',voxel=.016,subdiv=1)
    for s in (-1,1):
        side='L' if s>0 else 'R';eye(g,head,s)
        # Closed pointed ear with an inset concha and a visibly thick helix.
        pts=[(s*.55,-.012,3.185),(s*.73,-.06,3.25),(s*.91,-.015,3.41),(s*.985,.020,3.475)]
        petal(g,'sculpted_ear_'+side,pts,.139,'skin','head',bulge=.046,steps=64,cols=32,veins=0,trim=False)
        inset=[(s*.62,-.066,3.228),(s*.73,-.091,3.273),(s*.88,-.05,3.392),(s*.929,-.020,3.431)]
        inner=petal(g,'ear_concha_'+side,inset,.065,'skin','head',bulge=.008,steps=48,cols=24,veins=0,trim=False)
        inner['selya_inner_ear']=True
        part='leg.'+side
        pieces=[g.uv('Selya_thigh_'+side,(s*.223,.025,1.12),(.190,.183,.418),'sv_skin',part,seg=64,rings=40),
                g.uv('Selya_calf_'+side,(s*.249,.012,.618),(.142,.15,.34),'sv_skin',part,seg=64,rings=40),
                g.uv('Selya_foot_'+side,(s*.25,-.082,.177),(.148,.222,.126),'sv_skin',part,seg=56,rings=36)]
        leg=g.fuse('Selya_anatomical_leg_'+side,pieces,part,voxel=.018,subdiv=1)
        # Toe pads remain individually editable. Voxel fusion previously
        # swallowed the shallow pads into one smooth slipper-shaped foot.
        for j in range(4):
            x=s*.25+(j-1.5)*.058;y=-.294-.012*(1-abs(j-1.4)/2)
            g.uv('Selya_distinct_toe_'+side+str(j),(x,y,.137),
                 (.032,.080-.007*abs(j-1.4),.045),'sv_skin',part,seg=40,rings=24)
        part='arm.'+side
        parts=[g.sweep('Selya_arm_'+side,[(s*.335,0,2.355),(s*.49,-.003,2.19),
               (s*.665,-.04,1.953),(s*.90,-.065,1.722)],
               [.139,.135,.098,.068],[.133,.123,.092,.064],'sv_skin',part,normal=(0,-1,0),steps=100,sides=56),
               g.uv('Selya_palm_'+side,(s*.974,-.086,1.658),(.115,.073,.085),'sv_skin',part,seg=56,rings=32)]
        for j in range(4):
            y=-.132+j*.036;z=1.67+(j-1.5)*.027;end=1.195-.020*abs(j-1.3)
            parts.append(g.sweep('Selya_finger_'+side+str(j),[(s*1.014,y,z),(s*1.108,y-.021,z-.006),
                         (s*end,y-.041,z-.022)],[.027,.024,.009],[.023,.018,.008],
                         'sv_skin',part,normal=(0,-1,0),steps=30,sides=20))
        parts.append(g.sweep('Selya_thumb_'+side,[(s*.944,-.12,1.66),(s*.982,-.18,1.572),(s*1.045,-.197,1.555)],
                     [.035,.027,.009],[.028,.022,.008],'sv_skin',part,normal=(0,-1,0),steps=34,sides=24))
        g.fuse('Selya_anatomical_arm_hand_'+side,parts,part,voxel=.0145,subdiv=1)
    bvh=tree(head)
    def front(x,z,offset=.005):
        p,_,_,_=bvh.ray_cast(Vector((x,-3,z)),Vector((0,1,0)))
        if p is None:raise ValueError('Missing Selya expression landmark')
        return p+Vector((0,-offset,0))
    for s in (-1,1):
        pts=[front(s*x,z,.005) for x,z in ((.13,3.601),(.24,3.633),(.35,3.629),(.46,3.587))]
        g.sweep('Selya_arched_brow_'+str(s),pts,[.002,.022,.024,.001],[.002,.012,.012,.001],
                'sv_brow','head',normal=(0,-1,0),steps=60,sides=20)
        pts=[front(s*x,z,.005) for x,z in ((0,2.955),(.047,2.950),(.106,2.962),(.16,2.998))]
        g.sweep('Selya_smile_'+str(s),pts,[.003,.005,.005,.001],[.002,.003,.003,.001],'sv_lip','head',normal=(0,-1,0),steps=40,sides=16)
        g.uv('Selya_nostril_'+str(s),front(s*.036,3.050,.002),(.010,.003,.006),'sv_skin_shadow','head',seg=24,rings=14)
    return head


def flower(g,name,c,normal,r,part,petals=7,gold_only=False):
    c=Vector(c);n=Vector(normal).normalized();u=Vector((1,0,0))-n*n.x;u.normalize();v=n.cross(u).normalized()
    for j in range(petals):
        a=TAU*j/petals+.20;d=u*math.cos(a)+v*math.sin(a)
        points=[c,c+d*r*.45+n*.016,c+d*r*.90+n*.028,c+d*r*1.12]
        petal(g,name+'_petal_'+str(j),points,r*.31,'gold' if gold_only else 'coral',part,
              normal=n,steps=32,cols=16,veins=0 if gold_only else 1,bulge=.012,trim=not gold_only)
    if not gold_only:
        for j in range(4):
            a=TAU*(j+.25)/4;d=u*math.cos(a)+v*math.sin(a)
            petal(g,name+'_sage_leaf_'+str(j),[c-n*.018,c+d*r*.55-n*.013,c+d*r*1.16-n*.007,c+d*r*1.35],
                  r*.19,'mint',part,normal=n,steps=30,cols=16,veins=1,bulge=.010)
    gem(g,name+'_center',c+n*.039,n,r*.31,part)


def axis_ring(g,name,c,axis,radius,part,tube=.018):
    c=Vector(c);n=Vector(axis).normalized();u=Vector((0,1,0))-n*n.y;u.normalize();v=n.cross(u).normalized()
    pts=[c+(u*math.cos(TAU*j/32)+v*math.sin(TAU*j/32))*radius for j in range(33)]
    return g.line('Selya_'+name,pts,tube,'sv_gold',part,resolution=3)


def fitted_sandal_strap(g,side,sign,y,span,index):
    leg=next(o for o in g.ASSET if o.name=='AST_Selya_anatomical_leg_'+side)
    bvh=tree(leg);vs=[];fs=[];rows=36
    for below in (False,True):
        for i in range(rows+1):
            x=sign*.25-span+2*span*i/rows
            for edge in (-1,1):
                yy=y+edge*.019
                hit,n,_,_=bvh.ray_cast(Vector((x,yy,.47)),Vector((0,0,-1)))
                if hit is None:hit,n,_,_=bvh.find_nearest(Vector((x,yy,.16)))
                if hit is None:raise ValueError('Unfitted Selya sandal strap')
                vs.append(hit+n*(.004 if below else .014))
    offset=2*(rows+1)
    for i in range(rows):
        a=i*2;b=a+2
        fs.extend(((a,a+1,b+1,b),(a+offset,b+offset,b+1+offset,a+1+offset),
                   (a,b,b+offset,a+offset),(a+1,a+1+offset,b+1+offset,b+1)))
    fs.extend(((0,offset,offset+1,1),(2*rows,2*rows+1,2*rows+1+offset,2*rows+offset)))
    return g.mesh('Selya_surface_fitted_sandal_strap_'+side+str(index),vs,fs,'sv_gold','leg.'+side)


def wardrobe(g):
    bodice=g.uv('Selya_fitted_mint_bodice',(0,.005,2.171),(.377,.274,.340),'sv_mint','body',seg=72,rings=48)
    values=[]
    for vertex in bodice.data.vertices:
        p=bodice.matrix_world@vertex.co
        grain=noise(Vector((p.x*24,p.y*24,p.z*24)))
        values.append(mix(g.color('597D67'),g.color('9CB79A'),.49+.10*grain)[:3]+(1.,))
    paint(bodice,values)
    for s in (-1,1):
        petal(g,'coral_bodice_'+str(s),[(s*.048,-.292,1.926),(s*.183,-.310,2.145),
              (s*.256,-.275,2.408),(s*.323,-.178,2.473)],.146,'coral','body',
              normal=(0,-1,0),bulge=.031,steps=56,cols=24,veins=5)
        petal(g,'ivory_neckline_'+str(s),[(s*.063,-.303,2.04),(s*.150,-.324,2.249),
              (s*.28,-.219,2.462),(s*.341,-.153,2.465)],.064,'ivory','body',
              normal=(0,-1,0),bulge=.012,steps=44,cols=20,veins=2)
    ring(g,'fitted_waist_belt',(0,.014),.386,.277,1.925,'body',.031)
    gem(g,'heart_waist_emerald',(0,-.337,1.926),(0,-1,0),.160,'body')
    for j in range(5):
        a=math.pi+TAU*(j-2)/9;d=Vector((math.sin(a),0,math.cos(a)))
        c=Vector((0,-.313,1.920))
        petal(g,'waist_gold_calyx_'+str(j),[c,c+d*.15+Vector((0,-.012,0)),
              c+d*.24,c+d*.29],.044,'gold','body',normal=(0,-1,0),
              bulge=.012,steps=32,cols=16,veins=0,trim=False)
    ring(g,'neck_choker',(0,0),.175,.161,2.586,'neck',.021)
    gem(g,'throat_emerald',(0,-.206,2.565),(0,-1,.02),.089,'neck')
    for s in (-1,1):
        for j in range(2):
            c=Vector((s*.055,-.183,2.591));end=Vector((s*(.22+j*.06),-.104,2.65+j*.020))
            petal(g,'collar_leaf_'+str(s)+'_'+str(j),[c,c.lerp(end,.35)+Vector((0,-.02,0)),
                  c.lerp(end,.79),end],.040,'gold','neck',normal=(0,-1,.25),
                  steps=32,cols=16,veins=0,trim=False,bulge=.009)
    # A flaring asymmetric botanical skirt, not uniform straight petal columns.
    tiers=[(10,1.845,.64,1.015,'mint'),(9,1.90,.86,1.025,'ivory'),(8,1.948,1.08,.996,'coral')]
    for layer,(count,top,bottom,radius,mat) in enumerate(tiers):
        for j in range(count):
            a=TAU*(j+.37*(layer%2))/count;d=Vector((math.sin(a),math.cos(a),0))
            side=abs(d.x);curl=.23*side+.035*math.sin(j*2.7+layer)
            r=radius*(.96+.05*math.sin(j*1.73+layer))
            start=d*.235+Vector((0,.015,top))
            end=d*r+Vector((0,.01,bottom+curl))
            pts=[start,d*.455+Vector((0,.015,top-.17)),
                 d*(r*.87)+Vector((0,.01,bottom-.02)),end]
            petal(g,'dress_tier_%d_petal_%02d'%(layer,j),pts,.252 if layer!=2 else .281,
                  mat,'body',normal=tuple(d),bulge=.032,steps=58,cols=24,
                  veins=4 if layer==2 else 3)
    # Central elongated overlapping petals echo the illustrated front motif.
    petal(g,'front_mint_heart',[(0,-.286,1.87),(0,-.52,1.66),(0,-.75,1.31),(0,-.845,1.19)],
          .132,'mint','body',normal=(0,-1,0),steps=52,cols=24,veins=4)
    petal(g,'front_coral_drop',[(0,-.303,1.72),(0,-.57,1.46),(0,-.80,1.10),(0,-.858,.995)],
          .158,'coral','body',normal=(0,-1,0),steps=52,cols=24,veins=4)
    # Four real, two-sided pearly membranes. Their smaller branches share the
    # actual curved surface on both sides, rather than floating in a flat plane.
    for s in (-1,1):
        side='L' if s>0 else 'R';part='wing.'+side
        petal(g,'upper_wing_'+side,[(s*.225,.275,2.42),(s*.75,.40,2.89),
              (s*1.68,.59,3.48),(s*1.96,.56,3.40)],.338,'wing',part,
              normal=(0,-1,.12),bulge=.038,steps=80,cols=32,veins=9,wing=True)
        petal(g,'lower_wing_'+side,[(s*.24,.282,2.38),(s*.63,.43,2.52),
              (s*1.41,.57,2.37),(s*1.59,.50,2.16)],.255,'wing',part,
              normal=(0,-1,.17),bulge=.029,steps=76,cols=30,veins=7,wing=True)
        # Flower at the wing/upper-arm junction, with small solid leaf petals.
        flower(g,'shoulder_blossom_'+side,(s*.465,-.062,2.245),(s*.17,-.985,0),.139,'arm.'+side,petals=5)
    for s in (-1,1):
        side='L' if s>0 else 'R';part='arm.'+side
        axis=Vector((s*.57,-.05,-.65))
        axis_ring(g,'wrist_cuff_'+side,(s*.833,-.061,1.807),axis,.081,part,.021)
        for j in range(3):
            root=Vector((s*.831,-.140,1.829));end=root+Vector((s*(.005+(j-1)*.098),.014,.217-.050*abs(j-1)))
            petal(g,'wrist_leaf_'+side+str(j),[root,root.lerp(end,.36)+Vector((0,-.024,0)),
                  root.lerp(end,.80),end],.055,'coral' if j==1 else 'gold',part,
                  normal=(0,-1,0),steps=40,cols=20,veins=1 if j==1 else 0,trim=j==1,bulge=.015)
        part='leg.'+side
        sole=g.uv('Selya_sandal_sole_'+side,(s*.25,-.122,.064),(.163,.281,.048),'sv_gold_dark',part,seg=80,rings=32)
        ring(g,'ankle_band_'+side,(s*.249,.012),.151,.159,.406,part,.021)
        fitted_sandal_strap(g,side,s,-.235,.110,0)
        fitted_sandal_strap(g,side,s,-.172,.133,1)
        gem(g,'ankle_emerald_'+side,(s*.249,-.170,.413),(0,-1,0),.063,part)
        for j in range(3):
            c=Vector((s*.249,-.161,.420));end=c+Vector(((j-1)*.121,.027,.221-.045*abs(j-1)))
            petal(g,'ankle_flower_'+side+str(j),[c,c.lerp(end,.32)+Vector((0,-.014,0)),
                  c.lerp(end,.83),end],.065,'coral',part,normal=(0,-1,0),
                  steps=40,cols=20,veins=1,bulge=.018)
    flower(g,'coral_hair_blossom',(.591,-.319,3.846),(.26,-.964,.045),.232,'head',petals=7)
    for s in (-1,1):
        side='L' if s>0 else 'R'
        flower(g,'sun_drop_earring_'+side,(s*.669,-.124,3.078),(s*.10,-.99,0),.105,'head',petals=7,gold_only=True)


def build(g):
    palette(g)
    print('SELYA sculpting anatomy and recessed eyes',flush=True)
    anatomy(g)
    print('SELYA continuous scored hair and crown',flush=True)
    hair(g)
    print('SELYA botanical dress, wing membranes and gold fittings',flush=True)
    wardrobe(g)
    # Paint after socket Booleans so every generated orbital vertex is colored.
    for obj in g.ASSET:
        if obj.type=='MESH' and obj.data.materials and obj.data.materials[0]==g.M['sv_skin']:
            colors=[]
            for vertex in obj.data.vertices:
                col=skin_color(g,obj.matrix_world@vertex.co)
                if obj.get('selya_inner_ear'):col=mix(col,g.color('A76A38'),.33)
                colors.append(col)
            paint(obj,colors)
    # The shared bright studio intentionally overexposes light pigments. Keep
    # the authored linear colors rich in source and exported vertex colors.
    pigment_factors={'sv_skin':.78,'sv_hair':.76,'sv_coral':.75,'sv_ivory':.88,'sv_mint':.88}
    for obj in g.ASSET:
        if obj.type!='MESH' or not obj.data.materials:continue
        attr=obj.data.color_attributes.get('AST_eye_color')
        if attr is None:continue
        factor=next((v for k,v in pigment_factors.items() if obj.data.materials[0]==g.M[k]),1.)
        if factor==1:continue
        colors=[]
        for entry in attr.data:
            c=entry.color;colors.append((c[0]*factor,c[1]*factor,c[2]*factor,c[3]))
        paint(obj,colors)
    return {'name':'Selya','kind':'fairy','family':'biped','bones':[
        ('body',(0,.02,1.55),(0,.02,2.37),None),
        ('neck',(0,0,2.39),(0,0,2.77),'body'),('head',(0,0,2.77),(0,0,3.89),'neck'),
        ('arm.L',(.335,0,2.355),(.974,-.086,1.658),'body'),
        ('arm.R',(-.335,0,2.355),(-.974,-.086,1.658),'body'),
        ('leg.L',(.223,.025,1.48),(.249,.012,.22),'body'),
        ('leg.R',(-.223,.025,1.48),(-.249,.012,.22),'body'),
        ('wing.L',(.235,.28,2.40),(1.43,.5,2.99),'body'),
        ('wing.R',(-.235,.28,2.40),(-1.43,.5,2.99),'body')],
        'notes':['Reference-led v002: warmer sculpted face, smaller teal almond eyes with continuous orbital skin, fitted lids, blush and shaped hands/feet.',
                 'Continuous scored coral/gold S-locks and fitted scalp/bun replace the parallel hair slabs and cap seam.',
                 'Four thick pearly wing membranes carry modeled fine gold branches on both surfaces; flared coral, ivory and sage petals have real curved gold edges.',
                 'Original fairy.png remains unchanged. Rear anatomy and concealed garment structure are inferred; no exact likeness or mobile-performance acceptance is claimed.']}

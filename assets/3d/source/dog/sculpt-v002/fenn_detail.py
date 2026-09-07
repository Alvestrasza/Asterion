"""Local sculpt tools for a reference-led quadruped; no image projection."""
import math

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.noise import noise


def mix(a,b,t):
    t=max(0.,min(1.,t))
    return tuple(x+(y-x)*t for x,y in zip(a,b))


def smooth(t):
    t=max(0.,min(1.,t))
    return t*t*(3-2*t)


def path(points,count):
    points=list(map(Vector,points));n=len(points)-1;degree=min(3,n)
    knots=[0.]*(degree+1)+[i/(n-degree+1) for i in range(1,n-degree+1)]+[1.]*(degree+1)
    result=[]
    for sample in range(count+1):
        t=sample/count
        span=n if sample==count else next(i for i in range(degree,n+1) if knots[i]<=t<knots[i+1])
        d=[points[span-degree+j].copy() for j in range(degree+1)]
        for r in range(1,degree+1):
            for j in range(degree,r-1,-1):
                a,b=knots[j+span-degree],knots[j+1+span-r]
                f=(t-a)/(b-a) if b>a else 0
                d[j]=d[j-1]*(1-f)+d[j]*f
        result.append(d[degree])
    return result


class Surface:
    """Immutable clean support: capture before fine skin displacement."""
    def __init__(self,obj):
        self.tree=BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                                     [tuple(p.vertices) for p in obj.data.polygons])

    def contact(self,p,n,offset=.008):
        p,n=Vector(p),Vector(n).normalized()
        hit,normal,_,_=self.tree.ray_cast(p+n*1.8,-n,3.6)
        if hit is None:
            hit,normal,_,distance=self.tree.find_nearest(p)
            if hit is None or distance>.30:raise ValueError('Missing local sculpt support')
        if normal.dot(n)<0:normal=-normal
        return hit+normal*offset,normal

    def outward(self,origin,n,offset=.008,limit=.9):
        n=Vector(n).normalized()
        hit,normal,_,_=self.tree.ray_cast(Vector(origin),n,limit)
        if hit is None:raise ValueError('Interior support ray misses local skin')
        if normal.dot(n)<0:normal=-normal
        return hit+normal*offset,normal


class Art:
    def __init__(self,g,prefix,colors):
        self.g,self.prefix=g,prefix
        self.keys={}
        for name,(hexcolor,metal,rough) in colors.items():
            key=prefix+'_'+name;self.keys[name]=key
            g.M[key]=g.material(key,hexcolor,metal,rough)
        key=prefix+'_painted_coat';self.keys['paint']=key
        mat=g.material(key,'FFFFFF',0,.67)
        shader=mat.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Specular IOR Level'].default_value=.20
        attr=mat.node_tree.nodes.new('ShaderNodeVertexColor');attr.layer_name='AST_eye_color'
        mat.node_tree.links.new(attr.outputs['Color'],shader.inputs['Base Color']);g.M[key]=mat

    def mesh(self,name,verts,faces,mat='coat',part='body',smooth_faces=True):
        obj=self.g.mesh(self.prefix+'_'+name,verts,faces,self.keys.get(mat,mat),part,smooth_faces)
        bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bm.to_mesh(obj.data);bm.free();obj.data.update()
        return obj

    def uv(self,name,p,r,mat='coat',part='body',seg=56,rings=36):
        return self.g.uv(self.prefix+'_'+name,p,r,self.keys[mat],part,seg=seg,rings=rings)

    def fuse(self,name,parts,part='body',voxel=.019,subdiv=1):
        return self.g.fuse(self.prefix+'_'+name,parts,part,voxel=voxel,subdiv=subdiv)

    def colors(self,obj,values):
        attr=obj.data.color_attributes.get('AST_eye_color') or obj.data.color_attributes.new(
            name='AST_eye_color',type='FLOAT_COLOR',domain='POINT')
        attr.data.foreach_set('color',[x for color in values for x in color])

    def paint(self,obj,palette,relief=.0015,palette_at=None):
        matrix=obj.matrix_world.copy();inverse=matrix.inverted()
        normal_matrix=matrix.to_3x3().inverted().transposed()
        positions=[matrix@v.co for v in obj.data.vertices]
        normals=[(normal_matrix@v.normal).normalized() for v in obj.data.vertices]
        colors=[]
        def ridges(u,v):
            u+=.14*math.sin(v*1.73)+.09*math.sin(v*3.19+u*.64)
            v+=.12*math.sin(u*1.17)+.055*math.sin(u*3.7)
            row=math.floor(v);u+=.5*(row%2);column=math.floor(u)
            t=v-row;q=u-column-.5;seed=math.sin(column*19.17+row*33.41)
            q+=.065*math.sin(math.pi*t)*seed;width=(.42+.033*seed)*(.72+.28*math.sin(math.pi*t))
            ridge=max(0,1-(q/width)**2)**1.65*math.sin(math.pi*t)**.72
            return ridge*(1-.13*math.exp(-(q/.04)**2))
        for vertex,p,n in zip(obj.data.vertices,positions,normals):
            warp=noise(p*7)*1.5
            fiber=noise(Vector((p.x*77+warp,p.y*68,p.z*19)))*1.6
            dorsal=noise(Vector((p.x*68,p.y*16+warp,p.z*78)))*1.6
            fiber=fiber*(1-abs(n.z)**4)+dorsal*abs(n.z)**4
            fine=noise(Vector((p.x*133,p.y*149,p.z*53)))*.20
            f=max(0,min(1,.5+.55*(fiber+fine)))
            wx,wy,wz=(abs(n.x)**6,abs(n.y)**6,abs(n.z)**6);total=wx+wy+wz
            fur=(wx*ridges(p.y*18,p.z*13+p.y*3)+wy*ridges(p.x*21,p.z*16)+wz*ridges(p.x*21,p.y*14))/total
            vertex.co=inverse@(p+n*relief*fur)
            pal=palette_at(p) if palette_at else palette
            color=mix(pal[0],pal[2],.55+.075*f)
            color=mix(color,pal[3],.015*f)
            colors.append(color[:3]+(1,))
        obj.data.materials.clear();obj.data.materials.append(self.g.M[self.keys['paint']])
        for polygon in obj.data.polygons:polygon.material_index=0;polygon.use_smooth=True
        self.colors(obj,colors);obj.data.update()
        obj['sculpt_detail']='Directional, non-periodic short fur geometry and authored vertex color'

    def lock(self,name,points,width,depth,palette,part='head',normal=(0,-1,0),steps=64,sides=44,root_palette=None):
        centers=path(points,steps);previous=Vector(normal).normalized();frames=[]
        profile=[]
        for i,c in enumerate(centers):
            t=i/steps;tangent=(centers[min(steps,i+1)]-centers[max(0,i-1)]).normalized()
            n=previous-tangent*previous.dot(tangent)
            if n.length<1.e-6:
                alternate=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((0,1,0))
                n=alternate-tangent*alternate.dot(tangent)
            n.normalize();previous=n;frames.append((tangent,tangent.cross(n).normalized(),n))
            profile.append(.0015+math.sqrt(1-math.exp(-24*t))*max(0,1-t**2.7)**1.35)
        maximum=0
        for i in range(1,steps):
            a,b=centers[i]-centers[i-1],centers[i+1]-centers[i]
            den=a.length*b.length*(a+b).length
            if den>1.e-12:
                k=2*a.cross(b).length/den;bend=b.normalized()-a.normalized()
                if bend.length>1.e-7:
                    bend.normalize();_,u,n=frames[i]
                    maximum=max(maximum,k*math.sqrt((width*u.dot(bend))**2+(depth*n.dot(bend))**2)*profile[i])
        gain=min(1,.68/maximum) if maximum else 1
        verts,faces,colors=[],[],[]
        for i,c in enumerate(centers):
            t=i/steps;_,u,n=frames[i];radius=profile[i]*gain;fade=math.sin(math.pi*t)**.65
            for j in range(sides):
                a=math.tau*j/sides;outward=math.sin(a);lateral=math.cos(a)
                groove=(.5+.5*math.cos(9*a+.45*math.sin(t*3)))**10
                sculpt=1+fade*(.036*math.cos(3*a)-.058*groove+.009*math.cos(19*a+t*2))
                verts.append(c+u*(width*radius*lateral*sculpt)+n*(depth*radius*outward*sculpt))
                light=max(0,outward);color=mix(palette[0],palette[2],.55+.15*light)
                stripe=math.exp(-((lateral-.22)/.4)**2)*light**2*fade
                color=mix(color,palette[3],.10*stripe);color=mix(color,palette[0],.08*groove*fade)
                if root_palette is not None:
                    color=mix(mix(root_palette[0],root_palette[2],.61),color,smooth(t/.66))
                colors.append(color[:3]+(1,))
        for i in range(steps):
            for j in range(sides):
                a=i*sides+j;b=i*sides+(j+1)%sides;faces.append((a,a+sides,b+sides,b))
        root=len(verts);verts.append(centers[0]);colors.append(colors[0])
        tip=len(verts);verts.append(centers[-1]);colors.append(colors[-2])
        for j in range(sides):
            k=(j+1)%sides;faces += [(root,j,k),(tip,steps*sides+k,steps*sides+j)]
        obj=self.mesh(name,verts,faces,'paint',part);self.colors(obj,colors)
        obj['safe_curvature_gain']=gain
        return obj

    def weights(self,obj):
        groups={key:obj.vertex_groups.new(name=key) for key in ('body','neck','leg.FL','leg.FR','leg.HL','leg.HR')}
        for vertex in obj.data.vertices:
            p=obj.matrix_world@vertex.co;neck=smooth((p.z-1.62)/.48)
            limb=smooth((1.42-p.z)/.55)*smooth((abs(p.x)-.13)/.16)
            key='leg.'+('F' if p.y<.10 else 'H')+('L' if p.x>0 else 'R')
            for name,weight in [('neck',neck),('body',(1-neck)*(1-limb)),(key,(1-neck)*limb)]:
                if weight>1.e-8:groups[name].add([vertex.index],weight,'REPLACE')

    def ribbon(self,name,points,normals,width,part='body',closed=False,mat='metal',height_scale=1):
        points=list(map(Vector,points));normals=list(map(Vector,normals));verts=[];faces=[]
        profile=[(-.5,-.004),(-.5,.008),(-.36,.022),(.36,.022),(.5,.008),(.5,-.004)]
        count=len(points)
        for i,p in enumerate(points):
            a=points[(i-1)%count] if closed else points[max(0,i-1)]
            b=points[(i+1)%count] if closed else points[min(count-1,i+1)]
            tangent=(b-a).normalized();across=tangent.cross(normals[i]).normalized();n=across.cross(tangent).normalized()
            for x,z in profile:verts.append(p+across*x*width+n*z*height_scale)
        for i in range(count if closed else count-1):
            for j in range(6):
                k=(i+1)%count;faces.append((i*6+j,k*6+j,k*6+(j+1)%6,i*6+(j+1)%6))
        if not closed:faces += [tuple(reversed(range(6))),tuple((count-1)*6+j for j in range(6))]
        return self.mesh(name,verts,faces,mat,part)

    def star(self,name,p,n,r,part='body',stretch=1,mat='metal_light'):
        p,n=Vector(p),Vector(n).normalized();u=Vector((0,0,1)).cross(n).normalized();v=n.cross(u)
        outline=[(0,1),(.23,.23),(1,0),(.23,-.23),(0,-1),(-.23,-.23),(-1,0),(-.23,.23)]
        verts=[p+u*x*r+v*z*r*stretch for x,z in outline]+[p+n*.034,p-n*.007]
        faces=[]
        for i in range(8):faces += [(i,(i+1)%8,8),((i+1)%8,i,9)]
        return self.mesh(name,verts,faces,mat,part,False)

    def frame(self,name,p,n,outline,part='body',gem='gem'):
        p,n=Vector(p),Vector(n).normalized();u=Vector((0,0,1)).cross(n).normalized();v=n.cross(u)
        count=len(outline);verts=[];faces=[]
        for scale,depth in [(1,-.01),(1,.015),(.92,.032),(.73,.032),(.66,.009)]:
            for x,z in outline:verts.append(p+u*x*scale+v*z*scale+n*depth)
        for ring in range(4):
            for i in range(count):faces.append((ring*count+i,ring*count+(i+1)%count,(ring+1)*count+(i+1)%count,(ring+1)*count+i))
        faces += [tuple(reversed(range(count))),tuple(4*count+i for i in range(count))]
        self.mesh(name+'_frame',verts,faces,'metal',part,False)
        verts=[];faces=[]
        for scale,depth in [(.65,.010),(.45,.086)]:
            for x,z in outline:verts.append(p+u*x*scale+v*z*scale+n*depth)
        verts.append(p-u*.02+n*.098)
        for i in range(count):
            j=(i+1)%count;faces += [(i,j,j+count,i+count),(i+count,j+count,2*count)]
        faces.append(tuple(reversed(range(count))))
        obj=self.mesh(name+'_crystal',verts,faces,gem,part,False)
        obj.data.materials.append(self.g.M[self.keys['gem_light']]);obj.data.materials.append(self.g.M[self.keys['gem_dark']])
        for poly in obj.data.polygons:poly.material_index=(0,1,0,2,1,0)[poly.index%6]

    def eye(self,head,sign,palette,skin_palette,palette_at=None,width=.48,height=.55,z=2.49):
        side='L' if sign>0 else 'R';name='eye_'+side;support=Surface(head)
        n=Vector((sign*.53,-.847,.025)).normalized();u=Vector((0,0,1)).cross(n).normalized();v=n.cross(u)
        c,_=support.contact((sign*.425,-1.40,z),n,.007)
        c-=n*.048
        def coord(a,t=1):
            x=width*.5*math.cos(a)*t
            zz=height*.5*math.sin(a)*(.85+.15*abs(math.sin(a)))*t+sign*x*.10
            return x,zz
        def point(x,zz,offset=0):
            r2=(x/(width*.5))**2+(zz/(height*.5))**2
            return c+u*x+v*zz+n*(.013+.043*max(0,1-r2)+offset)
        seg=144;rings=56
        outline=[c+u*x+v*zz for x,zz in (coord(math.tau*j/seg,1.16) for j in range(seg))]
        verts=[p+n*.50 for p in outline]+[p-n*.43 for p in outline]
        faces=[tuple(range(seg)),tuple(reversed(range(seg,seg*2)))]
        faces.extend((j,j+seg,(j+1)%seg+seg,(j+1)%seg) for j in range(seg))
        cutter=self.mesh(name+'_socket_tool',verts,faces,'coat','head')
        mod=head.modifiers.new('Recessed ocular opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
        self.g.apply(head,mod);self.g.ASSET.remove(cutter);bpy.data.objects.remove(cutter,do_unlink=True)
        verts=[];faces=[]
        for row in range(13):
            t=row/12
            for j in range(seg):
                x,zz=coord(math.tau*j/seg,1+.185*t);flat=c+u*x+v*zz
                hit,_=support.contact(flat,n,.004)
                # One shared geometric boundary: no overlapping flat annulus
                # strip crossing the curved iris at its outer edge.
                verts.append(point(x,zz).lerp(hit,smooth(t)))
        for row in range(12):
            for j in range(seg):
                a=row*seg+j;b=row*seg+(j+1)%seg;faces.append((a,a+seg,b+seg,b))
        rim=self.mesh(name+'_skin_annulus',verts,faces,'coat','head')
        self.paint(rim,skin_palette,.0002,palette_at)
        verts=[];faces=[];colors=[];upper,lower=palette;ivory=self.g.color('E9E4D9');black=self.g.color('02050A')
        for row in range(rings+1):
            t=max(.00001,row/rings)
            for j in range(seg):
                a=math.tau*j/seg;x,zz=coord(a,t);verts.append(point(x,zz))
                ir=math.sqrt((x/(width*.402))**2+((zz+height*.012)/(height*.433))**2)
                pr=math.sqrt((x/(width*.227))**2+((zz-height*.070)/(height*.272))**2)
                color=ivory
                if ir<1.022:
                    f=max(0,min(1,.47-zz/(height*.78)))
                    intensity=.98+.025*math.sin(a*71+ir*13)+.014*math.sin(a*109-ir*19)
                    if ir>.92:intensity*=.38+.62*(1-ir)/.08
                    color=tuple(value*intensity for value in mix(upper,lower,f)[:3])+(1,)
                    color=mix(color,ivory,smooth((ir-.983)/.039))
                if pr<1:color=mix(black,color,smooth((pr-.95)/.05))
                colors.append(color)
        for row in range(rings):
            for j in range(seg):
                a=row*seg+j;b=row*seg+(j+1)%seg;faces.append((a,a+seg,b+seg,b))
        key=self.prefix+'_'+name+'_living_iris';mat=self.g.material(key,'FFFFFF',0,.25);self.g.M[key]=mat
        shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Specular IOR Level'].default_value=.20
        attribute=mat.node_tree.nodes.new('ShaderNodeVertexColor');attribute.layer_name='AST_eye_color'
        mat.node_tree.links.new(attribute.outputs['Color'],shader.inputs['Base Color'])
        eye=self.mesh(name,verts,faces,key,'head');self.colors(eye,colors);eye['eye_side']=side
        for upper_lid in (True,False):
            start,end=(0,math.pi) if upper_lid else (math.pi,math.tau)
            points=[point(*coord(start+(end-start)*i/40),.006) for i in range(41)]
            widths=[(.003+.026*math.sin(math.pi*i/40)**.65) if upper_lid else .006 for i in range(41)]
            self.g.sweep(self.prefix+'_'+name+('_upper_lid' if upper_lid else '_lower_lid'),points,widths,
                         [w*.52 for w in widths],self.keys['ink'] if upper_lid else self.keys['coat'],'head',normal=n,steps=88,sides=20)
        x=sign*width*.475
        self.g.sweep(self.prefix+'_'+name+'_lash_wing',[point(x,.035,.008),point(x+sign*.042,.065,.010),point(x+sign*.087,.112,.002)],
                     [.018,.026,.0005],[.010,.012,.0005],self.keys['ink'],'head',normal=n,steps=32,sides=18)
        for suffix,x,zz,rx,rz in [('catchlight',-.067,.117,.039,.045),('pinlight',.072,-.150,.013,.017)]:
            self.g.disk(self.prefix+'_'+name+'_'+suffix,point(x,zz,.009),u,v,n,rx,rz,self.keys['white'],'head',bulge=.001,rings=8,seg=48)
        lidverts=[]
        for p in verts:
            d=p-c;lidverts.append(c+u*d.dot(u)*1.075+v*d.dot(v)*1.055+n*(d.dot(n)+.031))
        lid=self.mesh(name+'_closed_lid',lidverts,faces,'coat','lid.'+side)
        self.paint(lid,skin_palette,.0001,palette_at);lid['ast_lid_pivot']=list(c+n*.031)
        points=[point(width*.46*q,-height*.10*(1-q*q),.035) for q in (-1,-.75,-.5,-.25,0,.25,.5,.75,1)]
        lash=self.g.sweep(self.prefix+'_'+name+'_closed_lash',points,[.002,.010,.012,.010,.002],[.001,.005,.006,.005,.001],
                          self.keys['ink'],'lid.'+side,normal=n,steps=60,sides=16)
        lash['ast_lid_pivot']=list(c+n*.031)

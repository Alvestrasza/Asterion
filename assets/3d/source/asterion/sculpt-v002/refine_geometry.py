"""Reference-led mesh refinements on an in-memory copy; never rebuild the rig."""
import math
from array import array
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def remove(g, prefixes):
    for obj in list(g.ASSET):
        if obj.name.startswith(prefixes):
            g.ASSET.remove(obj)
            bpy.data.objects.remove(obj, do_unlink=True)


def apply_surface(g, obj, levels=1):
    modifiers=[m for m in obj.modifiers if m.type=='ARMATURE']
    states=[m.show_viewport for m in modifiers]
    for m in modifiers:m.show_viewport=False
    mod=obj.modifiers.new('Reference surface resolution', 'SUBSURF')
    mod.levels=levels;mod.subdivision_type='CATMULL_CLARK'
    g.apply(obj,mod)
    for m,state in zip(modifiers,states):m.show_viewport=state


def muzzle_point(p):
    # Keep the eyes, skull and all rig pivots in place. Sculpt only the lower
    # forward muzzle into a more compact wedge with a firmer chin.
    p=p.copy()
    amount=math.exp(-((p.y+1.88)/.36)**4)*max(0,min(1,(3.68-p.z)/.23))
    p.x*=1-.12*amount
    p.z+=.044*amount*max(0,min(1,(3.43-p.z)/.15))
    p.y-=.038*amount*math.exp(-(p.x/.27)**2)
    return p


def face(g):
    for obj in g.ASSET:
        if obj.type!='MESH' or obj.get('ast_part') not in ('head','eye.L','eye.R','lid.L','lid.R'):continue
        inv=obj.matrix_world.inverted()
        for v in obj.data.vertices:v.co=inv@muzzle_point(obj.matrix_world@v.co)
        obj.data.update()
    head=bpy.data.objects['AST_Sculpted_head']
    bvh=BVHTree.FromPolygons([head.matrix_world@v.co for v in head.data.vertices],
                            [list(p.vertices) for p in head.data.polygons])
    remove(g,('AST_gentle_smile.',))
    for s,side in ((1,'L'),(-1,'R')):
        points=[]
        for x,z in ((0,3.325),(.17,3.318),(.32,3.328),(.425,3.36)):
            hit,n,_,_=bvh.ray_cast(Vector((s*x,-3,z)),Vector((0,1,0)))
            if hit is not None:points.append(hit+n*.004)
        if len(points)==4:g.line('restrained_mouth.'+side,points,.006,'black','head',resolution=10)
        eye=bpy.data.objects['AST_living_eye.'+side]
        center=Vector((s*.538,-1.648,3.79));across=Vector((s*.893,.450,0)).normalized()
        colors=[]
        for vert in eye.data.vertices:
            d=eye.matrix_world@vert.co-center;x=d.dot(across);z=d.z
            ix=(x+.032)/.256;iz=(z+.026)/.241;r=math.hypot(ix,iz)
            col=g.color('D3C8A2')
            if r<1:
                theta=math.atan2(iz,ix)
                fiber=.038*math.sin(91*theta+1.2*math.sin(13*theta))+.016*math.sin(147*theta)
                brightness=(.42+.09*max(0,-iz)+fiber)*(1-.35*max(0,iz))
                col=g.color('005493' if r>.90 else '00B0F4')
                col=tuple(c*brightness for c in col[:3])+(1,)
            if ((x+.042)/.071)**2+((z-.001)/.165)**2<1:col=g.color('010917')
            colors.extend(col)
        eye.data.color_attributes['AST_eye_color'].data.foreach_set('color',colors)
        brow=bpy.data.objects['AST_upper_brow.'+side]
        # Preserve the fitted brow centerline but reduce its tubular inflation.
        for start in range(0,len(brow.data.vertices),24):
            ring=list(brow.data.vertices[start:start+24])
            center=sum((v.co for v in ring),Vector())/len(ring)
            for v in ring:v.co=center+(v.co-center)*.80


def horns(g):
    remove(g,('AST_great_horn.','AST_inner_horn.','AST_horn_highlight_ridge.'))
    for s,side in ((1,'L'),(-1,'R')):
        specs=[('great_horn.',[(s*.57,-1.01,4.32),(s*.74,-.65,4.71),(s*.98,-.12,5.04),(s*1.07,.46,5.35),(s*.96,.70,5.80)],
                [.23,.34,.31,.17,.0005],[.132,.18,.144,.076,.0005],'gold',160,64),
               ('inner_horn.',[(s*.35,-1.49,4.19),(s*.47,-1.17,4.56),(s*.51,-.79,4.86),(s*.43,-.58,5.27)],
                [.14,.20,.17,.0005],[.084,.101,.078,.0005],'gold_light',112,56)]
        for prefix,path,widths,depths,mat,steps,sides in specs:
            centers=g.spline(path,steps);vs=[];fs=[]
            for i,c in enumerate(centers):
                t=i/steps;tan=(centers[min(i+1,steps)]-centers[max(0,i-1)]).normalized()
                normal=Vector((s*.95,.05,.15));normal=(normal-tan*normal.dot(tan)).normalized();u=tan.cross(normal).normalized()
                width=g.interpolate(widths,t);depth=g.interpolate(depths,t)
                for j in range(sides):
                    angle=math.tau*j/sides+.11*math.sin(math.pi*t)
                    sector=angle/(math.tau/8);segment=math.floor(sector);blend=sector-segment
                    a=segment*math.tau/8;b=(segment+1)*math.tau/8
                    px=(1-blend)*math.cos(a)+blend*math.cos(b)
                    py=(1-blend)*math.sin(a)+blend*math.sin(b)
                    px=.88*px+.12*math.cos(angle);py=.88*py+.12*math.sin(angle)
                    # Broad longitudinal facets with fine, embedded growth grain.
                    grain=.0015*math.sin(47*angle+2.1*t)*math.sin(math.pi*t)**1.5
                    v=c+u*(width*px)+normal*(depth*py+grain)
                    vs.append(v)
            for i in range(steps):
                for j in range(sides):
                    a=i*sides+j;b=i*sides+(j+1)%sides;fs.append((a,a+sides,b+sides,b))
            fs.extend([tuple(range(sides)),tuple(steps*sides+j for j in reversed(range(sides)))])
            obj=g.mesh(prefix+side,vs,fs,mat,'head')
            obj['ast_refinement']='Flattened longitudinal horn planes with embedded growth grain'


def scales(g):
    for name in ('AST_body_scale_sculpt','AST_head_scale_sculpt','AST_tail_scale_sculpt'):
        obj=bpy.data.objects[name]
        # Smoother shallow lamellae preserve the anatomical rows, instead of
        # the coarse uniformly contrasting tile edges in the first pass.
        apply_surface(g,obj)
        obj.data.update()
    # Overlap the central nape shields more closely to remove isolated pyramids.
    for obj in g.ASSET:
        if obj.name.startswith('AST_dorsal_neck_plate_'):
            center=sum((v.co for v in obj.data.vertices),Vector())/len(obj.data.vertices)
            for v in obj.data.vertices:
                v.co.x*=1.12;v.co.z=center.z+(v.co.z-center.z)*1.13
                v.co.y=center.y+(v.co.y-center.y)*.78
    # Small fitted shield lamellae across the previously smooth temple/rear skull.
    head=bpy.data.objects['AST_Sculpted_head']
    bvh=BVHTree.FromPolygons([head.matrix_world@v.co for v in head.data.vertices],
                            [list(p.vertices) for p in head.data.polygons])
    verts=[];faces=[]
    outline=[(0,.60),(.34,.37),(.45,.03),(.30,-.30),(0,-.59),(-.30,-.30),(-.45,.03),(-.34,.37)]
    for s in (-1,1):
        for row in range(9):
            z=3.60+row*.07
            for col in range(7):
                y=-1.33+col*.112+(row%2)*.04
                if y<-1.12 and z<4.08:continue
                hit,n,_,_=bvh.ray_cast(Vector((s*3,y,z)),Vector((-s,0,0)))
                if hit is None or abs(n.x)<.32:continue
                up=Vector((0,0,1));up=(up-n*up.dot(n)).normalized();u=up.cross(n).normalized()
                base=len(verts);verts.append(hit+n*.005)
                for ring in range(1,7):
                    t=ring/6
                    for x,zz in outline:
                        near,nn,_,_=bvh.find_nearest(hit+(u*x+up*zz)*.126*t)
                        verts.append(near+nn*(.0015+.004*(1-t*t)))
                for j in range(8):faces.append((base,base+1+j,base+1+(j+1)%8))
                for ring in range(5):
                    a=base+1+ring*8;b=a+8
                    for j in range(8):faces.append((a+j,b+j,b+(j+1)%8,a+(j+1)%8))
    for row in range(14):
        z=3.44+row*.073
        for col in range(11):
            x=-.56+col*.105+(row%2)*.03
            if abs(x)<.115:continue
            hit,n,_,_=bvh.ray_cast(Vector((x,2,z)),Vector((0,-1,0)))
            if hit is None or n.y<.22:continue
            up=Vector((0,0,1));up=(up-n*up.dot(n)).normalized();u=up.cross(n).normalized()
            base=len(verts);verts.append(hit+n*.005)
            for ring in range(1,7):
                t=ring/6
                for xx,zz in outline:
                    near,nn,_,_=bvh.find_nearest(hit+(u*xx+up*zz)*.135*t)
                    verts.append(near+nn*(.0015+.004*(1-t*t)))
            for j in range(8):faces.append((base,base+1+j,base+1+(j+1)%8))
            for ring in range(5):
                a=base+1+ring*8;b=a+8
                for j in range(8):faces.append((a+j,b+j,b+(j+1)%8,a+(j+1)%8))
    obj=g.mesh('temple_overlapping_lamellae',verts,faces,'scale_dark','head')
    apply_surface(g,obj)


def armor_detail(g):
    # Fitted shallow blue lamellae continue the reference scale language onto
    # the armor, kept inside the existing gold/inlay silhouette.
    import armor
    for sign,side in ((1,'L'),(-1,'R')):
        vs=[];fs=[]
        for row in range(6):
            z=2.43-row*.09
            for col in range(5):
                theta=.82+col*.105+(row%2)*.032
                if row>3 and abs(theta-1.025)>.105:continue
                base=len(vs)
                center,n=armor._shoulder_surface(theta,z,sign,.032)
                vs.append(center+n*.007)
                for ring in range(1,9):
                    t=ring/8
                    for j in range(12):
                        a=math.tau*j/12
                        pp,nn=armor._shoulder_surface(theta+.063*math.cos(a)*t,z+.073*math.sin(a)*t,sign,.032)
                        vs.append(pp+nn*(.006*(1-t*t)))
                for j in range(12):fs.append((base,base+1+j,base+1+(j+1)%12))
                for ring in range(7):
                    a=base+1+ring*12;b=a+12
                    for j in range(12):fs.append((a+j,b+j,b+(j+1)%12,a+(j+1)%12))
        obj=g.mesh('shoulder_enamel_lamellae_'+side,vs,fs,'armor','armor.shoulder.'+side)
        apply_surface(g,obj)
    for obj in g.ASSET:
        if '_gold_claw_' in obj.name:
            coords=[obj.matrix_world@v.co for v in obj.data.vertices]
            ybase=max(p.y for p in coords);inv=obj.matrix_world.inverted()
            for v,p in zip(obj.data.vertices,coords):
                p.y=ybase+(p.y-ybase)*.82
                p.z=max(.073,.073+(p.z-.073)*.92)
                v.co=inv@p


def surface_color(g):
    # Low-amplitude authored color survives glTF; no unsupported procedural
    # texture graph or image projection. Keep all eyes on their own color data.
    palettes={'navy':'05162F','scale_dark':'091D3C','scale':'0D2449','belly':'112947','armor':'081C3D'}
    for key,h in palettes.items():
        m=g.M[key];m.diffuse_color=g.color(h)
        m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=g.color(h)
    for key in ('gold','gold_light','gold_dark'):
        bsdf=g.M[key].node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Roughness'].default_value=.43
        bsdf.inputs['Metallic'].default_value=.64
    for obj in g.ASSET:
        if obj.type!='MESH' or obj.name.startswith('AST_living_eye.'):continue
        count=len(obj.data.vertices)
        coordinates=np.empty(count*3,dtype=np.float32);obj.data.vertices.foreach_get('co',coordinates)
        xyz=coordinates.reshape((-1,3));x,y,z=xyz.T
        weight=1+.032*np.sin(x*31+y*13+z*19)*np.sin(z*43-y*17)
        if 'horn' in obj.name:weight=1+.10*np.sin(z*9+y*6)*np.sin(x*27-y*11)+.025*np.sin(z*83+y*93)
        colors=np.ones((count,4),dtype=np.float32);colors[:,:3]=weight[:,None]
        attr=obj.data.color_attributes.get('AST_eye_color') or obj.data.color_attributes.new(name='AST_eye_color',type='FLOAT_COLOR',domain='POINT')
        attr.data.foreach_set('color',colors.ravel())
        for mat in obj.data.materials:
            if not mat or mat.name=='AST_Eye_living_azure' or mat.get('ast_v002_color'):continue
            bsdf=mat.node_tree.nodes.get('Principled BSDF')
            if bsdf is None:continue
            nodes=mat.node_tree.nodes;links=mat.node_tree.links
            attrnode=nodes.new('ShaderNodeVertexColor');attrnode.layer_name='AST_eye_color'
            # The installed glTF exporter recognizes the modern RGBA Mix node,
            # not legacy MixRGB. The latter rendered correctly in Blender but
            # silently exported a white palette and no surface variation.
            mult=nodes.new('ShaderNodeMix');mult.data_type='RGBA';mult.blend_type='MULTIPLY'
            mult.inputs[0].default_value=1;mult.clamp_result=False
            mult.inputs[6].default_value=bsdf.inputs['Base Color'].default_value[:]
            links.new(attrnode.outputs['Color'],mult.inputs[7]);links.new(mult.outputs[2],bsdf.inputs['Base Color'])
            mat['ast_v002_color']=True


def refine(g,rig):
    before={o.as_pointer() for o in g.ASSET}
    face(g);horns(g);scales(g);armor_detail(g)
    # Only new meshes need attachment. Existing skin data/action/bone bytes stay.
    import rig_delivery
    for obj in g.ASSET:
        if obj.type=='MESH' and obj.as_pointer() not in before:rig_delivery._skin(obj,rig)
    surface_color(g)
    return {'face':'Narrowed wedge muzzle, shorter mouth, fuller azure irises and less tubular brows',
            'horns':'Flattened longitudinal facets and embedded growth grain',
            'scales':'Shallow softened anatomical lamellae and fitted temple transitions',
            'armor':'Fitted blue layered lamellae inside preserved shoulder outlines',
            'claws':'Shorter seated tapered gold claws with restrained lower envelope'}

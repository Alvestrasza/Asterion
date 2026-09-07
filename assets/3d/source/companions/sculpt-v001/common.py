"""Shared geometric eye, gentle presentation rig and independent asset checks.

The existing Asterion toolkit is reused without changing its accepted master.
All geometry remains volumetric; no reference-image projection is performed.
"""
from __future__ import annotations
import importlib.util
import json
import math
import struct
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT.parents[1]
CLIPS = ('idle','blink','happy','eat','play','pet_reaction','sleep','wake','walk')


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def toolkit():
    return load_file('companion_geometry', SOURCE_ROOT/'asterion'/'sculpt-v001'/'build_sculpt.py')


def exporter():
    return load_file('companion_exporter', SOURCE_ROOT/'asterion'/'sculpt-v001'/'rig_delivery.py')


def eye(g, name, center, normal, width, height, iris, skin, side, head=None):
    """Full width/height almond eye, optional real socket, movable closed lid."""
    # The reference pets have broad, round, expressive irises, not slit pupils.
    height=min(height,width*1.03)
    c = Vector(center); n = Vector(normal).normalized()
    u = Vector((0,0,1)).cross(n).normalized(); v = n.cross(u).normalized()
    tree=None
    if head is not None:
        # Builders specify the desired facial landmark. Project it onto the
        # actual fused skull so no eye can be hidden inside its curved surface.
        tree=BVHTree.FromPolygons([head.matrix_world@p.co for p in head.data.vertices],
                                  [list(p.vertices) for p in head.data.polygons])
        hit,hit_normal,_,_=tree.ray_cast(c+n*max(1,width*3),-n)
        if hit is None:raise ValueError('Eye landmark misses the head: '+name)
        c=hit+n*.006
        cutter = g.uv(name+'_socket_tool', c-n*width*.11,
                      (width*.51,height*.52,width*.29), skin, 'head',seg=64,rings=40)
        cutter.rotation_euler = Matrix((u,v,n)).transposed().to_euler()
        mod = head.modifiers.new(name+' recessed socket','BOOLEAN')
        mod.operation='DIFFERENCE'; mod.solver='EXACT'; mod.object=cutter
        g.apply(head,mod);g.ASSET.remove(cutter);bpy.data.objects.remove(cutter,do_unlink=True)
    def surface(x,z,offset=0):
        point=c+u*x+v*z
        if tree is not None:
            hit,_,_,_=tree.ray_cast(point+n*max(1,width*3),-n)
            if hit is not None:point=hit+n*.006
        return point+n*offset
    material = g.material(name+'_living_iris','FFFFFF',0,.37)
    bsdf = material.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Specular IOR Level'].default_value=.26
    bsdf.inputs['Roughness'].default_value=.20
    bsdf.inputs['Emission Strength'].default_value=0
    attribute = material.node_tree.nodes.new('ShaderNodeVertexColor')
    attribute.layer_name='AST_eye_color'
    material.node_tree.links.new(attribute.outputs['Color'],bsdf.inputs['Base Color'])
    verts=[]; faces=[]; colors=[]; outline=[]
    segments=128; rings=38
    iris_color=g.color(iris); cream=g.color('F8F0DF'); dark=g.color('030610')
    for ring in range(rings+1):
        t=max(.00001,ring/rings)
        for j in range(segments):
            a=math.tau*j/segments; xx=math.cos(a);zz=math.sin(a)
            x=width*.5*xx*t;z=height*.5*zz*(.90+.1*abs(zz))*t
            bulge=width*.11*(1-t*t)
            # Follow the skull at the rim; a planar eye would float at its sides.
            verts.append(surface(x,z,bulge))
            ir=math.sqrt((x/(width*.405))**2+((z+height*.045)/(height*.44))**2)
            pr=(x/(width*.225))**2+((z-height*.085)/(width*.235))**2
            col=cream
            if ir < 1:
                angle=math.atan2(z/height,x/width)
                fiber=.055*math.sin(angle*93)+.025*math.sin(angle*143)
                intensity=(.36+.62*max(0,-z/(height*.5))+fiber)
                if ir>.88:intensity*=.32
                col=tuple(ch*intensity for ch in iris_color[:3])+(1,)
            if pr<1:col=dark
            colors.append(col)
            if ring==rings:outline.append(verts[-1])
    for ring in range(rings):
        for j in range(segments):
            a=ring*segments+j;b=ring*segments+(j+1)%segments
            faces.append((a,b,b+segments,a+segments))
    obj=g.mesh(name+'_eye',verts,faces,material,'head')
    obj['eye_side']=side
    attr=obj.data.color_attributes.new(name='AST_eye_color',type='FLOAT_COLOR',domain='POINT')
    for item,col in zip(attr.data,colors):item.color=col
    ink_key='_eye_ink'
    if ink_key not in g.M:g.M[ink_key]=g.material('eye_ink','101019',0,.55)
    if '_eye_white' not in g.M:g.M['_eye_white']=g.material('eye_catchlight','FFFFFF',0,.30)
    for upper in (True,False):
        pts=[]
        start,end=(0,math.pi) if upper else (math.pi,math.tau)
        for j in range(17):
            a=start+(end-start)*j/16
            pts.append(surface(width*.5*math.cos(a),height*.5*math.sin(a)*( .90+.1*abs(math.sin(a))),.008))
        g.line(name+('_upper_lid' if upper else '_lower_lid'),pts,
               width*(.026 if upper else .013),ink_key if upper else skin,'head',resolution=4)
    for suffix,xy,size in [('catchlight',(-.105,.20),.066),('pinlight',(.12,-.25),.023)]:
        x=width*xy[0];z=height*xy[1]
        t2=(x/(width*.5))**2+(z/(height*.5))**2
        p=surface(x,z,width*.11*(1-t2)+.005)
        g.disk(name+'_'+suffix,p,u,v,n,width*size,height*size,'_eye_white','head',bulge=.001,rings=5,seg=32)
    # A slightly expanded curved cover provides overlap at the eye corners.
    lid_verts=[]
    for point in verts:
        d=point-c;lid_verts.append(c+u*d.dot(u)*1.055+v*d.dot(v)*1.055+n*(d.dot(n)+width*.036))
    lid=g.mesh(name+'_closed_lid',lid_verts,faces,skin,'lid.'+side)
    lid['ast_lid_pivot']=list(c+n*(width*.036))
    return obj


def _curves(action):
    if hasattr(action,'fcurves'):yield from action.fcurves
    else:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in getattr(strip,'channelbags',[]):yield from bag.fcurves


def activate(rig, action, frame=1):
    rig.animation_data_create();rig.animation_data.action=action
    if getattr(action,'slots',None):rig.animation_data.action_slot=action.slots[0]
    bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()


def rig_asset(g, spec):
    data=bpy.data.armatures.new(spec['kind']+'_armature')
    rig=bpy.data.objects.new(spec['kind']+'_rig',data);bpy.context.collection.objects.link(rig)
    g.active(rig);bpy.ops.object.mode_set(mode='EDIT')
    root=data.edit_bones.new('root');root.head=(0,0,0);root.tail=(0,0,.35);root.use_deform=True
    definitions=list(spec['bones'])
    for name,head,tail,parent in definitions:
        bone=data.edit_bones.new(name);bone.head=head;bone.tail=tail
        if (Vector(tail)-Vector(head)).length<.01:raise ValueError('Bone length too small: '+name)
    for name,head,tail,parent in definitions:data.edit_bones[name].parent=data.edit_bones[parent or 'root']
    for side in ('L','R'):
        lids=[o for o in g.ASSET if o.get('ast_part')=='lid.'+side]
        if not lids:raise ValueError('Missing blink lid '+side)
        p=Vector(lids[0]['ast_lid_pivot']);b=data.edit_bones.new('lid.'+side)
        b.head=p;b.tail=p+Vector((0,0,.15));b.parent=data.edit_bones['head']
    bpy.ops.object.mode_set(mode='OBJECT')
    rig.show_in_front=True
    bone_names=set(data.bones.keys())
    for obj in g.ASSET:
        if obj.type!='MESH':raise ValueError('Asset object is not a mesh: '+obj.name)
        part=obj.get('ast_part','body')
        if part not in bone_names:raise ValueError(f'Unknown deformation part {part!r} on {obj.name}')
        if len(obj.vertex_groups)==0:
            vg=obj.vertex_groups.new(name=part);vg.add(list(range(len(obj.data.vertices))),1,'REPLACE')
        else:
            for v in obj.data.vertices:
                weights=[p.weight for p in v.groups if p.weight>0]
                if not weights or abs(sum(weights)-1)>.001 or len(weights)>4:
                    raise ValueError('Invalid authored weight on '+obj.name)
        obj.parent=rig
        mod=obj.modifiers.new('Presentation deformation','ARMATURE');mod.object=rig
        mod.use_deform_preserve_volume=False
    create_clips(rig,spec)
    return rig


def create_clips(rig,spec):
    durations={'idle':121,'blink':19,'happy':61,'eat':91,'play':81,
               'pet_reaction':76,'sleep':121,'wake':61,'walk':49}
    height=max(v[2][2] for v in spec['bones'])
    biped=spec['family']=='biped';bones=rig.pose.bones
    for name,count in durations.items():
        action=bpy.data.actions.new(name);action.use_fake_user=True
        rig.animation_data_create();rig.animation_data.action=action
        frames=list(range(1,count+1,2))
        if frames[-1]!=count:frames.append(count)
        for frame in frames:
            t=(frame-1)/(count-1);wave=math.sin(math.tau*t);ease=math.sin(math.pi*t)**2
            for bone in bones:
                bone.rotation_mode='XYZ';bone.location=(0,0,0);bone.rotation_euler=(0,0,0);bone.scale=(1,1,1)
            closed=0.0
            if name=='blink':closed=math.sin(math.pi*t)**.7
            elif name=='sleep':closed=1
            elif name=='wake':closed=max(0,1-t*3)
            for side in ('L','R'):bones['lid.'+side].scale=(max(.0001,closed),)*3
            if name=='idle':bones['head'].rotation_euler.x=.016*wave
            elif name=='happy':
                bones['head'].rotation_euler.z=.10*math.sin(math.tau*t)*ease
                bones['root'].location.y=height*.012*ease*max(0,math.sin(math.tau*t*2))
            elif name=='eat':bones['head'].rotation_euler.x=.09*ease*(.72+.28*math.sin(math.tau*t*3))
            elif name=='play':
                bones['root'].location.y=height*.045*ease
                bones['head'].rotation_euler.z=.12*wave*ease
            elif name=='pet_reaction':bones['head'].rotation_euler.z=.13*ease
            elif name=='sleep':bones['head'].rotation_euler.x=.09+.004*wave
            elif name=='wake':bones['head'].rotation_euler.x=.09*(1-t)-.02*ease
            elif name=='walk':
                for side in ('L','R'):
                    sign=1 if side=='L' else -1
                    for key,phase in [(('leg.' if biped else 'leg.F')+side,1),(('arm.' if biped else 'leg.H')+side,-1)]:
                        if key in bones:bones[key].rotation_euler.x=sign*phase*(.07 if biped else .035)*wave
            for bone in bones:
                if bone.name.startswith('tail'):bone.rotation_euler.z+=(.05 if name=='idle' else .12)*wave
                if bone.name.startswith('ear.'):
                    bone.rotation_euler.z+=.018*wave*(1 if bone.name.endswith('L') else -1)
                if bone.name.startswith('wing.'):
                    bone.rotation_euler.y+=.09*math.sin(math.tau*t*2)*(1 if bone.name.endswith('L') else -1)
                bone.keyframe_insert(data_path='location',frame=frame,group=bone.name)
                bone.keyframe_insert(data_path='rotation_euler',frame=frame,group=bone.name)
                bone.keyframe_insert(data_path='scale',frame=frame,group=bone.name)
        for curve in _curves(action):
            for key in curve.keyframe_points:key.interpolation='LINEAR'
    bpy.context.scene.render.fps=30
    activate(rig,bpy.data.actions['idle'],1)


def bounds(objects):
    points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
    lo=Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
    return lo,hi


def configure_stage(g,objects,resolution=1100,samples=48):
    cam=g.stage(resolution,samples);lo,hi=bounds(objects)
    center=(lo+hi)*.5;span=hi-lo
    ground=bpy.data.objects.get('STUDIO_ground');ground.location.z=lo.z-.008
    # Consistent neutral gallery light; white and pastel materials stay colored.
    scene=bpy.context.scene
    scene.view_settings.look='AgX - Medium High Contrast'
    return cam,center,span


def render_views(g,cam,center,span,output,kind,views):
    scene=bpy.context.scene;paths={};radius=max(span)*3
    directions={'hero':Vector((.85,-1.45,.35)), 'front':Vector((0,-1,.045)),
                'side':Vector((1,0,.06)), 'rear':Vector((0,1,.07))}
    for name in views:
        direction=directions[name].normalized();cam.location=center+direction*radius;g.point_at(cam,center)
        # Axis-aligned bounding corners projected onto the orthographic image.
        right=Vector((0,0,1)).cross(direction).normalized();up=direction.cross(right).normalized()
        corners=[Vector((x*span.x/2,y*span.y/2,z*span.z/2)) for x in (-1,1) for y in (-1,1) for z in (-1,1)]
        extent=max(max(abs(p.dot(right)),abs(p.dot(up))) for p in corners)*2
        cam.data.ortho_scale=extent*1.12
        path=output/(kind+'-sculpt-'+name+'.png');scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True);paths[name]=str(path)
    direction=directions['hero'].normalized();cam.location=center+direction*radius;g.point_at(cam,center)
    return paths


def glb_json(path):
    data=path.read_bytes()
    if data[:4]!=b'glTF' or struct.unpack_from('<I',data,4)[0]!=2:raise ValueError('Invalid GLB')
    if struct.unpack_from('<I',data,8)[0]!=len(data):raise ValueError('Truncated GLB')
    length=struct.unpack_from('<I',data,12)[0]
    return json.loads(data[20:20+length])

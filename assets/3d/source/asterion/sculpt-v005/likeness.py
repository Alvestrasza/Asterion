"""Reference-led crown, face, scale and pigment study on the sealed v004 master.

No new rig, keyframes, physics, subdivision inflation or reference projection.
The temporary no-head-mane decision is retained until explicitly superseded.
"""
import math
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def coordinates(obj):
    p = np.empty(len(obj.data.vertices)*3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', p)
    m = np.asarray(obj.matrix_world, dtype=float)
    return p.reshape((-1,3)) @ m[:3,:3].T + m[:3,3]


def write(obj, p):
    if not np.isfinite(p).all():
        raise ValueError('Nonfinite authored geometry')
    m = np.asarray(obj.matrix_world.inverted(), dtype=float)
    local = p @ m[:3,:3].T + m[:3,3]
    obj.data.vertices.foreach_set('co', local.astype(np.float32).ravel())
    obj.data.update()


def smooth(a,b,p):
    t = np.clip((p-a)/(b-a),0,1)
    return t*t*(3-2*t)


def palette(g):
    # Adjust the actual modern Mix factor, not an unconnected BSDF default.
    colors = dict(navy='071738', scale_dark='081B3D', scale='091D40',
                  belly='112A53', armor='0A1C45', gold='C99638',
                  gold_light='E7B951', gold_dark='87561E')
    for key,h in colors.items():
        mat = g.M[key]; value = g.color(h)
        mat.diffuse_color = value
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value = value
        for node in mat.node_tree.nodes:
            if node.bl_idname == 'ShaderNodeMix' and node.data_type == 'RGBA':
                node.inputs[6].default_value = value
        bsdf.inputs['Roughness'].default_value = .36 if key.startswith('gold') else .57
        bsdf.inputs['Specular IOR Level'].default_value = .30 if key.startswith('gold') else .16


def iris(g, obj):
    """Paint the existing continuous eye topology with a deeper rounded pupil."""
    if len(obj.data.vertices) != 87*192:
        raise ValueError('Unexpected sealed ocular topology')
    ring = np.repeat(np.arange(87)/86,192)
    angle = np.tile(np.arange(192)*math.tau/192,87)
    x = .380*np.cos(angle)*ring
    zz = np.sin(angle)
    z = np.where(zz>0,.182,.204)*zz*(.78+.22*np.abs(zz))*ring + .052*np.cos(angle)*ring
    ix, iz = (x+.052)/.233, (z+.020)/.238
    radius = np.hypot(ix,iz)
    pupil = ((x+.048)/.105)**2 + ((z-.036)/.158)**2
    colors = np.tile(np.array(g.color('D8CFAA')), (len(x),1))
    inside = radius<1
    light = np.clip(.58-.47*iz + .045*np.cos(np.arctan2(iz,ix)*47),.22,1.15)
    bright = np.array(g.color('009FE9'))[:3]
    colors[inside,:3] = bright[None,:]*light[inside,None]*.45
    rim = inside & (radius>.86)
    colors[rim,:3] = np.array(g.color('06446F'))[:3]*.58
    colors[pupil<1,:3] = np.array(g.color('010918'))[:3]
    obj.data.color_attributes['AST_eye_color'].data.foreach_set('color',colors.astype(np.float32).ravel())


def scale_relief(g,obj,support):
    p = coordinates(obj); before = p.copy()
    tree = BVHTree.FromPolygons([support.matrix_world@v.co for v in support.data.vertices],
                               [list(f.vertices) for f in support.data.polygons])
    # Preserve original row topology and attachment weights. Reduce protruding
    # pebble-like relief while retaining legible plate boundaries.
    for i,point in enumerate(p):
        hit,normal,_,distance = tree.find_nearest(Vector(point))
        if hit is not None and distance<.065:
            delta = Vector(point)-hit
            if delta.dot(normal)>0:
                p[i] = hit + delta*.56
    write(obj,p)
    # Bring neighboring plate materials into a single, coherent navy family.
    colors = np.ones((len(p),4),dtype=np.float32)
    gain = .94 + .025*np.sin(p[:,0]*11+p[:,1]*19+p[:,2]*8)
    colors[:,:3] = gain[:,None]
    obj.data.color_attributes['AST_eye_color'].data.foreach_set('color',colors.ravel())
    return {'name':obj.name,'operation':'shallower skin-seated lamellae and unified navy pigment',
            'max_displacement':float(np.linalg.norm(p-before,axis=1).max())}


def apply(g,rig,kind):
    if kind!='asterion':raise ValueError(kind)
    edits=[]
    palette(g)
    for obj in g.ASSET:
        p=coordinates(obj); before=p.copy(); operation=None
        name=obj.name
        if name.startswith(('AST_great_horn.','AST_inner_horn.')):
            height=np.maximum(0,p[:,2]-4.17)
            p[:,2]-=.17*height
            p[:,1]+=.16*smooth(4.32,5.65,before[:,2])
            # Retain rooted broad blade volume; tighten the crown's lateral spread.
            p[:,0]*=1-.055*smooth(4.30,5.65,before[:,2])
            operation='lower, swept-back broad crown blades'
        elif name.startswith(('AST_Dragon_Leaf_Ear_','AST_Dragon_Ear_Swept_Gold_Inlay_')):
            outward=np.maximum(0,np.abs(p[:,0])-.74)
            p[:,0]-=np.sign(p[:,0])*.22*outward
            p[:,2]+=.08*smooth(.76,1.40,np.abs(before[:,0]))
            operation='shorter upright ear silhouette with coherent gold insert'
        elif name in ('AST_Sculpted_head','AST_head_scale_sculpt','AST_temple_overlapping_lamellae') or name.startswith('AST_cheek_scale_'):
            lower=1-smooth(3.42,3.54,p[:,2])
            front=1-smooth(-1.63,-1.15,p[:,1])
            p[:,0]*=1+.10*lower*front
            p[:,2]+=.033*lower*front*np.exp(-((np.abs(p[:,0])-.42)/.27)**2)
            operation='fuller lifted cheek pads and a softer lower-face contour'
        elif name=='AST_rounded_nose':
            center=p.mean(axis=0)
            p=center+(p-center)*np.array((1.23,1.12,1.15))
            p[:,1]-=.010
            operation='broader softly raised triangular nose'
        elif '_gold_claw_' in name:
            center=p.mean(axis=0)
            p[:,2]=.06+(p[:,2]-.06)*1.20
            p[:,1]=center[1]+(p[:,1]-center[1])*1.15-.020
            operation='fuller forward-curving golden claws'
        if operation:
            write(obj,p)
            edits.append(dict(name=name,operation=operation,max_displacement=float(np.linalg.norm(p-before,axis=1).max())))
        if name.startswith('AST_living_eye.'):
            iris(g,obj)
            edits.append(dict(name=name,operation='deep azure iris with broader rounded pupil and fine radial pigment',max_displacement=0))
    for name,support in [('body','body'),('head','head'),('tail','tail')]:
        edits.append(scale_relief(g,bpy.data.objects['AST_'+name+'_scale_sculpt'],bpy.data.objects['AST_Sculpted_'+support]))
    # The old independent almond covers protrude from the far orbit. Build
    # closed-cover geometry from each actual curved eye surface instead; keep
    # the same object, lid joint and untouched scale-action curves.
    for sign,side in ((1,'L'),(-1,'R')):
        eye=bpy.data.objects['AST_living_eye.'+side]
        lid=bpy.data.objects['AST_closed_eyelid.'+side]
        points=coordinates(eye)
        center=points[:192].mean(axis=0)
        normal=np.array((sign*.45,-.892,.03));normal/=np.linalg.norm(normal)
        tree=BVHTree.FromPolygons([Vector(p) for p in points],[list(f.vertices) for f in eye.data.polygons])
        for prefix in ('AST_eye_catchlight.','AST_eye_pinlight.'):
            glint=bpy.data.objects[prefix+side];gp=coordinates(glint);original=gp.copy()
            for index,point in enumerate(gp):
                hit,_,_,_=tree.find_nearest(Vector(point))
                if hit is None:raise ValueError('Catchlight lacks corneal support')
                gp[index]=hit+Vector(normal)*.001
            write(glint,gp)
            edits.append(dict(name=glint.name,operation='catchlight seated on the actual eye beneath closed-cover geometry',
                max_displacement=float(np.linalg.norm(gp-original,axis=1).max())))
        points=center+(points-center)*1.060+normal*.014
        old=lid.data
        lid.data=eye.data.copy();lid.data.name='AST_v005_conforming_closed_cover_'+side
        lid.data.materials.clear();lid.data.materials.append(g.M['navy'])
        lid.data.color_attributes['AST_eye_color'].data.foreach_set('color',np.ones(len(points)*4,dtype=np.float32))
        lid.vertex_groups.clear()
        group=lid.vertex_groups.new(name='lid.'+side);group.add(list(range(len(points))),1.0,'REPLACE')
        write(lid,points)
        if not old.users:bpy.data.meshes.remove(old)
        edits.append(dict(name=lid.name,operation='curved close-fitting lid surface rebuilt from the actual eye; original lid bone/actions retained',max_displacement=0,new_vertices=len(points)))
    # Shorter smile is seated back on the altered real muzzle surface.
    head=bpy.data.objects['AST_Sculpted_head']
    tree=BVHTree.FromPolygons([head.matrix_world@v.co for v in head.data.vertices],[list(f.vertices) for f in head.data.polygons])
    for obj in g.ASSET:
        if not obj.name.startswith('AST_rounded_mouth.'):continue
        p=coordinates(obj);before=p.copy();p[:,0]*=.90
        for i,point in enumerate(p):
            hit,n,_,_=tree.ray_cast(Vector((point[0],-4,point[2])),Vector((0,1,0)))
            if hit is None:raise ValueError('Unsupported lip contour')
            p[i]=hit+n*.004
        write(obj,p)
        edits.append(dict(name=obj.name,operation='short surface-seated lip corners',max_displacement=float(np.linalg.norm(p-before,axis=1).max())))
    body=bpy.data.objects['AST_Sculpted_body']
    body_tree=BVHTree.FromPolygons([body.matrix_world@v.co for v in body.data.vertices],[list(f.vertices) for f in body.data.polygons])
    for obj in g.ASSET:
        if not obj.name.startswith('AST_Back_Collar_Gold_Rim_'):continue
        p=coordinates(obj);before=p.copy()
        for i,point in enumerate(p):
            hit,n,_,distance=body_tree.find_nearest(Vector(point))
            if hit is not None and distance>.035:
                p[i]=hit+(Vector(point)-hit)*(max(.028,distance*.14)/distance)
        write(obj,p)
        edits.append(dict(name=obj.name,operation='rear collar rim fitted to the actual neck instead of a floating arch',max_displacement=float(np.linalg.norm(p-before,axis=1).max())))
    # Raise the upper chest into the long exposed neck, leaving the entire
    # head/ocular family at its original lid-bone pivots. Translating a lid's
    # rest vertices away from a scale-animation pivot would make it flap during
    # partial blinks even if a fully closed frame happened to line up.
    def upper_chest(z):
        return .16*smooth(1.8,2.65,z)*(1-smooth(3.05,3.50,z))
    for obj in g.ASSET:
        part=str(obj.get('ast_part',''))
        if part=='head' or part.startswith(('eye.','lid.')) or obj.name.startswith('AST_fitted_nape_shield_'):
            continue
        p=coordinates(obj);before=p.copy()
        if obj.get('ast_hair_export'):
            # Translate complete strand rings, not each radial sample through
            # a nonuniform field: the latter would turn circular hair into
            # ellipses and disagree with Blender's native scalar strand radii.
            sides=int(obj.get('ast_hair_sides',0))
            if sides<3 or len(p)%sides:raise ValueError('Unexpected hair ring layout')
            rings=p.reshape((-1,sides,3));centers=rings.mean(axis=1)
            rings[:,:,2]+=(upper_chest(centers[:,2]))[:,None]
        else:
            p[:,2]+=upper_chest(p[:,2])
        displacement=float(np.linalg.norm(p-before,axis=1).max())
        if displacement>1e-6:
            write(obj,p)
            edits.append(dict(name=obj.name,operation='fuller raised upper-chest field with original ocular pivots preserved',max_displacement=displacement))
    for obj in bpy.context.scene.objects:
        if obj.type!='CURVES' or not obj.get('ast_native_hair'):continue
        attribute=obj.data.attributes.get('position')
        if attribute is None:raise ValueError('Native strand position attribute missing')
        data=np.empty(len(attribute.data)*3,dtype=np.float32)
        attribute.data.foreach_get('vector',data)
        m=np.asarray(obj.matrix_world,dtype=float)
        p=data.reshape((-1,3))@m[:3,:3].T+m[:3,3]
        p[:,2]+=upper_chest(p[:,2])
        inv=np.asarray(obj.matrix_world.inverted(),dtype=float)
        p=p@inv[:3,:3].T+inv[:3,3]
        attribute.data.foreach_set('vector',p.astype(np.float32).ravel())
    return dict(notes='Swept-back compact crown, shorter coherent neck/ears, fuller cheek/nose silhouette, rounded azure pupils, shallow navy scales, fitted rear collar and fuller gold claws. Head mane still omitted by prior instruction.',
                edited_objects=edits,added_base_clothing=[],head_mane_omitted=True,native_tail_groom_same_silhouette_field=True)

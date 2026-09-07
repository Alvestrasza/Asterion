"""Round the muzzle and fit overlapping dorsal shields to the actual anatomy."""
import math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)))
    return t*t*(3-2*t)


def rounded_muzzle(p):
    p=p.copy()
    depth=max(0,-p.y-1.78)
    lower=1-smooth(3.56,3.80,p.z)
    # Monotonic compression: the forward surface cannot fold into a lip shelf.
    p.y+=.47*(depth-.04*(1-math.exp(-depth/.04)))*lower
    p.x*=1+.14*smooth(0,.24,depth)*lower
    return p


def soften_muzzle(head):
    import numpy as np
    coords=np.empty(len(head.data.vertices)*3,dtype=np.float32)
    head.data.vertices.foreach_get('co',coords);coords=coords.reshape((-1,3))
    edges=np.empty(len(head.data.edges)*2,dtype=np.int32)
    head.data.edges.foreach_get('vertices',edges);edges=edges.reshape((-1,2))
    a,b=edges.T;degree=np.bincount(edges.ravel(),minlength=len(coords)).clip(1)
    weight=np.array([.55*smooth(1.62,1.89,-p[1])*(1-smooth(3.43,3.60,p[2])) for p in coords],dtype=np.float32)
    for _ in range(18):
        total=np.zeros_like(coords);np.add.at(total,a,coords[b]);np.add.at(total,b,coords[a])
        coords+=(total/degree[:,None]-coords)*weight[:,None]
    head.data.vertices.foreach_set('co',coords.ravel());head.data.update()


def surface(obj):
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
        [list(p.vertices) for p in obj.data.polygons])


def discard(g,prefixes):
    removed=[]
    for obj in list(g.ASSET):
        if obj.name.startswith(prefixes):
            removed.append(obj.name);g.ASSET.remove(obj)
            bpy.data.objects.remove(obj,do_unlink=True)
    return removed


def add_white_attribute(obj):
    attr=obj.data.color_attributes.get('AST_eye_color') or obj.data.color_attributes.new(
        name='AST_eye_color',type='FLOAT_COLOR',domain='POINT')
    attr.data.foreach_set('color',[1.0]*(4*len(obj.data.vertices)))


def refine_face(g,rig,delivery):
    head=bpy.data.objects['AST_Sculpted_head']
    before=min((head.matrix_world@v.co).y for v in head.data.vertices)
    changed=[]
    excluded=('AST_orbital_socket.','AST_living_eye.','AST_upper_brow.',
        'AST_lower_eyelid.','AST_closed_eyelid.','AST_eye_catchlight.','AST_eye_pinlight.')
    for obj in g.ASSET:
        if obj.get('ast_part')!='head' or obj.name.startswith(excluded):continue
        inverse=obj.matrix_world.inverted();count=0
        for vertex in obj.data.vertices:
            original=obj.matrix_world@vertex.co;point=rounded_muzzle(original)
            if (original-point).length>1e-8:
                vertex.co=inverse@point;count+=1
        if count:obj.data.update();changed.append(obj.name)
    soften_muzzle(head)
    removed=discard(g,('AST_nose','AST_recessed_nostril.','AST_restrained_mouth.'))
    bvh=surface(head);new=[]
    hit,n,_,_=bvh.ray_cast(Vector((0,-4,3.48)),Vector((0,1,0)))
    if hit is None:raise ValueError('No rounded nose attachment surface')
    outline=[(0,-.054),(-.081,-.025),(-.136,.022),(-.107,.051),
        (0,.057),(.107,.051),(.136,.022),(.081,-.025)]
    vertices=[]
    for elevation in (-.004,.032):
        for x,z in outline:
            point,normal,_,_=bvh.ray_cast(Vector((x,-4,3.48+z)),Vector((0,1,0)))
            if point is None:raise ValueError('Nose outline must contact the muzzle')
            vertices.append(point+normal*elevation)
    faces=[tuple(reversed(range(8))),tuple(range(8,16))]
    faces.extend((i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8))
    nose=g.mesh('rounded_nose',vertices,faces,'navy','head')
    bevel=nose.modifiers.new('Soft triangular nose edges','BEVEL');bevel.width=.011;bevel.segments=5
    g.apply(nose,bevel)
    new.append(nose)
    for sign,side in ((1,'L'),(-1,'R')):
        hit,n,_,_=bvh.ray_cast(Vector((sign*.225,-4,3.49)),Vector((0,1,0)))
        if hit is None:raise ValueError('No rounded nostril attachment surface')
        nostril=g.uv('rounded_nostril.'+side,hit+n*.001,(.026,.007,.014),'black','head',seg=40,rings=24)
        new.append(nostril)
        points=[]
        for x,z in ((0,3.338),(.12,3.329),(.24,3.34),(.355,3.365)):
            hit,n,_,_=bvh.ray_cast(Vector((sign*x,-4,z)),Vector((0,1,0)))
            if hit is None:raise ValueError('No rounded lip attachment surface')
            points.append(hit+n*.002)
        new.append(g.line('rounded_mouth.'+side,points,.0045,'black','head',resolution=16))
    for obj in new:
        add_white_attribute(obj);delivery._skin(obj,rig)
    after=min((head.matrix_world@v.co).y for v in head.data.vertices)
    return {'changed_objects':changed,'removed_objects':removed,
        'new_objects':[o.name for o in new],'head_front_before':before,'head_front_after':after,
        'head_front_retraction':after-before,'mouth_half_width':.355,
        'description':'Shorter broader muzzle, rounded nose and shorter surface-fitted lip line; eye geometry untouched'}


def dorsal_plates(g,rig,delivery):
    head=bpy.data.objects['AST_Sculpted_head'];body=bpy.data.objects['AST_Sculpted_body']
    surfaces=[(head,surface(head)),(body,surface(body))]
    old=[o for o in g.ASSET if o.name.startswith(('AST_dorsal_neck_plate_','AST_spine_scale_'))]
    old_gaps=[]
    for obj in old:
        points=[obj.matrix_world@v.co for v in obj.data.vertices]
        old_gaps.append(min(min(bvh.find_nearest(p)[3] for _,bvh in surfaces) for p in points))
    removed=discard(g,('AST_dorsal_neck_plate_','AST_spine_scale_'))
    # Shield, not spike: a broad rounded shoulder and a trailing tip.
    outline=[(0,-1),(.57,-.78),(.94,-.22),(.88,.30),(.51,.77),(0,1.03),(-.51,.77),(-.88,.30),(-.94,-.22),(-.57,-.78)]
    from mathutils import Vector
    # Catmull-Rom perimeter resampling softens the shoulder without subdivision
    # moving the base away from the measured skin surface.
    controls=[Vector(p) for p in outline];perimeter=[]
    for i,p in enumerate(controls):
        p0=controls[(i-1)%len(controls)];p2=controls[(i+1)%len(controls)];p3=controls[(i+2)%len(controls)]
        for step in range(5):
            t=step/5
            perimeter.append((2*p+(-p0+p2)*t+(2*p0-5*p+4*p2-p3)*t*t+(-p0+3*p-3*p2+p3)*t*t*t)*.5)
    records=[]
    def project(x,along,mode):
        origin=Vector((x,5,along)) if mode=='nape' else Vector((x,along,6))
        direction=Vector((0,-1,0)) if mode=='nape' else Vector((0,0,-1))
        hits=[]
        for source,bvh in surfaces if mode=='nape' else surfaces[1:]:
            hit,n,index,distance=bvh.ray_cast(origin,direction)
            if hit is not None:hits.append((distance,hit,n,source,index))
        if not hits:raise ValueError('No anatomical dorsal surface')
        _,hit,n,source,index=min(hits,key=lambda item:item[0])
        return hit,n,source,index
    def shield(name,mode,center,width,length,rise):
        vs=[];fs=[];attachments=[];n=len(perimeter);rings=10
        def vertex(x,along,height):
            hit,normal,source,face=project(x,along,mode)
            vs.append(hit+normal*height);attachments.append((source,face,hit))
        # Top center, radial top rings, buried matching underside rings.
        vertex(0,center,rise)
        for k in range(1,rings+1):
            r=k/rings
            for u,v in perimeter:
                along=center+v*length*r*(-1 if mode=='nape' else 1)
                vertex(u*width*r,along,-.005+rise*(1-r*r)**1.45)
        for i in range(n):fs.append((0,1+i,1+(i+1)%n))
        for k in range(rings-1):
            a=1+k*n;b=a+n
            for i in range(n):j=(i+1)%n;fs.append((a+i,b+i,b+j,a+j))
        bottom=len(vs)
        for u,v in perimeter:
            vertex(u*width,center+v*length*(-1 if mode=='nape' else 1),-.011)
        end=1+(rings-1)*n
        for i in range(n):j=(i+1)%n;fs.append((end+i,bottom+i,bottom+j,end+j))
        vertex(0,center,-.011);bottom_center=len(vs)-1
        for i in range(n):fs.append((bottom_center,bottom+(i+1)%n,bottom+i))
        # X cross -Z faces rear (+Y); X cross Y faces up (+Z).
        obj=g.mesh(name,vs,fs,'scale_dark','neck' if mode=='nape' else 'body')
        delivery._skin(obj,rig)
        # Nearest anatomical polygon supplies weights; the plate follows the
        # same skin instead of a different procedural head/neck boundary.
        groups={group.name:group for group in obj.vertex_groups}
        for source in (head,body):
            for group in source.vertex_groups:
                if group.name not in groups:groups[group.name]=obj.vertex_groups.new(name=group.name)
        indices=list(range(len(vs)))
        for group in groups.values():group.remove(indices)
        for i,(source,face,hit) in enumerate(attachments):
            vertex_index=min(source.data.polygons[face].vertices,
                key=lambda index:(source.matrix_world@source.data.vertices[index].co-hit).length_squared)
            weights=source.data.vertices[vertex_index].groups
            for weight in weights:
                groups[source.vertex_groups[weight.group].name].add([i],weight.weight,'REPLACE')
        add_white_attribute(obj)
        obj['ast_surface_fitted']=True;obj['ast_dorsal_region']=mode
        obj['ast_skin_rise']=rise
        # Independent nearest-surface distance of the actual finished rim.
        rim_points=vs[end:end+n]
        distances=[min(bvh.find_nearest(p)[3] for _,bvh in surfaces) for p in rim_points]
        records.append({'name':obj.name,'region':mode,'max_rim_distance':max(distances),'rise':rise,'vertices':len(vs)})
    for j in range(11):
        shield('fitted_nape_shield_'+str(j),'nape',4.40-j*.163,.163 if j<6 else .147,.124,.037)
    for j in range(10):
        shield('fitted_back_shield_'+str(j),'back',-.055+j*.15,.145,.124,.042)
    return {'removed_objects':removed,'plates':records,'baseline_max_nearest_plate_gap':max(old_gaps),
        'max_fitted_rim_distance':max(r['max_rim_distance'] for r in records),
        'description':'Closed overlapping shield lamellae projected onto anatomical skin, with transferred attachment weights'}


def separate_equipment(g):
    armor=[];body=[]
    extras=('AST_Fore_Cuff_','AST_Hind_Cuff_','AST_Fore_Sculpted_Gold_Cuff_',
        'AST_Hind_Sculpted_Gold_Cuff_','AST_Haunch_','AST_tail_gold_inlay_','AST_forehead_diadem_')
    collection=bpy.data.collections.new('AST_Equipment_Ceremonial_Gold_v1')
    bpy.context.scene.collection.children.link(collection)
    for obj in g.ASSET:
        is_armor=str(obj.get('ast_part','')).startswith('armor.') or obj.name.startswith(extras)
        obj['asterion_component']='armor' if is_armor else 'body'
        obj['asterion_rig']='asterion-rig-v1'
        if is_armor:
            obj['asterion_equipment_slot']='outfit';obj['asterion_equipment_id']='ceremonial-gold-v1'
            for existing in list(obj.users_collection):existing.objects.unlink(obj)
            collection.objects.link(obj);armor.append(obj)
        else:body.append(obj)
    if not armor or not body:raise ValueError('Both equipment and anatomy must be present')
    return body,armor

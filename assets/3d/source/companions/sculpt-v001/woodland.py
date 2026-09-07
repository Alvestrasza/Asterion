"""Volumetric Liora, Nyra and Fenn from the approved companion portraits.

The portraits guide identity; all surfaces below are modeled in three dimensions.
Single-view hidden anatomy is a coherent species-specific interpretation.
"""
import math
import random

import bpy
import bmesh
from mathutils import Vector
from common import eye


def _materials(g, kind):
    palettes = {
        "rabbit": {"fur":"D9C6A4", "light":"F3E1BD", "shade":"B79D7D", "ear":"AB8FB9",
                   "ear_dark":"705C82", "metal":"B87759", "metal_light":"E9AF87", "armor":"B8A5C4",
                   "gem":"959BE4", "gem_light":"D6E6FF", "nose":"B87F79", "ink":"49392F"},
        "cat": {"fur":"25272B", "light":"A6A8AD", "shade":"15181D", "ear":"895740",
                "ear_dark":"573828", "metal":"B87954", "metal_light":"E4A887", "armor":"086C66",
                "gem":"07B27E", "gem_light":"73F1BE", "nose":"B47B53", "ink":"0A1114"},
        "dog": {"fur":"CA8C35", "light":"E8C887", "shade":"9D6229", "ear":"764A29",
                "ear_dark":"4D321F", "metal":"CF9B3E", "metal_light":"F1CD77", "armor":"182B52",
                "gem":"243F80", "gem_light":"4D79C5", "nose":"382919", "ink":"392A1A"},
    }
    for key, color in palettes[kind].items():
        metal = .55 if key in ("metal", "metal_light") else (.10 if key in ("armor", "gem", "gem_light") else 0)
        rough = .35 if metal else .62
        g.M[key] = g.material(kind + "_" + key, color, metal, rough)


def _mesh(g, name, vertices, faces, material, part="body", smooth=True):
    obj = g.mesh(name, vertices, faces, material, part, smooth)
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data); bm.free(); obj.data.update()
    return obj


def _shape(g, name, center, normal, outline, material, part="body", raised=.035):
    n = Vector(normal).normalized()
    u = Vector((0, 0, 1)).cross(n).normalized()
    v = n.cross(u).normalized()
    c = Vector(center)
    verts = [c + u * x + v * z for x,z in outline]
    count = len(verts)
    verts += [c + n * raised, c - n * .012]
    faces = []
    for i in range(count):
        faces += [(i, (i+1)%count, count), ((i+1)%count, i, count+1)]
    return _mesh(g, name, verts, faces, material, part, False)


def _mount(obj,target,axis=1,sign=-1,baseline=0,clearance=.008):
    """Seat relief markings on the actual sculpt without floating decals."""
    targets=target if isinstance(target,(tuple,list)) else [target]
    surfaces=[(surface,surface.matrix_world.inverted()) for surface in targets]
    obj_inv=obj.matrix_world.inverted()
    direction=Vector((0,0,0));direction[axis]=-sign
    for vertex in obj.data.vertices:
        point=obj.matrix_world@vertex.co;origin=point.copy();origin[axis]=sign*5
        hits=[]
        for surface,inverse in surfaces:
            hit,position,_,_=surface.ray_cast(inverse@origin,inverse.to_3x3()@direction)
            if hit:hits.append(surface.matrix_world@position)
        if hits:
            position=max(hits,key=lambda position:position[axis]*sign)
            point[axis]=position[axis]+sign*clearance+(point[axis]-baseline)
            vertex.co=obj_inv@point
    obj.data.update()
    return obj


def _crescent(g,name,center,normal,size,material="metal_light",part="body"):
    c=Vector(center);n=Vector(normal).normalized();u=Vector((0,0,1)).cross(n).normalized();v=n.cross(u)
    outer=[Vector((math.cos(math.radians(54+i*252/36))*size,math.sin(math.radians(54+i*252/36))*size)) for i in range(37)]
    inner=[Vector((size*.35+math.cos(math.radians(54+i*252/36))*size*.76,math.sin(math.radians(54+i*252/36))*size*.90)) for i in range(37)]
    inner[0]=outer[0];inner[-1]=outer[-1]
    verts=[];faces=[];stride=3;layer=37*stride
    for front in (True,False):
        for i in range(37):
            for j in range(3):
                p=inner[i].lerp(outer[i],j/2);height=.014*math.sin(math.pi*j/2) if front else -.005
                verts.append(c+u*p.x+v*p.y+n*height)
    for side in range(2):
        for i in range(36):
            for j in range(2):
                a=side*layer+i*stride+j;faces.append((a,a+stride,a+stride+1,a+1))
    for i in range(36):
        for j in (0,2):
            a=i*stride+j;b=(i+1)*stride+j;faces.append((a,b,b+layer,a+layer))
    for i in (0,36):
        for j in range(2):
            a=i*stride+j;faces.append((a,a+1,a+1+layer,a+layer))
    return _mesh(g,name,verts,faces,material,part)


def _haunch_crescent(g,name,target,sign,center_y,center_z,size,material,part):
    """A closed, shallow crescent fitted wholly to one hind-leg surface."""
    # Two intersecting circles give a genuine crescent without the crossed
    # inner/outer strips produced by forcing unrelated ellipse endpoints.
    offset,inner_radius=.35,.90
    meet_x=(1-inner_radius*inner_radius+offset*offset)/(2*offset)
    meet_z=math.sqrt(1-meet_x*meet_x)
    outer_angle=math.atan2(meet_z,meet_x)
    inner_angle=math.atan2(meet_z,meet_x-offset)
    rows,across=48,4
    inverse=target.matrix_world.inverted()
    direction=Vector((-sign,0,0));local_direction=inverse.to_3x3()@direction
    projected=[];profiles=[];row_indices=[]
    for row in range(rows+1):
        t=row/rows
        a=outer_angle+t*(math.tau-2*outer_angle)
        b=inner_angle+t*(math.tau-2*inner_angle)
        outer=Vector((math.cos(a),math.sin(a)))
        inner=Vector((offset+inner_radius*math.cos(b),inner_radius*math.sin(b)))
        indices=[]
        for column in ([0] if row in (0,rows) else range(across+1)):
            fraction=column/across;p=inner.lerp(outer,fraction)*size
            origin=Vector((sign*5,center_y+sign*p.x,center_z+p.y))
            found,position,normal,_=target.ray_cast(inverse@origin,local_direction)
            if not found:
                raise ValueError(name+": crescent extends beyond its single mounting surface")
            position=target.matrix_world@position
            normal=(target.matrix_world.to_3x3()@normal).normalized()
            indices.append(len(projected));projected.append((position,normal))
            profiles.append(math.sin(math.pi*t)**.45*math.sin(math.pi*fraction))
        row_indices.append(indices)
    count=len(projected)
    # The buried back and low rolled face leave no floating perimeter or fin.
    vertices=[p+n*(.0025+.006*profiles[i]) for i,(p,n) in enumerate(projected)]
    vertices += [p-n*.001 for p,n in projected]
    front=[]
    for row in range(rows):
        lower,upper=row_indices[row],row_indices[row+1]
        if len(lower)==1:
            front += [(lower[0],upper[j],upper[j+1]) for j in range(across)]
        elif len(upper)==1:
            front += [(lower[j],upper[0],lower[j+1]) for j in range(across)]
        else:
            front += [(lower[j],upper[j],upper[j+1],lower[j+1]) for j in range(across)]
    faces=front+[tuple(i+count for i in reversed(face)) for face in front]
    boundary=[indices[0] for indices in row_indices]
    boundary += [indices[-1] for indices in reversed(row_indices[1:-1])]
    for i,a in enumerate(boundary):
        b=boundary[(i+1)%len(boundary)];faces.append((a,b,b+count,a+count))
    return _mesh(g,name,vertices,faces,material,part)


def _star(g, name, center, normal, size, material="metal", part="body", stretch=1):
    outline = [(0,.5),(.105,.12),(.5,0),(.105,-.12),(0,-.5),(-.105,-.12),(-.5,0),(-.105,.12)]
    return _shape(g, name, center, normal, [(x*size,z*size*stretch) for x,z in outline], material, part, .025)


def _ribbon(g, name, points, width, material="metal", part="body", normal=(0,-1,0), taper=False):
    pts = [Vector(p) for p in points]
    n = Vector(normal).normalized()
    vertices, faces = [], []
    profile=[(-.5,-.009),(-.5,.005),(-.32,.022),(.32,.022),(.5,.005),(.5,-.009)]
    for i,p in enumerate(pts):
        t=(pts[min(len(pts)-1,i+1)]-pts[max(0,i-1)]).normalized()
        a=t.cross(n).normalized(); local_n=a.cross(t).normalized()
        w=width*(max(.04,math.sin(math.pi*i/(len(pts)-1)))**.55 if taper else 1)
        for x,z in profile: vertices.append(p+a*x*w+local_n*z)
    for i in range(len(pts)-1):
        for j in range(6):
            a=i*6+j;b=i*6+(j+1)%6;faces.append((a,a+6,b+6,b))
    faces += [tuple(reversed(range(6))),tuple((len(pts)-1)*6+j for j in range(6))]
    return _mesh(g,name,vertices,faces,material,part)


def _fur(g,name,start,tip,width=.13,depth=.032,material="light",part="head",normal=(0,-1,0)):
    a,b=Vector(start),Vector(tip);mid=a.lerp(b,.49)+Vector(normal).normalized()*depth*.42
    return g.sweep(name,[a,mid,b],[width*.60,width,.001],[depth*.62,depth,.001],material,part,
                   normal=normal,steps=17,sides=16,flute=.085,ridge=depth*.23)


def _surface_fur(g,name,target,start,flow,width=.045,depth=.009,material="fur",part="body"):
    """Low sculpted hair strokes seated on the continuous skin surface."""
    start,flow=Vector(start),Vector(flow);inverse=target.matrix_world.inverted()
    hit,_,normal,_=target.closest_point_on_mesh(inverse@start)
    normal=(target.matrix_world.to_3x3()@normal).normalized() if hit else Vector((1,0,0))
    transverse=flow.cross(normal).normalized();along,across=12,8;stride=across+1
    layer=(along+1)*stride;vertices=[];faces=[]
    for front in (True,False):
        for i in range(along+1):
            t=i/along;halfwidth=width*max(.015,math.sin(math.pi*t))**.70
            for j in range(across+1):
                side=-1+2*j/across;probe=start+flow*t+transverse*side*halfwidth
                found,position,n,_=target.closest_point_on_mesh(inverse@probe)
                if found:
                    position=target.matrix_world@position;n=(target.matrix_world.to_3x3()@n).normalized()
                else:position,n=probe,normal
                relief=.0015+depth*math.sin(math.pi*t)*(1-side*side) if front else .0002
                # Two shallow channels suggest hair rather than reptilian scales.
                if front:relief*=1-.15*math.exp(-((side-.34)/.11)**2)-.15*math.exp(-((side+.34)/.11)**2)
                vertices.append(position+n*relief)
    for layer_index in range(2):
        for i in range(along):
            for j in range(across):
                a=layer_index*layer+i*stride+j;faces.append((a,a+stride,a+stride+1,a+1))
    for i in range(along):
        for j in (0,across):
            a=i*stride+j;b=(i+1)*stride+j;faces.append((a,b,b+layer,a+layer))
    for i in (0,along):
        for j in range(across):
            a=i*stride+j;faces.append((a,a+1,a+1+layer,a+layer))
    return _mesh(g,name,vertices,faces,material,part)


def _body_fur(g,name,body):
    for sign,side in [(1,"L"),(-1,"R")]:
        for row in range(3):
            for j in range(7):
                y=-.18+j*.17+(row%2)*.06;z=1.78-row*.19
                _surface_fur(g,name+"_flank_fur_"+side+str(row)+"_"+str(j),body,
                             (sign*.75,y,z),(0,.18,-.10),.037,.007)
        for j in range(8):
            _surface_fur(g,name+"_back_fur_"+side+str(j),body,(sign*.23,-.03+j*.16,1.99),(0,.22,-.035),.046,.009)


def _haunch_fur(g,name,haunch,sign,side,y=.69):
    for row in range(3):
        for j in range(5):
            _surface_fur(g,name+"_haunch_fur_"+side+str(row)+"_"+str(j),haunch,
                         (sign*1.02,y-.23+j*.13,1.34-row*.19),(0,.10,-.19),.042,.008,part="leg.H"+side)


def _tail_finish(g,name,tail,steps,sides,amount=.85):
    """Continuous gradient fur with fine integral, color-matched streaks."""
    centers=[]
    for i in range(steps+1):
        centers.append(sum((tail.data.vertices[i*sides+j].co for j in range(sides)),Vector())/sides)
    mat_key=name+"_tail_gradient"
    material=g.material(mat_key,"FFFFFF",0,.66);g.M[mat_key]=material
    nodes=material.node_tree.nodes;shader=nodes.get('Principled BSDF')
    attribute=nodes.new('ShaderNodeVertexColor');attribute.layer_name='AST_eye_color'
    material.node_tree.links.new(attribute.outputs['Color'],shader.inputs['Base Color'])
    shader.inputs['Emission Strength'].default_value=0
    tail.data.materials.clear();tail.data.materials.append(material)
    attr=tail.data.color_attributes.new(name='AST_eye_color',type='FLOAT_COLOR',domain='POINT')
    base=g.M['fur'].diffuse_color;light=g.M['light'].diffuse_color
    for i,vertex in enumerate(tail.data.vertices):
        ring=i//sides;t=ring/steps;radial=(vertex.co-centers[ring]).normalized()
        window=min(1,max(0,(t-.18)/.17))*min(1,max(0,(.97-t)/.17))
        # Subtle longitudinal channels are part of the tail itself. Separate
        # constant-color patches would interrupt its charcoal/silver or gold/
        # cream gradient and read as contrasting leaves after GLB import.
        angle=math.tau*(i%sides)/sides
        vertex.co+=radial*(.0015*window*math.cos(9*angle+.25*math.sin(math.tau*t)))
        blend=amount*window*min(1,max(0,.45+radial.z*1.20))
        attr.data[i].color=tuple(base[j]*(1-blend)+light[j]*blend for j in range(3))+(1,)
    tail.data.update()


def _leaf_ear(g, name, root, mid, tip, width, part, fur="fur", inner="ear", metal=False):
    """Closed long ear with a concave inset and raised fleshy perimeter."""
    root,mid,tip=map(Vector,(root,mid,tip));sign=1 if root.x>0 else -1
    along,across=72,36;stride=across+1;layer=(along+1)*stride
    vertices,faces,indices=[],[],[]
    def surface(t,u,front=True):
        c=(1-t)**2*root+2*(1-t)*t*mid+t*t*tip
        tangent=(2*(1-t)*(mid-root)+2*t*(tip-mid)).normalized()
        n=Vector((sign*.12,-1,.065));n=(n-tangent*n.dot(tangent)).normalized()
        a=tangent.cross(n).normalized()
        w=max(.001,width*math.sin(math.pi*t)**.78+.09*(1-t)**3)
        z=(.060*abs(u)**5-.045*(1-u*u))*math.sin(math.pi*t) if front else -.055-.055*(1-u*u)*math.sin(math.pi*t)
        return c+a*w*u+n*z,n
    for front in (True,False):
        for i in range(along+1):
            for j in range(across+1):vertices.append(surface(i/along,-1+2*j/across,front)[0])
    for side in range(2):
        for i in range(along):
            for j in range(across):
                a=side*layer+i*stride+j;faces.append((a,a+stride,a+stride+1,a+1))
                indices.append(1 if side==0 and abs(-1+2*(j+.5)/across)<.77 and .08<i/along<.96 else 0)
    for i in range(along):
        for j in (0,across):
            a=i*stride+j;b=(i+1)*stride+j;faces.append((a,b,b+layer,a+layer));indices.append(0)
    for i in (0,along):
        for j in range(across):
            a=i*stride+j;faces.append((a,a+1,a+1+layer,a+layer));indices.append(0)
    obj=_mesh(g,name,vertices,faces,fur,part)
    obj.data.materials.append(g.M[inner])
    for p,m in zip(obj.data.polygons,indices):p.material_index=m
    if metal:
        for edge in (-.90,.90):
            pts=[surface(.065+.89*i/50,edge)[0]+surface(.065+.89*i/50,edge)[1]*.007 for i in range(51)]
            _ribbon(g,name+"_rose_edge"+str(edge),pts,.026,"metal",part,taper=True)
    return obj


def _limb(g,name,x,y,top,kind,part):
    if kind=="rabbit" and "H" in part:
        pieces=[g.uv(name+"_haunch",(x,y,top-.25),(.43,.50,.60),"fur",part),
                g.uv(name+"_shin",(x,y-.08,.46),(.28,.32,.38),"fur",part),
                g.uv(name+"_paw",(x,y-.28,.19),(.29,.40,.19),"fur",part)]
    else:
        radius=.235 if kind=="rabbit" else .245
        pieces=[g.uv(name+"_upper",(x,y,top-.23),(radius*1.2,radius*1.1,.47),"fur",part),
                g.uv(name+"_lower",(x,y-.05,.52),(radius,radius,.42),"fur",part),
                g.uv(name+"_paw",(x,y-.20,.18),(radius*1.21,radius*1.58,.19),"fur",part)]
    for k in (-1,0,1):pieces.append(g.uv(name+"_toe"+str(k),(x+k*.13,y-.39,.17),(.105,.17,.135),"fur",part,seg=28,rings=20))
    obj=g.fuse(name,pieces,part,voxel=.025,subdiv=1)
    if kind=="dog":
        # Cream socks are faces of the same continuous paw, with no overlapping
        # toe pads or striped shells added on top of the golden foot.
        obj.data.materials.append(g.M["light"])
        cream_index=len(obj.data.materials)-1
        for polygon in obj.data.polygons:
            p=obj.matrix_world@polygon.center
            boundary=.355+.025*math.sin((p.x-x)*22)+.017*math.cos((p.y-y)*19)
            if p.z<boundary:polygon.material_index=cream_index
    for k in (-.5,.5):g.line(name+"_toecrease"+str(k),[(x+k*.14,y-.485,.185),(x+k*.14,y-.46,.25),(x+k*.14,y-.39,.287)],.0055,"shade",part)
    return obj


def _cuff(g,name,x,y,z,rx=.235,ry=.245,part="body"):
    verts,faces=[],[];count=64
    for ring,(dz,offset) in enumerate([(-.055,0),(-.044,.017),(.045,.017),(.056,0),(.048,-.014),(-.048,-.014)]):
        for i in range(count):
            a=math.tau*i/count;verts.append((x+(rx+offset)*math.cos(a),y+(ry+offset)*math.sin(a),z+dz+.038*abs(math.cos(a))))
    for r in range(6):
        for i in range(count):faces.append((r*count+i,r*count+(i+1)%count,((r+1)%6)*count+(i+1)%count,((r+1)%6)*count+i))
    _mesh(g,name,verts,faces,"metal",part)
    _star(g,name+"_diamond",(x,y-ry-.035,z+.056),(0,-1,0),.21,"metal_light",part,1.3)


def _gem(g,name,center,width,height,part="body"):
    c=Vector(center);poly=[(0,.52),(.49,.23),(.49,-.23),(0,-.52),(-.49,-.23),(-.49,.23)]
    verts=[];faces=[]
    for scale,depth in [(1,0),(.78,-.031),(.59,-.11)]:
        for x,z in poly:verts.append(c+Vector((x*width*scale,depth,z*height*scale)))
    for r in range(2):
        for i in range(6):faces.append((r*6+i,r*6+(i+1)%6,(r+1)*6+(i+1)%6,(r+1)*6+i))
    faces += [tuple(range(12,18)),tuple(reversed(range(6)))]
    obj=_mesh(g,name,verts,faces,"gem",part,False);obj.data.materials.append(g.M["gem_light"])
    for i,p in enumerate(obj.data.polygons):p.material_index=1 if i in (6,9,11) else 0
    pts=[c+Vector((x*(width+.10),-.010,z*(height+.10))) for x,z in poly];pts.append(pts[0])
    _ribbon(g,name+"_bezel",pts,.065,"metal",part)
    return obj


def _armor(g,kind):
    def surface(angle,z,sign,out=.0):
        radius=.76+.045*math.cos((z-1.45)*2)
        n=Vector((sign*math.sin(angle),-math.cos(angle),0))
        clearance=.072 if kind=="Nyra" else 0
        return Vector((sign*radius*math.sin(angle),-.28-.86*math.cos(angle),z))+n*(out+clearance),n
    outline=[(.42,2.02),(.88,1.89),(1.61,1.79),(1.75,1.62),(1.40,1.35),(1.01,.99),(.62,1.17),(.40,1.49)]
    for sign,side in [(1,"L"),(-1,"R")]:
        center=Vector((1.0,1.54));verts=[];faces=[];mi=[];sub=7
        peri=[]
        for i,p in enumerate(outline):
            a,b=Vector(p),Vector(outline[(i+1)%len(outline)])
            for j in range(sub):peri.append(a.lerp(b,j/sub))
        radii=[1,.98,.83,.79,.72,.6,.45,.25,.01];count=len(peri)
        for ri,r in enumerate(radii):
            for p in peri:
                uv=center+(p-center)*r;verts.append(surface(uv.x,uv.y,sign,.02 if ri<3 else .009)[0])
        for r in range(len(radii)-1):
            for j in range(count):
                faces.append((r*count+j,r*count+(j+1)%count,(r+1)*count+(j+1)%count,(r+1)*count+j));mi.append(0 if r<3 else 1)
        faces.append(tuple((len(radii)-1)*count+j for j in range(count)));mi.append(1)
        obj=_mesh(g,kind+"_curved_shoulder_"+side,verts,faces,"metal","body");obj.data.materials.append(g.M["armor"])
        for p,i in zip(obj.data.polygons,mi):p.material_index=i
        solid=obj.modifiers.new("Solid ceremonial plate","SOLIDIFY");solid.thickness=.035;g.apply(obj,solid)
        point,normal=surface(.79,1.57,sign,.030);_star(g,kind+"_shoulder_star_"+side,point,normal,.20,"metal_light")
        point,normal=surface(1.22,1.67,sign,.025);_star(g,kind+"_shoulder_gem_star_"+side,point,normal,.21,"gem_light")
        g.line(kind+"_collar_"+side,[(sign*.32,-.91,2.06),(sign*.53,-.92,1.88),(sign*.45,-1.075,1.60)],.034,"metal","body")
    _gem(g,kind+"_chest_crystal",(0,-1.22,1.40),.42,.56)
    _star(g,kind+"_chest_upper_diamond",(0,-1.21,1.91),(0,-1,0),.27,"metal_light","body",1.2)


def _mouth_line(g,name,points,target,radius):
    """Seat the smile on the muzzle rather than suspending a planar curve."""
    inv=target.matrix_world.inverted();direction=inv.to_3x3()@Vector((0,1,0));seated=[]
    for p in g.spline(points,48):
        p=Vector(p);origin=Vector((p.x,-5,p.z))
        found,hit,normal,_=target.ray_cast(inv@origin,direction)
        if not found:raise ValueError(name+': mouth landmark misses muzzle')
        normal=(target.matrix_world.to_3x3()@normal).normalized()
        seated.append(target.matrix_world@hit+normal*radius*.50)
    return g.line(name,seated,radius,'ink','head',resolution=3)


def _face(g,kind,head,center_z,front_y,width=.88,iris="30A8ED"):
    for sign,side in [(1,"L"),(-1,"R")]:
        eye(g,kind+"_eye_"+side,(sign*.47,front_y+.13,center_z+.12),(sign*.42,-.90,.04),.48,.51,iris,"fur",side,head=head)
    nose_z=center_z-.24
    _shape(g,kind+"_nose",(0,front_y-.30,nose_z),(0,-1,-.02),[(-.095,.031),(.095,.031),(.061,-.020),(0,-.073),(-.061,-.020)],"nose","head",.038)
    _mouth_line(g,kind+"_philtrum",[(0,front_y-.314,nose_z-.048),(0,front_y-.305,nose_z-.15)],head,.007)
    for sign,side in [(1,"L"),(-1,"R")]:
        _mouth_line(g,kind+"_smile_"+side,[(0,front_y-.303,nose_z-.145),(sign*.13,front_y-.299,nose_z-.18),(sign*.27,front_y-.231,nose_z-.155),(sign*.33,front_y-.185,nose_z-.105)],head,.007)


def _rabbit(g):
    _materials(g,"rabbit")
    pieces=[g.uv("Liora_ribcage",(0,.11,1.20),(.65,.91,.68),"fur"),
            g.uv("Liora_rump",(0,.65,1.15),(.70,.70,.77),"fur"),
            g.uv("Liora_chest",(0,-.54,1.40),(.58,.56,.82),"fur"),
            g.uv("Liora_neck",(0,-.68,1.94),(.48,.44,.47),"fur")]
    body=g.fuse("Liora_continuous_body",pieces,voxel=.030,subdiv=1)
    _body_fur(g,"Liora",body)
    head=g.fuse("Liora_sculpted_head",[
        g.uv("Liora_skull",(0,-.88,2.50),(.80,.68,.71),"fur","head"),
        g.uv("Liora_cheek_L",(.255,-1.365,2.22),(.33,.31,.25),"fur","head"),
        g.uv("Liora_cheek_R",(-.255,-1.365,2.22),(.33,.31,.25),"fur","head"),
        g.uv("Liora_chin",(0,-1.19,2.07),(.44,.35,.18),"fur","head"),
        g.uv("Liora_nose_bridge",(0,-1.52,2.22),(.18,.19,.15),"fur","head")],"head",voxel=.020,subdiv=1)
    _face(g,"Liora",head,2.50,-1.40,iris="A8C6F2")
    for sign,side in [(1,"L"),(-1,"R")]:
        _leaf_ear(g,"Liora_long_lavender_ear_"+side,(sign*.40,-.73,2.98),(sign*.63,-.62,4.04),(sign*.82,-.50,4.91),.275,"ear."+side,metal=True)
        for j in range(5):
            z=2.29+j*.105
            _fur(g,"Liora_cheek_fan_"+side+str(j),(sign*.65,-1.02,z),(sign*(.82+.027*(j%3)),-.82,z+.036+.022*(j%2)),.077,.021,"fur" if j%2 else "light","head",(sign*.58,-.81,0))
        for j in range(3):
            _fur(g,"Liora_ear_base_tuft_"+side+str(j),(sign*(.37+j*.08),-.72,3.00+j*.10),(sign*(.51+j*.085),-.70,3.44+j*.12),.085,.028,"light","ear."+side,(0,-1,0))
        _limb(g,"Liora_foreleg_"+side,sign*.42,-.65,1.32,"rabbit","leg.F"+side)
        hind=_limb(g,"Liora_hindleg_"+side,sign*.58,.69,1.31,"rabbit","leg.H"+side)
        _haunch_fur(g,"Liora",hind,sign,side)
        haunch_star=_star(g,"Liora_rose_haunch_star_"+side,(sign*.91,.73,1.38),(sign,0,.1),.23,"metal_light","leg.H"+side)
        _mount(haunch_star,hind,0,sign,sign*.91,.012)
        _cuff(g,"Liora_rose_cuff_"+side,sign*.42,-.70,.46,part="leg.F"+side)
        temple=_star(g,"Liora_temple_star_"+side,(sign*.654,-1.29,2.83),(sign*.42,-.86,.1),.19,"metal","head",1.2)
        _mount(temple,head,baseline=-1.29,clearance=.010)
    puff=[g.uv("Liora_tail_core",(0,1.49,1.32),(.35,.39,.39),"light","tail",seg=48,rings=32)]
    for i in range(7):
        a=math.tau*i/7
        puff.append(g.uv("Liora_tail_round_lobe"+str(i),(.17*math.sin(a),1.59+.06*math.cos(a),1.36+.20*math.cos(a)),(.23,.25,.24),"light","tail",seg=32,rings=24))
    tail=g.fuse("Liora_rounded_cotton_puff",puff,"tail",voxel=.019,subdiv=1)
    for row in range(3):
        for i in range(9):
            a=math.tau*i/9;z=1.14+row*.18
            _surface_fur(g,"Liora_tail_cotton_curl"+str(row)+"_"+str(i),tail,
                         (.35*math.sin(a),1.51+.37*math.cos(a),z),(.13*math.cos(a),-.13*math.sin(a),.11),.052,.010,"light","tail")
    for i in range(11):
        x=(i-5)*.073
        z=2.06-.05*(i%3)
        _fur(g,"Liora_soft_chest_bib"+str(i),(x,-.995,z),(x*1.14,-1.04,z-.16-.035*(i%2)),.057,.018,"light" if i%3 else "fur","body")
    emblem=_star(g,"Liora_forehead_diamond",(0,-1.474,2.97),(0,-.98,.15),.37,"metal","head",1.32)
    _mount(emblem,head,baseline=-1.474)
    inset=_shape(g,"Liora_forehead_inset",(0,-1.506,2.972),(0,-1,.15),[(0,.096),(.047,0),(0,-.09),(-.047,0)],"fur","head",.010)
    _mount(inset,head,baseline=-1.506,clearance=.046)
    _armor(g,"Liora")
    return _spec("Liora","rabbit",2.45,[("ear.L",(.40,-.73,2.98),(.72,-.56,4.62),"head"),("ear.R",(-.40,-.73,2.98),(-.72,-.56,4.62),"head")],
                 ["Cream rabbit with elongated lavender ear bowls, rose-gold/lilac armor, crystal pendant and cotton tail.","Single-view rear anatomy and motion are interpreted; portrait is not projected onto geometry."])


def _cat(g):
    _materials(g,"cat")
    body=g.fuse("Nyra_feline_body",[
        g.uv("Nyra_ribcage",(0,.12,1.23),(.57,.95,.63),"fur"),
        g.uv("Nyra_rump",(0,.76,1.23),(.57,.57,.64),"fur"),
        g.uv("Nyra_chest",(0,-.57,1.48),(.53,.51,.75),"fur"),
        g.uv("Nyra_neck",(0,-.66,1.98),(.43,.42,.46),"fur")],voxel=.029,subdiv=1)
    _body_fur(g,"Nyra",body)
    head=g.fuse("Nyra_feline_head",[
        g.uv("Nyra_skull",(0,-.85,2.52),(.79,.64,.68),"fur","head"),
        g.uv("Nyra_muzzle_L",(.245,-1.34,2.22),(.31,.30,.22),"fur","head"),
        g.uv("Nyra_muzzle_R",(-.245,-1.34,2.22),(.31,.30,.22),"fur","head"),
        g.uv("Nyra_chin",(0,-1.25,2.08),(.39,.31,.15),"fur","head"),
        g.uv("Nyra_nose_bridge",(0,-1.48,2.26),(.17,.20,.14),"fur","head")],"head",voxel=.019,subdiv=1)
    _face(g,"Nyra",head,2.50,-1.39,iris="11DF93")
    for sign,side in [(1,"L"),(-1,"R")]:
        _leaf_ear(g,"Nyra_rust_inner_ear_"+side,(sign*.53,-.62,2.92),(sign*.84,-.55,3.51),(sign*1.02,-.40,3.85),.278,"ear."+side)
        for j in range(4):
            _fur(g,"Nyra_white_ear_tuft_"+side+str(j),(sign*(.68+j*.03),-.67,3.12+j*.08),(sign*(.86+j*.023),-.64,3.24+j*.07),.087,.022,"light","ear."+side,(0,-1,0))
        for j in range(7):
            z=2.18+j*.12
            _fur(g,"Nyra_cheek_lock_"+side+str(j),(sign*.58,-1.06,z),(sign*(.97+.028*(j%3)),-.68,z+.08),.125,.035,"light" if j in (1,2,5) else "fur","head",(sign*.50,-.85,0))
        for j in range(3):
            _fur(g,"Nyra_outer_ear_lock_"+side+str(j),(sign*.69,-.33,2.85+j*.12),(sign*1.11,.05,3.04+j*.20),.11,.034,"fur","head",(sign*.82,-.30,.15))
        _limb(g,"Nyra_foreleg_"+side,sign*.42,-.65,1.35,"cat","leg.F"+side)
        hind=_limb(g,"Nyra_hindleg_"+side,sign*.57,.69,1.35,"cat","leg.H"+side)
        _haunch_fur(g,"Nyra",hind,sign,side)
        for pair,y,x in [("F",-.70,.42),("H",.64,.57)]:
            _cuff(g,"Nyra_copper_cuff_"+pair+side,sign*x,y,.42,part="leg."+pair+side)
            for j in (-1,0,1):
                g.sweep("Nyra_copper_claw_"+pair+side+str(j),[(sign*x+j*.13,y-.40,.25),(sign*x+j*.13,y-.51,.22),(sign*x+j*.13,y-.61,.10)],[.074,.080,.002],[.071,.067,.002],"metal_light","leg."+pair+side,normal=(1,0,0),steps=16,sides=18)
        brow=[(sign*.23,-1.38,2.88),(sign*.37,-1.35,2.96),(sign*.51,-1.26,2.95),(sign*.62,-1.13,2.90)]
        _ribbon(g,"Nyra_copper_brow_"+side,brow,.041,"metal","head",taper=True)
        _haunch_crescent(g,"Nyra_haunch_copper_moon_"+side,hind,sign,.74,1.25,.17,"metal","leg.H"+side)
        haunch_star=_star(g,"Nyra_haunch_star_"+side,(sign*.57,.81,1.79),(sign,0,.3),.13,"metal_light")
        _mount(haunch_star,body,0,sign,sign*.57,.012)
    # Silver swept forelock and layered crest are her strongest secondary silhouette.
    crown=[(-.33,-.99,2.98,-.22,-.28,3.52,.17),(-.08,-1.03,3.05,.13,-.12,3.70,.17),
           (.21,-.91,3.02,.42,-.15,3.53,.17),(.41,-.73,3.03,.70,-.09,3.41,.13),
           (-.50,-.77,3.00,-.59,-.22,3.37,.12)]
    for i,(x,y,z,xx,yy,zz,w) in enumerate(crown):
        a=Vector((x,y,z));tip=Vector((xx,yy,zz));delta=tip-a
        # Rounded, bent hair locks with a soft central crest rather than flat
        # triangular blades. The silhouette follows the backward fur sweep.
        controls=[a,a+Vector((delta.x*.25,delta.y*.14,delta.z*.52)),
                  a+Vector((delta.x*.73,delta.y*.65,delta.z*.93)),tip]
        g.sweep("Nyra_silver_crown_"+str(i),controls,[w*.52,w,w*.70,.001],
                [.047,.085,.062,.001],"light","head",normal=(0,-1,.15),steps=40,sides=30,flute=.045,ridge=.009)
    for i in range(10):
        x=(i-4.5)*.06
        _fur(g,"Nyra_dark_chest_ruff_"+str(i),(x,-1.01,2.05),(x*1.2,-1.16,1.58-.14*(1-abs(x))),.076,.035,"fur","body")
    tail_points=[(0,1.04,1.43),(0,1.61,1.50),(0,2.03,2.06),(0,2.32,2.68),
                 (0,2.72,2.74),(0,2.96,2.39),(0,2.87,1.98),(0,2.83,1.65),(0,3.04,1.50),(0,3.15,1.65)]
    tail=g.sweep("Nyra_swept_plume_tail",tail_points,[.18,.22,.24,.30,.32,.27,.21,.14,.075,.001],
                 [.20,.23,.26,.31,.31,.27,.21,.14,.07,.001],"fur","tail",normal=(1,0,0),steps=132,sides=36,flute=.035)
    _tail_finish(g,"Nyra",tail,132,36,.88)
    emblem=_star(g,"Nyra_copper_forehead_star",(0,-1.439,2.96),(0,-1,.12),.31,"metal_light","head",1.3)
    _mount(emblem,head,baseline=-1.439)
    _armor(g,"Nyra")
    return _spec("Nyra","cat",2.47,[("ear.L",(.53,-.62,2.92),(.92,-.44,3.67),"head"),("ear.R",(-.53,-.62,2.92),(-.92,-.44,3.67),"head")],
                 ["Charcoal cat with emerald eyes, silver swept crown/cheeks/plume tail, rust ear bowls and copper/teal ceremonial armor.","Single-view hidden anatomy is inferred; the tail is a real curled volume, not a portrait relief."])


def _dog(g):
    _materials(g,"dog")
    body=g.fuse("Fenn_puppy_body",[
        g.uv("Fenn_ribcage",(0,.16,1.26),(.61,.96,.67),"fur"),
        g.uv("Fenn_rump",(0,.76,1.21),(.61,.63,.66),"fur"),
        g.uv("Fenn_chest",(0,-.52,1.48),(.59,.55,.78),"fur"),
        g.uv("Fenn_neck",(0,-.69,1.98),(.48,.45,.47),"fur")],voxel=.029,subdiv=1)
    _body_fur(g,"Fenn",body)
    head=g.fuse("Fenn_puppy_head",[
        g.uv("Fenn_skull",(0,-.88,2.58),(.83,.69,.73),"fur","head"),
        g.uv("Fenn_lower_face",(0,-1.17,2.20),(.58,.43,.33),"fur","head")],"head",voxel=.020,subdiv=1)
    muzzle=g.fuse("Fenn_cream_muzzle",[
        g.uv("Fenn_muzzle_L",(.245,-1.45,2.25),(.34,.33,.24),"light","head"),
        g.uv("Fenn_muzzle_R",(-.245,-1.45,2.25),(.34,.33,.24),"light","head"),
        g.uv("Fenn_muzzle_bridge",(0,-1.57,2.32),(.26,.24,.21),"light","head"),
        g.uv("Fenn_soft_chin",(0,-1.40,2.09),(.43,.34,.17),"light","head")],"head",voxel=.020,subdiv=1)
    for sign,side in [(1,"L"),(-1,"R")]:
        eye(g,"Fenn_eye_"+side,(sign*.47,-1.405,2.71),(sign*.40,-.91,.02),.49,.54,"2387E4","fur",side,head=head)
        _fur(g,"Fenn_cream_brow_"+side,(sign*.28,-1.37,3.01),(sign*.62,-1.20,3.09),.095,.026,"light","head",(0,-1,.1))
    nose=g.uv("Fenn_velvet_nose",(0,-1.797,2.335),(.167,.087,.110),"nose","head",seg=56,rings=36)
    _mouth_line(g,"Fenn_philtrum",[(0,-1.813,2.265),(0,-1.789,2.167)],muzzle,.009)
    for sign,side in [(1,"L"),(-1,"R")]:
        _mouth_line(g,"Fenn_happy_mouth_"+side,[(0,-1.789,2.167),(sign*.14,-1.765,2.127),(sign*.29,-1.687,2.147),(sign*.37,-1.619,2.199)],muzzle,.009)
        g.uv("Fenn_nostril_"+side,(sign*.085,-1.874,2.343),(.030,.012,.023),"ink","head",seg=24,rings=16)
        ear_points=[(sign*.63,-.63,3.03),(sign*.92,-.59,2.97),(sign*1.06,-.63,2.58),(sign*1.01,-.77,2.16),(sign*1.15,-.78,2.13)]
        g.sweep("Fenn_floppy_ear_"+side,ear_points,[.16,.285,.315,.23,.001],[.10,.135,.14,.10,.001],"ear","ear."+side,normal=(0,-1,0),steps=70,sides=36,flute=.045)
        for j in range(13):
            t=j/12;x=sign*(.78+.31*t);z=3.02-.72*t
            _fur(g,"Fenn_silky_ear_lock_"+side+str(j),(x,-.73,z),(sign*(abs(x)+.07),-.91,z-.42),.118,.028,"fur" if t<.35 else ("shade" if t<.7 else "ear"),"ear."+side,(0,-1,0))
        for j in range(5):
            _fur(g,"Fenn_soft_cheek_"+side+str(j),(sign*.48,-1.25,2.14+j*.065),(sign*.73,-1.00,2.16+j*.074),.078,.023,"light","head",(sign*.4,-.9,0))
        fore=_limb(g,"Fenn_foreleg_"+side,sign*.42,-.65,1.37,"dog","leg.F"+side)
        hind=_limb(g,"Fenn_hindleg_"+side,sign*.58,.69,1.36,"dog","leg.H"+side)
        _haunch_fur(g,"Fenn",hind,sign,side)
        for pair,x,y in [("F",.42,-.65),("H",.58,.69)]:
            paw=fore if pair=="F" else hind
            for j in range(4):
                _surface_fur(g,"Fenn_soft_paw_fur_"+pair+side+str(j),paw,
                             (sign*x+(j-1.5)*.095,y-.41,.34),(0,.02,-.14),.028,.006,"light","leg."+pair+side)
        _haunch_crescent(g,"Fenn_haunch_crescent_"+side,hind,sign,.74,1.25,.18,"light","leg.H"+side)
        cheek_star=_star(g,"Fenn_cheek_star_"+side,(sign*.48,-1.49,2.27),(sign*.28,-.96,0),.16,"metal_light","head")
        _mount(cheek_star,muzzle,baseline=-1.49,clearance=.009)
    # Sculpted layered cream bib and loose neck ruff, independent of the collar.
    for row in range(3):
        for j in range(9):
            x=(j-4)*.105;z=1.97-row*.17
            _fur(g,"Fenn_chest_bib_"+str(row)+"_"+str(j),(x,-1.03+.18*abs(x),z),(x*1.20,-1.105+.17*abs(x),z-.43+.17*abs(x)),.097,.037,"light","body")
    for j in range(9):
        x=(j-4)*.125
        _fur(g,"Fenn_golden_crown_"+str(j),(x,-.92,3.09-.13*abs(x)),(x+.09,-.49,3.31+.12*math.cos(j*.8)),.101,.040,"fur" if j%3 else "light","head",(0,-1,.25))
    # Wide navy leather collar with two gold borders and a circular celestial tag.
    count=112;verts=[];faces=[]
    for z,out in [(1.91,0),(1.91,.042),(2.10,.042),(2.10,0)]:
        for i in range(count):
            a=math.tau*i/count;verts.append(((.505+out)*math.cos(a),-.71+(.49+out)*math.sin(a),z+.06*math.sin(a)))
    for ring in range(4):
        for i in range(count):faces.append((ring*count+i,ring*count+(i+1)%count,((ring+1)%4)*count+(i+1)%count,((ring+1)%4)*count+i))
    _mesh(g,"Fenn_navy_celestial_collar",verts,faces,"armor","body")
    for z in (1.915,2.10):
        pts=[(.557*math.cos(math.tau*i/90),-.71+.54*math.sin(math.tau*i/90),z+.06*math.sin(math.tau*i/90)) for i in range(91)]
        g.line("Fenn_collar_gold_edge"+str(z),pts,.012,"metal","body")
    for sign,side in [(1,"L"),(-1,"R")]:
        for j in range(3):
            a=-math.pi/2+sign*(.27+j*.32);normal=(math.cos(a),math.sin(a),0)
            _star(g,"Fenn_collar_star_"+side+str(j),(.56*math.cos(a),-.71+.545*math.sin(a),1.99+.06*math.sin(a)),normal,.087,"metal_light")
    g.line("Fenn_pendant_ring",[(.063*math.sin(math.tau*i/40),-1.263,1.81+.079*math.cos(math.tau*i/40)) for i in range(41)],.015,"metal","body")
    g.disk("Fenn_navy_round_medallion",Vector((0,-1.30,1.53)),Vector((1,0,0)),Vector((0,0,1)),Vector((0,-1,0)),.265,.286,"armor","body",bulge=.034,rings=14,seg=72)
    g.line("Fenn_medallion_gold_rim",[(.264*math.sin(math.tau*i/80),-1.322,1.53+.286*math.cos(math.tau*i/80)) for i in range(81)],.026,"metal","body")
    _star(g,"Fenn_medallion_star",(0,-1.372,1.64),(0,-1,0),.30,"metal_light")
    _crescent(g,"Fenn_medallion_moon",(0,-1.369,1.43),(0,-1,0),.155,"metal_light")
    emblem=_star(g,"Fenn_forehead_celestial_star",(0,-1.463,3.08),(0,-1,.15),.39,"metal_light","head",1.25)
    _mount(emblem,head,baseline=-1.463)
    tail_points=[(0,1.13,1.35),(0,1.60,1.50),(0,1.97,1.84),(0,2.04,2.23),(0,1.76,2.45),(0,1.43,2.30),(0,1.49,2.07)]
    tail=g.sweep("Fenn_curled_golden_tail",tail_points,[.20,.23,.29,.31,.30,.19,.001],
                 [.22,.25,.30,.31,.28,.17,.001],"fur","tail",normal=(1,0,0),steps=98,sides=36,flute=.035)
    _tail_finish(g,"Fenn",tail,98,36,.67)
    return _spec("Fenn","dog",2.53,[("ear.L",(.63,-.63,3.03),(1.02,-.72,2.18),"head"),("ear.R",(-.63,-.63,3.03),(-1.02,-.72,2.18),"head")],
                 ["Golden puppy with hanging brown-tipped ears, blue eyes, cream muzzle/bib/paws, navy star collar, round moon-and-star tag and curled fluffy tail.","Unseen anatomy and motion are coherent interpretations of the approved single-view puppy portrait."])


def _spec(name,kind,head_z,extra,notes):
    return {"name":name,"kind":kind,"family":"quadruped","bones":[
        ("body",(0,.1,.95),(0,.1,1.65),None),
        ("neck",(0,-.48,1.65),(0,-.70,head_z-.43),"body"),
        ("head",(0,-.72,head_z-.43),(0,-.82,head_z+.49),"neck"),
        ("leg.FL",(.42,-.65,1.35),(.42,-.80,.18),"body"),
        ("leg.FR",(-.42,-.65,1.35),(-.42,-.80,.18),"body"),
        ("leg.HL",(.58,.69,1.30),(.58,.46,.19),"body"),
        ("leg.HR",(-.58,.69,1.30),(-.58,.46,.19),"body"),
        ("tail",(0,1.04,1.34),(0,1.78,1.48),"body")]+extra,"notes":notes}


def build(g,kind):
    if kind=="rabbit":return _rabbit(g)
    if kind=="cat":return _cat(g)
    if kind=="dog":return _dog(g)
    raise ValueError("Unsupported woodland companion: " + kind)

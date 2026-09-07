"""Liora v002: groomed cream fur, cheek fans, bib and a cotton-tail sculpture.

The approved rabbit portrait is the identity reference, not a projected texture.
Fine coat relief is modeled on the supplied fused anatomy. Larger silhouette
tufts are closed, shallow, swept solids; the tail has one full underlying volume.

Call ``build(g)`` after anatomy/weights and before fitted eyes and ornaments.
The function returns newly registered meshes, also updates only the supplied
``liora_v2_body`` and ``liora_v2_head`` cream surfaces, and preserves their groups.
It never repaints or modifies the ear surfaces; small new ear-base tufts follow
their ear bones. Additional body fur inherits the nearest
anatomical skin weights, including fore/hind limb groups.
"""
from __future__ import annotations

import math

from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from mathutils.noise import noise


TAU = math.tau


def _mix(a,b,t):
    t=max(0.,min(1.,t))
    return tuple(x+(y-x)*t for x,y in zip(a,b))


def _palette(g):
    key='lvf_painted_coat'
    if key not in g.M:
        mat=g.material('Liora_groomed_cream_fur','F1DFBF',0,.72)
        bsdf=mat.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Specular IOR Level'].default_value=.19
        bsdf.inputs['Coat Weight'].default_value=0
        vertex=mat.node_tree.nodes.new('ShaderNodeVertexColor')
        vertex.layer_name='AST_eye_color'
        mat.node_tree.links.new(vertex.outputs['Color'],bsdf.inputs['Base Color'])
        g.M[key]=mat
    # Deliberately warmer and darker than the first draft's near-white coat;
    # the bright studio still lifts this palette toward the reference cream.
    return tuple(g.color(h) for h in ('A48661','CDB28B','E2CBA8','F1DFC0'))


def _grain(p,n):
    """Non-periodic short anisotropic fibers; no normal-dependent phase bands."""
    x,y,z=p
    warp=1.15*noise(Vector((x*7.1,y*7.1,z*7.1)))
    vertical=noise(Vector((x*68.+warp,y*68.,z*18.)))
    dorsal=noise(Vector((x*68.,y*18.+warp,z*68.)))
    fine=noise(Vector((x*139.,y*127.,z*49.)))
    top=abs(n.z)**4
    return max(-1.,min(1.,((1.-top)*vertical+top*dorsal)*1.75+fine*.30))


def _colors(obj,colors):
    attr=obj.data.color_attributes.get('AST_eye_color')
    if attr is None:
        attr=obj.data.color_attributes.new(name='AST_eye_color',type='FLOAT_COLOR',domain='POINT')
    if attr.domain!='POINT' or attr.data_type!='FLOAT_COLOR':
        raise ValueError('Liora coat requires POINT/FLOAT_COLOR on '+obj.name)
    attr.data.foreach_set('color',[c for rgba in colors for c in rgba])


def _find(g,suffix):
    found=[o for o in g.ASSET if o.type=='MESH' and o.name.lower().endswith(suffix)]
    if len(found)!=1:
        raise ValueError('Expected exactly one '+suffix+' before fur.build(g)')
    return found[0]


def _coat_relief(g,obj,palette,head=False):
    """Sub-millimeter-to-millimeter short fibers on the actual skin topology.

    An anisotropic non-periodic noise field forms short irregular fibers. The
    relief is deliberately shallower than the first draft's visible bands.
    No new object, remesh, modifier, texture, or vertex-group change is involved.
    """
    obj.data.update()
    matrix=obj.matrix_world.copy()
    inverse=matrix.inverted()
    normal_matrix=matrix.to_3x3().inverted().transposed()
    # Reading vertex.normal after changing any coordinate may force Blender to
    # recalculate the entire mesh's normals. Snapshot both inputs before the
    # first write so this pass stays linear even on the dense fused anatomy.
    original_positions=[matrix@vertex.co for vertex in obj.data.vertices]
    original_normals=[(normal_matrix@vertex.normal).normalized()
                      for vertex in obj.data.vertices]
    colors=[]
    for vertex,p,n in zip(obj.data.vertices,original_positions,original_normals):
        x,y,z=p
        fine=_grain(p,n)
        fiber=max(0.,min(1.,.5+.68*fine))
        relief=fiber*fiber
        # The future fitted eye/muzzle area stays especially soft and quiet.
        face=head and y<-1.30 and 1.98<z<2.82
        amplitude=.00055 if face else .00135 if head else .00185
        vertex.co=inverse@(p+n*(amplitude*relief))
        under=max(0.,-n.z)*.08
        col=_mix(palette[0],palette[2],.52+.43*fiber-under)
        col=_mix(col,palette[3],.075*fiber)
        colors.append(col[:3]+(1.,))
    obj.data.materials.clear();obj.data.materials.append(g.M['lvf_painted_coat'])
    for polygon in obj.data.polygons:
        polygon.material_index=0
        polygon.use_smooth=True
    _colors(obj,colors)
    obj.data.update()
    obj['fur_surface']='Short groomed geometric relief; no projected artwork'
    obj['fur_maximum_relief']=.00135 if head else .00185


class _Surface:
    def __init__(self,obj):
        self.obj=obj
        positions=[obj.matrix_world@v.co for v in obj.data.vertices]
        self.tree=BVHTree.FromPolygons(positions,[list(p.vertices) for p in obj.data.polygons])
        self.kd=KDTree(len(positions))
        for i,p in enumerate(positions):self.kd.insert(p,i)
        self.kd.balance()
        self.names={group.index:group.name for group in obj.vertex_groups}

    def anchor(self,landmark,normal):
        p=Vector(landmark);n=Vector(normal).normalized()
        hit,_,_,_=self.tree.ray_cast(p+n*1.4,-n,2.8)
        if hit is None:
            nearest=self.tree.find_nearest(p)
            if nearest is None or nearest[0] is None:
                raise ValueError('Liora fur anchor cannot find anatomy')
            hit=nearest[0]
        return hit

    def skin(self,obj):
        """Copy anatomical groups, retaining the source's normalized blend."""
        cache={}
        for vertex in obj.data.vertices:
            _,index,_=self.kd.find(obj.matrix_world@vertex.co)
            groups=[(self.names[g.group],g.weight)
                    for g in self.obj.data.vertices[index].groups
                    if g.group in self.names and g.weight>1.e-7]
            groups=sorted(groups,key=lambda item:item[1],reverse=True)[:4]
            if not groups:
                raise ValueError('Fused Liora body needs weights before fur.build(g)')
            total=sum(weight for _,weight in groups)
            for name,weight in groups:
                if name not in cache:
                    cache[name]=obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
                cache[name].add([vertex.index],weight/total,'REPLACE')


def _bezier(points,t):
    a,b,c,d=(Vector(p) for p in points)
    s=1.-t
    return a*s**3+b*(3*s*s*t)+c*(3*s*t*t)+d*t**3


def _tuft(g,palette,name,points,width,depth,part,normal,steps=42,sides=32,
          tone=0.,surface=None,coat_grain=False):
    """Closed shallow fur clump with fine integrated grooves and a soft root.

    These short crescent forms have a low profile, not the rounded, large
    cross-section of pony hair and not a flat armor/leaf surface.
    """
    centers=[_bezier(points,i/steps) for i in range(steps+1)]
    previous=Vector(normal).normalized()
    verts,faces,colors=[],[],[]
    for i,c in enumerate(centers):
        t=i/steps
        tangent=(centers[min(steps,i+1)]-centers[max(0,i-1)]).normalized()
        n=previous-tangent*previous.dot(tangent)
        if n.length<1.e-6:
            alternate=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((0,1,0))
            n=alternate-tangent*alternate.dot(tangent)
        n.normalize();previous=n
        u=tangent.cross(n).normalized()
        profile=.0015+math.sqrt(max(0.,math.sin(math.pi*t)))*(1.-t*.58)
        for j in range(sides):
            a=TAU*j/sides
            outward=math.sin(a);lateral=math.cos(a)
            groove=(.5+.5*math.cos(7*a+.45*math.sin(t*3.1)))**8
            micro=math.sin(15*a+1.4*t)
            ridge=1.-.055*groove*math.sin(math.pi*t)+.006*micro
            position=c+u*(width*profile*lateral*ridge)+n*(depth*profile*outward*ridge)
            verts.append(tuple(position))
            light=max(0.,outward)
            col=_mix(palette[1],palette[2],.34+.37*light+tone)
            col=_mix(col,palette[3],.11*light*(.6+.4*math.sin(math.pi*t)))
            col=_mix(col,palette[0],.12*groove+.045*(1.-light))
            if coat_grain:
                # Tail wisps share the core's short-fiber coloration, avoiding
                # pale individual leaves standing out against a textured ball.
                fiber=max(0.,min(1.,.5+.68*_grain(position,n)))
                col=_mix(palette[0],palette[2],.50+.43*fiber)
                col=_mix(col,palette[3],.05*fiber)
            colors.append(col[:3]+(1.,))
    for i in range(steps):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides
            faces.append((a,a+sides,b+sides,b))
    root=len(verts);verts.append(tuple(centers[0]));colors.append(colors[0])
    tip=len(verts);verts.append(tuple(centers[-1]));colors.append(colors[-2])
    for j in range(sides):
        k=(j+1)%sides
        faces.append((root,j,k))
        faces.append((tip,steps*sides+k,steps*sides+j))
    obj=g.mesh('Liora_fur_'+name,verts,faces,'lvf_painted_coat',part)
    _colors(obj,colors)
    if surface is not None:surface.skin(obj)
    return obj


def _cotton_core(g,palette):
    """One coherent rounded puff with gently modeled spiral cotton grain."""
    center=Vector((0,1.52,1.43))
    sides=112;rings=76
    verts=[tuple(center+Vector((0,0,.480)))];colors=[palette[2]]
    for i in range(1,rings):
        b=math.pi*i/rings
        for j in range(sides):
            a=TAU*j/sides
            swirl=a+1.20*math.cos(b)
            coarse=.006*math.cos(5*swirl)*math.sin(b)**2
            fine=.0015*math.cos(31*swirl+7*b)*math.sin(b)
            radius=1.+coarse+fine
            p=center+Vector((.410*math.sin(b)*math.cos(a),
                             .440*math.sin(b)*math.sin(a),.480*math.cos(b)))*radius
            verts.append(tuple(p))
            fur=max(0.,min(1.,.5+.68*_grain(p,(p-center).normalized())))
            col=_mix(palette[0],palette[2],.50+.43*fur)
            col=_mix(col,palette[3],.05*fur)
            colors.append(col[:3]+(1.,))
    bottom=len(verts);verts.append(tuple(center-Vector((0,0,.480))));colors.append(palette[2])
    faces=[]
    for j in range(sides):faces.append((0,1+j,1+(j+1)%sides))
    for i in range(rings-2):
        for j in range(sides):
            a=1+i*sides+j;b=1+i*sides+(j+1)%sides
            faces.append((a,a+sides,b+sides,b))
    start=1+(rings-2)*sides
    for j in range(sides):faces.append((bottom,start+(j+1)%sides,start+j))
    obj=g.mesh('Liora_fur_cotton_tail_core',verts,faces,'lvf_painted_coat','tail')
    _colors(obj,colors)
    return obj


def build(g):
    """Apply the short coat and register Liora's groomed silhouette fur."""
    palette=_palette(g)
    body=_find(g,'liora_v2_body');head=_find(g,'liora_v2_head')
    _coat_relief(g,body,palette)
    _coat_relief(g,head,palette,head=True)
    body_surface=_Surface(body)
    made=[]

    def tuft(name,points,width,depth,part='head',normal=(0,-1,0),**kw):
        obj=_tuft(g,palette,name,points,width,depth,part,normal,**kw)
        made.append(obj)
        return obj

    # Broad, deeply overlapping cheek bundles with three unequal soft tips.
    # Shared buried roots keep them integrated rather than a white leaf comb.
    for s,side in ((-1,'R'),(1,'L')):
        for i,z in enumerate((2.12,2.255,2.405,2.55,2.685)):
            extension=(.30,.36,.39,.36,.29)[i]
            variation=1. if s>0 else .78
            root=Vector((s*(.555+variation*(.008,-.012,.016,-.006,.010)[i]),
                         -1.105+.024*i+variation*(.012,-.016,.008,-.011,.010)[i],
                         z+variation*(.010,-.009,.014,-.011,.008)[i]))
            # A small rigid turn changes the groom direction without making
            # any bundle longer or creating a more prominent pointed spike.
            angle=variation*(-.057,.043,-.034,.061,-.047)[i]*s
            axis=Vector((s*.25,-.95,.14)).normalized()
            offsets=[Vector((0,0,0)),Vector((s*.15,.057,-.012)),
                     Vector((s*(extension-.065),.19,.055+.011*i)),
                     Vector((s*extension,.315,.115+.009*i))]
            points=[root+v*math.cos(angle)+axis.cross(v)*math.sin(angle)
                    +axis*(axis.dot(v)*(1.-math.cos(angle))) for v in offsets]
            width=(.110,.131,.137,.122,.096)[i]*(.91,1.09,.96,1.13,.88)[i]
            depth=.052*(1.10,.90,1.05,.94,1.12)[i]
            tuft('cheek_'+side+'_%02d'%i,points,width,depth,
                 normal=(s*.68,-.73,.10),steps=52,sides=40,tone=.010)
            for split,offset in enumerate((-.054,.044)):
                pts=[root+Vector((0,-.006,offset*.35)),
                     points[1]+Vector((s*.008,-.012,offset*.58)),
                     points[2]+Vector((s*(.027 if split==0 else -.018),-.010,offset)),
                     points[3]+Vector((s*(.023 if split==0 else -.043),
                                       .013 if split==0 else -.028,offset))]
                tuft('cheek_'+side+'_soft_split_%02d_%d'%(i,split),pts,
                     width*.53,.027,normal=(s*.68,-.73,.10),
                     steps=40,sides=28,tone=.018 if split else -.015)

        # Two restrained side-muzzle wisps finish the jaw edge.
        for i in range(2):
            tuft('jaw_'+side+'_%02d'%i,[(s*(.38+.07*i),-1.38,2.05+.04*i),
                 (s*(.48+.08*i),-1.35,2.03+.04*i),
                 (s*(.58+.09*i),-1.29,2.08+.04*i),
                 (s*(.66+.09*i),-1.21,2.12+.04*i)],.044,.019,
                 normal=(s*.6,-.8,0),steps=36,sides=28)

    # Small swept forehead locks stop below the separately owned ear bases.
    for i,x in enumerate((-.27,-.14,.01,.15,.28)):
        z=3.035-.04*abs(x)/.28
        tuft('forehead_%02d'%i,[(x,-1.02,z-.07),(x-.01,-1.13,z+.055),
             (x+.045,-1.04,z+.13),(x+.11,-.94,z+.17)],.060,.026,
             normal=(0,-1,.4),steps=40,sides=32,tone=.025)

    # Fine cream brush at each inner ear base. Only added meshes are authored;
    # the finished ear surfaces and guard geometry remain owned by anatomy.
    for s,side in ((-1,'R'),(1,'L')):
        ear=_find(g,'liora_v2_cupped_ear_'+side.lower())
        ear_surface=_Surface(ear)
        for i in range(3):
            n=Vector((0,-1,.10)).normalized()
            a=ear_surface.anchor((s*(.408+.036*i),-.90,2.965+.047*i),n)-n*.016
            pts=[a,a+Vector((s*.022,-.037,.075)),
                 a+Vector((s*.060,-.026,.190)),a+Vector((s*.080,-.007,.260))]
            tuft('inner_ear_brush_'+side+'_%d'%i,pts,.054-i*.004,.029,
                 part='ear.'+side,normal=n,steps=42,sides=32,tone=.025)

    # The bib is attached to the measured front surface, with existing neck
    # blends copied onto every vertex. It remains shallow under the jewelry.
    for row,(z,xs) in enumerate(((1.91,(-.28,-.14,0,.14,.28)),
                               (1.73,(-.24,-.08,.08,.24)))):
        for i,x in enumerate(xs):
            n=Vector((x*.35,-1,.05)).normalized()
            a=body_surface.anchor((x,-1.14,z),n)-n*.018
            outward=(1 if x>0 else -1 if x<0 else 0)
            points=[a,a+Vector((outward*.018,-.038,-.058)),
                    a+Vector((outward*.025,-.045,-.148)),
                    a+Vector((outward*.045,-.024,-.205+.025*row))]
            tuft('bib_%d_%d'%(row,i),points,.063,.027,part='body',normal=n,
                 steps=42,sides=32,surface=body_surface,tone=.025)

    # Sparse short fringe at flank/haunch silhouettes. Fine surface relief,
    # not these tufts, carries the coat across the rest of the anatomy.
    for s,side in ((-1,'R'),(1,'L')):
        for i,(y,z) in enumerate(((-.20,1.40),(.18,1.53),(.47,1.45),(.77,1.31),
                                  (.86,1.07),(.70,.85),(.37,.79),(-.42,.82))):
            n=Vector((s,.12,.10)).normalized()
            a=body_surface.anchor((s*.69,y,z),n)-n*.010
            points=[a,a+Vector((s*.021,.034,-.035)),
                    a+Vector((s*.030,.079,-.074)),
                    a+Vector((s*.027,.105,-.124))]
            tuft('short_coat_'+side+'_%02d'%i,points,.037,.016,
                 part='body',normal=n,steps=32,sides=24,surface=body_surface)

    # Tail: a full cotton puff covered from every angle by closely fitted,
    # staggered spiral wisps. No bare front hemisphere or circular leaf wreath.
    made.append(_cotton_core(g,palette))
    center=Vector((0,1.52,1.43));rx,ry,rz=.410,.440,.480
    golden=math.pi*(3.-math.sqrt(5.))
    for i in range(48):
        y=1.-2.*(i+.5)/48
        ring=math.sqrt(1.-y*y);a=i*golden
        origin=Vector((ring*math.cos(a),y,ring*math.sin(a)))
        tangent=Vector((-origin.z,.30,origin.x))
        tangent-=origin*tangent.dot(origin)
        if tangent.length<.12:tangent=Vector((1,0,0))-origin*origin.x
        tangent.normalize()
        curl=origin.cross(tangent).normalized()
        points=[]
        length=.83+.16*math.sin(i*2.37)
        tip_lift=1.075+.010*math.sin(i*1.73)
        # Buried roots and a barely raised, broad middle merge into the core.
        # Only the tiny tapered end flutters above the cotton surface.
        for k,(arc,factor) in enumerate(((0,.930),(length/3,1.018),
                                        (2*length/3,1.035),(length,tip_lift))):
            direction=(origin*math.cos(arc)+tangent*math.sin(arc)
                       +curl*(.11*math.sin(arc)**2)).normalized()
            points.append(center+Vector((rx*direction.x,ry*direction.y,rz*direction.z))*factor)
        middle=(points[1]+points[2])*.5-center
        normal=Vector((middle.x/(rx*rx),middle.y/(ry*ry),middle.z/(rz*rz))).normalized()
        tuft('cotton_spiral_wisp_%02d'%i,points,.151+.014*math.sin(i*2.1),
             .021+.002*math.cos(i*1.7),part='tail',normal=normal,
             steps=60,sides=40,tone=.022*math.sin(i*.9),coat_grain=True)

    # Two small attached curls soften the upper silhouette, staying close to
    # the puff instead of returning the removed long crown spike.
    tuft('cotton_upper_flutter_L',[(0,1.48,1.855),(.03,1.57,1.918),
         (.08,1.63,1.950),(.08,1.72,1.909)],.075,.022,
         part='tail',normal=(0,.35,1),steps=52,sides=32,coat_grain=True)
    tuft('cotton_upper_flutter_R',[(-.18,1.50,1.828),(-.17,1.60,1.905),
         (-.11,1.69,1.925),(-.06,1.75,1.877)],.071,.021,
         part='tail',normal=(-.2,.35,1),steps=52,sides=32,coat_grain=True)

    return made

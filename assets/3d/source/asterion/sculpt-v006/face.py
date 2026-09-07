"""Asterion facial sculpture on the immutable v005 master.

Only the face changes. Original lids retain their center-scale presentation
animation; this is not an anatomical eyelid rig. No imagery is projected.
"""
import math
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

DEPENDENCIES = []


def points(obj):
    xyz = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', xyz)
    m = np.asarray(obj.matrix_world, dtype=float)
    return xyz.reshape(-1, 3).astype(float) @ m[:3, :3].T + m[:3, 3]


def write(obj, xyz):
    if not np.isfinite(xyz).all():
        raise ValueError('Nonfinite face geometry: ' + obj.name)
    inv = np.asarray(obj.matrix_world.inverted(), dtype=float)
    local = xyz @ inv[:3, :3].T + inv[:3, 3]
    obj.data.vertices.foreach_set('co', local.astype(np.float32).ravel())
    obj.data.update()


def smooth(a, b, value):
    t = np.clip((value-a)/(b-a), 0, 1)
    return t*t*(3-2*t)


def paint(obj, colors):
    attr = obj.data.color_attributes.get('AST_eye_color')
    if attr is None:
        attr = obj.data.color_attributes.new(name='AST_eye_color', type='FLOAT_COLOR', domain='POINT')
    attr.data.foreach_set('color', np.clip(colors, 0, 1).astype(np.float32).ravel())


def painted_material(g, name, roughness=.52):
    mat = g.material(name, 'FFFFFF', 0, roughness)
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Specular IOR Level'].default_value = .17
    attr = mat.node_tree.nodes.new('ShaderNodeVertexColor')
    attr.layer_name = 'AST_eye_color'
    mat.node_tree.links.new(attr.outputs['Color'], bsdf.inputs['Base Color'])
    return mat


def skin_colors(g, obj):
    xyz = points(obj)
    x, y, z = xyz.T
    base = np.array(g.color('0B2044'))
    colors = np.tile(base, (len(xyz), 1))
    # Broad anatomical pigment, not screen-facing highlights or random speckle.
    cheek = np.exp(-((np.abs(x)-.43)/.34)**2 - ((z-3.47)/.22)**2)
    lip = np.exp(-(x/.48)**4 - ((z-3.285)/.075)**2)
    front = 1-smooth(-1.70, -.90, y)
    colors[:, :3] *= (1 + .17*cheek*front - .17*lip*front)[:, None]
    return colors


def replace_mesh(obj, vertices, faces, material, rig, bone):
    old = obj.data
    mesh = bpy.data.meshes.new(obj.name + '_v006_surface')
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    mesh.update()
    obj.data = mesh
    obj.vertex_groups.clear()
    obj.vertex_groups.new(name=bone).add(list(range(len(vertices))), 1.0, 'REPLACE')
    write(obj, np.asarray(vertices))
    for poly in mesh.polygons:
        poly.use_smooth = True
    if not old.users:
        bpy.data.meshes.remove(old)


def apply(g, rig, kind):
    if kind != 'asterion':
        raise ValueError(kind)
    names = {o.name for o in g.ASSET if o.name in
        ('AST_Sculpted_head', 'AST_head_scale_sculpt', 'AST_temple_overlapping_lamellae', 'AST_rounded_nose')
        or o.name.startswith(('AST_cheek_scale_', 'AST_orbital_socket.', 'AST_living_eye.',
            'AST_upper_brow.', 'AST_lower_eyelid.', 'AST_closed_eyelid.',
            'AST_eye_catchlight.', 'AST_eye_pinlight.', 'AST_rounded_mouth.', 'AST_rounded_nostril.'))}
    edited = []
    skin = painted_material(g, 'Asterion_v006_anatomical_face_navy')
    ocular = painted_material(g, 'Asterion_v006_deep_azure_eyes', .35)
    ocular.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value = .045
    nose_mat = g.material('Asterion_v006_soft_nose', '091B39', 0, .50)
    nose_mat.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value = .12
    fields = []
    for sign, side in ((1, 'L'), (-1, 'R')):
        center = np.array(rig.data.bones['lid.'+side].head_local)
        n = np.array((sign*.45, -.892, .03)); n /= np.linalg.norm(n)
        u = np.array((sign*.893, .450, 0)); u /= np.linalg.norm(u)
        v = np.cross(n, u)
        if v[2] < 0: v = -v
        fields.append((side, center, u, v, n))
    # Move eye, closed lid, lash and the supporting skull through the same
    # centered field. This leaves the original lid transform origin untouched.
    for obj in g.ASSET:
        if obj.name not in names: continue
        before = points(obj); result = before.copy()
        surface = obj.name in ('AST_Sculpted_head', 'AST_head_scale_sculpt', 'AST_temple_overlapping_lamellae')
        orbital = any(token in obj.name for token in ('eye', 'brow', 'orbital'))
        if surface or orbital:
            delta = np.zeros_like(before)
            for side, center, u, v, n in fields:
                if orbital and not obj.name.endswith('.'+side): continue
                d = before-center; x, z, depth = d@u, d@v, d@n
                gain = np.ones(len(d)) if orbital else (1-smooth(1.0, 1.65, np.maximum(np.abs(x)/.35, np.abs(z)/.245))) * (1-smooth(.11, .30, np.abs(depth)))
                new_x = x * 1.075
                new_z = z * (1.15-.030*np.clip(np.abs(x)/.31, 0, 1)**2)
                delta += gain[:, None]*((new_x-x)[:, None]*u+(new_z-z)[:, None]*v)
            result += delta
        if surface or obj.name.startswith('AST_cheek_scale_'):
            front = 1-smooth(-1.70, -1.13, before[:, 1])
            lower = 1-smooth(3.40, 3.64, before[:, 2])
            cheek = np.exp(-((np.abs(before[:, 0])-.33)/.31)**2 - ((before[:, 2]-3.42)/.20)**2)
            result[:, 1] -= .048*cheek*front
            result[:, 2] += .035*(1-smooth(3.20, 3.40, before[:, 2]))*front
            result[:, 0] *= 1+.022*lower*front
        if obj.name.startswith('AST_upper_brow.'):
            # Reduce the former tubular brow cross-section, not its entire arc.
            if len(result) % 24 == 0:
                rings = result.reshape(-1, 24, 3)
                centers = rings.mean(axis=1)
                result = (centers[:, None, :] + (rings-centers[:, None, :])*.86).reshape(-1, 3)
        distance = float(np.linalg.norm(result-before, axis=1).max())
        if distance > 1e-7:
            write(obj, result)
            edited.append(dict(name=obj.name, operation='Centered larger ocular aperture with coherent supporting flesh; rounded cheek/chin field', max_displacement=distance))
        if surface or obj.name.startswith(('AST_cheek_scale_', 'AST_upper_brow.', 'AST_lower_eyelid.', 'AST_closed_eyelid.')):
            # A dedicated facial shader leaves all body/armor materials exact.
            for index in range(len(obj.data.materials)): obj.data.materials[index] = skin
            paint(obj, skin_colors(g, obj))
    head = bpy.data.objects['AST_Sculpted_head']
    hp = points(head)
    tree = BVHTree.FromPolygons([Vector(p) for p in hp], [list(f.vertices) for f in head.data.polygons])
    for side, center, u, v, n in fields:
        eye = bpy.data.objects['AST_living_eye.'+side]
        p = points(eye)
        c = p[:192].mean(axis=0)
        x, z = (p-c)@u, (p-c)@v
        ix, iz = (x+.025)/.246, (z+.012)/.261
        radius = np.hypot(ix, iz)
        pupil = np.hypot((x+.030)/.105, (z-.024)/.180)
        iris_t = np.clip(.49-z/.40, 0, 1)
        upper, lower = np.array(g.color('032044')), np.array(g.color('0098E1'))
        upper[:3] *= .60; lower[:3] *= .40
        iris = upper[None, :]*(1-iris_t[:, None]) + lower[None, :]*iris_t[:, None]
        angle = np.arctan2(iz, ix)
        fiber = .025*np.sin(angle*63+radius*18)+.018*np.sin(angle*109-radius*11)
        iris[:, :3] *= (1+fiber)[:, None]
        rim = smooth(.83, .99, radius)
        iris = iris*(1-rim[:, None]) + np.array(g.color('062744'))*rim[:, None]
        sclera = np.tile(np.array(g.color('C9CBB9')), (len(p), 1))
        sclera[:, :3] *= (1-.30*smooth(.00, .18, z))[:, None]
        colors = np.where((radius<1)[:, None], iris, sclera)
        pupil_edge = smooth(.945, 1.01, pupil)
        colors = np.array(g.color('010813'))*(1-pupil_edge[:, None])+colors*pupil_edge[:, None]
        colors[:, 3] = 1
        eye.data.materials[0] = ocular
        paint(eye, colors)
        edited.append(dict(name=eye.name, operation='Broader graded azure iris, larger dark pupil, restrained warm sclera and thin limbal ring', max_displacement=0))
        lid = bpy.data.objects['AST_closed_eyelid.'+side]
        cover = c+(p-c)*1.105+n*.019
        replace_mesh(lid, cover, [list(f.vertices) for f in eye.data.polygons], skin, rig, 'lid.'+side)
        paint(lid, skin_colors(g, lid))
        edited.append(dict(name=lid.name, operation='Closed cover refitted to the enlarged actual eye with unchanged original lid pivot and action', max_displacement=0, new_vertices=len(cover)))
        # Blend the aperture physically into the existing carved skull. The
        # outer edge is ray-seated on actual skin, not a flat raised oval band.
        outer = p[-192:]
        # The lateral temple bends away sharply: a circular 1.5x collar would
        # extend outside the skull there. Widen only toward bridge/forehead.
        radial=1.50-.33*smooth(0,.15,(outer-c)@u)
        edge = c+(outer-c)*radial[:,None]
        anchors = []
        for q in edge:
            hit, normal, _, distance = tree.ray_cast(Vector(q+n*.55), Vector(-n), 1.0)
            if hit is None or distance > .74:
                hit, normal, _, _ = tree.find_nearest(Vector(q))
            if hit is None: raise ValueError('Missing orbital skin support')
            anchors.append(np.asarray(hit)-np.asarray(normal)*.014)
        anchors = np.array(anchors)
        # Smooth only adjacent support samples and bury the root. Retaining
        # the actual three-dimensional hits keeps the outer corner on skin.
        anchors=sum(np.roll(anchors,k,axis=0)*w for k,w in ((-2,1),(-1,2),(0,3),(1,2),(2,1)))/9-n*.025
        verts, faces = [], []
        for row in range(13):
            t=row/12; blend=t*t*(3-2*t)
            ring=(outer+n*.004)*(1-blend)+anchors*blend+n*(.007*math.sin(math.pi*t))
            verts.extend(ring)
        for row in range(12):
            for j in range(192):
                a=row*192+j; b=row*192+(j+1)%192
                faces.append((a,b,b+192,a+192))
        # Ring rows advance outwards while columns advance counterclockwise:
        # their raw cross product points inward, unlike the central eye disk.
        if np.dot(np.cross(u,v),n)>0: faces=[tuple(reversed(f)) for f in faces]
        socket=bpy.data.objects['AST_orbital_socket.'+side]
        replace_mesh(socket,verts,faces,skin,rig,'head')
        paint(socket,skin_colors(g,socket))
        edited.append(dict(name=socket.name,operation='Continuous twelve-ring skin-seated orbital transition replacing the raised oval socket',max_displacement=0,new_vertices=len(verts)))
        # The inherited lower rim is an open sweep. Close its two exposed ends
        # so side views do not look into a dark tube at the outer canthus.
        lower_lid = bpy.data.objects['AST_lower_eyelid.'+side]
        lp = points(lower_lid).tolist()
        polygons = [list(f.vertices) for f in lower_lid.data.polygons]
        edges = {}
        for polygon in polygons:
            for a,b in zip(polygon,polygon[1:]+polygon[:1]):
                key=tuple(sorted((a,b)))
                edges.setdefault(key,[]).append((a,b))
        boundary={pair[0]:pair[1] for pairs in edges.values() if len(pairs)==1 for pair in pairs}
        while boundary:
            start=next(iter(boundary));loop=[start];current=boundary.pop(start)
            while current!=start:
                loop.append(current)
                if current not in boundary: raise ValueError('Non-loop lower lid boundary')
                current=boundary.pop(current)
            mid=len(lp);lp.append(np.asarray([lp[i] for i in loop]).mean(axis=0).tolist())
            for a,b in zip(loop,loop[1:]+loop[:1]): polygons.append([b,a,mid])
        replace_mesh(lower_lid,lp,polygons,skin,rig,'head')
        paint(lower_lid,skin_colors(g,lower_lid))
        edited.append(dict(name=lower_lid.name,operation='Closed lower canthus sweep ends',max_displacement=0,new_vertices=len(lp)))
        cornea=BVHTree.FromPolygons([Vector(q) for q in p],[list(f.vertices) for f in eye.data.polygons])
        for prefix, factor in (('AST_eye_catchlight.', .92), ('AST_eye_pinlight.', .75)):
            obj=bpy.data.objects[prefix+side]; original=points(obj); gp=original.copy(); gc=gp.mean(axis=0)
            gp=gc+(gp-gc)*factor
            for i,q in enumerate(gp):
                hit,_,_,_=cornea.find_nearest(Vector(q))
                if hit is None: raise ValueError('Unseated corneal glint')
                gp[i]=np.asarray(hit)+n*.001
            write(obj,gp)
            edited.append(dict(name=obj.name,operation='Small cornea-seated highlights underneath the preserved closing lid',max_displacement=float(np.linalg.norm(gp-original,axis=1).max())))
    # A softly rounded three-dimensional nose instead of a thin polygonal badge.
    nose=bpy.data.objects['AST_rounded_nose']
    verts,faces=[],[]
    rows,sides=48,96
    for row in range(rows+1):
        lat=-math.pi/2+math.pi*row/rows
        rr=max(1e-6,math.cos(lat))
        for j in range(sides):
            theta=math.tau*j/sides
            xx=math.cos(theta);zz=math.sin(theta)
            verts.append((.168*rr*xx*(.82+.18*zz), -2.005-.080*math.sin(lat),
                3.486+rr*(.076*zz+.015*xx*xx)))
    for row in range(rows):
        for j in range(sides):
            a=row*sides+j;b=row*sides+(j+1)%sides
            faces.append((a,b,b+sides,a+sides))
    replace_mesh(nose,verts,faces,nose_mat,rig,'head')
    nose_tree=BVHTree.FromPolygons([Vector(q) for q in verts],faces)
    edited.append(dict(name=nose.name,operation='Rounded triangular nasal volume with inset root and convex front instead of a thin badge',max_displacement=0,new_vertices=len(verts)))
    for sign,side in ((1,'L'),(-1,'R')):
        obj=bpy.data.objects['AST_rounded_nostril.'+side]
        p=points(obj);before=p.copy();c=p.mean(axis=0)
        hit,normal,_,_=nose_tree.ray_cast(Vector((sign*.111,-3,3.475)),Vector((0,1,0)))
        if hit is None: raise ValueError('Missing nasal support')
        target=np.asarray(hit)+np.asarray(normal)*.001
        p=target+(p-c)*np.array((.55,.9,.7));write(obj,p)
        edited.append(dict(name=obj.name,operation='Nares tucked into the nasal alae rather than freestanding cheek dots',max_displacement=float(np.linalg.norm(p-before,axis=1).max())))
        mouth=bpy.data.objects['AST_rounded_mouth.'+side]
        centers,normals=[],[]
        for t in np.linspace(0,1,73):
            x=sign*.373*t;z=3.354-.028*math.sin(math.pi*t)+.040*t*t
            hit,normal,_,_=tree.ray_cast(Vector((x,-3,z)),Vector((0,1,0)))
            if hit is None: raise ValueError('Unsupported smile')
            centers.append(np.asarray(hit)+np.asarray(normal)*.002)
            normals.append(np.asarray(normal))
        verts,faces=[],[]
        for i,(c,n) in enumerate(zip(centers,normals)):
            tangent=centers[min(i+1,72)]-centers[max(0,i-1)]
            tangent/=np.linalg.norm(tangent)
            across=np.cross(tangent,n);across/=np.linalg.norm(across)
            radius=.002+.005*math.sin(math.pi*(.08+.84*i/72))
            for j in range(12):
                a=math.tau*j/12
                verts.append(c+radius*(math.cos(a)*n+math.sin(a)*across))
        for i in range(72):
            for j in range(12):
                a=i*12+j;b=i*12+(j+1)%12
                faces.append((a,b,b+12,a+12))
        replace_mesh(mouth,verts,faces,mouth.data.materials[0],rig,'head')
        edited.append(dict(name=mouth.name,operation='Gently lifted volumetric lip arcs seated on the rounded muzzle without collapsing tube radii',max_displacement=0,new_vertices=len(verts)))
    return dict(notes='Face-only study: larger integrated azure eyes, skin-seated orbital transitions, lighter brow volume, softly rounded cheeks/chin, shaped nasal planes and a restrained lifted mouth. Head mane remains omitted.',
        edited_objects=edited,face_objects=sorted(names),removed_face_objects=[],added_base_clothing=[],
        face_frame=dict(center=[0,-1.15,3.80],span=[2.0,1.90,1.65]),
        head_mane_omitted=True,original_lid_pivots_unchanged=True,
        animation_limit='Original uniform-scale eyelid closure is retained, not anatomically reauthored.')

"""Nyra/Fenn likeness pass: primary hair volumes, face and continuous fur.

Operates on a loaded immutable v003 master. No bones, animation data or image
projection are authored. New sculpt parts use the original rigid part weights.
"""
from pathlib import Path
import importlib.util
import math
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = ROOT / 'cat/sculpt-v002/nyra_detail.py'
DEPENDENCIES = [HELPER_PATH]
spec = importlib.util.spec_from_file_location('likeness_feline_sculpt_tools', HELPER_PATH)
art = importlib.util.module_from_spec(spec)
spec.loader.exec_module(art)


def coordinates(obj):
    values = np.empty(len(obj.data.vertices) * 3, dtype=np.float64)
    obj.data.vertices.foreach_get('co', values)
    m = np.array(obj.matrix_world)
    return values.reshape((-1, 3)) @ m[:3, :3].T + m[:3, 3]


def write(obj, values):
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite sculpt coordinates: ' + obj.name)
    m = np.array(obj.matrix_world.inverted())
    local = values @ m[:3, :3].T + m[:3, 3]
    obj.data.vertices.foreach_set('co', local.ravel())
    obj.data.update()


def change(obj, values, description, edits):
    delta = float(np.linalg.norm(values - coordinates(obj), axis=1).max())
    write(obj, values)
    edits.append(dict(name=obj.name, operation=description, max_displacement=delta))


def palette(g, *hexes):
    return tuple(g.color(h) for h in hexes)


def toolkit(g, kind):
    a = art.Art.__new__(art.Art)
    a.g = g
    a.prefix = ('nyra' if kind == 'cat' else 'fenn') + '_v4'
    old = 'nyra_v2' if kind == 'cat' else 'fenn_v2'
    a.keys = {key: old + '_' + key for key in ('coat', 'ink', 'white', 'nose', 'metal', 'metal_light')}
    a.keys['paint'] = old + '_painted_coat'
    for material in bpy.data.materials:
        g.M[material.name.removeprefix('AST_')] = material
    # The source helpers pass undecorated dictionary keys to the toolkit.
    for key in a.keys.values():
        if key not in g.M:
            found = next((m for m in bpy.data.materials if m.name in (key, 'AST_' + key)), None)
            if found is None:
                raise ValueError('Missing existing painted sculpt material: ' + key)
            g.M[key] = found
    return a


def attach(obj, rig, component='body'):
    part = str(obj.get('ast_part', 'body'))
    if part not in rig.data.bones:
        raise ValueError('Unknown original bone: ' + part)
    obj['asterion_component'] = component
    obj.parent = rig
    group = obj.vertex_groups.get(part) or obj.vertex_groups.new(name=part)
    group.add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')
    modifier = obj.modifiers.new('Original presentation rig', 'ARMATURE')
    modifier.object = rig
    return obj


def remove(g, selectors, edits):
    for obj in list(g.ASSET):
        if any(s in obj.name for s in selectors):
            edits.append(dict(name=obj.name, operation='Replaced by a newly shaped continuous sculpt family', max_displacement=0))
            g.ASSET.remove(obj)
            bpy.data.objects.remove(obj, do_unlink=True)


def catmull(points, samples):
    points = np.asarray(points, dtype=float)
    result = []
    for t in np.linspace(0, len(points) - 1, samples + 1):
        i = min(len(points) - 2, int(t)); f = t - i
        p0, p1, p2, p3 = points[max(0, i - 1)], points[i], points[i + 1], points[min(len(points) - 1, i + 2)]
        result.append(.5 * ((2 * p1) + (-p0 + p2) * f + (2*p0 - 5*p1 + 4*p2 - p3)*f*f + (-p0 + 3*p1 - 3*p2 + p3)*f*f*f))
    return [Vector(v) for v in result]


def volume(a, name, points, sizes, pal_fn, part, normal, rows=168, sides=64):
    """Closed curved fur mass with long-flow relief, never repeated fur tiles."""
    centers = catmull(points, rows)
    sizes = catmull([(w, d, 0) for w, d in sizes], rows)
    verts, colors, faces, frames = [], [], [], []
    previous = Vector(normal).normalized()
    for i, center in enumerate(centers):
        t = i / rows
        tangent = (centers[min(rows, i+1)] - centers[max(0, i-1)]).normalized()
        n = previous - tangent * previous.dot(tangent)
        if n.length < 1e-6:
            n = Vector((0, 0, 1)) - tangent * tangent.z
        n.normalize(); previous = n
        u = tangent.cross(n).normalized(); frames.append((tangent, u, n))
        for j in range(sides):
            angle = math.tau * j / sides
            radial = u * math.cos(angle) + n * math.sin(angle)
            groove = (.5 + .5*math.cos(13*angle + .8*math.sin(t*5)))**7
            broad = math.cos(5*angle - t*8)
            fade = math.sin(math.pi*t)**.5
            gain = 1 + fade*(.024*broad - .044*groove)
            p = center + (u*max(.0004, sizes[i].x)*math.cos(angle) + n*max(.0004, sizes[i].y)*math.sin(angle))*gain
            verts.append(p)
            pal = pal_fn(t, radial)
            f = .61 + .09*max(0, radial.z) + .055*broad - .07*groove
            color = art.mix(pal[0], pal[2], f)
            color = art.mix(color, pal[3], .12*max(0, broad)*fade)
            colors.append(color)
    for i in range(rows):
        for j in range(sides):
            k = i*sides+j; l = i*sides+(j+1)%sides
            faces.append((k, k+sides, l+sides, l))
    faces += [tuple(reversed(range(sides))), tuple(rows*sides+j for j in range(sides))]
    obj = a.mesh(name, verts, faces, 'paint', part)
    a.colors(obj, colors)
    return obj, centers, sizes, frames


def flowing_color(a, obj, pal, strength=.30):
    """Paint long coherent highlight/shadow ribbons into a volumetric lock."""
    mesh=obj.data
    ids=list(mesh.polygons[0].vertices)
    sides=max(abs(ids[(i+1)%4]-ids[i]) for i in range(4))
    rings=(len(mesh.vertices)-2)//sides
    if rings*sides+2 != len(mesh.vertices):
        raise ValueError('Unexpected sculpt lock topology')
    values=[]
    for i in range(rings):
        t=i/(rings-1);fade=math.sin(math.pi*t)**.5
        for j in range(sides):
            angle=math.tau*j/sides
            broad=.5+.5*math.sin(angle*3+.15*math.sin(t*5))
            fiber=(.5+.5*math.cos(angle*17+t*.9))**4
            shade=.38+.40*max(0,math.sin(angle))-.18*(1-broad)*fade-.12*fiber*fade
            color=art.mix(pal[0],pal[2],shade)
            color=art.mix(color,pal[3],strength*broad**4*fade)
            color=art.mix(pal[0],color,.28+.72*art.smooth(t/.44))
            values.append(color)
    values += [values[0],values[-1]]
    a.colors(obj,values)


def tail_strands(a, rig, prefix, centers, sizes, frames, palette_fn, angle_offsets, count=9):
    """Long overlapping surface-parametric strands, rather than short plates."""
    rows=len(centers)-1
    for strand, base_angle in enumerate(angle_offsets):
        for i in range(count):
            start=.10+i*.078+.013*math.sin(strand*3+i)
            end=min(.98,start+.21+.025*math.sin(i+strand*2))
            control=[];normals=[]
            for k in range(25):
                f=k/24;t=start+(end-start)*f;idx=min(rows-1,int(t*rows));blend=t*rows-idx
                center=centers[idx].lerp(centers[idx+1],blend)
                sz=sizes[idx].lerp(sizes[idx+1],blend)
                tan,u,n=frames[idx]
                angle=base_angle+.15*math.sin(t*5+strand)+.07*f
                radial=(u*math.cos(angle)+n*math.sin(angle)).normalized()
                # Embedded roots, shallow continuous top, tapered free tip.
                lift=-.018+.034*math.sin(math.pi*f)+.028*f**5
                control.append(center+u*sz.x*math.cos(angle)+n*sz.y*math.sin(angle)+radial*lift)
                normals.append(radial)
            pal=palette_fn((start+end)*.5,normals[12])
            obj=a.lock(prefix+'_'+str(strand)+'_'+str(i),control,.047+(i%3)*.007,.017,pal,'tail',
                normal=normals[0],steps=62,sides=28,root_palette=pal)
            flowing_color(a,obj,pal,.15)
            attach(obj,rig)


def noise_field(points):
    """Vectorized, continuous deterministic value noise for baked coat color."""
    cell=np.floor(points).astype(np.int64);f=points-cell;f=f*f*(3-2*f)
    value=np.zeros(len(points))
    for x in (0,1):
        for y in (0,1):
            for z in (0,1):
                c=cell+np.array((x,y,z))
                h=np.sin(c[:,0]*127.1+c[:,1]*311.7+c[:,2]*74.7)*43758.5453123
                h-=np.floor(h)
                weight=(f[:,0] if x else 1-f[:,0])*(f[:,1] if y else 1-f[:,1])*(f[:,2] if z else 1-f[:,2])
                value+=weight*h
    return value


def coat_color(g,kind):
    prefix='AST_nyra_v2_' if kind=='cat' else 'AST_fenn_v2_'
    records=[]
    for obj in g.ASSET:
        if not (obj.name in (prefix+'body',prefix+'head') or
                (obj.name.startswith(prefix+'eye_') and obj.name.endswith(('_skin_annulus','_closed_lid')))):
            continue
        attr=obj.data.color_attributes.get('AST_eye_color')
        if attr is None:
            continue
        p=coordinates(obj)
        q=p*np.array((49.,43.,16.))
        q[:,0]+=.8*np.sin(p[:,2]*9)+.4*np.sin(p[:,1]*13)
        long=noise_field(q)
        fine=noise_field(p*np.array((97.,91.,31.)))
        broad=noise_field(p*6.5)
        gain=.60+.49*long+.18*fine+.18*broad
        values=np.empty(len(attr.data)*4);attr.data.foreach_get('color',values)
        values=values.reshape((-1,4));before=values.copy()
        values[:,:3]*=gain[:,None]
        if kind=='cat':
            values[:,:3]*=np.array((1.16,1.02,.89))
        else:
            values[:,:3]*=np.array((1.0,.96,.86))
        attr.data.foreach_set('color',np.clip(values,0,1).ravel())
        records.append(dict(name=obj.name,operation='Baked directional painterly coat color',
            maximum_linear_color_difference=float(np.max(np.abs(values-before)))))
    return records


def clear_pendant(g, edits):
    """Move the complete old pendant in front of the fuller new breast fur.

    A conservative projected-footprint bound provides actual depth clearance,
    including the bezel tips. No fur is deleted or hidden beneath the outfit.
    The original hanging tab is reconnected with its collar-side ring fixed.
    """
    disk=bpy.data.objects['AST_fenn_v2_navy_celestial_medallion']
    normal=np.array(Vector((0,-1,-.08)).normalized())
    across=np.array((1.,0.,0.))
    up=np.cross(normal,across)
    center=coordinates(disk).mean(axis=0)
    pendant=[o for o in g.ASSET if o==disk or o.name.startswith('AST_fenn_v2_medallion_')]
    fur=[o for o in g.ASSET if o.name.startswith(('AST_fenn_v4_continuous_cream_breast',
                                               'AST_fenn_v4_overlapping_breast_lock_'))]
    fur_points=np.concatenate([coordinates(o) for o in fur])
    relative=fur_points-center
    mask=((relative@across)/.289)**2+((relative@up)/.351)**2 <= 1
    if not mask.any():
        raise ValueError('No breast fur under the original pendant footprint')
    maximum_fur_depth=float((fur_points[mask]@normal).max())
    original_pendant_depth=min(float((coordinates(o)@normal).min()) for o in pendant)
    margin=.024
    distance=max(0., maximum_fur_depth+margin-original_pendant_depth)
    if distance>.35:
        raise ValueError('Unexpected pendant clearance: inspect breast geometry')
    offset=normal*distance
    for obj in pendant:
        change(obj,coordinates(obj)+offset,'Complete pendant family moved forward for measured fur clearance',edits)
    tab=bpy.data.objects['AST_fenn_v2_collar_hanging_tab']
    values=coordinates(tab)
    if len(values)!=270:
        raise ValueError('Unexpected original suspension tab topology')
    weight=np.repeat(np.linspace(0,1,45),6)
    weight=weight*weight*(3-2*weight)
    change(tab,values+weight[:,None]*offset,'Suspension tab reconnected to moved loop; collar-side ring retained',edits)
    fixed_ring_error=float(np.max(np.abs(coordinates(tab)[:6]-values[:6])))
    if fixed_ring_error>1e-7:
        raise ValueError('The original collar-side tab attachment moved')
    final_depth=min(float((coordinates(o)@normal).min()) for o in pendant)
    measured=final_depth-maximum_fur_depth
    if measured<margin-1e-5:
        raise ValueError('Pendant and fur lack the required projected clearance')
    return dict(method='Conservative projected ellipse and front/back support-plane separation',
        ellipse_radii=[.289,.351],footprint_fur_vertices=int(mask.sum()),
        normal=normal.tolist(),family=[o.name for o in pendant],translation=offset.tolist(),
        translation_distance=distance,required_clearance=margin,measured_clearance=measured,
        original_tab_collar_ring_unchanged=fixed_ring_error<=1e-7,
        tab_collar_ring_maximum_error=fixed_ring_error,bib_deleted_or_hidden=False)


def ocular(g, kind, edits):
    prefix, zc, width, height = ('nyra_v2', 2.50, .54, .47) if kind == 'cat' else ('fenn_v2', 2.515, .53, .49)
    # The same smooth field moves the cut opening, orbital annulus and every
    # ocular surface, including the original closed lid and its lash.
    for obj in g.ASSET:
        if not (obj.name == 'AST_' + prefix + '_head' or '_eye_' in obj.name):
            continue
        p = coordinates(obj)
        weight = np.clip((-.95-p[:, 1])/.22, 0, 1)
        weight *= np.exp(-((p[:, 2]-zc)/.42)**6)
        weight *= np.clip((np.abs(p[:, 0])-.10)/.17, 0, 1)
        amount = .15 if kind == 'cat' else .07
        p[:, 2] += (-(p[:, 2]-zc)*amount + (np.abs(p[:, 0])-.42)*(.12 if kind == 'cat' else .025))*weight
        change(obj, p, 'Coherent expressive orbital shaping including original blink lid', edits)
    for sign, side in ((1, 'L'), (-1, 'R')):
        obj = bpy.data.objects['AST_' + prefix + '_eye_' + side]
        p = coordinates(obj)
        n = Vector((sign*.53, -.847, .025)).normalized()
        u = Vector((0, 0, 1)).cross(n).normalized(); v = n.cross(u)
        center = p[:144].mean(axis=0)
        xy = p - center
        x, z = xy @ np.array(u), xy @ np.array(v)
        iris_r = np.sqrt((x/(width*.408))**2 + ((z+height*.008)/(height*(.377 if kind == 'cat' else .411)))**2)
        pupil_r = np.sqrt((x/(width*(.178 if kind == 'cat' else .195)))**2 + ((z-height*.055)/(height*.251))**2)
        angle = np.arctan2(z/height, x/width)
        upper = np.array(g.color('052820' if kind == 'cat' else '081833'))
        lower = np.array(g.color('16AD79' if kind == 'cat' else '258EC7'))
        f = np.clip(.50 - z/(height*.58), 0, 1)
        colors = upper + (lower-upper)*f[:, None]
        spokes = .86 + .17*np.sin(angle*47 + iris_r*16) + .09*np.cos(angle*89-iris_r*12)
        spoke_mask = np.clip((iris_r-.36)/.2, 0, 1)*np.clip((1-iris_r)/.06, 0, 1)
        colors[:, :3] *= (1 + (spokes-1)*spoke_mask)[:, None]
        rim = np.clip((iris_r-.88)/.105, 0, 1)
        colors[:, :3] *= (1-.65*rim)[:, None]
        black = np.array(g.color('02090D'))
        pm = np.clip((pupil_r-.955)/.045, 0, 1)
        colors = black + (colors-black)*pm[:, None]
        colors[iris_r > 1.01] = np.array(g.color('EEE9D8'))
        colors[:, 3] = 1
        attr = obj.data.color_attributes.get('AST_eye_color')
        attr.data.foreach_set('color', np.clip(colors, 0, 1).ravel())
        obj['likeness_iris'] = 'Authored radial fibers, darker upper iris, narrow oval pupil, retained catchlights'


def cat(a, rig, edits):
    g = a.g
    coat = palette(g, '111314', '222525', '424541', '6C6F69')
    silver = palette(g, '171B1D', '3C4549', '69757B', 'B6C0C4')
    remove(g, ('silver_crest_', 'crest_undercoat_', 'ear_inner_brush_', 'continuous_plume_tail',
               'plume_edge_bundle_', 'tail_copper_sweep_'), edits)
    # Forehead-rooted diagonally swept locks. Unequal heights form the reference
    # flame crest instead of the previous horizontal row of stubby blades.
    for i, data in enumerate([
        (-.31,-1.25,2.86, -.39,-.25,3.58,.155),
        (-.08,-1.31,2.87, .20,-.03,3.88,.218),
        (.12,-1.29,2.89, .58,.01,3.65,.202),
        (.33,-1.15,2.88, .77,.03,3.42,.165),
        (-.44,-.99,2.87, -.48,.04,3.47,.13),
        (.02,-.73,3.00, .41,.16,3.61,.17),
        (-.25,-.63,2.94, -.05,.30,3.46,.15)]):
        x,y,z,xx,yy,zz,w = data
        if i < 4:
            y += .06
            z += .12
        for under in (False,):
            offset = .035 if under else 0
            obj = a.lock(('crest_shadow_' if under else 'silver_flame_')+str(i),
                [(x,y+offset,z-.025 if under else z), (x-.035,y-.010,z+.38),
                 (xx-.10, yy-.18, zz-.12), (xx, yy, zz)],
                w*(1.03 if under else .91), .072 if under else .070,
                coat if under else silver, steps=88, sides=44, root_palette=coat)
            flowing_color(a,obj,silver,.28)
            attach(obj, rig)
    for obj in list(g.ASSET):
        if 'cupped_rust_ear_' not in obj.name:
            continue
        sign = 1 if obj.name.endswith('_L') else -1
        p = coordinates(obj); before = p.copy()
        root = np.array((sign*.53,-.63,2.86)); tip = np.array((sign*1.045,-.31,3.68))
        tvec = (tip-root)/np.linalg.norm(tip-root)
        t = np.clip((p-root) @ tvec / np.linalg.norm(tip-root),0,1)
        line = root + t[:,None]*(tip-root)
        # Sharper triangular taper, broader root, concave side silhouette.
        factor = 1.18-.55*t
        p = line + (p-line)*factor[:,None]
        p[:,2] += .07*t
        change(obj,p,'Triangular feline ear outline with sharper tapered tip',edits)
        side = 'L' if sign > 0 else 'R'
        for i in range(5):
            r=(sign*(.61+i*.050),-.648,2.97+i*.062)
            obj = a.lock('silver_ear_brush_'+side+str(i), [r,
                (r[0]+sign*.085,r[1]-.025,r[2]+.03),
                (r[0]+sign*.145,r[1]+.008,r[2]+.084),
                (r[0]+sign*.19,r[1]+.055,r[2]+.105)],
                .051,.024,silver,'ear.'+side,steps=44,sides=28,root_palette=coat)
            attach(obj,rig)
    # Bring the formerly blue-gray cheek streaks into the reference's silver.
    for obj in list(g.ASSET):
        if not any(s in obj.name for s in ('cheek_fan_', 'cheek_split_', 'outer_dark_ruff_')):
            continue
        p = coordinates(obj); center=p.mean(axis=0)
        side = 1 if center[0]>0 else -1
        t=np.clip((np.abs(p[:,0])-.56)/.40,0,1)
        p[:,1] += .09*t; p[:,2] += .04*t
        change(obj,p,'Rearward curved cheek flow, preserving embedded roots',edits)
        if 'cheek_split_' in obj.name or any(obj.name.endswith(str(i)) for i in (1,3,5)):
            attr=obj.data.color_attributes.get('AST_eye_color')
            if attr:
                values=np.empty(len(attr.data)*4);attr.data.foreach_get('color',values)
                values=values.reshape((-1,4));values[:,:3] *= np.array((2.00,1.73,1.40))
                attr.data.foreach_set('color',np.clip(values,0,1).ravel())
    oldnose=bpy.data.objects['AST_nyra_v2_triangular_copper_nose']
    p=coordinates(oldnose); c=p.mean(axis=0);p=c+(p-c)*np.array((.74,.92,.66));p[:,2]+=.018
    change(oldnose,p,'Smaller softly rounded feline nose',edits)
    nose_mat=oldnose.data.materials[0]
    nose_mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=g.color('9B5838')
    points=[(0,1.00,1.32),(.05,1.50,1.44),(.14,1.95,1.97),(.16,2.37,2.50),
        (.13,2.80,2.48),(.10,3.10,2.12),(.05,3.09,1.76),(0,2.94,1.37),(0,3.11,1.20),(0,3.29,1.35)]
    sizes=[(.18,.20),(.27,.285),(.35,.31),(.355,.325),(.335,.31),(.285,.29),(.24,.245),(.17,.18),(.105,.125),(.001,.001)]
    def color(t,n):
        amount=.78*art.smooth((t-.20)/.18)*(1-art.smooth((t-.62)/.18))*art.smooth((n.z+.25)/.7)
        return tuple(art.mix(d,l,amount) for d,l in zip(coat,silver))
    core, centers, widths, frames=volume(a,'sculpted_s_plume',points,sizes,color,'tail',(1,0,0),rows=220,sides=88)
    attach(core,rig)
    tail_strands(a,rig,'plume_surface_flow',centers,widths,frames,color,
        (.40,.94,1.43,2.00,3.82,4.36,4.88,5.40),count=8)
    for side,sign in (('L',1),('R',-1)):
        for j in range(2):
            pts=[];normals=[]
            for i in range(72):
                t=.28+j*.065+.20*i/71;idx=int(t*220);_,u,n=frames[idx]
                angle=sign*(math.pi/2+.08-.45*i/71)
                radial=u*math.cos(angle)+n*math.sin(angle)
                pts.append(centers[idx]+u*(widths[idx].x+.008)*math.cos(angle)+n*(widths[idx].y+.008)*math.sin(angle))
                normals.append(radial)
            obj=a.ribbon('tail_copper_flame_'+side+str(j),pts,normals,.034,'tail',height_scale=.48)
            attach(obj,rig,'armor')


def dog(a, rig, edits):
    g=a.g
    golden=palette(g,'75400D','B26D18','E7A945','FFDA82')
    cream=palette(g,'AF8950','DEC38B','F7E4B7','FFF2CF')
    brown=palette(g,'20170D','49321B','7A522C','AA7B45')
    remove(g,('plush_floppy_ear_','ear_flow_','ear_root_wisp_','cream_bib_',
        'full_curled_tail','crown_flick_','cheek_fluff_'),edits)
    body=bpy.data.objects['AST_fenn_v2_body'];head=bpy.data.objects['AST_fenn_v2_head']
    for obj in g.ASSET:
        if obj==head or 'gentle_smile_' in obj.name:
            p=coordinates(obj)
            amount=np.clip((2.16-p[:,2])/.27,0,1)*np.clip((-.78-p[:,1])/.38,0,1)
            p[:,2]+=.055*amount
            change(obj,p,'Softer lifted lower jaw exposing the original collar',edits)
    nose=bpy.data.objects['AST_fenn_v2_soft_triangular_nose'];center=coordinates(nose).mean(axis=0)
    for obj in g.ASSET:
        if obj==nose or obj.name.startswith('AST_fenn_v2_nostril_'):
            p=coordinates(obj);p=center+(p-center)*np.array((1.13,1.0,1.10))
            change(obj,p,'Broader rounded puppy nose including coherent nostrils',edits)
    nose.data.materials[0].node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=g.color('473019')
    support=art.Surface(body);face=art.Surface(head)
    for sign,side in ((1,'L'),(-1,'R')):
        def ear_color(t,n):
            f=art.smooth((t-.07)/.45)
            return tuple(art.mix(a,b,f) for a,b in zip(golden,brown))
        points=[(sign*.48,-.67,2.88),(sign*.73,-.62,2.98),(sign*.965,-.67,2.78),
            (sign*1.04,-.74,2.48),(sign*1.13,-.82,2.16),(sign*1.26,-.81,2.015),(sign*1.40,-.76,2.06)]
        sizes=[(.105,.115),(.22,.17),(.295,.18),(.31,.17),(.25,.14),(.14,.083),(.001,.001)]
        core,centers,widths,frames=volume(a,'flowing_drop_ear_'+side,points,sizes,ear_color,'ear.'+side,(0,-1,0),rows=172,sides=72)
        attach(core,rig)
        # Long uneven locks merge into the curved ear shell; no short tile grid.
        ear=art.Surface(core)
        for i in range(7):
            t=.06+(i%3)*.045;idx=int(t*172);tan,u,n=frames[idx]
            lateral=(i-3)*.23
            start=centers[idx]+u*widths[idx].x*lateral
            root,no=ear.contact(start,(0,-1,0),-.014)
            endt=.70+.043*math.sin(i*2.1);id2=int(endt*172)
            mididx=int((t+endt)*.50*172)
            _,mu,mn=frames[mididx];_,eu,en=frames[id2]
            mid=centers[mididx]+mu*widths[mididx].x*lateral*.92+mn*widths[mididx].y*.91
            end=centers[id2]+eu*widths[id2].x*lateral*.96+en*widths[id2].y*.96
            pal=ear_color(.55,Vector((0,-1,0)))
            obj=a.lock('long_ear_wave_'+side+str(i),[root,root+Vector((sign*.07,-.01,-.11)),mid,end],
                .072+(i%2)*.018,.027,pal,'ear.'+side,(0,-1,.05),steps=88,sides=32,root_palette=golden)
            # Coordinate-based brown tips, independent of the strand's length.
            values=[]
            for vtx in obj.data.vertices:
                t2=art.smooth((2.94-vtx.co.z)/.54)
                pal2=tuple(art.mix(aa,bb,t2) for aa,bb in zip(golden,brown))
                values.append(art.mix(pal2[0],pal2[2],.68+.04*math.sin(vtx.co.z*22+vtx.co.x*17)))
            a.colors(obj,values);attach(obj,rig)
        warm_cheek=tuple(art.mix(c,h,.35) for c,h in zip(cream,golden))
        for i in range(8):
            z=2.02+i*.071+.013*math.sin(i*2.3)
            root,n=face.contact((sign*(.64+.012*math.cos(i*2.7)),-1.13,z),(sign*.60,-.80,.02),-.022)
            sweep=.11+.022*math.sin(i*2.1)
            obj=a.lock('soft_cheek_fan_'+side+str(i),[root,root+Vector((sign*.045,-.008,-.029)),
                root+Vector((sign*sweep*.70,.062,-.032)),root+Vector((sign*sweep,.17,-.013+.015*math.sin(i)))],
                .063+.008*math.sin(i*1.8),.014,warm_cheek if i<4 else golden,
                normal=(sign*.60,-.80,0),steps=45,sides=30,root_palette=golden)
            attach(obj,rig)
    # A fully backed cream breast silhouette extends under the medallion. Each
    # row overlaps the next; the previous uncovered center is now actual fur.
    rows,cols=84,72;verts=[];colors=[];faces=[]
    for back in (False,True):
        for i in range(rows+1):
            t=i/rows;z=1.765-.82*t
            width=.22+.25*math.sin(math.pi*t)**.50
            width*=1-.63*art.smooth((t-.69)/.31)
            for j in range(cols+1):
                q=2*j/cols-1;x=q*width
                zz=z+.14*t*abs(q)**1.5
                p,n=support.contact((x,-1.18,zz),(0,-1,.02),-.008 if back else .032)
                if not back:
                    p+=n*.012*(.5+.5*math.sin(q*33+t*3))**3*math.sin(math.pi*t)
                verts.append(p)
                colors.append(art.mix(cream[0],cream[2],.63+.06*math.sin(q*19+t*8)))
    layer=(rows+1)*(cols+1)
    for side in range(2):
        for i in range(rows):
            for j in range(cols):
                k=side*layer+i*(cols+1)+j;faces.append((k,k+1,k+cols+2,k+cols+1))
    edge=list(range(cols+1))+[r*(cols+1)+cols for r in range(1,rows+1)]+[rows*(cols+1)+j for j in range(cols-1,-1,-1)]+[r*(cols+1) for r in range(rows-1,0,-1)]
    faces.extend((k,l,l+layer,k+layer) for k,l in zip(edge,edge[1:]+edge[:1]))
    bib=a.mesh('continuous_cream_breast',verts,faces,'paint','body');a.colors(bib,colors);attach(bib,rig)
    for row in range(4):
        count=9 if row<3 else 7
        for j in range(count):
            x=(j-(count-1)/2)*(.091 if row<3 else .068)
            z=1.74-row*.16-.040*abs(x)
            root,n=support.contact((x,-1.2,z),(0,-1,.01),.015)
            length=.235+.035*math.cos(x*3)+(j%2)*.015
            control=[root,root+Vector((x*.06,-.03,-.085)),
                root+Vector((x*.16,-.035,-length*.70)),root+Vector((x*.24,-.012,-length))]
            # Seat every center along the actual rounded breast, with enough
            # overlap to prevent holes and with the last tip tangent to it.
            seated=[]
            for k,p in enumerate(art.path(control,14)):
                q,no=support.contact(p,(0,-1,.02),.025+.018*math.sin(math.pi*k/14))
                seated.append(q)
            obj=a.lock('overlapping_breast_lock_'+str(row)+'_'+str(j),seated,
                .092+(j%3)*.007,.030,cream,'body',normal=(0,-1,0),steps=48,sides=28,root_palette=cream)
            attach(obj,rig)
    for i in range(7):
        x=(i-3)*.105; root,n=face.contact((x,-.84+.07*math.sin(i*2.3),3.12),(0,0,1),-.022)
        flick=.095+.038*math.sin(i*2.0+.7)
        obj=a.lock('wind_swept_crown_'+str(i),[root,root+Vector((.045,.065,.055)),
            root+Vector((.085,.16,flick)),root+Vector((.13+.023*math.cos(i*2),.27,flick*.87))],
            .086+.009*math.sin(i*2.5),.026,golden,normal=(0,0,1),steps=54,sides=32)
        attach(obj,rig)
    points=[(0,1.04,1.23),(0,1.60,1.40),(0,2.02,1.71),(0,2.20,2.08),
        (0,2.08,2.39),(0,1.78,2.45),(0,1.50,2.27),(0,1.54,2.04)]
    sizes=[(.20,.215),(.255,.26),(.285,.29),(.30,.285),(.28,.27),(.235,.24),(.16,.18),(.001,.001)]
    def tail_color(t,n):
        f=art.smooth((t-.22)/.35)*art.smooth((n.z+.35)/.70)
        return tuple(art.mix(aa,bb,f) for aa,bb in zip(golden,cream))
    core,centers,widths,frames=volume(a,'golden_cream_curl',points,sizes,tail_color,'tail',(1,0,0),rows=190,sides=80)
    attach(core,rig)
    tail_strands(a,rig,'cream_plume_flow',centers,widths,frames,tail_color,
        (.3,.85,1.4,2.0,3.8,4.35,4.90,5.48),count=8)


def apply(g, rig, kind):
    if kind not in ('cat','dog'):
        raise ValueError('Expected cat or dog')
    original_names={o.name for o in g.ASSET}
    edits=[]
    a=toolkit(g,kind)
    ocular(g,kind,edits)
    (cat if kind=='cat' else dog)(a,rig,edits)
    clearance=clear_pendant(g,edits) if kind=='dog' else None
    color_edits=coat_color(g,kind)
    added=[o.name for o in g.ASSET if o.name not in original_names]
    for obj in g.ASSET:
        if obj.name in added:
            edits.append(dict(name=obj.name,operation='New reference-shaped volumetric sculpt surface',
                authored_bounds=[coordinates(obj).min(axis=0).tolist(),coordinates(obj).max(axis=0).tolist()]))
    return dict(notes=('Swept silver flame crest, triangular ears, tapered feline eye surround and full S-plume.'
        if kind=='cat' else 'Flowing dark-tipped ear masses, continuous overlapping cream breast, curved plume and richer expressive eyes.'),
        edited_objects=edits,added_base_clothing=[],added_sculpt_objects=added,
        material_edits=color_edits,
        pendant_clearance=clearance,
        dependency_paths=['assets/3d/source/cat/sculpt-v002/nyra_detail.py'],
        ocular_revision='Coherently reshaped orbital surfaces and closed lids; original actions unchanged.',
        likeness_limit='Single-view hidden surfaces inferred; artistic reconstruction, not exact 1:1 identity.')

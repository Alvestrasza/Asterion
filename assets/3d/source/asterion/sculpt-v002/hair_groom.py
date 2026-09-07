"""Asterion's deterministic ivory groom and matching portable tube geometry.

The approved four-view sheet governs the compact swept cheek/mantle fans and
dorsal tail plume. Native Blender hair is the editable authority. Every export
tube is built from the identical strand positions and radii, with no simulation,
new bones or authored actions. The historical sculpt-v001 source is not edited.

Native API: https://docs.blender.org/api/5.0/bpy.types.Curves.html
The relevant calls were also probed on the installed Blender 5.2.1 LTS.
"""
from array import array
from dataclasses import dataclass
import hashlib
import math
import random

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


SEED = 915204
SIDES = 5
POINTS_PER_STRAND = 14
TRIANGLES_PER_STRAND = (POINTS_PER_STRAND - 1) * SIDES * 2 + (SIDES - 2) * 2


def _smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _bezier(points, t):
    a, b, c, d = points
    q = 1.0 - t
    return a * q ** 3 + b * (3 * q * q * t) + c * (3 * q * t * t) + d * t ** 3


def _allocate(total, weights):
    """Largest-remainder allocation; the requested count is never exceeded."""
    total = int(total)
    if total < 0 or not weights or any(w <= 0 for w in weights):
        raise ValueError('Expected a nonnegative strand count and positive weights')
    scale = total / sum(weights)
    ideal = [w * scale for w in weights]
    counts = [int(v) for v in ideal]
    order = sorted(range(len(weights)), key=lambda i: (-(ideal[i] - counts[i]), i))
    for i in order[:total - sum(counts)]:
        counts[i] += 1
    return counts


def _frame(tangent, preferred):
    tangent = tangent.normalized()
    normal = preferred - tangent * preferred.dot(tangent)
    if normal.length_squared < 1.e-12:
        alternate = Vector((0, 0, 1)) if abs(tangent.z) < .9 else Vector((0, 1, 0))
        normal = alternate - tangent * alternate.dot(tangent)
    normal.normalize()
    return tangent.cross(normal).normalized(), normal


class _Support:
    """Immutable base-skin support; decorative scales are not hair emitters."""
    def __init__(self, obj):
        self.name = obj.name
        self.tree = BVHTree.FromPolygons(
            [obj.matrix_world @ v.co for v in obj.data.vertices],
            [tuple(p.vertices) for p in obj.data.polygons])
        self.fallbacks = 0
        self.root_queries = 0
        self.max_fallback_distance = 0.0

    def root(self, landmark, normal):
        landmark, normal = Vector(landmark), Vector(normal).normalized()
        self.root_queries += 1
        point, no, _, _ = self.tree.ray_cast(landmark + normal * .70, -normal, 1.40)
        if point is None:
            point, no, _, distance = self.tree.find_nearest(landmark)
            if point is None or distance > .30:
                raise ValueError(f'Groom root misses local {self.name} skin')
            self.fallbacks += 1
            self.max_fallback_distance = max(self.max_fallback_distance, distance)
        if no.dot(normal) < 0:
            no = -no
        # Hair begins just inside the base skin; never at a detached tuft root.
        return point - no * .0052, no


@dataclass
class _Guide:
    controls: tuple
    width: float
    depth: float
    normal: Vector
    support: _Support
    root_spread: float = .10

    @property
    def weight(self):
        return self.width * sum((b - a).length for a, b in zip(self.controls, self.controls[1:]))


def _guide(support, root, tip, width, depth, normal, curl=.075):
    normal = Vector(normal).normalized()
    root, normal = support.root(root, normal)
    tip = Vector(tip)
    span = tip - root
    first = root + span * .32 + normal * .026 + Vector((0, 0, .030))
    second = root + span * .79 - Vector((0, 0, curl))
    return _Guide((root, first, second, tip), width, depth, normal, support)


def _mane_guides(sign, head, body):
    """Overlapping diagonal cascades, not horizontal tiers of equal tufts."""
    # These inner guides begin beside the exposed blue dorsal strip. Their
    # staggered lower tips cross the next root patch, filling the rear skull
    # continuously while keeping that narrow strip readable.
    inner = [
        (.27, -.22, 4.19, .88, .43, 3.90, .148),
        (.30, -.17, 3.98, .95, .47, 3.50, .173),
        (.29, -.14, 3.68, .88, .45, 3.14, .159),
        (.30, -.12, 3.41, .88, .39, 2.87, .171),
        (.29, -.14, 3.22, .72, .33, 2.72, .146),
        (.28, -.18, 3.02, .66, .28, 2.62, .126),
    ]
    # Only the upper locks flick upwards behind the ears. Progressively longer
    # downward sweeps carry the lower mantle; unequal spacing/widths avoid a
    # combed shelf silhouette in the side and rear views.
    outer = [
        (.67, -.44, 4.16, 1.04, .59, 4.29, .163),
        (.74, -.44, 3.96, 1.19, .52, 3.98, .176),
        (.73, -.40, 3.75, 1.13, .48, 3.48, .172),
        (.69, -.38, 3.51, 1.16, .42, 3.08, .195),
        (.64, -.32, 3.31, .96, .44, 2.76, .174),
        (.58, -.27, 3.08, .88, .28, 2.64, .150),
    ]
    guides = []
    for i, (x, y, z, xx, yy, zz, width) in enumerate(inner + outer):
        support = head if z >= 3.43 else body
        guide = _guide(support, (sign*x, y, z), (sign*xx, yy, zz),
                       width, .062 if i < len(inner) else .078,
                       (sign*.67, .74, .015), curl=.082 + .025*(i % 3))
        guide.root_spread = .112 + .013*(i % 3)
        guides.append(guide)
    return guides


def _cheek_guides(sign, head, body):
    # Each patch starts behind the eye; short cream fur frames the blue muzzle.
    specs = [
        (.72, -1.010, 3.72, 1.05, -.33, 3.75, .109),
        (.75, -.920, 3.53, 1.16, -.16, 3.40, .125),
        (.72, -.860, 3.37, 1.12, -.04, 3.10, .132),
        (.66, -.790, 3.19, .98, .035, 2.84, .146),
        (.61, -.700, 3.04, .84, .110, 2.70, .123),
    ]
    return [_guide(head if z >= 3.30 else body,
                   (sign*x, y, z), (sign*xx, yy, zz), width, .052,
                   (sign*.94, -.24, .035), curl=.048 + .019*i)
            for i, (x, y, z, xx, yy, zz, width) in enumerate(specs)]


def _tail_guides(g, tail, body):
    controls = [(0,1.35,2.08),(0,1.90,2.04),(0,2.24,1.66),
                (.06,2.56,1.17),(.12,2.97,.89),(.12,3.23,1.06)]
    centers = g.spline(controls, 300)

    def sample(t):
        f = max(0, min(.985, t))*300
        i = min(299, int(f)); blend = f-i
        c = centers[i].lerp(centers[i+1], blend)
        tangent = (centers[min(300,i+2)]-centers[max(0,i-1)]).normalized()
        up = Vector((0,-tangent.z,tangent.y)).normalized()
        radius = g.interpolate([.32,.31,.23,.16,.07,.001], t)
        return c, up, radius

    # Three short, overlapping proximal whorls start on the actual rump skin.
    # They conceal neither armor nor dorsal scales and bridge the otherwise
    # blunt cut edge where the narrower tail support emerges from the rump.
    result = []
    for i, (x, y, z, end_t) in enumerate([
            (-.065, 1.19, 2.46, .185),
            (.060, 1.27, 2.45, .230),
            (.010, 1.34, 2.43, .270)]):
        root, no = body.root((x, y, z), (0, .24, .97))
        end, end_normal, end_radius = sample(end_t)
        tip = end + end_normal*(end_radius+.166) + Vector((x*.50,0,0))
        span = tip-root
        first = root+span*.26+Vector((0,-.014,.055))
        second = root+span*.72+Vector((0,.005,.092))
        result.append(_Guide((root,first,second,tip), .194-.013*i,
                             .071, no, body, .112))
    # Alternating, unevenly spaced trailing fans keep the cream proximal and
    # create a few coherent flicks, rather than a single flat ribbon to the tip.
    for i in range(12):
        t = .018+i*.040 + .007*math.sin(i*1.61)
        c, up, radius = sample(t)
        sign = 1 if i % 2 else -1
        x = sign*(.065+.024*math.sin(i*1.71))
        root, no = tail.root(c+up*radius+Vector((x,0,0)), up)
        controls = [root]
        end_spread = .018*math.sin(i*2.13)
        for j, dt in enumerate((.044, .118, .196+end_spread)):
            pos, normal, r = sample(t+dt)
            height = (.119,.196,.159)[j] + .025*math.sin(i*1.2)
            controls.append(pos+normal*(r+height)+Vector((x*(1.02-.14*j),0,0)))
        result.append(_Guide(tuple(controls), .213-.115*t, .078-.019*t,
                             no, tail, .094))
    return result


def _strands(guides, count, seed):
    """Deterministic clump-correlated roots, varied lengths and restrained flyaways."""
    rng = random.Random(seed)
    allocation = _allocate(count, [guide.weight for guide in guides])
    positions, radii, shades = array('f'), array('f'), array('i')
    min_length, max_length = float('inf'), 0.0
    lengths = []
    for guide, amount in zip(guides, allocation):
        flow = (guide.controls[1]-guide.controls[0]).normalized()
        across, normal = _frame(flow, guide.normal)
        skin_flow = flow - guide.normal*flow.dot(guide.normal)
        if skin_flow.length_squared < 1.e-10:
            skin_flow = across.cross(guide.normal)
        skin_flow.normalize()
        for strand in range(amount):
            angle = rng.random()*math.tau; radial = math.sqrt(rng.random())
            a, b = math.cos(angle)*radial, math.sin(angle)*radial
            root_landmark = guide.controls[0]+across*(a*guide.width*.55)+skin_flow*(b*guide.root_spread)
            root, _ = guide.support.root(root_landmark, guide.normal)
            root_delta = root-guide.controls[0]
            short = rng.random() < .145
            length_factor = rng.uniform(.53,.74) if short else rng.uniform(.76,1.025)
            flyaway = not short and rng.random() < .042
            phase = rng.random()*math.tau
            wave = rng.uniform(.0020,.0055)*(1.7 if flyaway else 1.0)
            subclump = strand % 7
            subphase = subclump*2.399963229728653
            tip_offset = (across*math.cos(subphase)*guide.width*.08 +
                          normal*math.sin(subphase)*guide.depth*.10)
            tip_offset += across*rng.uniform(-.003,.003)+normal*rng.uniform(-.002,.002)
            base_radius = rng.uniform(.0029,.0045)*(0.68 if flyaway else 1.0)
            # Darker inner fibers give the ivory fan depth without painted cards.
            shade = 2 if b < -.63 or rng.random() < .075 else 1 if b > .60 else 0
            shades.append(shade)
            strand_points = []
            for point_index in range(POINTS_PER_STRAND):
                t = point_index/(POINTS_PER_STRAND-1)
                s = t*length_factor
                center = _bezier(guide.controls,s)
                volume = math.sin(math.pi*min(1,s))**.72
                taper = (1-t)**1.35
                offset = root_delta*taper
                offset += across*(a*guide.width*.74*volume)+normal*(b*guide.depth*.76*volume)
                offset += tip_offset*_smooth((t-.20)/.80)
                wave_fade = math.sin(math.pi*t)**.8
                offset += across*(math.sin(phase+t*math.pi*2.1)*wave*wave_fade)
                offset += normal*(math.sin(phase*.73+t*math.pi*1.5)*wave*.48*wave_fade)
                if flyaway:
                    offset += normal*(.017*math.sin(math.pi*t)**1.3)
                p = center+offset
                if point_index == 0:
                    p = root
                r = base_radius*(1-.965*t**1.14)*(1-.18*t)+.000075
                positions.extend(p)
                radii.append(r)
                strand_points.append(p)
            length = sum((b-a).length for a,b in zip(strand_points,strand_points[1:]))
            min_length, max_length = min(min_length,length), max(max_length,length)
            lengths.append(length)
    return positions, radii, shades, {
        'guides':len(guides), 'strands':count, 'short_fraction_target':.145,
        'flyaway_fraction_target':.042, 'length_min':min_length,
        'length_max':max_length, 'length_mean':sum(lengths)/len(lengths),
        'per_guide_strands':allocation}


def _materials(g):
    result = []
    for name, color, factor in [('ivory','C9B187',.61),('light','DECAA5',.61),('depth','9F8258',.60)]:
        key = 'groom_v002_'+name
        material = g.material(key,color,0,.61)
        shader = material.node_tree.nodes.get('Principled BSDF')
        tint = tuple(v*factor for v in material.diffuse_color[:3])+(1,)
        material.diffuse_color = tint
        shader.inputs['Base Color'].default_value = tint
        shader.inputs['Specular IOR Level'].default_value = .24
        shader.inputs['Coat Weight'].default_value = 0
        shader.inputs['Emission Strength'].default_value = 0
        g.M[key] = material
        result.append(material)
    return result


def _attach_native(obj, rig, bone_name):
    # Blender bone parenting evaluates at the bone tail. This explicit inverse
    # produces the same rest->pose transform as one-weight linear mesh skinning.
    bone = rig.data.bones[bone_name]
    rest_parent = rig.matrix_world @ bone.matrix_local @ Matrix.Translation((0,bone.length,0))
    obj.parent = rig
    obj.parent_type = 'BONE'
    obj.parent_bone = bone_name
    obj.matrix_parent_inverse = rest_parent.inverted()
    obj.matrix_basis = Matrix.Identity(4)


def _attach_mesh(obj, rig, bone_name):
    obj.vertex_groups.new(name=bone_name).add(list(range(len(obj.data.vertices))),1.0,'REPLACE')
    modifier = obj.modifiers.new('Existing rigid groom attachment','ARMATURE')
    modifier.object = rig
    modifier.use_vertex_groups = True
    modifier.use_deform_preserve_volume = False
    obj.parent = rig
    obj.matrix_world = Matrix.Identity(4)


def _make_pair(g, rig, group, bone_name, positions, radii, shades, materials):
    strand_count = len(shades)
    point_count = strand_count*POINTS_PER_STRAND
    if len(positions) != point_count*3 or len(radii) != point_count:
        raise ValueError('Native/export strand layout mismatch')
    name = 'AST_Groom_v002_'+group.replace('.','_')
    data = bpy.data.hair_curves.new(name+'_editable_hair')
    data.add_curves([POINTS_PER_STRAND]*strand_count)
    data.set_types(type='POLY')
    data.attributes['position'].data.foreach_set('vector',positions)
    radius = data.attributes.new('radius','FLOAT','POINT')
    radius.data.foreach_set('value',radii)
    material_index = data.attributes.new('material_index','INT','CURVE')
    material_index.data.foreach_set('value',shades)
    for material in materials:
        data.materials.append(material)
    data.selection_domain = 'CURVE'
    native = bpy.data.objects.new(name+'_native',data)
    bpy.context.collection.objects.link(native)
    native['ast_native_hair'] = True
    native['ast_hair_group'] = group
    native['ast_bone'] = bone_name
    native['ast_part'] = 'head' if bone_name == 'head' else 'tail'
    native['ast_hair_seed'] = SEED
    native['ast_hair_basis'] = 'POLY'
    native['ast_hair_points_per_strand'] = POINTS_PER_STRAND
    native['ast_hair_strand_count'] = strand_count
    _attach_native(native,rig,bone_name)

    vertex_positions = array('f')
    loop_indices, loop_starts, loop_totals, face_materials = array('i'),array('i'),array('i'),array('i')
    loop_start = 0

    def polygon(indices, material):
        nonlocal loop_start
        loop_starts.append(loop_start);loop_totals.append(len(indices))
        loop_indices.extend(indices);face_materials.append(material)
        loop_start += len(indices)

    angles = [(math.cos(math.tau*i/SIDES),math.sin(math.tau*i/SIDES)) for i in range(SIDES)]
    for strand in range(strand_count):
        offset = strand*POINTS_PER_STRAND
        points = [Vector(positions[(offset+i)*3:(offset+i+1)*3]) for i in range(POINTS_PER_STRAND)]
        previous = Vector((0,0,1))
        for i,center in enumerate(points):
            tangent = (points[min(POINTS_PER_STRAND-1,i+1)]-points[max(0,i-1)]).normalized()
            across,normal = _frame(tangent,previous);previous = normal
            r = radii[offset+i]
            for c,s in angles:
                vertex_positions.extend(center+across*(r*c)+normal*(r*s))
        base = strand*POINTS_PER_STRAND*SIDES
        for ring in range(POINTS_PER_STRAND-1):
            for side in range(SIDES):
                a=base+ring*SIDES+side;b=base+ring*SIDES+(side+1)%SIDES
                polygon((a,a+SIDES,b+SIDES,b),shades[strand])
        # No added cap-center vertices: validator ordering remains rectangular.
        tip = base+(POINTS_PER_STRAND-1)*SIDES
        for side in range(1,SIDES-1):
            polygon((base,base+side,base+side+1),shades[strand])
            polygon((tip,tip+side+1,tip+side),shades[strand])

    mesh = bpy.data.meshes.new(name+'_tube_mesh')
    mesh.vertices.add(len(vertex_positions)//3)
    mesh.vertices.foreach_set('co',vertex_positions)
    mesh.loops.add(len(loop_indices));mesh.loops.foreach_set('vertex_index',loop_indices)
    mesh.polygons.add(len(loop_starts))
    mesh.polygons.foreach_set('loop_start',loop_starts);mesh.polygons.foreach_set('loop_total',loop_totals)
    for material in materials:
        mesh.materials.append(material)
    mesh.polygons.foreach_set('material_index',face_materials)
    mesh.polygons.foreach_set('use_smooth',[True]*len(mesh.polygons))
    mesh.update(calc_edges=True)
    export = bpy.data.objects.new(name+'_export',mesh)
    bpy.context.collection.objects.link(export)
    export['ast_hair_export'] = True
    export['ast_hair_group'] = group
    export['ast_hair_sides'] = SIDES
    export['ast_hair_points_per_strand'] = POINTS_PER_STRAND
    export['ast_hair_strand_count'] = strand_count
    export['ast_hair_seed'] = SEED
    export['ast_bone'] = bone_name
    export['ast_part'] = native['ast_part']
    export['ast_hair_vertex_layout'] = 'strand-major/ring-major/sides-major; no cap centers'
    export.hide_render = True
    export.hide_set(True)
    _attach_mesh(export,rig,bone_name)
    g.ASSET.append(export)

    # Check actual stored Blender buffers, not only pre-construction Python data.
    stored_points = np.empty(point_count*3,dtype=np.float32)
    stored_radius = np.empty(point_count,dtype=np.float32)
    stored_vertices = np.empty(point_count*SIDES*3,dtype=np.float32)
    data.attributes['position'].data.foreach_get('vector',stored_points)
    data.attributes['radius'].data.foreach_get('value',stored_radius)
    mesh.vertices.foreach_get('co',stored_vertices)
    rings = stored_vertices.reshape(point_count,SIDES,3).astype(np.float64)
    centers = stored_points.reshape(point_count,3).astype(np.float64)
    centroid_error = float(np.max(np.linalg.norm(rings.mean(axis=1)-centers,axis=1)))
    radius_error = float(np.max(np.abs(np.linalg.norm(rings-centers[:,None,:],axis=2)-stored_radius[:,None])))
    if centroid_error > 1.e-5 or radius_error > 1.e-5:
        raise ValueError('Stored native hair and export ring correspondence failed')
    if not np.isfinite(rings).all() or not np.isfinite(stored_radius).all() or not (stored_radius>0).all():
        raise ValueError('Nonfinite or nonpositive groom geometry')
    digest = hashlib.sha256(stored_points.tobytes()+stored_radius.tobytes()).hexdigest()
    for obj in (native,export):
        obj['ast_hair_strand_data_sha256'] = digest
    return native,export,{
        'group':group,'bone':bone_name,'native_object':native.name,'export_object':export.name,
        'native_type':native.type,'strand_count':strand_count,'point_count':point_count,
        'vertices':len(mesh.vertices),'triangles':strand_count*TRIANGLES_PER_STRAND,
        'sides':SIDES,'points_per_strand':POINTS_PER_STRAND,
        'stored_max_centroid_error':centroid_error,'stored_max_radius_error':radius_error,
        'all_strands_correspond':True,'strand_data_sha256':digest,
        'radius_min':float(stored_radius.min()),'radius_max':float(stored_radius.max())}


def build(g, rig, triangle_budget=2600000):
    """Return native curve objects, same-strand export meshes and measured report.

    The caller loads a sculpt-v001 copy at idle frame 1 and removes only its old
    mane/cheek/tail-plume objects. Native hair is visible in the editable master;
    tube equivalents start hidden and must be shown for export/reimport checks.
    This function never changes frames, actions, bones or animation keyframes.
    """
    budget = int(triangle_budget)
    if budget < TRIANGLES_PER_STRAND*5:
        raise ValueError('Hair budget must permit at least one strand per groom region')
    if rig.type != 'ARMATURE' or any(bone not in rig.data.bones for bone in ('head','tail.01')):
        raise ValueError('Expected the existing Asterion head and tail.01 bones')
    sources = {}
    for region,name in [('head','AST_Sculpted_head'),('body','AST_Sculpted_body'),('tail','AST_Sculpted_tail')]:
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != 'MESH':
            raise ValueError(f'Missing original base anatomy {name}')
        sources[region] = _Support(obj)
    frame_before = (bpy.context.scene.frame_current,bpy.context.scene.frame_subframe)
    actions_before = tuple(action.as_pointer() for action in bpy.data.actions)
    active_action_before = rig.animation_data.action if rig.animation_data else None
    specifications = [
        ('mane.L','head',.30,_mane_guides(1,sources['head'],sources['body'])),
        ('mane.R','head',.30,_mane_guides(-1,sources['head'],sources['body'])),
        ('cheek.L','head',.10,_cheek_guides(1,sources['head'],sources['body'])),
        ('cheek.R','head',.10,_cheek_guides(-1,sources['head'],sources['body'])),
        ('tail','tail.01',.20,_tail_guides(g,sources['tail'],sources['body'])),
    ]
    total_strands = budget//TRIANGLES_PER_STRAND
    allocation = _allocate(total_strands,[spec[2] for spec in specifications])
    materials = _materials(g)
    native_objects,export_objects,groups = [],[],[]
    for i,((group,bone,_,guides),count) in enumerate(zip(specifications,allocation)):
        positions,radii,shades,detail = _strands(guides,count,SEED+i*7907)
        native,export,report = _make_pair(g,rig,group,bone,positions,radii,shades,materials)
        report.update(detail);groups.append(report)
        native_objects.append(native);export_objects.append(export)
    bpy.context.view_layer.update()
    if frame_before != (bpy.context.scene.frame_current,bpy.context.scene.frame_subframe):
        raise RuntimeError('Groom construction changed the caller frame')
    if actions_before != tuple(action.as_pointer() for action in bpy.data.actions):
        raise RuntimeError('Groom construction changed the action data-block set')
    if (rig.animation_data.action if rig.animation_data else None) != active_action_before:
        raise RuntimeError('Groom construction changed the active action')
    triangles = total_strands*TRIANGLES_PER_STRAND
    report = {
        'revision':'asterion-sculpt-v002-native-groom','seed':SEED,
        'triangle_budget':budget,'triangles':triangles,'unused_triangle_budget':budget-triangles,
        'strands':total_strands,'native_points':total_strands*POINTS_PER_STRAND,
        'export_vertices':total_strands*POINTS_PER_STRAND*SIDES,
        'native_objects':len(native_objects),'export_objects':len(export_objects),
        'material_names':[material.name for material in materials],
        'native_curve_type':'POLY','tube_sides':SIDES,'points_per_strand':POINTS_PER_STRAND,
        'all_strands_correspond':all(group['all_strands_correspond'] for group in groups),
        'all_strands_rigidly_attached':True,'bone_attachments':['head','tail.01'],
        'native_visible_export_mesh_hidden':True,'simulation':False,
        'new_bones':0,'new_actions':0,'frame_and_action_assignment_preserved':True,
        'groups':groups,
        'support':{name:{'object':support.name,'root_queries':support.root_queries,
                         'nearest_fallbacks':support.fallbacks,
                         'max_nearest_distance':support.max_fallback_distance}
                   for name,support in sources.items()},
        'interpretation':'Authored irregular clumped ivory groom from the approved four-view sheet; no image projection or exact 1:1 claim.',
        'animation_limit':'Existing rigid head/tail.01 attachment only; no new secondary motion or physics.',
    }
    return native_objects,export_objects,report

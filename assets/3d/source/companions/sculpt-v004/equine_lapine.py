"""Reference-led Caelo and Liora forms, applied to immutable v003 masters.

This pass replaces primary hair silhouettes, reshapes complete orbital families
with their supporting skull, and authors continuous three-dimensional color.
It never changes the original skeleton, rest pose, weights or action curves.
No projected image, camera-facing geometry, texture or provider is involved.
"""
from __future__ import annotations

import math
import bpy
import numpy as np
from mathutils import Vector
from mathutils.noise import noise

DEPENDENCIES = []


def _points(obj):
    local = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', local)
    m = np.asarray(obj.matrix_world, dtype=float)
    return local.reshape((-1, 3)).astype(float) @ m[:3, :3].T + m[:3, 3]


def _write(obj, world):
    if not np.isfinite(world).all():
        raise ValueError('Nonfinite authored coordinates: ' + obj.name)
    m = np.linalg.inv(np.asarray(obj.matrix_world, dtype=float))
    local = world @ m[:3, :3].T + m[:3, 3]
    obj.data.vertices.foreach_set('co', local.astype(np.float32).ravel())
    obj.data.update()


def _change(obj, before, after, operation):
    distance = float(np.linalg.norm(after - before, axis=1).max())
    if distance < 1.e-6:
        return None
    _write(obj, after)
    return {'name': obj.name, 'operation': operation,
            'vertices': len(after), 'max_displacement': distance}


def _smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def _bind(obj, rig, part, component='body'):
    if part not in rig.data.bones:
        raise ValueError('New sculpture requests unknown original bone: ' + part)
    obj['ast_part'] = part
    obj['asterion_component'] = component
    obj['asterion_rig'] = rig.get('asterion_rig', '') or ('pony-rig-v1' if 'Caelo' in obj.name else 'rabbit-rig-v1')
    obj.parent = rig
    obj.vertex_groups.clear()
    group = obj.vertex_groups.new(name=part)
    group.add(list(range(len(obj.data.vertices))), 1., 'REPLACE')
    modifier = obj.modifiers.new('Original presentation rig', 'ARMATURE')
    modifier.object = rig


def _remove(g, objects):
    names = []
    for obj in objects:
        names.append(obj.name)
        g.ASSET.remove(obj)
        bpy.data.objects.remove(obj, do_unlink=True)
    return names


def _colors(obj, values):
    layer = obj.data.color_attributes.get('AST_eye_color')
    if layer is None:
        layer = obj.data.color_attributes.new(name='AST_eye_color', type='FLOAT_COLOR', domain='POINT')
    if layer.domain != 'POINT' or len(layer.data) != len(values):
        raise ValueError('Unexpected authored color domain: ' + obj.name)
    layer.data.foreach_set('color', np.clip(np.asarray(values), 0, 1).astype(np.float32).ravel())


def _painted_material(g, name, color, roughness=.52):
    material = g.material(name, color, 0., roughness)
    bsdf = material.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Specular IOR Level'].default_value = .24
    vertex = material.node_tree.nodes.new('ShaderNodeVertexColor')
    vertex.layer_name = 'AST_eye_color'
    material.node_tree.links.new(vertex.outputs['Color'], bsdf.inputs['Base Color'])
    return material


def _mix(a, b, t):
    return np.asarray(a) * (1 - t) + np.asarray(b) * t


def _path(points, count):
    """Clamped cubic B-spline with a continuous, non-overshooting centerline."""
    points = [Vector(p) for p in points]
    n = len(points) - 1
    degree = min(3, n)
    knots = [0.] * (degree + 1) + [i / (n - degree + 1) for i in range(1, n - degree + 1)] + [1.] * (degree + 1)
    result = []
    for sample in range(count + 1):
        t = sample / count
        span = n if sample == count else next(i for i in range(degree, n + 1) if knots[i] <= t < knots[i + 1])
        values = [points[span - degree + j].copy() for j in range(degree + 1)]
        for r in range(1, degree + 1):
            for j in range(degree, r - 1, -1):
                a, b = knots[j + span - degree], knots[j + 1 + span - r]
                f = (t - a) / (b - a) if b > a else 0.
                values[j] = values[j - 1] * (1 - f) + values[j] * f
        result.append(values[degree])
    return result


def _lock(g, rig, material, palette, name, points, width, depth, part='head',
          normal=(0, -1, 0), steps=88, sides=48, tone=0., fullness=3.1):
    """A closed plump lock with an embedded root and a flowing crescent tip.

    Width describes the silhouette, depth describes the visible plush volume.
    Four broad highlight bands and low channels are continuous vertex paint and
    surface relief; no separate wires or stacked strips define the silhouette.
    """
    centers = _path(points, steps)
    previous = Vector(normal).normalized()
    vertices, faces, colors = [], [], []
    dark, shade, base, highlight = [np.asarray(c) for c in palette]
    for row, center in enumerate(centers):
        t = row / steps
        tangent = (centers[min(steps, row + 1)] - centers[max(0, row - 1)]).normalized()
        n = previous - tangent * previous.dot(tangent)
        if n.length < 1.e-5:
            fallback = Vector((0, 0, 1)) if abs(tangent.z) < .9 else Vector((0, 1, 0))
            n = fallback - tangent * fallback.dot(tangent)
        n.normalize()
        previous = n
        u = tangent.cross(n).normalized()
        profile = .0015 + math.sqrt(1 - math.exp(-25 * t)) * max(0, 1 - t ** fullness) ** 1.3
        fade = math.sin(math.pi * t) ** .8
        for col in range(sides):
            angle = math.tau * col / sides
            lateral, outward = math.cos(angle), math.sin(angle)
            channel = (.5 + .5 * math.cos(6 * angle + .65 * t)) ** 8
            sculpt = 1 + fade * (.07 * math.cos(3 * angle + .7 * t) - .055 * channel)
            p = center + u * (width * profile * lateral * sculpt) + n * (depth * profile * outward * sculpt)
            vertices.append(tuple(p))
            light = max(0., outward)
            color = _mix(dark, shade, .54 + .28 * light)
            color = _mix(color, base, .18 + .56 * light ** .7 + tone)
            ribbon = math.exp(-((lateral - .17 - .13 * math.sin(t * 4.8)) / .54) ** 2)
            color = _mix(color, highlight, (.18 + .55 * fade) * light ** 1.4 * ribbon)
            broad_shadow = (.5 + .5 * math.cos(3 * angle + .85 * t + .5)) ** 2
            color[:3] *= .79 + .18 * broad_shadow - .18 * channel * fade
            color[3] = 1
            colors.append(color)
    for row in range(steps):
        for col in range(sides):
            a, b = row * sides + col, row * sides + (col + 1) % sides
            faces.append((a, a + sides, b + sides, b))
    root, tip = len(vertices), len(vertices) + 1
    vertices += [tuple(centers[0]), tuple(centers[-1])]
    colors += [colors[0], colors[-1]]
    for col in range(sides):
        nxt = (col + 1) % sides
        faces.extend(((root, col, nxt), (tip, steps * sides + nxt, steps * sides + col)))
    obj = g.mesh(name, vertices, faces, material, part)
    _colors(obj, colors)
    _bind(obj, rig, part)
    obj['shape_reference'] = 'Approved original companion portrait; unseen surfaces inferred.'
    return obj


def _eye_fields(g, kind):
    """One coherent orbital warp for eye, lids, lashes and socket support.

    Eye centers and bone pivots remain fixed. The same deformation field acts
    on the underlying skull; outer corners taper upward instead of remaining
    vertical ovals. Original bind weights and topology are retained.
    """
    prefix = 'AST_caelo_v2_eye_' if kind == 'pony' else 'AST_liora_v2_eye_'
    width, height = (.495, .585) if kind == 'pony' else (.48, .55)
    fields = []
    for sign, side in ((1, 'L'), (-1, 'R')):
        n = np.array((sign * (.60 if kind == 'pony' else .55), -.80 if kind == 'pony' else -.835, .035 if kind == 'pony' else .03))
        n /= np.linalg.norm(n)
        u = np.cross((0, 0, 1), n)
        u /= np.linalg.norm(u)
        v = np.cross(n, u)
        lid = bpy.data.objects[prefix + side + '_closed_lid']
        c = np.asarray(lid['ast_lid_pivot']) - n * (.029 if kind == 'pony' else .031)
        fields.append((prefix + side, sign, c, u, v, n))
        eye = bpy.data.objects[prefix + side]
        local = _points(eye) - c
        x, z = local @ u, local @ v
        _iris(g, eye, x, z, width, height, kind)
    edits = []
    for obj in list(g.ASSET):
        part = str(obj.get('ast_part', ''))
        if part != 'head' and not part.startswith('lid.'):
            continue
        if prefix not in obj.name and not obj.name.endswith('_v2_head'):
            continue
        before = _points(obj)
        delta = np.zeros_like(before)
        for family, sign, c, u, v, n in fields:
            if prefix in obj.name and not obj.name.startswith(family):
                continue
            d = before - c
            x, z, depth = d @ u, d @ v, d @ n
            q = np.clip(np.abs(x) / (width * .52), 0, 1.3)
            new_z = z * ((.970 if kind == 'pony' else .940) - .145 * q ** 1.7) + sign * x * .055
            new_x = x * (1.035 if kind == 'pony' else 1.065)
            if obj.name.startswith(family):
                gain = np.ones(len(before))
            else:
                radius = np.maximum(np.abs(x) / (width * .60), np.abs(z) / (height * .60))
                gain = (1 - _smooth((radius - 1) / .72)) * (1 - _smooth((np.abs(depth) - .13) / .30))
                gain *= 1 - _smooth((-z - height * .52) / (height * .18))
            delta += gain[:, None] * ((new_x - x)[:, None] * u + (new_z - z)[:, None] * v)
        item = _change(obj, before, before + delta,
                       'Coherent tapered orbital field across eye, lash, movable lid and supporting skull')
        if item:
            edits.append(item)
    return edits


def _iris(g, obj, x, z, width, height, kind):
    """Depth, limbal ring and irregular radial colors authored on actual eyes."""
    ivory = np.array(g.color('FFF1DA'))
    dark = np.array(g.color('151A35' if kind == 'pony' else '262239'))
    upper = np.array(g.color('354C86' if kind == 'pony' else '595079'))
    middle = np.array(g.color('658CCA' if kind == 'pony' else '8F9FCC'))
    lower = np.array(g.color('A6DCF2' if kind == 'pony' else 'B2D9E5'))
    radius = np.sqrt((x / (width * .414)) ** 2 + ((z + height * .025) / (height * .445)) ** 2)
    pupil = np.sqrt((x / (width * .195)) ** 2 + ((z - height * .055) / (height * .279)) ** 2)
    angle = np.arctan2(z, x)
    amount = np.clip(.46 - z / (height * .80), 0, 1)
    colors = np.tile(ivory, (len(x), 1))
    inner = _mix(upper, middle, np.clip(amount * 1.42, 0, 1)[:, None])
    inner = _mix(inner, lower, np.clip((amount - .39) * 1.5, 0, 1)[:, None])
    rays = .035 * np.sin(angle * 43 + radius * 13) + .025 * np.sin(angle * 67 - radius * 9)
    facets = .04 * np.sin(angle * 11 + .7) * np.sin(radius * math.pi)
    limbus = .28 + .72 * np.clip((1 - radius) / .10, 0, 1)
    inner[:, :3] *= ((.94 + rays + facets) * limbus)[:, None]
    colors[radius < 1] = inner[radius < 1]
    transition = _smooth((pupil - .935) / .065)
    pupils = _mix(dark, colors, transition[:, None])
    colors[pupil < 1] = pupils[pupil < 1]
    colors[:, 3] = 1
    _colors(obj, colors)


def _caelo_hair(g, rig):
    old = [o for o in g.ASSET if o.name.startswith('AST_Caelo_hair_') and 'fitted_' not in o.name]
    removed = _remove(g, old)
    material = _painted_material(g, 'Caelo_v4_cloud_blue_lavender_waves', '7BA1D4', .43)
    palette = [g.color(c) for c in ('283263', '566AA6', '7DA7DE', 'DAF3FE')]
    made = []
    def lock(name, pts, width, depth, **kw):
        obj = _lock(g, rig, material, palette, 'Caelo_v4_' + name, pts, width, depth, **kw)
        if name in ('rolled_forelock', 'forelock_lower_crescent', 'forelock_inner_turn', 'swept_crown', 'crown_lift'):
            p = _points(obj)
            high = np.maximum(0., p[:, 2] - 3.90)
            p[:, 2] -= high * .28
            p[:, 2] += p[:, 0] * .245
            _write(obj, p)
        if name.startswith('tail_'):
            p = _points(obj)
            p[:, 1] = 1.19 + (p[:, 1] - 1.19) * .84
            p[:, 2] = 1.84 + (p[:, 2] - 1.84) * .86
            _write(obj, p)
        made.append(obj)
        return obj
    # Broad diagonally rolled forelock. The lowest point folds around the brow
    # and the asymmetrical outer tip flicks upward, as in the approved portrait.
    lock('rolled_forelock', [(.38, -1.08, 3.97), (.22, -1.32, 4.30),
         (-.20, -1.54, 4.35), (-.62, -1.62, 4.10), (-.78, -1.65, 3.78),
         (-.94, -1.62, 3.75), (-1.06, -1.56, 3.89)], .32, .205, steps=116)
    lock('forelock_lower_crescent', [(.27, -1.31, 3.95), (.12, -1.59, 4.09),
         (-.26, -1.70, 4.09), (-.56, -1.73, 3.88), (-.69, -1.71, 3.59),
         (-.92, -1.61, 3.70)], .215, .138, steps=104, tone=.02)
    lock('forelock_inner_turn', [(.38, -1.09, 3.90), (.42, -1.34, 4.05),
         (.30, -1.58, 4.00), (.16, -1.63, 3.85), (.14, -1.61, 3.69)], .122, .088, steps=76, tone=-.09)
    lock('swept_crown', [(.21, -.56, 3.82), (.35, -.71, 4.18),
         (.10, -1.00, 4.43), (-.25, -1.31, 4.40), (-.58, -1.47, 4.21),
         (-.84, -1.46, 4.25)], .283, .198, steps=112)
    lock('crown_lift', [(.20, -.50, 3.82), (.21, -.50, 4.12),
         (-.08, -.71, 4.37), (-.29, -.98, 4.47), (-.46, -1.13, 4.38)], .205, .150, steps=84)
    lock('parting_temple', [(.32, -1.00, 3.90), (.55, -1.16, 3.91),
         (.70, -1.22, 3.79), (.68, -1.24, 3.59), (.83, -1.15, 3.56)], .138, .100)
    # Both sides receive real lower-neck crescents and alternating rear flicks,
    # not the same parallel hanging ribbon replicated three times.
    for sign, side in ((1, 'L'), (-1, 'R')):
        def mirrored(points):
            return [(sign * x, y, z + (.025 if sign < 0 else 0)) for x, y, z in points]
        lock('temple_wave_' + side, mirrored([(.43, -.88, 3.76), (.68, -.85, 3.63),
             (.76, -.85, 3.42), (.73, -.83, 3.22), (.85, -.68, 3.17)]),
             .161, .099, normal=(sign, -.2, 0), steps=80)
        lock('mane_main_curl_' + side, mirrored([(.36, -.41, 3.66), (.69, -.14, 3.56),
             (.72, .03, 3.19), (.60, -.10, 2.84), (.56, -.04, 2.44),
             (.64, .29, 2.31), (.64, .50, 2.51)]),
             .22, .14, part='neck', normal=(sign, .15, 0), steps=132, fullness=3.2)
        lock('mane_face_curl_' + side, mirrored([(.48, -.64, 3.53), (.69, -.43, 3.28),
             (.68, -.55, 2.94), (.47, -.52, 2.61), (.40, -.35, 2.22),
             (.48, -.07, 2.17), (.54, .09, 2.33)]),
             .19, .12, part='neck', normal=(sign, -.08, 0), steps=124)
        for index, (z, y) in enumerate(((3.55, -.19), (3.20, -.07), (2.85, .01))):
            lock('mane_flick_' + side + '_' + str(index), mirrored([(.43, y - .20, z + .10),
                 (.60, y + .07, z), (.68, y + .30, z - .16),
                 (.70, y + .44, z + .10)]), .18 - index * .012, .106 - index * .008,
                 part='neck', normal=(sign, .12, 0), steps=76)
    lock('rear_continuous_sweep', [(0, -.34, 3.52), (.08, .20, 3.30),
         (.08, .26, 2.97), (-.05, .21, 2.64), (-.11, .31, 2.38),
         (-.06, .47, 2.42)], .33, .125, part='neck', normal=(0, 1, 0), steps=112, tone=-.06)
    # A full S-volume carries the tail, with three wide surface curls closing
    # around it. Its lower tips turn back outwards, rather than hanging pipes.
    lock('tail_full_S_plume', [(0, 1.19, 1.84), (0, 1.58, 2.50),
         (0, 2.19, 2.76), (0, 2.77, 2.31), (0, 2.77, 1.76),
         (0, 2.52, 1.31), (0, 2.70, .88), (0, 3.03, .68), (0, 3.14, .90)],
         .405, .31, part='tail', normal=(1, 0, 0), steps=164, sides=64, fullness=3.8, tone=-.08)
    for sign, side in ((1, 'L'), (-1, 'R')):
        lock('tail_surface_curl_' + side, [(sign * .12, 1.33, 2.03), (sign * .38, 1.78, 2.76),
             (sign * .44, 2.48, 2.61), (sign * .46, 2.90, 2.08),
             (sign * .43, 2.70, 1.48), (sign * .30, 2.97, 1.09),
             (sign * .17, 3.38, 1.10), (sign * .10, 3.45, 1.38)],
             .28, .130, part='tail', normal=(sign, 0, 0), steps=156, sides=56, fullness=3.5)
        lock('tail_low_turn_' + side, [(sign * .28, 2.35, 1.98), (sign * .40, 2.65, 1.72),
             (sign * .43, 2.47, 1.23), (sign * .35, 2.54, .67),
             (sign * .20, 2.88, .56), (sign * .08, 3.16, .72)],
             .21, .100, part='tail', normal=(sign, 0, 0), steps=112, fullness=3.0, tone=-.03)
        lock('tail_crown_flick_' + side, [(sign * .09, 1.27, 1.96), (sign * .18, 1.56, 2.62),
             (sign * .16, 2.02, 2.96), (sign * .08, 2.37, 2.91)],
             .208, .137, part='tail', normal=(sign, 0, 0), steps=96)
    return removed, made


def _rabbit_shape(g):
    edits = []
    for obj in g.ASSET:
        part = str(obj.get('ast_part', ''))
        before = _points(obj)
        after = before.copy()
        if part.startswith('ear.'):
            sign = 1 if part.endswith('.L') else -1
            t = np.clip((before[:, 2] - 2.91) / 1.87, 0, 1)
            after[:, 0] += sign * .34 * t ** 1.2
            after[:, 1] += .05 * t * t
            operation = 'Outward-swept ear silhouette, including its detachable guard and ear-base brush'
        elif part in ('body', 'leg.HL', 'leg.HR') and not str(obj.name).startswith('AST_Liora_fur_cotton'):
            haunch = np.exp(-((before[:, 1] - .67) / .45) ** 4 - ((before[:, 2] - .96) / .53) ** 4)
            side = _smooth((np.abs(before[:, 0]) - .30) / .36)
            after[:, 0] += np.sign(before[:, 0]) * .095 * haunch * side
            operation = 'Fuller round rabbit haunch; local field includes fitted outfit at that surface'
        else:
            continue
        item = _change(obj, before, after, operation)
        if item:
            edits.append(item)
    return edits


def _rabbit_fur(g, rig):
    old = [o for o in g.ASSET if o.name.startswith(('AST_Liora_fur_cheek_', 'AST_Liora_fur_cotton_', 'AST_Liora_fur_forehead_'))
           and o.name != 'AST_Liora_fur_cotton_tail_core']
    removed = _remove(g, old)
    material = _painted_material(g, 'Liora_v4_layered_cream_plush', 'E4CDAB', .64)
    palette = [g.color(c) for c in ('967A55', 'BEA17B', 'DDC4A1', 'EFDBBA')]
    made = []
    def lock(name, pts, width, depth, **kw):
        obj = _lock(g, rig, material, palette, 'Liora_v4_' + name, pts, width, depth, **kw)
        made.append(obj)
        return obj
    # Wide shallow overlapping cushions grow backwards from the cheeks, then
    # flick up in five unequal points. No many-leaf comb or parallel grooves.
    for sign, side in ((1, 'L'), (-1, 'R')):
        cheek_objects = []
        for index, z in enumerate((2.15, 2.29, 2.43, 2.57, 2.69)):
            length = (.25, .32, .33, .34, .23)[index]
            rootx = .54 + (.015 if index == 0 else 0)
            obj = lock('cheek_cushion_' + side + '_' + str(index),
                 [(sign * rootx, -1.07 + .035 * index, z),
                  (sign * (rootx + .15), -1.16 + .025 * index, z - .003),
                  (sign * (rootx + length), -.80 + .025 * index, z + .060),
                  (sign * (rootx + length + .014), -.55 + .045 * index, z + (.125, .15, .19, .215, .18)[index])],
                 (.125, .16, .152, .143, .102)[index], (.053, .056, .059, .054, .040)[index],
                 normal=(sign * .73, -.68, .07), steps=72, sides=40, tone=.005)
            cheek_objects.append(obj)
        for obj in cheek_objects:
            made.remove(obj)
            for modifier in list(obj.modifiers):
                if modifier.type == 'ARMATURE':
                    obj.modifiers.remove(modifier)
            matrix = obj.matrix_world.copy()
            obj.parent = None
            obj.matrix_world = matrix
        cheek = g.fuse('Liora_v4_continuous_cheek_fluff_' + side, cheek_objects, 'head', voxel=.009, subdiv=1)
        cheek.data.materials.clear()
        cheek.data.materials.append(material)
        normals = [v.normal.copy() for v in cheek.data.vertices]
        values = []
        for vertex, normal in zip(cheek.data.vertices, normals):
            p = cheek.matrix_world @ vertex.co
            fiber = .5 + .5 * noise(Vector((p.x * 68, p.y * 21, p.z * 59)))
            outward = max(0., normal.x * sign * .6 - normal.y * .8)
            value = _mix(palette[1], palette[2], .36 + .48 * fiber)
            value = _mix(value, palette[3], .12 * outward)
            values.append(value)
        _colors(cheek, values)
        for modifier in list(cheek.modifiers):
            if modifier.type == 'ARMATURE':
                cheek.modifiers.remove(modifier)
        _bind(cheek, rig, 'head')
        made.append(cheek)
        # A low rounded crown sweep, not a row of projecting feather spikes.
        lock('crown_sweep_' + side, [(sign * .14, -.80, 2.98), (sign * .27, -.95, 3.06),
             (sign * .16, -1.08, 3.10), (sign * .02, -1.10, 3.075)],
             .104, .025, normal=(0, -.6, 1), steps=76)
    # Keep the original closed cotton core and replace its many random scale-
    # like wisps with fewer shallow, consistently swept surface crescents.
    tail_objects = [bpy.data.objects['AST_Liora_fur_cotton_tail_core']]
    removed.append(tail_objects[0].name)
    for sign, side in ((1, 'L'), (-1, 'R')):
        paths = [
            [(.12, 1.20, 1.60), (.34, 1.47, 1.94), (.28, 1.81, 2.06), (.08, 2.01, 1.97)],
            [(.25, 1.57, 1.52), (.42, 1.83, 1.71), (.37, 2.10, 1.65), (.19, 2.23, 1.84)],
            [(.24, 1.57, 1.20), (.38, 1.82, 1.14), (.31, 2.02, 1.11), (.15, 2.11, 1.30)],
        ]
        for index, points in enumerate(paths):
            obj = lock('cotton_silhouette_curl_' + side + str(index),
                       [(sign * x, y, z) for x, y, z in points],
                       (.17, .17, .14)[index], (.060, .072, .061)[index],
                       part='tail', normal=(sign, .1, 0), steps=80, sides=40, fullness=3.0)
            p = _points(obj)
            center = np.array((0., 1.52, 1.43))
            _write(obj, center + (p - center) * .76)
            made.remove(obj)
            tail_objects.append(obj)
    for obj in tail_objects:
        for modifier in list(obj.modifiers):
            if modifier.type == 'ARMATURE':
                obj.modifiers.remove(modifier)
        matrix = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = matrix
    tail = g.fuse('Liora_v4_continuous_cotton_plush', tail_objects, 'tail', voxel=.008, subdiv=1)
    tail.data.materials.clear()
    tail.data.materials.append(material)
    normals = [vertex.normal.copy() for vertex in tail.data.vertices]
    values = []
    tail_palette = [g.color(c) for c in ('A48661', 'CDB28B', 'E2CBA8', 'F1DFC0')]
    for vertex, normal in zip(tail.data.vertices, normals):
        p = tail.matrix_world @ vertex.co
        grain = noise(Vector((p.x * 62, p.y * 23, p.z * 73)))
        fiber = np.clip(.5 + grain * .9, 0, 1)
        vertex.co += normal * (.0015 * fiber)
        value = _mix(tail_palette[0], tail_palette[2], .56 + .37 * fiber)
        value = _mix(value, tail_palette[3], .055 * fiber)
        values.append(value)
    tail.data.update()
    _colors(tail, values)
    _bind(tail, rig, 'tail')
    made.append(tail)
    return removed, made


def _coat_color(g, kind):
    """Broader warm planes complement the sculpture without camera projection."""
    headname = 'AST_caelo_v2_head' if kind == 'pony' else 'AST_liora_v2_head'
    count = 0
    for obj in g.ASSET:
        if obj.name != headname:
            continue
        layer = obj.data.color_attributes.get('AST_eye_color')
        if layer is None or layer.domain != 'POINT':
            continue
        values = np.empty(len(layer.data) * 4, dtype=np.float32)
        layer.data.foreach_get('color', values)
        values = values.reshape((-1, 4)).astype(float)
        p = _points(obj)
        if kind == 'pony':
            warm = np.exp(-((p[:, 1] + 1.96) / .27) ** 2 - ((p[:, 2] - 2.98) / .25) ** 2)
            values[:, 0] *= .97
            values[:, 1] *= .97 - .055 * warm
            values[:, 2] *= .98 - .073 * warm
        else:
            # The reference fur has warm ochre valleys, not uniformly white.
            shade = .90 + .10 * _smooth((p[:, 2] - 2.15) / .85)
            values[:, :3] *= shade[:, None]
        _colors(obj, values)
        count += 1
    return count


def apply(g, rig, kind):
    if kind not in ('pony', 'rabbit'):
        raise ValueError('Equine/lapine module only handles pony and rabbit')
    edits = _eye_fields(g, kind)
    if kind == 'pony':
        removed, made = _caelo_hair(g, rig)
        notes = ('Rebuilt diagonally rolled cloud-blue forelock, layered neck crescents and full S-shaped tail; '
                 'coherently tapered eyes/socket/lids with deeper blue irises and warm muzzle planes. '
                 'Original rig, action curves and detachable outfit retained.')
    else:
        edits += _rabbit_shape(g)
        removed, made = _rabbit_fur(g, rig)
        notes = ('Outward swept guarded ears and fuller haunch; rebuilt overlapping cream cheek cushions and '
                 'swept cotton-tail plume. Coherently tapered eyes/socket/lids and lavender-blue iris palette. '
                 'Original rig, action curves and detachable outfit retained.')
    painted = _coat_color(g, kind)
    return {'notes': notes, 'edited_objects': edits, 'added_base_clothing': [],
            'replaced_source_objects': removed, 'new_sculpture_objects': [o.name for o in made],
            'repainted_head_surfaces': painted, 'ocular_change': 'Coherent eye, eyelid, lash and skull field; original bone centers and actions retained.',
            'likeness_limit': 'Single-view reference does not establish hidden geometry. Authored closer likeness, not exact 1:1 acceptance.'}

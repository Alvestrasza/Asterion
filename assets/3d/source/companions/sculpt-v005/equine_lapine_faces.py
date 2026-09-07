"""Face-only, original-reference-led Caelo and Liora refinement.

Continuous sculpted socket rims join the colored ocular surface to the actual
skull. Original lid pivots and uniform-scale presentation actions are retained;
the expanding-disk intermediate blink is not claimed to be an anatomical blink.
All original shared materials are copied before any facial material edit.
"""
from __future__ import annotations

import math
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

DEPENDENCIES = []


def _world(obj):
    p = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', p)
    m = np.asarray(obj.matrix_world, dtype=float)
    return p.reshape((-1, 3)).astype(float) @ m[:3, :3].T + m[:3, 3]


def _write(obj, points):
    if not np.isfinite(points).all():
        raise ValueError('Nonfinite facial sculpture: ' + obj.name)
    inverse = np.linalg.inv(np.asarray(obj.matrix_world, dtype=float))
    local = points @ inverse[:3, :3].T + inverse[:3, 3]
    obj.data.vertices.foreach_set('co', local.astype(np.float32).ravel())
    obj.data.update()


def _colors(obj, colors):
    layer = obj.data.color_attributes.get('AST_eye_color')
    if layer is None:
        layer = obj.data.color_attributes.new(name='AST_eye_color', type='FLOAT_COLOR', domain='POINT')
    if layer.domain != 'POINT' or len(colors) != len(layer.data):
        raise ValueError('Unexpected facial color domain')
    values = np.asarray(colors, dtype=np.float32)
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite facial paint')
    layer.data.foreach_set('color', np.clip(values, 0, 1).ravel())


def _bind(obj, rig, kind, part='head', pivot=None):
    if part not in rig.data.bones:
        raise ValueError('Unknown original face bone: ' + part)
    obj['ast_part'] = part
    obj['asterion_component'] = 'body'
    obj['asterion_rig'] = kind + '-rig-v1'
    obj.parent = rig
    obj.vertex_groups.clear()
    obj.vertex_groups.new(name=part).add(list(range(len(obj.data.vertices))), 1., 'REPLACE')
    armature = obj.modifiers.new('Unchanged original face rig', 'ARMATURE')
    armature.object = rig
    if pivot is not None:
        obj['ast_lid_pivot'] = list(pivot)
    return obj


def allowed_faces(objects, kind):
    prefix = 'AST_caelo_v2_' if kind == 'pony' else 'AST_liora_v2_'
    suffixes = ('head', 'eye_', 'nostril_', 'smile_') if kind == 'pony' else (
        'head', 'eye_', 'soft_rose_nose', 'philtrum', 'gentle_smile_', 'whisker_pore_')
    return [o for o in objects if any(o.name == prefix + s or (s.endswith('_') and o.name.startswith(prefix + s)) for s in suffixes)]


def _material(g, name, tint, roughness=.45, vertex=False):
    mat = g.material(name, tint, 0., roughness)
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Specular IOR Level'].default_value = .23
    if vertex:
        node = mat.node_tree.nodes.new('ShaderNodeVertexColor')
        node.layer_name = 'AST_eye_color'
        mat.node_tree.links.new(node.outputs['Color'], bsdf.inputs['Base Color'])
    return mat


class _Skin:
    def __init__(self, obj):
        self.object = obj
        self.positions = [Vector(p) for p in _world(obj)]
        self.bvh = BVHTree.FromPolygons(self.positions, [list(p.vertices) for p in obj.data.polygons])
        self.kd = KDTree(len(self.positions))
        for index, p in enumerate(self.positions):
            self.kd.insert(p, index)
        self.kd.balance()
        layer = obj.data.color_attributes.get('AST_eye_color')
        self.colors = ([tuple(c.color) for c in layer.data] if layer is not None else
                       [tuple(obj.data.materials[0].diffuse_color)] * len(self.positions))

    def color(self, point):
        _, index, _ = self.kd.find(point)
        return self.colors[index]

    def front(self, x, z, clearance=0.):
        hit, _, _, _ = self.bvh.ray_cast(Vector((x, -5., z)), Vector((0, 1, 0)))
        if hit is None:
            raise ValueError('Facial landmark lacks continuous skull support')
        return hit + Vector((0, -clearance, 0))


def _sculpt_head(head, kind):
    # Single-user data and a private material copy isolate the body, ears,
    # old mane and all outfit shaders from this deliberately facial revision.
    if head.data.users > 1:
        head.data = head.data.copy()
    for index, material in enumerate(head.data.materials):
        copied = material.copy()
        copied.name = material.name + '_face_v005'
        head.data.materials[index] = copied
    before = _world(head)
    p = before.copy()
    if kind == 'pony':
        zone = np.clip((-p[:, 1] - 1.68) / .39, 0, 1) * np.clip((3.20 - p[:, 2]) / .32, 0, 1)
        p[:, 0] *= 1 + .105 * zone
        p[:, 1] += .027 * zone
        # A low, softly rounded paired muzzle instead of a pointed muzzle lip.
        muzzle = np.exp(-((p[:, 0] / .30) ** 4) - ((p[:, 2] - 2.97) / .16) ** 4)
        p[:, 1] -= .018 * muzzle * np.clip((-p[:, 1] - 1.65) / .35, 0, 1)
        nares = np.exp(-((np.abs(p[:, 0]) - .199) / .032) ** 2 - ((p[:, 2] - 3.060) / .021) ** 2)
        p[:, 1] += .012 * nares * np.clip((-p[:, 1] - 1.94) / .12, 0, 1)
    else:
        # Slightly fuller paired whisker pads, centered on the small heart nose.
        pad = np.exp(-((np.abs(p[:, 0]) - .20) / .17) ** 4 - ((p[:, 2] - 2.105) / .15) ** 4)
        p[:, 1] -= .041 * pad * np.clip((-p[:, 1] - 1.20) / .35, 0, 1)
    _write(head, p)
    return {'name': head.name, 'operation': 'Species-specific soft muzzle planes on original facial skin only',
            'max_displacement': float(np.linalg.norm(p - before, axis=1).max())}


def _eye(g, rig, kind, side, pivot, skin, skin_material, materials):
    sign = 1 if side == 'L' else -1
    name = ('caelo' if kind == 'pony' else 'liora') + '_v5_eye_' + side
    n = Vector((sign * (.60 if kind == 'pony' else .55), -.80 if kind == 'pony' else -.835, .035 if kind == 'pony' else .03)).normalized()
    u = Vector((0, 0, 1)).cross(n).normalized()
    v = n.cross(u).normalized()
    old_center = Vector(pivot) - n * (.029 if kind == 'pony' else .031)
    center = old_center - n * .024
    width, height = (.542, .515) if kind == 'pony' else (.545, .487)
    segments, rings = 192, 96
    def outline(angle, scale=1.):
        q = math.cos(angle)
        upper = math.sin(angle) >= 0
        if upper:
            z = height * .55 * max(0, 1 - q * q) ** .59 * (1 + .07 * sign * q)
        else:
            z = -height * .435 * max(0, 1 - q * q) ** .75
        z += sign * q * .032
        return width * .5 * q * scale, z * scale
    def ocular(x, z, radius):
        # The eye lives behind the flesh rim, with restrained ocular curvature.
        return center + u * x + v * z + n * (.022 * (1 - min(1, radius) ** 2))
    eye_vertices, faces, eye_colors = [], [], []
    white = np.array(g.color('F4E8D4'))
    dark = np.array(g.color('070C18'))
    upper = np.array(g.color('203052' if kind == 'pony' else '3C315F'))
    middle = np.array(g.color('5076B5' if kind == 'pony' else '70739E'))
    lower = np.array(g.color('83C8EB' if kind == 'pony' else '93C6DB'))
    for row in range(rings + 1):
        radius = max(.00001, row / rings)
        for col in range(segments):
            angle = math.tau * col / segments
            x, z = outline(angle, radius)
            eye_vertices.append(ocular(x, z, radius))
            # The upper iris continues behind the upper lid, as in the
            # approved portraits: do not leave a surprised white halo above it.
            iris = math.sqrt((x / (width * .395)) ** 2 + ((z - height * .045) / (height * .500)) ** 2)
            pupil = math.sqrt((x / (width * .240)) ** 2 + ((z - height * .060) / (height * .315)) ** 2)
            shade = .78 + .22 * (1 - max(0, z / (height * .6)))
            color = white * shade
            sclera = color.copy()
            if iris < 1.015:
                amount = max(0, min(1, .27 - z / (height * .85)))
                split = min(1, amount * 1.65)
                color = upper * (1 - split) + middle * split
                light = max(0, min(1, (amount - .40) * 1.7))
                color = color * (1 - light) + lower * light
                fiber = .028 * math.sin(angle * 73 + iris * 17) + .021 * math.sin(angle * 113 - iris * 23)
                shade = (.93 + fiber) * (.26 + .74 * min(1, (1 - iris) / .09))
                phi = math.atan2((z - height * .045) / (height * .500), x / (width * .395))
                sector = math.floor((phi + math.pi) / math.tau * 13)
                facet = .90 + .11 * math.sin(sector * 2.31 + .7) + .05 * math.sin(sector * 4.7)
                shade *= 1 + (facet - 1) * max(0, min(1, (iris - .48) / .30))
                shade *= 1 - .14 * math.exp(-((pupil - 1.105) / .09) ** 2)
                color *= shade
                edge = max(0, min(1, (iris - .985) / .030))
                edge = edge * edge * (3 - 2 * edge)
                color = color * (1 - edge) + sclera * edge
            if pupil < 1:
                t = max(0, min(1, (pupil - .97) / .03))
                color = dark * (1 - t) + color * t
            color[3] = 1
            eye_colors.append(color)
    for row in range(rings):
        for col in range(segments):
            a, b = row * segments + col, row * segments + (col + 1) % segments
            faces.append((a, a + segments, b + segments, b))
    eye = g.mesh(name, eye_vertices, faces, materials['eye'], 'head')
    eye['eye_side'] = side
    _colors(eye, eye_colors)
    _bind(eye, rig, kind)
    # A broad continuous annulus makes actual flesh, not an isolated colored
    # sticker. Its outer edge is measured on the original skull in every ray.
    annulus_vertices, annulus_faces, annulus_colors = [], [], []
    edges = []
    for col in range(segments):
        a = math.tau * col / segments
        x, z = outline(a, 1.015)
        inner = ocular(x, z, 1.) + n * .011
        for scale in (1.42, 1.50, 1.62, 1.78, 1.95):
            xx, zz = outline(a, scale)
            probe = old_center + u * xx + v * zz
            hit, normal, _, _ = skin.bvh.ray_cast(probe + n * 1.5, -n, 3.)
            if hit is not None and abs((hit - probe).dot(n)) < .39:
                break
        else:
            raise ValueError('Cannot seal original ocular socket at ' + name)
        edges.append((inner, hit, normal, scale))
    band_rows = 36
    for row in range(band_rows + 1):
        t = row / band_rows
        for col, (inner, outer, outer_normal, outer_scale) in enumerate(edges):
            angle = math.tau * col / segments
            xx, zz = outline(angle, 1.015 + (outer_scale - 1.015) * t)
            probe = old_center + u * xx + v * zz
            # C1 depth interpolation retains the skull tangent, unlike a
            # smoothstep applied to all XYZ coordinates (a visible patch rim).
            transverse = (outer - inner) - n * (outer - inner).dot(n)
            end_slope = -outer_normal.dot(transverse) / max(.20, outer_normal.dot(n))
            depth0, depth1 = (inner - old_center).dot(n), (outer - old_center).dot(n)
            depth = (2*t**3 - 3*t*t + 1) * depth0 + (-2*t**3 + 3*t*t) * depth1 + (t**3-t*t) * end_slope
            p = probe + n * depth
            hit, _, _, _ = skin.bvh.ray_cast(probe + n * 1.5, -n, 3.)
            if hit is not None and t > .50 and abs((hit - p).dot(n)) < .040:
                blend = min(1., (t - .50) / .45)
                blend = blend * blend * (3 - 2 * blend)
                p = p.lerp(hit, blend)
            # Bury the final narrow border, so no independent seam or
            # coplanar shell remains visible on the actual head surface.
            p += n * (.0012 - .0042 * max(0., (t - .88) / .12))
            annulus_vertices.append(p)
            color = np.array(skin.color(p))
            # The inner lower waterline has a very subtle warm transition.
            warm = (1 - t) ** 3 * .025
            color[:3] *= (1, 1 - warm, 1 - warm * 1.2)
            annulus_colors.append(color)
    for row in range(band_rows):
        for col in range(segments):
            a, b = row * segments + col, row * segments + (col + 1) % segments
            annulus_faces.append((a, a + segments, b + segments, b))
    # Relax only the interior support band. Ray transitions at the old boolean
    # cavity can otherwise make small radial shading fans under a lower lid.
    # Both exact boundary loops remain fixed, so socket fit is not loosened.
    band = np.asarray(annulus_vertices, dtype=float).reshape((band_rows + 1, segments, 3))
    paint = np.asarray(annulus_colors, dtype=float).reshape((band_rows + 1, segments, 4))
    gain = np.sin(np.linspace(0, math.pi, band_rows + 1))[:, None, None] ** 2
    for _ in range(18):
        for grid in (band, paint):
            avg = (np.roll(grid, 1, axis=1) + np.roll(grid, -1, axis=1) +
                   np.roll(grid, 1, axis=0) + np.roll(grid, -1, axis=0)) * .25
            grid += .48 * gain * (avg - grid)
    annulus_vertices = [Vector(p) for p in band.reshape((-1, 3))]
    annulus_colors = paint.reshape((-1, 4))
    annulus = g.mesh(name + '_integrated_orbital_flesh', annulus_vertices, annulus_faces, skin_material, 'head')
    _colors(annulus, annulus_colors)
    _bind(annulus, rig, kind)
    # A dark tapered upper lash and quiet flesh-colored lower waterline replace
    # the old continuous dark oval outline. The upper outer corner is lifted.
    for top in (True, False):
        a0, a1 = (0., math.pi) if top else (math.pi, math.tau)
        pts = [ocular(*outline(a0 + (a1 - a0) * j / 40), 1.) + n * .013 for j in range(41)]
        widths = [(.002 + .024 * math.sin(math.pi * j / 40) ** .60 * (1 + .48 * sign * math.cos(math.pi * j / 40))) if top else .007 for j in range(41)]
        obj = g.sweep(name + ('_tapered_upper_lash' if top else '_lower_waterline'), pts, widths,
                      [w * .48 for w in widths], materials['lash'] if top else materials['waterline'], 'head',
                      normal=n, steps=104, sides=20)
        _bind(obj, rig, kind)
    outer_x = sign * width * .485
    wing = [ocular(*outline(.20 if sign > 0 else math.pi - .20), 1.) + n * .014,
            ocular(outer_x + sign * .034, .108, 1.) + n * .012,
            ocular(outer_x + sign * .083, .151, 1.) + n * .005]
    obj = g.sweep(name + '_outer_lash_wing', wing, [.011, .017, .0006], [.004, .008, .0004],
                  materials['lash'], 'head', normal=n, steps=42, sides=20)
    _bind(obj, rig, kind)
    if kind == 'pony':
        band_bvh = BVHTree.FromPolygons(annulus_vertices, annulus_faces)
        pts = []
        for x, z in ((-.135, .350), (-.045, .387), (.066, .388), (.160, .350)):
            probe = old_center + u * (sign * x) + v * (z - .045)
            hit, _, _, _ = skin.bvh.ray_cast(probe + n, -n, 2.)
            if hit is None:
                raise ValueError('Blue brow lacks facial support')
            band_hit, _, _, _ = band_bvh.ray_cast(probe + n, -n, 2.)
            if band_hit is not None and (band_hit - hit).dot(n) > 0:
                hit = band_hit
            pts.append(hit + n * .004)
        obj = g.sweep(name + '_soft_blue_brow', pts, [.001, .023, .019, .001], [.001, .004, .004, .001],
                      materials['brow'], 'head', normal=n, steps=56, sides=20)
        _bind(obj, rig, kind)
    # Small corneal catchlight clusters. The iris shader carries the remaining
    # wet highlight; no giant white disk or outline highlight is introduced.
    for suffix, x, z, rx, rz in (('catchlight', -.066, .126, .030, .035), ('pinlight', .093, -.132, .008, .012)):
        radius = math.sqrt((x / (width * .5)) ** 2 + (z / (height * .5)) ** 2)
        obj = g.disk(name + '_' + suffix, ocular(x, z, radius) + n * .004,
                     u, v, n, rx, rz, materials['glint'], 'head', bulge=.001, rings=10, seg=48)
        _bind(obj, rig, kind)
    # Exactly the same original pivot. Full closed lids cover the new eye with
    # a conservative rim margin; original scaling semantics are unchanged.
    lid_vertices = []
    for p in eye_vertices:
        d = p - old_center
        lid_vertices.append(old_center + u * d.dot(u) * 1.060 + v * d.dot(v) * 1.045 + n * (d.dot(n) + .037))
    original_name = ('caelo' if kind == 'pony' else 'liora') + '_v2_eye_' + side
    lid = g.mesh(original_name + '_closed_lid', lid_vertices, faces, skin_material, 'lid.' + side)
    # Sampling a hollow socket's nearest surface by angle creates a starburst
    # on a closed lid. Use the averaged surrounding flesh with restrained
    # world-space color variation instead of spreading cavity-wall colors.
    lid_base = np.mean([skin.color(edge[1]) for edge in edges], axis=0)
    lid_colors = []
    for p in lid_vertices:
        color = lid_base.copy()
        grain = .994 + .006 * math.sin(p.z * 117 + math.sin(p.x * 82)) * math.sin(p.x * 113 + .4 * p.y)
        color[:3] *= grain
        lid_colors.append(color)
    _colors(lid, lid_colors)
    _bind(lid, rig, kind, 'lid.' + side, pivot)
    closed_pts = [old_center + u * (width * .45 * q) + v * (-height * .105 * (1 - q * q)) + n * (.018 + .023 * (1 - q * q))
                  for q in (-1, -.75, -.5, -.25, 0, .25, .5, .75, 1)]
    closed = g.sweep(original_name + ('_sleeping_lash' if kind == 'pony' else '_closed_lash'), closed_pts, [.001, .008, .012, .008, .001], [.001, .004, .006, .004, .001],
                     materials['lash'], 'lid.' + side, normal=n, steps=64, sides=16)
    _bind(closed, rig, kind, 'lid.' + side, pivot)


def _mouth(g, rig, kind, skin, materials):
    prefix = 'caelo_v5_' if kind == 'pony' else 'liora_v5_'
    if kind == 'pony':
        for sign in (-1, 1):
            pts = [skin.front(sign * x, z, .004) for x, z in ((0, 2.850), (.082, 2.853), (.177, 2.876), (.240, 2.913), (.259, 2.936))]
            obj = g.sweep(prefix + 'soft_smile_' + str(sign), pts, [.002, .004, .0055, .006, .001],
                          [.001, .0025, .003, .003, .0007], materials['mouth'], 'head', normal=(0, -1, 0), steps=72, sides=18)
            _bind(obj, rig, kind)
            pts = [skin.front(sign * x, z, .003) for x, z in ((.169, 3.037), (.185, 3.059), (.208, 3.069), (.224, 3.061))]
            obj = g.sweep(prefix + 'nostril_recess_' + str(sign), pts, [.001, .009, .008, .0008], [.001, .003, .003, .0005],
                          materials['nose'], 'head', normal=(0, -1, 0), steps=40, sides=20)
            _bind(obj, rig, kind)
    else:
        outline = [(-.081, 2.171), (-.062, 2.192), (-.027, 2.187), (0., 2.171), (.027, 2.187),
                   (.062, 2.192), (.081, 2.171), (.055, 2.144), (0, 2.114), (-.055, 2.144)]
        ring = [skin.front(x, z, .004) for x, z in outline]
        vertices = [skin.front(0, 2.160, .033)] + ring
        vertices += [skin.front(x, z, -.008) for x, z in outline]
        faces = [(0, j + 1, (j + 1) % len(ring) + 1) for j in range(len(ring))]
        faces += [(j + 1, j + 1 + len(ring), (j + 1) % len(ring) + 1 + len(ring), (j + 1) % len(ring) + 1) for j in range(len(ring))]
        faces.append(tuple(reversed(range(1 + len(ring), 1 + len(ring) * 2))))
        obj = g.mesh(prefix + 'rounded_heart_nose', vertices, faces, materials['nose'], 'head')
        mod = obj.modifiers.new('Soft nose edge', 'BEVEL'); mod.width = .005; mod.segments = 3; g.apply(obj, mod)
        mod = obj.modifiers.new('Rounded nose cushion', 'SUBSURF'); mod.levels = 1; g.apply(obj, mod)
        _bind(obj, rig, kind)
        pts = [skin.front(0, z, .004) for z in (2.117, 2.084, 2.057)]
        obj = g.sweep(prefix + 'short_philtrum', pts, [.003, .004, .003], [.0015, .002, .0015], materials['mouth'], 'head',
                      normal=(0, -1, 0), steps=28, sides=16)
        _bind(obj, rig, kind)
        for sign in (-1, 1):
            pts = [skin.front(sign * x, z, .004) for x, z in ((0, 2.058), (.055, 2.036), (.123, 2.044), (.197, 2.075), (.231, 2.109))]
            obj = g.sweep(prefix + 'gentle_smile_' + str(sign), pts, [.002, .004, .004, .0045, .0006],
                          [.001, .002, .002, .002, .0005], materials['mouth'], 'head', normal=(0, -1, 0), steps=72, sides=18)
            _bind(obj, rig, kind)
            for j in range(3):
                center = skin.front(sign * (.091 + j * .035), 2.154 + (j % 2) * .017, .002)
                obj = g.uv(prefix + 'whisker_pore_' + str(sign) + '_' + str(j), center, (.0028, .001, .0028),
                           materials['mouth'], 'head', seg=16, rings=12)
                _bind(obj, rig, kind)


def apply(g, rig, kind):
    if kind not in ('pony', 'rabbit'):
        raise ValueError('Unsupported equine/lapine face kind')
    prefix = 'AST_caelo_v2_' if kind == 'pony' else 'AST_liora_v2_'
    original = allowed_faces(g.ASSET, kind)
    original_names = [o.name for o in original]
    head = bpy.data.objects[prefix + 'head']
    pivots = {s: list(bpy.data.objects[prefix + 'eye_' + s + '_closed_lid']['ast_lid_pivot']) for s in ('L', 'R')}
    edits = [_sculpt_head(head, kind)]
    skin = _Skin(head)
    removed = []
    for obj in original:
        if obj == head:
            continue
        removed.append(obj.name)
        g.ASSET.remove(obj)
        bpy.data.objects.remove(obj, do_unlink=True)
    start = len(g.ASSET)
    tag = 'Caelo' if kind == 'pony' else 'Liora'
    materials = {
        'eye': _material(g, tag + '_v5_living_iris', 'FFFFFF', .24, True),
        'lash': _material(g, tag + '_v5_tapered_lash', '21180F' if kind == 'pony' else '38251D', .53),
        'waterline': _material(g, tag + '_v5_warm_waterline', 'CDBBA0', .63),
        'brow': _material(g, tag + '_v5_blue_brow', '8B9CA9', .63),
        'glint': _material(g, tag + '_v5_controlled_glint', 'FAFDFF', .25),
        'mouth': _material(g, tag + '_v5_muzzle_crease', '80604E', .67),
        'nose': _material(g, tag + '_v5_soft_nose', 'B9867A' if kind == 'pony' else 'BE8583', .48),
    }
    eye_bsdf = materials['eye'].node_tree.nodes.get('Principled BSDF')
    eye_bsdf.inputs['Specular IOR Level'].default_value = .12
    eye_bsdf.inputs['Coat Weight'].default_value = .025
    eye_bsdf.inputs['Coat Roughness'].default_value = .28
    for side in ('L', 'R'):
        _eye(g, rig, kind, side, pivots[side], skin, head.data.materials[0], materials)
    _mouth(g, rig, kind, skin, materials)
    added = [o.name for o in g.ASSET[start:]]
    for side in ('L', 'R'):
        obj = bpy.data.objects['AST_' + ('caelo' if kind == 'pony' else 'liora') + '_v5_eye_' + side]
        edits.append({'name': obj.name, 'operation': 'Replaced original ocular geometry with recessed arched opening, large dark pupil and layered reference iris paint',
                      'max_displacement': 0., 'new_vertices': len(obj.data.vertices)})
    removed = [name for name in removed if name not in added]
    return {'notes': 'Face-only recessed arched eyes, integrated orbital flesh, larger dark pupils, restrained corneal glints and species-specific muzzle expression.',
            'edited_objects': edits, 'face_objects': sorted(set(original_names + added)),
            'removed_face_objects': removed, 'added_base_clothing': [], 'added_face_objects': [name for name in added if name not in original_names],
            'face_frame': {'center': [0, -1.34, 3.25] if kind == 'pony' else [0, -1.07, 2.43],
                           'span': [1.88, 1.50, 1.46] if kind == 'pony' else [1.94, 1.35, 1.44]},
            'original_lid_pivots': pivots,
            'animation_limit': 'Original lid actions scale a closed mesh uniformly from its center; intermediate closure remains an expanding disk, not an anatomical blink.'}

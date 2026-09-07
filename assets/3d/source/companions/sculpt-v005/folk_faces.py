"""Facial-only reconstruction refinements on immutable woodland-folk masters.

No whole-character deformation, image projection or animation reauthoring.
Every edited shader is copied into a face-only material before modification.
"""
from __future__ import annotations

import math
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

DEPENDENCIES = []
NAMES = {'orc': 'Brumo', 'fairy': 'Selya', 'elf': 'Aelira'}
HEADS = {'orc': 'AST_Brumo_v2_head', 'fairy': 'AST_Selya_sculpted_head', 'elf': 'AST_Aelira_v2_refined_head'}
EYES = {'orc': 'AST_Brumo_v2_eye_', 'fairy': 'AST_Selya_eye_', 'elf': 'AST_Aelira_v2_eye_'}
FRAMES = {'orc': ((0, -.28, 2.74), (1.43, .94, 1.22)),
          'fairy': ((0, -.28, 3.30), (1.39, .92, 1.25)),
          'elf': ((0, -.25, 2.87), (1.20, .86, 1.19))}


def coords(obj):
    p = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', p)
    matrix = np.asarray(obj.matrix_world, dtype=np.float64)
    return p.reshape((-1, 3)).astype(np.float64) @ matrix[:3, :3].T + matrix[:3, 3]


def write(obj, p, records, operation):
    before = coords(obj)
    if not np.isfinite(p).all():
        raise ValueError('Nonfinite facial surface: ' + obj.name)
    inverse = np.asarray(obj.matrix_world.inverted(), dtype=np.float64)
    obj.data.vertices.foreach_set('co', (p @ inverse[:3, :3].T + inverse[:3, 3]).astype(np.float32).ravel())
    obj.data.update()
    distance = float(np.linalg.norm(p - before, axis=1).max(initial=0))
    records.append({'name': obj.name, 'operation': operation, 'max_displacement': distance})


def smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def colors(obj, values):
    attr = obj.data.color_attributes.get('AST_eye_color')
    if attr is None:
        attr = obj.data.color_attributes.new(name='AST_eye_color', type='FLOAT_COLOR', domain='POINT')
    attr.data.foreach_set('color', np.asarray(values, dtype=np.float32).ravel())


def allowed(obj, kind):
    if obj.name == HEADS[kind] or obj.name.startswith(EYES[kind]):
        return True
    prefix = 'AST_' + NAMES[kind] + '_'
    return obj.name.startswith(prefix) and any(token in obj.name for token in (
        '_nostril_', '_gentle_smile', '_warm_smile', '_lower_lip', '_smile_',
        '_expressive_brow_', '_arched_brow_', '_v2_brow_', '_upturned_tusk_'))


def role(obj, kind):
    name = obj.name
    if name == HEADS[kind] or any(s in name for s in ('orbital_skin', 'closed_lid', 'lower_lid', 'lower_skin_lid')):
        return 'skin'
    if name in (EYES[kind] + 'L', EYES[kind] + 'R'):
        return 'eye'
    if 'lash' in name:
        return 'ink'
    if 'brow' in name:
        return 'brow'
    if 'nostril' in name:
        return 'nostril'
    if 'smile' in name or 'lip' in name:
        return 'lip'
    if 'tusk' in name:
        return 'tusk'
    return 'glint'


def isolated_materials(objects, kind):
    cache = {}
    for obj in objects:
        obj.data = obj.data.copy()
        family = role(obj, kind)
        for i, original in enumerate(list(obj.data.materials)):
            key = (original.as_pointer(), family)
            if key not in cache:
                material = original.copy()
                material.name = NAMES[kind] + '_v5_face_' + family + '_' + original.name
                bsdf = material.node_tree.nodes.get('Principled BSDF')
                if family == 'skin':
                    bsdf.inputs['Roughness'].default_value = .64
                    bsdf.inputs['Specular IOR Level'].default_value = .16
                    node = next((n for n in material.node_tree.nodes if n.type == 'VERTEX_COLOR'), None)
                    if node is None:
                        node = material.node_tree.nodes.new('ShaderNodeVertexColor')
                    node.layer_name = 'AST_eye_color'
                    material.node_tree.links.new(node.outputs['Color'], bsdf.inputs['Base Color'])
                elif family == 'eye':
                    bsdf.inputs['Roughness'].default_value = .32
                    bsdf.inputs['Specular IOR Level'].default_value = .09
                cache[key] = material
            obj.data.materials[i] = cache[key]
    return len(cache)


def orbital_warp(p, centers, kind):
    result = p.copy()
    for c, rx, rz, sign in centers:
        d = p - c
        x = d[:, 0] / rx
        z = d[:, 2] / rz
        radial = np.maximum(np.abs(x), np.abs(z))
        influence = (1 - smooth((radial - 1.12) / .78)) * (1 - smooth((d[:, 1] - .045) / .19))
        # Keep the zero of this warp at the original lid scale pivot. Local
        # corner shaping changes the opening without translating the eye.
        corner = smooth(np.abs(x) / 1.1)
        contraction = {'orc': .11, 'fairy': .075, 'elf': .11}[kind]
        dz = -d[:, 2] * contraction * corner
        dz += {'orc': .011, 'fairy': .009, 'elf': .009}[kind] * sign * np.clip(x, -1.2, 1.2)
        result[:, 2] += dz * influence
    return result


def orbital_fits(centers, kind):
    fits = {}
    segments = 128 if kind == 'fairy' else 144
    for side, (c, rx, rz, sign) in zip(('L', 'R'), centers):
        obj = next(o for o in bpy.context.scene.objects if o.name.startswith(EYES[kind] + side) and 'orbital_skin' in o.name)
        rings = orbital_warp(coords(obj), centers, kind).reshape((13, segments, 3))
        inner = rings[0]
        outer = primary_forms(rings[-1], kind)
        d = inner - c
        features = np.column_stack((d[:, 0], d[:, 2], d[:, 0] ** 2,
                                    d[:, 2] ** 2, d[:, 0] * d[:, 2]))
        coefficients = np.linalg.lstsq(features, outer[:, 1] - inner[:, 1], rcond=None)[0]
        fits[side] = {'coefficients': coefficients, 'outer': outer,
                      'edge_rms_before': float(np.sqrt(np.mean((outer[:, 1] - inner[:, 1]) ** 2))),
                      'edge_rms_after': float(np.sqrt(np.mean((features @ coefficients - (outer[:, 1] - inner[:, 1])) ** 2)))}
    return fits


def ocular_depth_fit(obj, p, centers, kind, fits):
    side = 'L' if obj.name.startswith(EYES[kind] + 'L') else 'R'
    c, rx, rz, sign = centers[0 if side == 'L' else 1]
    dx = p[:, 0] - c[0]
    dz = p[:, 2] - c[2]
    a, b, cxx, czz, cxz = fits[side]['coefficients']
    # A zero-offset fitted surface retains the original scale pivot. The
    # vertical slope is essential: the lower cheek root is forward of the
    # old eye plane whereas the upper/temporal root lies behind that plane.
    curvature = cxx * dx * dx + czz * dz * dz + cxz * dx * dz
    depth = a * dx + b * dz + curvature
    if role(obj, kind) in ('eye', 'glint'):
        # Seat the corneal crown a little deeper while preserving its exact
        # rim. This also restores clearance beneath the unchanged lid scale
        # sequence instead of moving the lid pivot or reauthoring a blink.
        radial_squared = (dx / rx) ** 2 + (dz / rz) ** 2
        depth += .014 * np.clip(1 - radial_squared, 0, 1)
    p[:, 1] += depth
    if 'orbital_skin' in obj.name:
        segments = 128 if kind == 'fairy' else 144
        if len(p) != 13 * segments:
            raise ValueError('Unexpected authored orbital annulus topology')
        rings = p.reshape((13, segments, 3))
        # Replace the former projecting flange with a fitted narrow skin
        # transition. The root is the actual face boundary, never an overlay
        # left floating in front of the cheek.
        inner = rings[0].copy()
        outer = fits[side]['outer']
        for i, t in enumerate(np.linspace(0, 1, 13)):
            rings[i] = inner * (1 - t) + outer * t
    return p


def primary_forms(p, kind):
    q = p.copy()
    front = 1 - smooth((p[:, 1] + .20) / .28)
    x, z = p[:, 0], p[:, 2]
    if kind == 'orc':
        jaw = np.exp(-((z - 2.39) / .20) ** 2) * front
        q[:, 0] *= 1 + .060 * jaw
        cheek = np.exp(-((np.abs(x) - .37) / .19) ** 2 - ((z - 2.49) / .20) ** 2) * front
        q[:, 1] += .012 * cheek
        nose = np.exp(-(x / .19) ** 4 - ((z - 2.535) / .145) ** 4) * (1 - smooth((p[:, 1] + .58) / .13))
        q[:, 0] *= 1 + .14 * nose
        q[:, 2] += (2.535 - z) * .13 * nose
        q[:, 1] += .014 * nose
    elif kind == 'fairy':
        lower = np.exp(-((z - 2.99) / .17) ** 2) * front
        q[:, 0] *= 1 + .032 * lower
        q[:, 2] += .015 * np.exp(-((z - 2.81) / .105) ** 2) * front
        cheek = np.exp(-((np.abs(x) - .37) / .21) ** 2 - ((z - 3.075) / .19) ** 2) * front
        q[:, 1] -= .018 * cheek
        nose = np.exp(-(x / .09) ** 4 - ((z - 3.07) / .09) ** 4) * (1 - smooth((p[:, 1] + .53) / .08))
        q[:, 1] -= .008 * nose
    else:
        chin = np.exp(-((z - 2.45) / .155) ** 2) * front
        q[:, 0] *= 1 - .045 * chin
        cheek = np.exp(-((np.abs(x) - .29) / .15) ** 2 - ((z - 2.70) / .155) ** 2) * front
        q[:, 1] -= .016 * cheek
        # Delicate nasolabial/lip support, not a lengthened pointed muzzle.
        q[:, 1] -= .009 * np.exp(-(x / .12) ** 2 - ((z - 2.535) / .055) ** 2) * front
    return q


def paint_skin(g, obj, kind, centers):
    p = coords(obj)
    attr = obj.data.color_attributes.get('AST_eye_color')
    previous = np.ones((len(p), 4), dtype=np.float32)
    if attr is not None:
        attr.data.foreach_get('color', previous.ravel())
    base, blush, glow = [np.array(g.color(h)[:3]) for h in {
        'orc': ('77703C', '9D7044', 'AB995A'),
        'fairy': ('C48246', 'CA6747', 'E5AB70'),
        'elf': ('BB7D49', 'C2694A', 'DBA26D')}[kind]]
    front = 1 - smooth((p[:, 1] + .18) / .26)
    zc = {'orc': 2.47, 'fairy': 3.105, 'elf': 2.72}[kind]
    xc = {'orc': .36, 'fairy': .38, 'elf': .30}[kind]
    cheek = np.exp(-((np.abs(p[:, 0]) - xc) / .17) ** 2 - ((p[:, 2] - zc) / .105) ** 2)
    face = np.tile(base * {'orc': .76, 'fairy': .85, 'elf': .85}[kind], (len(p), 1))
    warm = cheek * (.26 if kind == 'orc' else .38)
    face = face * (1 - warm[:, None]) + blush[None, :] * warm[:, None] * .83
    ridge = np.exp(-(p[:, 0] / .22) ** 2 - ((p[:, 2] - (zc + .34)) / .35) ** 2)
    face = face * (1 - .07 * ridge[:, None]) + glow * (.07 * ridge[:, None])
    shade = np.ones(len(p))
    for c, rx, rz, sign in centers:
        x = (p[:, 0] - c[0]) / rx
        z = (p[:, 2] - c[2]) / rz
        r = np.sqrt(x * x + z * z)
        orbital = np.exp(-((r - 1.1) / .29) ** 2) * smooth((z + .10) / .8)
        shade *= 1 - .23 * orbital
    chin_z = {'orc': 2.29, 'fairy': 2.85, 'elf': 2.38}[kind]
    shade *= 1 - .16 * np.exp(-((p[:, 2] - chin_z) / .105) ** 2)
    pigment = 1 + .018 * np.sin(p[:, 0] * 43 + p[:, 2] * 31) * np.sin(p[:, 1] * 47 - p[:, 2] * 21)
    face *= (shade * pigment)[:, None]
    values = previous.astype(np.float64)
    values[:, :3] = values[:, :3] * (1 - front[:, None]) + face * front[:, None]
    values[:, 3] = 1
    colors(obj, values)


def paint_eye(g, obj, kind, side):
    p = coords(obj)
    n = Vector(((.19 if kind == 'fairy' else .24) * (1 if side == 'L' else -1), -.981 if kind == 'fairy' else -.97, .025 if kind == 'fairy' else .018)).normalized()
    u = Vector((0, 0, 1)).cross(n).normalized()
    v = n.cross(u).normalized()
    x, z = p @ np.array(u), p @ np.array(v)
    x -= (x.min() + x.max()) / 2
    z -= (z.min() + z.max()) / 2
    rx, rz = np.max(np.abs(x)), np.max(np.abs(z))
    x /= rx; z /= rz
    radius = np.sqrt((x / .83) ** 2 + ((z + .04) / .98) ** 2)
    px, pz = {'orc': (.46, .60), 'fairy': (.44, .58), 'elf': (.46, .60)}[kind]
    pupil = np.sqrt((x / px) ** 2 + ((z - .11) / pz) ** 2)
    upper, middle, lower = [np.array(g.color(h)[:3]) for h in {
        'orc': ('251209', '87400C', 'CA851F'),
        'fairy': ('071C19', '174838', '3C8765'),
        'elf': ('170A1C', '49205B', '9459AF')}[kind]]
    # Preserve the artwork's shaded upper iris and luminous lower crescent;
    # a linear mix in linear-light color made most of the iris pastel.
    f = np.clip(.36 - z * .64, 0, 1) ** 2.2
    iris = upper * (1 - f[:, None]) + lower * f[:, None]
    iris = iris * .85 + middle * .15
    a = np.arctan2(z, x)
    fibers = 1 + .062 * np.sin(a * 53 + radius * 18) + .033 * np.sin(a * 89 - radius * 13)
    limb = .33 + .67 * (1 - smooth((radius - .84) / .16))
    iris *= (fibers * limb)[:, None]
    ivory = np.array(g.color('E7D7BC')[:3])
    color = np.tile(ivory, (len(p), 1)) * (.77 + .23 * np.clip(-z, 0, 1))[:, None]
    iris_blend = 1 - smooth((radius - .97) / .06)
    color = color * (1 - iris_blend[:, None]) + iris * iris_blend[:, None]
    dark = np.array(g.color('070B10' if kind == 'elf' else '080C09')[:3])
    pupil_blend = 1 - smooth((pupil - .96) / .07)
    color = color * (1 - pupil_blend[:, None]) + dark * pupil_blend[:, None]
    colors(obj, np.column_stack((color, np.ones(len(p)))))
    return {'name': obj.name, 'pupil_half_width_fraction': px, 'pupil_half_height_fraction': pz,
            'iris_half_width_fraction': .83, 'iris_half_height_fraction': .98}


def apply(g, rig, kind):
    if kind not in NAMES:
        raise ValueError('Unsupported facial companion: ' + kind)
    objects = [obj for obj in g.ASSET if allowed(obj, kind)]
    if not objects or HEADS[kind] not in {obj.name for obj in objects}:
        raise ValueError('Approved facial source objects missing')
    records = []
    material_count = isolated_materials(objects, kind)
    centers = []
    for side in ('L', 'R'):
        eye = bpy.data.objects[EYES[kind] + side]
        p = coords(eye)
        c = np.array(rig.data.bones['lid.' + side].head_local)
        centers.append((c, (p[:, 0].max() - p[:, 0].min()) / 2,
                        (p[:, 2].max() - p[:, 2].min()) / 2, 1 if side == 'L' else -1))
    fits = orbital_fits(centers, kind)
    for obj in objects:
        p = coords(obj)
        if obj.name == HEADS[kind] or obj.name.startswith(EYES[kind]) or 'brow' in obj.name:
            write(obj, orbital_warp(p, centers, kind), records, 'pivot_fixed_continuous_arch_and_socket_corner_shape')
        if obj.name.startswith(EYES[kind]):
            write(obj, ocular_depth_fit(obj, coords(obj), centers, kind, fits), records,
                  'curved_eye_and_inner_orbit_with_fixed_skull_join_and_lid_pivot')
        if obj.name == HEADS[kind] or any(s in obj.name for s in ('nostril', 'smile', 'lip', 'tusk')):
            write(obj, primary_forms(coords(obj), kind), records, 'species_specific_cheek_chin_nose_and_lip_support')
        if kind == 'orc' and 'upturned_tusk' in obj.name:
            q = coords(obj)
            q[:, 2] = 2.340 + (q[:, 2] - 2.340) * .76
            center_x = q[:, 0].mean()
            q[:, 0] = center_x + (q[:, 0] - center_x) * 1.10
            write(obj, q, records, 'shorter_broader_friendly_ivory_tusk')
        if kind == 'orc' and 'gentle_smile' in obj.name:
            q = coords(obj)
            q[:, 0] *= .94
            q[:, 2] += .023 * np.clip(np.abs(q[:, 0]) / .35, 0, 1) ** 2
            write(obj, q, records, 'gently_raised_smile_corners_beside_short_tusks')
        if 'upper_lash' in obj.name or 'lower_lid' in obj.name or 'lower_skin_lid' in obj.name:
            p = coords(obj)
            if len(p) % 20 != 0:
                raise ValueError('Unexpected authored lash tube topology')
            rings = p.reshape((-1, 20, 3))
            mid = rings.mean(axis=1, keepdims=True)
            factor = (1.18 if kind != 'fairy' else 1.10) if 'upper_lash' in obj.name else .48
            rings = mid + (rings - mid) * factor
            write(obj, rings.reshape((-1, 3)), records, 'tapered_upper_arch_and_slim_lower_lid_margin')
        family = role(obj, kind)
        if family == 'skin':
            paint_skin(g, obj, kind, centers)
        elif family in ('ink', 'nostril', 'lip'):
            tint = {'ink': '171410', 'nostril': '302619', 'lip': '302B1B' if kind == 'orc' else '5C3725'}[family]
            if 'lower_lip' in obj.name:
                tint = 'A06447'
            for material in obj.data.materials:
                bsdf = material.node_tree.nodes.get('Principled BSDF')
                for link in list(bsdf.inputs['Base Color'].links):
                    material.node_tree.links.remove(link)
                bsdf.inputs['Base Color'].default_value = g.color(tint)
                bsdf.inputs['Roughness'].default_value = .62
        records.append({'name': obj.name, 'operation': 'isolated_face_material_and_reference_value_structure', 'max_displacement': 0})
    head = bpy.data.objects[HEADS[kind]]
    tree = BVHTree.FromPolygons([head.matrix_world @ v.co for v in head.data.vertices],
                               [list(poly.vertices) for poly in head.data.polygons])
    for obj in objects:
        if 'orbital_skin' in obj.name:
            segments = 128 if kind == 'fairy' else 144
            p = coords(obj)
            for i in range(len(p) - segments, len(p)):
                hit, normal, _, distance = tree.find_nearest(Vector(p[i]))
                if hit is None or distance > .025:
                    raise ValueError('Orbital root no longer meets the actual facial skin')
                p[i] = np.array(hit - normal * .001)
            write(obj, p, records, 'orbital_outer_root_embedded_in_actual_facial_surface')
        if role(obj, kind) in ('lip', 'nostril'):
            p = coords(obj)
            if role(obj, kind) == 'lip' and kind != 'fairy' and len(p) % 10 == 0:
                rings = p.reshape((-1, 10, 3))
                middle = rings.mean(axis=1, keepdims=True)
                t = np.linspace(0, 1, len(rings))
                taper = (.12 + .68 * np.sin(math.pi * t) ** .5)[:, None, None]
                p = (middle + (rings - middle) * taper).reshape((-1, 3))
            for q in p:
                hit, _, _, _ = tree.ray_cast(Vector((q[0], -4, q[2])), Vector((0, 1, 0)))
                if hit is not None:
                    q[1] = hit.y - (.0015 if 'lower_lip' not in obj.name else .0025)
            write(obj, p, records, 'subtle_mouth_and_nostril_relief_seated_on_facial_skin')
        if 'brow' not in obj.name:
            continue
        sides = {'orc': 32, 'fairy': 20, 'elf': 28}[kind]
        p = coords(obj)
        if len(p) % sides:
            raise ValueError('Unexpected authored brow section topology')
        rings = p.reshape((-1, sides, 3))
        for ring in rings:
            c = ring.mean(axis=0)
            hit, _, _, _ = tree.ray_cast(Vector((c[0], -4, c[2])), Vector((0, 1, 0)))
            if hit is not None:
                ring[:, 1] += hit.y - c[1] - .004
        write(obj, rings.reshape((-1, 3)), records, 'brow_roots_seated_on_actual_facial_skin')
    irises = [paint_eye(g, bpy.data.objects[EYES[kind] + side], kind, side) for side in ('L', 'R')]
    center, span = FRAMES[kind]
    return {'edited_objects': records, 'face_objects': sorted(obj.name for obj in objects),
            'removed_face_objects': [], 'added_base_clothing': [],
            'face_frame': {'center': list(center), 'span': list(span)},
            'face_material_copies': material_count, 'iris_design': irises,
            'orbital_surface_fit': {side: {key: value.tolist() if isinstance(value, np.ndarray) else value
                for key, value in fit.items() if key in ('coefficients', 'edge_rms_before', 'edge_rms_after')} for side, fit in fits.items()},
            'original_lid_scale_pivots_unchanged': True,
            'notes': 'Facial-only sculpt, coherent pivot-fixed ocular arches, deeper broad irises and pupils, isolated warm skin value fields. Original body, joint shells, hair, ears, outfit and every action retained.'}

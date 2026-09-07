"""Primary-form likeness work for the three clothed woodland folk.

Applied to an immutable v003 master in memory. All displacements operate on
stored mesh vertices; the original rest skeleton and every action stay intact.
Pigment fields are authored three-dimensional colors, never image projection.
"""
from __future__ import annotations

import math
import bpy
import numpy as np
from mathutils import Vector

DEPENDENCIES = []
NAMES = {'orc': 'Brumo', 'fairy': 'Selya', 'elf': 'Aelira'}


def coords(obj):
    result = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', result)
    matrix = np.asarray(obj.matrix_world, dtype=np.float64)
    return result.reshape((-1, 3)).astype(np.float64) @ matrix[:3, :3].T + matrix[:3, 3]


def write(obj, points, records, operation):
    before = coords(obj)
    if not np.isfinite(points).all():
        raise ValueError('Nonfinite primary-form change: ' + obj.name)
    inverse = np.asarray(obj.matrix_world.inverted(), dtype=np.float64)
    local = points @ inverse[:3, :3].T + inverse[:3, 3]
    obj.data.vertices.foreach_set('co', local.astype(np.float32).ravel())
    obj.data.update()
    distance = float(np.linalg.norm(points - before, axis=1).max(initial=0))
    if distance > .000001:
        records.append({'name': obj.name, 'operation': operation, 'max_displacement': distance})


def smooth(value):
    value = np.clip(value, 0, 1)
    return value * value * (3 - 2 * value)


def color_field(obj, values):
    attr = obj.data.color_attributes.get('AST_eye_color')
    if attr is None:
        attr = obj.data.color_attributes.new(name='AST_eye_color', type='FLOAT_COLOR', domain='POINT')
    attr.data.foreach_set('color', np.asarray(values, dtype=np.float32).ravel())


def pigmented_material(g, original, kind):
    material = original.copy()
    material.name = 'AST_' + NAMES[kind] + '_v4_directional_hair_pigment'
    nodes = material.node_tree.nodes
    node = next((node for node in nodes if node.type == 'VERTEX_COLOR'), None)
    if node is None:
        node = nodes.new('ShaderNodeVertexColor')
    node.layer_name = 'AST_eye_color'
    material.node_tree.links.new(node.outputs['Color'], nodes.get('Principled BSDF').inputs['Base Color'])
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Roughness'].default_value = .46
    bsdf.inputs['Specular IOR Level'].default_value = .21
    return material


def weighted(obj, rig, kind, component='body', part='head'):
    obj['ast_part'] = part
    obj['asterion_component'] = component
    obj['asterion_rig'] = kind + '-rig-v1'
    if component == 'armor':
        obj['asterion_equipment_slot'] = 'outfit'
        obj['asterion_equipment_id'] = kind + '-outfit-v1'
    if part not in rig.data.bones:
        raise ValueError('Unknown original bone for new surface: ' + part)
    obj.vertex_groups.new(name=part).add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')
    obj.modifiers.new('Original companion skin', 'ARMATURE').object = rig
    obj.parent = rig


def remove(g, predicate, records):
    removed = []
    for obj in list(g.ASSET):
        if predicate(obj):
            name = obj.name
            g.ASSET.remove(obj)
            bpy.data.objects.remove(obj, do_unlink=True)
            removed.append(name)
            records.append({'name': name, 'operation': 'replaced_by_guided_reference_hair_volume', 'max_displacement': 0})
    return removed


def curve_centers(points, count):
    """Clamped cubic B-spline: no Catmull knot elbows in a thick lock."""
    points = list(map(Vector, points))
    n = len(points) - 1
    degree = min(3, n)
    knots = [0.] * (degree + 1) + [i / (n - degree + 1) for i in range(1, n - degree + 1)] + [1.] * (degree + 1)
    result = []
    for j in range(count + 1):
        t = j / count
        k = n if j == count else next(k for k in range(degree, n + 1) if knots[k] <= t < knots[k + 1])
        d = [points[k - degree + i].copy() for i in range(degree + 1)]
        for r in range(1, degree + 1):
            for i in range(degree, r - 1, -1):
                lo, hi = knots[i + k - degree], knots[i + 1 + k - r]
                blend = (t - lo) / (hi - lo) if hi > lo else 0
                d[i] = d[i - 1] * (1 - blend) + d[i] * blend
        result.append(d[degree])
    return result


def lock(g, rig, kind, name, points, width, depth, material, tone=0, steps=100, sides=48, normal=(0, -1, 0)):
    """Parallel-transported, tapered lock with broad sculpted ridges and a curl.

    Width is limited at tight turns so the lock does not fold through itself.
    The asymmetric highlight lies along the lock, not across the whole head.
    """
    centers = curve_centers(points, steps)
    vertices, faces, colors = [], [], []
    previous = Vector(normal).normalized()
    palette = {'orc': ('0C070B', '2F1828', '714142'),
               'fairy': ('692C28', 'C65A47', 'F1B07C'),
               'elf': ('091C18', '1F4437', '739073')}
    dark, middle, light = [np.array(g.color(c)[:3]) for c in palette[kind]]
    if kind == 'fairy' and tone >= .20:
        dark, middle, light = [np.array(g.color(c)[:3]) for c in ('713A23', 'C8924F', 'F4CB85')]
    for i, c in enumerate(centers):
        t = i / steps
        tangent = (centers[min(steps, i + 1)] - centers[max(0, i - 1)]).normalized()
        normal_v = previous - tangent * previous.dot(tangent)
        if normal_v.length < 1e-6:
            normal_v = Vector((0, 0, 1)) - tangent * tangent.z
        normal_v.normalize()
        across = tangent.cross(normal_v).normalized()
        previous = normal_v
        shape = (.36 + .64 * math.sin(math.pi * min(1, t / .97)) ** .50) * max(.0004, 1 - t ** 3.1) ** .82
        w = width * shape + .00025
        d = depth * (.70 + .30 * math.sin(math.pi * t)) * max(.0005, 1 - t ** 3.2)
        if 0 < i < steps:
            before = centers[i] - centers[i - 1]
            after = centers[i + 1] - centers[i]
            curvature = 2 * before.cross(after).length / max(1e-10, before.length * after.length * (before + after).length)
            if curvature > .001:
                # Smooth reciprocal reduction avoids a row-wise clamp crease.
                w /= math.sqrt(1 + (w * curvature / .90) ** 4)
                d /= math.sqrt(1 + (d * curvature / .90) ** 4)
        for j in range(sides):
            a = math.tau * j / sides
            q = math.cos(a)
            facing = max(0, math.sin(a))
            channels = .082 * math.cos(q * 5 * math.pi + .7 * t) + .022 * math.cos(q * 17 * math.pi + t * 4)
            vertices.append(c + across * w * q + normal_v * d * math.sin(a) * (1 + channels))
            lobe = max(0, math.cos((q - .13) * math.pi * 1.10)) ** 5
            fleck = .055 * math.sin(t * 130 + q * 31) * math.sin(t * 37 - q * 47)
            f = np.clip(.23 + .54 * facing + .09 * math.sin(t * 9) + tone, 0, 1)
            color = dark * (1 - f) + middle * f
            highlight = min(.47, (.16 + tone) * lobe * facing * (.35 + .65 * math.sin(math.pi * t)) + max(0, fleck))
            color = color * (1 - highlight) + light * highlight
            colors.append(tuple(color) + (1.,))
    for i in range(steps):
        for j in range(sides):
            a = i * sides + j
            b = i * sides + (j + 1) % sides
            faces.append((a, a + sides, b + sides, b))
    faces.extend([tuple(range(sides)), tuple(steps * sides + j for j in reversed(range(sides)))])
    obj = g.mesh(NAMES[kind] + '_v4_' + name, vertices, faces, material, 'head')
    color_field(obj, colors)
    weighted(obj, rig, kind)
    return obj


def orbital_forms(g, kind, records):
    """A single continuous warp changes eye, orbital skin, true socket and lid.

    The rest-lid center stays fixed. Peripheral influence fades outside the
    orbital family, avoiding a resized floating eye in the old larger socket.
    """
    prefixes = {'orc': 'AST_Brumo_v2_eye_', 'fairy': 'AST_Selya_eye_', 'elf': 'AST_Aelira_v2_eye_'}
    settings = {'orc': (.88, .025), 'fairy': (.84, .026), 'elf': (.78, .028)}
    ratio, cant = settings[kind]
    centers = []
    for side in ('L', 'R'):
        obj = bpy.data.objects[prefixes[kind] + side]
        p = coords(obj)
        c = (p.max(axis=0) + p.min(axis=0)) / 2
        rx = (p[:, 0].max() - p[:, 0].min()) / 2
        rz = (p[:, 2].max() - p[:, 2].min()) / 2
        centers.append((c, rx, rz, 1 if side == 'L' else -1))
    head_name = {'orc': 'AST_Brumo_v2_head', 'fairy': 'AST_Selya_sculpted_head', 'elf': 'AST_Aelira_v2_refined_head'}[kind]
    for obj in g.ASSET:
        if not (obj.name == head_name or 'eye_' in obj.name or 'brow' in obj.name):
            continue
        p = coords(obj)
        result = p.copy()
        for c, rx, rz, sign in centers:
            d = p - c
            distance = np.maximum(np.abs(d[:, 0]) / (rx * 1.20), np.abs(d[:, 2]) / (rz * 1.20))
            strength = 1 - smooth((distance - 1) / .80)
            strength *= 1 - smooth((d[:, 1] - .055) / .16)
            corner = np.clip(sign * d[:, 0] / rx, -1.1, 1.1)
            dz = d[:, 2] * (ratio - 1) + cant * corner
            result[:, 2] += dz * strength
        write(obj, result, records, 'continuous_almond_orbit_and_closed_lid_recontour')
    return {'orbital_vertical_scale': ratio, 'outer_corner_rise': cant,
            'original_blink_bone_and_pivot_unchanged': True}


def iris_pigment(g, kind, records):
    """Restore the reference's dark limbal ring and varied radial iris fibers."""
    prefixes = {'orc': 'AST_Brumo_v2_eye_', 'fairy': 'AST_Selya_eye_', 'elf': 'AST_Aelira_v2_eye_'}
    for side in ('L', 'R'):
        obj = bpy.data.objects[prefixes[kind] + side]
        attr = obj.data.color_attributes.get('AST_eye_color')
        values = np.empty(len(attr.data) * 4, dtype=np.float32)
        attr.data.foreach_get('color', values)
        values = values.reshape((-1, 4)).astype(np.float64)
        p = coords(obj)
        c = (p.min(axis=0) + p.max(axis=0)) / 2
        x = (p[:, 0] - c[0]) / ((p[:, 0].max() - p[:, 0].min()) / 2)
        z = (p[:, 2] - c[2]) / ((p[:, 2].max() - p[:, 2].min()) / 2)
        a = np.arctan2(z, x)
        # Distinguish the colored iris from warm off-white sclera and pupil.
        rgb = values[:, :3]
        chroma = rgb.max(axis=1) - rgb.min(axis=1)
        active = (chroma > .026) & (rgb.min(axis=1) < .24) & (rgb.max(axis=1) > .025)
        shade = .78 + .12 * np.sin(a * 39 + z * 11) + .07 * np.sin(a * 71 - x * 9)
        shade *= .84 + .18 * np.clip(-z, 0, 1)
        rgb[active] *= shade[active, None]
        color_field(obj, values)
        records.append({'name': obj.name, 'operation': 'radial_iris_depth_and_upper_shadow', 'max_displacement': 0})


def brumo(g, rig, records):
    reference = next(o for o in g.ASSET if 'front_swept_lock_' in o.name)
    material = pigmented_material(g, reference.data.materials[0], 'orc')
    removed = remove(g, lambda o: any(s in o.name for s in ('front_swept_lock_', 'low_crown_gather_')), records)
    # Reconstruct a staggered rising quiff. The former equal-length fringe was
    # a row of heavy downward lobes across the entire forehead.
    for j in range(6):
        q = (j - 2.5) / 2.5
        pts = [(q * .50, -.394 + .054 * abs(q), 3.12 + .18 * abs(q)),
               (q * .49 - .055, -.386, 3.35 + .015 * math.cos(j)),
               (q * .38 + .12, -.235, 3.59 + .075 * math.sin(j * 1.4)),
               (q * .25 + .29, -.035, 3.79 + .105 * math.cos(j * 1.15))]
        lock(g, rig, 'orc', 'rising_plum_quiff_%02d' % j, pts, .177 + .025 * (j % 3), .074,
             material, tone=.055 if j in (2, 5) else 0, steps=88)
    for j in range(7):
        q = (j - 3) / 3
        lock(g, rig, 'orc', 'gathered_crown_%02d' % j,
             [(q * .50, -.08, 3.45), (q * .52, .10, 3.61), (q * .38, .31, 3.61), (q * .19, .39, 3.69)],
             .135, .060, material, normal=(0, 0, 1), steps=72)
    # Retain every original facial/eyelid scale pivot. A translation of the
    # whole head's stored vertices would be scaled away on an opening lid:
    # the fully closed cover could fit while intermediate blinks visibly flap.
    # Shorten the lower-body rhythm and fill the upper chest instead.
    for obj in g.ASSET:
        p = coords(obj)
        changed = p.copy()
        part = str(obj.get('ast_part', ''))
        if part != 'head' and not part.startswith(('eye.', 'lid.')):
            if 'long_front_tabard' in obj.name:
                hem = 1 - smooth((p[:, 2] - .43) / .26)
                changed[:, 2] += .11 * smooth(np.abs(p[:, 0]) / .19) * hem
                changed[:, 1] -= .010 * np.cos(p[:, 0] * 25) * hem
            body = 1 - smooth((p[:, 2] - 1.92) / .43)
            changed[:, 0] *= 1 + .092 * body
            lower_compaction = .095 * p[:, 2] * (1 - smooth((p[:, 2] - 1.00) / 1.15))
            chest_fill = .12 * smooth((p[:, 2] - 1.65) / .35) * (1 - smooth((p[:, 2] - 2.10) / .32))
            changed[:, 2] += chest_fill - lower_compaction
        if obj.name == 'AST_Brumo_v2_head':
            chin = np.exp(-((p[:, 2] - 2.42) / .20) ** 2)
            changed[:, 0] *= 1 + .028 * chin
            cheek = np.exp(-((np.abs(p[:, 0]) - .32) / .18) ** 2 - ((p[:, 2] - 2.52) / .13) ** 2)
            changed[:, 1] += .031 * cheek * (1 - smooth((p[:, 1] + .35) / .11))
        write(obj, changed, records, 'compact_lower_body_and_raised_chest_preserving_original_facial_pivots')
    return removed


def selya(g, rig, records):
    reference = bpy.data.objects['AST_Selya_continuous_crown_and_flowing_underhair']
    material = pigmented_material(g, reference.data.materials[0], 'fairy')
    old_patterns = ('flowing_face_wave_', 'integrated_lower_curl_', 'overlapping_crown_wave_',
                    'scalp_fitted_swept_fringe', 'golden_fringe_inset', 'scalp_fitted_right_parting')
    removed = remove(g, lambda o: any(s in o.name for s in old_patterns), records)
    p = coords(reference)
    shortened = p.copy()
    below = p[:, 2] < 3.06
    shortened[below, 2] = 3.06 + (p[below, 2] - 3.06) * .12
    taper = 1 - .20 * (1 - smooth((p[:, 2] - 3.05) / .58))
    shortened[:, 0] *= taper
    shortened[:, 1] = .10 + (shortened[:, 1] - .10) * taper
    write(reference, shortened, records, 'short_nape_foundation_beneath_free_curl_silhouette')
    for j in range(15):
        a = -.045 + math.pi * 1.03 * j / 14
        radial = Vector((math.cos(a), math.sin(a), 0))
        lateral = Vector((-math.sin(a), math.cos(a), 0))
        pts = []
        heights = (4.145, 3.89, 3.50, 3.16, 2.89, 2.59, 2.35, 2.14, 2.24, 2.41)
        radii = (.05, .56, .76, .75, .66, .84, .76, .91, 1.03, .99)
        for k, (z, radius) in enumerate(zip(heights, radii)):
            phase = .10 * math.sin(k * 1.30 + j * .6) * min(1, k / 3)
            point = radial * radius + lateral * phase + Vector((0, .10, z + .085 * math.sin(j * 1.7) * min(1, k / 5)))
            pts.append(point)
        lock(g, rig, 'fairy', 'copper_waterfall_curl_%02d' % j, pts,
             .147 + .024 * (j % 3), .075, material, tone=.025 * (j % 4), normal=radial, steps=120)
    curves = [
        ([(.16, -.30, 4.00), (-.15, -.48, 3.90), (-.42, -.53, 3.67), (-.57, -.48, 3.42),
          (-.56, -.57, 3.17), (-.63, -.59, 2.97), (-.80, -.46, 2.81), (-.87, -.30, 2.91), (-.77, -.22, 3.00)], .125, .080, .085),
        ([(.46, -.20, 3.86), (.62, -.38, 3.77), (.65, -.48, 3.65), (.68, -.45, 3.46),
          (.57, -.54, 3.17), (.62, -.55, 2.97), (.80, -.42, 2.79), (.88, -.30, 2.86), (.79, -.22, 2.98)], .135, .078, .035),
        ([(.10, -.365, 4.012), (-.16, -.565, 3.925), (-.46, -.625, 3.71), (-.63, -.515, 3.44),
          (-.61, -.515, 3.22), (-.49, -.525, 3.13)], .057, .018, .24),
        ([(-.48, -.14, 3.71), (-.68, -.30, 3.48), (-.69, -.41, 3.19), (-.63, -.35, 2.94),
          (-.79, -.22, 2.70), (-1.00, -.02, 2.66), (-1.03, .02, 2.82)], .101, .052, .01),
        ([(.48, -.11, 3.70), (.69, -.26, 3.44), (.68, -.39, 3.14), (.62, -.28, 2.88),
          (.77, -.13, 2.62), (1.00, .02, 2.58), (1.04, .08, 2.74)], .108, .059, .035),
        ([(.12, -.28, 4.04), (.28, -.54, 4.01), (.42, -.59, 3.85),
          (.59, -.52, 3.73), (.72, -.31, 3.77)], .147, .073, .075)]
    for j, (points, width, depth, tone) in enumerate(curves):
        lock(g, rig, 'fairy', 'face_framing_copper_spiral_%02d' % j, points, width, depth, material, tone, steps=116)
    # Her original dress stays closed. A curved taper near the waist continues
    # through the fitted floral trim without separating the overlay from it.
    for obj in g.ASSET:
        if obj.get('ast_part') not in ('body', 'neck') or 'wing' in obj.name:
            continue
        p = coords(obj)
        scale = 1 - .065 * np.exp(-((p[:, 2] - 2.02) / .31) ** 2)
        changed = p.copy()
        changed[:, :2] *= scale[:, None]
        write(obj, changed, records, 'fitted_botanical_waist_with_attached_ornaments')
    for obj in g.ASSET:
        if 'ear_concha_' in obj.name:
            p = coords(obj)
            p[:, 1] += .019
            write(obj, p, records, 'recessed_leaf_ear_concha')
        if obj.name in ('AST_Selya_upper_wing_L', 'AST_Selya_upper_wing_R', 'AST_Selya_lower_wing_L', 'AST_Selya_lower_wing_R'):
            p = coords(obj)
            blend = np.clip(.52 + .17 * np.sin(p[:, 0] * 11 + p[:, 2] * 8) * np.sin(p[:, 2] * 14 - p[:, 0] * 5), 0, 1)
            mint, pearl = np.array(g.color('A0C8B4')), np.array(g.color('E9DDC0'))
            colors = mint[None, :] * (1 - blend[:, None]) + pearl[None, :] * blend[:, None]
            colors[:, :3] *= .68
            color_field(obj, colors)
            records.append({'name': obj.name, 'operation': 'authored_pearl_and_mint_membrane_cells', 'max_displacement': 0})
    return removed


def aelira(g, rig, records):
    reference = next(o for o in g.ASSET if 'parted_crown_' in o.name)
    material = pigmented_material(g, reference.data.materials[0], 'elf')
    removed = remove(g, lambda o: any(s in o.name for s in ('parted_crown_', 'swept_hairline_', 'face_framing_curl_', 'secondary_curl_')), records)
    for sign in (-1, 1):
        for j in range(5):
            t = j / 4
            lock(g, rig, 'elf', 'arched_parted_crown_%s_%02d' % (sign, j),
                 [(sign * .018, .22 - .39 * t, 3.50 - .033 * t),
                  (sign * .20, .02 - .29 * t, 3.55 - .035 * t),
                  (sign * .44, -.13 - .22 * t, 3.40 - .063 * t),
                  (sign * .55, -.04 - .30 * t, 3.17 - .046 * t),
                  (sign * .54, .10 - .28 * t, 3.00 + .025 * t)],
                 .135 - .008 * (j % 2), .056, material, tone=.035 if j in (1, 4) else 0, steps=88)
        points = [(sign * .045, -.235, 3.47), (sign * .225, -.446, 3.385),
                  (sign * .43, -.45, 3.18), (sign * .44, -.45, 2.96),
                  (sign * .53, -.455, 2.73), (sign * .47, -.45, 2.50),
                  (sign * .62, -.27, 2.34), (sign * .59, -.19, 2.25), (sign * .49, -.17, 2.32)]
        lock(g, rig, 'elf', 'flowing_temple_ringlet_' + str(sign), points, .089, .051, material, tone=.055, steps=120)
    # The reference braid is a soft plait, with a clearly changing silhouette;
    # the old cylindrical repeated links had too little lateral rhythm.
    for obj in g.ASSET:
        if 'interwoven_plait_' in obj.name or 'braid_tassel_' in obj.name or 'braid_engraved_tie_' in obj.name:
            p = coords(obj)
            factor = 1 + .085 * np.sin((p[:, 2] - 1.25) * 4.1)
            p[:, 0] = .52 + (p[:, 0] - .52) * factor
            p[:, 1] -= .035 * np.sin((p[:, 2] - 1.28) * 3.7)
            write(obj, p, records, 'soft_asymmetric_plait_silhouette')
        elif 'leaf_ear_' in obj.name:
            p = coords(obj)
            tip = smooth((np.abs(p[:, 0]) - .55) / .40)
            p[:, 0] -= np.sign(p[:, 0]) * .07 * tip
            p[:, 2] -= .045 * tip
            write(obj, p, records, 'reference_leaf_ear_proportion')
        elif any(s in obj.name for s in ('full_folded_forest_cape', 'cape_embroidered_hem', 'cape_gold_selvedge_', 'cape_hem_leaf_', 'cape_margin_leaf_', 'cape_margin_vine_')):
            p = coords(obj)
            drape = 1 - smooth((p[:, 2] - .45) / 1.85)
            p[:, 0] *= 1 + .07 * drape
            p[:, 1] += .049 * np.cos(p[:, 0] * 12 + .45 * p[:, 2]) * drape
            write(obj, p, records, 'broad_tapered_cloak_folds_and_matching_hem')
    return removed


def richer_pigments(g, kind, records):
    """Baked POINT color, meaningful in both Blender and glTF/Three.js."""
    for obj in g.ASSET:
        if not obj.data.materials or '_v4_' in obj.name or 'eye_' in obj.name:
            continue
        material_names = ' '.join(mat.name.lower() for mat in obj.data.materials)
        hair = 'hair' in material_names and not any(s in obj.name for s in ('blossom', 'gold', 'binding', 'collar'))
        skin = any(s in material_names for s in ('skin', 'warm_skin'))
        cloth = any(s in material_names for s in ('cloth_field', 'leather_field', 'plate_colors', 'sv_coral', 'selya_coral', 'selya_mint', 'ae_v2_woven_', 'ae_v2_cape'))
        if not (hair or skin or cloth):
            continue
        attr = obj.data.color_attributes.get('AST_eye_color')
        if attr is None:
            continue
        values = np.empty(len(attr.data) * 4, dtype=np.float32)
        attr.data.foreach_get('color', values)
        values = values.reshape((-1, 4)).astype(np.float64)
        p = coords(obj)
        pigment = .98 + .035 * np.sin(p[:, 0] * 23 + p[:, 2] * 19) * np.cos(p[:, 1] * 29 - p[:, 2] * 13)
        if hair:
            pigment *= {'orc': .58, 'fairy': .81, 'elf': .60}[kind]
        elif skin:
            pigment *= {'orc': .87, 'fairy': .89, 'elf': .85}[kind]
            if kind in ('fairy', 'elf'):
                z = 3.07 if kind == 'fairy' else 2.65
                cheek = np.exp(-((np.abs(p[:, 0]) - (.40 if kind == 'fairy' else .32)) / .14) ** 2 - ((p[:, 2] - z) / .12) ** 2)
                cheek *= 1 - smooth((p[:, 1] + .24) / .12)
                values[:, 0] *= 1 + .16 * cheek
                values[:, 1] *= 1 - .16 * cheek
                values[:, 2] *= 1 - .09 * cheek
        else:
            pigment *= .86
        values[:, :3] *= pigment[:, None]
        color_field(obj, values)
        records.append({'name': obj.name, 'operation': 'reference_pigment_depth_and_cheek_tint', 'max_displacement': 0})


def complete_body_joints(g, rig, kind):
    """Close inherited limb/garment gaps with fitted, overlapping joint shells.

    The historical limbs remain editable. New surfaces share their existing
    skin/cloth material and the original body/limb bones; no joint is moved.
    """
    if kind == 'fairy':
        return {'connectors': [], 'added_base_clothing': []}
    from mathutils.kdtree import KDTree
    added, clothes = [], []

    def finish(obj, donor, part, *, shoulder=False, garment=False):
        weighted(obj, rig, kind, part=part)
        p = coords(obj)
        if shoulder:
            inner, width = (.30, .18) if kind == 'orc' else (.22, .14)
            limb = smooth((np.abs(p[:, 0]) - inner) / width)
            body = obj.vertex_groups.new(name='body')
            original = obj.vertex_groups[part]
            for i, amount in enumerate(limb):
                original.add([i], float(amount), 'REPLACE')
                body.add([i], float(1 - amount), 'REPLACE')
        attr = donor.data.color_attributes.get('AST_eye_color')
        if attr is not None:
            source_points = coords(donor)
            tree = KDTree(len(source_points))
            for i, point in enumerate(source_points):
                tree.insert(point, i)
            tree.balance()
            values = np.empty(len(attr.data) * 4, dtype=np.float32)
            attr.data.foreach_get('color', values)
            values = values.reshape((-1, 4))
            color_field(obj, [values[tree.find(point)[1]] for point in p])
        edge_faces = {}
        for face in obj.data.polygons:
            indices = list(face.vertices)
            for a, b in zip(indices, indices[1:] + indices[:1]):
                edge = tuple(sorted((a, b)))
                edge_faces[edge] = edge_faces.get(edge, 0) + 1
        closed = bool(edge_faces) and all(count == 2 for count in edge_faces.values())
        valid_weights = all(v.groups and abs(sum(w.weight for w in v.groups) - 1) < 1e-6 and
            all(math.isfinite(w.weight) and 0 <= w.weight <= 1 and obj.vertex_groups[w.group].name in rig.data.bones
                for w in v.groups) for v in obj.data.vertices)
        if not closed or not valid_weights or not np.isfinite(p).all():
            raise ValueError('Invalid closed body connector: ' + obj.name)
        added.append({'name': obj.name, 'component': 'body', 'closed_manifold': closed,
            'non_two_face_edges': sum(count != 2 for count in edge_faces.values()),
            'finite_geometry': True, 'finite_normalized_known_rig_weights': valid_weights,
            'original_bones': [group.name for group in obj.vertex_groups],
            'triangles': sum(len(face.vertices) - 2 for face in obj.data.polygons)})
        if garment:
            clothes.append(obj.name)
        return obj

    def sphere(name, center, radii, donor, part, **options):
        obj = g.uv(NAMES[kind] + '_v4_' + name, center, radii, donor.data.materials[0], part, seg=64, rings=40)
        if kind == 'elf' and options.get('shoulder'):
            # Flatten only the upper armhole crown beneath the original cloak
            # edge; the lower overlap with the existing sleeve stays intact.
            p = coords(obj)
            p[:, 2] -= .040 * smooth((p[:, 2] - 2.070) / .100)
            write(obj, p, [], 'fit_new_tunic_armhole_beneath_existing_cloak')
        return finish(obj, donor, part, **options)

    if kind == 'orc':
        for side, sign in (('L', 1), ('R', -1)):
            arm = bpy.data.objects['AST_Brumo_strong_arm_' + side]
            # Use the actual displaced end ring, not an estimated sphere. Its
            # outer edge follows the existing arm exactly; the rounded dome
            # reaches inward into the closed thorax beneath the pauldron.
            points = coords(arm)
            cap = max((face for face in arm.data.polygons if len(face.vertices) > 8),
                      key=lambda face: points[list(face.vertices), 2].mean())
            rim = points[list(cap.vertices)]
            center = rim.mean(axis=0)
            radial = rim - center
            normal = np.linalg.svd(radial, full_matrices=False)[2][-1]
            if normal[2] < 0:
                normal = -normal
            vertices, faces = [], []
            rows, sides = 36, len(rim)
            for row in range(1, rows):
                angle = -math.pi / 2 + math.pi * row / rows
                depth = .225 if angle >= 0 else .065
                for offset in radial:
                    vertices.append(center + offset * math.cos(angle) * 1.009 + normal * depth * math.sin(angle))
            for row in range(rows - 2):
                for j in range(sides):
                    a = row * sides + j; b = row * sides + (j + 1) % sides
                    faces.append((a, b, b + sides, a + sides))
            low, high = len(vertices), len(vertices) + 1
            vertices.extend([center - normal * .065, center + normal * .225])
            last = (rows - 2) * sides
            for j in range(sides):
                faces.extend([(low, (j + 1) % sides, j), (high, last + j, last + (j + 1) % sides)])
            # Orient the complete shell independently of mirrored ring order.
            volume = sum(np.dot(vertices[face[0]], np.cross(vertices[face[j]], vertices[face[j + 1]]))
                         for face in faces for j in range(1, len(face) - 1))
            if volume < 0:
                faces = [tuple(reversed(face)) for face in faces]
            obj = g.mesh('Brumo_v4_closed_deltoid_' + side, vertices, faces, arm.data.materials[0], 'arm.' + side)
            finish(obj, arm, 'arm.' + side, shoulder=True)
            sphere('closed_wrist_' + side, (sign * .771, -.151, 1.061), (.118, .105, .100), arm, 'arm.' + side)
            leg = bpy.data.objects['AST_Brumo_leg_' + side]
            sphere('closed_ankle_' + side, (sign * .326, -.009, .257), (.145, .143, .095), leg, 'leg.' + side)
    else:
        for side, sign in (('L', 1), ('R', -1)):
            sleeve = bpy.data.objects['AST_Aelira_soft_cream_sleeve_' + side]
            sphere('closed_tunic_armhole_' + side, (sign * .393, .021, 2.072), (.198, .171, .146),
                   sleeve, 'arm.' + side, shoulder=True, garment=True)
            hand = bpy.data.objects['AST_Aelira_v2_shaped_hand_' + str(sign)]
            center = (.490, -.324, 1.465) if sign > 0 else (-.640, -.169, 1.283)
            sphere('closed_wrist_' + side, center, (.078, .075, .104), hand, 'arm.' + side)
        # The split skirt hides the front only. A closed trouser seat is needed
        # between the tunic hem and both upper legs when the cape is removed.
        trouser = bpy.data.objects['AST_Aelira_forest_trouser_L']
        sphere('closed_base_trouser_seat', (0, .052, 1.283), (.365, .224, .236), trouser, 'body', garment=True)
    return {'connectors': added, 'added_base_clothing': clothes,
            'method': 'Fitted overlapping closed body shells; original limbs, rest bones and actions retained.',
            'motion_clearance_accepted': False}


def apply(g, rig, kind):
    if kind not in NAMES:
        raise ValueError('Unsupported folk companion: ' + kind)
    records = []
    original_count = len(g.ASSET)
    ocular = orbital_forms(g, kind, records)
    iris_pigment(g, kind, records)
    removed = {'orc': brumo, 'fairy': selya, 'elf': aelira}[kind](g, rig, records)
    richer_pigments(g, kind, records)
    joints = complete_body_joints(g, rig, kind)
    notes = {
        'orc': 'Staggered rising plum quiff, broader compact lower-body proportions and fuller upper chest while preserving facial scale pivots; continuous almond orbital reshaping, richer olive/plum pigment and complete base underclothes retained.',
        'fairy': 'Free copper waterfall curls replace straight hair strips and the low cap hem; coherent almond eye/socket/lid shape, warm cheek pigment and fitted layered botanical waist; complete mint/ivory dress and wings retained.',
        'elf': 'Arched parted crown and flowing temple ringlets replace slab-like fringe; softer plait silhouette, narrower leaf-ear tips, coherent almond eye/socket/lid shape and deeper forest pigment; opaque tunic, trousers and boots retained.'}
    return {'notes': notes[kind], 'edited_objects': records, 'added_base_clothing': joints['added_base_clothing'],
            'body_joint_completion': joints,
            'replaced_hair_objects': removed, 'original_source_object_count': original_count,
            'candidate_source_object_count': len(g.ASSET), 'ocular_refinement': ocular,
            'original_source_rig_and_actions_modified': False}

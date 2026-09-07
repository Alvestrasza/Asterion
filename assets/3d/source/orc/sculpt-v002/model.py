"""Brumo v002: reference-led face, scored swept hair and forged leather armor.

The portrait is the visual authority. Source v001 is retained and used only for
stable under-clothing limb construction and the nine-clip biped skeleton.
"""
from __future__ import annotations
import math
from pathlib import Path
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'companions' / 'sculpt-v001'))
import humanoids as base
import sculpt_helpers as h


def front(g, obj, name, points, width, mat, part='body'):
    bvh = h.tree(obj); seated = []
    for x, _, z in g.spline(points, 48):
        p, n, _, _ = bvh.ray_cast(Vector((x, -3, z)), Vector((0, 1, 0)))
        if p is None: raise ValueError(name + ': missing supporting armor')
        seated.append(p + n * .017)
    return h.ribbon(g, name, seated, width, mat, part, steps=80)


def emblem(g, name, center, width, height, part='body'):
    x, y, z = center
    base._diamond(g, name, center, width, height, 'br_gold', 'br_armor', part)
    vs = [(x, y - .069, z + height * .65), (x + width * .61, y - .069, z),
          (x, y - .069, z - height * .65), (x - width * .61, y - .069, z), (x, y - .105, z)]
    g.mesh(name + '_four_cut_star', vs, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], 'br_gold_hi', part, smooth=False)


def shoulder(g, sign):
    side = 'L' if sign > 0 else 'R'; part = 'arm.' + side
    vs, fs = [], []; rows, cols = 44, 112
    def pos(t, a):
        return Vector((sign * .56 + .293 * t * math.cos(a), .028 + .346 * t * math.sin(a),
                       2.145 - .246 * t ** 1.65 - .055 * t ** 3 * abs(math.sin(a))))
    for row in range(rows + 1):
        t = max(.00001, row / rows)
        for col in range(cols): vs.append(pos(t, math.tau * col / cols))
    for row in range(rows):
        for col in range(cols):
            a = row * cols + col; b = row * cols + (col + 1) % cols; fs.append((a, a + cols, b + cols, b))
    obj = base._shell(g, 'Brumo_v2_forged_pauldron_' + side, vs, fs, 'br_armor_hi', part, .036, 0)
    h.detail_surface(g, obj, '382333', 'br_v2_plate_colors', .002)
    band, bandfaces = [], []
    for row in range(7):
        for j in range(cols): band.append(pos(.80 + .205 * row / 6, math.tau * j / cols) + Vector((0, 0, .012)))
    for row in range(6):
        for j in range(cols):
            a = row * cols + j; b = row * cols + (j + 1) % cols
            bandfaces.append((a, a + cols, b + cols, b))
    base._shell(g, 'Brumo_v2_pauldron_broad_forged_border_' + side, band, bandfaces, 'br_gold', part, .020, 0)
    for j in range(3):
        a = -math.pi * .72 + j * .23; p = pos(.80, a); p.z += .027
        g.uv('Brumo_v2_pauldron_rivet_' + side + str(j), p, (.013, .013, .009), 'br_gold_hi', part, seg=24, rings=16)
    emblem(g, 'Brumo_v2_pauldron_star_' + side, (sign * .65, -.279, 1.978), .071, .078, part)


def head(g):
    skin = 'br_skin'
    obj = g.fuse('Brumo_v2_head', [
        g.uv('Brumo_v2_cranium', (0, .015, 2.76), (.665, .51, .63), skin, 'head', seg=80, rings=56),
        g.uv('Brumo_v2_lower_face', (0, -.235, 2.56), (.590, .36, .39), skin, 'head'),
        g.uv('Brumo_v2_jaw', (0, -.19, 2.34), (.47, .335, .205), skin, 'head'),
        g.uv('Brumo_v2_cheekL', (.30, -.395, 2.50), (.276, .206, .22), skin, 'head'),
        g.uv('Brumo_v2_cheekR', (-.30, -.395, 2.50), (.276, .206, .22), skin, 'head'),
        g.uv('Brumo_v2_nose_bridge', (0, -.526, 2.62), (.105, .111, .13), skin, 'head'),
        g.uv('Brumo_v2_nose_wings', (0, -.609, 2.53), (.147, .104, .087), skin, 'head')], 'head', voxel=.0135, subdiv=1)
    for sign in (-1, 1):
        side = 'L' if sign > 0 else 'R'
        h.eye(g, 'Brumo_v2_eye_' + side, obj, side, (sign * .275, -.53, 2.79), .346, .346,
              skin, 'br_shadow', '703109', 'F4AD2B')
        h.ear(g, 'Brumo_v2_cupped_ear_' + side, sign, 2.77, 1.045, skin, 'br_inner')
        h.lock(g, 'Brumo_v2_expressive_brow_' + side,
               [(sign * .105, -.515, 3.009), (sign * .21, -.544, 3.067), (sign * .33, -.513, 3.063), (sign * .432, -.449, 3.007)],
               .052, .033, 'br_hair', steps=52, sides=32)
        g.sweep('Brumo_v2_upturned_tusk_' + side,
                [(sign * .297, -.526, 2.365), (sign * .305, -.602, 2.392), (sign * .301, -.628, 2.451), (sign * .29, -.613, 2.522)],
                [.048, .054, .033, .0006], [.044, .042, .027, .0004], 'br_ivory', 'head', normal=(1, 0, 0), steps=52, sides=36)
        h.seated_line(g, 'Brumo_v2_nostril_' + side, obj,
                      [(sign * .058, -1, 2.516), (sign * .086, -1, 2.526), (sign * .114, -1, 2.519)], .008, 'br_shadow')
    h.seated_line(g, 'Brumo_v2_gentle_smile', obj,
                   [(-.354, -1, 2.394), (-.21, -1, 2.361), (0, -1, 2.348), (.22, -1, 2.370), (.356, -1, 2.414)], .007, 'br_shadow')
    base._haircap(g, 'Brumo_v2', (0, .042, 2.80), (.688, .536, .65), 'br_hair')
    # A closed crown mass joins the lifted quiff to the gathered topknot.
    # Its upper surface is covered by shallow, overlapping scalp-following locks.
    g.uv('Brumo_v2_closed_crown_underhair', (0, .015, 3.375), (.59, .36, .23),
         'br_hair', 'head', seg=72, rings=40)
    for j in range(11):
        q = (j - 5) / 5
        h.lock(g, 'Brumo_v2_low_crown_gather_' + str(j),
               [(q * .52, -.23, 3.40 - .10 * abs(q)),
                (q * .52, -.07, 3.60 - .13 * q * q),
                (q * .45, .15, 3.59 - .12 * q * q),
                (q * .32, .35, 3.49 - .055 * abs(q))],
               .128, .044, 'br_hair', normal=(0, 0, 1), steps=52, sides=36)
    for j in range(7):
        q = (j - 3) / 3
        h.lock(g, 'Brumo_v2_front_swept_lock_' + str(j),
               [(q * .54, -.439 + .12 * abs(q), 3.09 - .028 * abs(q)),
                (q * .49 - .035, -.365, 3.32), (q * .41 + .09, -.17, 3.52 - .024 * abs(q)),
                (q * .36 + .19, .068, 3.67 - .072 * abs(q))], .178 + .018 * math.cos(j * 1.7), .081, 'br_hair_hi' if j == 3 else 'br_hair')
    for sign in (-1, 1):
        for j in range(6):
            z = 3.30 - j * .13
            h.lock(g, 'Brumo_v2_side_swept_lock_' + str(sign) + '_' + str(j),
                   [(sign * .50, -.06, z), (sign * .65, .04, z + .03), (sign * .65, .29, z + .12),
                    (sign * .58, .48, z + .18)], .122 - .006 * (j % 3), .063, 'br_hair', normal=(sign * .65, -.76, 0), steps=60, sides=40)
        for j in range(3):
            h.lock(g, 'Brumo_v2_temple_lock_' + str(sign) + str(j),
                   [(sign * (.44 + .038 * j), -.29 + .11 * j, 3.35), (sign * (.61 + .035 * j), -.30 + .13 * j, 3.12),
                    (sign * (.65 + .025 * j), -.18 + .13 * j, 2.93), (sign * .62, -.02 + .13 * j, 2.78)],
                   .125, .056, 'br_hair', normal=(sign * .6, -.8, 0), steps=48, sides=32)
    for j in range(11):
        longitude = (j - 5) / 5 * 1.32
        points = []
        for theta in (.35, .96, 1.61, 2.22 + .05 * math.sin(j)):
            points.append((.722 * math.sin(theta) * math.sin(longitude),
                           .042 + .59 * math.sin(theta) * math.cos(longitude), 2.80 + .70 * math.cos(theta)))
        h.lock(g, 'Brumo_v2_nape_lock_' + str(j), points, .155, .054, 'br_hair', normal=(math.sin(longitude), math.cos(longitude), 0), steps=56, sides=36)
    g.sweep('Brumo_v2_topknot_root_bundle', [(0, .14, 3.27), (0, .23, 3.47), (0, .29, 3.70)],
            [.20, .18, .148], [.19, .17, .135], 'br_hair', 'head', normal=(1, 0, 0), steps=32, sides=36)
    base._axis_ring(g, 'Brumo_v2_topknot_forged_binding', (0, .255, 3.64), (0, .4, 1), .20, .16, .042, 'br_gold', 'head')
    for j in range(7):
        a = math.tau * j / 7
        h.lock(g, 'Brumo_v2_topknot_plume_' + str(j), [(0, .22, 3.53), (.13 * math.cos(a), .31 + .1 * math.sin(a), 3.72),
               (.20 * math.cos(a), .42 + .15 * math.sin(a), 3.88), (.28 * math.cos(a), .53 + .20 * math.sin(a), 4.02 - .075 * (j % 3))],
               .133, .066, 'br_hair_hi' if j == 2 else 'br_hair', normal=(0, -1, 0))


def build(g):
    spec = base._brumo(g)
    h.remove(g, lambda o: o.get('ast_part') in ('head', 'lid.L', 'lid.R') or any(q in o.name for q in (
        'round_pauldron', 'pauldron_bound', 'pauldron_emblem', 'cross_chest_harness', 'chest_insignia', 'belt_insignia',
        'wrist_fur', 'boot_fur', 'hip_lamella')))
    for key, color, metal, rough in [('br_skin', '72743A', 0, .68), ('br_inner', '444522', 0, .73),
        ('br_hair', '24141F', 0, .56), ('br_hair_hi', '2C1B26', 0, .55), ('br_armor', '2C192B', .12, .57),
        ('br_armor_hi', '3D2639', .12, .55), ('br_leather', '4F281B', 0, .61), ('br_gold', 'A3783B', .66, .40),
        ('br_gold_hi', 'C9A161', .60, .39), ('br_fur', 'CEB489', 0, .65), ('hv_white', 'FFFFFF', 0, .29)]:
        g.M[key] = g.material('brumo_v2_' + key, color, metal, rough)
    # Reassign old retained material slots to the refined palette.
    for obj in g.ASSET:
        for i, mat in enumerate(obj.data.materials):
            key = mat.name.removeprefix('AST_')
            if key in g.M: obj.data.materials[i] = g.M[key]
    head(g)
    for sign in (-1, 1):
        shoulder(g, sign)
        side = 'L' if sign > 0 else 'R'
        for which, center, radius, part in [('wrist', (sign * .73, -.041, 1.48), .18, 'arm.' + side),
                                           ('boot', (sign * .29, .019, .59), .185, 'leg.' + side)]:
            c = Vector(center)
            for j in range(16):
                a = math.tau * j / 16; d = Vector((math.cos(a), math.sin(a), 0))
                h.lock(g, 'Brumo_v2_' + which + '_fur_' + side + str(j),
                       [c + d * radius, c + d * (radius + .038) + Vector((0, 0, -.020)),
                        c + d * (radius + .068) + Vector((0, 0, -.053)), c + d * (radius + .062) + Vector((0, 0, -.102 - .024 * math.sin(j * 2)))],
                       .045 + .011 * (j % 3) / 2, .025, 'br_fur', part, normal=d, steps=32, sides=24)
        vs, fs = [], []; rows, cols = 36, 40
        def point(t, u):
            a = -math.pi / 2 + sign * (.15 + 1.66 * u)
            return Vector(((.472 + .072 * t) * math.cos(a), .01 + (.329 + .058 * t) * math.sin(a),
                           1.066 - t * (.38 + .07 * math.sin(math.pi * u))))
        for row in range(rows + 1):
            for col in range(cols + 1): vs.append(point(row / rows, col / cols))
        for row in range(rows):
            for col in range(cols):
                a = row * (cols + 1) + col; fs.append((a, a + 1, a + cols + 2, a + cols + 1))
        base._shell(g, 'Brumo_v2_curved_hip_lamella_' + side, vs, fs, 'br_armor_hi', 'body', .025, 0)
        edge = [point(i / 32, 0) for i in range(33)] + [point(1, i / 48) for i in range(1, 49)] + [point(1 - i / 32, 1) for i in range(1, 33)]
        h.ribbon(g, 'Brumo_v2_hip_lamella_border_' + side, edge, .045, 'br_gold', normal=(0, -1, 0), steps=96)
    cuirass = next(o for o in g.ASSET if 'fitted_aubergine_cuirass' in o.name)
    for sign in (-1, 1):
        front(g, cuirass, 'Brumo_v2_fitted_cross_harness_' + str(sign),
              [(sign * .29, -1, 1.96), (sign * .21, -1, 1.79), (0, -1, 1.65), (-sign * .39, -1, 1.43)], .065, 'br_gold')
        for z in (1.92, 1.77):
            front(g, cuirass, 'Brumo_v2_harness_stitch_' + str(sign) + str(z),
                  [(sign * .26, -1, z), (sign * .27, -1, z - .025)], .010, 'br_gold_hi')
    emblem(g, 'Brumo_v2_chest_star', (0, -.389, 1.72), .162, .188)
    emblem(g, 'Brumo_v2_belt_star', (0, -.421, 1.12), .171, .17)
    belt = next(o for o in g.ASSET if 'layered_leather_belt' in o.name)
    for prefix, target, original_y in [('Brumo_v2_chest_star', cuirass, -.389), ('Brumo_v2_belt_star', belt, -.421)]:
        bvh = h.tree(target)
        for obj in g.ASSET:
            if prefix not in obj.name: continue
            for vertex in obj.data.vertices:
                p = obj.matrix_world @ vertex.co
                query_z = max(1.045, min(1.195, p.z)) if target == belt else p.z
                hit, _, _, _ = bvh.ray_cast(Vector((p.x, -3, query_z)), Vector((0, 1, 0)))
                if hit is not None:
                    stand_off = .044 if target == cuirass else .009
                    p.y = hit.y - stand_off - max(0, original_y - p.y) * .30
                    vertex.co = obj.matrix_world.inverted() @ p
    # Material and modeled shallow relief work apply only to clothing surfaces.
    for obj in list(g.ASSET):
        if obj.name.startswith('AST_Brumo_') and '_bound_edge' not in obj.name and any(s in obj.name for s in ('cuirass', 'tabard', 'hip_plate', 'bracer', 'gaiter', 'leather_belt')):
            is_leather = any(s in obj.name for s in ('bracer', 'gaiter', 'leather_belt'))
            h.detail_surface(g, obj, '48251A' if is_leather else '332032', 'br_v2_leather_field' if is_leather else 'br_v2_cloth_field', .0035, subdiv=True)
    for obj in list(g.ASSET):
        if obj.data.materials and obj.data.materials[0] == g.M['br_skin']:
            h.color_mesh(g, obj, 'br_v2_skin_field', '72743A', lambda p, b: tuple(c * (.91 + .050 * math.sin(p.x * 31 + p.z * 16) * math.sin(p.y * 27 - p.z * 11)) for c in b[:3]) + (1,))
    spec['notes'] = ['Reference-led v002: smaller fitted amber eyes, broad olive face, short upward tusks, recessed ears and deeply scored swept topknot.',
                     'Forged shoulder armor, fitted broad cross straps, sculpted layered fur, textured leather, shaped hands and open-toe footwear.',
                     'Original portrait and v001 preserved. Hidden surfaces and neutral pose inferred; nine stylized clips do not establish collision-free gait.']
    return spec

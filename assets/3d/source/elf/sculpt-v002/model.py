"""Aelira v002: warm elven face, scored braided hair and embroidered tailoring.

The original portrait remains unchanged. Garment backs, braid routing and the
neutral stance are inferred. Geometry is volumetric and editable, not projected.
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


def seat_relief(g, names, targets, original_y, zrange=None):
    """Fit the ornament back and compress its cut relief onto actual support."""
    trees = [h.tree(obj) for obj in targets]
    for obj in g.ASSET:
        if not any(name in obj.name for name in names): continue
        inverse = obj.matrix_world.inverted()
        for vertex in obj.data.vertices:
            p = obj.matrix_world @ vertex.co
            z = max(zrange[0], min(zrange[1], p.z)) if zrange else p.z
            hits = [tree.ray_cast(Vector((p.x, -3, z)), Vector((0, 1, 0)))[0] for tree in trees]
            hits = [hit for hit in hits if hit is not None]
            if not hits: raise ValueError(obj.name + ': ornament has no supporting surface')
            p.y = min(hit.y for hit in hits) - .008 - max(0, original_y - p.y) * .32
            vertex.co = inverse @ p


def embroidery(g, target, name, points, mat, part='body', size=.043):
    """Raised leaf stitches seated on the real cloth, including every leaf tip."""
    bvh = h.tree(target)
    def surface(x, z, offset=.006):
        p, n, _, _ = bvh.ray_cast(Vector((x, -3, z)), Vector((0, 1, 0)))
        return p + n * offset if p is not None else None
    pts = [surface(x, z) for x, z in points]
    if any(p is None for p in pts): return
    g.line(name + '_vine_stitch', pts, .0045, mat, part, resolution=4)
    for j, (x, z) in enumerate(points[1:-1]):
        sign = -1 if j % 2 else 1
        start = Vector((x, z)); end = Vector((x + sign * size, z + size * .65))
        along = end - start; across = Vector((-along.y, along.x)).normalized()
        vs, fs = [], []; rows, cols = 20, 8
        missing = False
        for row in range(rows + 1):
            t = row / rows; center = start.lerp(end, t)
            for col in range(cols + 1):
                q = col / cols * 2 - 1
                p = center + across * (q * size * .26 * math.sin(math.pi * t))
                hit = surface(p.x, p.y, .007 + .004 * math.sin(math.pi * t) * (1 - q * q))
                if hit is None: missing = True; break
                vs.append(hit)
            if missing: break
        if missing: continue
        for row in range(rows):
            for col in range(cols):
                a = row * (cols + 1) + col; fs.append((a, a + 1, a + cols + 2, a + cols + 1))
        obj = g.mesh(name + '_embroidered_leaf_' + str(j), vs, fs, mat, part)
        mod = obj.modifiers.new('Embroidery thread body', 'SOLIDIFY'); mod.thickness = .003; g.apply(obj, mod)


def hand(g, sign, center, part):
    c = Vector(center); pieces = [g.uv('Aelira_v2_palm', c, (.116, .082, .141), 'ae_skin', part)]
    for j in range(4):
        x = c.x + (j - 1.5) * .047
        length = .131 - .019 * abs(j - 1.5)
        pieces.append(g.sweep('Aelira_v2_finger_' + str(sign) + str(j),
                      [(x, c.y, c.z - .060), (x, c.y - .012, c.z - .126),
                       (x + sign * .014, c.y - .039, c.z - .073 - length)],
                      [.028, .027, .015], [.031, .028, .019], 'ae_skin', part,
                      normal=(0, -1, 0), steps=26, sides=24))
    pieces.append(g.sweep('Aelira_v2_thumb_' + str(sign),
                  [(c.x - sign * .082, c.y, c.z + .052), (c.x - sign * .131, c.y - .031, c.z - .002),
                   (c.x - sign * .118, c.y - .066, c.z - .069)],
                  [.044, .036, .022], [.038, .032, .025], 'ae_skin', part, normal=(0, -1, 0), steps=28, sides=24))
    obj = g.fuse('Aelira_v2_shaped_hand_' + str(sign), pieces, part, voxel=.0095, subdiv=1)
    for j in range(4):
        x = c.x + (j - 1.5) * .047
        h.seated_line(g, 'Aelira_v2_knuckle_crease_' + str(sign) + str(j), obj,
                      [(x - .012, -1, c.z - .087), (x, -1, c.z - .092), (x + .012, -1, c.z - .088)], .002, 'ae_lip', part)


def face_and_hair(g):
    skin = 'ae_skin'
    head = g.fuse('Aelira_v2_refined_head', [
        g.uv('Aelira_v2_cranium', (0, .008, 2.864), (.52, .436, .595), skin, 'head', seg=80, rings=56),
        g.uv('Aelira_v2_soft_face', (0, -.188, 2.716), (.446, .315, .39), skin, 'head'),
        g.uv('Aelira_v2_tapered_chin', (0, -.143, 2.464), (.304, .276, .178), skin, 'head'),
        g.uv('Aelira_v2_cheekL', (.245, -.341, 2.696), (.18, .14, .17), skin, 'head'),
        g.uv('Aelira_v2_cheekR', (-.245, -.341, 2.696), (.18, .14, .17), skin, 'head'),
        g.uv('Aelira_v2_nose_bridge', (0, -.452, 2.722), (.048, .070, .10), skin, 'head'),
        g.uv('Aelira_v2_soft_nose', (0, -.507, 2.653), (.066, .069, .054), skin, 'head')], 'head', voxel=.0125, subdiv=1)
    for sign in (-1, 1):
        side = 'L' if sign > 0 else 'R'
        h.eye(g, 'Aelira_v2_eye_' + side, head, side, (sign * .232, -.46, 2.877), .312, .309,
              skin, 'ae_shadow', '542A6D', 'BE75DC')
        h.ear(g, 'Aelira_v2_leaf_ear_' + side, sign, 2.888, .955, skin, 'ae_inner')
        h.lock(g, 'Aelira_v2_brow_' + side, [(sign * .099, -.471, 3.068), (sign * .186, -.490, 3.102),
               (sign * .29, -.449, 3.103), (sign * .386, -.372, 3.062)], .029, .019, 'ae_hair', steps=44, sides=28)
        h.seated_line(g, 'Aelira_v2_nostril_' + side, head,
                      [(sign * .027, -1, 2.64), (sign * .043, -1, 2.635)], .003, 'ae_shadow')
    h.seated_line(g, 'Aelira_v2_warm_smile', head,
                  [(-.165, -1, 2.53), (-.072, -1, 2.510), (0, -1, 2.509), (.097, -1, 2.526), (.17, -1, 2.556)], .006, 'ae_shadow')
    h.seated_line(g, 'Aelira_v2_lower_lip', head, [(-.092, -1, 2.499), (0, -1, 2.489), (.085, -1, 2.514)], .009, 'ae_lip')
    cap = base._haircap(g, 'Aelira_v2', (0, .027, 2.874), (.562, .478, .655), 'ae_hair')
    # Raise the central forehead hairline, retaining the low temple/nape shape.
    for vertex in cap.data.vertices:
        p = vertex.co
        a = math.atan2((p.y - .027) / .478, p.x / .562)
        radius = math.sqrt((p.x / .562) ** 2 + ((p.y - .027) / .478) ** 2 + ((p.z - 2.874) / .655) ** 2)
        theta = math.acos(max(-1, min(1, (p.z - 2.874) / (.655 * radius))))
        theta *= 1 - .22 * max(0, -math.sin(a)) ** 4
        p.x = .562 * radius * math.sin(theta) * math.cos(a)
        p.y = .027 + .478 * radius * math.sin(theta) * math.sin(a)
        p.z = 2.874 + .655 * radius * math.cos(theta)
    # Asymmetric curtain part, overlying scored locks cover the under-cap edge.
    for sign in (-1, 1):
        for j in range(4):
            t = j / 3
            h.lock(g, 'Aelira_v2_parted_crown_' + str(sign) + '_' + str(j),
                   [(sign * .014, .26 - .18 * t, 3.49 - .03 * t),
                    (sign * .15, .05 - .26 * t, 3.53 - .015 * t),
                    (sign * .36, -.19 - .16 * t, 3.43 - .14 * t),
                    (sign * (.50 - .02 * t), -.24 - .08 * t, 3.05 + .13 * t)],
                   .165 - .015 * (j % 2), .042, 'ae_hair_hi' if j == 2 else 'ae_hair', steps=58, sides=36)
        h.lock(g, 'Aelira_v2_swept_hairline_' + str(sign),
               [(sign * .008, -.30, 3.43), (sign * .18, -.45, 3.38),
                (sign * .29, -.49, 3.18), (sign * .40, -.41, 3.07)],
               .150, .041, 'ae_hair', steps=60, sides=40)
        # The dominant framing curl narrows below the cheek and turns out.
        h.lock(g, 'Aelira_v2_face_framing_curl_' + str(sign),
               [(sign * .31, -.358, 3.30), (sign * .48, -.452, 3.018), (sign * .463, -.473, 2.72),
                (sign * .565, -.34, 2.493), (sign * .515, -.376, 2.326)], .09, .046, 'ae_hair', steps=90, sides=44)
        h.lock(g, 'Aelira_v2_secondary_curl_' + str(sign),
               [(sign * .48, -.16, 2.976), (sign * .561, -.23, 2.70), (sign * .54, -.34, 2.41),
                (sign * .457, -.37, 2.286)], .059, .035, 'ae_hair_hi', steps=70, sides=36)
    for j in range(10):
        longitude = (j - 4.5) / 4.5 * 1.45
        pts = []
        for theta in (.23, .83, 1.51, 2.22):
            pts.append((.593 * math.sin(theta) * math.sin(longitude),
                        .027 + .514 * math.sin(theta) * math.cos(longitude), 2.874 + .689 * math.cos(theta)))
        h.lock(g, 'Aelira_v2_back_swept_lock_' + str(j), pts, .128, .045, 'ae_hair',
               normal=(math.sin(longitude), math.cos(longitude), 0), steps=58, sides=36)
    # A true crossing plait, wider and less repetitive than the first-pass cord.
    route = [(.36, .272, 3.357), (.50, .25, 3.17), (.535, .08, 2.87),
             (.51, -.10, 2.63), (.44, -.28, 2.40), (.48, -.34, 2.19), (.46, -.36, 1.82)]
    centers = g.spline(route, 190)
    for strand in range(3):
        pts = []
        for i, c in enumerate(centers):
            t = i / 190; phase = math.tau * (t * 4.8 + strand / 3)
            pts.append(c + Vector((.078 * math.sin(phase), .049 * math.sin(2 * phase), 0)))
        obj = g.sweep('Aelira_v2_interwoven_plait_' + str(strand), pts, [.054, .070, .070, .054],
                      [.044, .054, .054, .044], 'ae_hair_hi' if strand == 0 else 'ae_hair', 'head',
                      normal=(0, -1, 0), steps=260, sides=40, flute=.07)
        h.detail_surface(g, obj, '23422E' if strand == 0 else '1C3427', 'ae_v2_braid_field_' + str(strand), .0008)
    for z in (1.830, 1.877):
        base._ring(g, 'Aelira_v2_braid_engraved_tie_' + str(z), (.46, -.36, z), .103, .089, .019, 'ae_gold', 'head')
    for j in range(6):
        h.lock(g, 'Aelira_v2_braid_tassel_' + str(j),
               [(.46 + (j - 2.5) * .019, -.36, 1.86), (.445 + (j - 2.5) * .024, -.405, 1.72),
                (.43 + (j - 2.5) * .027, -.382, 1.64), (.42 + (j - 2.5) * .031, -.35, 1.60 + .024 * abs(j - 2.5))],
               .032, .024, 'ae_hair', steps=46, sides=28)


def skirt(g, sign):
    vs, fs = [], []; rows, cols = 54, 44
    def point(t, u):
        hem = .82 - .17 * math.sin(math.pi * u) + .10 * u
        return Vector((sign * (.033 + .30 * u + (.068 + .12 * u) * t),
                       -.283 + .095 * u * u + .028 * math.sin(u * 10 + t * 1.4) * math.sin(math.pi * t) + .038 * t * t,
                       1.454 * (1 - t) + hem * t))
    for row in range(rows + 1):
        for col in range(cols + 1): vs.append(point(row / rows, col / cols))
    for row in range(rows):
        for col in range(cols):
            a = row * (cols + 1) + col; fs.append((a, a + 1, a + cols + 2, a + cols + 1))
    obj = base._shell(g, 'Aelira_v2_tailored_split_skirt_' + str(sign), vs, fs, 'ae_cream', 'body', .018, 0)
    edge = [point(i / 40, 0) for i in range(41)] + [point(1, i / 48) for i in range(1, 49)] + [point(1 - i / 40, 1) for i in range(1, 41)]
    h.ribbon(g, 'Aelira_v2_skirt_leather_binding_' + str(sign), [p + Vector((0, -.012, 0)) for p in edge], .037, 'ae_leather', steps=112)
    h.ribbon(g, 'Aelira_v2_skirt_fine_gold_edge_' + str(sign), [p + Vector((0, -.024, 0)) for p in edge], .012, 'ae_gold', steps=112)
    return obj


def cape_point(t, a, offset=0):
    """Draped cloth surface; common parameterization also seats its embroidery."""
    fold = (.038 * math.sin(6 * a + .3 * math.sin(t * 3)) + .012 * math.sin(13 * a - t)) * t ** .65
    rx = .43 + .47 * t ** .82 + fold
    ry = .275 + .235 * t + fold
    p = Vector((rx * math.cos(a), .065 + ry * math.sin(a) + .14 * (1 - t) ** 2 * abs(math.cos(a)) ** 6,
                2.16 * (1 - t) + .32 * t + .048 * math.cos(6 * a + .25) * t * t))
    return p + Vector((math.cos(a), math.sin(a), 0)) * offset


def cape_leaf(g, name, start, end, width=.040):
    """Small solid embroidery leaf conforming to the curved cape parameters."""
    vs, fs = [], []; rows, cols = 14, 6
    dt, da = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dt * 1.84, da * .70)
    for row in range(rows + 1):
        t = row / rows
        for col in range(cols + 1):
            q = col / cols * 2 - 1; across = q * width * math.sin(math.pi * t)
            tt = start[0] + dt * t - da * .70 / length * across / 1.84
            aa = start[1] + da * t + dt * 1.84 / length * across / .70
            vs.append(cape_point(tt, aa, .009 + .005 * math.sin(math.pi * t) * (1 - q * q)))
    for row in range(rows):
        for col in range(cols):
            a = row * (cols + 1) + col; fs.append((a, a + cols + 1, a + cols + 2, a + 1))
    obj = g.mesh(name, vs, fs, 'ae_gold', 'body')
    mod = obj.modifiers.new('Raised gold thread', 'SOLIDIFY'); mod.thickness = .0025; g.apply(obj, mod)


def cloak(g):
    vs, fs = [], []; rows, cols = 76, 116
    for row in range(rows + 1):
        for col in range(cols + 1): vs.append(cape_point(row / rows, -.31 + (math.pi + .62) * col / cols))
    for row in range(rows):
        for col in range(cols):
            a = row * (cols + 1) + col; fs.append((a, a + cols + 1, a + cols + 2, a + 1))
    cape = base._shell(g, 'Aelira_v2_full_folded_forest_cape', vs, fs, 'ae_cloak', 'body', .022, 0)
    h.detail_surface(g, cape, '123C33', 'ae_v2_cape_woven_field', .0017)
    for sign in (-1, 1):
        edge = -.31 if sign < 0 else math.pi + .31
        into = -sign
        g.line('Aelira_v2_cape_gold_selvedge_' + str(sign), [cape_point(i / 100, edge, .004) for i in range(101)], .012, 'ae_gold', 'body', resolution=2)
        pts = [cape_point(.12 + i / 80 * .82, edge + into * (.088 + .020 * math.sin(i / 80 * 9)), .01) for i in range(81)]
        g.line('Aelira_v2_cape_margin_vine_' + str(sign), pts, .005, 'ae_gold', 'body', resolution=2)
        for j in range(16):
            t = .16 + .047 * j; a = edge + into * (.088 + .020 * math.sin((t - .12) / .82 * 9))
            cape_leaf(g, 'Aelira_v2_cape_margin_leaf_' + str(sign) + '_' + str(j), (t, a), (t - .035, a + into * .080), .012)
        # Neck-to-shoulder mantle is a closed-thickness cloth piece, not a floating collar tube.
    mantle_v, mantle_f = [], []; radial, around = 28, 104
    for row in range(radial + 1):
        t = row / radial
        for col in range(around):
            a = math.tau * col / around
            mantle_v.append(((.17 + .39 * t) * math.cos(a), .035 + (.175 + .18 * t) * math.sin(a),
                             2.305 - .245 * t - .040 * math.sin(a) * t + .014 * math.sin(7 * a + t) * t))
    for row in range(radial):
        for col in range(around):
            a = row * around + col; b = row * around + (col + 1) % around
            mantle_f.append((a, a + around, b + around, b))
    mantle = base._shell(g, 'Aelira_v2_connected_cloak_mantle', mantle_v, mantle_f, 'ae_cloak', 'body', .023, 0)
    h.detail_surface(g, mantle, '163F33', 'ae_v2_mantle_field', .0015)
    g.line('Aelira_v2_mantle_gold_edge', [Vector(mantle_v[radial * around + j % around]) + Vector((0, 0, .006)) for j in range(around + 1)], .010, 'ae_gold', 'body', resolution=2)
    g.line('Aelira_v2_cape_embroidered_hem', [cape_point(.947, -.24 + (math.pi + .48) * i / 120, .011) for i in range(121)], .005, 'ae_gold', 'body', resolution=2)
    for j in range(28):
        a = -.16 + (math.pi + .32) * j / 27
        cape_leaf(g, 'Aelira_v2_cape_hem_leaf_' + str(j), (.947, a), (.914, a + .052), .013)
    return cape, mantle


def boot_details(g, sign, side):
    part = 'leg.' + side; boot = next(o for o in g.ASSET if 'shaped_boot_' + side in o.name)
    vs, fs = [], []; rows, cols = 12, 80
    def point(t, a):
        return Vector((sign * .255 + (.166 + .013 * t) * math.cos(a),
                       .01 + (.180 + .009 * t) * math.sin(a), .423 + .088 * t + .036 * math.cos(2 * a)))
    for row in range(rows + 1):
        for col in range(cols): vs.append(point(row / rows, math.tau * col / cols))
    for row in range(rows):
        for col in range(cols):
            a = row * cols + col; b = row * cols + (col + 1) % cols; fs.append((a, b, b + cols, a + cols))
    cuff = base._shell(g, 'Aelira_v2_shaped_cream_boot_cuff_' + side, vs, fs, 'ae_cream', part, .012, 0)
    for t in (.08, .94):
        g.line('Aelira_v2_cuff_gold_stitch_' + side + str(t), [point(t, math.tau * j / 80) for j in range(81)], .006, 'ae_gold', part, resolution=2)
    bvh = h.tree(boot)
    for index, z in enumerate((.20, .33)):
        pts = []
        for j in range(49):
            x = sign * .255 - .109 + .218 * j / 48; zz = z + .025 * (1 - 2 * j / 48)
            p, n, _, _ = bvh.ray_cast(Vector((x, -3, zz)), Vector((0, 1, 0)))
            if p is None: raise ValueError('Boot strap has no support')
            pts.append(p + n * .008)
        h.ribbon(g, 'Aelira_v2_fitted_boot_strap_' + side + str(index), pts, .053, 'ae_leather', part, steps=64)
        original_y = -.29 + .05 * index
        base._diamond(g, 'Aelira_v2_boot_buckle_' + side + str(index), (sign * .255, original_y, z), .046, .055, 'ae_gold', 'ae_leather', part)
        seat_relief(g, ['Aelira_v2_boot_buckle_' + side + str(index)], [boot], original_y)
    h.seated_line(g, 'Aelira_v2_toecap_stitch_' + side, boot,
                  [(sign * .255 - .125, -1, .095), (sign * .255, -1, .137), (sign * .255 + .125, -1, .095)], .003, 'ae_gold', part)
    embroidery(g, cuff, 'Aelira_v2_cuff_leaf_' + side,
               [(sign * .255 - .080 + .020 * j, .472 + .008 * math.sin(j)) for j in range(9)], 'ae_forest', part, .023)


def build(g):
    spec = base._aelira(g)
    h.remove(g, lambda o: o.get('ast_part') in ('head', 'lid.L', 'lid.R') or any(q in o.name for q in (
        'sculpted_hand', 'split_cream_skirt', '_embroidery_', 'tabard_gold_sprig', 'cloak_star_clasp', 'belt_leaf_clasp',
        'boot_cuff', 'boot_buckle', 'boot_strap', 'full_lined_forest_cape', 'cape_gold_selvedge',
        'cape_weighted_hem', 'draped_cloak_shoulder', 'cloak_shoulder_gold_seam')))
    for key, tint, metal, rough in [('ae_skin', 'C4864D', 0, .64), ('ae_inner', '925531', 0, .68),
        ('ae_shadow', '593723', 0, .70), ('ae_lip', 'B96E4C', 0, .59), ('ae_hair', '1A3427', 0, .55),
        ('ae_hair_hi', '284A32', 0, .53), ('ae_forest', '2B4128', 0, .72), ('ae_cloak', '123C33', 0, .73),
        ('ae_lining', '20594B', 0, .70), ('ae_cream', 'CFC09F', 0, .79), ('ae_cream_hi', 'DDCDB0', 0, .77),
        ('ae_leather', '493120', 0, .64), ('ae_gold', 'AA804A', .60, .44), ('ae_gold_hi', 'C49D64', .58, .42),
        ('hv_white', 'FFFFFF', 0, .29)]:
        g.M[key] = g.material('aelira_v2_' + key, tint, metal, rough)
    for obj in g.ASSET:
        for i, material in enumerate(obj.data.materials):
            key = material.name.removeprefix('AST_')
            if key in g.M: obj.data.materials[i] = g.M[key]
    face_and_hair(g)
    cape, mantle = cloak(g)
    skirts = {sign: skirt(g, sign) for sign in (-1, 1)}
    for sign in (-1, 1):
        side = 'L' if sign > 0 else 'R'; arm = 'arm.' + side; leg = 'leg.' + side
        center = (sign * .64, -.18, 1.18) if sign < 0 else (.49, -.33, 1.36)
        hand(g, sign, center, arm)
        boot_details(g, sign, side)
    # Real shallow folds and woven color fields on retained tailoring.
    for obj in list(g.ASSET):
        name = obj.name
        if not name.startswith('AST_Aelira_') or any(q in name for q in ('edge', 'seam', 'stitch', 'bound', 'binding', 'buckle', 'gold', 'clasp')): continue
        if any(q in name for q in ('cream_tunic', 'cream_sleeve', 'tailored_split_skirt')):
            h.detail_surface(g, obj, 'CFC09F', 'ae_v2_woven_cream', .003, subdiv=True)
        elif any(q in name for q in ('forest_trouser', 'center_tabard', 'forest_v_neck')):
            h.detail_surface(g, obj, '293D25', 'ae_v2_woven_green', .003, subdiv=True)
        elif 'full_lined_forest_cape' in name:
            h.detail_surface(g, obj, '123C33', 'ae_v2_woven_cape', .0035)
        elif any(q in name for q in ('shaped_boot', 'wide_leather_belt', 'leaf_vambrace')):
            h.detail_surface(g, obj, '48301F' if 'vambrace' not in name else '2C4429', 'ae_v2_leather' if 'vambrace' not in name else 'ae_v2_green_leather', .002, subdiv=True)
    tunic = next(o for o in g.ASSET if 'cream_tunic' in o.name)
    for sign in (-1, 1):
        embroidery(g, tunic, 'Aelira_v2_bodice_vine_' + str(sign),
                   [(sign * (.16 + .028 * math.sin(j * .70)), 1.69 + .045 * j) for j in range(10)], 'ae_forest', size=.033)
        embroidery(g, skirts[sign], 'Aelira_v2_skirt_vine_' + str(sign),
                   [(sign * (.207 + .011 * j), 1.24 - .041 * j) for j in range(10)], 'ae_forest', size=.032)
        sleeve = next(o for o in g.ASSET if 'soft_cream_sleeve_' + ('L' if sign > 0 else 'R') in o.name)
        embroidery(g, sleeve, 'Aelira_v2_sleeve_vine_' + str(sign),
                   [(sign * (.45 + .017 * j), 2.038 - .028 * j) for j in range(8)], 'ae_forest', 'arm.' + ('L' if sign > 0 else 'R'), .028)
        vambrace = next(o for o in g.ASSET if 'leaf_vambrace_' + ('L' if sign > 0 else 'R') in o.name)
        embroidery(g, vambrace, 'Aelira_v2_vambrace_laurel_' + str(sign),
                   [(sign * (.643 if sign < 0 else .525 + .014 * j), (1.40 if sign < 0 else 1.54) + .026 * j) for j in range(8)],
                   'ae_gold', 'arm.' + ('L' if sign > 0 else 'R'), .032)
    tabard = next(o for o in g.ASSET if o.name == 'AST_Aelira_center_tabard')
    embroidery(g, tabard, 'Aelira_v2_tabard_gold_laurel', [(0, .72 + .034 * j) for j in range(13)], 'ae_gold', size=.038)
    # Small architectural fasteners rather than featureless oversized diamonds.
    for name, center, rx, rz in [('cloak', (0, -.324, 2.154), .087, .104), ('belt', (0, -.313, 1.538), .128, .143)]:
        base._diamond(g, 'Aelira_v2_' + name + '_clasp', center, rx, rz, 'ae_gold', 'ae_leather')
        x, y, z = center
        poly = [(0, rz * .70), (rx * .15, rz * .15), (rx * .68, 0), (rx * .15, -rz * .15), (0, -rz * .70), (-rx * .15, -rz * .15), (-rx * .68, 0), (-rx * .15, rz * .15)]
        g.mesh('Aelira_v2_' + name + '_leaf_star', [(x + xx, y - .070, z + zz) for xx, zz in poly] + [(x, y - .084, z)],
               [(j, (j + 1) % 8, 8) for j in range(8)], 'ae_gold_hi', 'body', smooth=False)
        if name == 'belt':
            support = [o for o in g.ASSET if 'wide_leather_belt' in o.name]
            limits = (1.46, 1.61)
        else:
            support = [o for o in g.ASSET if any(q in o.name for q in ('cream_tunic', 'forest_v_neck_insert', 'connected_cloak_mantle')) and 'edge' not in o.name]
            limits = (2.07, 2.195)
        seat_relief(g, ['Aelira_v2_' + name + '_clasp', 'Aelira_v2_' + name + '_leaf_star'], support, y, limits)
    # Skin is initialized after both Boolean sockets, preventing black cut rings.
    for obj in list(g.ASSET):
        if obj.data.materials and obj.data.materials[0] == g.M['ae_skin']:
            def tint(p, b):
                blush = math.exp(-((abs(p.x) - .29) / .16) ** 2 - ((p.z - 2.69) / .15) ** 2 - ((p.y + .43) / .19) ** 2)
                grain = .97 + .016 * math.sin(p.x * 48 + p.z * 31) * math.sin(p.y * 39 - p.z * 28)
                return (b[0] * grain, b[1] * grain * (1 - .12 * blush), b[2] * grain * (1 - .09 * blush), 1)
            h.color_mesh(g, obj, 'ae_v2_warm_skin', 'C4864D', tint)
    spec['notes'] = ['Reference-led v002: modest violet almond eyes, warm cheeks, refined elven muzzle, genuinely recessed long ears and tapered brows.',
                     'Overlapping scored crown locks, three crossing braid strands, loose face curls, embroidered cream tailoring and shaped open fingers.',
                     'Layered cuff boots, crossed leather straps, leaf clasps and textured lined cape. Hidden construction inferred; original portrait and v001 preserved.']
    return spec

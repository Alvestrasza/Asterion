"""Brumo and Aelira: separate volumetric sculptures from the original portraits.

Only the supplied front-quarter portraits are authoritative. Backs, hair routing,
garment construction and neutral standing poses are coherent interpretations.
"""
from __future__ import annotations
import math
import random
import bpy
from mathutils import Vector
from common import eye

TAU = math.tau


def _mats(g, prefix, specs):
    for key, value in specs.items():
        m = g.material(prefix + key, *value)
        # The shared bright studio otherwise washes out the portrait palette.
        factor = (.42 if key.startswith('hair') else .64 if key in ('skin', 'inner')
                  else .72 if key.startswith('gold') else .76 if key in ('fur', 'cream', 'cream_hi')
                  else .72 if key.startswith('armor') else 1)
        if factor != 1:
            rgba = tuple(c * factor for c in m.diffuse_color[:3]) + (1,)
            m.diffuse_color = rgba
            m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = rgba
        g.M[prefix + key] = m


def _shell(g, name, vertices, faces, mat, part, thickness=.022, subdiv=1):
    o = g.mesh(name, vertices, faces, mat, part)
    if subdiv:
        mod = o.modifiers.new('Tailored smooth construction', 'SUBSURF')
        mod.levels = subdiv
        g.apply(o, mod)
    mod = o.modifiers.new('Physical material thickness', 'SOLIDIFY')
    mod.thickness = thickness
    g.apply(o, mod)
    return o


def _tube(g, name, rows, mat, part='body', sides=72, steps=32):
    """A closed tailored torso/boot volume, rows=(Z, X radius, Y radius, Y center)."""
    verts, faces = [], []
    for i in range(steps + 1):
        t = i / steps * (len(rows) - 1)
        k = min(int(t), len(rows) - 2)
        f = t - k
        z, rx, ry, cy = [rows[k][j] * (1 - f) + rows[k + 1][j] * f for j in range(4)]
        for j in range(sides):
            a = TAU * j / sides
            fold = 1 + .009 * math.cos(12 * a + .25 * i)
            verts.append((rx * math.cos(a) * fold, cy + ry * math.sin(a) * fold, z))
    for i in range(steps):
        for j in range(sides):
            a = i * sides + j
            b = i * sides + (j + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces.extend([tuple(reversed(range(sides))), tuple(steps * sides + j for j in range(sides))])
    return g.mesh(name, verts, faces, mat, part)


def _ring(g, name, center, rx, ry, thickness, mat, part, slope=0):
    x, y, z = center
    pts = [(x + rx * math.cos(TAU * j / 64), y + ry * math.sin(TAU * j / 64),
            z + slope * math.cos(TAU * j / 64)) for j in range(65)]
    return g.line(name, pts, thickness, mat, part, resolution=2)


def _axis_ring(g, name, center, axis, rx, ry, thickness, mat, part):
    c, t = Vector(center), Vector(axis).normalized()
    n = Vector((0, -1, 0)); n = (n - t * n.dot(t)).normalized()
    u = t.cross(n).normalized()
    pts = [c + u * (rx * math.cos(TAU * j / 64)) + n * (ry * math.sin(TAU * j / 64)) for j in range(65)]
    return g.line(name, pts, thickness, mat, part, resolution=2)


def _panel(g, name, center, width, height, mat, trim, part='body', pointed=True, bow=.04):
    """Curved, thick-backed cloth/metal shield panel, with modeled perimeter."""
    x0, y0, z0 = center
    vs, fs, edge = [], [], []
    nu, nv = 24, 28
    def point(u, t):
        taper = (1 - .94 * max(0, (t - .67) / .33)) if pointed else (1 - .12 * t)
        xx = width * u * taper
        return (x0 + xx, y0 + bow * u * u - .016 * t, z0 - height * t)
    for i in range(nv + 1):
        for j in range(nu + 1):
            vs.append(point(-1 + 2 * j / nu, i / nv))
    for i in range(nv):
        for j in range(nu):
            a = i * (nu + 1) + j
            fs.append((a, a + 1, a + nu + 2, a + nu + 1))
    o = _shell(g, name, vs, fs, mat, part, .025, 1)
    for i in range(17): edge.append(point(-1, i / 16))
    for i in range(1, 17): edge.append(point(-1 + 2 * i / 16, 1))
    for i in range(1, 17): edge.append(point(1, 1 - i / 16))
    if trim:
        edge = [(x, y - .032, z) for x, y, z in edge]
        g.line(name + '_bound_edge', edge, .022, trim, part, resolution=2)
    return o


def _diamond(g, name, center, rx, rz, gold, inner, part='body'):
    x, y, z = center
    corners = [(x, y, z + rz), (x + rx, y, z), (x, y, z - rz), (x - rx, y, z)]
    back = [(a, b + .035, c) for a, b, c in corners]
    vertices = corners + [(x, y - .060, z)] + back
    faces = [(i, (i + 1) % 4, 4) for i in range(4)]
    faces += [(i, i + 5, (i + 1) % 4 + 5, (i + 1) % 4) for i in range(4)]
    faces.append((8, 7, 6, 5))
    g.mesh(name + '_cut_setting', vertices, faces, inner, part, smooth=False)
    g.line(name + '_metal_bezel', corners + [corners[0]], .024, gold, part, resolution=1)


def _leaf(g, name, points, width, depth, mat, part='head', steps=22):
    return g.sweep(name, points, [.04 * width, width, width * .77, .001],
                   [depth * .5, depth, depth * .65, .001], mat, part,
                   normal=(0, -1, 0), steps=steps, sides=18, flute=.055, ridge=depth * .18)


def _ears(g, prefix, base_z, span, skin, inner, part='head'):
    for s in (-1, 1):
        side = 'L' if s > 0 else 'R'
        pts = [(s * .53, -.015, base_z), (s * .69, -.03, base_z + .055),
               (s * (span - .13), .035, base_z + .26), (s * span, .045, base_z + .39)]
        g.sweep(prefix + '_ear_' + side, pts, [.13, .21, .105, .001],
                [.07, .065, .035, .001], skin, part, normal=(0, -1, 0), steps=36, sides=28)
        ip = [(s * .61, -.078, base_z + .02), (s * .75, -.084, base_z + .13),
              (s * (span - .17), -.012, base_z + .28), (s * (span - .035), .022, base_z + .37)]
        g.sweep(prefix + '_ear_recess_' + side, ip, [.045, .120, .060, .001],
                [.018, .02, .011, .001], inner, part, normal=(0, -1, 0), steps=30, sides=22)
        g.line(prefix + '_ear_fold_' + side,
               [(s * .61, -.103, base_z - .06), (s * .73, -.11, base_z + .04),
                (s * .76, -.09, base_z + .13)], .028, skin, part)


def _haircap(g, prefix, center, radii, mat):
    cx, cy, cz = center
    rx, ry, rz = radii
    sides, rows = 80, 44
    vs, fs = [], []
    for i in range(rows + 1):
        for j in range(sides):
            a = TAU * j / sides
            # Forehead stays exposed; the back is covered down to the nape.
            limit = 1.61 + .55 * math.sin(a)
            t = .012 + (limit - .012) * i / rows
            ripple = 1 + .012 * math.cos(12 * a + 1.8 * t)
            vs.append((cx + rx * math.sin(t) * math.cos(a) * ripple,
                       cy + ry * math.sin(t) * math.sin(a) * ripple,
                       cz + rz * math.cos(t)))
    for i in range(rows):
        for j in range(sides):
            a = i * sides + j
            b = i * sides + (j + 1) % sides
            fs.append((a, b, b + sides, a + sides))
    return _shell(g, prefix + '_sculpted_hair_cap', vs, fs, mat, 'head', .026, 1)


def _hand(g, prefix, center, skin, part, small=False):
    x, y, z = center
    scale = .8 if small else 1
    parts = [g.uv(prefix + '_palm', center, (.145 * scale, .112 * scale, .165 * scale), skin, part)]
    for j in range(4):
        xx = x + (j - 1.5) * .060 * scale
        parts.append(g.uv(prefix + '_finger_' + str(j), (xx, y - .018, z - .13 * scale),
                          (.043 * scale, .082 * scale, (.09 - .012 * abs(j - 1.5)) * scale), skin, part, seg=24, rings=18))
    side = 1 if x > 0 else -1
    parts.append(g.uv(prefix + '_thumb', (x - side * .128 * scale, y - .054, z),
                      (.066 * scale, .077 * scale, .101 * scale), skin, part, seg=28, rings=20))
    return g.fuse(prefix + '_sculpted_hand', parts, part, voxel=.013 if small else .016, subdiv=1)


def _fur_ring(g, name, center, radius, mat, part, count=13):
    x, y, z = center
    for j in range(count):
        a = TAU * j / count
        p = (x + radius * math.cos(a), y + radius * math.sin(a), z)
        ca = a + .12 * (-1 if j % 2 else 1)
        end = (x + (radius + .078) * math.cos(ca), y + (radius + .078) * math.sin(ca), z - .075 - .028 * (j % 3))
        mid = (x + (radius + .043) * math.cos(a), y + (radius + .043) * math.sin(a), z + .005)
        g.sweep(name + str(j), [p, mid, end], [.037, .058 + .009 * (j % 2), .001],
                [.024, .035, .001], mat, part, normal=(math.cos(a), math.sin(a), 0), steps=20, sides=16, flute=.10)


def _face(g, prefix, z, skin, blush, iris, broad):
    rx, ry = (.64, .49) if broad else (.54, .435)
    parts = [g.uv(prefix + '_cranium', (0, 0, z), (rx, ry, .65), skin, 'head', seg=64, rings=48),
             g.uv(prefix + '_face_plane', (0, -.225, z - .125), (rx * .91, .36, .44), skin, 'head'),
             g.uv(prefix + '_chin', (0, -.15, z - .39), (rx * .72, .32, .22), skin, 'head')]
    if broad:
        parts.extend([g.uv(prefix + '_cheek_' + str(s), (s * .30, -.40, z - .25), (.28, .22, .22), skin, 'head') for s in (-1, 1)])
    head = g.fuse(prefix + '_sculpted_head', parts, 'head', voxel=.022, subdiv=1)
    for s in (-1, 1):
        side = 'L' if s > 0 else 'R'
        eye(g, prefix + '_eye_' + side, (s * (.285 if broad else .249), -.525 if broad else -.486, z + .015),
            (s * .20, -.979, .025), .422 if broad else .399, .442 if broad else .388,
            iris, skin, side, head=head)
    nose_parts = [g.uv(prefix + '_nose_bridge', (0, -.548 if broad else -.48, z - .155),
                       (.093 if broad else .048, .11 if broad else .072, .14 if broad else .102), skin, 'head'),
                  g.uv(prefix + '_nose_tip', (0, -.633 if broad else -.56, z - .214),
                       (.14 if broad else .068, .10 if broad else .063, .078 if broad else .059), skin, 'head')]
    g.fuse(prefix + '_nose', nose_parts, 'head', voxel=.012, subdiv=1)
    for s in (-1, 1):
        g.uv(prefix + '_nostril_' + str(s), (s * (.085 if broad else .040), -.705 if broad else -.602, z - .235),
             (.028 if broad else .014, .010, .015 if broad else .009), prefix + 'shadow', 'head', seg=24, rings=16)
    mw = .31 if broad else .185
    my = -.59 if broad else -.477
    g.line(prefix + '_smiling_mouth', [(-mw, my + .016, z - .334), (-mw * .56, my - .028, z - .373),
               (0, my - .045, z - .378), (mw * .6, my - .026, z - .365), (mw, my + .014, z - .322)],
           .012 if broad else .009, prefix + 'shadow', 'head')
    if not broad:
        g.sweep(prefix + '_lower_lip', [(-.10, -.516, z - .386), (0, -.532, z - .397), (.11, -.511, z - .38)],
                [.005, .023, .003], [.006, .014, .003], blush, 'head', normal=(0, -1, 0), steps=24, sides=16)
    return head


def _brumo(g):
    p = 'br_'
    _mats(g, p, {
        'skin': ('7D8040', 0, .72), 'inner': ('535426', 0, .76), 'shadow': ('343420', 0, .8),
        'hair': ('281A23', 0, .56), 'hair_hi': ('442B35', 0, .58),
        'armor': ('342333', .16, .59), 'armor_hi': ('483048', .13, .62),
        'leather': ('502D21', 0, .72), 'seam': ('251813', 0, .8),
        'gold': ('A97D42', .64, .42), 'gold_hi': ('CFAC69', .60, .38),
        'fur': ('C7AA78', 0, .78), 'ivory': ('EAD5AC', 0, .54), 'nail': ('626238', 0, .8),
    })
    skin, gold = p + 'skin', p + 'gold'
    g.uv('Brumo_padded_torso', (0, .04, 1.54), (.46, .27, .52), skin, 'body', seg=56, rings=40)
    g.uv('Brumo_neck', (0, .01, 2.07), (.26, .25, .26), skin, 'body')
    _face(g, p, 2.84, skin, skin, 'C77A16', True)
    _ears(g, p, 2.89, 1.04, skin, p + 'inner')
    for s in (-1, 1):
        side = 'L' if s > 0 else 'R'
        _leaf(g, 'Brumo_expressive_brow_' + side,
              [(s * .105, -.546, 3.085), (s * .25, -.555, 3.16), (s * .39, -.50, 3.14), (s * .46, -.43, 3.085)],
              .072, .045, p + 'hair')
        g.sweep('Brumo_small_tusk_' + side, [(s * .30, -.585, 2.46), (s * .315, -.655, 2.49),
                (s * .325, -.657, 2.59), (s * .315, -.639, 2.65)],
                [.070, .066, .035, .001], [.065, .050, .028, .001], p + 'ivory', 'head', normal=(1, 0, 0), steps=26, sides=24)
    _haircap(g, 'Brumo', (0, .035, 2.89), (.667, .524, .69), p + 'hair')
    # A dense swept crest, with overlapping locks, not a generic sphere of hair.
    for j in range(9):
        t = (j - 4) / 4
        root = (t * .55, -.34 + .14 * abs(t), 3.21 - .11 * abs(t))
        _leaf(g, 'Brumo_swept_forelock_' + str(j), [root,
              (t * .49 - .06, -.29, 3.43 - .05 * abs(t)), (t * .45 + .08, -.06, 3.65),
              (t * .40 + .20, .12, 3.80 - .14 * abs(t) + .08 * math.sin(j * 2.3))],
              .17 - .025 * abs(t), .076, p + ('hair_hi' if j % 4 == 0 else 'hair'))
    for s in (-1, 1):
        for j in range(7):
            z = 3.37 - j * .09
            _leaf(g, 'Brumo_side_lock_' + str(s) + '_' + str(j),
                  [(s * .48, .01, z), (s * .63, .07, z + .04), (s * .63, .34, z + .12), (s * .56, .49, z + .18)],
                  .105, .056, p + 'hair')
    _ring(g, 'Brumo_topknot_gold_binding', (0, .25, 3.76), .185, .15, .040, gold, 'head')
    for j in range(8):
        a = TAU * j / 8
        _leaf(g, 'Brumo_topknot_lock_' + str(j), [(0, .18, 3.56),
              (.11 * math.cos(a), .22 + .10 * math.sin(a), 3.80),
              (.24 * math.cos(a), .29 + .18 * math.sin(a), 3.96),
              (.30 * math.cos(a), .36 + .23 * math.sin(a), 4.10 - .09 * (j % 3))],
              .127, .07, p + ('hair_hi' if j % 3 == 0 else 'hair'))
    _tube(g, 'Brumo_fitted_aubergine_cuirass', [(1.17, .45, .31, .03), (1.50, .54, .355, .015),
           (1.88, .52, .34, .035), (2.02, .34, .285, .04)], p + 'armor')
    _ring(g, 'Brumo_collar_rim', (0, .04, 2.01), .34, .286, .026, gold, 'body')
    _ring(g, 'Brumo_cuirass_hem', (0, .03, 1.22), .47, .323, .025, gold, 'body')
    for s in (-1, 1):
        side = 'L' if s > 0 else 'R'
        arm = 'arm.' + side
        shoulder, elbow, wrist = (s * .50, .035, 1.91), (s * .73, -.005, 1.56), (s * .71, -.145, 1.17)
        g.sweep('Brumo_strong_arm_' + side, [shoulder, elbow, wrist], [.225, .187, .14], [.22, .17, .14],
                skin, arm, normal=(0, -1, 0), steps=42, sides=32)
        _hand(g, 'Brumo_hand_' + side, (s * .695, -.17, 1.07), skin, arm)
        g.uv('Brumo_round_pauldron_' + side, (s * .55, .025, 1.915), (.30, .372, .245), p + 'armor_hi', arm)
        _ring(g, 'Brumo_pauldron_bound_edge_' + side, (s * .55, .025, 1.84), .282, .35, .034, gold, arm, slope=s * -.045)
        _diamond(g, 'Brumo_pauldron_emblem_' + side, (s * .68, -.276, 1.952), .080, .093, gold, p + 'gold_hi', arm)
        g.sweep('Brumo_leather_bracer_' + side, [(s * .72, -.115, 1.22), (s * .735, -.071, 1.38), (s * .731, -.037, 1.47)],
                [.166, .18, .174], [.163, .178, .17], p + 'leather', arm, normal=(0, -1, 0), steps=26, sides=36)
        _ring(g, 'Brumo_bracer_bottom_rim_' + side, (s * .72, -.115, 1.23), .170, .16, .022, gold, arm)
        _fur_ring(g, 'Brumo_wrist_fur_' + side, (s * .73, -.041, 1.48), .18, p + 'fur', arm)
        leg = 'leg.' + side
        g.sweep('Brumo_leg_' + side, [(s * .27, .045, 1.04), (s * .29, .025, .70), (s * .30, -.005, .29)],
                [.225, .197, .155], [.235, .19, .16], skin, leg, normal=(0, -1, 0), steps=34, sides=30)
        footparts = [g.uv('Brumo_foot_' + side, (s * .30, -.125, .155), (.227, .335, .150), skin, leg)]
        for j in range(4):
            xx = s * .30 + (j - 1.5) * .103
            footparts.append(g.uv('Brumo_toe_' + side + str(j), (xx, -.352, .117), (.070, .119, .089), skin, leg, seg=24, rings=18))
            g.uv('Brumo_toenail_' + side + str(j), (xx, -.464, .133), (.041, .017, .032), p + 'nail', leg, seg=20, rings=14)
        g.fuse('Brumo_foot_sculpt_' + side, footparts, leg, voxel=.015, subdiv=1)
        g.sweep('Brumo_boot_gaiter_' + side, [(s * .30, .006, .21), (s * .30, .006, .40), (s * .29, .019, .58)],
                [.192, .198, .188], [.185, .193, .188], p + 'leather', leg, normal=(0, -1, 0), steps=25, sides=36)
        _ring(g, 'Brumo_boot_ankle_edge_' + side, (s * .30, .008, .28), .196, .195, .025, gold, leg)
        _fur_ring(g, 'Brumo_boot_fur_' + side, (s * .29, .019, .59), .185, p + 'fur', leg)
        _diamond(g, 'Brumo_boot_buckle_' + side, (s * .30, -.185, .46), .079, .099, gold, p + 'leather', leg)
    _tube(g, 'Brumo_layered_leather_belt', [(1.04, .466, .323, .01), (1.20, .474, .333, .01)], p + 'leather', steps=12)
    for z in (1.075, 1.14, 1.195):
        _ring(g, 'Brumo_belt_seam_' + str(z), (0, .01, z), .475, .336, .009, p + 'seam', 'body')
    _diamond(g, 'Brumo_chest_insignia', (0, -.369, 1.69), .16, .205, gold, p + 'gold_hi')
    _diamond(g, 'Brumo_belt_insignia', (0, -.415, 1.115), .176, .181, gold, p + 'armor')
    for s in (-1, 1):
        g.line('Brumo_cross_chest_harness_' + str(s), [(s * .37, -.22, 1.965), (s * .27, -.336, 1.82),
               (s * .10, -.384, 1.62), (-s * .38, -.296, 1.43)], .027, gold, 'body')
        panel = _panel(g, 'Brumo_hip_lamella_' + str(s), (s * .33, -.222, 1.055), .205, .47, p + 'armor_hi', gold)
    _panel(g, 'Brumo_long_front_tabard', (0, -.38, 1.025), .19, .61, p + 'armor', gold)
    _panel(g, 'Brumo_back_tabard', (0, .325, 1.07), .23, .55, p + 'armor', gold, bow=-.035)
    return {'name': 'Brumo', 'kind': 'orc', 'family': 'biped', 'bones': _bones(True),
            'notes': ['Olive skin, amber eyes, broad smiling face, small ivory tusks, aubergine swept topknot, bronze-edged armor, leather and fur.',
                      'Distinct sculpted humanoid anatomy. Hidden garment backs and neutral stance are inferred from the single canonical portrait.']}


def _sprig(g, name, points, mat, part='body', size=.055):
    points = [(x, y - .05, z) for x, y, z in points]
    g.line(name + '_stem', points, .007, mat, part, resolution=5)
    for j in range(1, len(points)):
        x, y, z = points[j]
        s = -1 if j % 2 else 1
        _leaf(g, name + '_leaf_' + str(j), [(x, y - .006, z - .025),
              (x + s * size * .5, y - .012, z), (x + s * size, y - .009, z + .047),
              (x + s * size * 1.1, y, z + .055)], size * .36, .008, mat, part, 12)


def _aelira(g):
    p = 'ae_'
    _mats(g, p, {
        'skin': ('B87945', 0, .66), 'inner': ('8D4E2E', 0, .7), 'shadow': ('502917', 0, .76),
        'lip': ('AD643F', 0, .59), 'hair': ('173A2B', 0, .60), 'hair_hi': ('31543A', 0, .62),
        'forest': ('253F28', 0, .77), 'cloak': ('123D36', 0, .76), 'lining': ('205149', 0, .73),
        'cream': ('D2C2A1', 0, .83), 'cream_hi': ('E0D4B7', 0, .83),
        'leather': ('473022', 0, .72), 'gold': ('A98550', .60, .44), 'gold_hi': ('C7A574', .57, .4),
    })
    skin, gold = p + 'skin', p + 'gold'
    g.uv('Aelira_neck', (0, .01, 2.25), (.168, .166, .23), skin, 'body')
    _face(g, p, 2.875, skin, p + 'lip', '9654B3', False)
    _ears(g, p, 2.91, .94, skin, p + 'inner')
    for s in (-1, 1):
        _leaf(g, 'Aelira_brow_' + str(s), [(s * .115, -.496, 3.105), (s * .24, -.517, 3.15),
              (s * .36, -.47, 3.14), (s * .42, -.425, 3.10)], .032, .020, p + 'hair')
    _haircap(g, 'Aelira', (0, .025, 2.89), (.585, .48, .70), p + 'hair')
    _leaf(g, 'Aelira_natural_central_part', [(0, .0, 3.57), (0, -.26, 3.51),
          (.018, -.438, 3.36), (.012, -.459, 3.235)], .12, .044, p + 'hair')
    for s in (-1, 1):
        for j in range(5):
            k = j / 4
            _leaf(g, 'Aelira_parted_crown_' + str(s) + '_' + str(j),
                  [(s * .015, -.335 + .13 * k, 3.425 + .085 * k),
                   (s * .23, -.39 + .12 * k, 3.50), (s * .43, -.38 + .14 * k, 3.36),
                   (s * .53, -.20 + .19 * k, 3.12)], .102, .045, p + ('hair_hi' if j % 3 == 0 else 'hair'))
        # Loose cheek curls remain separate from the asymmetrical long braid.
        _leaf(g, 'Aelira_face_framing_curl_' + str(s), [(s * .39, -.36, 3.28), (s * .53, -.41, 2.99),
              (s * .48, -.47, 2.65), (s * .58, -.29, 2.43)], .090, .045, p + 'hair')
        _leaf(g, 'Aelira_lower_curl_' + str(s), [(s * .54, -.21, 2.61), (s * .60, -.30, 2.39),
              (s * .54, -.39, 2.22), (s * .45, -.43, 2.18)], .07, .035, p + 'hair')
    # Three actual interwoven volumetric strands drape over the left shoulder.
    braid_centers = [(0.38, .24, 3.40), (.55, .19, 3.17), (.57, .04, 2.84),
                     (.59, -.20, 2.49), (.63, -.43, 2.10), (.61, -.49, 1.83)]
    for strand in range(3):
        pts = []
        for i in range(121):
            t = i / 120 * (len(braid_centers) - 1)
            k = min(int(t), len(braid_centers) - 2)
            q = t - k
            c = Vector(braid_centers[k]).lerp(Vector(braid_centers[k + 1]), q)
            phase = TAU * (i / 120 * 6.3 + strand / 3)
            c.x += .094 * math.sin(phase)
            c.y += .058 * math.sin(2 * phase)
            pts.append(c)
        g.sweep('Aelira_interwoven_braid_' + str(strand), pts, [.060, .073, .065, .055],
                [.048, .060, .053, .043], p + ('hair_hi' if strand == 0 else 'hair'), 'head',
                normal=(0, -1, 0), steps=180, sides=20, flute=.07)
    _ring(g, 'Aelira_braid_gold_tie', (.61, -.49, 1.83), .11, .10, .025, gold, 'head')
    for j in range(5):
        _leaf(g, 'Aelira_braid_tassel_' + str(j), [(.61, -.49, 1.86), (.58 + j * .02, -.50, 1.75),
              (.54 + j * .037, -.50, 1.64), (.54 + j * .04, -.485, 1.60 + .035 * abs(j - 2))], .055, .027, p + 'hair')
    # Full back hair with flowing locks beneath the braided crown.
    for j in range(9):
        x = (j - 4) * .105
        _leaf(g, 'Aelira_back_hair_lock_' + str(j), [(x, .35, 3.31), (x * 1.1, .47, 3.02),
              (x * .97, .45, 2.62), (x * .9, .35, 2.37 + .05 * (j % 3))], .09, .046, p + ('hair_hi' if j % 3 == 0 else 'hair'))
    _tube(g, 'Aelira_cream_tunic', [(1.36, .32, .235, .03), (1.64, .32, .24, .02),
           (1.91, .435, .272, .015), (2.14, .39, .25, .035), (2.20, .20, .19, .025)], p + 'cream')
    _panel(g, 'Aelira_forest_v_neck_insert', (0, -.285, 2.15), .13, .54, p + 'forest', gold, bow=.008)
    for s in (-1, 1):
        side = 'L' if s > 0 else 'R'
        arm = 'arm.' + side
        shoulder = (s * .40, .02, 2.06)
        elbow = (s * .64, -.025, 1.78) if s < 0 else (s * .68, .015, 1.73)
        wrist = (s * .64, -.155, 1.32) if s < 0 else (s * .49, -.31, 1.50)
        g.sweep('Aelira_soft_cream_sleeve_' + side, [shoulder, elbow, wrist], [.173, .152, .107],
                [.18, .145, .10], p + 'cream_hi', arm, normal=(0, -1, 0), steps=44, sides=34, flute=.025)
        c0 = Vector(wrist).lerp(Vector(elbow), .02)
        c1 = Vector(wrist).lerp(Vector(elbow), .62)
        g.sweep('Aelira_leaf_vambrace_' + side, [c0, c0.lerp(c1, .5), c1], [.121, .149, .158],
                [.119, .145, .153], p + 'forest', arm, normal=(0, -1, 0), steps=28, sides=32, flute=.025)
        for q in (.04, .57):
            c = Vector(wrist).lerp(Vector(elbow), q)
            rad = .127 if q < .1 else .160
            _axis_ring(g, 'Aelira_bracer_gilt_' + side + str(q), c, Vector(elbow) - Vector(wrist), rad, rad * .98, .016, gold, arm)
        hand = (wrist[0], wrist[1] - .020, wrist[2] - .14)
        _hand(g, 'Aelira_hand_' + side, hand, skin, arm, small=True)
        _sprig(g, 'Aelira_sleeve_embroidery_' + side,
               [(s * .46, -.148, 2.03), (s * .53, -.166, 1.98), (s * .59, -.158, 1.89)], p + 'forest', arm, .049)
        leg = 'leg.' + side
        g.sweep('Aelira_forest_trouser_' + side, [(s * .235, .055, 1.20), (s * .24, .04, .88), (s * .255, -.005, .46)],
                [.212, .187, .136], [.219, .190, .137], p + 'forest', leg, normal=(0, -1, 0), steps=42, sides=34, flute=.035)
        bootparts = [g.uv('Aelira_boot_foot_' + side, (s * .255, -.128, .12), (.183, .326, .12), p + 'leather', leg),
                     g.uv('Aelira_boot_ankle_' + side, (s * .255, .01, .32), (.143, .16, .23), p + 'leather', leg)]
        g.fuse('Aelira_shaped_boot_' + side, bootparts, leg, voxel=.015, subdiv=1)
        g.uv('Aelira_boot_integrated_sole_' + side, (s * .255, -.128, .041), (.177, .315, .035), p + 'leather', leg, seg=44, rings=22)
        _ring(g, 'Aelira_boot_cuff_' + side, (s * .255, .01, .50), .161, .172, .028, p + 'cream', leg)
        _diamond(g, 'Aelira_boot_buckle_' + side, (s * .255, -.160, .35), .062, .08, gold, p + 'leather', leg)
        g.line('Aelira_boot_strap_' + side, [(s * .255 - .13, -.16, .245), (s * .255, -.228, .23),
               (s * .255 + .13, -.16, .245)], .026, p + 'leather', leg)
    _tube(g, 'Aelira_wide_leather_belt', [(1.45, .348, .257, .02), (1.62, .340, .25, .02)], p + 'leather', steps=12)
    for z in (1.475, 1.60):
        _ring(g, 'Aelira_belt_gilt_stitch_' + str(z), (0, .02, z), .348, .258, .009, gold, 'body')
    _diamond(g, 'Aelira_belt_leaf_clasp', (0, -.345, 1.535), .13, .168, gold, p + 'gold_hi')
    # Split cream skirt with long forest center tabard and leaf embroidery.
    for s in (-1, 1):
        _panel(g, 'Aelira_split_cream_skirt_' + str(s), (s * .25, -.242, 1.44), .215, .73,
               p + 'cream', gold, bow=.055)
        _sprig(g, 'Aelira_skirt_leaf_embroidery_' + str(s),
               [(s * .26, -.264, 1.18), (s * .29, -.257, 1.07), (s * .32, -.246, .98),
                (s * .36, -.235, .89)], p + 'forest', size=.058)
    _panel(g, 'Aelira_center_tabard', (0, -.297, 1.43), .114, .84, p + 'forest', gold, bow=.006)
    _sprig(g, 'Aelira_tabard_gold_sprig', [(0, -.285, .74), (0, -.29, .82), (0, -.297, .90), (0, -.301, .98)], gold, size=.049)
    # Back cape is an open-front, lined, thick shell with a scalloped hem.
    vs, fs = [], []
    rows, columns = 48, 88
    for i in range(rows + 1):
        t = i / rows
        z = 2.12 * (1 - t) + .30 * t
        rx = .435 + .49 * t ** .8
        ry = .275 + .235 * t
        for j in range(columns + 1):
            a = -.16 + (math.pi + .32) * j / columns
            wave = .022 * math.sin(8 * a) * t
            vs.append((rx * math.cos(a), .065 + (ry + wave) * math.sin(a), z + .045 * math.cos(6 * a) * t * t))
    for i in range(rows):
        for j in range(columns):
            a = i * (columns + 1) + j
            fs.append((a, a + columns + 1, a + columns + 2, a + 1))
    cape = _shell(g, 'Aelira_full_lined_forest_cape', vs, fs, p + 'cloak', 'body', .028, 1)
    for j in (0, columns):
        pts = [vs[i * (columns + 1) + j] for i in range(0, rows + 1, 3)]
        g.line('Aelira_cape_gold_selvedge_' + str(j), pts, .016, gold, 'body', resolution=3)
    hem = [vs[rows * (columns + 1) + j] for j in range(0, columns + 1, 2)]
    g.line('Aelira_cape_weighted_hem', hem, .020, p + 'lining', 'body', resolution=2)
    # Shoulder scarf folds join to the front star-shaped cloak fastening.
    for s in (-1, 1):
        g.sweep('Aelira_draped_cloak_shoulder_' + str(s), [(0, -.193, 2.19), (s * .29, -.18, 2.18),
                (s * .49, -.04, 2.13), (s * .53, .17, 1.985)],
                [.095, .125, .123, .022], [.05, .065, .058, .01], p + 'cloak', 'body', normal=(0, -1, 0), steps=42, sides=24, flute=.05)
        g.line('Aelira_cloak_shoulder_gold_seam_' + str(s), [(0, -.242, 2.13), (s * .27, -.234, 2.10),
               (s * .46, -.113, 2.055)], .015, gold, 'body')
    _diamond(g, 'Aelira_cloak_star_clasp', (0, -.340, 2.15), .10, .12, gold, p + 'gold_hi')
    return {'name': 'Aelira', 'kind': 'elf', 'family': 'biped', 'bones': _bones(False),
            'notes': ['Warm complexion, violet eyes, pointed recessed ears, forest-green parted hair and three interwoven braid strands.',
                      'Cream embroidered split tunic, long green cape, leaf clasps and leather boots preserve the portrait identity.',
                      'Hidden rear hair and cape construction are inferred. Clothing and hair are fully volumetric meshes.']}


def _bones(orc):
    if orc:
        return [('body', (0, 0, 1.08), (0, 0, 2.03), None),
                ('neck', (0, 0, 2.03), (0, 0, 2.20), 'body'),
                ('head', (0, 0, 2.13), (0, 0, 3.35), 'neck'),
                ('arm.L', (.50, .035, 1.91), (.71, -.145, 1.17), 'body'),
                ('arm.R', (-.50, .035, 1.91), (-.71, -.145, 1.17), 'body'),
                ('leg.L', (.27, .045, 1.04), (.30, -.005, .20), 'body'),
                ('leg.R', (-.27, .045, 1.04), (-.30, -.005, .20), 'body')]
    return [('body', (0, 0, 1.30), (0, 0, 2.20), None),
            ('neck', (0, 0, 2.20), (0, 0, 2.36), 'body'),
            ('head', (0, 0, 2.31), (0, 0, 3.34), 'neck'),
            ('arm.L', (.40, .02, 2.06), (.49, -.31, 1.50), 'body'),
            ('arm.R', (-.40, .02, 2.06), (-.64, -.155, 1.32), 'body'),
            ('leg.L', (.235, .055, 1.20), (.255, -.005, .20), 'body'),
            ('leg.R', (-.235, .055, 1.20), (-.255, -.005, .20), 'body')]


def build(g, kind):
    if kind == 'orc':
        return _brumo(g)
    if kind == 'elf':
        return _aelira(g)
    raise ValueError('Humanoid builder supports only orc and elf')

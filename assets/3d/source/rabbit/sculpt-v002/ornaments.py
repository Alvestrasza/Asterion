"""Liora's rose-gold regalia, constructed from the approved rabbit portrait.

build(g) adds editable, closed hardware after the named anatomy has been built.
No source image is projected onto a surface. The coordinator owns rendering,
rigging, export and fresh-import checks. X is lateral, negative Y is forward.
"""
import math
from functools import lru_cache

import bmesh
from mathutils import Vector


def _materials(g):
    colors = {
        'lo_rose': ('AE755C', .55, .43),
        'lo_rose_light': ('D49C7C', .55, .41),
        'lo_rose_dark': ('704537', .52, .45),
        'lo_lavender': ('957BA8', .10, .48),
        'lo_lavender_light': ('B39BC7', .09, .46),
        'lo_lavender_dark': ('6E587F', .08, .49),
        'lo_crystal': ('7E8DCF', .18, .29),
        'lo_crystal_light': ('9EDCEE', .14, .27),
        'lo_crystal_dark': ('565694', .16, .31),
        'lo_crystal_lilac': ('C2B6E3', .14, .28),
    }
    for key, values in colors.items():
        g.M[key] = g.material(key, *values)


def _mesh(g, name, vertices, faces, material='lo_rose', part='body', smooth=True):
    obj = g.mesh('liora_v2_' + name, vertices, faces, material, part, smooth)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


def _basis(normal):
    n = Vector(normal).normalized()
    u = Vector((0, 0, 1)).cross(n).normalized()
    return u, n.cross(u).normalized(), n


def _contact(target, point, direction, clearance=0):
    """Contact one named anatomical surface, excluding fur and other ornaments."""
    p, n = Vector(point), Vector(direction).normalized()
    inverse = target.matrix_world.inverted()
    found, hit, local_n, _ = target.ray_cast(
        inverse @ (p+n*2), inverse.to_3x3() @ -n)
    if not found:
        found, hit, local_n, _ = target.closest_point_on_mesh(inverse @ p)
    if not found:
        raise ValueError('Liora ornament has no contact on ' + target.name)
    hit = target.matrix_world @ hit
    outward = (target.matrix_world.to_3x3() @ local_n).normalized()
    if outward.dot(n) < 0:
        outward = -outward
    return hit+outward*clearance, outward


def _inside_contact(target, origin, direction, clearance=0, distance=.9):
    """First outward skin hit from a known interior point; never a far limb."""
    origin, radial = Vector(origin), Vector(direction).normalized()
    inverse = target.matrix_world.inverted()
    found, hit, local_n, _ = target.ray_cast(
        inverse@origin, inverse.to_3x3()@radial, distance=distance)
    if not found:
        raise ValueError('Liora interior support ray misses its bounded skin region')
    hit = target.matrix_world@hit
    if (hit-origin).length > distance+.001:
        raise ValueError('Liora interior support ray exceeded the local region')
    normal = (target.matrix_world.to_3x3()@local_n).normalized()
    if normal.dot(radial) < 0:
        normal = -normal
    return hit+normal*clearance, normal


def _smooth_surface(raw, clearance=.022):
    @lru_cache(maxsize=None)
    def surface(u, v):
        d = .010
        p, direction = raw(u, v)
        left, right = raw(u-d, v)[0], raw(u+d, v)[0]
        lower, upper = raw(u, v-d)[0], raw(u, v+d)[0]
        normal = (right-left).cross(upper-lower).normalized()
        if normal.dot(direction) < 0:
            normal = -normal
        return (p*4+left+right+lower+upper)/8+normal*clearance, normal
    return surface


def _neck_weights(obj):
    body = obj.vertex_groups.new(name='body')
    neck = obj.vertex_groups.new(name='neck')
    for vertex in obj.data.vertices:
        z = (obj.matrix_world@vertex.co).z
        w = max(0, min(1, (z-1.62)/.48))
        w = w*w*(3-2*w)
        if w < 1:
            body.add([vertex.index], 1-w, 'REPLACE')
        if w > 0:
            neck.add([vertex.index], w, 'REPLACE')


def _ribbon(g, name, points, normals, width, part='body', closed=False, support=None):
    points, normals = list(map(Vector, points)), list(map(Vector, normals))
    profile = [(-.5, -.004), (-.5, .010), (-.37, .023),
               (.37, .023), (.5, .010), (.5, -.004)]
    vertices, faces, count = [], [], len(points)
    for i, point in enumerate(points):
        before = points[(i-1) % count] if closed else points[max(0, i-1)]
        after = points[(i+1) % count] if closed else points[min(count-1, i+1)]
        tangent = (after-before).normalized()
        across = tangent.cross(normals[i]).normalized()
        normal = across.cross(tangent).normalized()
        for x, depth in profile:
            base, local_n = point+across*x*width, normal
            if support:
                base, local_n = support(base, i)
            vertices.append(base+local_n*depth)
    for i in range(count if closed else count-1):
        for j in range(6):
            k = (i+1) % count
            faces.append((i*6+j, k*6+j, k*6+(j+1) % 6, i*6+(j+1) % 6))
    if not closed:
        faces += [tuple(reversed(range(6))), tuple((count-1)*6+j for j in range(6))]
    obj = _mesh(g, name, vertices, faces, part=part)
    obj.data.materials.append(g.M['lo_rose_light'])
    obj.data.materials.append(g.M['lo_rose_dark'])
    for i, polygon in enumerate(obj.data.polygons):
        polygon.material_index = 1 if i % 6 in (1, 3) else (2 if i % 6 == 5 else 0)
    return obj


def _star(g, name, center, normal, radius, part='body', stretch=1, material='lo_rose'):
    """Four-point rose-gold spark, with crisp alternating triangular facets."""
    center = Vector(center)
    u, v, n = _basis(normal)
    outline = [(0, 1), (.24, .23), (1, 0), (.23, -.23),
               (0, -1), (-.23, -.24), (-1, 0), (-.24, .23)]
    vertices = [center+u*x*radius+v*z*radius*stretch for x, z in outline]
    vertices += [center+n*.029, center-n*.007]
    faces = []
    for i in range(8):
        faces += [(i, (i+1) % 8, 8), ((i+1) % 8, i, 9)]
    obj = _mesh(g, name, vertices, faces, material, part, False)
    obj.data.materials.append(g.M['lo_rose_light' if material == 'lo_rose' else 'lo_crystal_light'])
    for i, polygon in enumerate(obj.data.polygons):
        polygon.material_index = 1 if i % 4 == 0 else 0
    return obj


def _open_diamond(g, name, center, normal, outer, inner, support, part='head'):
    """Closed chamfered metal surrounding a genuinely open, skin-filled center."""
    center = Vector(center)
    u, v, n = _basis(normal)
    outer, inner = list(map(Vector, outer)), list(map(Vector, inner))
    perimeter = []
    for side in range(4):
        for sample in range(12):
            t = sample/12
            perimeter.append((inner[side].lerp(inner[(side+1) % 4], t),
                              outer[side].lerp(outer[(side+1) % 4], t)))
    profile = [(0, .008), (.13, .023), (.45, .029), (.86, .019), (1, .005)]
    count, vertices, faces = len(perimeter), [], []
    for front in (True, False):
        for fraction, height in profile:
            for a, b in perimeter:
                p = a.lerp(b, fraction)
                base, local_n = support(center+u*p.x+v*p.y)
                vertices.append(base+local_n*(height if front else -.002))
    layer = count*len(profile)
    for back in range(2):
        for ring in range(len(profile)-1):
            for i in range(count):
                a = back*layer+ring*count+i
                b = back*layer+ring*count+(i+1) % count
                faces.append((a, b, b+count, a+count))
    for ring in (0, len(profile)-1):
        for i in range(count):
            a, b = ring*count+i, ring*count+(i+1) % count
            faces.append((a, b, b+layer, a+layer))
    obj = _mesh(g, name, vertices, faces, part=part)
    obj.data.materials.append(g.M['lo_rose_light'])
    obj.data.materials.append(g.M['lo_rose_dark'])
    for polygon in obj.data.polygons:
        # The alternating long chamfers stay crisp without filling the opening.
        index = polygon.index
        polygon.material_index = 1 if index < count else (2 if index >= layer else 0)
    return obj


def _pendant_setting(g, name, center, normal, outline, support):
    c = Vector(center)
    u, v, n = _basis(normal)
    # The architectural outline remains angular in the front view, while its
    # back follows the breast profile. A flat plane floated away at the tip.
    perimeter = []
    for i, point in enumerate(outline):
        a, b = Vector(point), Vector(outline[(i+1) % len(outline)])
        for step in range(10):
            perimeter.append(a.lerp(b, step/10))

    def vertex(x, z, depth):
        base, outward = support(c+u*x+v*z)
        return base+outward*depth

    count, vertices, faces, colors = len(perimeter), [], [], []
    for scale, depth in [(1, -.012), (1, .014), (.91, .035), (.73, .035), (.66, .010)]:
        for x, z in perimeter:
            vertices.append(vertex(x*scale, z*scale, depth))
    for ring in range(4):
        for i in range(count):
            faces.append((ring*count+i, ring*count+(i+1) % count,
                          (ring+1)*count+(i+1) % count, (ring+1)*count+i))
            colors.append([2, 1, 0, 1][ring])
    faces += [tuple(reversed(range(count))), tuple(4*count+i for i in range(count))]
    colors += [2, 2]
    obj = _mesh(g, name+'_rose_bezel', vertices, faces)
    obj.data.materials.append(g.M['lo_rose_light'])
    obj.data.materials.append(g.M['lo_rose_dark'])
    for polygon, index in zip(obj.data.polygons, colors):
        polygon.material_index = index
    _neck_weights(obj)
    count, vertices, faces, colors = len(outline), [], [], []
    for scale, depth in [(.65, .014), (.46, .092)]:
        for x, z in outline:
            vertices.append(vertex(x*scale, z*scale, depth))
    vertices.append(vertex(-.022, .015, .103))
    for i in range(count):
        j = (i+1) % count
        faces += [(i, j, j+count, i+count), (i+count, j+count, 2*count)]
        colors += [[3, 2, 0, 1, 3, 0][i % 6], [1, 3, 0, 2, 1, 3][i % 6]]
    faces.append(tuple(reversed(range(count))))
    colors.append(2)
    obj = _mesh(g, name+'_lilac_crystal', vertices, faces, 'lo_crystal', smooth=False)
    for material in ('lo_crystal_light', 'lo_crystal_dark', 'lo_crystal_lilac'):
        obj.data.materials.append(g.M[material])
    for polygon, index in zip(obj.data.polygons, colors):
        polygon.material_index = index
    _neck_weights(obj)


def _panel(g, name, outline, center, surface):
    center = Vector(center)
    perimeter = []
    for edge, point in enumerate(outline):
        a, b = Vector(point), Vector(outline[(edge+1) % len(outline)])
        for i in range(16):
            perimeter.append(a.lerp(b, i/16))
    anchors = [(1, .004), (.98, .017), (.94, .028), (.79, .028),
               (.74, .010), (.68, .015), (.40, .020), (.16, .023)]
    rings, indices = [], []
    for interval, (a, b) in enumerate(zip(anchors, anchors[1:])):
        steps = 6 if interval == 2 else 3
        for j in range(steps):
            t = j/steps
            rings.append((a[0]*(1-t)+b[0]*t, a[1]*(1-t)+b[1]*t))
            indices.append([2, 1, 0, 1, 3, 3, 3][interval])
    rings.append(anchors[-1])
    count, vertices, faces, colors = len(perimeter), [], [], []
    for scale, height in rings:
        for point in perimeter:
            uv = center+(point-center)*scale
            p, n = surface(uv.x, uv.y)
            vertices.append(p+n*height)
    peak = len(vertices)
    p, n = surface(center.x, center.y)
    vertices.append(p+n*.024)
    for ring in range(len(rings)-1):
        for i in range(count):
            faces.append((ring*count+i, ring*count+(i+1) % count,
                          (ring+1)*count+(i+1) % count, (ring+1)*count+i))
            colors.append(indices[ring])
    for i in range(count):
        faces.append(((len(rings)-1)*count+i, (len(rings)-1)*count+(i+1) % count, peak))
        colors.append(3)
    back = len(vertices)
    for point in perimeter:
        p, n = surface(point.x, point.y)
        vertices.append(p-n*.010)
    back_center = len(vertices)
    p, n = surface(center.x, center.y)
    vertices.append(p-n*.010)
    for i in range(count):
        j = (i+1) % count
        faces += [(i, j, back+j, back+i), (back+j, back+i, back_center)]
        colors += [2, 2]
    obj = _mesh(g, name, vertices, faces)
    for key in ('lo_rose_light', 'lo_rose_dark', 'lo_lavender'):
        obj.data.materials.append(g.M[key])
    for polygon, index in zip(obj.data.polygons, colors):
        polygon.material_index = index
    _neck_weights(obj)


def _forehead(g, head):
    normal = Vector((0, -1, .05)).normalized()
    center = Vector((0, -1.42, 2.86))
    support = lambda p: _contact(head, p, normal, .005)
    _open_diamond(g, 'open_forehead_diamond', center, normal,
                  [(0, .232), (.151, -.003), (0, -.250), (-.151, -.003)],
                  [(0, .089), (.062, -.003), (0, -.094), (-.062, -.003)], support)
    p, n = _contact(head, (0, -1.20, 3.075), (0, -1, .12), .010)
    _star(g, 'forehead_upper_spark', p, n, .046, 'head', 1.55)
    for sign, side in ((1, 'L'), (-1, 'R')):
        p, n = _contact(head, (sign*.66, -1.22, 2.795),
                         (sign*.60, -.79, .07), .011)
        _star(g, 'delicate_temple_star_'+side, p, n, .076, 'head', 1.25)


def _armor(g, body):
    shoulder_outline = [(.40, 1.95), (.81, 1.87), (1.32, 1.75),
                        (1.73, 1.52), (1.47, 1.26), (1.12, 1.16),
                        (.81, 1.32), (.52, 1.28), (.37, 1.55)]
    # The cap starts on the ribcage, behind the neck. The previous y=-.34
    # vertical projection climbed the neck and created two tall copper fins.
    saddle_outline = [(.015, .065), (.42, .045), (.68, .23),
                      (.77, .60), (.65, 1.04), (.37, 1.25),
                      (.045, 1.34), (-.055, 1.10), (-.035, .63)]
    for sign, side in ((1, 'L'), (-1, 'R')):
        def shoulder_raw(angle, z):
            normal = Vector((sign*math.sin(angle), -math.cos(angle), 0))
            return _contact(body, Vector((0, -.35, z))+normal*.7, normal)

        def saddle_raw(y, angle):
            normal = Vector((sign*math.sin(angle), 0, math.cos(angle)))
            return _inside_contact(body, (0, y, 1.03), normal, distance=.98)

        shoulder, saddle = _smooth_surface(shoulder_raw), _smooth_surface(saddle_raw)
        _panel(g, 'fitted_lavender_shoulder_'+side, shoulder_outline, (1.0, 1.58), shoulder)
        _panel(g, 'curved_lavender_saddle_'+side, saddle_outline, (.32, .69), saddle)
        p, n = shoulder(1.02, 1.62)
        _star(g, 'shoulder_rose_spark_'+side, p+n*.036, n, .081)
        p, n = shoulder(1.39, 1.67)
        _star(g, 'shoulder_lilac_spark_'+side, p+n*.031, n, .065,
              material='lo_lavender_light')
        p, n = _contact(body, (sign*.93, .59, 1.36), (sign, 0, .06), .010)
        _star(g, 'haunch_rose_star_'+side, p, n, .089, 'leg.H'+side, 1.12)
    points, normals = [], []
    count = 144
    for i in range(count):
        angle = math.tau*i/count
        n = Vector((math.sin(angle), 0, math.cos(angle)))
        p, normal = _inside_contact(body, (0, .055, 1.03), n, .010, .9)
        points.append(p)
        normals.append(normal)

    def girth_support(probe, index):
        angle = math.tau*index/count
        radial = Vector((math.sin(angle), 0, math.cos(angle)))
        return _inside_contact(body, (0, probe.y, 1.03), radial, .010, .9)

    _ribbon(g, 'rose_body_girth', points, normals, .076, closed=True, support=girth_support)


def _breast(g, body):
    n = Vector((0, -.985, -.173)).normalized()
    center, _ = _contact(body, (0, -1.10, 1.16), n, .012)
    u, v, n = _basis(n)

    def setting_support(probe):
        # Clean support keeps the large facets and chamfers free from fur noise.
        # Use a common forward axis for relief rather than copying face normals.
        point, _ = _contact(body, probe, (0, -1, 0), .013)
        return point, Vector((0, -1, 0))

    _pendant_setting(g, 'long_breast_pendant', center, n,
                     [(0, .354), (.223, .163), (.226, -.175),
                      (0, -.404), (-.226, -.175), (-.223, .163)], setting_support)
    connector = center+v*.505+n*.007
    _pendant_setting(g, 'upper_diamond_connector', connector, n,
                     [(0, .177), (.132, 0), (0, -.177), (-.132, 0)], setting_support)
    anchors = []
    for probe in (connector+u*.119, connector-u*.119):
        point, outward = setting_support(probe)
        anchors.append(point+outward*.020)
    points, normals, directions, blends = [], [], [], []
    steps = 152
    for i in range(steps+1):
        t = i/steps
        angle = .45+(math.tau-.9)*t
        z = anchors[0].z+.34*math.sin(math.pi*t)**.80
        center_y = -.54-.15*max(0, min(1, (z-1.50)/.5))
        radial = Vector((math.sin(angle), -math.cos(angle), 0))
        p, normal = _contact(body, Vector((0, center_y, z))+radial*.6, radial, .013)
        blend = min(1, min(t, 1-t)/.075)
        blend = blend*blend*(3-2*blend)
        endpoint = anchors[0] if t < .5 else anchors[1]
        points.append(endpoint.lerp(p, blend))
        normals.append(n.lerp(normal, blend).normalized())
        directions.append(radial)
        blends.append(blend)

    def support(probe, index):
        p, normal = _contact(body, probe, directions[index], .013)
        return probe.lerp(p, blends[index]), normals[index].lerp(normal, blends[index]).normalized()

    collar = _ribbon(g, 'continuous_rose_neck_harness', points, normals, .071, support=support)
    _neck_weights(collar)


def _cuffs(g, body):
    inverse = body.matrix_world.inverted()
    for sign, side in ((1, 'L'), (-1, 'R')):
        x, part = sign*.405, 'leg.F'+side

        def support_at(angle, z, clearance=.007):
            center_y = -.72+.07*max(0, min(1, (z-.39)/.36))
            radial = Vector((math.cos(angle), math.sin(angle), 0))
            origin = Vector((x, center_y, z))
            found, hit, normal, _ = body.ray_cast(
                inverse@origin, inverse.to_3x3()@radial, distance=.41)
            if not found:
                raise ValueError('Liora cuff has no local foreleg contact: '+side)
            hit = body.matrix_world@hit
            normal = (body.matrix_world.to_3x3()@normal).normalized()
            if normal.dot(radial) < 0:
                normal = -normal
            return hit+normal*clearance, normal

        for ring, z in enumerate((.390, .477)):
            points, normals = [], []
            for i in range(112):
                a = math.tau*i/112
                front_distance = abs((a+math.pi/2+math.pi) % math.tau-math.pi)
                rise = .041*max(0, 1-front_distance/.87)
                p, normal = support_at(a, z+rise)
                points.append(p)
                normals.append(normal)

            def support(probe, index):
                return support_at(math.tau*index/112, probe.z)

            _ribbon(g, 'double_angular_fore_cuff_'+side+'_'+str(ring),
                    points, normals, .046, part, closed=True, support=support)
        center, normal = support_at(-math.pi/2, .513, .008)

        def diamond_support(probe):
            center_y = -.72+.07*max(0, min(1, (probe.z-.39)/.36))
            angle = math.atan2(probe.y-center_y, probe.x-x)
            return support_at(angle, probe.z, .009)

        _open_diamond(g, 'open_fore_cuff_diamond_'+side, center, normal,
                      [(0, .150), (.110, .005), (0, -.127), (-.110, .005)],
                      [(0, .063), (.041, .005), (0, -.053), (-.041, .005)],
                      diamond_support, part)


def build(g):
    """Return only new regalia meshes; source anatomy and other pets are untouched."""
    anatomy = {obj.name: obj for obj in g.ASSET}
    body = anatomy.get('AST_liora_v2_body') or anatomy.get('liora_v2_body')
    head = anatomy.get('AST_liora_v2_head') or anatomy.get('liora_v2_head')
    if body is None or head is None:
        raise ValueError('Build Liora v002 body and head before the ornaments')
    clean_support = getattr(g, 'ORNAMENT_SUPPORT', {})
    if not all(key in clean_support for key in ('body', 'head')):
        raise ValueError('Liora ornaments require pre-fur body/head support copies')
    # The coordinator owns these hidden, non-exported support meshes and removes
    # them after this function. The visible anatomy and fur remain untouched.
    body, head = clean_support['body'], clean_support['head']
    start = len(g.ASSET)
    _materials(g)
    _forehead(g, head)
    _armor(g, body)
    _breast(g, body)
    _cuffs(g, body)
    return list(g.ASSET[start:])

"""Caelo's fitted celestial regalia, modeled from the approved pony portrait.

The editable ornaments are real closed volumes, not projected artwork. The
coordinator creates the anatomy before calling build(g), then owns rendering,
rigging, export and fresh-import acceptance. Coordinates: X lateral, -Y front.
"""
import math
from functools import lru_cache

import bmesh
from mathutils import Vector


def _materials(g):
    palette = {
        'co_gold': ('B77C35', .67, .36),
        'co_gold_light': ('E2AE60', .63, .33),
        'co_gold_dark': ('765024', .61, .41),
        'co_blue': ('536CB4', .16, .43),
        'co_blue_light': ('7C9BDA', .15, .40),
        'co_blue_dark': ('344B8C', .12, .45),
        'co_gem': ('367FCD', .20, .28),
        'co_gem_light': ('A8D9F8', .16, .26),
        'co_gem_dark': ('204C9E', .22, .30),
    }
    for key, values in palette.items():
        g.M[key] = g.material(key, *values)


def _mesh(g, name, vertices, faces, material='co_gold', part='body', smooth=True):
    obj = g.mesh('caelo_v2_' + name, vertices, faces, material, part, smooth)
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


def _contact(target, point, normal, clearance=0):
    """Ray-seat on one continuous sculpt, using closest point only at its edge."""
    p, n = Vector(point), Vector(normal).normalized()
    inverse = target.matrix_world.inverted()
    found, hit, local_n, _ = target.ray_cast(
        inverse @ (p + n * 3), inverse.to_3x3() @ -n)
    if not found:
        found, hit, local_n, _ = target.closest_point_on_mesh(inverse @ p)
    if not found:
        raise ValueError('Caelo ornament cannot contact ' + target.name)
    hit = target.matrix_world @ hit
    outward = (target.matrix_world.to_3x3() @ local_n).normalized()
    if outward.dot(n) < 0:
        outward = -outward
    return hit + outward * clearance, outward


def _sample_path(points, count=64):
    points = [Vector(p) for p in points]
    result = []
    for sample in range(count + 1):
        f = sample / count * (len(points) - 1)
        i = min(int(f), len(points) - 2)
        t = f - i
        a, b = points[max(0, i-1)], points[i]
        c, d = points[i+1], points[min(len(points)-1, i+2)]
        result.append(.5 * ((2*b) + (-a+c)*t +
                           (2*a-5*b+4*c-d)*t*t + (-a+3*b-3*c+d)*t*t*t))
    return result


def _ribbon(g, name, points, normals, width, part='body', closed=False, support=None):
    """A broad flat metal strap with actual chamfered edge cross-sections."""
    points = [Vector(p) for p in points]
    normals = [Vector(n).normalized() for n in normals]
    # Width is tangential to the support surface; height is true metal relief.
    profile = [(-.5, -.006), (-.5, .012), (-.38, .022),
               (.38, .022), (.5, .012), (.5, -.006)]
    vertices, faces = [], []
    count, sides = len(points), len(profile)
    for i, p in enumerate(points):
        previous = points[(i-1) % count] if closed else points[max(0, i-1)]
        following = points[(i+1) % count] if closed else points[min(count-1, i+1)]
        tangent = (following-previous).normalized()
        across = tangent.cross(normals[i]).normalized()
        normal = across.cross(tangent).normalized()
        for x, z in profile:
            base = p + across*x*width
            local_n = normal
            if support is not None:
                base, local_n = support(base, i)
            vertices.append(base + local_n*z)
    for i in range(count if closed else count-1):
        for j in range(sides):
            a = i*sides+j
            b = ((i+1) % count)*sides+j
            faces.append((a, b, ((i+1) % count)*sides+(j+1) % sides,
                          i*sides+(j+1) % sides))
    if not closed:
        faces += [tuple(reversed(range(sides))),
                  tuple((count-1)*sides+j for j in range(sides))]
    obj = _mesh(g, name, vertices, faces, part=part)
    obj.data.materials.append(g.M['co_gold_light'])
    obj.data.materials.append(g.M['co_gold_dark'])
    for i, polygon in enumerate(obj.data.polygons):
        edge = i % sides
        polygon.material_index = 1 if edge in (1, 3) else (2 if edge == 5 else 0)
    return obj


def _star(g, name, center, normal, radius, part='body'):
    """Five pointed, architectural facets matching the portrait's gold stars."""
    c = Vector(center)
    u, v, n = _basis(normal)
    outline = []
    for i in range(10):
        a = math.pi/2 + math.tau*i/10
        r = radius if i % 2 == 0 else radius*.43
        outline.append(u*(r*math.cos(a)) + v*(r*math.sin(a)))
    vertices = [c+p for p in outline]
    vertices += [c+p*.77+n*.019 for p in outline]
    vertices += [c+n*.053, c-n*.012]
    faces, colors = [], []
    for i in range(10):
        j = (i+1) % 10
        faces += [(i, j, j+10, i+10), (i+10, j+10, 20), (j, i, 21)]
        colors += [1 if i % 2 else 0, 1 if i % 3 else 2, 2]
    obj = _mesh(g, name, vertices, faces, part=part, smooth=False)
    obj.data.materials.append(g.M['co_gold_light'])
    obj.data.materials.append(g.M['co_gold_dark'])
    for polygon, color in zip(obj.data.polygons, colors):
        polygon.material_index = color
    return obj


def _gem_frame(g, name, center, normal, outline, part='body', gem=True):
    """Deep closed bevel frame, broad gold reveal and hand-faceted crystal."""
    c = Vector(center)
    u, v, n = _basis(normal)
    count = len(outline)
    vertices, faces, colors = [], [], []
    # Outer chamfer, broad flat architectural reveal, and inner bevel.
    for scale, depth in [(1, -.012), (1, .020), (.94, .037),
                         (.74, .037), (.68, .009)]:
        for x, z in outline:
            vertices.append(c + u*x*scale + v*z*scale + n*depth)
    for ring in range(4):
        for i in range(count):
            faces.append((ring*count+i, ring*count+(i+1) % count,
                          (ring+1)*count+(i+1) % count, (ring+1)*count+i))
            colors.append(2 if ring == 0 else (1 if ring in (1, 3) else 0))
    faces.append(tuple(reversed(range(count))))
    colors.append(2)
    if gem:
        faces.append(tuple(4*count+i for i in range(count)))
        colors.append(2)
    else:
        # The tiara's elongated drop is solid faceted gold, not an empty socket.
        peak = len(vertices)
        local_center = sum((Vector(p) for p in outline), Vector((0, 0))) / count
        vertices.append(c + u*local_center.x + v*local_center.y + n*.046)
        for i in range(count):
            faces.append((4*count+i, 4*count+(i+1) % count, peak))
            colors.append(1 if i % 2 else 0)
    frame = _mesh(g, name+'_gold_frame', vertices, faces, part=part, smooth=False)
    frame.data.materials.append(g.M['co_gold_light'])
    frame.data.materials.append(g.M['co_gold_dark'])
    for polygon, color in zip(frame.data.polygons, colors):
        polygon.material_index = color
    if gem:
        vertices, faces, colors = [], [], []
        for scale, depth in [(.675, .013), (.52, .081)]:
            for x, z in outline:
                vertices.append(c + u*x*scale + v*z*scale + n*depth)
        vertices.append(c + u*(-.022) + v*.014 + n*.089)
        for i in range(count):
            j = (i+1) % count
            faces += [(i, j, j+count, i+count), (i+count, j+count, count*2)]
            colors += [1 if i in (0, count-1) else (2 if i % 3 == 1 else 0),
                       [0, 1, 0, 2, 0, 1][i % 6]]
        faces.append(tuple(reversed(range(count))))
        colors.append(2)
        crystal = _mesh(g, name+'_faceted_crystal', vertices, faces,
                        'co_gem', part, False)
        crystal.data.materials.append(g.M['co_gem_light'])
        crystal.data.materials.append(g.M['co_gem_dark'])
        for polygon, color in zip(crystal.data.polygons, colors):
            polygon.material_index = color
    return frame


def _smooth_surface(raw, clearance):
    """Smooth support positions/normals before offsetting broad polished metal."""
    @lru_cache(maxsize=None)
    def surface(u, v):
        delta = .010
        center = raw(u, v)
        left, right = raw(u-delta, v), raw(u+delta, v)
        lower, upper = raw(u, v-delta), raw(u, v+delta)
        p = (center[0]*4 + left[0] + right[0] + lower[0] + upper[0])/8
        normal = (right[0]-left[0]).cross(upper[0]-lower[0]).normalized()
        if normal.dot(center[1]) < 0:
            normal = -normal
        return p+normal*clearance, normal
    return surface


def _panel(g, name, outline, center, surface, part='body'):
    """Convex curved blue armor with a broad continuous chamfered gold rim."""
    center = Vector(center)
    perimeter = []
    for i, point in enumerate(outline):
        a, b = Vector(point), Vector(outline[(i+1) % len(outline)])
        for step in range(18):
            perimeter.append(a.lerp(b, step/18))
    count = len(perimeter)
    vertices, faces, colors = [], [], []
    anchors = [(1, .004), (.989, .018), (.953, .031), (.81, .031),
               (.765, .017), (.72, .020), (.52, .028), (.25, .033)]
    rings, ring_colors = [], []
    for interval, (a, b) in enumerate(zip(anchors, anchors[1:])):
        # Both the contour and the broad rim need a dense surface grid. Large
        # twisted quads spanning the rim produced rippled gold highlights.
        divisions = 7 if interval == 2 else (5 if interval > 4 else 3)
        for step in range(divisions):
            t = step/divisions
            rings.append((a[0]*(1-t)+b[0]*t, a[1]*(1-t)+b[1]*t))
            ring_colors.append([2, 1, 0, 1, 3, 3, 3][interval])
    rings.append(anchors[-1])
    for scale, relief in rings:
        for point in perimeter:
            uv = center + (point-center)*scale
            p, n = surface(uv.x, uv.y)
            vertices.append(p+n*relief)
    p, n = surface(center.x, center.y)
    tip = len(vertices)
    vertices.append(p+n*.035)
    for ring in range(len(rings)-1):
        for i in range(count):
            faces.append((ring*count+i, ring*count+(i+1) % count,
                          (ring+1)*count+(i+1) % count, (ring+1)*count+i))
            colors.append(ring_colors[ring])
    for i in range(count):
        faces.append(((len(rings)-1)*count+i,
                      (len(rings)-1)*count+(i+1) % count, tip))
        colors.append(3)
    # Back follows the same support rather than bridging it with a flat cap.
    back_start = len(vertices)
    for point in perimeter:
        p, n = surface(point.x, point.y)
        vertices.append(p-n*.013)
    back_center = len(vertices)
    p, n = surface(center.x, center.y)
    vertices.append(p-n*.013)
    for i in range(count):
        j = (i+1) % count
        faces += [(i, j, back_start+j, back_start+i),
                  (back_start+j, back_start+i, back_center)]
        colors += [2, 2]
    obj = _mesh(g, name, vertices, faces, part=part)
    for material in ('co_gold_light', 'co_gold_dark', 'co_blue'):
        obj.data.materials.append(g.M[material])
    for polygon, color in zip(obj.data.polygons, colors):
        polygon.material_index = color
    return obj


def _tiara(g, head):
    path = _sample_path([(-.49, -1.43, 3.745), (-.36, -1.60, 3.765),
                         (-.18, -1.74, 3.73), (0, -1.80, 3.685),
                         (.18, -1.74, 3.73), (.36, -1.60, 3.765),
                         (.49, -1.43, 3.745)], 76)
    seated = [_contact(head, point, (0, -1, .02), .008) for point in path]
    _ribbon(g, 'broad_chamfered_tiara', [p for p, _ in seated],
            [n for _, n in seated], .066, 'head')
    center, normal = _contact(head, (0, -1.82, 3.685), (0, -1, .06), .029)
    _gem_frame(g, 'tiara_diamond_drop', center, normal,
               [(0, .045), (.065, -.074), (0, -.211), (-.065, -.074)],
               'head', gem=False)
    _star(g, 'tiara_central_star', center+normal*.020, normal, .142, 'head')
    for sign, side in ((1, 'L'), (-1, 'R')):
        path = _sample_path([(sign*.49, -1.43, 3.745),
                             (sign*.55, -1.24, 3.76),
                             (sign*.54, -1.03, 3.73),
                             (sign*.46, -.87, 3.72)], 36)
        seated = [_contact(head, p, (sign*.88, -.12, .3), .008) for p in path]
        _ribbon(g, 'tiara_temple_band_'+side, [p for p, _ in seated],
                [n for _, n in seated], .060, 'head')
        point, normal = _contact(head, (sign*.55, -1.13, 3.70),
                                 (sign*.90, 0, .22), .028)
        _star(g, 'tiara_temple_star_'+side, point, normal, .105, 'head')


def _armor(g, torso):
    shoulder_outline = [(.37, 2.29), (.72, 2.24), (1.21, 2.13),
                        (1.63, 1.97), (1.60, 1.86), (1.10, 1.69),
                        (.66, 1.84), (.39, 2.05)]
    saddle_outline = [(-.04, .035), (.67, .035), (.96, .28),
                      (1.04, .70), (.93, 1.25), (.74, 1.46),
                      (.36, 1.47), (.10, 1.30), (-.025, .89)]
    for sign, side in ((1, 'L'), (-1, 'R')):
        def shoulder_raw(angle, z):
            normal = Vector((sign*math.sin(angle), -math.cos(angle), 0))
            point = Vector((0, -.48, z)) + normal*.65
            return _contact(torso, point, normal)

        def saddle_raw(y, angle):
            normal = Vector((sign*math.sin(angle), 0, math.cos(angle)))
            point = Vector((0, y, 1.55)) + normal*.60
            return _contact(torso, point, normal)

        shoulder = _smooth_surface(shoulder_raw, .030)
        saddle = _smooth_surface(saddle_raw, .024)

        _panel(g, 'polygonal_shoulder_shield_'+side, shoulder_outline,
               (.98, 2.00), shoulder)
        _panel(g, 'curved_blue_saddle_'+side, saddle_outline, (.48, .73), saddle)
        p, n = shoulder(.98, 2.035)
        _star(g, 'shoulder_gold_star_'+side, p+n*.050, n, .117)
        p, n = saddle(.59, .96)
        _star(g, 'saddle_main_star_'+side, p+n*.050, n, .148)
        p, n = saddle(.87, 1.28)
        _star(g, 'saddle_border_star_'+side, p+n*.043, n, .105)
    # A true girth joins the saddle and breast harness around the lower torso.
    points, normals = [], []
    for i in range(108):
        a = math.tau*i/108
        normal = Vector((math.sin(a), 0, math.cos(a)))
        p, n = _contact(torso, Vector((0, .20, 1.55))+normal*.60, normal, .012)
        points.append(p)
        normals.append(n)
    _ribbon(g, 'broad_saddle_girth', points, normals, .090, closed=True)


def _breast_jewel(g, torso):
    normal = Vector((0, -.928, -.371)).normalized()
    center, _ = _contact(torso, (0, -1.31, 1.94), normal, .055)
    outline = [(0, .335), (.266, .178), (.258, -.173),
               (0, -.350), (-.258, -.173), (-.266, .178)]
    _gem_frame(g, 'shield_breast_jewel', center, normal, outline)
    u, v, n = _basis(normal)
    _star(g, 'breast_frame_upper_star', center+v*.350+n*.053, n, .132)
    # One uninterrupted harness runs from one upper frame corner, around the
    # actual neck, into the other corner. There are no separate cut-off links.
    anchors = [center+u*.251+v*.187+n*.004,
               center-u*.251+v*.187+n*.004]
    points, normals, directions, blends = [], [], [], []
    count = 168
    for i in range(count+1):
        t = i/count
        angle = .72 + (math.tau-1.44)*t
        z = anchors[0].z + .46*math.sin(math.pi*t)**.80
        neck_y = -.68-.32*max(0, min(1, (z-2.01)/.52))
        radial = Vector((math.sin(angle), -math.cos(angle), 0))
        p, outward = _contact(torso, Vector((0, neck_y, z))+radial*.6,
                               radial, .014)
        endpoint = anchors[0] if t < .5 else anchors[1]
        blend = min(1, min(t, 1-t)/.085)
        blend = blend*blend*(3-2*blend)
        # The first few millimetres are a physical bridge into the raised bezel;
        # the rest is fully seated, including both edges of the broad strap.
        p = endpoint.lerp(p, blend)
        outward = n.lerp(outward, blend).normalized()
        points.append(p)
        normals.append(outward)
        directions.append(radial)
        blends.append(blend)

    def collar_support(probe, index):
        seated, local_n = _contact(torso, probe, directions[index], .014)
        blend = blends[index]
        return probe.lerp(seated, blend), normals[index].lerp(local_n, blend).normalized()

    collar = _ribbon(g, 'continuous_fitted_neck_harness', points, normals, .086,
                     support=collar_support)
    body_group = collar.vertex_groups.new(name='body')
    neck_group = collar.vertex_groups.new(name='neck')
    for vertex in collar.data.vertices:
        z = (collar.matrix_world@vertex.co).z
        weight = max(0, min(1, (z-1.92)/.66))
        weight = weight*weight*(3-2*weight)
        if weight < 1:
            body_group.add([vertex.index], 1-weight, 'REPLACE')
        if weight > 0:
            neck_group.add([vertex.index], weight, 'REPLACE')


def _anklets(g, torso):
    inverse = torso.matrix_world.inverted()
    for pair, y in (('F', -.74), ('H', .66)):
        for sign, side in ((1, 'L'), (-1, 'R')):
            x, part = sign*.415, 'leg.'+pair+side

            def support_at(angle, z, clearance=.008):
                # Cast outwards from inside this particular lower leg. A long
                # outside-in ray could seat the medial band on the opposite leg.
                center_y = y + (.75*max(0, z-.36) if pair == 'H' else .06*max(0, z-.43))
                origin = Vector((x, center_y, z))
                radial = Vector((math.cos(angle), math.sin(angle), 0))
                found, hit, local_n, _ = torso.ray_cast(
                    inverse@origin, inverse.to_3x3()@radial, distance=.42)
                if not found:
                    raise ValueError('Caelo anklet misses its own lower leg: '+part)
                hit = torso.matrix_world@hit
                normal = (torso.matrix_world.to_3x3()@local_n).normalized()
                if normal.dot(radial) < 0:
                    normal = -normal
                return hit+normal*clearance, normal

            for ring, z in enumerate((.39, .49)):
                points, normals = [], []
                for i in range(112):
                    a = math.tau*i/112
                    p, normal = support_at(a, z)
                    points.append(p)
                    normals.append(normal)

                def band_support(probe, index):
                    return support_at(math.tau*index/112, probe.z)

                _ribbon(g, 'flat_double_anklet_'+pair+side+'_'+str(ring),
                        points, normals, .055, part, closed=True, support=band_support)
            point, normal = support_at(-math.pi/2, .475, .022)
            _gem_frame(g, 'anklet_diamond_'+pair+side, point, normal,
                       [(0, .185), (.127, .014), (0, -.162), (-.127, .014)], part)


def build(g):
    """Add fitted regalia after anatomy exists, returning only these new meshes."""
    anatomy = {obj.name: obj for obj in g.ASSET}
    torso = anatomy.get('AST_caelo_v2_torso')
    head = anatomy.get('AST_caelo_v2_head')
    if torso is None or head is None:
        raise ValueError('Caelo v002 ornaments require the continuous torso and head first')
    start = len(g.ASSET)
    _materials(g)
    _tiara(g, head)
    _armor(g, torso)
    _breast_jewel(g, torso)
    _anklets(g, torso)
    return list(g.ASSET[start:])

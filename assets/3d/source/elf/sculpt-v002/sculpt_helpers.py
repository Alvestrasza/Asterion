"""Local, editable humanoid v002 geometry; no reference-image projection.

Shared only by Brumo and Aelira. All surface colors are authored mathematical
fields. Eye sockets are cut before skin color attributes are created.
"""
from __future__ import annotations
import math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def remove(g, predicate):
    for obj in list(g.ASSET):
        if predicate(obj):
            g.ASSET.remove(obj)
            bpy.data.objects.remove(obj, do_unlink=True)


def tree(obj):
    return BVHTree.FromPolygons([obj.matrix_world @ v.co for v in obj.data.vertices],
                               [list(p.vertices) for p in obj.data.polygons])


def color_mesh(g, obj, key, hexcolor, variation=None):
    """A fully initialized POINT color field, also valid after GLB export."""
    original = obj.data.materials[0]
    if key not in g.M:
        mat = original.copy(); mat.name = key
        node = mat.node_tree.nodes.new('ShaderNodeVertexColor')
        node.layer_name = 'AST_eye_color'
        mat.node_tree.links.new(node.outputs['Color'], mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
        g.M[key] = mat
    obj.data.materials[0] = g.M[key]
    attr = obj.data.color_attributes.get('AST_eye_color') or obj.data.color_attributes.new(
        name='AST_eye_color', type='FLOAT_COLOR', domain='POINT')
    base = g.color(hexcolor)
    for vertex, item in zip(obj.data.vertices, attr.data):
        p = obj.matrix_world @ vertex.co
        item.color = variation(p, base) if variation else base


def ribbon(g, name, points, width, mat, part='body', normal=(0, -1, 0), steps=80):
    """Broad beveled strip with a closed back, not a cylindrical wire."""
    centers = g.spline(points, steps); normal = Vector(normal).normalized()
    profile = [(-.5, -.009), (-.5, .007), (-.34, .018), (.34, .018), (.5, .007), (.5, -.009)]
    verts, faces = [], []
    for i, center in enumerate(centers):
        tangent = (centers[min(i + 1, steps)] - centers[max(i - 1, 0)]).normalized()
        n = (normal - tangent * normal.dot(tangent)).normalized(); u = tangent.cross(n).normalized()
        for x, z in profile: verts.append(center + u * width * x + n * z)
    for i in range(steps):
        for j in range(6):
            a = i * 6 + j; b = i * 6 + (j + 1) % 6
            faces.append((a, a + 6, b + 6, b))
    faces.extend([tuple(reversed(range(6))), tuple(steps * 6 + j for j in range(6))])
    return g.mesh(name, verts, faces, mat, part)


def lock(g, name, points, width, depth, mat, part='head', normal=(0, -1, 0), steps=68, sides=48):
    """A tapered organic lock with many actual, shallow longitudinal channels."""
    centers = g.spline(points, steps); normal = Vector(normal).normalized()
    verts, faces = [], []
    for i, center in enumerate(centers):
        t = i / steps
        tangent = (centers[min(i + 1, steps)] - centers[max(i - 1, 0)]).normalized()
        n = (normal - tangent * normal.dot(tangent)).normalized(); u = tangent.cross(n).normalized()
        w = width * (.075 + .925 * math.sin(math.pi * min(1, t / .97)) ** .64) * (1 - t ** 4.5) + .0005
        d = depth * (.65 + .35 * math.sin(math.pi * t)) * (1 - t ** 3.8) + .0004
        for j in range(sides):
            a = math.tau * j / sides; q = math.cos(a)
            channel = .065 * math.cos(q * 9 * math.pi + .42 * math.sin(t * 5)) + .023 * math.cos(q * 19 * math.pi + t)
            verts.append(center + u * (w * q) + n * (d * math.sin(a) * (1 + channel)))
    for i in range(steps):
        for j in range(sides):
            a = i * sides + j; b = i * sides + (j + 1) % sides
            faces.append((a, a + sides, b + sides, b))
    faces.extend([tuple(reversed(range(sides))), tuple(steps * sides + j for j in range(sides))])
    obj = g.mesh(name, verts, faces, mat, part)
    base = g.M[mat].diffuse_color
    attr = obj.data.color_attributes.new(name='AST_eye_color', type='FLOAT_COLOR', domain='POINT')
    for i, item in enumerate(attr.data):
        t = (i // sides) / steps; a = math.tau * (i % sides) / sides
        k = .75 + .23 * math.sin(math.pi * t) + .07 * math.sin(a * 7 + t * 4)
        item.color = tuple(c * k for c in base[:3]) + (1,)
    key = mat + '_scored_color'
    if key not in g.M:
        material = g.M[mat].copy(); material.name = key
        node = material.node_tree.nodes.new('ShaderNodeVertexColor'); node.layer_name = 'AST_eye_color'
        material.node_tree.links.new(node.outputs['Color'], material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
        g.M[key] = material
    obj.data.materials[0] = g.M[key]
    return obj


def seated_line(g, name, target, points, radius, mat, part='head', offset=.004):
    bvh = tree(target); seated = []
    for x, y, z in g.spline(points, 60):
        p, n, _, _ = bvh.ray_cast(Vector((x, -4, z)), Vector((0, 1, 0)))
        if p is not None: seated.append(p + n * offset)
    if len(seated) < 2: raise ValueError(name + ' has no supporting surface')
    return g.line(name, seated, radius, mat, part, resolution=2)


def eye(g, name, head, side, center, width, height, skin, ink, upper, lower):
    """A modestly convex colored eye, an actual socket and seamless skin annulus."""
    sign = 1 if side == 'L' else -1
    n = Vector((sign * .24, -.97, .018)).normalized()
    u = Vector((0, 0, 1)).cross(n).normalized(); v = n.cross(u).normalized()
    bvh = tree(head); center = Vector(center)
    hit, _, _, _ = bvh.ray_cast(center + n * 2, -n)
    if hit is None: raise ValueError(name + ' eye landmark misses head')
    c = hit - n * .012
    def coord(a, t):
        x = width * .5 * math.cos(a) * t
        z = height * .5 * math.sin(a) * (.78 + .22 * abs(math.sin(a))) * t + sign * x * .10
        return x, z
    seg, rings = 144, 56
    outline = [c + u * x + v * z for x, z in (coord(math.tau * j / seg, 1.10) for j in range(seg))]
    cutverts = [p + n * .4 for p in outline] + [p - n * .32 for p in outline]
    cutfaces = [tuple(range(seg)), tuple(reversed(range(seg, seg * 2)))]
    cutfaces.extend((j, j + seg, (j + 1) % seg + seg, (j + 1) % seg) for j in range(seg))
    cutter = g.mesh(name + '_cutter', cutverts, cutfaces, skin, 'head')
    mod = head.modifiers.new('True fitted eye socket', 'BOOLEAN'); mod.operation = 'DIFFERENCE'; mod.solver = 'EXACT'; mod.object = cutter
    g.apply(head, mod); g.ASSET.remove(cutter); bpy.data.objects.remove(cutter, do_unlink=True)
    vs, fs = [], []
    for row in range(13):
        t = row / 12; scale = .99 + .16 * t
        for j in range(seg):
            x, z = coord(math.tau * j / seg, scale); p = c + u * x + v * z
            hit, _, _, _ = bvh.ray_cast(p + n * 2, -n)
            if hit is None: raise ValueError(name + ' orbital rim has no support')
            vs.append((p + n * .006).lerp(hit + n * .003, t * t * (3 - 2 * t)))
    for row in range(12):
        for j in range(seg):
            a = row * seg + j; b = row * seg + (j + 1) % seg; fs.append((a, a + seg, b + seg, b))
    g.mesh(name + '_orbital_skin', vs, fs, skin, 'head')
    verts, faces, colors = [], [], []
    upper, lower = g.color(upper), g.color(lower); sclera = g.color('F7E8CA'); black = g.color('090C13')
    def point(x, z, t): return c + u * x + v * z + n * (.006 + .033 * (1 - t * t))
    for row in range(rings + 1):
        t = max(.00001, row / rings)
        for j in range(seg):
            a = math.tau * j / seg; x, z = coord(a, t); verts.append(point(x, z, t))
            ir = math.sqrt((x / (width * .365)) ** 2 + ((z + height * .008) / (height * .425)) ** 2)
            pr = math.sqrt((x / (width * .176)) ** 2 + ((z - height * .066) / (height * .239)) ** 2)
            col = sclera
            if ir < 1:
                f = max(0, min(1, .33 - z / (height * .70)))
                grain = .95 + .034 * math.sin(a * 59 + ir * 8) + .021 * math.sin(a * 103 - ir * 11)
                if ir > .91: grain *= .45 + .55 * (1 - ir) / .09
                col = tuple((upper[k] * (1 - f) + lower[k] * f) * grain for k in range(3)) + (1,)
            if pr < 1: col = black
            colors.append(col)
    for row in range(rings):
        for j in range(seg):
            a = row * seg + j; b = row * seg + (j + 1) % seg; faces.append((a, a + seg, b + seg, b))
    material = g.material(name + '_living_iris', 'FFFFFF', 0, .32)
    material.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value = .14
    node = material.node_tree.nodes.new('ShaderNodeVertexColor'); node.layer_name = 'AST_eye_color'
    material.node_tree.links.new(node.outputs['Color'], material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    obj = g.mesh(name, verts, faces, material, 'head'); obj['eye_side'] = side
    attr = obj.data.color_attributes.new(name='AST_eye_color', type='FLOAT_COLOR', domain='POINT')
    for item, col in zip(attr.data, colors): item.color = col
    for top in (True, False):
        start, end = (0, math.pi) if top else (math.pi, math.tau)
        points = [point(*coord(start + (end - start) * j / 40, 1), 1) + n * .005 for j in range(41)]
        widths = [.003 + (.019 if top else .005) * math.sin(math.pi * j / 40) ** .65 for j in range(41)]
        g.sweep(name + ('_upper_lash' if top else '_lower_lid'), points, widths, [w * .55 for w in widths],
                ink if top else skin, 'head', normal=n, steps=80, sides=20)
    x = sign * width * .47
    g.sweep(name + '_lash_wing', [point(x, .022, 1), point(x + sign * .035, .045, 1), point(x + sign * .065, .081, 1)],
            [.013, .019, .0005], [.009, .010, .0004], ink, 'head', normal=n, steps=28, sides=20)
    for suffix, x, z, radius in [('catchlight', -width * .13, height * .22, width * .071), ('pinlight', width * .14, -height * .22, width * .023)]:
        t = math.sqrt((x / (width * .5)) ** 2 + (z / (height * .5)) ** 2)
        g.disk(name + '_' + suffix, point(x, z, t) + n * .005, u, v, n, radius, radius * 1.07, 'hv_white', 'head', bulge=.001, rings=8, seg=48)
    lidverts = []
    for p in verts:
        d = p - c; lidverts.append(c + u * d.dot(u) * 1.085 + v * d.dot(v) * 1.065 + n * (d.dot(n) + .020))
    lid = g.mesh(name + '_closed_lid', lidverts, faces, skin, 'lid.' + side); lid['ast_lid_pivot'] = list(c + n * .020)
    pts = [point(width * .44 * q, -height * .10 * (1 - q * q), abs(q)) + n * .026 for q in (-1, -.7, -.35, 0, .35, .7, 1)]
    lash = g.sweep(name + '_sleep_lash', pts, [.001, .006, .008, .006, .001], [.001, .003, .004, .003, .001],
                   ink, 'lid.' + side, normal=n, steps=48, sides=16)
    lash['ast_lid_pivot'] = list(c + n * .020)


def ear(g, name, sign, z, span, skin, inner):
    """Leaf-shaped closed ear with a real depressed concha and rolled helix."""
    root = Vector((sign * .51, -.005, z)); tip = Vector((sign * span, .035, z + .36))
    axis = (tip - root).normalized(); across = Vector((-sign * .24, 0, .97)).normalized()
    steps, cols = 68, 32; vs, fs = [], []
    def pos(t, q, back=False):
        center = root.lerp(tip, t); fade = math.sin(math.pi * t) ** .62
        width = (.19 if span > 1 else .158) * fade + .0002
        return center + across * (q * width) + Vector((0, (.048 if back else -.083 + .105 * (1 - q * q)) * fade, 0))
    for back in (False, True):
        for row in range(steps + 1):
            for col in range(cols + 1): vs.append(pos(row / steps, col / cols * 2 - 1, back))
    size = (steps + 1) * (cols + 1)
    for row in range(steps):
        for col in range(cols):
            a = row * (cols + 1) + col; b = a + cols + 1
            fs.extend([(a, a + 1, b + 1, b), (a + size, b + size, b + size + 1, a + size + 1)])
    boundary = list(range(cols + 1)) + [r * (cols + 1) + cols for r in range(1, steps + 1)]
    boundary += [steps * (cols + 1) + j for j in range(cols - 1, -1, -1)] + [r * (cols + 1) for r in range(steps - 1, 0, -1)]
    fs.extend((a, b, b + size, a + size) for a, b in zip(boundary, boundary[1:] + boundary[:1]))
    g.mesh(name, vs, fs, skin, 'head')
    vs, fs = [], []
    for row in range(61):
        t = .13 + .77 * row / 60
        for col in range(25):
            q = (col / 24 * 2 - 1) * .77 * math.sin(math.pi * row / 60) ** .22
            vs.append(pos(t, q) + Vector((0, -.018, 0)))
    for row in range(60):
        for col in range(24):
            a = row * 25 + col; fs.append((a, a + 1, a + 26, a + 25))
    obj = g.mesh(name + '_concha', vs, fs, inner, 'head')
    mod = obj.modifiers.new('Concha inset backing', 'SOLIDIFY'); mod.thickness = .007; g.apply(obj, mod)
    g.sweep(name + '_antihelix', [pos(.13, -.30), pos(.29, -.45), pos(.45, -.15), pos(.57, .24)],
            [.013, .031, .022, .002], [.013, .029, .020, .002], skin, 'head', normal=(0, -1, 0), steps=42, sides=22)


def detail_surface(g, obj, hexcolor, key, amplitude=.002, subdiv=False):
    if subdiv:
        mod = obj.modifiers.new('Tailoring tessellation', 'SUBSURF'); mod.levels = 1; g.apply(obj, mod)
    obj.data.update()
    normals = [vertex.normal.copy() for vertex in obj.data.vertices]
    for vertex, normal in zip(obj.data.vertices, normals):
        p = obj.matrix_world @ vertex.co
        low = math.sin(p.z * 19 + p.x * 5) * math.sin(p.y * 13 + p.x * 11)
        grain = math.sin(p.x * 89 + p.y * 41) * math.sin(p.z * 97 - p.x * 27)
        vertex.co += normal * (amplitude * (.80 * low + .20 * grain))
    color_mesh(g, obj, key, hexcolor, lambda p, b: tuple(c * (.91 + .055 * math.sin(p.x * 17 + p.z * 9) * math.sin(p.z * 23 + p.y * 7) + .025 * math.sin(p.x * 81 + p.y * 31 + p.z * 107)) for c in b[:3]) + (1,))



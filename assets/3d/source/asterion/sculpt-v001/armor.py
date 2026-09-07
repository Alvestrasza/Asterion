"""Reference-based, fully volumetric Asterion ceremonial armor.

Coordinates: +X is the character's left, -Y is forward, +Z is up.
Every returned object is a mesh and is tagged for the assembly rig.
"""

import math
import bpy
import bmesh
from mathutils import Vector


def _mesh(name, vertices, faces, materials, indices=None, smooth=True, part="body"):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(vertices, [], faces)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.clear()
    for material in materials:
        mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj["ast_part"] = part
    for index, polygon in enumerate(mesh.polygons):
        polygon.use_smooth = smooth
        if indices:
            polygon.material_index = indices[index]
    return obj


def _bevel(obj, width=0.018, segments=3):
    modifier = obj.modifiers.new("Soft hand-finished metal edges", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    modifier.angle_limit = 0.45
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)
    return obj


def _sample(points, subdivisions=10, cyclic=False):
    """Interpolating Catmull-Rom curve; exact authored silhouette landmarks."""
    source = [Vector(p) for p in points]
    result = []
    count = len(source)
    for index in range(count if cyclic else count - 1):
        p0 = source[(index - 1) % count] if cyclic else source[max(0, index - 1)]
        p1 = source[index]
        p2 = source[(index + 1) % count]
        p3 = source[(index + 2) % count] if cyclic else source[min(count - 1, index + 2)]
        for step in range(subdivisions):
            t = step / subdivisions
            result.append((2 * p1 + (-p0 + p2) * t +
                           (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                           (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t) * 0.5)
    if not cyclic:
        result.append(source[-1])
    return result


def _ribbon(name, points, width, height, normal, mats, part, cyclic=False,
            curved=True, taper=False):
    """Solid shaped strap, with dark walls and a faceted polished crown."""
    points = _sample(points, 7, cyclic) if curved else [Vector(p) for p in points]
    normal = Vector(normal).normalized()
    count = len(points)
    vertices = []
    profile = [(-0.50, -0.35), (0.50, -0.35), (0.50, 0.12),
               (0.34, 0.50), (-0.34, 0.50), (-0.50, 0.12)]
    for index, point in enumerate(points):
        before = points[(index - 1) % count] if cyclic else points[max(index - 1, 0)]
        after = points[(index + 1) % count] if cyclic else points[min(index + 1, count - 1)]
        tangent = (after - before).normalized()
        across = tangent.cross(normal).normalized()
        local_normal = across.cross(tangent).normalized()
        amount = 1.0
        if taper:
            amount = max(0.04, math.sin(math.pi * index / (count - 1)) ** 0.55)
        for u, v in profile:
            vertices.append(tuple(point + across * width * u * amount + local_normal * height * v))
    faces, indices = [], []
    for ring in range(count if cyclic else count - 1):
        nxt = (ring + 1) % count
        for edge in range(6):
            faces.append((ring * 6 + edge, nxt * 6 + edge,
                          nxt * 6 + (edge + 1) % 6, ring * 6 + (edge + 1) % 6))
            indices.append(2 if edge == 0 else (1 if edge in (2, 4) else 0))
    if not cyclic:
        faces.extend([tuple(reversed(range(6))), tuple((count - 1) * 6 + i for i in range(6))])
        indices.extend([2, 2])
    return _mesh(name, vertices, faces, mats, indices, True, part)


def _shoulder_surface(theta, z, sign, elevation=0.0):
    """A smooth convex shoulder shell; theta is measured from forward."""
    radius_x = 0.73 + 0.33 * math.exp(-((z - 1.92) / 0.75) ** 2)
    radius_y = 1.08
    point = Vector((sign * radius_x * math.sin(theta),
                    -0.57 - radius_y * math.cos(theta), z))
    derivative_x = -2 * (z - 1.92) / (0.75 ** 2) * (radius_x - 0.73)
    tangent_theta = Vector((sign * radius_x * math.cos(theta), radius_y * math.sin(theta), 0))
    tangent_z = Vector((sign * derivative_x * math.sin(theta), 0, 1))
    normal = tangent_theta.cross(tangent_z).normalized() * sign
    return point + normal * (elevation + 0.052), normal


def _plate(name, outline, center, normal, mats, part):
    """Closed, double-curved shield: broad gold bevel, ink reveal, blue inlay."""
    perimeter = _sample(outline, 8, True)
    # Preserve the emblematic lower V as a point instead of rounding its
    # silhouette into a shallow scallop at the tip.
    for segment in (5, 6):
        a, b = Vector(outline[segment]), Vector(outline[segment + 1])
        for step in range(8):
            perimeter[segment * 8 + step] = a.lerp(b, step / 8)
    center = Vector(center)
    sign = 1 if normal[0] > 0 else -1
    # Edge profile is explicitly modeled, so a gold perimeter follows the
    # sculpted panel instead of floating over it as a round outline.
    rings = [(1.0, -0.018), (1.006, 0.008), (0.973, 0.037),
             (0.814, 0.040), (0.786, 0.024), (0.762, 0.027),
             (0.745, 0.030), (0.729, 0.030)]
    rings.extend([(0.70 - i * 0.025, 0.030) for i in range(28)])
    vertices = []
    for radius, elevation in rings:
        for point in perimeter:
            uv = center + (point - center) * radius
            position, _ = _shoulder_surface(uv.x, uv.z, sign, elevation)
            vertices.append(tuple(position))
    central_point, _ = _shoulder_surface(center.x, center.z, sign, 0.030)
    vertices.append(tuple(central_point))
    central = len(vertices) - 1
    count = len(perimeter)
    faces, indices = [], []
    ring_mats = [2, 1, 0, 1, 2, 3, 3] + [4] * (len(rings) - 8)
    for ring in range(len(rings) - 1):
        for i in range(count):
            j = (i + 1) % count
            faces.append((ring * count + i, ring * count + j,
                          (ring + 1) * count + j, (ring + 1) * count + i))
            indices.append(ring_mats[ring])
    for i in range(count):
        faces.append(((len(rings) - 1) * count + i,
                      (len(rings) - 1) * count + (i + 1) % count, central))
        indices.append(4)
    back_index = len(vertices)
    back_point, _ = _shoulder_surface(center.x, center.z, sign, -0.038)
    vertices.append(tuple(back_point))
    for i in range(count):
        faces.append(((i + 1) % count, i, back_index))
        indices.append(4)
    return _mesh(name, vertices, faces, mats, indices, True, part)


def _mount_hip(obj, sign, baseline=None):
    """Conform small raised heraldry to the finished sculpt's real surface."""
    body = bpy.data.objects.get("AST_Sculpted_body")
    if body is None:
        return obj
    inverse = body.matrix_world.inverted()
    direction = inverse.to_3x3() @ Vector((-sign, 0, 0))
    vertices = obj.data.vertices
    original_points = [v.co.copy() for v in vertices]
    for index, vertex in enumerate(vertices):
        point = original_points[index]
        if baseline is None:
            group = index // 6 * 6
            reference_x = sum(original_points[j].x for j in range(group, min(group + 6, len(vertices)))) / min(6, len(vertices) - group)
        else:
            reference_x = sign * baseline
        origin = inverse @ Vector((sign * 3.0, point.y, point.z))
        hit, position, _, _ = body.ray_cast(origin, direction)
        if hit:
            position = body.matrix_world @ position
            vertex.co.x = position.x + sign * 0.048 + (point.x - reference_x)
    obj.data.update()
    return obj


def _polygon_extrusion(name, points, normal, thickness, material, part, bevel=0.008):
    normal = Vector(normal).normalized()
    points = [Vector(p) for p in points]
    count = len(points)
    verts = [tuple(p - normal * thickness * 0.5) for p in points]
    verts += [tuple(p + normal * thickness * 0.5) for p in points]
    faces = [tuple(reversed(range(count))), tuple(range(count, count * 2))]
    faces += [(i, (i + 1) % count, (i + 1) % count + count, i + count) for i in range(count)]
    obj = _mesh(name, verts, faces, [material], smooth=False, part=part)
    if bevel:
        _bevel(obj, bevel, 3)
    return obj


def _star(name, center, normal, width, height, mats, part):
    normal = Vector(normal).normalized()
    up = Vector((0, 0, 1))
    across = up.cross(normal).normalized()
    up = normal.cross(across).normalized()
    c = Vector(center)
    outline = [(0, 0.5), (0.12, 0.12), (0.5, 0), (0.12, -0.12),
               (0, -0.5), (-0.12, -0.12), (-0.5, 0), (-0.12, 0.12)]
    verts = [tuple(c + across * x * width + up * y * height) for x, y in outline]
    verts += [tuple(c + normal * 0.035), tuple(c - normal * 0.014)]
    faces, mi = [], []
    for i in range(8):
        faces.extend([(i, (i + 1) % 8, 8), ((i + 1) % 8, i, 9)])
        mi.extend([i % 2, 2])
    return _mesh(name, verts, faces, mats, mi, False, part)


def _gem(name, center, width, height, mats, part):
    """Six-sided crystal: table, crown, girdle, pavilion, no texture tricks."""
    c = Vector(center)
    shape = [(0.0, 0.52), (0.48, 0.24), (0.48, -0.24),
             (0.0, -0.54), (-0.48, -0.24), (-0.48, 0.24)]
    levels = [(1.0, 0.0), (1.0, -0.035), (0.64, -0.112)]
    verts = []
    for scale, forward in levels:
        for x, z in shape:
            verts.append(tuple(c + Vector((x * width * scale, forward, z * height * scale))))
    faces, indices = [], []
    for ring in range(2):
        for j in range(6):
            faces.append((ring * 6 + j, ring * 6 + (j + 1) % 6,
                          (ring + 1) * 6 + (j + 1) % 6, (ring + 1) * 6 + j))
            indices.append([1, 0, 2, 0, 1, 1][j] if ring else 2)
    faces.extend([tuple(range(12, 18)), tuple(reversed(range(6)))])
    indices.extend([0, 2])
    return _mesh(name, verts, faces, mats, indices, False, part)


def _chest(objects, m):
    part = "armor.chest"
    metal = [m["gold"], m["gold_light"], m["gold_dark"]]
    breast_outline = [(0, -1.505, 2.40), (0.345, -1.515, 2.17),
                      (0.405, -1.515, 1.77), (0.302, -1.505, 1.43),
                      (0, -1.44, 1.13), (-0.302, -1.505, 1.43),
                      (-0.405, -1.515, 1.77), (-0.345, -1.515, 2.17)]
    objects.append(_polygon_extrusion("AST_Fitted_Navy_Breast_Shield", breast_outline,
                                     (0, -1, 0), 0.070, m["armor"], part, 0.028))
    # The inky backing separates the luminous gem and broad gold setting.
    outline = [(0, -1.585, 2.235), (0.32, -1.555, 2.045),
               (0.32, -1.55, 1.675), (0, -1.60, 1.435),
               (-0.32, -1.555, 1.675), (-0.32, -1.555, 2.045)]
    objects.append(_polygon_extrusion("AST_Chest_Pendant_Backplate", outline,
                                     (0, -1, 0), 0.08, m["armor"], part, 0.018))
    frame = [(0, -1.67, 2.183), (0.283, -1.638, 2.018),
             (0.283, -1.638, 1.701), (0, -1.675, 1.498),
             (-0.283, -1.638, 1.701), (-0.283, -1.638, 2.018)]
    objects.append(_ribbon("AST_Chest_Raised_Hexagonal_Gold_Setting", frame,
                           0.085, 0.060, (0, -1, 0), metal, part, True, False))
    well = [(0, -1.692, 2.12), (0.229, -1.692, 1.988),
            (0.229, -1.692, 1.732), (0, -1.692, 1.573),
            (-0.229, -1.692, 1.732), (-0.229, -1.692, 1.988)]
    objects.append(_polygon_extrusion("AST_Chest_Gem_Shadow_Well", well,
                                     (0, -1, 0), 0.025, m["black"], part, 0.005))
    objects.append(_gem("AST_Chest_Faceted_Azure_Crystal", (0, -1.707, 1.854),
                        0.432, 0.502, [m["gem"], m["gem_light"], m["gem_dark"]], part))
    # Heraldic open diamond atop the pendant, with crossed tapering arms.
    diamond = [(0, -1.62, 2.508), (0.128, -1.655, 2.336),
               (0, -1.68, 2.184), (-0.128, -1.655, 2.336)]
    objects.append(_ribbon("AST_Chest_Crown_Diamond", diamond, 0.052, 0.038,
                           (0, -1, 0), metal, part, True, False))
    objects.append(_polygon_extrusion("AST_Chest_Crown_Diamond_Inset",
                                     [(0, -1.65, 2.407), (0.041, -1.666, 2.341),
                                      (0, -1.67, 2.284), (-0.041, -1.666, 2.341)],
                                     (0, -1, 0), 0.023, m["gold_light"], part, 0.004))
    for sign, label in [(1, "L"), (-1, "R")]:
        transform = lambda pts: [(sign * x, y, z) for x, y, z in pts]
        crown_arm = transform([(0.0, -1.645, 2.217), (0.162, -1.625, 2.339),
                               (0.319, -1.56, 2.271), (0.365, -1.514, 2.355)])
        objects.append(_ribbon("AST_Chest_Crown_Arm_" + label, crown_arm,
                               0.056, 0.042, (0, -1, 0), metal, part, curved=False))
        lower_flame = transform([(0.307, -1.57, 1.88), (0.381, -1.54, 1.653),
                                 (0.291, -1.584, 1.401), (0.181, -1.575, 1.232),
                                 (0.0, -1.49, 1.113)])
        objects.append(_ribbon("AST_Chest_Lower_Sculpted_Flame_" + label, lower_flame,
                               0.082, 0.052, (0, -1, 0), metal, part, curved=False))
        lower_inset = transform([(0.17, -1.64, 1.482), (0.129, -1.631, 1.362),
                                 (0, -1.615, 1.278)])
        objects.append(_ribbon("AST_Chest_Lower_Inset_Chevron_" + label, lower_inset,
                               0.040, 0.031, (0, -1, 0), metal, part, curved=False))
        connector = transform([(0.13, -1.635, 2.17), (0.327, -1.565, 2.295),
                               (0.445, -1.501, 2.552)])
        objects.append(_ribbon("AST_Chest_Neck_Connector_" + label, connector,
                               0.052, 0.045, (0, -1, 0), metal, part))


def _cuff(objects, m, sign, label, hind=False):
    limb = "hind" if hind else "fore"
    part = limb + "." + label
    x, y = sign * (0.68 if hind else 0.65), 1.05 if hind else -1.08
    rx, ry = (0.292, 0.325) if hind else (0.281, 0.318)
    metal = [m["gold"], m["gold_light"], m["gold_dark"]]
    count = 96
    vertices = []
    # A broad continuous V-wave cuff wraps each wrist. Its top and bottom
    # bevels are geometry, with a darker inner surface against the scales.
    levels = [(-0.065, 0.0), (-0.057, 0.017), (-0.040, 0.028),
              (0.043, 0.028), (0.061, 0.013), (0.061, -0.011),
              (-0.065, -0.012)]
    for height, outset in levels:
        for i in range(count):
            angle = i * 2 * math.pi / count
            center_z = 0.659 + 0.055 * abs(math.cos(angle)) - 0.029 * max(0, -math.sin(angle))
            vertices.append((x + (rx + outset) * math.cos(angle),
                             y + (ry + outset) * math.sin(angle), center_z + height))
    faces, indices = [], []
    for ring in range(len(levels)):
        for i in range(count):
            next_ring, nxt = (ring + 1) % len(levels), (i + 1) % count
            faces.append((ring * count + i, ring * count + nxt,
                          next_ring * count + nxt, next_ring * count + i))
            indices.append([2, 1, 0, 1, 2, 2, 2][ring])
    objects.append(_mesh("AST_" + limb.title() + "_Sculpted_Gold_Cuff_" + label,
                         vertices, faces, metal, indices, True, part))
    front_y = y - ry - 0.04
    diamond = [(x, front_y, 0.844), (x + 0.128, front_y, 0.681),
               (x, front_y - 0.025, 0.529), (x - 0.128, front_y, 0.681)]
    objects.append(_polygon_extrusion("AST_" + limb.title() + "_Cuff_Diamond_" + label,
                                     diamond, (0, -1, 0), 0.047, m["gold"], part, 0.014))
    inset = [(x, front_y - 0.029, 0.771), (x + 0.048, front_y - 0.036, 0.685),
             (x, front_y - 0.047, 0.591), (x - 0.048, front_y - 0.036, 0.685)]
    objects.append(_polygon_extrusion("AST_" + limb.title() + "_Cuff_Diamond_Ink_Inset_" + label,
                                     inset, (0, -1, 0), 0.014, m["armor"], part, 0.004))
    objects.append(_ribbon("AST_" + limb.title() + "_Cuff_Diamond_Light_Spine_" + label,
                           [(x, front_y - 0.052, 0.749), (x, front_y - 0.059, 0.629)],
                           0.018, 0.015, (0, -1, 0), metal, part, curved=False))
    # Raised swept outer spur echoes the horn language in the turnaround.
    spur = [(x + sign * (rx - 0.012), y - 0.115, 0.629),
            (x + sign * (rx + 0.035), y - 0.055, 0.867),
            (x + sign * (rx + 0.006), y + 0.048, 0.961),
            (x + sign * (rx - 0.010), y + 0.061, 0.751)]
    objects.append(_polygon_extrusion("AST_" + limb.title() + "_Cuff_Outer_Spur_" + label,
                                     spur, (sign, 0, 0), 0.051, m["gold"], part, 0.014))


def build_armor(materials):
    """Build and return reference-faithful armor meshes without altering scene settings."""
    m, objects = materials, []
    metal = [m["gold"], m["gold_light"], m["gold_dark"]]
    blue_inlay = bpy.data.materials.new("AST_Armor_Blue_Inlay")
    blue_inlay.use_nodes = True
    blue_inlay.diffuse_color = (0.011, 0.142, 0.479, 1.0)
    blue_shader = blue_inlay.node_tree.nodes.get("Principled BSDF")
    blue_shader.inputs["Base Color"].default_value = blue_inlay.diffuse_color
    blue_shader.inputs["Metallic"].default_value = 0.16
    blue_shader.inputs["Roughness"].default_value = 0.37
    panel_materials = [m["gold"], m["gold_light"], m["gold_dark"], blue_inlay, m["armor"]]
    for sign, label in [(1, "L"), (-1, "R")]:
        part = "armor.shoulder." + label
        transform = lambda pts: [(sign * x, y, z) for x, y, z in pts]
        # The outline is authored in angular/height coordinates and evaluated
        # on a single convex surface. This prevents radial fan-fold creases.
        outline = [(0.58, 0, 2.968), (0.89, 0, 2.79), (1.38, 0, 2.59),
                   (1.82, 0, 2.56), (1.78, 0, 2.37), (1.53, 0, 2.07),
                   (1.02, 0, 1.47), (0.64, 0, 1.84), (0.36, 0, 2.20),
                   (0.41, 0, 2.65)]
        center = (1.05, 0, 2.28)
        normal = (sign * 0.52, -0.84, 0.04)
        objects.append(_plate("AST_Curved_Ceremonial_Shoulder_Shield_" + label,
                              outline, center, normal, panel_materials, part))
        # A subtle blue chevron sits within the dark enamel; this should read
        # as authored ornament, not additional gold clutter.
        inset_uv = [(0.72, 0, 2.36), (0.81, 0, 2.16),
                    (1.025, 0, 1.80), (1.38, 0, 2.13)]
        inset = [tuple(_shoulder_surface(p.x, p.z, sign, 0.039)[0])
                 for p in _sample(inset_uv, 12)]
        objects.append(_ribbon("AST_Shoulder_Enamel_Blue_Chevron_" + label, inset,
                               0.018, 0.014, normal, [blue_inlay] * 3,
                               part, curved=False, taper=True))
        star_center, star_normal = _shoulder_surface(0.76, 2.35, sign, 0.034)
        objects.append(_star("AST_Shoulder_Four_Point_Gold_Star_" + label,
                              star_center, star_normal,
                              0.139, 0.165, metal, part))
        # Rear collar rim remains visible between the mane and shield.
        collar = transform([(0.395, -0.15, 2.988), (0.555, 0.03, 2.843),
                            (0.669, 0.156, 2.597), (0.846, 0.007, 2.452)])
        objects.append(_ribbon("AST_Back_Collar_Gold_Rim_" + label, collar,
                               0.076, 0.043, (sign * 0.9, 0.1, 0.3), metal, part))
        # The paired crescent motifs occupy the outside haunch in side/rear views.
        hip_normal = (sign, 0, 0)
        hip_arc = transform([(0.799, 0.633, 1.941), (0.87, 0.845, 2.172),
                             (0.884, 1.087, 2.244), (0.873, 1.327, 2.156),
                             (0.79, 1.485, 1.94)])
        objects.append(_mount_hip(_ribbon("AST_Haunch_Gold_Crescent_" + label, hip_arc,
                                         0.042, 0.020, hip_normal, metal, "body", taper=True), sign))
        lower_arc = [(x + sign * 0.006, y, z - 0.070) for x, y, z in hip_arc]
        objects.append(_mount_hip(_ribbon("AST_Haunch_Inner_Gold_Crescent_" + label, lower_arc,
                                         0.018, 0.014, hip_normal, metal, "body", taper=True), sign))
        objects.append(_mount_hip(_star("AST_Haunch_Four_Point_Star_" + label,
                                        (sign * 0.776, 0.943, 2.444), hip_normal,
                                        0.217, 0.205, metal, "body"), sign, 0.776))
        _cuff(objects, m, sign, label, False)
        _cuff(objects, m, sign, label, True)
    chest_start = len(objects)
    _chest(objects, m)
    for obj in objects[chest_start:]:
        for vertex in obj.data.vertices:
            vertex.co.z += 0.20
        obj.data.update()
    for obj in objects:
        obj["ast_reference"] = "User-approved four-view Asterion turnaround, 2026-09-05"
    return objects

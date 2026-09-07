"""Solid sculpted dragon ears based on Asterion's four-view turnaround."""

import math
import bpy
import bmesh
from mathutils import Vector


def _mesh(name, vertices, faces, materials, indices):
    data = bpy.data.meshes.new(name + "_Mesh")
    data.from_pydata(vertices, [], faces)
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    for material in materials:
        data.materials.append(material)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    for polygon, index in zip(data.polygons, indices):
        polygon.material_index = index
        polygon.use_smooth = True
    obj["ast_part"] = "head"
    obj["ast_reference"] = "User-provided four-view Asterion turnaround, 2026-09-05"
    return obj


def _frame(t, sign):
    """A gently curved leaf axis with an orthonormal front-facing frame."""
    a = Vector((sign * 0.715, -0.610, 4.035))
    b = Vector((sign * 1.120, -0.265, 4.030))
    c = Vector((sign * 1.315, -0.095, 4.305))
    d = Vector((sign * 1.468, 0.098, 4.565))
    center = (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * d
    tangent = (3 * (1 - t) ** 2 * (b - a) + 6 * (1 - t) * t * (c - b) + 3 * t * t * (d - c)).normalized()
    nominal_normal = Vector((sign * 0.50, -0.83, 0.20)).normalized()
    normal = (nominal_normal - tangent * nominal_normal.dot(tangent)).normalized()
    across = tangent.cross(normal).normalized() * sign
    # Positive U follows the downward/outward side on both ears.
    if across.z > 0:
        across = -across
    width = max(0.0008, 0.247 * max(0, math.sin(math.pi * t)) ** 0.90 + 0.104 * (1 - t) ** 3)
    return center, tangent, normal, across, width


def _surface(t, u, sign, front=True):
    center, _, normal, across, width = _frame(t, sign)
    amplitude = max(0.0, math.sin(math.pi * t)) ** 0.8
    # Cross-section: a recessed, gently dished center and a raised folded
    # perimeter. The back is a separate smoothly convex surface, not a plane.
    if front:
        depth = amplitude * (0.052 * abs(u) ** 6 - 0.063 * (1 - u * u))
        depth += amplitude * 0.029 * math.exp(-((abs(u) - 0.89) / 0.075) ** 2)
        depth += amplitude * 0.013 * math.exp(-((u + 0.52) / 0.09) ** 2)
    else:
        depth = -0.035 - amplitude * (0.087 * (1 - u * u) + 0.013)
    # A little asymmetric expansion of the lower half gives the dragon-leaf
    # silhouette its pointed bowl, rather than a symmetrical cat-ear triangle.
    lateral = width * u * (1.0 + 0.085 * max(u, 0) * math.sin(math.pi * t))
    return center + across * lateral + normal * depth, normal, width


def _shell(sign, side, mats):
    along, across = 100, 64
    vertices, faces, indices = [], [], []
    stride = across + 1
    layer_size = (along + 1) * stride
    for front in (True, False):
        for i in range(along + 1):
            t = i / along
            for j in range(across + 1):
                u = -1 + 2 * j / across
                point, _, _ = _surface(t, u, sign, front)
                vertices.append(tuple(point))
    for layer in range(2):
        base = layer * layer_size
        for i in range(along):
            for j in range(across):
                a = base + i * stride + j
                faces.append((a, a + stride, a + stride + 1, a + 1))
                u = abs(-1 + 2 * (j + 0.5) / across)
                if layer:
                    index = 0
                elif u > 0.94:
                    index = 0
                elif u > 0.82:
                    index = 2
                elif u < 0.61 and 0.10 < i / along < 0.93:
                    index = 1
                else:
                    index = 0
                indices.append(index)
    # Seal both longitudinal rims and both root/tip edges.
    for i in range(along):
        for j in (0, across):
            a, b = i * stride + j, (i + 1) * stride + j
            faces.append((a, b, b + layer_size, a + layer_size))
            indices.append(0)
    for i in (0, along):
        for j in range(across):
            a, b = i * stride + j, i * stride + j + 1
            faces.append((a, b, b + layer_size, a + layer_size))
            indices.append(0)
    return _mesh("AST_Dragon_Leaf_Ear_" + side, vertices, faces,
                 [mats["navy"], mats["armor"], mats.get("scale_dark", mats["scale"])], indices)


def _gold_sweep(sign, side, mats):
    """A wide, tapered, bevel-crowned gold blade fitted into the lower bowl."""
    along = 100
    profile = [(-0.50, -0.004), (-0.50, 0.003), (-0.34, 0.013),
               (0.34, 0.013), (0.50, 0.003), (0.50, -0.004)]
    vertices, faces, indices = [], [], []
    for i in range(along + 1):
        q = i / along
        t = 0.075 + 0.87 * q
        _, _, _, _, halfwidth = _frame(t, sign)
        strip_width = 0.066 * max(0.045, math.sin(math.pi * q)) ** 0.65
        # Wide at the base/middle, narrowing to a blade toward the ear tip.
        center_u = 0.71 - 0.09 * q
        for lateral, height in profile:
            u = center_u + strip_width / halfwidth * lateral
            point, normal, _ = _surface(t, u, sign)
            vertices.append(tuple(point + normal * (0.009 + height)))
    for i in range(along):
        for j in range(6):
            a, b = i * 6 + j, i * 6 + (j + 1) % 6
            faces.append((a, a + 6, b + 6, b))
            indices.append([2, 1, 0, 1, 2, 2][j])
    faces.append(tuple(reversed(range(6))))
    faces.append(tuple(along * 6 + j for j in range(6)))
    indices.extend([2, 2])
    return _mesh("AST_Dragon_Ear_Swept_Gold_Inlay_" + side, vertices, faces,
                 [mats["gold"], mats["gold_light"], mats["gold_dark"]], indices)


def build_ears(materials):
    """Return closed sculpted ear meshes and fitted goldwork for both sides."""
    objects = []
    for sign, side in ((1, "L"), (-1, "R")):
        objects.append(_shell(sign, side, materials))
        objects.append(_gold_sweep(sign, side, materials))
    return objects

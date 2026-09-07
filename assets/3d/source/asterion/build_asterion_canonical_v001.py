"""Build the canonical, source-faithful Asterion 3D master.

The single canonical 2D illustration is treated as immutable evidence.  The
visible side is reconstructed as a dense, UV-mapped, closed relief shell so
that no painted feature is reinterpreted or omitted.  Depth, the opposite
side, and motion are necessarily inferred because no other canonical views
exist yet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


ASSET_NAME = "asterion-canonical-highpoly-v001"
CANONICAL_SHA256 = "8F074029DAAEF3024753A54DDDADA288AAACD76631D7E7AE626FAC62250FE59F"
BBOX_SOURCE = (10, 5, 182, 203)
WORLD_HEIGHT = 2.80
BASE_Z = 0.055
FPS = 30


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-reference", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--grid-scale", type=int, default=4)
    parser.add_argument("--export-glb", action="store_true")
    parser.add_argument("--preview-resolution", type=int, default=1024)
    argv = []
    if "--" in __import__("sys").argv:
        argv = __import__("sys").argv[__import__("sys").argv.index("--") + 1 :]
    return parser.parse_args(argv)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def verify_reference(path: Path) -> None:
    actual = sha256(path)
    if actual != CANONICAL_SHA256:
        raise RuntimeError(
            f"Canonical reference digest mismatch: expected {CANONICAL_SHA256}, got {actual}"
        )


def clean_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.armatures,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.actions,
    ):
        for block in list(datablocks):
            datablocks.remove(block)


def image_arrays(path: Path) -> tuple[bpy.types.Image, np.ndarray, np.ndarray]:
    image = bpy.data.images.load(str(path), check_existing=False)
    image.name = "AST_CANONICAL_SOURCE"
    image.colorspace_settings.name = "sRGB"
    width, height = image.size
    rgba = np.asarray(image.pixels[:], dtype=np.float32).reshape(height, width, 4)
    # Blender exposes image rows bottom-first.  Production fields use ordinary
    # image coordinates (origin at top-left), matching the canonical PNG.
    rgba = np.flipud(rgba)
    return image, rgba[:, :, :3], rgba[:, :, 3] > 0.5


def chamfer_distance(mask: np.ndarray) -> np.ndarray:
    """Small exact-enough distance field at the 192x208 source resolution."""
    height, width = mask.shape
    inf = float(height + width + 10)
    result = np.where(mask, inf, 0.0).astype(np.float32)
    diagonal = math.sqrt(2.0)
    for y in range(height):
        for x in range(width):
            if not mask[y, x]:
                continue
            best = result[y, x]
            if y > 0:
                best = min(best, result[y - 1, x] + 1.0)
                if x > 0:
                    best = min(best, result[y - 1, x - 1] + diagonal)
                if x + 1 < width:
                    best = min(best, result[y - 1, x + 1] + diagonal)
            if x > 0:
                best = min(best, result[y, x - 1] + 1.0)
            result[y, x] = best
    for y in range(height - 1, -1, -1):
        for x in range(width - 1, -1, -1):
            if not mask[y, x]:
                continue
            best = result[y, x]
            if y + 1 < height:
                best = min(best, result[y + 1, x] + 1.0)
                if x > 0:
                    best = min(best, result[y + 1, x - 1] + diagonal)
                if x + 1 < width:
                    best = min(best, result[y + 1, x + 1] + diagonal)
            if x + 1 < width:
                best = min(best, result[y, x + 1] + 1.0)
            result[y, x] = best
    return result


def box_blur(values: np.ndarray, passes: int = 2) -> np.ndarray:
    result = values.astype(np.float32)
    for _ in range(passes):
        padded = np.pad(result, 1, mode="edge")
        result = sum(
            padded[dy : dy + values.shape[0], dx : dx + values.shape[1]]
            for dy in range(3)
            for dx in range(3)
        ) / 9.0
    return result


def semantic_depth(rgb: np.ndarray, mask: np.ndarray, distance: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    height, width = mask.shape
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    target = np.full((height, width), 0.055, dtype=np.float32)

    # Overlapping anatomical volumes.  These do not alter the canonical outline;
    # they only infer the unseen half-thickness of the closed 3D shell.
    volumes = (
        (50, 69, 43, 43, 0.335),   # skull and muzzle
        (61, 42, 60, 42, 0.205),   # crown / horn fan
        (76, 102, 34, 48, 0.255),  # neck and mane root
        (99, 132, 57, 45, 0.370),  # ribcage / armour
        (130, 139, 38, 42, 0.335), # haunch
        (153, 126, 28, 24, 0.185), # tail base
        (174, 143, 22, 19, 0.105), # tail tip
        (29, 166, 15, 43, 0.135),  # near foreleg
        (59, 168, 15, 41, 0.125),  # far foreleg
        (120, 168, 18, 40, 0.160), # near hindleg
        (147, 168, 16, 36, 0.135), # far hindleg
    )
    for cx, cy, rx, ry, depth in volumes:
        radius_sq = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
        field = 0.035 + (depth - 0.035) * np.exp(-1.55 * radius_sq)
        target = np.maximum(target, field.astype(np.float32))

    # Cross-sections taper continuously into every silhouette edge.
    edge_factor = np.clip(distance / 8.0, 0.0, 1.0) ** 0.58
    half_depth = 0.012 + (target - 0.012) * edge_factor

    # Paint-aware relief: metal trim, the gem, the luminous eye and pale mane
    # sit slightly proud of the underlying hide/cloth without repainting them.
    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    luminance = red * 0.2126 + green * 0.7152 + blue * 0.0722
    highpass = luminance - box_blur(luminance, passes=2)
    gold = (red > green * 1.13) & (green > blue * 1.45) & (red > 0.18)
    pale = (red > 0.42) & (green > 0.32) & (blue > 0.17)
    cyan = (blue > red * 1.35) & (green > red * 1.15) & (blue > 0.22)
    armour = (blue > red * 1.18) & (blue > green * 0.92) & (blue > 0.08)
    relief = highpass * 0.030
    relief += gold.astype(np.float32) * 0.016
    relief += pale.astype(np.float32) * 0.010
    relief += armour.astype(np.float32) * 0.006
    relief += cyan.astype(np.float32) * 0.018
    relief = np.clip(relief, -0.010, 0.036) * edge_factor * mask
    return half_depth * mask, relief.astype(np.float32)


def cell_to_node(values: np.ndarray, active: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    height, width = active.shape
    total = np.zeros((height + 1, width + 1), dtype=np.float32)
    count = np.zeros((height + 1, width + 1), dtype=np.float32)
    weighted = values * active
    for ys, xs in ((slice(0, height), slice(0, width)),
                   (slice(1, height + 1), slice(0, width)),
                   (slice(0, height), slice(1, width + 1)),
                   (slice(1, height + 1), slice(1, width + 1))):
        total[ys, xs] += weighted
        count[ys, xs] += active
    nodes = np.divide(total, count, out=np.zeros_like(total), where=count > 0)
    return nodes, count > 0


def world_mapping(grid_scale: int) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = BBOX_SOURCE
    pixel_size = WORLD_HEIGHT / float(y1 - y0)
    center_x = (x0 + x1) * 0.5
    return pixel_size, center_x, float(y1), BASE_Z


def pixel_to_world(px: float, py: float, grid_scale: int = 1) -> tuple[float, float]:
    pixel_size, center_x, bottom_y, base_z = world_mapping(grid_scale)
    return (px - center_x) * pixel_size, (bottom_y - py) * pixel_size + base_z


def build_dense_shell(
    collection: bpy.types.Collection,
    image: bpy.types.Image,
    rgb_source: np.ndarray,
    mask_source: np.ndarray,
    grid_scale: int,
) -> tuple[bpy.types.Object, dict[str, np.ndarray], dict[str, int]]:
    source_height, source_width = mask_source.shape
    distance_source = chamfer_distance(mask_source)
    half_depth_source, relief_source = semantic_depth(rgb_source, mask_source, distance_source)

    active = np.repeat(np.repeat(mask_source, grid_scale, axis=0), grid_scale, axis=1)
    half_depth_cells = np.repeat(np.repeat(half_depth_source, grid_scale, axis=0), grid_scale, axis=1)
    relief_cells = np.repeat(np.repeat(relief_source, grid_scale, axis=0), grid_scale, axis=1)
    grid_height, grid_width = active.shape
    depth_nodes, needed_nodes = cell_to_node(half_depth_cells, active)
    relief_nodes, _ = cell_to_node(relief_cells, active)

    node_y, node_x = np.nonzero(needed_nodes)
    node_count = len(node_x)
    node_index = np.full(needed_nodes.shape, -1, dtype=np.int32)
    node_index[node_y, node_x] = np.arange(node_count, dtype=np.int32)

    pixel_size, center_x, bottom_y, base_z = world_mapping(grid_scale)
    source_x = node_x.astype(np.float32) / grid_scale
    source_y = node_y.astype(np.float32) / grid_scale
    world_x = (source_x - center_x) * pixel_size
    world_z = (bottom_y - source_y) * pixel_size + base_z
    depth = depth_nodes[node_y, node_x]
    relief = relief_nodes[node_y, node_x]

    coordinates = np.empty((node_count * 2, 3), dtype=np.float32)
    coordinates[:node_count, 0] = world_x
    coordinates[:node_count, 1] = -(depth + relief)
    coordinates[:node_count, 2] = world_z
    coordinates[node_count:, 0] = world_x
    coordinates[node_count:, 1] = depth + relief * 0.42
    coordinates[node_count:, 2] = world_z

    cell_y, cell_x = np.nonzero(active)
    top_left = node_index[cell_y, cell_x]
    top_right = node_index[cell_y, cell_x + 1]
    bottom_left = node_index[cell_y + 1, cell_x]
    bottom_right = node_index[cell_y + 1, cell_x + 1]
    front_faces = np.column_stack((top_left, bottom_left, bottom_right, top_right))
    back_faces = np.column_stack((top_left + node_count, top_right + node_count,
                                  bottom_right + node_count, bottom_left + node_count))

    padded = np.pad(active, 1, constant_values=False)
    boundary_faces: list[np.ndarray] = []
    boundary_material_indices: list[np.ndarray] = []
    for direction, boundary, face_builder in (
        ("top", active & ~padded[:-2, 1:-1], lambda tl, tr, bl, br: np.column_stack((tl, tr, tr + node_count, tl + node_count))),
        ("bottom", active & ~padded[2:, 1:-1], lambda tl, tr, bl, br: np.column_stack((bl, bl + node_count, br + node_count, br))),
        ("left", active & ~padded[1:-1, :-2], lambda tl, tr, bl, br: np.column_stack((tl, tl + node_count, bl + node_count, bl))),
        ("right", active & ~padded[1:-1, 2:], lambda tl, tr, bl, br: np.column_stack((tr, br, br + node_count, tr + node_count))),
    ):
        by, bx = np.nonzero(boundary)
        tl = node_index[by, bx]
        tr = node_index[by, bx + 1]
        bl = node_index[by + 1, bx]
        br = node_index[by + 1, bx + 1]
        boundary_faces.append(face_builder(tl, tr, bl, br))
        source_by = np.clip(by // grid_scale, 0, source_height - 1)
        source_bx = np.clip(bx // grid_scale, 0, source_width - 1)
        colors = rgb_source[source_by, source_bx]
        red, green, blue = colors[:, 0], colors[:, 1], colors[:, 2]
        material_indices = np.ones(len(colors), dtype=np.int32)  # navy edge
        gold = (red > green * 1.13) & (green > blue * 1.22) & (red > 0.09)
        pale = (red > 0.28) & (green > 0.18) & (blue > 0.075) & (green > red * 0.60) & (blue > red * 0.25)
        blue_edge = (blue > red * 1.22) & (blue > green * 0.92) & (blue > 0.05)
        material_indices[gold] = 2
        material_indices[pale] = 3
        material_indices[blue_edge] = 4
        boundary_material_indices.append(material_indices)
    faces = np.concatenate((front_faces, back_faces, *boundary_faces), axis=0).astype(np.int32)

    mesh = bpy.data.meshes.new("AST_CANONICAL_DENSE_SHELL_MESH")
    mesh.vertices.add(len(coordinates))
    mesh.vertices.foreach_set("co", coordinates.ravel())
    loop_vertices = faces.ravel()
    mesh.loops.add(len(loop_vertices))
    mesh.loops.foreach_set("vertex_index", loop_vertices)
    mesh.polygons.add(len(faces))
    mesh.polygons.foreach_set("loop_start", np.arange(len(faces), dtype=np.int32) * 4)
    mesh.polygons.foreach_set("loop_total", np.full(len(faces), 4, dtype=np.int32))
    mesh.polygons.foreach_set("use_smooth", np.ones(len(faces), dtype=np.bool_))
    face_materials = np.zeros(len(faces), dtype=np.int32)
    boundary_start = len(front_faces) + len(back_faces)
    face_materials[boundary_start:] = np.concatenate(boundary_material_indices)
    mesh.polygons.foreach_set("material_index", face_materials)

    per_vertex_uv = np.empty((node_count * 2, 2), dtype=np.float32)
    uv = np.column_stack((node_x.astype(np.float32) / grid_width,
                          1.0 - node_y.astype(np.float32) / grid_height))
    per_vertex_uv[:node_count] = uv
    per_vertex_uv[node_count:] = uv
    uv_layer = mesh.uv_layers.new(name="AST_CANONICAL_UV")
    uv_layer.data.foreach_set("uv", per_vertex_uv[loop_vertices].ravel())
    mesh.update(calc_edges=True)
    mesh.validate(verbose=False, clean_customdata=False)

    obj = bpy.data.objects.new("AST_CANONICAL_DENSE_SHELL", mesh)
    collection.objects.link(obj)
    material = make_canonical_material(image)
    mesh.materials.append(material)
    for edge_material in make_edge_materials():
        mesh.materials.append(edge_material)
    obj["asset_role"] = "canonical_dense_closed_relief"
    obj["source_sha256"] = CANONICAL_SHA256
    obj["visible_side_fidelity"] = "UV projection from immutable canonical PNG"
    obj["inferred_dimensions"] = "depth and opposite side"
    obj["grid_scale"] = grid_scale

    fields = {
        "node_source_x": source_x,
        "node_source_y": source_y,
        "node_count": np.asarray([node_count], dtype=np.int32),
    }
    stats = {
        "source_width": source_width,
        "source_height": source_height,
        "grid_width": grid_width,
        "grid_height": grid_height,
        "active_cells": int(active.sum()),
        "shell_vertices": int(len(coordinates)),
        "shell_quads": int(len(faces)),
        "shell_triangles": int(len(faces) * 2),
        "boundary_quads": int(sum(len(item) for item in boundary_faces)),
    }
    return obj, fields, stats


def make_canonical_material(image: bpy.types.Image) -> bpy.types.Material:
    material = bpy.data.materials.new("AST_MAT_CANONICAL_PAINT")
    material.use_nodes = True
    material.diffuse_color = (0.06, 0.10, 0.24, 1.0)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    for node in list(nodes):
        nodes.remove(node)
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (560, 0)
    emission = nodes.new("ShaderNodeEmission")
    emission.location = (120, 90)
    emission.inputs["Strength"].default_value = 1.0
    diffuse = nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.location = (120, -100)
    diffuse.inputs["Roughness"].default_value = 0.72
    mix = nodes.new("ShaderNodeMixShader")
    mix.location = (360, 0)
    # The source is already fully painted.  Only a restrained diffuse share is
    # added to reveal the inferred curvature in oblique views.
    mix.inputs[0].default_value = 0.12
    texture = nodes.new("ShaderNodeTexImage")
    texture.location = (-260, 40)
    texture.image = image
    texture.interpolation = "Linear"
    texture.extension = "CLIP"
    links.new(texture.outputs["Color"], emission.inputs["Color"])
    links.new(texture.outputs["Color"], diffuse.inputs["Color"])
    links.new(emission.outputs["Emission"], mix.inputs[1])
    links.new(diffuse.outputs["BSDF"], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])
    material["canonical_texture_sha256"] = CANONICAL_SHA256
    return material


def make_exact_material(image: bpy.types.Image) -> bpy.types.Material:
    material = bpy.data.materials.new("AST_MAT_CANONICAL_EXACT_PROOF")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    for node in list(nodes):
        nodes.remove(node)
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (380, 0)
    emission = nodes.new("ShaderNodeEmission")
    emission.location = (120, 0)
    emission.inputs["Strength"].default_value = 1.0
    texture = nodes.new("ShaderNodeTexImage")
    texture.location = (-220, 0)
    texture.image = image
    texture.interpolation = "Closest"
    texture.extension = "CLIP"
    links.new(texture.outputs["Color"], emission.inputs["Color"])
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    material["asset_role"] = "canonical_registration_proof_only"
    material["canonical_texture_sha256"] = CANONICAL_SHA256
    return material


def add_bone(
    armature_data: bpy.types.Armature,
    name: str,
    pixel: tuple[float, float],
    parent: str | None,
    *,
    deform: bool = True,
) -> None:
    x, z = pixel_to_world(*pixel)
    bone = armature_data.edit_bones.new(name)
    bone.head = (x, -0.060, z)
    bone.tail = (x, 0.060, z)
    bone.use_deform = deform
    if parent:
        bone.parent = armature_data.edit_bones[parent]
        bone.use_connect = False


def create_rig(collection: bpy.types.Collection) -> bpy.types.Object:
    data = bpy.data.armatures.new("AST_CANONICAL_RIG_DATA")
    armature = bpy.data.objects.new("AST_CANONICAL_RIG", data)
    collection.objects.link(armature)
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    add_bone(data, "root", (101, 141), None, deform=False)
    add_bone(data, "body", (106, 132), "root")
    add_bone(data, "neck", (72, 108), "body")
    add_bone(data, "head", (49, 72), "neck")
    add_bone(data, "jaw", (38, 88), "head")
    add_bone(data, "foreleg.L", (31, 151), "body")
    add_bone(data, "forepaw.L", (29, 184), "foreleg.L")
    add_bone(data, "foreleg.R", (59, 151), "body")
    add_bone(data, "forepaw.R", (59, 185), "foreleg.R")
    add_bone(data, "hindleg.L", (119, 154), "body")
    add_bone(data, "hindpaw.L", (121, 185), "hindleg.L")
    add_bone(data, "hindleg.R", (146, 153), "body")
    add_bone(data, "hindpaw.R", (148, 183), "hindleg.R")
    add_bone(data, "tail.01", (143, 126), "body")
    add_bone(data, "tail.02", (160, 132), "tail.01")
    add_bone(data, "tail.03", (176, 145), "tail.02")
    add_bone(data, "lid.front", (42, 72), "head")
    add_bone(data, "lid.back", (42, 72), "head")
    bpy.ops.object.mode_set(mode="POSE")
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
    bpy.ops.object.mode_set(mode="OBJECT")
    armature.show_in_front = True
    armature["asset_role"] = "canonical_animation_rig"
    armature["rig_version"] = "canonical-v001"
    return armature


def sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -30.0, 30.0)))


def skinning_scores(px: np.ndarray, py: np.ndarray) -> tuple[list[str], np.ndarray]:
    names = [
        "body", "neck", "head", "jaw",
        "foreleg.L", "forepaw.L", "foreleg.R", "forepaw.R",
        "hindleg.L", "hindpaw.L", "hindleg.R", "hindpaw.R",
        "tail.01", "tail.02", "tail.03",
    ]
    scores: list[np.ndarray] = []
    scores.append(0.16 + 1.30 * np.exp(-(((px - 105) / 55) ** 2 + ((py - 132) / 45) ** 2)))
    scores.append(1.50 * np.exp(-(((px - 70) / 29) ** 2 + ((py - 111) / 34) ** 2)))
    scores.append(2.15 * np.exp(-(((px - 51) / 48) ** 2 + ((py - 63) / 49) ** 2)) * sigmoid((119 - py) / 6))
    jaw_gate = sigmoid((py - 78) / 3) * sigmoid((105 - py) / 4) * sigmoid((65 - px) / 4)
    scores.append(2.25 * jaw_gate)

    leg_gate = sigmoid((py - 137) / 4)
    for center in (30, 59, 120, 147):
        base = 2.45 * np.exp(-((px - center) / 12.0) ** 2) * leg_gate
        paw_gate = sigmoid((py - 178) / 3.5)
        scores.append(base * (1.0 - paw_gate * 0.92))
        scores.append(base * paw_gate * 1.40)

    tail_gate = sigmoid((px - 136) / 4) * sigmoid((py - 96) / 5) * sigmoid((159 - py) / 4)
    scores.append(2.10 * np.exp(-((px - 145) / 12) ** 2) * tail_gate)
    scores.append(2.35 * np.exp(-((px - 161) / 11) ** 2) * tail_gate)
    scores.append(2.55 * np.exp(-((px - 177) / 10) ** 2) * tail_gate)
    matrix = np.vstack(scores).T.astype(np.float32)

    # glTF skinning is deliberately bounded to four influences per vertex.
    if matrix.shape[1] > 4:
        keep = np.argpartition(matrix, -4, axis=1)[:, -4:]
        allowed = np.zeros_like(matrix, dtype=np.bool_)
        allowed[np.arange(len(matrix))[:, None], keep] = True
        matrix = np.where(allowed, matrix, 0.0)
    sums = matrix.sum(axis=1, keepdims=True)
    matrix = np.divide(matrix, sums, out=np.zeros_like(matrix), where=sums > 0)
    return names, matrix


def attach_skin(obj: bpy.types.Object, armature: bpy.types.Object, fields: dict[str, np.ndarray]) -> dict[str, int]:
    px = fields["node_source_x"]
    py = fields["node_source_y"]
    node_count = int(fields["node_count"][0])
    names, weights = skinning_scores(px, py)
    quantization_levels = 48
    assignments = 0
    for column, name in enumerate(names):
        group = obj.vertex_groups.new(name=name)
        quantized = np.rint(weights[:, column] * quantization_levels).astype(np.int16)
        for level in np.unique(quantized):
            if level <= 0:
                continue
            base_indices = np.nonzero(quantized == level)[0].astype(np.int32)
            indices = np.concatenate((base_indices, base_indices + node_count))
            group.add(indices.tolist(), float(level) / quantization_levels, "REPLACE")
            assignments += len(indices)
    modifier = obj.modifiers.new("AST_CANONICAL_ARMATURE", "ARMATURE")
    modifier.object = armature
    obj.parent = armature
    obj.matrix_parent_inverse = armature.matrix_world.inverted()
    return {"deform_groups": len(names), "weight_assignments": assignments, "max_influences": 4}


def solid_material(name: str, color: tuple[float, float, float, float], metallic: float = 0.0) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = 0.42
    shader.inputs["Metallic"].default_value = metallic
    return material


def linear_channel(value: float) -> float:
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def linear_rgba_from_bytes(red: int, green: int, blue: int, alpha: int = 255) -> tuple[float, float, float, float]:
    return (
        linear_channel(red / 255.0),
        linear_channel(green / 255.0),
        linear_channel(blue / 255.0),
        alpha / 255.0,
    )


def make_edge_materials() -> list[bpy.types.Material]:
    return [
        solid_material("AST_MAT_EDGE_NAVY", linear_rgba_from_bytes(7, 15, 38), 0.02),
        solid_material("AST_MAT_EDGE_GOLD", linear_rgba_from_bytes(156, 96, 25), 0.18),
        solid_material("AST_MAT_EDGE_IVORY", linear_rgba_from_bytes(194, 167, 112), 0.02),
        solid_material("AST_MAT_EDGE_BLUE", linear_rgba_from_bytes(20, 64, 130), 0.10),
    ]


def emissive_material_from_bytes(name: str, red: int, green: int, blue: int) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    for node in list(nodes):
        nodes.remove(node)
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = linear_rgba_from_bytes(red, green, blue)
    emission.inputs["Strength"].default_value = 1.0
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def create_eyelid(
    collection: bpy.types.Collection,
    armature: bpy.types.Object,
    side: str,
    front: bool,
) -> bpy.types.Object:
    center_x, center_z = pixel_to_world(42, 72)
    pixel_size, _, _, _ = world_mapping(1)
    radius_x, radius_z = 10.8 * pixel_size, 6.2 * pixel_size
    depth = -0.420 if front else 0.420
    segments = 48
    vertices = [(center_x, depth, center_z)]
    outline: list[tuple[float, float]] = []
    half = segments // 2
    for index in range(half + 1):
        fraction = index / half
        local_x = -radius_x + 2.0 * radius_x * fraction
        local_z = radius_z * math.sin(math.pi * fraction) ** 1.35
        outline.append((local_x, local_z))
    for index in range(half - 1, 0, -1):
        fraction = index / half
        local_x = -radius_x + 2.0 * radius_x * fraction
        local_z = -radius_z * math.sin(math.pi * fraction) ** 1.35
        outline.append((local_x, local_z))
    tilt = math.radians(8.0)
    for local_x, local_z in outline:
        rotated_x = local_x * math.cos(tilt) - local_z * math.sin(tilt)
        rotated_z = local_x * math.sin(tilt) + local_z * math.cos(tilt)
        vertices.append((center_x + rotated_x, depth, center_z + rotated_z))
    faces = []
    for index in range(segments):
        nxt = 1 + ((index + 1) % segments)
        # Front is viewed from negative Y and therefore needs a -Y normal;
        # glTF viewers cull the opposite winding even though Blender's viewport
        # normally draws both sides.
        faces.append((0, nxt, 1 + index) if front else (0, 1 + index, nxt))
    mesh = bpy.data.meshes.new(f"AST_EYELID_{side.upper()}_MESH")
    mesh.from_pydata(vertices, [], faces)
    eyelid_material = bpy.data.materials.get("AST_MAT_EYELID_NAVY")
    if eyelid_material is None:
        eyelid_material = emissive_material_from_bytes("AST_MAT_EYELID_NAVY", 13, 22, 48)
    mesh.materials.append(eyelid_material)
    obj = bpy.data.objects.new(f"AST_EYELID_{side.upper()}", mesh)
    collection.objects.link(obj)
    group_name = f"lid.{side}"
    group = obj.vertex_groups.new(name=group_name)
    group.add(list(range(len(vertices))), 1.0, "REPLACE")
    modifier = obj.modifiers.new("AST_CANONICAL_ARMATURE", "ARMATURE")
    modifier.object = armature
    obj.parent = armature
    obj.matrix_parent_inverse = armature.matrix_world.inverted()
    obj["asset_role"] = "animated_eyelid"
    return obj


def create_eyelid_seam(
    collection: bpy.types.Collection,
    armature: bpy.types.Object,
    side: str,
    front: bool,
) -> bpy.types.Object:
    center_x, center_z = pixel_to_world(42, 72)
    pixel_size, _, _, _ = world_mapping(1)
    depth = -0.424 if front else 0.424
    samples = 25
    half_width = 0.62 * pixel_size
    points: list[tuple[float, float]] = []
    for index in range(samples):
        fraction = index / (samples - 1)
        local_x = (-10.0 + 20.0 * fraction) * pixel_size
        local_z = (1.8 * (fraction - 0.5) - 1.25 * math.sin(math.pi * fraction)) * pixel_size
        points.append((center_x + local_x, center_z + local_z))
    vertices: list[tuple[float, float, float]] = []
    for index, (x, z) in enumerate(points):
        previous = points[max(0, index - 1)]
        following = points[min(samples - 1, index + 1)]
        tangent_x, tangent_z = following[0] - previous[0], following[1] - previous[1]
        length = max(math.hypot(tangent_x, tangent_z), 1e-8)
        normal_x, normal_z = -tangent_z / length * half_width, tangent_x / length * half_width
        vertices.append((x + normal_x, depth, z + normal_z))
        vertices.append((x - normal_x, depth, z - normal_z))
    faces = []
    for index in range(samples - 1):
        a, b = index * 2, index * 2 + 1
        c, d = index * 2 + 3, index * 2 + 2
        faces.append((a, b, c, d) if front else (a, d, c, b))
    mesh = bpy.data.meshes.new(f"AST_EYELID_SEAM_{side.upper()}_MESH")
    mesh.from_pydata(vertices, [], faces)
    seam_material = bpy.data.materials.get("AST_MAT_EYELID_SEAM")
    if seam_material is None:
        seam_material = emissive_material_from_bytes("AST_MAT_EYELID_SEAM", 43, 123, 206)
    mesh.materials.append(seam_material)
    obj = bpy.data.objects.new(f"AST_EYELID_SEAM_{side.upper()}", mesh)
    collection.objects.link(obj)
    group_name = f"lid.{side}"
    group = obj.vertex_groups.new(name=group_name)
    group.add(list(range(len(vertices))), 1.0, "REPLACE")
    modifier = obj.modifiers.new("AST_CANONICAL_ARMATURE", "ARMATURE")
    modifier.object = armature
    obj.parent = armature
    obj.matrix_parent_inverse = armature.matrix_world.inverted()
    obj["asset_role"] = "animated_eyelid_seam"
    return obj


def reset_pose(armature: bpy.types.Object) -> None:
    for bone in armature.pose.bones:
        bone.location = (0.0, 0.0, 0.0)
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)
    armature.pose.bones["lid.front"].scale = (1.0, 1.0, 0.018)
    armature.pose.bones["lid.back"].scale = (1.0, 1.0, 0.018)


def radians3(values: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(math.radians(value) for value in values)


def create_action(
    armature: bpy.types.Object,
    name: str,
    end_frame: int,
    poses: list[tuple[int, dict[str, dict[str, tuple[float, float, float]]]]],
    *,
    loop: bool,
) -> bpy.types.Action:
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    action.use_frame_range = True
    action.frame_start = 1
    action.frame_end = end_frame
    action["clip_name"] = name
    action["loop"] = loop
    action["fps"] = FPS
    action["canonical_source_sha256"] = CANONICAL_SHA256
    armature.animation_data_create()
    armature.animation_data.action = action
    for frame, overrides in poses:
        reset_pose(armature)
        for bone_name, transform in overrides.items():
            bone = armature.pose.bones[bone_name]
            if "location" in transform:
                bone.location = transform["location"]
            if "rotation" in transform:
                bone.rotation_euler = radians3(transform["rotation"])
            if "scale" in transform:
                bone.scale = transform["scale"]
        for bone in armature.pose.bones:
            bone.keyframe_insert(data_path="location", frame=frame, group=bone.name)
            bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=bone.name)
            bone.keyframe_insert(data_path="scale", frame=frame, group=bone.name)
    return action


def create_animations(armature: bpy.types.Object) -> dict[str, bpy.types.Action]:
    actions: dict[str, bpy.types.Action] = {}
    actions["idle"] = create_action(armature, "idle", 80, [
        (1, {}),
        (20, {"body": {"location": (0, 0, 0.020)}, "head": {"rotation": (0, -1.4, 0)}, "tail.02": {"rotation": (0, 4, 0)}, "tail.03": {"rotation": (0, 7, 0)}}),
        (40, {"body": {"location": (0, 0, 0.037)}, "neck": {"rotation": (0, 1.2, 0)}, "tail.02": {"rotation": (0, -4, 0)}, "tail.03": {"rotation": (0, -7, 0)}}),
        (60, {"body": {"location": (0, 0, 0.018)}, "head": {"rotation": (0, 1.0, 0)}, "tail.02": {"rotation": (0, 3, 0)}, "tail.03": {"rotation": (0, 6, 0)}}),
        (80, {}),
    ], loop=True)
    actions["blink"] = create_action(armature, "blink", 20, [
        (1, {}), (7, {}),
        (10, {"lid.front": {"scale": (1, 1, 1)}, "lid.back": {"scale": (1, 1, 1)}}),
        (13, {}), (20, {}),
    ], loop=True)
    actions["happy"] = create_action(armature, "happy", 48, [
        (1, {}),
        (12, {"body": {"location": (0, 0, 0.09)}, "neck": {"rotation": (0, -7, 0)}, "head": {"rotation": (0, 8, 0)}, "tail.01": {"rotation": (0, 12, 0)}, "tail.02": {"rotation": (0, 22, 0)}, "tail.03": {"rotation": (0, 27, 0)}}),
        (22, {"body": {"location": (0, 0, 0.16)}, "foreleg.L": {"rotation": (0, -16, 0)}, "forepaw.L": {"rotation": (0, 22, 0)}, "head": {"rotation": (0, -7, 0)}, "tail.01": {"rotation": (0, -14, 0)}, "tail.02": {"rotation": (0, -24, 0)}, "tail.03": {"rotation": (0, -30, 0)}}),
        (34, {"body": {"location": (0, 0, 0.07)}, "head": {"rotation": (0, 5, 0)}, "tail.02": {"rotation": (0, 18, 0)}}),
        (48, {}),
    ], loop=False)
    actions["eat"] = create_action(armature, "eat", 60, [
        (1, {}),
        (14, {"neck": {"rotation": (0, -24, 0)}, "head": {"rotation": (0, 11, 0)}}),
        (23, {"neck": {"rotation": (0, -28, 0)}, "head": {"rotation": (0, 13, 0)}, "jaw": {"rotation": (0, -18, 0)}}),
        (31, {"neck": {"rotation": (0, -27, 0)}, "head": {"rotation": (0, 11, 0)}, "jaw": {"rotation": (0, 2, 0)}}),
        (40, {"neck": {"rotation": (0, -26, 0)}, "jaw": {"rotation": (0, -16, 0)}}),
        (60, {}),
    ], loop=False)
    actions["play"] = create_action(armature, "play", 56, [
        (1, {}),
        (10, {"body": {"location": (0, 0, -0.06)}, "foreleg.L": {"rotation": (0, 12, 0)}, "foreleg.R": {"rotation": (0, 12, 0)}}),
        (22, {"body": {"location": (-0.03, 0, 0.24)}, "foreleg.L": {"rotation": (0, -22, 0)}, "foreleg.R": {"rotation": (0, -18, 0)}, "hindleg.L": {"rotation": (0, 18, 0)}, "hindleg.R": {"rotation": (0, 20, 0)}, "tail.02": {"rotation": (0, 19, 0)}}),
        (34, {"body": {"location": (0.02, 0, 0.28)}, "foreleg.L": {"rotation": (0, 17, 0)}, "hindleg.L": {"rotation": (0, -18, 0)}, "tail.02": {"rotation": (0, -20, 0)}}),
        (46, {"body": {"location": (0, 0, -0.03)}}),
        (56, {}),
    ], loop=False)
    actions["pet_reaction"] = create_action(armature, "pet_reaction", 48, [
        (1, {}),
        (12, {"neck": {"rotation": (0, -7, 0)}, "head": {"rotation": (0, 13, 0)}, "body": {"location": (0, 0.02, 0.03)}, "tail.02": {"rotation": (0, 17, 0)}}),
        (24, {"neck": {"rotation": (0, -9, 0)}, "head": {"rotation": (0, -11, 0)}, "body": {"location": (0, -0.02, 0.05)}, "tail.02": {"rotation": (0, -19, 0)}}),
        (36, {"head": {"rotation": (0, 8, 0)}, "tail.02": {"rotation": (0, 12, 0)}}),
        (48, {}),
    ], loop=False)
    sleep_pose = {
        "body": {"location": (0.09, 0, -0.18), "rotation": (0, 4, 0)},
        "neck": {"rotation": (0, -29, 0)},
        "head": {"rotation": (0, 24, 0)},
        "foreleg.L": {"rotation": (0, 34, 0)}, "foreleg.R": {"rotation": (0, 31, 0)},
        "forepaw.L": {"rotation": (0, -42, 0)}, "forepaw.R": {"rotation": (0, -40, 0)},
        "hindleg.L": {"rotation": (0, -28, 0)}, "hindleg.R": {"rotation": (0, -26, 0)},
        "hindpaw.L": {"rotation": (0, 34, 0)}, "hindpaw.R": {"rotation": (0, 32, 0)},
        "tail.01": {"rotation": (0, 16, 0)}, "tail.02": {"rotation": (0, 25, 0)}, "tail.03": {"rotation": (0, 22, 0)},
        "lid.front": {"scale": (1, 1, 1)}, "lid.back": {"scale": (1, 1, 1)},
    }
    sleep_breathe = {key: dict(value) for key, value in sleep_pose.items()}
    sleep_breathe["body"] = {"location": (0.09, 0, -0.158), "rotation": (0, 4, 0)}
    actions["sleep"] = create_action(armature, "sleep", 80, [(1, sleep_pose), (40, sleep_breathe), (80, sleep_pose)], loop=True)
    actions["wake"] = create_action(armature, "wake", 48, [
        (1, sleep_pose), (14, sleep_breathe),
        (25, {"body": {"location": (0.04, 0, -0.07)}, "neck": {"rotation": (0, -16, 0)}, "head": {"rotation": (0, 9, 0)}, "lid.front": {"scale": (1, 1, 0.62)}, "lid.back": {"scale": (1, 1, 0.62)}}),
        (35, {"body": {"location": (0, 0, 0.025)}, "neck": {"rotation": (0, 4, 0)}, "head": {"rotation": (0, -4, 0)}, "lid.front": {"scale": (1, 1, 0.10)}, "lid.back": {"scale": (1, 1, 0.10)}}),
        (48, {}),
    ], loop=False)
    actions["walk"] = create_action(armature, "walk", 41, [
        (1, {"foreleg.L": {"rotation": (0, -17, 0)}, "foreleg.R": {"rotation": (0, 17, 0)}, "hindleg.L": {"rotation": (0, 17, 0)}, "hindleg.R": {"rotation": (0, -17, 0)}, "tail.02": {"rotation": (0, 7, 0)}}),
        (11, {"body": {"location": (0, 0, 0.04)}}),
        (21, {"foreleg.L": {"rotation": (0, 17, 0)}, "foreleg.R": {"rotation": (0, -17, 0)}, "hindleg.L": {"rotation": (0, -17, 0)}, "hindleg.R": {"rotation": (0, 17, 0)}, "tail.02": {"rotation": (0, -7, 0)}}),
        (31, {"body": {"location": (0, 0, 0.04)}}),
        (41, {"foreleg.L": {"rotation": (0, -17, 0)}, "foreleg.R": {"rotation": (0, 17, 0)}, "hindleg.L": {"rotation": (0, 17, 0)}, "hindleg.R": {"rotation": (0, -17, 0)}, "tail.02": {"rotation": (0, 7, 0)}}),
    ], loop=True)
    armature.animation_data.action = actions["idle"]
    bpy.context.scene.frame_set(1)
    return actions


def point_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def setup_stage(resolution: int) -> tuple[bpy.types.Object, bpy.types.Object]:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.dither_intensity = 0.0
    scene.render.fps = FPS
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0

    world = bpy.data.worlds.get("AST_CANONICAL_WORLD") or bpy.data.worlds.new("AST_CANONICAL_WORLD")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.003, 0.008, 0.025, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.24
    scene.world = world

    floor_material = solid_material("AST_MAT_REVIEW_FLOOR", (0.012, 0.026, 0.070, 1.0), 0.12)
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0.010))
    floor = bpy.context.object
    floor.name = "REVIEW_CANONICAL_FLOOR"
    floor.data.materials.append(floor_material)
    floor["asset_role"] = "review_only"

    bpy.ops.object.camera_add(location=(0, -6, 1.45))
    camera = bpy.context.object
    camera.name = "REVIEW_CANONICAL_CAMERA"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 3.18
    camera.data.lens = 58
    scene.camera = camera

    light_specs = (
        ("REVIEW_KEY", (-3.0, -4.2, 5.2), (1.0, 0.74, 0.47), 360.0, 4.0),
        ("REVIEW_FILL", (2.1, -3.0, 3.2), (0.24, 0.48, 1.0), 240.0, 3.5),
        ("REVIEW_RIM", (2.9, 3.5, 4.4), (0.42, 0.65, 1.0), 320.0, 3.0),
    )
    for name, location, color, energy, size in light_specs:
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.color = color
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = location
        point_at(light, (0, 0, 1.35))
        light["asset_role"] = "review_only"
    return camera, floor


def render_views(
    camera: bpy.types.Object,
    floor: bpy.types.Object,
    armature: bpy.types.Object,
    actions: dict[str, bpy.types.Action],
    shell: bpy.types.Object,
    pbr_material: bpy.types.Material,
    exact_material: bpy.types.Material,
    eyelids: list[bpy.types.Object],
    output_dir: Path,
) -> dict[str, str]:
    scene = bpy.context.scene
    center_z = BASE_Z + WORLD_HEIGHT * 0.5
    specs = {
        "canonical-side": ("idle", 1, (0.0, -6.0, center_z), (0.0, 0.0, center_z), 3.04, True, True),
        "hero": ("idle", 1, (-3.6, -5.3, 3.05), (0.0, 0.0, 1.37), 3.55, False, False),
        "front": ("idle", 1, (-6.0, 0.0, center_z), (0.0, 0.0, center_z), 3.16, False, False),
        "rear-three-quarter": ("idle", 1, (3.6, 5.3, 2.75), (0.0, 0.0, 1.34), 3.55, False, False),
        "blink": ("blink", 10, (0.0, -6.0, center_z), (0.0, 0.0, center_z), 3.04, True, True),
        "happy": ("happy", 22, (-3.6, -5.3, 3.05), (0.0, 0.0, 1.42), 3.65, False, False),
        "sleep": ("sleep", 40, (-3.6, -5.3, 2.65), (0.0, 0.0, 1.05), 3.60, False, False),
        "walk": ("walk", 11, (0.0, -6.0, center_z), (0.0, 0.0, center_z), 3.12, True, False),
    }
    outputs: dict[str, str] = {}
    for name, (action_name, frame, location, target, scale, transparent, exact) in specs.items():
        armature.animation_data.action = actions[action_name]
        scene.frame_set(frame)
        camera.location = location
        camera.data.ortho_scale = scale
        point_at(camera, target)
        floor.hide_render = transparent
        scene.render.film_transparent = transparent
        shell.data.materials[0] = exact_material if exact else pbr_material
        show_lids = name in {"blink", "sleep"}
        for eyelid in eyelids:
            eyelid.hide_render = not show_lids
        destination = output_dir / f"{ASSET_NAME}-{name}.png"
        scene.render.filepath = str(destination)
        bpy.ops.render.render(write_still=True)
        outputs[name] = str(destination)
    # Pixel-registered evidence render.  Its camera maps the original 192x208
    # canvas one-to-one; it is the objective likeness check for the known view.
    old_resolution = (scene.render.resolution_x, scene.render.resolution_y)
    scene.render.resolution_x = 192
    scene.render.resolution_y = 208
    pixel_size, _, _, _ = world_mapping(1)
    canvas_center_z = pixel_to_world(96, 104)[1]
    camera.location = (0.0, -6.0, canvas_center_z)
    camera.data.ortho_scale = 208 * pixel_size
    point_at(camera, (0.0, 0.0, canvas_center_z))
    shell.data.materials[0] = exact_material
    for eyelid in eyelids:
        eyelid.hide_render = True
    floor.hide_render = True
    scene.render.film_transparent = True
    armature.animation_data.action = actions["idle"]
    scene.frame_set(1)
    registration = output_dir / f"{ASSET_NAME}-canonical-registration.png"
    scene.render.filepath = str(registration)
    bpy.ops.render.render(write_still=True)
    outputs["canonical-registration"] = str(registration)
    scene.render.resolution_x, scene.render.resolution_y = old_resolution
    shell.data.materials[0] = pbr_material
    for eyelid in eyelids:
        eyelid.hide_render = False
    floor.hide_render = False
    scene.render.film_transparent = False
    armature.animation_data.action = actions["idle"]
    scene.frame_set(1)
    return outputs


def export_glb(
    armature: bpy.types.Object,
    delivery_meshes: list[bpy.types.Object],
    destination: Path,
) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    for obj in delivery_meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.gltf(
        filepath=str(destination),
        export_format="GLB",
        use_selection=True,
        export_extras=True,
        export_yup=True,
        export_apply=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_action_filter=False,
        export_frame_range=False,
        export_force_sampling=True,
        export_skins=True,
        export_def_bones=False,
        export_rest_position_armature=True,
        export_optimize_animation_size=True,
        export_cameras=False,
        export_lights=False,
        export_meshopt_compression_enable=True,
        export_meshopt_extension="EXT_meshopt_compression",
    )


def main() -> None:
    args = parse_args()
    canonical = Path(args.canonical_reference).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    verify_reference(canonical)
    if args.grid_scale < 1 or args.grid_scale > 6:
        raise ValueError("grid-scale must be in the range 1..6")

    clean_scene()
    image, rgb, mask = image_arrays(canonical)
    collection = bpy.data.collections.new("ASTERION_CANONICAL_MASTER")
    bpy.context.scene.collection.children.link(collection)
    shell, fields, mesh_stats = build_dense_shell(collection, image, rgb, mask, args.grid_scale)
    pbr_material = shell.data.materials[0]
    exact_material = make_exact_material(image)
    armature = create_rig(collection)
    skin_stats = attach_skin(shell, armature, fields)
    eyelid_front = create_eyelid(collection, armature, "front", True)
    eyelid_back = create_eyelid(collection, armature, "back", False)
    eyelid_seam_front = create_eyelid_seam(collection, armature, "front", True)
    eyelid_seam_back = create_eyelid_seam(collection, armature, "back", False)
    actions = create_animations(armature)
    camera, floor = setup_stage(args.preview_resolution)

    scene = bpy.context.scene
    scene["asset_name"] = ASSET_NAME
    scene["asset_version"] = "1.0.0"
    scene["canonical_reference"] = canonical.name
    scene["canonical_sha256"] = CANONICAL_SHA256
    scene["source_view_fidelity"] = "exact source texture and alpha silhouette"
    scene["inference_boundary"] = "depth, reverse view, and animation"
    scene["grid_scale"] = args.grid_scale
    collection["delivery_role"] = "canonical_highpoly_master"

    outputs = render_views(
        camera,
        floor,
        armature,
        actions,
        shell,
        pbr_material,
        exact_material,
        [eyelid_front, eyelid_back, eyelid_seam_front, eyelid_seam_back],
        output_dir,
    )
    blend_path = output_dir / f"{ASSET_NAME}.blend"
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)

    glb_path = output_dir / f"{ASSET_NAME}.glb"
    delivery_meshes = [shell, eyelid_front, eyelid_back, eyelid_seam_front, eyelid_seam_back]
    if args.export_glb:
        export_glb(armature, delivery_meshes, glb_path)

    report = {
        "asset": ASSET_NAME,
        "version": "1.0.0",
        "canonical": {
            "path": str(canonical),
            "sha256": CANONICAL_SHA256,
            "visible_side": "direct UV projection; no generative reinterpretation",
            "inferred": ["depth", "opposite side", "deformation", "motion"],
        },
        "mesh": mesh_stats,
        "skinning": skin_stats,
        "bones": len(armature.data.bones),
        "actions": {
            name: {
                "frame_start": int(action.frame_start),
                "frame_end": int(action.frame_end),
                "loop": bool(action["loop"]),
            }
            for name, action in actions.items()
        },
        "outputs": {
            "blend": str(blend_path),
            "blend_sha256": sha256(blend_path),
            "glb": str(glb_path) if args.export_glb else None,
            "glb_sha256": sha256(glb_path) if args.export_glb else None,
            "renders": outputs,
        },
        "blender": bpy.app.version_string,
    }
    report_path = output_dir / f"{ASSET_NAME}-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

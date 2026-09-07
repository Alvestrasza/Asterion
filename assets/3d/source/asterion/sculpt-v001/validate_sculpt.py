"""Fresh-import structural, skeletal and render evidence for volumetric Asterion.

Run in a separate Blender process:
  blender --background --python validate_sculpt.py -- --glb asset.glb --output evidence

The output is a directory containing JSON evidence and 850px front, hero and
closed-blink renders. Import timing is fixed at 30 fps BEFORE glTF import.
No source GLB is changed. This is asset validation, not mobile acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import bpy
from mathutils import Vector


CLIPS = {"idle", "blink", "happy", "eat", "play", "pet_reaction", "sleep", "wake", "walk"}
PAWS = ("fore.paw.L", "fore.paw.R", "hind.paw.L", "hind.paw.R")
WEIGHT_EPSILON = 1e-5
WEIGHT_SUM_TOLERANCE = 0.002


def args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--glb", required=True)
    parser.add_argument("--output", required=True, help="New evidence output directory")
    parser.add_argument("--samples", type=int, default=40)
    parser.add_argument("--device", choices=("OPTIX", "CPU"), default="OPTIX")
    return parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _glb_document(path):
    with path.open("rb") as stream:
        magic, version, declared_length = struct.unpack("<III", stream.read(12))
        chunk_length, chunk_type = struct.unpack("<II", stream.read(8))
        if magic != 0x46546C67 or version != 2 or chunk_type != 0x4E4F534A:
            raise ValueError("Expected a glTF 2.0 binary file with JSON first chunk")
        if declared_length != path.stat().st_size:
            raise ValueError("GLB header length does not match file bytes")
        return json.loads(stream.read(chunk_length).decode("utf-8"))


def _finite_matrix(matrix):
    return all(math.isfinite(value) for row in matrix for value in row)


def _activate(rig, action, frame):
    animation = rig.animation_data_create()
    for track in animation.nla_tracks:
        track.mute = True
    animation.action = action
    # Blender 4.4+ imported actions are slotted. Select the armature slot
    # explicitly so action switching cannot silently leave the old pose.
    if hasattr(action, "slots") and len(action.slots):
        slots = list(action.slots)
        matching = [slot for slot in slots if rig.name in slot.identifier]
        animation.action_slot = matching[0] if matching else slots[0]
    bpy.context.scene.frame_set(int(frame))
    bpy.context.view_layer.update()


def _bounds_update(bounds, point):
    for axis in range(3):
        bounds[0][axis] = min(bounds[0][axis], point[axis])
        bounds[1][axis] = max(bounds[1][axis], point[axis])


def _bounds_new():
    return [[math.inf]*3, [-math.inf]*3]


def _inspect(meshes, rig):
    bones = set(rig.data.bones.keys()) if rig else set()
    bounds = _bounds_new()
    paw_data = {name: {"vertices": 0, "weight_sum": 0.0, "weighted_xyz": [0.0]*3,
                       "bounds": _bounds_new()} for name in PAWS}
    result = {"vertices": 0, "triangles": 0, "unweighted_vertices": 0,
              "nonfinite_vertices": 0, "nonfinite_transforms": 0,
              "negative_or_excess_weights": 0, "vertices_over_four_influences": 0,
              "unnormalized_vertices": 0, "unknown_weight_groups": 0,
              "max_influences": 0, "max_weight_sum_error": 0.0, "mesh_details": []}
    for obj in meshes:
        obj.data.calc_loop_triangles()
        group_names = {group.index: group.name for group in obj.vertex_groups}
        world = obj.matrix_world.copy()
        if not _finite_matrix(world):
            result["nonfinite_transforms"] += 1
        local_bad_weights = 0
        for vertex in obj.data.vertices:
            point = world @ vertex.co
            if not all(math.isfinite(value) for value in point):
                result["nonfinite_vertices"] += 1
            else:
                _bounds_update(bounds, point)
            influences = []
            for group in vertex.groups:
                if not math.isfinite(group.weight) or group.weight < -WEIGHT_EPSILON or group.weight > 1+WEIGHT_EPSILON:
                    result["negative_or_excess_weights"] += 1
                if group.weight > WEIGHT_EPSILON:
                    name = group_names.get(group.group)
                    if name not in bones:
                        result["unknown_weight_groups"] += 1
                    else:
                        influences.append((name, group.weight))
            count = len(influences)
            result["max_influences"] = max(result["max_influences"], count)
            if count > 4:
                result["vertices_over_four_influences"] += 1
            if not count:
                result["unweighted_vertices"] += 1
            error = abs(sum(weight for _, weight in influences)-1.0)
            result["max_weight_sum_error"] = max(result["max_weight_sum_error"], error)
            if error > WEIGHT_SUM_TOLERANCE:
                result["unnormalized_vertices"] += 1
                local_bad_weights += 1
            for name, weight in influences:
                if name in paw_data and weight > 0.25:
                    data = paw_data[name]
                    data["vertices"] += 1
                    data["weight_sum"] += weight
                    for axis in range(3):
                        data["weighted_xyz"][axis] += point[axis]*weight
                    _bounds_update(data["bounds"], point)
        result["vertices"] += len(obj.data.vertices)
        result["triangles"] += len(obj.data.loop_triangles)
        result["mesh_details"].append({"name": obj.name, "vertices": len(obj.data.vertices),
            "triangles": len(obj.data.loop_triangles), "material_slots": len(obj.data.materials),
            "unnormalized_vertices": local_bad_weights})
    if not all(math.isfinite(value) for corner in bounds for value in corner):
        bounds = [[0.0]*3, [0.0]*3]
    result["bounds"] = {"min": bounds[0], "max": bounds[1],
                        "span": [bounds[1][i]-bounds[0][i] for i in range(3)]}
    for name, data in paw_data.items():
        data["centroid"] = [v/data["weight_sum"] for v in data.pop("weighted_xyz")] if data["weight_sum"] else None
        if not data["vertices"]:
            data["bounds"] = None
    result["paw_surfaces"] = paw_data
    return result


def _paw_checks(paw_data):
    checks = {}
    for name, data in paw_data.items():
        center = data["centroid"]
        correct_side = center and (center[0] > 0.2 if name.endswith(".L") else center[0] < -0.2)
        correct_end = center and (center[1] < -0.4 if name.startswith("fore") else center[1] > 0.4)
        checks[name] = bool(data["vertices"] >= 50 and data["weight_sum"] >= 10 and
                            correct_side and correct_end and center[2] < 0.70)
    return checks


def _animation_checks(rig, actions, meshes):
    evidence = {}
    if not rig:
        return evidence
    for name in sorted(CLIPS & set(actions)):
        action = actions[name]
        start, end = action.frame_range
        frames = sorted({int(round(start)), int(round((start+end)/2)), int(round(end))})
        bad = 0
        for frame in frames:
            _activate(rig, action, frame)
            bad += sum(not _finite_matrix(bone.matrix) for bone in rig.pose.bones)
            bad += sum(not _finite_matrix(obj.matrix_world) for obj in meshes)
        evidence[name] = {"frame_range": [float(start), float(end)], "sampled_frames": frames,
                          "nonfinite_sampled_transforms": bad}
    return evidence


def _point_at(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z", "Y").to_euler()


def _stage(samples, requested_device):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.device = "CPU"
    device = "CPU"
    device_note = None
    if requested_device == "OPTIX":
        try:
            preferences = bpy.context.preferences.addons["cycles"].preferences
            preferences.compute_device_type = "OPTIX"
            preferences.get_devices()
            has_optix = any(d.type == "OPTIX" for d in preferences.devices)
            if has_optix:
                for candidate in preferences.devices:
                    candidate.use = candidate.type == "OPTIX"
                scene.cycles.device = "GPU"
                device = "OPTIX"
            else:
                device_note = "No available OPTIX device; used Cycles CPU."
        except Exception as exc:
            device_note = f"OPTIX unavailable; used Cycles CPU ({type(exc).__name__})."
    scene.render.resolution_x = scene.render.resolution_y = 850
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    world = bpy.data.worlds.new("validation_studio_world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.60, 0.57, 0.51, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.7
    scene.world = world
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0.035))
    ground = bpy.context.object
    ground.name = "validation_studio_ground"
    material = bpy.data.materials.new("validation_off_white")
    material.use_nodes = True
    bsdf = material.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.730, 0.715, 0.665, 1)
    bsdf.inputs["Roughness"].default_value = 0.8
    bsdf.inputs["Emission Color"].default_value = (0.730, 0.715, 0.665, 1)
    bsdf.inputs["Emission Strength"].default_value = 0.25
    ground.data.materials.append(material)
    for name, position, energy, size, color in (
        ("key", (-4, -6, 9), 1450, 5, (1, 0.90, 0.76)),
        ("fill", (5, -4, 5), 1100, 5, (0.78, 0.87, 1)),
        ("rim", (2, 5, 7), 1850, 4, (1, 0.88, 0.66)),
        ("top", (-1, 1, 10), 900, 3, (1, 0.96, 0.88)),
    ):
        data = bpy.data.lights.new("validation_"+name, "AREA")
        data.energy, data.size, data.color = energy, size, color
        data.shape = "DISK"
        light = bpy.data.objects.new("validation_"+name, data)
        scene.collection.objects.link(light)
        light.location = position
        _point_at(light, (0, 0, 2.5))
    data = bpy.data.cameras.new("validation_camera")
    data.type = "ORTHO"
    camera = bpy.data.objects.new("validation_camera", data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return camera, {"engine": "CYCLES", "device": device, "device_note": device_note,
                    "resolution": [850, 850], "samples": samples, "denoising": True}


def _render_evidence(rig, actions, output, samples, device):
    camera, settings = _stage(samples, device)
    scene = bpy.context.scene
    renders = {}
    # Exactly match the production review cameras for honest re-import comparison.
    views = {
        "front": ("idle", (0, -14, 4.3), (0, -0.15, 2.88), 6.6),
        "hero": ("idle", (8, -12, 5.8), (0, 0.25, 2.88), 6.8),
        "blink": ("blink", (8, -12, 5.8), (0, 0.25, 2.88), 6.8),
    }
    for name, (clip, position, target, scale) in views.items():
        action = actions[clip]
        start, end = action.frame_range
        # Authored blink closes fully across t=.44-.57: midpoint is the peak.
        frame = int(round((start+end)/2)) if clip == "blink" else int(round(start))
        _activate(rig, action, frame)
        camera.location = position
        camera.data.ortho_scale = scale
        _point_at(camera, target)
        path = output/f"asterion-sculpt-glb-import-{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        renders[name] = {"path": str(path), "clip": clip, "frame": frame,
                         "camera_position": list(position), "camera_target": list(target),
                         "ortho_scale": scale}
    _activate(rig, actions["idle"], int(round(actions["idle"].frame_range[0])))
    return renders, settings


def main():
    options = args()
    source, output = Path(options.glb).resolve(), Path(options.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    document = _glb_document(source)
    authored_names = {animation.get("name") for animation in document.get("animations", [])}
    authored_cameras = len(document.get("cameras", []))
    authored_lights = len(document.get("extensions", {}).get("KHR_lights_punctual", {}).get("lights", []))
    primitives = sum(len(mesh.get("primitives", [])) for mesh in document.get("meshes", []))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    bpy.context.scene.render.fps_base = 1.0
    bpy.ops.import_scene.gltf(filepath=str(source))
    scene = bpy.context.scene
    imported_cameras = [o.name for o in scene.objects if o.type == "CAMERA"]
    imported_lights = [o.name for o in scene.objects if o.type == "LIGHT"]
    armatures = [o for o in scene.objects if o.type == "ARMATURE"]
    rig = armatures[0] if len(armatures) == 1 else None
    all_meshes = [o for o in scene.objects if o.type == "MESH"]
    # Blender's importer may create this unexported armature display helper.
    helpers = [o for o in all_meshes if o.name.startswith("Icosphere") and not o.data.materials
               and len(o.data.vertices) == 42 and not o.vertex_groups]
    for helper in helpers:
        helper.hide_render = True
    meshes = [o for o in all_meshes if o not in helpers]
    actions = {a.name: a for a in bpy.data.actions}
    if rig and "idle" in actions:
        _activate(rig, actions["idle"], int(round(actions["idle"].frame_range[0])))
    geometry = _inspect(meshes, rig)
    paw_checks = _paw_checks(geometry["paw_surfaces"])
    animation_checks = _animation_checks(rig, actions, meshes)
    span = geometry["bounds"]["span"]
    checks = {
        "one_armature": len(armatures) == 1,
        "twenty_two_bones": bool(rig and len(rig.data.bones) == 22),
        "authored_nine_clips": authored_names == CLIPS and len(document.get("animations", [])) == 9,
        "imported_nine_clips": set(actions) == CLIPS,
        "no_authored_cameras_or_lights": authored_cameras == authored_lights == 0,
        "no_imported_cameras_or_lights": not imported_cameras and not imported_lights,
        "finite_geometry": geometry["nonfinite_vertices"] == geometry["nonfinite_transforms"] == 0,
        "finite_animation_samples": len(animation_checks) == 9 and
            all(v["nonfinite_sampled_transforms"] == 0 for v in animation_checks.values()),
        "all_vertices_weighted": geometry["unweighted_vertices"] == 0,
        "normalized_skinning": geometry["unnormalized_vertices"] == geometry["negative_or_excess_weights"] == 0,
        "maximum_four_influences": geometry["max_influences"] <= 4,
        "known_deformation_groups": geometry["unknown_weight_groups"] == 0,
        "volumetric_bounds_x_y_z": span[0] >= 2.0 and span[1] >= 4.0 and span[2] >= 5.0,
        "four_separate_weighted_paw_surfaces": all(paw_checks.values()),
        "nonempty_triangle_geometry": geometry["triangles"] > 0,
    }
    renders, render_settings, render_error = {}, {}, None
    if rig and {"idle", "blink"}.issubset(actions):
        try:
            renders, render_settings = _render_evidence(rig, actions, output, options.samples, options.device)
        except Exception as exc:
            render_error = f"{type(exc).__name__}: {exc}"
    checks["three_import_evidence_renders"] = len(renders) == 3 and all(
        Path(render["path"]).is_file() for render in renders.values())
    report = {
        "asset": str(source), "sha256": _sha256(source), "file_size_bytes": source.stat().st_size,
        "blender": bpy.app.version_string, "import_fps": scene.render.fps,
        "authored_meshes": len(document.get("meshes", [])), "imported_meshes": len(meshes),
        "authored_primitives_draw_call_estimate": primitives,
        "materials": len(document.get("materials", [])), "extensions": document.get("extensionsUsed", []),
        "authored_cameras": authored_cameras, "authored_lights": authored_lights,
        "imported_cameras": imported_cameras, "imported_lights": imported_lights,
        "import_helpers_ignored": [o.name for o in helpers],
        "armatures": len(armatures), "bones": len(rig.data.bones) if rig else 0,
        "authored_actions": sorted(authored_names), "imported_actions": sorted(actions),
        "geometry": geometry, "paw_checks": paw_checks, "animation_checks": animation_checks,
        "renders": renders, "render_settings": render_settings, "render_error": render_error,
        "checks": checks, "passed": all(checks.values()),
        "mobile_performance_accepted": False,
        "warnings": (["High primitive/draw-call count. Merge compatible skinned meshes by shared material "
                      "after assigning vertex groups; retain eyelid and bone weights, then re-export and validate. "
                      "A high-poly offline render does not establish mobile performance."] if primitives > 64 else []),
    }
    destination = output/"asterion-sculpt-glb-validation.json"
    destination.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"report": str(destination), "passed": report["passed"], "checks": checks,
                      "triangles": geometry["triangles"], "bounds": geometry["bounds"],
                      "draw_call_estimate": primitives}, indent=2), flush=True)
    if not report["passed"]:
        raise RuntimeError("Volumetric Asterion GLB validation failed; inspect JSON evidence")


if __name__ == "__main__":
    main()

"""Fresh-import validation for the canonical Asterion GLB."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector


REQUIRED_ACTIONS = {"idle", "blink", "happy", "eat", "play", "pet_reaction", "sleep", "wake", "walk"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--glb", required=True)
    parser.add_argument("--output-dir", required=True)
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


def point_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def setup_render() -> bpy.types.Object:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.render.dither_intensity = 0.0
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.003, 0.008, 0.025, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.2
    scene.world = world
    for name, location, energy, color in (
        ("VALIDATE_KEY", (-3, -4, 5), 280, (1.0, 0.75, 0.48)),
        ("VALIDATE_FILL", (2, -3, 3), 190, (0.25, 0.48, 1.0)),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.color = color
        data.shape = "DISK"
        data.size = 4.0
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = location
        point_at(light, (0, 0, 1.4))
    data = bpy.data.cameras.new("VALIDATE_CAMERA_DATA")
    data.type = "ORTHO"
    data.ortho_scale = 3.04
    camera = bpy.data.objects.new("VALIDATE_CAMERA", data)
    scene.collection.objects.link(camera)
    camera.location = (0, -6, 1.455)
    point_at(camera, (0, 0, 1.455))
    scene.camera = camera
    return camera


def main() -> None:
    args = parse_args()
    glb = Path(args.glb).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    # glTF stores animation time in seconds.  Import at the authored rate so
    # evidence frames (notably blink frame 10) land on the intended keyframes.
    bpy.context.scene.render.fps = 30
    bpy.ops.import_scene.gltf(filepath=str(glb))

    all_meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    # Blender's glTF importer creates an unexported 42-vertex Icosphere helper
    # for armature visualization.  It is absent from the GLB node/mesh tables
    # and must not be counted as delivery geometry.
    import_helpers = [obj for obj in all_meshes if obj.name.startswith("Icosphere") and not obj.data.materials]
    meshes = [obj for obj in all_meshes if obj not in import_helpers]
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    actions = {action.name: action for action in bpy.data.actions}
    action_names = set(actions)
    triangles = 0
    vertices = 0
    max_influences = 0
    unweighted_vertices = 0
    mesh_details = []
    for obj in meshes:
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
        vertices += len(obj.data.vertices)
        object_unweighted = 0
        object_max_influences = 0
        for vertex in obj.data.vertices:
            influence_count = sum(1 for group in vertex.groups if group.weight > 0.0001)
            max_influences = max(max_influences, influence_count)
            object_max_influences = max(object_max_influences, influence_count)
            if not vertex.groups:
                unweighted_vertices += 1
                object_unweighted += 1
        mesh_details.append({
            "name": obj.name,
            "vertices": len(obj.data.vertices),
            "triangles": len(obj.data.loop_triangles),
            "unweighted_vertices": object_unweighted,
            "max_vertex_influences": object_max_influences,
        })

    armature = armatures[0] if armatures else None
    camera = setup_render()
    renders = {}
    if armature:
        armature.animation_data_create()
        for name, frame in (("idle", 1), ("blink", 10), ("walk", 11)):
            if name not in actions:
                continue
            armature.animation_data.action = actions[name]
            bpy.context.scene.frame_set(frame)
            destination = output_dir / f"asterion-canonical-highpoly-v001-glb-import-{name}.png"
            bpy.context.scene.render.filepath = str(destination)
            bpy.ops.render.render(write_still=True)
            renders[name] = str(destination)

    materials = sorted({material.name for obj in meshes for material in obj.data.materials if material})
    images = sorted(image.name for image in bpy.data.images)
    checks = {
        "one_armature": len(armatures) == 1,
        "bone_count_18": bool(armature and len(armature.data.bones) == 18),
        "required_actions": REQUIRED_ACTIONS.issubset(action_names),
        "highpoly_triangle_floor": triangles >= 1_360_000,
        "skinning_influence_limit": max_influences <= 4,
        "canonical_image_embedded": bool(images),
        "renders_written": len(renders) == 3 and all(Path(path).is_file() for path in renders.values()),
    }
    report = {
        "asset": str(glb),
        "sha256": sha256(glb),
        "file_size_bytes": glb.stat().st_size,
        "meshes": len(meshes),
        "import_helpers_ignored": [obj.name for obj in import_helpers],
        "mesh_details": mesh_details,
        "vertices": vertices,
        "triangles": triangles,
        "armatures": len(armatures),
        "bones": len(armature.data.bones) if armature else 0,
        "actions": sorted(action_names),
        "materials": materials,
        "images": images,
        "max_vertex_influences": max_influences,
        "unweighted_vertices": unweighted_vertices,
        "renders": renders,
        "checks": checks,
        "passed": all(checks.values()),
        "blender": bpy.app.version_string,
    }
    report_path = output_dir / "asterion-canonical-highpoly-v001-glb-validation.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise RuntimeError("Canonical GLB validation failed")


if __name__ == "__main__":
    main()

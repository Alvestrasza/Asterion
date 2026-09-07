"""Render a real animated Asterion turntable from an existing Blender master.

Example:
  blender --background release.blend --python render_motion.py -- --output E:/review/motion

Default: 96 frames, 720 square, 24 Cycles samples, 16 fps (six-second movie).
The idle armature animation is sampled into a temporary preview action, with
the actual blink action layered on its two lid bones near the initial front
view. A full camera orbit exposes the physical sculpture from every side.
The loaded master is never saved or altered on disk. No external codec or
Python package is required: Blender FFMPEG writes H.264/MPEG4 when available,
otherwise numbered PNG frames are retained as the explicit fallback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import bpy
from mathutils import Vector


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="Absolute output directory or new .mp4 filename")
    parser.add_argument("--frames", type=int, default=96)
    parser.add_argument("--fps", type=int, default=16)
    parser.add_argument("--resolution", type=int, default=720)
    parser.add_argument("--samples", type=int, default=24)
    parser.add_argument("--device", choices=("OPTIX", "CPU"), default="OPTIX")
    parser.add_argument("--encode-frames", help="Encode an existing absolute PNG frame directory through Blender VSE")
    parser.add_argument("--extract-video", action="store_true", help="Extract review stills from the existing output movie")
    return parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])


def digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            sha.update(block)
    return sha.hexdigest().upper()


def action_on(rig, action, frame):
    animation = rig.animation_data_create()
    for track in animation.nla_tracks:
        track.mute = True
    animation.action = action
    if hasattr(action, "slots") and action.slots:
        matching = [slot for slot in action.slots if rig.name in slot.identifier]
        animation.action_slot = matching[0] if matching else action.slots[0]
    integer_frame = math.floor(frame)
    bpy.context.scene.frame_set(integer_frame, subframe=frame-integer_frame)
    bpy.context.view_layer.update()


def curves(action):
    if hasattr(action, "fcurves"):
        yield from action.fcurves
    else:
        for layer in action.layers:
            for strip in layer.strips:
                if hasattr(strip, "channelbags"):
                    for channelbag in strip.channelbags:
                        yield from channelbag.fcurves


def bake_preview_action(rig, count):
    idle, blink = bpy.data.actions.get("idle"), bpy.data.actions.get("blink")
    if idle is None:
        raise ValueError("The loaded master must contain its authored idle action")
    idle_start, idle_end = map(float, idle.frame_range)
    blink_window = (5, min(20, count//4))
    lid_names = [name for name in ("lid.L", "lid.R") if name in rig.pose.bones]
    poses = []
    blink_frames = []
    for frame in range(1, count+1):
        t = (frame-1)/(count-1)
        action_on(rig, idle, idle_start+t*(idle_end-idle_start))
        pose = {bone.name: bone.matrix_basis.copy() for bone in rig.pose.bones}
        if blink is not None and lid_names and blink_window[0] <= frame <= blink_window[1]:
            b = (frame-blink_window[0])/(blink_window[1]-blink_window[0])
            begin, end = map(float, blink.frame_range)
            action_on(rig, blink, begin+b*(end-begin))
            for name in lid_names:
                pose[name] = rig.pose.bones[name].matrix_basis.copy()
            blink_frames.append(frame)
        poses.append(pose)
    action = bpy.data.actions.new("asterion_movie_preview")
    rig.animation_data.action = action
    for frame, pose in enumerate(poses, 1):
        for name, matrix in pose.items():
            bone = rig.pose.bones[name]
            bone.rotation_mode = "QUATERNION"
            bone.matrix_basis = matrix
            bone.keyframe_insert(data_path="location", frame=frame, group=name)
            bone.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=name)
            bone.keyframe_insert(data_path="scale", frame=frame, group=name)
    for curve in curves(action):
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"
    action_on(rig, action, 1)
    return {"source_idle_action": idle.name, "source_idle_frame_range": [idle_start, idle_end],
            "source_blink_action": blink.name if blink and blink_frames else None,
            "preview_blink_frames": blink_frames, "preview_action": action.name,
            "bone_count": len(rig.data.bones)}


def point_at(obj, target):
    obj.rotation_quaternion = (Vector(target)-obj.location).to_track_quat("-Z", "Y")


def orbit_camera(count):
    scene = bpy.context.scene
    original = scene.camera
    camera_data = original.data.copy() if original else bpy.data.cameras.new("motion_camera_data")
    camera = bpy.data.objects.new("motion_preview_camera", camera_data)
    scene.collection.objects.link(camera)
    camera.rotation_mode = "QUATERNION"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 6.9
    target = Vector((0, 0.25, 2.88))
    previous_quaternion = None
    for frame in range(1, count+1):
        angle = 2*math.pi*(frame-1)/(count-1)
        camera.location = (14.5*math.sin(angle), 0.25-14.5*math.cos(angle), 5.2)
        point_at(camera, target)
        if previous_quaternion is not None and previous_quaternion.dot(camera.rotation_quaternion) < 0:
            camera.rotation_quaternion.negate()
        previous_quaternion = camera.rotation_quaternion.copy()
        camera.keyframe_insert(data_path="location", frame=frame)
        camera.keyframe_insert(data_path="rotation_quaternion", frame=frame)
    for curve in curves(camera.animation_data.action):
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"
    scene.camera = camera
    return {"orbit_degrees": 360, "target": list(target), "radius": 14.5,
            "height": 5.2, "ortho_scale": camera.data.ortho_scale}


def ensure_stage():
    """Keep the master's approved studio, creating a fallback only if absent."""
    scene = bpy.context.scene
    if any(obj.type == "LIGHT" for obj in scene.objects):
        return "existing_master_studio"
    world = scene.world or bpy.data.worlds.new("motion_off_white_world")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.60, 0.57, 0.51, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.4
    for name, location, power, size, color in (
        ("key", (-4, -6, 9), 1150, 5, (1, 0.90, 0.76)),
        ("fill", (5, -4, 5), 850, 5, (0.78, 0.87, 1)),
        ("rim", (2, 5, 7), 1400, 4, (1, 0.88, 0.66)),
    ):
        light_data = bpy.data.lights.new("motion_"+name, "AREA")
        light_data.energy, light_data.size, light_data.color = power, size, color
        light_data.shape = "DISK"
        light = bpy.data.objects.new("motion_"+name, light_data)
        scene.collection.objects.link(light)
        light.location = location
        light.rotation_mode = "QUATERNION"
        point_at(light, (0, 0, 2.5))
    if not any("ground" in obj.name.lower() for obj in scene.objects if obj.type == "MESH"):
        bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0.035))
        ground = bpy.context.object
        ground.name = "motion_studio_ground"
        material = bpy.data.materials.new("motion_off_white_floor")
        material.use_nodes = True
        principled = material.node_tree.nodes["Principled BSDF"]
        principled.inputs["Base Color"].default_value = (0.730, 0.715, 0.665, 1)
        principled.inputs["Roughness"].default_value = 0.8
        principled.inputs["Emission Color"].default_value = (0.730, 0.715, 0.665, 1)
        principled.inputs["Emission Strength"].default_value = 0.7
        ground.data.materials.append(material)
    scene.view_settings.view_transform = "AgX"
    return "fallback_off_white_studio"


def configure_render(options):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = options.samples
    scene.cycles.use_denoising = True
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.07
    scene.cycles.seed = 17
    scene.cycles.use_animated_seed = False
    scene.cycles.device = "CPU"
    device, note = "CPU", None
    if options.device == "OPTIX":
        try:
            preferences = bpy.context.preferences.addons["cycles"].preferences
            preferences.compute_device_type = "OPTIX"
            preferences.get_devices()
            available = any(candidate.type == "OPTIX" for candidate in preferences.devices)
            if available:
                for candidate in preferences.devices:
                    candidate.use = candidate.type == "OPTIX"
                scene.cycles.device = "GPU"
                device = "OPTIX"
            else:
                note = "OPTIX not available; rendering with Cycles CPU."
        except Exception as exc:
            note = f"OPTIX not available ({type(exc).__name__}); rendering with Cycles CPU."
    scene.render.resolution_x = scene.render.resolution_y = options.resolution
    scene.render.resolution_percentage = 100
    scene.render.fps = options.fps
    scene.render.fps_base = 1.0
    scene.frame_start, scene.frame_end = 1, options.frames
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.render.use_overwrite = False
    scene.render.use_persistent_data = True
    return {"engine": "CYCLES", "device": device, "note": note,
            "samples": options.samples, "resolution": [options.resolution]*2,
            "frames": options.frames, "fps": options.fps,
            "duration_seconds": options.frames/options.fps}


def configure_output(movie):
    scene = bpy.context.scene
    try:
        # Blender 5.2 separates image/video output; older versions lack this.
        if hasattr(scene.render.image_settings, "media_type"):
            scene.render.image_settings.media_type = "VIDEO"
        scene.render.image_settings.file_format = "FFMPEG"
        scene.render.ffmpeg.format = "MPEG4"
        scene.render.ffmpeg.codec = "H264"
        scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
        scene.render.ffmpeg.ffmpeg_preset = "GOOD"
        scene.render.ffmpeg.audio_codec = "NONE"
        scene.render.image_settings.color_mode = "RGB"
        scene.render.filepath = str(movie)
        return "H264_MPEG4", None
    except (TypeError, ValueError, AttributeError) as exc:
        frames = movie.parent/(movie.stem+"-frames")
        if frames.exists() and any(frames.iterdir()):
            raise FileExistsError(f"Frame fallback directory already contains files: {frames}")
        frames.mkdir(parents=True, exist_ok=True)
        if hasattr(scene.render.image_settings, "media_type"):
            scene.render.image_settings.media_type = "IMAGE"
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGBA"
        scene.render.filepath = str(frames/"frame_")
        return "PNG_SEQUENCE", {"directory": str(frames),
                                 "reason": f"Blender FFMPEG unavailable: {type(exc).__name__}: {exc}"}


def verify_movie(movie, expected_frames, resolution, fps):
    clip = bpy.data.movieclips.load(str(movie))
    evidence = {"decoded_size": list(clip.size), "decoded_frames": clip.frame_duration,
                "decoded_fps": clip.fps}
    evidence["passed"] = (list(clip.size) == [resolution, resolution] and
                          clip.frame_duration == expected_frames and abs(clip.fps-fps) < 0.01)
    bpy.data.movieclips.remove(clip)
    if not evidence["passed"]:
        raise RuntimeError(f"Encoded movie metadata mismatch: {evidence}")
    return evidence


def encode_existing_frames(options, movie):
    """Use Blender's own sequencer/FFMPEG to encode without rerendering 3D."""
    directory = Path(options.encode_frames)
    if not directory.is_absolute():
        raise ValueError("--encode-frames must be an absolute path")
    frames = sorted(directory.glob("frame_*.png"))
    if len(frames) != options.frames:
        raise ValueError(f"Expected {options.frames} frames, found {len(frames)}")
    scene = bpy.data.scenes.new("motion_png_encoding")
    bpy.context.window.scene = scene
    editor = scene.sequence_editor_create()
    strips = editor.strips if hasattr(editor, "strips") else editor.sequences
    strip = strips.new_image(name="Rendered Asterion frames", filepath=str(frames[0]), channel=1, frame_start=1)
    for frame in frames[1:]:
        strip.elements.append(frame.name)
    strip.frame_final_duration = options.frames
    scene.render.resolution_x = scene.render.resolution_y = options.resolution
    scene.render.resolution_percentage = 100
    scene.render.fps, scene.render.fps_base = options.fps, 1.0
    scene.frame_start, scene.frame_end = 1, options.frames
    scene.render.use_sequencer = True
    scene.render.use_compositing = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure, scene.view_settings.gamma = 0.0, 1.0
    scene.sequencer_colorspace_settings.name = "sRGB"
    strip.colorspace_settings.name = "sRGB"
    media_format, _ = configure_output(movie)
    if media_format != "H264_MPEG4":
        raise RuntimeError("This Blender build cannot encode a movie; PNG frames remain available")
    bpy.ops.render.render(animation=True)
    if not movie.is_file() or movie.stat().st_size < 4096:
        raise RuntimeError("Blender sequencer did not write a nonempty MPEG4 movie")
    report_path = movie.with_name(movie.stem+"-report.json")
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
    report["movie"] = {"path": str(movie), "bytes": movie.stat().st_size, "sha256": digest(movie)}
    report["media_format"] = "H264_MPEG4"
    report["encoding"] = "Blender internal sequencer and FFMPEG, from preserved rendered PNG frames"
    report["movie_validation"] = verify_movie(movie, options.frames, options.resolution, options.fps)
    report["completed"] = True
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"event": "movie_encoded", "movie": str(movie), "report": str(report_path),
                      "validation": report["movie_validation"]}), flush=True)


def extract_movie_stills(movie, count, resolution, fps):
    """Decode representative movie frames through VSE, without a 3D render."""
    scene = bpy.data.scenes.new("motion_decoded_stills")
    bpy.context.window.scene = scene
    editor = scene.sequence_editor_create()
    strips = editor.strips if hasattr(editor, "strips") else editor.sequences
    strip = strips.new_movie(name="Encoded Asterion movie", filepath=str(movie), channel=1, frame_start=1)
    scene.render.resolution_x = scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.fps, scene.render.fps_base = fps, 1.0
    scene.render.use_sequencer = True
    scene.render.use_compositing = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure, scene.view_settings.gamma = 0.0, 1.0
    scene.sequencer_colorspace_settings.name = "sRGB"
    strip.colorspace_settings.name = "sRGB"
    frames = sorted({1, 13, 1+(count-1)//4, 1+(count-1)//2, 1+3*(count-1)//4, count})
    directory = movie.parent/(movie.stem+"-stills")
    directory.mkdir(parents=True, exist_ok=True)
    captured = []
    for frame in frames:
        path = directory/f"frame_{frame:04d}.png"
        scene.frame_set(frame)
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        captured.append({"frame": frame, "path": str(path), "source": "decoded_H264_movie"})
    return captured


def main():
    options = parse_args()
    if options.frames < 24 or options.fps < 1 or options.samples < 1 or options.resolution < 128:
        raise ValueError("Require frames>=24, fps>=1, samples>=1, resolution>=128")
    output = Path(options.output)
    if not output.is_absolute():
        raise ValueError("--output must be an absolute path")
    movie = output if output.suffix.lower() == ".mp4" else output/"asterion-turntable.mp4"
    movie = movie.resolve()
    if movie.exists() and not options.extract_video:
        raise FileExistsError(f"Choose a new movie destination: {movie}")
    movie.parent.mkdir(parents=True, exist_ok=True)
    if options.extract_video:
        captured = extract_movie_stills(movie, options.frames, options.resolution, options.fps)
        report_path = movie.with_name(movie.stem+"-report.json")
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
        report["representative_stills"] = captured
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"event": "movie_stills_extracted", "report": str(report_path), "stills": captured}), flush=True)
        return
    if options.encode_frames:
        encode_existing_frames(options, movie)
        return
    source = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    if source is None or not source.is_file():
        raise ValueError("Load the release .blend before running this script")
    rigs = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(rigs) != 1:
        raise ValueError(f"Expected one character armature, found {len(rigs)}")
    started = time.monotonic()
    animation = bake_preview_action(rigs[0], options.frames)
    camera = orbit_camera(options.frames)
    stage = ensure_stage()
    render = configure_render(options)
    media_format, fallback = configure_output(movie)
    bpy.context.scene.frame_set(1)
    report = {"source_blend": str(source), "source_sha256": digest(source),
              "blender": bpy.app.version_string, "animation": animation,
              "camera": camera, "stage": stage, "render": render,
              "media_format": media_format, "fallback": fallback,
              "master_saved_or_overwritten": False, "completed": False}
    report_path = movie.with_name(movie.stem+"-report.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"event": "render_started", "destination": str(movie),
                      "media_format": media_format, "render": render}), flush=True)
    bpy.ops.render.render(animation=True)
    if media_format == "H264_MPEG4":
        if not movie.is_file() or movie.stat().st_size < 4096:
            raise RuntimeError("Blender did not write a nonempty MPEG4 movie")
        report["movie"] = {"path": str(movie), "bytes": movie.stat().st_size, "sha256": digest(movie)}
        report["movie_validation"] = verify_movie(movie, options.frames, options.resolution, options.fps)
        report["representative_stills"] = extract_movie_stills(movie, options.frames, options.resolution, options.fps)
    else:
        frames = sorted(Path(fallback["directory"]).glob("frame_*.png"))
        if len(frames) != options.frames:
            raise RuntimeError(f"Expected {options.frames} PNG frames, found {len(frames)}")
        report["png_frames"] = {"count": len(frames), "first": str(frames[0]), "last": str(frames[-1])}
    report["completed"] = True
    report["elapsed_seconds"] = round(time.monotonic()-started, 2)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"event": "render_completed", "report": str(report_path),
                      "media_format": media_format, "elapsed_seconds": report["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    main()

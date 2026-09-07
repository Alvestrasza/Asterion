"""Deterministic 22-bone deformation and delivery for volumetric Asterion.

Coordinates are X lateral (L positive), negative Y forward, Z up.  Call
``build_rig(mesh_objects)`` after all visible geometry has been created, then
``export_glb(path, mesh_objects, rig)``.  Neither function runs on import.

Each mesh uses ``ast_part``: body, neck, head, fore.L/R, hind.L/R, tail,
mane, eye.L/R, lid.L/R, armor.chest, or armor.shoulder.L/R. Unknown ornaments
default to the head. ``ast_bone`` overrides this with one rigid bone name.
Lids are CLOSED cover geometry in the rest pose. ``ast_lid_pivot`` optionally
supplies their world-space center; otherwise their world bounds supply it.
Open lids scale to 0.0001 around that center; closed lids scale to 1.0.
Optional ``ast_lid_open_scale`` is a nonzero 3-vector for a custom open pose.
No other mesh is resized or reprojected by this module.
"""

from __future__ import annotations

from collections import defaultdict
from array import array
from math import acos, atan2, cos, exp, pi, sin, sqrt
from pathlib import Path
import json
import struct
import uuid

import bpy
from mathutils import Quaternion, Vector


FPS = 30
CLIPS = ("idle", "blink", "happy", "eat", "play", "pet_reaction", "sleep", "wake", "walk")
RIG_NAME = "asterion_sculpt_rig"
SIDES = (("L", 1.0), ("R", -1.0))


def _clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def _smooth(low, high, value):
    t = _clamp((value - low) / (high - low))
    return t * t * (3.0 - 2.0 * t)


def _lid_center(objects, side):
    relevant = [o for o in objects if o.get("ast_part") == f"lid.{side}"]
    for obj in relevant:
        if "ast_lid_pivot" in obj:
            return Vector(obj["ast_lid_pivot"])
    if relevant:
        corners = [obj.matrix_world @ Vector(corner) for obj in relevant for corner in obj.bound_box]
        return (Vector(tuple(min(p[i] for p in corners) for i in range(3))) +
                Vector(tuple(max(p[i] for p in corners) for i in range(3)))) * 0.5
    return Vector((0.56 if side == "L" else -0.56, -1.57, 3.7))


def _bones(objects):
    specs = [
        ("root", (0, 0, 0), (0, 0, 0.4), None),
        ("pelvis", (0, 1.0, 1.9), (0, 0.3, 1.9), "root"),
        ("spine", (0, 0.3, 1.9), (0, -0.5, 2.12), "pelvis"),
        ("chest", (0, -0.5, 2.12), (0, -0.85, 2.8), "spine"),
        ("neck", (0, -0.85, 2.8), (0, -1.03, 3.65), "chest"),
        ("head", (0, -1.03, 3.65), (0, -1.68, 3.55), "neck"),
        ("tail.01", (0, 1.45, 2.1), (0, 2.3, 1.45), "pelvis"),
        ("tail.02", (0, 2.3, 1.45), (0, 2.9, 1.0), "tail.01"),
    ]
    for side, sign in SIDES:
        x = 0.65 * sign
        specs.extend([
            (f"fore.upper.{side}", (x, -0.83, 1.9), (x, -0.94, 1.02), "chest"),
            (f"fore.lower.{side}", (x, -0.94, 1.02), (x, -1.18, 0.28), f"fore.upper.{side}"),
            (f"fore.paw.{side}", (x, -1.18, 0.28), (x, -1.46, 0.14), f"fore.lower.{side}"),
            (f"hind.upper.{side}", (x, 0.96, 1.9), (x, 1.27, 1.01), "pelvis"),
            (f"hind.lower.{side}", (x, 1.27, 1.01), (x, 0.88, 0.27), f"hind.upper.{side}"),
            (f"hind.paw.{side}", (x, 0.88, 0.27), (x, 0.60, 0.14), f"hind.lower.{side}"),
        ])
        p = _lid_center(objects, side)
        specs.append((f"lid.{side}", tuple(p), tuple(p + Vector((0, 0, 0.1))), "head"))
    return specs


def _weights(part, position):
    x, y, z = position
    if part == "body":
        # The sculpt is one fused mesh: its paws and neck must deform as their
        # anatomical regions, not inherit the torso merely from ast_part.
        if z > 2.45:
            return _weights("neck", position)
        side = "L" if x >= 0 else "R"
        region = "fore" if y < 0.12 else "hind"
        if z <= 1.25:
            return _weights(f"{region}.{side}", position)
        values = {
            "pelvis": exp(-((y - 0.98) / 0.65) ** 2),
            "spine": exp(-((y - 0.10) / 0.63) ** 2),
            "chest": exp(-((y + 0.75) / 0.60) ** 2),
        }
        total = sum(values.values())
        values = {name: weight / total for name, weight in values.items()}
        # At the low end every vertex belongs to its leg; moving upwards,
        # inner vertices merge into the torso before the outer shoulder mass.
        torso_fraction = _smooth(1.25, 1.95, z)
        lateral_support = _smooth(0.18, 0.58, abs(x))
        side_presence = 1.0 - _smooth(1.25, 1.70, z) * (1.0-lateral_support)
        limb_fraction = (1.0-torso_fraction) * side_presence
        values = {name: weight * (1.0-limb_fraction) for name, weight in values.items()}
        if limb_fraction > 1e-6:
            values[f"{region}.upper.{side}"] = limb_fraction
        # The lower neck emerges above the torso with a continuous chest
        # transition; no weight discontinuity at the neck classification line.
        if z > 2.12:
            neck_fraction = _smooth(2.12, 2.45, z)
            values = {name: weight * (1.0-neck_fraction) for name, weight in values.items()}
            values["chest"] = values.get("chest", 0.0) + neck_fraction
        return values
    if part == "neck":
        head = _smooth(3.28, 3.63, z)
        neck = _smooth(2.50, 2.92, z) * (1.0 - head)
        return {"chest": (1.0 - head) - neck, "neck": neck, "head": head}
    if part.startswith("fore.") or part.startswith("hind."):
        region, side = part.split(".", 1)
        upper = _smooth(0.79, 1.25, z)
        paw = 1.0 - _smooth(0.28, 0.55, z)
        lower = max(0.0, 1.0 - upper - paw)
        return {f"{region}.upper.{side}": upper, f"{region}.lower.{side}": lower,
                f"{region}.paw.{side}": paw}
    if part == "tail":
        tip = _smooth(1.95, 2.58, y)
        return {"tail.01": 1.0 - tip, "tail.02": tip}
    if part.startswith("lid."):
        return {part: 1.0}
    if part == "armor.chest" or part.startswith("armor.shoulder"):
        return {"chest": 1.0}
    if part == "mane":
        return {"head": 1.0}
    return {"head": 1.0}


def _skin(obj, rig):
    part = str(obj.get("ast_part", "head"))
    override = obj.get("ast_bone")
    if override and override not in rig.data.bones:
        raise ValueError(f"Unknown ast_bone {override!r} on {obj.name}")
    buckets = defaultdict(list)
    matrix = obj.matrix_world.copy()
    for vertex in obj.data.vertices:
        values = {override: 1.0} if override else _weights(part, matrix @ vertex.co)
        values = sorted(((name, weight) for name, weight in values.items() if weight > 1e-6),
                        key=lambda item: item[1], reverse=True)[:4]
        total = sum(weight for _, weight in values)
        # Integer weights make grouping fast and guarantee an exact unit sum.
        ticks = [int(round(1000.0 * weight / total)) for _, weight in values]
        ticks[0] += 1000 - sum(ticks)
        for (name, _), tick in zip(values, ticks):
            if tick:
                buckets[(name, tick)].append(vertex.index)
    for name in {name for name, _ in buckets}:
        group = obj.vertex_groups.get(name)
        if group:
            obj.vertex_groups.remove(group)
        obj.vertex_groups.new(name=name)
    for (name, tick), indices in buckets.items():
        obj.vertex_groups[name].add(indices, tick / 1000.0, "REPLACE")
    modifier = obj.modifiers.new("asterion_deformation", "ARMATURE")
    modifier.object = rig
    modifier.use_vertex_groups = True
    modifier.use_deform_preserve_volume = False  # Same linear skinning as glTF.
    obj.parent = rig
    obj.matrix_world = matrix


def _global_rotation(pose_bone, angles):
    q = (Quaternion(Vector((0, 0, 1)), angles[2]) @
         Quaternion(Vector((0, 1, 0)), angles[1]) @
         Quaternion(Vector((1, 0, 0)), angles[0]))
    rest = pose_bone.bone.matrix_local.to_quaternion()
    return rest.inverted() @ q @ rest


def _set_pose(rig, pose, frame):
    for pb in rig.pose.bones:
        values = pose.get(pb.name, {})
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = _global_rotation(pb, values.get("rotation", (0, 0, 0)))
        pb.location = pb.bone.matrix_local.to_3x3().inverted() @ Vector(values.get("location", (0, 0, 0)))
        default_scale = (1, 1, 1)
        if pb.name.startswith("lid."):
            default_scale = rig.get(f"open_scale_{pb.name}", (0.0001, 0.0001, 0.0001))
        pb.scale = values.get("scale", default_scale)
        pb.keyframe_insert(data_path="location", frame=frame, group=pb.name)
        pb.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=pb.name)
        pb.keyframe_insert(data_path="scale", frame=frame, group=pb.name)


def _leg_ik(pose, region, side, stride=0.0, lift=0.0, root_z=0.0):
    """Bake sagittal two-bone IK, with a level paw and fixed ground target."""
    if region == "fore":
        origin, joint, end = (-0.83, 1.9), (-0.94, 1.02), (-1.18, 0.28)
    else:
        origin, joint, end = (0.96, 1.9), (1.27, 1.01), (0.88, 0.27)
    a = (joint[0] - origin[0], joint[1] - origin[1])
    b = (end[0] - joint[0], end[1] - joint[1])
    l1, l2 = sqrt(a[0] ** 2 + a[1] ** 2), sqrt(b[0] ** 2 + b[1] ** 2)
    dy, dz = end[0] + stride - origin[0], end[1] + lift - origin[1] - root_z
    distance2 = dy * dy + dz * dz
    bend = -1.0 if a[0] * b[1] - a[1] * b[0] < 0 else 1.0
    beta = bend * acos(_clamp((distance2 - l1*l1 - l2*l2) / (2*l1*l2), -0.999999, 0.999999))
    alpha = atan2(dz, dy) - atan2(l2 * sin(beta), l1 + l2 * cos(beta))
    upper_delta = alpha - atan2(a[1], a[0])
    lower_delta = alpha + beta - atan2(b[1], b[0]) - upper_delta
    # Normalize to the small physical solution, avoiding +/- 2*pi jumps.
    upper_delta = (upper_delta + pi) % (2*pi) - pi
    lower_delta = (lower_delta + pi) % (2*pi) - pi
    pose[f"{region}.upper.{side}"] = {"rotation": (upper_delta, 0, 0)}
    pose[f"{region}.lower.{side}"] = {"rotation": (lower_delta, 0, 0)}
    pose[f"{region}.paw.{side}"] = {"rotation": (-upper_delta-lower_delta, 0, 0)}


def _lids(pose, amount):
    scale = max(0.0001, amount)
    for side, _ in SIDES:
        pose[f"lid.{side}"] = {"scale": (scale, scale, scale)}


def _pose(clip, t):
    """Continuous formulas use t in [0,1], with exact loop endpoint matches."""
    p = {}
    wave = sin(2*pi*t)
    envelope = sin(pi*t) ** 2
    if clip == "idle":
        p["neck"] = {"rotation": (0.012*wave, 0, 0)}
        p["head"] = {"rotation": (-0.009*wave, 0.012*wave, 0.012*wave)}
        p["tail.01"] = {"rotation": (0, 0, 0.055*wave)}
        p["tail.02"] = {"rotation": (0.025*wave, 0, 0.065*sin(2*pi*t))}
        # Small scale change confined above forelimb attachment.
        p["neck"]["scale"] = (1+0.003*wave, 1+0.004*wave, 1+0.003*wave)
    elif clip == "blink":
        amount = _smooth(0.20, 0.44, t) * (1-_smooth(0.57, 0.86, t))
        _lids(p, amount)
    elif clip in ("happy", "pet_reaction"):
        joy = clip == "happy"
        p["head"] = {"rotation": (-0.07*envelope, 0.08*envelope*wave, 0.065*envelope*wave)}
        p["neck"] = {"rotation": (-0.025*envelope, 0, 0)}
        p["tail.01"] = {"rotation": (0.045*envelope, 0, 0.16*envelope*sin(6*pi*t))}
        p["tail.02"] = {"rotation": (0.045*envelope, 0, 0.21*envelope*sin(6*pi*t-.35))}
        root_z = (0.035 if joy else -0.035) * envelope
        p["root"] = {"location": (0, 0, root_z)}
        for region in ("fore", "hind"):
            for side, _ in SIDES:
                _leg_ik(p, region, side, root_z=root_z)
        if not joy:
            _lids(p, 0.65*envelope)
    elif clip == "eat":
        p["neck"] = {"rotation": (0.18*envelope, 0, 0)}
        p["head"] = {"rotation": (0.12*envelope+0.035*envelope*sin(10*pi*t), 0, 0)}
        p["tail.02"] = {"rotation": (0, 0, 0.045*envelope*wave)}
    elif clip == "play":
        # A restrained invitation to play: crouch, alternating front paw lift.
        root_z = -0.12*envelope
        p["root"] = {"location": (0, 0, root_z)}
        p["head"] = {"rotation": (-0.08*envelope, 0, 0.06*envelope*wave)}
        p["tail.01"] = {"rotation": (0.10*envelope, 0, 0.13*envelope*sin(4*pi*t))}
        p["tail.02"] = {"rotation": (0.05*envelope, 0, 0.20*envelope*sin(4*pi*t-.3))}
        for region in ("fore", "hind"):
            for side, sign in SIDES:
                lift = 0.13*envelope*max(0, sign*wave) if region == "fore" else 0
                _leg_ik(p, region, side, stride=-0.035*envelope if region == "fore" else 0,
                        lift=lift, root_z=root_z)
    elif clip in ("sleep", "wake"):
        settled = 1.0 if clip == "sleep" else 1.0-_smooth(0.18, 0.86, t)
        breathe = 0.007*wave*settled
        root_z = -0.19*settled+breathe
        p["root"] = {"location": (0, 0, root_z)}
        p["neck"] = {"rotation": (0.16*settled, 0, 0)}
        p["head"] = {"rotation": (0.11*settled, 0, 0.06*settled)}
        p["tail.01"] = {"rotation": (0.08*settled, 0, 0.13*settled)}
        p["tail.02"] = {"rotation": (0.07*settled, 0, 0.25*settled)}
        for region in ("fore", "hind"):
            for side, _ in SIDES:
                _leg_ik(p, region, side, root_z=root_z)
        _lids(p, settled)
    elif clip == "walk":
        root_z = 0.008*(1-cos(4*pi*t))
        p["root"] = {"location": (0, 0, root_z)}
        p["neck"] = {"rotation": (0.018*wave, 0, 0)}
        p["head"] = {"rotation": (-0.014*wave, 0, 0)}
        p["tail.01"] = {"rotation": (0, 0, 0.075*wave)}
        p["tail.02"] = {"rotation": (0.025*wave, 0, 0.09*wave)}
        # Four-beat walk: hind L, fore L, hind R, fore R.  No root drift.
        offsets = {("hind", "L"): 0, ("fore", "L"): 0.25,
                   ("hind", "R"): 0.5, ("fore", "R"): 0.75}
        for (region, side), offset in offsets.items():
            phase = 2*pi*(t+offset)
            _leg_ik(p, region, side, stride=0.13*cos(phase),
                    lift=0.075*max(0, sin(phase)) ** 2, root_z=root_z)
    return p


def _action_curves(action):
    if hasattr(action, "fcurves"):
        yield from action.fcurves
    else:
        for layer in action.layers:
            for strip in layer.strips:
                if hasattr(strip, "channelbags"):
                    for bag in strip.channelbags:
                        yield from bag.fcurves


def create_actions(rig):
    durations = {"idle": 121, "blink": 19, "happy": 61, "eat": 91,
                 "play": 81, "pet_reaction": 76, "sleep": 121, "wake": 61, "walk": 49}
    loops = {"idle", "sleep", "walk"}
    rig.animation_data_create()
    result = {}
    for clip in CLIPS:
        if bpy.data.actions.get(clip):
            raise ValueError(f"Action {clip!r} already exists; build in a clean character scene")
        action = bpy.data.actions.new(clip)
        action.use_fake_user = True
        action["asterion_clip"] = clip
        action["loop"] = clip in loops
        action["fps"] = FPS
        rig.animation_data.action = action
        count = durations[clip]
        # Per-frame sampling avoids exporter interpolation/IK differences.
        for frame in range(1, count+1):
            _set_pose(rig, _pose(clip, (frame-1)/(count-1)), frame)
        for curve in _action_curves(action):
            for key in curve.keyframe_points:
                key.interpolation = "LINEAR"
        result[clip] = action
    rig.animation_data.action = result["idle"]
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, durations["idle"]
    scene.frame_set(1)
    rig["animation_clips"] = json.dumps({name: {"frames": durations[name], "loop": name in loops}
                                        for name in CLIPS}, sort_keys=True)
    return result


def build_rig(objects):
    """Skin visible meshes and return one animated 22-bone armature object."""
    objects = [o for o in objects if o.type == "MESH"]
    if not objects:
        raise ValueError("build_rig requires mesh objects")
    if bpy.data.objects.get(RIG_NAME):
        raise ValueError(f"{RIG_NAME} already exists; refusing to duplicate the rig")
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    data = bpy.data.armatures.new(RIG_NAME)
    rig = bpy.data.objects.new(RIG_NAME, data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for name, head, tail, parent in _bones(objects):
        bone = data.edit_bones.new(name)
        bone.head, bone.tail = head, tail
        bone.use_deform = True
        if parent:
            bone.parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.show_in_front = True
    data.display_type = "STICK"
    for side, _ in SIDES:
        custom = next((o.get("ast_lid_open_scale") for o in objects
                       if o.get("ast_part") == f"lid.{side}" and "ast_lid_open_scale" in o), None)
        if custom is not None:
            if len(custom) != 3 or min(custom) <= 0:
                raise ValueError("ast_lid_open_scale must contain three positive values")
            rig[f"open_scale_lid.{side}"] = list(custom)
    for obj in objects:
        _skin(obj, rig)
    create_actions(rig)
    rig["asset_role"] = "deformation_rig"
    rig["coordinate_system"] = "X lateral, negative Y front, Z up"
    rig["bone_count"] = len(data.bones)
    return rig


def _white_eye_attribute(mesh):
    """Make join defaults neutral while preserving the authored eye colors."""
    attribute = mesh.color_attributes.get("AST_eye_color")
    if attribute is None:
        attribute = mesh.color_attributes.new(name="AST_eye_color", type="FLOAT_COLOR", domain="POINT")
        attribute.data.foreach_set("color", array("f", [1.0]) * (len(attribute.data)*4))
    elif attribute.domain != "POINT" or attribute.data_type != "FLOAT_COLOR":
        raise ValueError("AST_eye_color must be a POINT/FLOAT_COLOR attribute before export")
    mesh.color_attributes.active_color_index = list(mesh.color_attributes).index(attribute)
    mesh.color_attributes.render_color_index = mesh.color_attributes.active_color_index


def _unify_material_slots(mesh):
    """Collapse duplicate references without merging visually distinct materials."""
    unique, remap, seen = [], {}, {}
    for index, material in enumerate(mesh.materials):
        pointer = material.as_pointer() if material else None
        if material is None:
            raise ValueError("Delivery geometry has an empty material slot")
        if pointer not in seen:
            seen[pointer] = len(unique)
            unique.append(material)
        remap[index] = seen[pointer]
    indices = array("i", [0])*len(mesh.polygons)
    mesh.polygons.foreach_get("material_index", indices)
    rewritten = array("i", (remap[index] for index in indices))
    mesh.materials.clear()
    for material in unique:
        mesh.materials.append(material)
    mesh.polygons.foreach_set("material_index", rewritten)
    mesh.update()


def _joined_export_copy(objects, rig, collection, token):
    """Bake per-object surface modifiers on copies, then join weighted copies."""
    copies = []
    for source in objects:
        duplicate = source.copy()
        duplicate.data = source.data.copy()
        duplicate.name = "export_copy_"+source.name
        duplicate["ast_export_temporary"] = token
        duplicate.data["ast_export_temporary"] = token
        duplicate.animation_data_clear()
        collection.objects.link(duplicate)
        duplicate.hide_viewport = False
        duplicate.hide_render = False
        duplicate.hide_set(False)
        # Armature deformations stay live and are exported as skinning. Other
        # modifiers must be baked BEFORE join, which keeps only active modifiers.
        bpy.ops.object.select_all(action="DESELECT")
        duplicate.select_set(True)
        bpy.context.view_layer.objects.active = duplicate
        for modifier in duplicate.modifiers:
            if modifier.type == "ARMATURE":
                modifier.show_viewport = False
        for modifier in list(duplicate.modifiers):
            if modifier.type == "ARMATURE":
                if modifier.object != rig:
                    raise ValueError(f"Unexpected armature on {source.name}")
                continue
            if modifier.show_viewport:
                bpy.ops.object.modifier_apply(modifier=modifier.name)
                duplicate.data["ast_export_temporary"] = token
            else:
                duplicate.modifiers.remove(modifier)
        _white_eye_attribute(duplicate.data)
        copies.append(duplicate)
    bpy.ops.object.select_all(action="DESELECT")
    for duplicate in copies:
        duplicate.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    joined = bpy.context.object
    joined.name = "asterion_sculpt_delivery"
    joined["ast_export_temporary"] = token
    joined.data["ast_export_temporary"] = token
    _unify_material_slots(joined.data)
    if joined.data.color_attributes.get("AST_eye_color") is None:
        raise ValueError("Joining delivery copies lost AST_eye_color")
    # Every copied object has the same armature, and join remaps vertex-group
    # indices by their names. Keep exactly one linear-skinning modifier.
    for modifier in list(joined.modifiers):
        joined.modifiers.remove(modifier)
    modifier = joined.modifiers.new("asterion_delivery_deformation", "ARMATURE")
    modifier.object = rig
    modifier.use_vertex_groups = True
    modifier.use_deform_preserve_volume = False
    return joined


def export_glb(path, objects, rig):
    """Export a temporary joined copy and inspect the embedded GLB JSON header.

    Blender's exporter RNA is authoritative for optional Meshopt support.
    The editable original meshes remain separate and untouched in the master.
    Temporary mesh copies reduce draw calls to the number of shared materials;
    skin weights and AST_eye_color survive joining. Copies are removed even on
    failure, and the original animation state is restored. Compression is
    lossless. The destination must not already exist to prevent silent loss.
    """
    destination = Path(path).resolve()
    if destination.exists():
        raise FileExistsError(f"Choose a new versioned destination: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    objects = [obj for obj in objects if obj.type == "MESH"]
    if not objects:
        raise ValueError("Export requires at least one skinned mesh")
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    token = uuid.uuid4().hex
    collection = bpy.data.collections.new("asterion_temporary_export_"+token[:8])
    bpy.context.scene.collection.children.link(collection)
    previous_action = rig.animation_data.action
    previous_slot = getattr(rig.animation_data, "action_slot", None)
    previous_frame = bpy.context.scene.frame_current
    previous_subframe = bpy.context.scene.frame_subframe
    supported = {p.identifier for p in bpy.ops.export_scene.gltf.get_rna_type().properties}
    requested = dict(filepath=str(destination), export_format="GLB", use_selection=True,
                     export_extras=False, export_yup=True, export_apply=True,
                     export_materials="EXPORT", export_image_format="AUTO",
                     export_vertex_color="MATERIAL", export_all_vertex_colors=False,
                     export_animations=True, export_animation_mode="ACTIONS",
                     export_action_filter=False, export_frame_range=False,
                     export_force_sampling=True, export_skins=True,
                     export_def_bones=False, export_rest_position_armature=True,
                     export_optimize_animation_size=True, export_cameras=False,
                     export_lights=False, export_meshopt_compression_enable=True,
                     export_meshopt_extension="EXT_meshopt_compression")
    settings = {key: value for key, value in requested.items() if key in supported}
    try:
        rig.animation_data.action = bpy.data.actions["idle"]
        bpy.context.scene.frame_set(1)
        joined = _joined_export_copy(objects, rig, collection, token)
        bpy.ops.object.select_all(action="DESELECT")
        joined.select_set(True)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.export_scene.gltf(**settings)
    finally:
        # UUID-owned duplicates are the only deletion targets. Original mesh
        # datablocks, materials, rig, and studio objects are never removed.
        for temporary in list(bpy.data.objects):
            if temporary.get("ast_export_temporary") == token:
                bpy.data.objects.remove(temporary, do_unlink=True)
        for mesh in list(bpy.data.meshes):
            if mesh.get("ast_export_temporary") == token and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        bpy.data.collections.remove(collection)
        rig.animation_data.action = previous_action
        if previous_action is not None and previous_slot is not None:
            rig.animation_data.action_slot = previous_slot
        bpy.context.scene.frame_set(previous_frame, subframe=previous_subframe)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects:
            obj.select_set(True)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
    with destination.open("rb") as stream:
        magic, version, length = struct.unpack("<III", stream.read(12))
        chunk_length, chunk_type = struct.unpack("<II", stream.read(8))
        if magic != 0x46546C67 or version != 2 or chunk_type != 0x4E4F534A:
            raise ValueError("Exporter output is not glTF 2.0 binary JSON")
        document = json.loads(stream.read(chunk_length).decode("utf-8"))
    names = [a.get("name") for a in document.get("animations", [])]
    if sorted(names) != sorted(CLIPS):
        raise ValueError(f"Expected exactly nine named clips, exported {names!r}")
    if document.get("cameras") or "KHR_lights_punctual" in document.get("extensions", {}):
        raise ValueError("Editor-only camera or lighting was exported")
    if length != destination.stat().st_size:
        raise ValueError("GLB declared and actual lengths differ")
    if len(document.get("meshes", [])) != 1:
        raise ValueError("Joined delivery should contain exactly one mesh")
    triangles = 0
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            if primitive.get("mode", 4) == 4 and "indices" in primitive:
                triangles += document["accessors"][primitive["indices"]]["count"] // 3
    return {"path": str(destination), "bytes": length, "triangles": triangles,
            "meshes": len(document.get("meshes", [])), "materials": len(document.get("materials", [])),
            "draw_call_estimate": sum(len(mesh.get("primitives", [])) for mesh in document.get("meshes", [])),
            "editable_source_meshes_preserved": len(objects),
            "animations": names, "skins": len(document.get("skins", [])),
            "bones": len(rig.data.bones), "extensions": document.get("extensionsUsed", []),
            "export_settings": settings, "blender_version": bpy.app.version_string}

"""Reference-led local shape edits and an explicit, species-specific outfit map.

Names are used only at authoring time on the sealed v002 scene. Runtime consumers
use exported semantic extras, never names or material colors. Natural markings,
wings, skin, eyes and opaque base clothing belong to the body.
"""
import math
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

NAMES = dict(pony='Caelo', rabbit='Liora', cat='Nyra', dog='Fenn', orc='Brumo', fairy='Selya', elf='Aelira')
EQUIPMENT = {
    'pony': ('anklet_diamond_', 'breast_frame_', 'broad_chamfered_tiara', 'broad_saddle_girth',
        'continuous_fitted_neck_harness', 'curved_blue_saddle_', 'flat_double_anklet_',
        'polygonal_shoulder_shield_', 'saddle_border_star_', 'saddle_main_star_',
        'shield_breast_jewel_', 'shoulder_gold_star_', 'tiara_central_star', 'tiara_diamond_drop_', 'tiara_temple_'),
    'rabbit': ('continuous_rose_neck_harness', 'curved_lavender_saddle_', 'delicate_temple_star_',
        'double_angular_fore_cuff_', 'ear_guard_blade_', 'fitted_lavender_shoulder_',
        'forehead_upper_spark', 'haunch_rose_star_', 'long_breast_pendant_', 'open_fore_cuff_diamond_',
        'open_forehead_diamond', 'rose_body_girth', 'rose_ear_guard_', 'shoulder_lilac_spark_',
        'shoulder_rose_spark_', 'upper_diamond_connector_'),
    'cat': ('angular_cuff_', 'continuous_copper_collar', 'copper_brow_', 'cuff_diamond_',
        'emerald_chest_', 'fitted_teal_shoulder_', 'forehead_copper_star', 'haunch_double_crescent_',
        'hip_spark_', 'lower_pendant_flame_', 'rounded_copper_toe_', 'shoulder_copper_star_',
        'shoulder_teal_star_', 'tail_copper_sweep_', 'upper_emerald_diamond_'),
    'dog': ('ankle_gold_spark_', 'cheek_spark_', 'collar_gold_edge_', 'collar_hanging_tab',
        'collar_star_', 'forehead_long_star', 'forehead_nested_star', 'medallion_',
        'navy_celestial_medallion', 'navy_star_collar'),
    'orc': ('fitted_aubergine_cuirass', 'cuirass_hem', 'cuirass_collar_rim', 'layered_leather_belt',
        'belt_seam_', 'long_front_tabard', 'back_tabard', 'leather_bracer_', 'bracer_bottom_rim_',
        'boot_gaiter_', 'boot_ankle_edge_', 'boot_buckle_', 'topknot_forged_binding', 'chest_star_',
        'belt_star_', 'curved_hip_lamella_', 'hip_lamella_border_', 'fitted_cross_harness_',
        'harness_stitch_', 'forged_pauldron_', 'pauldron_broad_forged_border_', 'pauldron_rivet_',
        'pauldron_star_', 'wrist_fur_', 'boot_fur_'),
    'fairy': ('dress_tier_2_petal_', 'coral_bodice_', 'coral_hair_blossom_', 'shoulder_blossom_',
        'sun_drop_earring_', 'collar_leaf_', 'neck_choker', 'throat_emerald_', 'fitted_waist_belt',
        'heart_waist_emerald_', 'waist_gold_calyx_', 'front_coral_drop_', 'ivory_neckline_',
        'topknot_collar', 'wrist_cuff_', 'wrist_leaf_', 'ankle_band_', 'ankle_emerald_', 'ankle_flower_'),
    'elf': ('wide_leather_belt', 'belt_gilt_stitch_', 'leaf_vambrace_', 'bracer_gilt_',
        'braid_engraved_tie_', 'full_folded_forest_cape', 'connected_cloak_mantle', 'mantle_gold_edge',
        'cape_embroidered_hem', 'cape_gold_selvedge_', 'cape_hem_leaf_', 'cape_margin_leaf_',
        'cape_margin_vine_', 'cloak_clasp_', 'cloak_leaf_star', 'belt_clasp_', 'belt_leaf_star',
        'cuff_gold_stitch_', 'cuff_leaf_', 'vambrace_laurel_', 'boot_buckle_', 'fitted_boot_strap_'),
}
HAIR = {
    'pony': ('AST_Caelo_hair_',),
    'rabbit': ('AST_Liora_fur_',),
    'cat': ('silver_crest_', 'crest_undercoat_', 'cheek_fan_', 'cheek_split_', 'ear_inner_brush_',
            'outer_dark_ruff_', 'haunch_coat_', 'nape_bundle_', 'dark_bib_', 'plume_edge_bundle_'),
    'dog': ('cheek_fluff_', 'crown_flick_', 'ear_flow_', 'ear_root_wisp_', 'haunch_flow_',
            'leg_fluff_', 'nape_flow_', 'cream_bib_'),
    'orc': ('front_swept_lock_', 'low_crown_gather_', 'side_swept_lock_', 'temple_lock_',
            'nape_lock_', 'topknot_plume_', 'topknot_root_bundle'),
    'fairy': ('flowing_face_wave_', 'integrated_lower_curl_', 'overlapping_crown_wave_', 'wrapped_topknot_'),
    'elf': ('parted_crown_', 'swept_hairline_', 'face_framing_curl_', 'secondary_curl_',
            'back_swept_lock_', 'interwoven_plait_', 'braid_tassel_'),
}
NOTES = {
    'pony': 'Fuller, scored sky-blue mane and tail; deeper root-to-ribbon color; shorter rounded lower muzzle.',
    'rabbit': 'Shorter, plumper cheek fans with softer overlapping tips and directional cream-fur relief.',
    'cat': 'Shortened silver cheek blades, fuller crest, darker strand valleys and a less projecting nose/mouth.',
    'dog': 'Plush, directional ear and bib tufts; shorter smile seated on the actual muzzle; natural cream moons retained.',
    'orc': 'Scored, shaded plum hair; separate forged/leather outfit above a complete opaque plum under-tunic and shorts.',
    'fairy': 'Copper hair ribbons with deeper directional relief; softly curled coral petal overlay separated from mint/ivory base dress and biological wings.',
    'elf': 'Layered green hair and braid relief; gently relaxed cape folds with attached embroidery; opaque tunic, trousers and boots retained.',
}


def matches(name, patterns):
    return any(pattern in name for pattern in patterns)


def coordinates(obj):
    points = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', points)
    return points.reshape((-1, 3)).astype(np.float64)


def write(obj, points):
    if not np.isfinite(points).all():
        raise ValueError('Nonfinite refinement: ' + obj.name)
    obj.data.vertices.foreach_set('co', np.asarray(points, dtype=np.float32).ravel())
    obj.data.update()


def refine_lock(obj, kind):
    """Score existing ring topology; never add detached filaments or subdivision."""
    mesh = obj.data
    if not mesh.polygons or len(mesh.polygons[0].vertices) != 4:
        return None
    ids = list(mesh.polygons[0].vertices)
    # Authoring helpers differ only in polygon winding and cap construction.
    sides = max(abs(ids[(i + 1) % 4] - ids[i]) for i in range(4))
    if not 24 <= sides <= 160:
        return None
    caps = len(mesh.vertices) % sides
    if caps not in (0, 2):
        return None
    points = coordinates(obj); original = points.copy()
    rings = (len(points) - caps) // sides
    if rings < 16:
        return None
    p = points[:rings * sides].reshape((rings, sides, 3))
    centers = p.mean(axis=1)
    delta = p - centers[:, None, :]
    t = np.linspace(0, 1, rings)[:, None]
    angle = np.arange(sides)[None, :] * math.tau / sides
    fade = np.sin(math.pi * t) ** .8
    channels = (0.5 + 0.5 * np.cos(7 * angle + .8 * np.sin(t * 4))) ** 5
    plush = kind in ('rabbit', 'dog')
    radial = 1 + (.075 if plush else .045) * fade - (.13 if plush else .17) * channels * fade
    # The blade-like cheek ends are too long in v002. Keep embedded roots fixed.
    shorten = .17 if kind == 'rabbit' and 'cheek_' in obj.name else (
        .14 if kind == 'cat' and matches(obj.name, ('cheek_fan_', 'cheek_split_')) else 0)
    moved_centers = centers - (centers - centers[0]) * (shorten * t ** 1.7)
    p[:] = moved_centers[:, None, :] + delta * radial[:, :, None]
    if caps:
        points[-1] += moved_centers[-1] - centers[-1]
    write(obj, points)
    attribute = mesh.color_attributes.get('AST_eye_color')
    if attribute is not None and attribute.domain == 'POINT':
        colors = np.empty(len(attribute.data) * 4, dtype=np.float32)
        attribute.data.foreach_get('color', colors); colors = colors.reshape((-1, 4))
        gain = (.82 + .23 * fade - .23 * channels * fade + .07 * np.cos(angle - .9) * fade).ravel()
        colors[:rings * sides, :3] *= gain[:, None]
        attribute.data.foreach_set('color', np.clip(colors, 0, 1).ravel())
    return {'name': obj.name, 'vertices': len(points), 'max_displacement': float(np.linalg.norm(points - original, axis=1).max()),
            'operation': 'fitted longitudinal relief, root shading and species-specific silhouette', 'shortening': shorten}


def lower_face(objects, kind):
    if kind not in ('pony', 'cat'):
        return []
    plane, top, strength = (-1.91, 3.03, .20) if kind == 'pony' else (-1.48, 2.36, .24)
    edits = []
    for obj in objects:
        if not (obj.name.endswith('_head') or matches(obj.name, ('smile_', 'nostril_', 'triangular_copper_nose'))):
            continue
        local = coordinates(obj); matrix = np.array(obj.matrix_world)
        points = local @ matrix[:3, :3].T + matrix[:3, 3]
        before = points.copy()
        mask = np.clip((top - points[:, 2]) / .16, 0, 1)
        points[:, 1] += np.maximum(0, plane - points[:, 1]) * strength * mask
        points[:, 0] *= 1 + .035 * mask * np.clip((plane + .1 - before[:, 1]) / .2, 0, 1)
        inverse = np.linalg.inv(matrix)
        write(obj, points @ inverse[:3, :3].T + inverse[:3, 3])
        difference = float(np.linalg.norm(points - before, axis=1).max())
        if difference > 1e-6:
            edits.append({'name': obj.name, 'operation': 'rounder, less projecting lower muzzle', 'max_displacement': difference})
    return edits


def dog_smile(objects):
    head = next(o for o in objects if o.name == 'AST_fenn_v2_head')
    tree = BVHTree.FromPolygons([head.matrix_world @ v.co for v in head.data.vertices], [list(p.vertices) for p in head.data.polygons])
    result = []
    for obj in objects:
        if 'gentle_smile_' not in obj.name:
            continue
        points = coordinates(obj); matrix = obj.matrix_world; inverse = matrix.inverted()
        for index, local in enumerate(points):
            p = matrix @ Vector(local); p.x *= .78
            hit, _, _, _ = tree.ray_cast(Vector((p.x, -4, p.z)), Vector((0, 1, 0)))
            if hit is None:
                raise ValueError('Smile lacks a supporting muzzle surface')
            # Preserve the small original tube cross-section relative to its row.
            p.y = hit.y - .006
            points[index] = inverse @ p
        write(obj, points)
        result.append({'name': obj.name, 'operation': 'shorter surface-seated smile', 'width_factor': .78})
    return result


def cloth_family(objects, kind):
    edits = []
    for obj in objects:
        petal = kind == 'fairy' and 'dress_tier_2_petal_' in obj.name
        cape = kind == 'elf' and matches(obj.name, ('full_folded_forest_cape', 'cape_embroidered_hem',
            'cape_gold_selvedge_', 'cape_hem_leaf_', 'cape_margin_leaf_', 'cape_margin_vine_'))
        if not (petal or cape):
            continue
        p = coordinates(obj); before = p.copy()
        if petal:
            amount = np.clip((1.48 - p[:, 2]) / .48, 0, 1) ** 2
            p[:, :2] *= (1 + .035 * amount[:, None])
            p[:, 2] += .022 * amount
        else:
            amount = np.clip((2.1 - p[:, 2]) / 1.4, 0, 1)
            p[:, 1] += .018 * amount * np.sin(p[:, 0] * 12 + p[:, 2] * 2)
        write(obj, p)
        edits.append({'name': obj.name, 'operation': 'coherent cloth-family relief including attached edging',
                      'max_displacement': float(np.linalg.norm(p - before, axis=1).max())})
    return edits


def orc_underclothes(g, rig):
    source = bpy.data.objects['AST_Brumo_fitted_aubergine_cuirass']
    obj = source.copy(); obj.data = source.data.copy()
    obj.name = 'AST_Brumo_v3_base_under_tunic'
    bpy.context.scene.collection.objects.link(obj)
    points = coordinates(obj); points[:, 0] *= .96; points[:, 1] = .03 + (points[:, 1] - .03) * .94
    write(obj, points)
    g.ASSET.append(obj)
    material = source.data.materials[0].copy(); material.name = 'Brumo_v3_base_cloth'
    bsdf = material.node_tree.nodes.get('Principled BSDF')
    for link in list(bsdf.inputs['Base Color'].links):
        material.node_tree.links.remove(link)
    bsdf.inputs['Base Color'].default_value = g.color('443044')
    obj.data.materials[0] = material
    shorts = g.uv('Brumo_v3_base_shorts', (0, .045, 1.035), (.431, .278, .31), material, 'body', seg=96, rings=64)
    shorts.parent = rig
    group = shorts.vertex_groups.new(name='body'); group.add(list(range(len(shorts.data.vertices))), 1, 'REPLACE')
    modifier = shorts.modifiers.new('Original presentation rig', 'ARMATURE'); modifier.object = rig
    return [obj.name, shorts.name]


def apply(g, rig, kind):
    original = list(g.ASSET)
    edits = []
    for obj in original:
        if matches(obj.name, HAIR[kind]):
            edit = refine_lock(obj, kind)
            if edit:
                edits.append(edit)
    edits += lower_face(original, kind)
    if kind == 'dog':
        edits += dog_smile(original)
    edits += cloth_family(original, kind)
    added = orc_underclothes(g, rig) if kind == 'orc' else []
    groups = {'body': [], 'armor': []}
    for obj in g.ASSET:
        # A family selector ending in '_' includes both its exact root mesh
        # (for example throat_emerald) and its children (gold_bezel, etc.).
        is_equipment = any(pattern in obj.name or obj.name.endswith(pattern.rstrip('_'))
                           for pattern in EQUIPMENT[kind])
        component = 'armor' if is_equipment else 'body'
        if obj.name in added:
            component = 'body'
        groups[component].append(obj)
    if len(edits) < 8:
        raise ValueError('Refinement selection unexpectedly empty: ' + kind)
    return groups, {'notes': NOTES[kind], 'edited_objects': edits, 'added_base_clothing': added,
        'equipment_source_objects': [o.name for o in groups['armor']],
        'body_source_objects': [o.name for o in groups['body']]}

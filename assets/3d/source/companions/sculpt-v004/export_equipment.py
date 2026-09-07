"""Two independently visible, skinned components on each unchanged companion rig.

Reuses the historical temporary-copy and public-extras helpers without changing
their source. The delivery is a local Blender export, not a game-dev package.
"""
from pathlib import Path
import sys
import uuid
import bpy

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'sculpt-v001'))
import common

legacy = common.load_file('modular_export_helpers', common.SOURCE_ROOT / 'asterion' / 'sculpt-v004' / 'export_equipment.py')
CLIPS = common.CLIPS


def extras(kind, component):
    result = {'asterion_component': component, 'asterion_rig': kind + '-rig-v1'}
    if component == 'armor':
        result.update(asterion_equipment_slot='outfit', asterion_equipment_id='ceremonial-gold-v1' if kind == 'asterion' else kind + '-outfit-v1')
    return result


def inspect(document, kind, bones):
    nodes = [n for n in document.get('nodes', []) if 'mesh' in n]
    components = {}
    for component in ('body', 'armor'):
        matches = [n for n in nodes if n.get('extras') == extras(kind, component)]
        if len(matches) == 1:
            node = matches[0]
            primitives = document['meshes'][node['mesh']]['primitives']
            components[component] = {'mesh': node['mesh'], 'skin': node.get('skin'),
                'triangles': sum(document['accessors'][p['indices']]['count'] // 3 for p in primitives),
                'primitives': len(primitives)}
    primitives = [p for m in document.get('meshes', []) for p in m.get('primitives', [])]
    skins = document.get('skins', [])
    def public_only(value):
        if isinstance(value, dict):
            if 'extras' in value and value['extras'] not in (extras(kind, 'body'), extras(kind, 'armor')):
                return False
            return all(public_only(v) for v in value.values())
        return not isinstance(value, list) or all(public_only(v) for v in value)
    triangles = sum(c['triangles'] for c in components.values())
    checks = {
        'two_character_meshes': len(nodes) == len(document.get('meshes', [])) == 2,
        'exact_distinct_components': set(components) == {'body', 'armor'} and
            len({c['mesh'] for c in components.values()}) == 2 and all(c['triangles'] > 0 for c in components.values()),
        'one_original_shared_skin': len(skins) == 1 and len(skins[0]['joints']) == bones and
            len(set(skins[0]['joints'])) == bones and all(n.get('skin') == 0 for n in nodes),
        'nine_original_clips': sorted(a['name'] for a in document.get('animations', [])) == sorted(CLIPS),
        'only_public_extras': public_only(document),
        'skinned_triangle_primitives': bool(primitives) and all(p.get('mode', 4) == 4 and
            'indices' in p and {'POSITION', 'JOINTS_0', 'WEIGHTS_0'} <= set(p['attributes']) for p in primitives),
        'under_40_primitives': 0 < len(primitives) < 40,
        'within_species_triangle_budget': 0 < triangles < (8000000 if kind == 'asterion' else 2000000),
        'self_contained_no_projection': bool(document.get('buffers')) and
            all('uri' not in b for b in document['buffers']) and not document.get('images'),
        'no_editor_stage': not document.get('cameras') and 'KHR_lights_punctual' not in document.get('extensions', {}),
        'meshopt': 'EXT_meshopt_compression' in document.get('extensionsUsed', []),
    }
    return {'checks': checks, 'components': components, 'triangles': triangles,
            'draw_calls': len(primitives), 'materials': len(document.get('materials', [])), 'bones': bones,
            'clips': list(CLIPS), 'compression_lossless': False}


def export(path, kind, groups, rig):
    path = Path(path)
    if path.exists():
        raise FileExistsError('A fresh output destination is required')
    objects = groups['body'] + groups['armor']
    if any(not v for v in groups.values()) or len({o.as_pointer() for o in objects}) != len(objects):
        raise ValueError('Body and equipment must be nonempty and disjoint')
    if any(o.type != 'MESH' for o in objects):
        raise ValueError('Only authored meshes may be exported')
    scene = bpy.context.scene
    action, slot = rig.animation_data.action, rig.animation_data.action_slot
    frame, subframe = scene.frame_current, scene.frame_subframe
    tracks = [(t, t.mute) for t in rig.animation_data.nla_tracks]
    selected, active = list(bpy.context.selected_objects), bpy.context.view_layer.objects.active
    token = uuid.uuid4().hex
    collection = bpy.data.collections.new(kind + '_owned_export_' + token[:8])
    scene.collection.children.link(collection)
    owned_objects, owned_meshes = set(), set()
    try:
        common.activate(rig, bpy.data.actions['idle'], 1)
        for track, _ in tracks:
            track.mute = True
        joined = []
        for component, sources in groups.items():
            obj = common.exporter()._joined_export_copy(sources, rig, collection, token)
            owned_objects.add(obj.as_pointer()); owned_meshes.add(obj.data.as_pointer())
            for owner in (obj, obj.data):
                for key in list(owner.keys()):
                    del owner[key]
            obj.name = kind + '_' + component
            obj.data.name = obj.name + '_geometry'
            for key, value in extras(kind, component).items():
                obj[key] = value
            joined.append(obj)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in joined + [rig]:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = rig
        with legacy._only_public_export_extras():
            result = bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                export_extras=True, export_yup=True, export_apply=True, export_materials='EXPORT',
                export_vertex_color='MATERIAL', export_all_vertex_colors=False,
                export_animations=True, export_animation_mode='ACTIONS', export_action_filter=False,
                export_frame_range=False, export_force_sampling=True, export_skins=True,
                export_def_bones=False, export_rest_position_armature=True, export_optimize_animation_size=True,
                export_cameras=False, export_lights=False, export_meshopt_compression_enable=True,
                export_meshopt_extension='EXT_meshopt_compression')
        if result != {'FINISHED'}:
            raise RuntimeError('Export did not finish')
    finally:
        for obj in list(bpy.data.objects):
            if obj.as_pointer() in owned_objects or obj.get('ast_export_temporary') == token:
                bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in list(bpy.data.meshes):
            if not mesh.users and (mesh.as_pointer() in owned_meshes or mesh.get('ast_export_temporary') == token):
                bpy.data.meshes.remove(mesh)
        bpy.data.collections.remove(collection)
        rig.animation_data.action = action
        if action is not None and slot is not None:
            rig.animation_data.action_slot = slot
        for track, mute in tracks:
            track.mute = mute
        scene.frame_set(frame, subframe=subframe)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selected:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = active
    report = inspect(legacy.read_document(path), kind, len(rig.data.bones))
    report['bytes'] = path.stat().st_size
    report['checks']['within_species_byte_budget'] = report['bytes'] < (80000000 if kind == 'asterion' else 25000000)
    if not all(report['checks'].values()):
        raise ValueError('Export contract failed: ' + repr(report['checks']))
    return report

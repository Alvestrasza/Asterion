"""Export detachable body/outfit nodes on Asterion's unchanged shared rig.

Source meshes remain individually editable. Only owned temporary mesh copies
are joined, sanitized and removed. The exporter extras filter is scoped and
restored; original scene, rig, bone, action and material properties are untouched.
"""
from contextlib import contextmanager
import importlib
import json
from pathlib import Path
import struct
import sys
import uuid

ROOT = Path(__file__).resolve().parent
CLIPS = ('idle', 'blink', 'happy', 'eat', 'play', 'pet_reaction', 'sleep', 'wake', 'walk')
RIG_ID = 'asterion-rig-v1'
OUTFIT_ID = 'ceremonial-gold-v1'
PUBLIC_KEYS = frozenset(('asterion_component', 'asterion_rig',
                         'asterion_equipment_slot', 'asterion_equipment_id'))


def component_extras(component):
    if component not in {'body', 'armor'}:
        raise ValueError('Unknown Asterion component')
    result = {'asterion_component': component, 'asterion_rig': RIG_ID}
    if component == 'armor':
        result.update(asterion_equipment_slot='outfit', asterion_equipment_id=OUTFIT_ID)
    return result


def _public_extras(value):
    if isinstance(value, dict):
        if 'extras' in value:
            extras = value['extras']
            if not isinstance(extras, dict) or not set(extras) <= PUBLIC_KEYS:
                return False
            values = {'asterion_component': {'body', 'armor'}, 'asterion_rig': {RIG_ID},
                      'asterion_equipment_slot': {'outfit'}, 'asterion_equipment_id': {OUTFIT_ID}}
            if any(not isinstance(v, str) or v not in values[key] for key, v in extras.items()):
                return False
        return all(_public_extras(v) for v in value.values())
    if isinstance(value, list):
        return all(_public_extras(v) for v in value)
    return True


def inspect_document(document):
    """Pure JSON acceptance seam, shared by export and independent validation."""
    nodes = document.get('nodes', [])
    mesh_nodes = [(index, node) for index, node in enumerate(nodes) if 'mesh' in node]
    components = {}
    for component in ('body', 'armor'):
        matches = [(i, n) for i, n in mesh_nodes
                   if n.get('extras', {}).get('asterion_component') == component]
        if len(matches) != 1:
            continue
        index, node = matches[0]
        mesh_index = node['mesh']
        if not isinstance(mesh_index, int) or not 0 <= mesh_index < len(document.get('meshes', [])):
            continue
        primitives = document['meshes'][mesh_index].get('primitives', [])
        components[component] = {
            'node': index, 'name': node.get('name'), 'mesh': mesh_index,
            'skin': node.get('skin'), 'extras': node.get('extras'),
            'triangles': sum(document['accessors'][p['indices']]['count'] // 3
                             for p in primitives if 'indices' in p),
            'material_primitives': len(primitives),
            'materials': [document.get('materials', [])[p['material']].get('name')
                          for p in primitives if 'material' in p],
        }
    primitives = [p for mesh in document.get('meshes', []) for p in mesh.get('primitives', [])]
    filters = {}
    for view in document.get('bufferViews', []):
        compression = view.get('extensions', {}).get('EXT_meshopt_compression')
        if compression is not None:
            name = compression.get('filter', 'NONE')
            filters[name] = filters.get(name, 0) + 1
    skins = document.get('skins', [])
    joints = skins[0].get('joints', []) if len(skins) == 1 else []
    names = [a.get('name') for a in document.get('animations', [])]
    checks = {
        'two_character_meshes': len(document.get('meshes', [])) == len(mesh_nodes) == 2,
        'exact_body_armor_nodes': set(components) == {'body', 'armor'} and
            all(components[key]['extras'] == component_extras(key) for key in components),
        'separate_component_geometry': len(components) == 2 and
            len({item['mesh'] for item in components.values()}) == 2 and
            all(item['triangles'] > 0 for item in components.values()),
        'one_shared_22_joint_skin': len(skins) == 1 and len(joints) == len(set(joints)) == 22 and
            all(isinstance(j, int) and 0 <= j < len(nodes) for j in joints) and
            len(mesh_nodes) == 2 and all(node.get('skin') == 0 for _, node in mesh_nodes),
        'exact_nine_named_clips': sorted(names) == sorted(CLIPS),
        'only_public_equipment_extras': _public_extras(document),
        'all_primitives_skinned_triangles': bool(primitives) and all(
            p.get('mode', 4) == 4 and 'indices' in p and
            {'POSITION', 'JOINTS_0', 'WEIGHTS_0'} <= set(p.get('attributes', {})) for p in primitives),
        'under_40_material_primitives': 0 < len(primitives) < 40,
        'self_contained_no_images': bool(document.get('buffers')) and
            all('uri' not in b for b in document['buffers']) and not document.get('images'),
        'no_editor_camera_or_light': not document.get('cameras') and
            'KHR_lights_punctual' not in document.get('extensions', {}),
        'meshopt_compressed': 'EXT_meshopt_compression' in document.get('extensionsUsed', []) and bool(filters),
    }
    return {'checks': checks, 'components': components,
            'triangles': sum(c['triangles'] for c in components.values()),
            'materials': len(document.get('materials', [])), 'clips': names,
            'draw_call_estimate': len(primitives),
            'compression': {'extension': 'EXT_meshopt_compression', 'buffer_view_filters': filters,
                            'KHR_mesh_quantization': 'KHR_mesh_quantization' in document.get('extensionsUsed', []),
                            'lossless_claimed': False,
                            'policy': 'Preserve the historical Blender encoder, including its precision-reducing attribute and quaternion filters. Source actions are compared exactly; imported motion is checked independently against v003.'}}


def read_document(path):
    with Path(path).open('rb') as stream:
        magic, version, length = struct.unpack('<III', stream.read(12))
        size, kind = struct.unpack('<II', stream.read(8))
        if magic != 0x46546C67 or version != 2 or kind != 0x4E4F534A or length != Path(path).stat().st_size:
            raise ValueError('Invalid GLB 2.0 header')
        return json.loads(stream.read(size))


@contextmanager
def _only_public_export_extras():
    # Blender's authoritative generate_extras() consults this module-global
    # membership policy for object, data, scene, bone and material properties.
    # An inverse allowlist avoids deleting/restoring source ID properties.
    extras = importlib.import_module('io_scene_gltf2.blender.com.extras')
    # nodes.py imports BLACK_LIST by value for its unrelated temporary-mesh
    # bookkeeping. Load it before replacing the extras module's policy.
    importlib.import_module('io_scene_gltf2.blender.exp.nodes')
    previous = extras.BLACK_LIST

    class PrivatePropertyPolicy:
        def __contains__(self, key):
            return key not in PUBLIC_KEYS

    extras.BLACK_LIST = PrivatePropertyPolicy()
    try:
        yield
    finally:
        extras.BLACK_LIST = previous


def export_glb(path, body_objects, armor_objects, rig):
    import bpy
    sys.path.insert(0, str(ROOT.parent / 'sculpt-v001'))
    import rig_delivery

    destination = Path(path).resolve()
    if destination.exists():
        raise FileExistsError('Choose a fresh, versioned GLB destination')
    groups = {'body': list(body_objects), 'armor': list(armor_objects)}
    objects = groups['body'] + groups['armor']
    if any(not group for group in groups.values()) or any(o.type != 'MESH' for o in objects):
        raise ValueError('Both body and armor require nonempty mesh-only groups')
    if len({o.as_pointer() for o in objects}) != len(objects):
        raise ValueError('Components must be disjoint and contain each source object once')
    if rig.type != 'ARMATURE' or len(rig.data.bones) != 22 or rig.animation_data is None:
        raise ValueError('Expected the original animated 22-bone armature')
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        raise ValueError('Export must start in Object mode')
    scene = bpy.context.scene
    previous = {'action': rig.animation_data.action,
                'slot': getattr(rig.animation_data, 'action_slot', None),
                'frame': scene.frame_current, 'subframe': scene.frame_subframe,
                'selected': list(bpy.context.selected_objects),
                'active': bpy.context.view_layer.objects.active,
                'tracks': [(t, t.mute) for t in rig.animation_data.nla_tracks]}
    token = uuid.uuid4().hex
    owned_objects, owned_meshes = set(), set()
    supported = {p.identifier for p in bpy.ops.export_scene.gltf.get_rna_type().properties}
    requested = dict(filepath=str(destination), export_format='GLB', use_selection=True,
                     export_extras=True, export_yup=True, export_apply=True,
                     export_materials='EXPORT', export_image_format='AUTO',
                     export_vertex_color='MATERIAL', export_all_vertex_colors=False,
                     export_animations=True, export_animation_mode='ACTIONS',
                     export_action_filter=False, export_frame_range=False,
                     export_force_sampling=True, export_skins=True,
                     export_def_bones=False, export_rest_position_armature=True,
                     export_optimize_animation_size=True, export_cameras=False,
                     export_lights=False, export_meshopt_compression_enable=True,
                     export_meshopt_extension='EXT_meshopt_compression')
    if not {'export_extras', 'export_meshopt_compression_enable', 'export_meshopt_extension'} <= supported:
        raise RuntimeError('This Blender exporter lacks required extras or Meshopt support')
    settings = {key: value for key, value in requested.items() if key in supported}
    collection = bpy.data.collections.new('asterion_owned_export_' + token[:8])
    scene.collection.children.link(collection)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        rig.animation_data.action = bpy.data.actions['idle']
        for track in rig.animation_data.nla_tracks:
            track.mute = True
        scene.frame_set(1)
        joined = []
        for component, sources in groups.items():
            temporary = rig_delivery._joined_export_copy(sources, rig, collection, token)
            owned_objects.add(temporary.as_pointer())
            owned_meshes.add(temporary.data.as_pointer())
            for owner in (temporary, temporary.data):
                for key in list(owner.keys()):
                    del owner[key]
            temporary.name = 'asterion_' + component
            temporary.data.name = 'asterion_' + component + '_geometry'
            for key, value in component_extras(component).items():
                temporary[key] = value
            joined.append(temporary)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in joined:
            obj.select_set(True)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        with _only_public_export_extras():
            result = bpy.ops.export_scene.gltf(**settings)
        if result != {'FINISHED'}:
            raise RuntimeError('Blender export did not finish')
    finally:
        for obj in list(bpy.data.objects):
            if obj.as_pointer() in owned_objects or obj.get('ast_export_temporary') == token:
                bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in list(bpy.data.meshes):
            if mesh.users == 0 and (mesh.as_pointer() in owned_meshes or mesh.get('ast_export_temporary') == token):
                bpy.data.meshes.remove(mesh)
        bpy.data.collections.remove(collection)
        rig.animation_data.action = previous['action']
        if previous['action'] is not None and previous['slot'] is not None:
            rig.animation_data.action_slot = previous['slot']
        for track, muted in previous['tracks']:
            track.mute = muted
        scene.frame_set(previous['frame'], subframe=previous['subframe'])
        bpy.ops.object.select_all(action='DESELECT')
        for obj in previous['selected']:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = previous['active']
    document = read_document(destination)
    evidence = inspect_document(document)
    if not all(evidence['checks'].values()):
        raise ValueError('Equipment export contract failed: ' +
                         ', '.join(key for key, passed in evidence['checks'].items() if not passed))
    return {**evidence, 'bytes': destination.stat().st_size, 'meshes': 2, 'skins': 1,
            'bones': 22, 'animations': evidence['clips'],
            'editable_source_meshes_preserved': len(objects),
            'extensions': document.get('extensionsUsed', []),
            'export_settings': {k: v for k, v in settings.items() if k != 'filepath'},
            'blender_version': bpy.app.version_string}

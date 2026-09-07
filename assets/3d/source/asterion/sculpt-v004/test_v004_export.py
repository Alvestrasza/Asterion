"""Small real-Blender export/state regression, never loads a project master.

Run Blender --background --factory-startup --python this.py -- --output NEW.glb
"""
import argparse
from pathlib import Path
import sys
import bpy

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / 'sculpt-v001'))
import export_equipment as equipment
import rig_delivery


def main(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    source = []
    material = bpy.data.materials.new('smoke_blue')
    material.diffuse_color = (0.02, 0.06, 0.2, 1)
    material['private_source_path'] = 'must-not-leak'
    for index, component in enumerate(('body', 'armor')):
        bpy.ops.mesh.primitive_cube_add(location=(index, 0, 2))
        obj = bpy.context.object
        obj.name = 'smoke_' + component
        obj.data.materials.append(material)
        obj['ast_part'] = 'body' if index == 0 else 'armor.chest'
        obj['private_source_path'] = 'must-not-leak'
        obj.data['private_mesh_tag'] = 'must-not-leak'
        source.append(obj)
    rig = rig_delivery.build_rig(source)
    rig['private_rig_tag'] = 'must-not-leak'
    rig.data.bones['root']['private_bone_tag'] = 'must-not-leak'
    bpy.context.scene['private_scene_tag'] = 'must-not-leak'
    bpy.data.actions['idle']['private_action_tag'] = 'must-not-leak'
    rig.animation_data.action = bpy.data.actions['sleep']
    bpy.context.scene.frame_set(14, subframe=0.5)
    bpy.ops.object.select_all(action='DESELECT')
    source[1].select_set(True)
    bpy.context.view_layer.objects.active = source[1]
    object_names = set(bpy.data.objects.keys())
    mesh_names = set(bpy.data.meshes.keys())
    result = equipment.export_glb(path, [source[0]], [source[1]], rig)
    assert all(result['checks'].values()), result
    assert result['triangles'] == 24, result
    assert rig.animation_data.action.name == 'sleep'
    assert bpy.context.scene.frame_current == 14 and bpy.context.scene.frame_subframe == 0.5
    assert bpy.context.selected_objects == [source[1]]
    assert bpy.context.view_layer.objects.active == source[1]
    assert set(bpy.data.objects.keys()) == object_names
    assert set(bpy.data.meshes.keys()) == mesh_names
    assert source[0]['private_source_path'] == 'must-not-leak'
    assert source[0].data['private_mesh_tag'] == 'must-not-leak'
    assert rig['private_rig_tag'] == 'must-not-leak'
    assert rig.data.bones['root']['private_bone_tag'] == 'must-not-leak'
    assert bpy.data.actions['idle']['private_action_tag'] == 'must-not-leak'
    assert material['private_source_path'] == 'must-not-leak'
    assert bpy.context.scene['private_scene_tag'] == 'must-not-leak'
    assert b'must-not-leak' not in Path(path).read_bytes()
    from io_scene_gltf2.blender.com import extras
    assert isinstance(extras.BLACK_LIST, list), 'Scoped extras policy was not restored'
    original_join = rig_delivery._joined_export_copy
    calls = 0

    def injected_failure(*args):
        nonlocal calls
        calls += 1
        joined = original_join(*args)
        if calls == 2:
            raise RuntimeError('intentional export-copy failure')
        return joined

    failure_path = Path(path).with_stem(Path(path).stem + '-failure')
    rig_delivery._joined_export_copy = injected_failure
    try:
        try:
            equipment.export_glb(failure_path, [source[0]], [source[1]], rig)
        except RuntimeError as error:
            assert str(error) == 'intentional export-copy failure'
        else:
            raise AssertionError('Forced failure did not execute')
    finally:
        rig_delivery._joined_export_copy = original_join
    assert not failure_path.exists()
    assert set(bpy.data.objects.keys()) == object_names
    assert set(bpy.data.meshes.keys()) == mesh_names
    assert rig.animation_data.action.name == 'sleep'
    assert bpy.context.scene.frame_current == 14 and bpy.context.scene.frame_subframe == 0.5
    assert bpy.context.selected_objects == [source[1]]
    assert bpy.context.view_layer.objects.active == source[1]
    assert not any(collection.name.startswith('asterion_owned_export_') for collection in bpy.data.collections)
    original_policy = extras.BLACK_LIST
    try:
        with equipment._only_public_export_extras():
            raise RuntimeError('intentional export-policy failure')
    except RuntimeError:
        pass
    assert extras.BLACK_LIST is original_policy
    print('PASS real equipment export: two nodes, one skin, nine clips, 22 bones, no private extras, exact scene restoration', flush=True)
    print('PASS forced failure: both sanitized/tagged copies cleaned, selection/action restored, no output, extras policy restored', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    main(Path(args.output).resolve())

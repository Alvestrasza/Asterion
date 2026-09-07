"""Independent v004 source-rig, detachable-equipment and fresh-import checks.

Blender --background --factory-startup --python validate_v004.py --
  --source candidate.blend --model candidate.glb --output NEW_DIRECTORY

This never saves an input. Reports use relative paths and input hashes. Source
motion equality is exact; imported motion equality is separately bounded by the
existing nine-sample-per-clip world skin-matrix comparison. Neither proves
collision-free animation, human likeness acceptance or mobile performance.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
BASELINE_SOURCE = ROOT.parent / 'sculpt-v003/asterion-sculpt-v003.blend'
BASELINE_MODEL = REPO / 'public/assets/3d/asterion/asterion-sculpt-v003.glb'


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(source, model, output, resolution=1200, render=True):
    import bpy
    verify = _module('v004_historical_validation', ROOT.parent / 'sculpt-v002/validate_refinement.py')
    geometry_hash = _module('v004_historical_geometry_hash', ROOT.parent / 'sculpt-v003/build_head_study.py').geometry_signature
    equipment = _module('v004_equipment_contract', ROOT / 'export_equipment.py')
    source, model, output = (Path(path).resolve() for path in (source, model, output))
    if source in {BASELINE_SOURCE.resolve(), BASELINE_MODEL.resolve()} or model in {BASELINE_SOURCE.resolve(), BASELINE_MODEL.resolve()}:
        raise ValueError('Candidate paths must not replace the historical source or model')
    if output.exists():
        raise FileExistsError('Choose a fresh validation output directory')
    if resolution < 128:
        raise ValueError('Resolution must be at least 128')
    dependencies = [Path(__file__), ROOT / 'export_equipment.py',
                    ROOT.parent / 'sculpt-v002/validate_refinement.py',
                    ROOT.parent / 'sculpt-v003/build_head_study.py',
                    ROOT.parent / 'sculpt-v001/build_sculpt.py']
    input_hashes = {path: verify.digest(path) for path in
                    (BASELINE_SOURCE, BASELINE_MODEL, source, model, *dependencies)}
    output.mkdir(parents=True)
    print('VALIDATE v003 baseline complete rig/action and tail geometry fingerprints', flush=True)
    bpy.ops.wm.open_mainfile(filepath=str(BASELINE_SOURCE))
    baseline = verify.rig_fingerprint(verify.unique_rig())
    verify.activate(verify.unique_rig(), bpy.data.actions['idle'], 1)
    original_tail = {obj.name: geometry_hash(obj) for obj in bpy.context.scene.objects
                     if obj.get('ast_native_hair') or obj.get('ast_hair_export')}
    print('VALIDATE candidate source component partition, original motion and tail-only native hair', flush=True)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    source_rig = verify.unique_rig()
    candidate = verify.rig_fingerprint(source_rig)
    checks = verify.compare_source(baseline, candidate)
    verify.activate(source_rig, bpy.data.actions['idle'], 1)
    hair = verify.inspect_hair()
    checks.update(hair['checks'])
    candidate_tail = {obj.name: geometry_hash(obj) for obj in bpy.context.scene.objects
                      if obj.get('ast_native_hair') or obj.get('ast_hair_export')}
    source_meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and obj.get('ast_part')]
    partitions = {key: [obj for obj in source_meshes if obj.get('asterion_component') == key]
                  for key in ('body', 'armor')}
    checks.update({
        'native_and_export_tail_geometry_exactly_unchanged': bool(original_tail) and original_tail == candidate_tail,
        'only_tail_hair_remains': {obj.get('ast_hair_group') for obj in bpy.context.scene.objects
                                  if obj.get('ast_native_hair') or obj.get('ast_hair_export')} == {'tail'},
        'all_source_meshes_partitioned_body_or_armor': bool(source_meshes) and
            len(source_meshes) == sum(map(len, partitions.values())) and all(partitions.values()),
        'source_component_contract_tags': bool(source_meshes) and all(
            obj.get('asterion_component') in partitions and
            all(obj.get(key) == value for key, value in
                equipment.component_extras(obj.get('asterion_component')).items()) for obj in source_meshes),
        'source_components_share_original_armature': bool(source_meshes) and all(
            obj.parent == source_rig and sum(mod.type == 'ARMATURE' for mod in obj.modifiers) == 1 and
            all(mod.object == source_rig for mod in obj.modifiers if mod.type == 'ARMATURE') for obj in source_meshes),
    })
    source_partition = {component: sorted(obj.name for obj in objects) for component, objects in partitions.items()}
    print('VALIDATE fresh baseline and candidate GLB import with the same importer', flush=True)
    baseline_rig, baseline_actions, _, _ = verify.fresh_import(BASELINE_MODEL)
    baseline_motion = verify.sample_deformation(baseline_rig, baseline_actions)
    checks['baseline_import_22_bones_nine_clips'] = len(baseline_rig.data.bones) == 22 and set(baseline_actions) == set(verify.CLIPS)
    document = equipment.read_document(model)
    schema = equipment.inspect_document(document)
    checks.update(schema['checks'])
    rig, actions, meshes, helpers = verify.fresh_import(model)
    geometry = verify.inspect_import(meshes, rig)
    motion = verify.compare_motion(baseline_motion, verify.sample_deformation(rig, actions))
    components = {}
    for component in ('body', 'armor'):
        matches = [obj for obj in meshes if obj.get('asterion_component') == component]
        if len(matches) == 1:
            components[component] = {
                'object': matches[0].name, 'geometry': verify.inspect_import(matches, rig),
                'materials': [material.name for material in matches[0].data.materials],
                'extras': {key: matches[0].get(key) for key in equipment.component_extras(component)},
            }
    triangle_evidence = verify.triangle_count_evidence(schema['triangles'], geometry['triangles'])
    checks.update({
        'two_imported_character_meshes': len(meshes) == 2 and set(components) == {'body', 'armor'},
        'imported_components_bound_to_same_armature': len(meshes) == 2 and all(
            sum(mod.type == 'ARMATURE' for mod in obj.modifiers) == 1 and
            all(mod.object == rig for mod in obj.modifiers if mod.type == 'ARMATURE') for obj in meshes),
        '22_imported_bones_nine_clips': len(rig.data.bones) == 22 and set(actions) == set(verify.CLIPS),
        'component_metadata_survives_fresh_import': len(components) == 2 and all(
            data['extras'] == equipment.component_extras(key) for key, data in components.items()),
        'finite_imported_geometry': geometry['nonfinite_vertices'] == geometry['nonfinite_transforms'] == 0,
        'all_imported_vertices_normalized_known_four_weights': all(geometry[key] == 0 for key in
            ('unweighted_vertices', 'invalid_weights', 'unknown_weights', 'over_four_weights')),
        'bounded_importer_triangle_count_difference': triangle_evidence['passed'],
        'imported_motion_unchanged': all(item['passed'] for item in motion.values()),
    })
    report = {
        'schema': 'asterion-v004-equipment-independent-validation-v1',
        'source': source.name, 'model': model.name,
        'source_sha256': input_hashes[source], 'model_sha256': input_hashes[model],
        'baseline_source': BASELINE_SOURCE.relative_to(REPO).as_posix(),
        'baseline_model': BASELINE_MODEL.relative_to(REPO).as_posix(),
        'baseline_source_sha256': input_hashes[BASELINE_SOURCE],
        'baseline_model_sha256': input_hashes[BASELINE_MODEL],
        'dependency_sha256': {path.relative_to(REPO).as_posix(): input_hashes[path] for path in dependencies},
        'blender': bpy.app.version_string, 'bytes': model.stat().st_size,
        'triangles': schema['triangles'], 'geometry': geometry,
        'triangle_count_evidence': triangle_evidence,
        'components': schema['components'], 'imported_components': components,
        'source_partition': source_partition, 'native_groom': hair,
        'tail_geometry_sha256': candidate_tail, 'materials': schema['materials'],
        'draw_call_estimate': schema['draw_call_estimate'], 'compression': schema['compression'], 'clips': list(actions),
        'rest_rig_sha256': candidate['rest_sha256'],
        'actions_sha256': {name: data['sha256'] for name, data in candidate['actions'].items()},
        'source_action_curve_count': sum(data['curve_count'] for data in candidate['actions'].values()),
        'source_action_key_count': sum(data['key_count'] for data in candidate['actions'].values()),
        'motion_comparison': motion,
        'excluded_imported_custom_shape_helpers': sorted(obj.name for obj in helpers),
        'checks': checks, 'renders': {},
        'human_likeness_accepted': False, 'mobile_performance_accepted': False,
    }
    report_path = output / 'validation.json'

    def save():
        report['checks']['all_input_files_unchanged'] = all(verify.digest(path) == digest for path, digest in input_hashes.items())
        report['passed'] = all(report['checks'].values())
        report_path.write_text(json.dumps(verify.plain(report), indent=2, allow_nan=False) + '\n', encoding='utf-8')

    save()
    if render and checks['finite_imported_geometry'] and {'idle', 'blink'} <= set(actions):
        print('RENDER fresh imported model: hero, rear, face, closed blink, and outfit-off hero/side', flush=True)
        views = verify.render_import(output, resolution, rig, actions)
        for name, data in views.items():
            report['renders'][name] = {'file': Path(data['path']).relative_to(output).as_posix(), 'sha256': data['sha256']}
        armor = [obj for obj in meshes if obj.get('asterion_component') == 'armor']
        if len(armor) == 1:
            original_hidden = armor[0].hide_render
            armor[0].hide_render = True
            try:
                verify.activate(rig, actions['idle'], actions['idle'].frame_range[0])
                stage = _module('v004_equipment_review_stage', ROOT.parent / 'sculpt-v001/build_sculpt.py')
                without = output / 'armor-off'
                without.mkdir()
                for name, path in stage.render(bpy.context.scene.camera, without, ['hero', 'side']).items():
                    report['renders']['armor_off_' + name] = {
                        'file': Path(path).relative_to(output).as_posix(), 'sha256': verify.digest(path)}
            finally:
                armor[0].hide_render = original_hidden
        checks['six_independent_import_review_renders'] = len(report['renders']) == 6
    save()
    print(json.dumps({'passed': report['passed'], 'triangles': report['triangles'],
                      'components': list(components), 'report': str(report_path)}, indent=2), flush=True)
    if not report['passed']:
        raise RuntimeError('Independent v004 checks failed: ' + ', '.join(key for key, passed in checks.items() if not passed))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--resolution', type=int, default=1200)
    parser.add_argument('--no-renders', action='store_true', help='Numerical preflight only; not visual acceptance')
    arguments = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    validate(arguments.source, arguments.model, arguments.output, arguments.resolution, not arguments.no_renders)

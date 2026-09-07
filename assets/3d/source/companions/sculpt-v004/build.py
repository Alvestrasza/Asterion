"""Refine, reopen and independently import one immutable preceding companion master.

Writes only to a new review directory. No source animation is authored here.
Separate source and imported checks precede any browser delivery.
"""
import argparse
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT.parent / 'sculpt-v001'))
import common
import export_equipment as equipment
import refinements

VERIFY_PATH = common.SOURCE_ROOT / 'asterion' / 'sculpt-v002' / 'validate_refinement.py'
SIGNATURE_PATH = common.SOURCE_ROOT / 'asterion' / 'sculpt-v003' / 'build_head_study.py'
verify = common.load_file('collection_v3_verify_helpers', VERIFY_PATH)
signatures = common.load_file('collection_v3_signature_helpers', SIGNATURE_PATH)


def rel(path):
    return Path(path).relative_to(REPO).as_posix()


def source_checks(before, after):
    return {'original_rest_rig_unchanged': before['rest_sha256'] == after['rest_sha256'],
        'original_constraints_drivers_unchanged': before['behavior_sha256'] == after['behavior_sha256'],
        'all_original_action_data_unchanged': set(before['actions']) == set(after['actions']) == set(common.CLIPS) and
            all(before['actions'][name]['sha256'] == after['actions'][name]['sha256'] and
                after['actions'][name]['finite_keys'] for name in common.CLIPS),
        'original_frame_rate_unchanged': (before['fps'], before['fps_base']) == (after['fps'], after['fps_base'])}


def eye_signatures(objects):
    return {o.name: signatures.geometry_signature(o) for o in objects
            if 'eye' in o.name.lower() or str(o.get('ast_part', '')).startswith('lid.')}


def fit_camera(g, camera, center, span, view):
    direction = Vector({'hero': (.85, -1.45, .35), 'front': (0, -1, .045),
                        'side': (1, 0, .06), 'rear': (0, 1, .07)}[view]).normalized()
    camera.location = center + direction * max(span) * 3
    g.point_at(camera, center)
    right = Vector((0, 0, 1)).cross(direction).normalized(); up = direction.cross(right).normalized()
    corners = [Vector((x * span.x / 2, y * span.y / 2, z * span.z / 2))
               for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    camera.data.ortho_scale = max(max(abs(p.dot(right)), abs(p.dot(up))) for p in corners) * 2 * 1.12


def render(g, out, kind, objects, armor, source=True):
    out.mkdir()
    scene = bpy.context.scene; camera = scene.camera
    lo, hi = common.bounds(objects); center = (lo + hi) * .5; span = hi - lo
    views = ('hero', 'front', 'side', 'rear', 'body-hero', 'body-side') if source else ('hero', 'rear', 'body-hero', 'blink')
    renders = {}
    rig = verify.unique_rig()
    for view in views:
        verify.activate(rig, bpy.data.actions['blink' if view == 'blink' else 'idle'], 10 if view == 'blink' else 1)
        for obj in armor:
            obj.hide_render = view.startswith('body-')
        fit_camera(g, camera, center, span, 'hero' if view == 'blink' else view.removeprefix('body-'))
        path = out / (kind + '-' + view + '.png')
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        renders[view] = {'file': path.name, 'sha256': verify.digest(path)}
    for obj in armor:
        obj.hide_render = False
    verify.activate(rig, bpy.data.actions['idle'], 1)
    fit_camera(g, camera, center, span, 'hero')
    return renders


def setup_render(resolution, samples):
    scene = bpy.context.scene
    scene.render.resolution_x = scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.cycles.samples = samples; scene.cycles.use_denoising = True
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
    available = [d for d in prefs.devices if d.type == 'OPTIX']
    for device in prefs.devices:
        device.use = device in available
    scene.cycles.device = 'GPU' if available else 'CPU'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', required=True, choices=tuple(refinements.NAMES))
    parser.add_argument('--output', required=True)
    parser.add_argument('--resolution', type=int, default=1200)
    parser.add_argument('--samples', type=int, default=40)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    kind = args.kind; out = Path(args.output).resolve()
    if out.exists():
        raise FileExistsError('Choose a fresh review directory')
    revision = 'sculpt-v005' if kind == 'asterion' else 'sculpt-v004'
    baseline = 'sculpt-v004' if kind == 'asterion' else 'sculpt-v003'
    master = REPO / 'assets/3d/source' / kind / baseline / (kind + '-' + baseline + '.blend')
    model = REPO / 'public/assets/3d' / kind / (kind + '-' + baseline + '.glb')
    reference = (REPO / 'assets/3d/reference/asterion/sculpt-v004/asterion-approved-turnaround.png' if kind == 'asterion'
        else REPO / 'public/assets/companions' / (kind + '.png'))
    dependencies = [ROOT / name for name in ('build.py', 'refinements.py', 'export_equipment.py')] + [
        ROOT.parent / 'sculpt-v001/common.py', VERIFY_PATH, SIGNATURE_PATH,
        common.SOURCE_ROOT / 'asterion/sculpt-v001/build_sculpt.py',
        common.SOURCE_ROOT / 'asterion/sculpt-v001/rig_delivery.py',
        common.SOURCE_ROOT / 'asterion/sculpt-v004/export_equipment.py'] + refinements.dependencies(kind)
    hashes = {rel(p): verify.digest(p) for p in [master, model, reference] + dependencies}
    out.mkdir(parents=True)
    print('LOAD', kind, flush=True)
    bpy.ops.wm.open_mainfile(filepath=str(master))
    bpy.context.preferences.filepaths.save_version = 0
    rig = verify.unique_rig(); verify.activate(rig, bpy.data.actions['idle'], 1)
    original_rig = verify.rig_fingerprint(rig)
    g = common.toolkit(); g.ASSET = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.get('ast_part')]
    g.M = {m.name.removeprefix('AST_'): m for m in bpy.data.materials if m.name.startswith('AST_')}
    original_eyes = eye_signatures(g.ASSET)
    groups, changes = refinements.apply(g, rig, kind)
    for component, objects in groups.items():
        collection = bpy.data.collections.new(refinements.NAMES[kind] + ' | ' + component)
        bpy.context.scene.collection.children.link(collection)
        for obj in objects:
            for previous in list(obj.users_collection):
                previous.objects.unlink(obj)
            collection.objects.link(obj)
            for key, value in equipment.extras(kind, component).items():
                obj[key] = value
    eyes = eye_signatures(g.ASSET)
    if not eyes:
        raise ValueError('Ocular meshes missing after likeness refinement')
    print('EXPORT', kind, len(changes['edited_objects']), 'refined objects', flush=True)
    glb = out / (kind + '-' + revision + '.glb'); blend = out / (kind + '-' + revision + '.blend')
    exported = equipment.export(glb, kind, groups, rig)
    setup_render(args.resolution, args.samples)
    source_views = render(g, out / 'source', kind, g.ASSET, groups['armor'])
    bpy.context.scene['revision'] = revision
    bpy.context.scene['equipment_policy'] = 'Independent outer outfit on original skeleton; complete body and base clothing remain visible.'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print('REOPEN master', kind, flush=True)
    bpy.ops.wm.open_mainfile(filepath=str(blend)); rig = verify.unique_rig()
    verify.activate(rig, bpy.data.actions['idle'], 1)
    candidate_rig = verify.rig_fingerprint(rig)
    checks = source_checks(original_rig, candidate_rig)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.get('ast_part')]
    checks['authored_eyes_survive_source_reopen'] = eyes == eye_signatures(meshes)
    checks['all_source_parts_classified_once'] = len(meshes) == sum(len(changes[k]) for k in ('equipment_source_objects', 'body_source_objects'))
    checks['explicit_editable_equipment_groups'] = all(o.get('asterion_component') in ('body', 'armor') for o in meshes)
    checks['meaningful_geometry_refinement'] = sum(e.get('max_displacement', 0) > .0001 for e in changes['edited_objects']) >= 8
    checks['base_clothing_present'] = all(bpy.data.objects.get(name) is not None and
        bpy.data.objects[name].get('asterion_component') == 'body' for name in changes['added_base_clothing'])
    hair = verify.inspect_hair() if kind == 'asterion' else None
    if hair is not None:
        checks.update(hair['checks'])
    print('FRESH historical import', kind, flush=True)
    old_rig, old_actions, _, _ = verify.fresh_import(model)
    old_motion = verify.sample_deformation(old_rig, old_actions)
    print('FRESH candidate import', kind, flush=True)
    new_rig, actions, imported, _ = verify.fresh_import(glb)
    geometry = verify.inspect_import(imported, new_rig)
    motion = verify.compare_motion(old_motion, verify.sample_deformation(new_rig, actions))
    document = verify.glb_document(glb)
    checks.update(equipment.inspect(document, kind, original_rig['bones'])['checks'])
    checks['within_species_byte_budget'] = glb.stat().st_size < (80000000 if kind == 'asterion' else 25000000)
    checks['finite_imported_geometry'] = geometry['nonfinite_vertices'] == geometry['nonfinite_transforms'] == 0
    checks['valid_normalized_known_weights'] = all(geometry[k] == 0 for k in
        ('unweighted_vertices', 'invalid_weights', 'unknown_weights', 'over_four_weights'))
    count_evidence = verify.triangle_count_evidence(exported['triangles'], geometry['triangles'])
    checks['bounded_importer_triangle_difference'] = count_evidence['passed']
    checks['nine_clips_match_historical_import'] = all(v['passed'] for v in motion.values())
    checks['two_imported_components'] = len(imported) == 2
    armor = [o for o in imported if o.get('asterion_component') == 'armor']
    checks['imported_equipment_metadata'] = len(armor) == 1
    bpy.context.scene.world = bpy.data.worlds.new('Likeness round independent import studio')
    verify.activate(new_rig, actions['idle'], 1)
    common.configure_stage(g, imported, args.resolution, args.samples)
    imported_views = render(g, out / 'import', kind, imported, armor, source=False)
    checks['all_historical_and_builder_inputs_unchanged'] = all(verify.digest(REPO / p) == sha for p, sha in hashes.items())
    report = {'schema': 'asterion-local-modular-companion-v1', 'version': revision, 'kind': kind,
        'name': refinements.NAMES[kind], 'source_sha256': verify.digest(blend), 'model_sha256': verify.digest(glb),
        'reference_sha256': verify.digest(reference), 'reference_input': rel(reference), 'input_sha256': hashes, 'blender': bpy.app.version_string,
        **exported, 'geometry': geometry, 'triangle_count_evidence': count_evidence, 'changes': changes,
        'original_rig': original_rig, 'candidate_rig': candidate_rig, 'motion_comparison': motion,
        'source_views': source_views, 'import_views': imported_views, 'hair_evidence': hair,
        'checks': checks, 'passed': all(checks.values()),
        'human_likeness_accepted': False, 'mobile_performance_accepted': False, 'paid_provider_used': False,
        'projection_used': False, 'ocular_geometry_intentionally_refined': original_eyes != eyes, 'package_status': 'Local hash-checked Blender delivery; no game-dev canonical receipt.',
        'animation_limit': 'Original source curves, keys, handles, rest rig and drivers compared exactly. Fresh GLBs compared at nine normalized times per clip with 2e-4 skin-matrix tolerance. Not a collision or gait acceptance.',
        'likeness_limit': 'Original approved artwork retained. Primary forms intentionally refined; unseen surfaces inferred. No exact 1:1 or human acceptance claim.'}
    (out / 'validation.json').write_text(json.dumps(verify.plain(report), indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'kind': kind, 'passed': report['passed'], 'triangles': exported['triangles'],
        'bytes': exported['bytes'], 'failed': [k for k, v in checks.items() if not v]}), flush=True)
    if not report['passed']:
        raise RuntimeError('Candidate acceptance failed')


if __name__ == '__main__':
    main()

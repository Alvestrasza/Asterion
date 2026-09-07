"""Face-only versioned Blender authoring with immutable-source scope checks."""
import argparse
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import contract
import guards
REPO = contract.REPO
sys.path.insert(0, str(ROOT.parent/'sculpt-v001'))
import common
legacy = common.load_file('face_round_sealed_pipeline', ROOT.parent/'sculpt-v004/build.py')
verify, signatures, equipment = legacy.verify, legacy.signatures, legacy.equipment


def rel(path):
    return Path(path).relative_to(REPO).as_posix()


def render(g, out, kind, objects, armor, frame, views, resolution, samples):
    out.mkdir()
    legacy.setup_render(resolution, samples)
    scene = bpy.context.scene
    camera = scene.camera
    lo, hi = common.bounds(objects)
    full_center, full_span = (lo+hi)*.5, hi-lo
    rig = verify.unique_rig()
    evidence = {}
    for view in views:
        blink = view.startswith('blink')
        when = {'blink-early': 5, 'blink-partial': 7, 'blink-closed': 10}.get(view, 1)
        verify.activate(rig, bpy.data.actions['blink' if blink else 'idle'], when)
        for obj in armor: obj.hide_render = view.startswith('body-')
        facial = view.startswith('face-') or blink
        center = Vector(frame['center']) if facial else full_center
        span = Vector(frame['span']) if facial else full_span
        direction = 'hero' if blink else view.removeprefix('face-').removeprefix('body-')
        legacy.fit_camera(g, camera, center, span, direction)
        path = out/(kind+'-'+view+'.png')
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        evidence[view] = dict(file=path.name, sha256=verify.digest(path), clip='blink' if blink else 'idle', frame=when)
    for obj in armor: obj.hide_render = False
    verify.activate(rig, bpy.data.actions['idle'], 1)
    legacy.fit_camera(g, camera, full_center, full_span, 'hero')
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', required=True, choices=contract.KINDS)
    parser.add_argument('--output', required=True)
    parser.add_argument('--resolution', type=int, default=1200)
    parser.add_argument('--samples', type=int, default=40)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    kind, out = args.kind, Path(args.output).resolve()
    if out.exists(): raise FileExistsError('A fresh private review destination is required')
    if not out.is_relative_to(REPO/'.private/3d-work/companions/sculpt-v005'):
        raise ValueError('Use the fixed private face-review workspace')
    module = common.load_file(kind+'_new_face_module', contract.module_path(kind))
    inputs = contract.input_paths(kind)
    if not set(getattr(module, 'DEPENDENCIES', [])) <= set(inputs):
        raise ValueError('Module dependency missing from fixed input contract')
    hashes = {rel(path): verify.digest(path) for path in inputs}
    version, baseline = contract.revision(kind), contract.baseline(kind)
    master = REPO/f'assets/3d/source/{kind}/{baseline}/{kind}-{baseline}.blend'
    model = REPO/f'public/assets/3d/{kind}/{kind}-{baseline}.glb'
    out.mkdir(parents=True)
    print('LOAD immutable master', kind, baseline, flush=True)
    bpy.ops.wm.open_mainfile(filepath=str(master))
    bpy.context.preferences.filepaths.save_version = 0
    rig = verify.unique_rig()
    verify.activate(rig, bpy.data.actions['idle'], 1)
    original_rig = verify.rig_fingerprint(rig)
    before = guards.snapshot(signatures, verify)
    g = common.toolkit()
    g.ASSET = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.get('ast_part')]
    g.M = {m.name.removeprefix('AST_'): m for m in bpy.data.materials if m.name.startswith('AST_')}
    changes = module.apply(g, rig, kind)
    after = guards.snapshot(signatures, verify)
    scope = guards.scope(before, after, changes)
    if not all(scope['checks'].values()):
        (out/'failed-scope.json').write_text(json.dumps(verify.plain(scope), indent=2), encoding='utf-8')
        raise ValueError('Face-only scope failed: '+str([k for k,v in scope['checks'].items() if not v]))
    groups = {component: [o for o in g.ASSET if o.get('asterion_component') == component] for component in ('body', 'armor')}
    if sum(map(len, groups.values())) != len(g.ASSET): raise ValueError('Unclassified source object')
    for component, objects in groups.items():
        for obj in objects:
            for key, value in equipment.extras(kind, component).items(): obj[key] = value
    changes['body_source_objects'] = [o.name for o in groups['body']]
    changes['equipment_source_objects'] = [o.name for o in groups['armor']]
    face_names = set(changes['face_objects'])-set(changes.get('removed_face_objects', []))
    face_objects = [o for o in g.ASSET if o.name in face_names]
    blink_samples = guards.evaluate_blinks(verify, rig, face_objects)
    glb, blend = out/(kind+'-'+version+'.glb'), out/(kind+'-'+version+'.blend')
    print('EXPORT face candidate', kind, flush=True)
    exported = equipment.export(glb, kind, groups, rig)
    source_views = render(g, out/'source', kind, g.ASSET, groups['armor'], changes['face_frame'],
        ('face-hero','face-front','face-side','blink-early','blink-partial','blink-closed','hero','rear','body-hero'), args.resolution, args.samples)
    bpy.context.scene['revision'] = version
    bpy.context.scene['face_round_scope'] = 'Face only. Nonfacial geometry, materials, original rest rig and all actions preserved.'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print('REOPEN and compare protected sculpture and shaders', kind, flush=True)
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    rig = verify.unique_rig()
    verify.activate(rig, bpy.data.actions['idle'], 1)
    candidate_rig = verify.rig_fingerprint(rig)
    reopened = guards.snapshot(signatures, verify)
    checks = legacy.source_checks(original_rig, candidate_rig)
    checks.update(scope['checks'])
    checks.update(face_geometry_survives_source_reopen=all(reopened['geometry'].get(n)==sha for n,sha in scope['candidate_face_geometry_sha256'].items()),
        all_protected_geometry_survives_source_reopen=all(reopened['geometry'].get(n)==sha for n,sha in scope['protected_geometry_sha256'].items()),
        all_protected_materials_survive_source_reopen=all(reopened['materials'].get(n)==sha for n,sha in scope['protected_material_sha256'].items()),
        finite_evaluated_partial_blinks=all(r['nonfinite_coordinates']==0 and r['evaluated_vertices']>0 for r in blink_samples))
    hair = verify.inspect_hair() if kind == 'asterion' else None
    if hair is not None: checks.update(hair['checks'])
    if not all(checks.values()):
        (out/'failed-reopen.json').write_text(json.dumps(verify.plain(checks), indent=2), encoding='utf-8')
        raise ValueError('Saved-source checks failed: '+str([k for k,v in checks.items() if not v]))
    print('FRESH baseline GLB face views and motion', kind, flush=True)
    old_rig, old_actions, old_meshes, _ = verify.fresh_import(model)
    old_motion = verify.sample_deformation(old_rig, old_actions)
    bpy.context.scene.world = bpy.data.worlds.new('Face comparison studio')
    common.configure_stage(g, old_meshes, args.resolution, args.samples)
    baseline_views = render(g, out/'baseline', kind, old_meshes,
        [o for o in old_meshes if o.get('asterion_component')=='armor'], changes['face_frame'],
        ('face-hero','face-front','face-side'), args.resolution, args.samples)
    print('FRESH candidate GLB face and partial-blink views', kind, flush=True)
    imported_rig, actions, imported, _ = verify.fresh_import(glb)
    geometry = verify.inspect_import(imported, imported_rig)
    motion = verify.compare_motion(old_motion, verify.sample_deformation(imported_rig, actions))
    checks.update(equipment.inspect(verify.glb_document(glb), kind, original_rig['bones'])['checks'])
    checks['within_species_byte_budget'] = glb.stat().st_size < (80000000 if kind=='asterion' else 25000000)
    checks['finite_imported_geometry'] = geometry['nonfinite_vertices'] == geometry['nonfinite_transforms'] == 0
    checks['valid_normalized_known_weights'] = all(geometry[k]==0 for k in ('unweighted_vertices','invalid_weights','unknown_weights','over_four_weights'))
    count_evidence = verify.triangle_count_evidence(exported['triangles'], geometry['triangles'])
    checks['bounded_importer_triangle_difference'] = count_evidence['passed']
    checks['nine_clips_match_historical_import'] = all(m['passed'] for m in motion.values())
    checks['two_imported_components'] = len(imported)==2
    armor = [o for o in imported if o.get('asterion_component')=='armor']
    checks['imported_equipment_metadata'] = len(armor)==1
    bpy.context.scene.world = bpy.data.worlds.new('Face comparison studio')
    common.configure_stage(g, imported, args.resolution, args.samples)
    imported_views = render(g, out/'import', kind, imported, armor, changes['face_frame'],
        ('face-hero','face-front','face-side','blink-early','blink-partial','blink-closed','hero','body-hero'), args.resolution, args.samples)
    checks['six_facial_views_present'] = contract.FACE_VIEWS <= set(source_views) and contract.FACE_VIEWS <= set(imported_views)
    checks['all_historical_and_builder_inputs_unchanged'] = all(verify.digest(REPO/path)==sha for path,sha in hashes.items())
    report = dict(schema='asterion-face-only-v1', kind=kind, name=contract.NAMES[kind], version=version,
        source_sha256=verify.digest(blend), model_sha256=verify.digest(glb), reference_input=contract.reference(kind),
        reference_sha256=hashes[contract.reference(kind)], input_sha256=hashes, blender=bpy.app.version_string,
        **{key:value for key,value in exported.items() if key!='checks'}, geometry=geometry, triangle_count_evidence=count_evidence, changes=changes,
        face_scope=scope, original_rig=original_rig, candidate_rig=candidate_rig,
        motion_comparison=motion, source_blink_samples=blink_samples, source_views=source_views,
        import_views=imported_views, baseline_views=baseline_views, hair_evidence=hair,
        checks=checks, passed=all(checks.values()), human_likeness_accepted=False, mobile_performance_accepted=False,
        paid_provider_used=False, projection_used=False, nonface_unchanged=True,
        package_status='Local hash-checked Blender delivery; no game-dev canonical receipt.',
        animation_limit='Original full action/rest/driver RNA unchanged; nine fresh GLB skin-matrix samples per clip. Original center-scale lids retained; no anatomical closure or collision-free motion claim.',
        likeness_limit='Face-only sculpt interpreted from unchanged original artwork. Hidden angles inferred. Not a 100-percent likeness or human identity acceptance claim.')
    (out/'validation.json').write_text(json.dumps(verify.plain(report), indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps({'kind':kind, 'passed':report['passed'], 'triangles':exported['triangles'], 'bytes':exported['bytes'], 'failed':[k for k,v in checks.items() if not v]}), flush=True)
    if not report['passed']: raise RuntimeError('Face candidate failed acceptance checks')


if __name__ == '__main__': main()

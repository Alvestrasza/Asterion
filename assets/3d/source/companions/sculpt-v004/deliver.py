"""Hash-gated delivery to new revision paths, with the proven staged rollback helper."""
import argparse
import importlib.util
import json
import re
import struct
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
spec = importlib.util.spec_from_file_location('historical_staged_delivery', ROOT.parent / 'sculpt-v002/deliver.py')
staged = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = staged
spec.loader.exec_module(staged)
KINDS = ('asterion', 'pony', 'rabbit', 'cat', 'dog', 'orc', 'fairy', 'elf')
CLIPS = {'idle','blink','happy','eat','play','pet_reaction','sleep','wake','walk'}
CHECKS = {'original_rest_rig_unchanged','original_constraints_drivers_unchanged','all_original_action_data_unchanged',
    'original_frame_rate_unchanged','authored_eyes_survive_source_reopen','all_source_parts_classified_once',
    'explicit_editable_equipment_groups','meaningful_geometry_refinement','base_clothing_present','two_character_meshes',
    'exact_distinct_components','one_original_shared_skin','nine_original_clips','only_public_extras',
    'skinned_triangle_primitives','under_40_primitives','within_species_triangle_budget','self_contained_no_projection',
    'no_editor_stage','meshopt','within_species_byte_budget','finite_imported_geometry','valid_normalized_known_weights',
    'bounded_importer_triangle_difference','nine_clips_match_historical_import','two_imported_components',
    'imported_equipment_metadata','all_historical_and_builder_inputs_unchanged'}
HAIR_CHECKS = {'native_curves_present','at_least_1000_native_strands','native_points_radii_static_finite',
    'matching_native_export_groups','all_native_points_match_export_tube_rings'}


def validate_evidence(report, kind, reference):
    baseline = 'sculpt-v004' if kind == 'asterion' else 'sculpt-v003'
    module = ('asterion/sculpt-v005/likeness.py' if kind == 'asterion' else 'companions/sculpt-v004/' +
        ('equine_lapine.py' if kind in ('pony','rabbit') else 'feline_canine.py' if kind in ('cat','dog') else 'folk.py'))
    inputs = {f'assets/3d/source/{kind}/{baseline}/{kind}-{baseline}.blend',
        f'public/assets/3d/{kind}/{kind}-{baseline}.glb', reference,
        *(f'assets/3d/source/companions/sculpt-v004/{name}' for name in ('build.py','refinements.py','export_equipment.py')),
        'assets/3d/source/companions/sculpt-v001/common.py',
        'assets/3d/source/asterion/sculpt-v002/validate_refinement.py',
        'assets/3d/source/asterion/sculpt-v003/build_head_study.py',
        'assets/3d/source/asterion/sculpt-v001/build_sculpt.py','assets/3d/source/asterion/sculpt-v001/rig_delivery.py',
        'assets/3d/source/asterion/sculpt-v004/export_equipment.py','assets/3d/source/'+module}
    if kind in ('cat','dog'):inputs.add('assets/3d/source/cat/sculpt-v002/nyra_detail.py')
    if set(report.get('input_sha256',{})) != inputs:
        raise ValueError('Required immutable input and builder evidence missing or substituted')
    expected_checks = CHECKS | (HAIR_CHECKS if kind == 'asterion' else set())
    if set(report.get('checks',{})) != expected_checks or not all(v is True for v in report['checks'].values()):
        raise ValueError('Required acceptance checks missing or failed')
    before,after=report.get('original_rig',{}),report.get('candidate_rig',{})
    for key in ('rest_sha256','behavior_sha256'):
        if not re.fullmatch('[A-F0-9]{64}',before.get(key,'')) or before.get(key)!=after.get(key):
            raise ValueError('Original rig fingerprint contradiction')
    bones=22 if kind=='asterion' else 10 if kind in ('orc','elf') else 12 if kind=='fairy' else 13
    if any(r.get('bones')!=bones or r.get('fps')!=30 or r.get('fps_base')!=1 for r in (before,after)):
        raise ValueError('Original rig dimensions or frame-rate contradiction')
    if any(set(r.get('actions',{}))!=CLIPS for r in (before,after)):
        raise ValueError('Original action evidence missing')
    if set(report.get('motion_comparison',{}))!=CLIPS:
        raise ValueError('Fresh motion evidence missing')
    for clip in CLIPS:
        a,b=before['actions'][clip],after['actions'][clip]
        if not re.fullmatch('[A-F0-9]{64}',a.get('sha256','')) or a.get('sha256')!=b.get('sha256'):
            raise ValueError('Original action fingerprint contradiction: '+clip)
        if not a.get('finite_keys') or not b.get('finite_keys') or a.get('curve_count',0)<=0 or a.get('key_count',0)<=0:
            raise ValueError('Incomplete action evidence: '+clip)
        sample=report['motion_comparison'][clip]
        error=sample.get('max_world_skin_matrix_component_error',float('inf'))
        if sample.get('passed') is not True or sample.get('sample_count')!=9 or not 0<=error<=2e-4:
            raise ValueError('Fresh motion evidence contradiction: '+clip)
    if report.get('projection_used') is not False or report.get('human_likeness_accepted') is not False or report.get('mobile_performance_accepted') is not False:
        raise ValueError('Unsupported projection or acceptance claim')


def validate_glb(content, report, kind):
    if len(content)<20 or struct.unpack_from('<4sII',content)!=(b'glTF',2,len(content)):
        raise ValueError('Invalid delivered GLB header')
    length,chunk=struct.unpack_from('<I4s',content,12)
    if chunk!=b'JSON':raise ValueError('Missing GLB document')
    doc=json.loads(content[20:20+length].decode('utf-8'))
    meshes=doc.get('meshes',[]);nodes=[n for n in doc.get('nodes',[]) if 'mesh' in n]
    primitives=[p for m in meshes for p in m.get('primitives',[])]
    count=sum(doc['accessors'][p['indices']]['count']//3 for p in primitives)
    bones=report['original_rig']['bones']
    if len(meshes)!=2 or len(nodes)!=2 or sorted(n.get('extras',{}).get('asterion_component','') for n in nodes)!=['armor','body']:
        raise ValueError('Delivered components contradict evidence')
    if len(doc.get('skins',[]))!=1 or len(doc['skins'][0]['joints'])!=bones or any(n.get('skin')!=0 for n in nodes):
        raise ValueError('Delivered shared skin contradicts evidence')
    if set(a.get('name') for a in doc.get('animations',[]))!=CLIPS or len(doc['animations'])!=9:
        raise ValueError('Delivered clips contradict evidence')
    if count!=report.get('triangles') or len(content)!=report.get('bytes') or len(primitives)!=report.get('draw_calls'):
        raise ValueError('Delivered counts contradict evidence')
    if not 0<count<(8000000 if kind=='asterion' else 2000000) or len(content)>=(80000000 if kind=='asterion' else 25000000):
        raise ValueError('Delivered geometry exceeds species budget')
    if not 0<len(primitives)<40 or doc.get('images') or any('uri' in b for b in doc.get('buffers',[])):
        raise ValueError('Delivered material or self-containment policy failed')


def prepare(work, kind, repo=REPO, *, previous=None, _historical=False):
    work = Path(work).resolve(); repo = Path(repo).resolve()
    if kind not in KINDS:
        raise ValueError('Unknown companion kind')
    revision = 'sculpt-v005' if kind == 'asterion' else 'sculpt-v004'
    report = json.loads((work / 'validation.json').read_text(encoding='utf-8'))
    expected_reference = ('assets/3d/reference/asterion/sculpt-v004/asterion-approved-turnaround.png'
        if kind == 'asterion' else 'public/assets/companions/' + kind + '.png')
    if report.get('reference_input') != expected_reference:
        raise ValueError('The approved reference authority cannot be substituted')
    validate_evidence(report, kind, expected_reference)
    if report['kind'] != kind or report['version'] != revision or report.get('passed') is not True:
        raise ValueError('Candidate is not accepted')
    if not report.get('checks') or not all(v is True for v in report['checks'].values()):
        raise ValueError('Candidate has failed checks')
    if not _historical:
        for name, sha in report['input_sha256'].items():
            path = (repo / name).resolve()
            if not path.is_relative_to(repo) or staged.digest(path) != sha:
                raise ValueError('Historical input or builder changed: ' + name)
    artifacts = []
    def add(path, content):
        path = path.resolve()
        if not path.is_relative_to(repo):
            raise ValueError('Destination outside repository')
        artifacts.append(staged.Artifact(path, content))
    def bound_file(source, target, sha):
        content = source.read_bytes()
        if staged.sha256(content) != sha:
            raise ValueError('Evidence mismatch: ' + source.name)
        add(target, content)
    source_root = repo / 'assets/3d/source' / kind / revision
    review_root = repo / 'assets/3d/reference' / kind / revision
    public = repo / 'public/assets/3d' / kind / (kind + '-' + revision + '.glb')
    master = source_root / (kind + '-' + revision + '.blend')
    validate_glb((work / public.name).read_bytes(), report, kind)
    bound_file(work / public.name, public, report['model_sha256'])
    bound_file(work / master.name, master, report['source_sha256'])
    bound_file(repo / report['reference_input'], review_root / 'original.png', report['reference_sha256'])
    for category in ('source', 'import'):
        expected = {'hero', 'front', 'side', 'rear', 'body-hero', 'body-side'} if category == 'source' else {'hero', 'rear', 'body-hero', 'blink'}
        if set(report[category + '_views']) != expected:
            raise ValueError('Missing required review view')
        for view, item in report[category + '_views'].items():
            path = (work / category / item['file']).resolve()
            if path.parent != work / category:
                raise ValueError('Image outside review directory')
            target = review_root / category / item['file']
            bound_file(path, target, item['sha256'])
            item['file'] = target.relative_to(repo).as_posix()
    # Keep full RNA fingerprints in the private build review, publish their exact
    # digest and curve/key counts without duplicating megabytes of keyframe data.
    for field in ('original_rig', 'candidate_rig'):
        rig = report[field]
        report[field] = {k: rig[k] for k in ('rest_sha256', 'behavior_sha256', 'bones', 'fps', 'fps_base')}
        report[field]['actions'] = {name: {k: a[k] for k in ('sha256', 'curve_count', 'key_count', 'finite_keys', 'frame_range')}
                                   for name, a in rig['actions'].items()}
    validation = review_root / 'validation.json'
    add(validation, staged.json_bytes(report))
    manifest = {k: report[k] for k in ('schema', 'kind', 'name', 'version', 'source_sha256', 'model_sha256',
        'reference_sha256', 'triangles', 'bytes', 'bones', 'clips', 'draw_calls', 'materials', 'components',
        'blender', 'human_likeness_accepted', 'mobile_performance_accepted', 'projection_used',
        'paid_provider_used', 'package_status', 'animation_limit', 'likeness_limit', 'compression_lossless')}
    manifest.update(source=master.relative_to(repo).as_posix(), model=public.relative_to(repo).as_posix(),
        reference=(review_root / 'original.png').relative_to(repo).as_posix(),
        validation=validation.relative_to(repo).as_posix(), validation_sha256=staged.sha256(staged.json_bytes(report)),
        fresh_import_passed=True, animations_unchanged=True, equipment_separate=True,
        input_sha256=report['input_sha256'], renders=report['source_views'], import_renders=report['import_views'],
        notes=report['changes']['notes'], edited_objects=len(report['changes']['edited_objects']))
    add(source_root / 'manifest.json', staged.json_bytes(manifest))
    # A prior private review is an exact overwrite baseline only, never fresh
    # acceptance evidence. It must reproduce every old artifact byte for byte.
    prior = {}
    if previous is not None:
        old = prepare(previous, kind, repo, _historical=True)
        prior = {item.target: item.checksum for item in old.artifacts}
    observed = {}
    for item in artifacts:
        value = staged.existing_hash(item.target)
        if not _historical and value is not None and value != item.checksum and value != prior.get(item.target):
            raise FileExistsError('Different content already exists at new delivery path: ' + str(item.target))
        observed[item.target] = value
    return staged.DeliveryPlan(repo, tuple(artifacts), manifest, observed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', required=True, choices=KINDS)
    parser.add_argument('--input', required=True)
    parser.add_argument('--previous', help='Exact previous private review for a hash-guarded pre-handoff correction')
    args = parser.parse_args()
    manifest = staged.execute_delivery(prepare(args.input, args.kind, previous=args.previous))
    print(json.dumps({k: manifest[k] for k in ('kind', 'triangles', 'bytes', 'model_sha256')}, indent=2))


if __name__ == '__main__':
    main()

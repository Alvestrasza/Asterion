"""Evidence-gated face delivery to new paths; immutable historical artifacts."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import re
import sys
import contract

REPO = contract.REPO
spec = importlib.util.spec_from_file_location('face_round_delivery_helpers', contract.ROOT.parent/'sculpt-v004/deliver.py')
legacy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = legacy
spec.loader.exec_module(legacy)
staged = legacy.staged


def validate_evidence(report, kind):
    if kind not in contract.KINDS: raise ValueError('Unknown companion kind')
    if report.get('schema') != 'asterion-face-only-v1' or report.get('kind') != kind or report.get('version') != contract.revision(kind):
        raise ValueError('Wrong face revision')
    if report.get('reference_input') != contract.reference(kind): raise ValueError('Approved reference authority cannot change')
    inputs = {p.relative_to(REPO).as_posix() for p in contract.input_paths(kind)}
    if set(report.get('input_sha256', {})) != inputs: raise ValueError('Required immutable input evidence missing or substituted')
    checks = contract.CHECKS | (contract.HAIR_CHECKS if kind == 'asterion' else set())
    if set(report.get('checks', {})) != checks or not all(v is True for v in report['checks'].values()):
        raise ValueError('Required face acceptance checks missing or failed')
    if report.get('passed') is not True or report.get('nonface_unchanged') is not True:
        raise ValueError('Candidate not accepted')
    for field in ('projection_used', 'paid_provider_used', 'human_likeness_accepted', 'mobile_performance_accepted'):
        if report.get(field) is not False: raise ValueError('Unsupported production or likeness claim')
    before, after = report['original_rig'], report['candidate_rig']
    bones = 22 if kind=='asterion' else 10 if kind in ('orc','elf') else 12 if kind=='fairy' else 13
    for key in ('rest_sha256', 'behavior_sha256'):
        if not re.fullmatch('[A-F0-9]{64}', before.get(key, '')) or before[key] != after.get(key):
            raise ValueError('Original rig fingerprint contradiction')
    if any(r.get('bones')!=bones or r.get('fps')!=30 or r.get('fps_base')!=1 for r in (before,after)):
        raise ValueError('Original rig dimensions or frame rate contradiction')
    if any(set(r.get('actions', {}))!=contract.CLIPS for r in (before,after)) or set(report.get('motion_comparison', {}))!=contract.CLIPS:
        raise ValueError('Original actions or fresh motion evidence missing')
    for clip in contract.CLIPS:
        a, b = before['actions'][clip], after['actions'][clip]
        if not re.fullmatch('[A-F0-9]{64}',a.get('sha256','')) or a['sha256']!=b.get('sha256'):
            raise ValueError('Original action fingerprint contradiction')
        if any(not r.get('finite_keys') or r.get('key_count',0)<=0 or r.get('curve_count',0)<=0 for r in (a,b)):
            raise ValueError('Incomplete source action evidence')
        sample = report['motion_comparison'][clip]
        if sample.get('passed') is not True or sample.get('sample_count')!=9 or not 0<=sample.get('max_world_skin_matrix_component_error',float('inf'))<=2e-4:
            raise ValueError('Fresh motion evidence contradiction')
    scope = report.get('face_scope', {})
    if scope.get('invalid_face_objects') != [] or scope.get('protected_object_count',0)<20 or scope.get('protected_material_count',0)<1:
        raise ValueError('Incomplete nonface protection evidence')
    if scope.get('original_lid_pivots') != scope.get('candidate_lid_pivots') or len(scope.get('original_lid_pivots', {}))<2:
        raise ValueError('Eyelid pivot contradiction')
    for key, count in (('protected_geometry_sha256',scope['protected_object_count']),('protected_material_sha256',scope['protected_material_count'])):
        values=scope.get(key,{})
        if len(values)!=count or not all(re.fullmatch('[A-F0-9]{64}',sha) for sha in values.values()):
            raise ValueError('Invalid protected source hashes')
    expected_frames=[1,5,7,8,9,10,12,16,24]
    samples=report.get('source_blink_samples',[])
    if [s.get('frame') for s in samples]!=expected_frames or any(s.get('nonfinite_coordinates')!=0 or s.get('evaluated_vertices',0)<=0 for s in samples):
        raise ValueError('Partial blink evaluation evidence missing')


def prepare(work, kind, repo=REPO, *, previous=None, _historical=False):
    work, repo = Path(work).resolve(), Path(repo).resolve()
    if kind not in contract.KINDS: raise ValueError('Unknown companion kind')
    report = json.loads((work/'validation.json').read_text(encoding='utf-8'))
    validate_evidence(report, kind)
    report = copy.deepcopy(report)
    if not _historical:
        for name, sha in report['input_sha256'].items():
            path=(repo/name).resolve()
            if not path.is_relative_to(repo) or staged.digest(path)!=sha:
                raise ValueError('Historical input or builder changed: '+name)
    version=contract.revision(kind)
    source_root=repo/'assets/3d/source'/kind/version
    review_root=repo/'assets/3d/reference'/kind/version
    master=source_root/(kind+'-'+version+'.blend')
    model=repo/'public/assets/3d'/kind/(kind+'-'+version+'.glb')
    artifacts=[]
    def add(target, data):
        target=target.resolve()
        if not target.is_relative_to(repo): raise ValueError('Destination outside repository')
        artifacts.append(staged.Artifact(target,data))
    def bound_file(source,target,sha):
        data=source.read_bytes()
        if staged.sha256(data)!=sha: raise ValueError('Evidence mismatch: '+source.name)
        add(target,data)
    legacy.validate_glb((work/model.name).read_bytes(),report,kind)
    bound_file(work/master.name,master,report['source_sha256'])
    bound_file(work/model.name,model,report['model_sha256'])
    bound_file(repo/report['reference_input'],review_root/'original.png',report['reference_sha256'])
    for category,expected in (('source',contract.SOURCE_VIEWS),('import',contract.IMPORT_VIEWS),('baseline',contract.BASELINE_VIEWS)):
        if set(report[category+'_views'])!=expected: raise ValueError('Missing required facial review view')
        for view,item in report[category+'_views'].items():
            path=(work/category/item['file']).resolve()
            if path.parent!=work/category: raise ValueError('Image outside review directory')
            target=review_root/category/item['file']
            bound_file(path,target,item['sha256'])
            item['file']=target.relative_to(repo).as_posix()
    for field in ('original_rig','candidate_rig'):
        data=report[field]
        report[field]={k:data[k] for k in ('rest_sha256','behavior_sha256','bones','fps','fps_base')}
        report[field]['actions']={name:{k:a[k] for k in ('sha256','curve_count','key_count','finite_keys','frame_range')} for name,a in data['actions'].items()}
    validation=review_root/'validation.json'
    validation_bytes=staged.json_bytes(report)
    add(validation,validation_bytes)
    manifest={k:report[k] for k in ('schema','kind','name','version','source_sha256','model_sha256','reference_sha256',
        'triangles','bytes','bones','clips','draw_calls','materials','components','blender','human_likeness_accepted',
        'mobile_performance_accepted','projection_used','paid_provider_used','package_status','animation_limit','likeness_limit','compression_lossless')}
    manifest.update(source=master.relative_to(repo).as_posix(),model=model.relative_to(repo).as_posix(),
        reference=(review_root/'original.png').relative_to(repo).as_posix(),validation=validation.relative_to(repo).as_posix(),
        validation_sha256=staged.sha256(validation_bytes),input_sha256=report['input_sha256'],
        renders=report['source_views'],import_renders=report['import_views'],baseline_renders=report['baseline_views'],
        face_scope_only=True,nonface_unchanged=True,animations_unchanged=True,equipment_separate=True,fresh_import_passed=True,
        notes=report['changes']['notes'],edited_objects=len(report['changes']['edited_objects']),
        protected_object_count=report['face_scope']['protected_object_count'],protected_material_count=report['face_scope']['protected_material_count'])
    add(source_root/'manifest.json',staged.json_bytes(manifest))
    if len({a.target for a in artifacts})!=len(artifacts): raise ValueError('Duplicate targets')
    prior={}
    if previous is not None:
        old=prepare(previous,kind,repo,_historical=True)
        prior={a.target:a.checksum for a in old.artifacts}
    observed={}
    for item in artifacts:
        actual=staged.existing_hash(item.target)
        if not _historical and actual is not None and actual!=item.checksum and actual!=prior.get(item.target):
            raise FileExistsError('Different existing content: '+str(item.target))
        observed[item.target]=actual
    return staged.DeliveryPlan(repo,tuple(artifacts),manifest,observed)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind',required=True,choices=contract.KINDS)
    parser.add_argument('--input',required=True)
    parser.add_argument('--previous')
    args=parser.parse_args()
    result=staged.execute_delivery(prepare(args.input,args.kind,previous=args.previous))
    print(json.dumps({k:result[k] for k in ('kind','triangles','bytes','model_sha256')},indent=2))


if __name__=='__main__':main()

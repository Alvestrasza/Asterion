"""Hash-bound, preflighted local Asterion v002 delivery; never replace v001."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[4]
SHARED=REPO/'assets/3d/source/companions/sculpt-v002/deliver.py'
spec=importlib.util.spec_from_file_location('asterion_staged_delivery',SHARED)
staging=importlib.util.module_from_spec(spec);sys.modules[spec.name]=staging;spec.loader.exec_module(staging)


def prepare(work):
    work=Path(work).resolve();cache={};items=[]
    def read(path):
        path=Path(path).resolve()
        if path not in cache:cache[path]=path.read_bytes()
        return cache[path]
    def add(target,content):
        target=Path(target).resolve()
        if not target.is_relative_to(REPO):raise ValueError('Target outside repository')
        items.append(staging.Artifact(target,content))
    def local_image(path,target):
        source=Path(path).resolve()
        if not source.is_relative_to(work):raise ValueError('Evidence image outside review directory')
        add(target,read(source))
    def digest(path):return staging.sha256(read(path))
    report=json.loads(read(work/'build-report.json'))
    check=json.loads(read(work/'validation/refinement-validation.json'))
    export=json.loads(read(work/'export-report.json'))
    master=work/'asterion-sculpt-v002.blend';glb=work/'asterion-sculpt-v002.glb'
    source_hash=digest(master);model_hash=digest(glb)
    reference=REPO/'assets/3d/reference/asterion/sculpt-v001/asterion-approved-turnaround.png'
    baseline=ROOT.parent/'sculpt-v001/asterion-sculpt-v001.blend'
    baseline_glb=REPO/'public/assets/3d/asterion/asterion-sculpt-v001.glb'
    if check.get('passed') is not True or not check.get('checks') or not all(v is True for v in check['checks'].values()):
        raise ValueError('Independent checks must all pass')
    if source_hash!=report['source_sha256'] or source_hash!=check['master_sha256']:raise ValueError('Master evidence mismatch')
    if model_hash!=report['model_sha256'] or model_hash!=check['glb_sha256']:raise ValueError('GLB evidence mismatch')
    if digest(baseline)!=report['baseline_master_sha256'] or digest(baseline)!=check['baseline_sha256']:raise ValueError('Original master changed')
    if digest(baseline_glb)!=check['baseline_glb_sha256']:raise ValueError('Original motion-calibration GLB changed')
    if digest(reference)!=report['reference_sha256']:raise ValueError('Approved reference changed')
    if report.get('geometry_preview_only') or report.get('animations_unchanged') is not True:raise ValueError('Incomplete source build')
    if not 4500000<=export['triangles']<=5500000:raise ValueError('Five-million delivery budget failed')
    if export['triangles']!=report['triangles'] or export['triangles']!=check['triangle_count_evidence']['authored']:
        raise ValueError('Triangle evidence disagrees')
    if export['bytes']!=len(read(glb)) or set(export['animations'])!=set(check['candidate_fingerprint']['actions']):
        raise ValueError('Export metadata disagrees with independently checked source')
    if not report.get('builder_sha256'):raise ValueError('Missing builder evidence')
    if set(report['renders'])!={'hero','front','side','rear','face'}:raise ValueError('Five source views required')
    if set(check['renders'])!={'hero','rear','face','closed_blink_front'}:raise ValueError('Four independent import views required')
    for name,sha in report['builder_sha256'].items():
        dependency=(REPO/name).resolve()
        if not dependency.is_relative_to(REPO) or digest(dependency)!=sha:raise ValueError('Builder changed: '+name)
    if digest(ROOT/'validate_refinement.py')!=check['validator_sha256']:raise ValueError('Validator changed after evidence run')
    public=REPO/'public/assets/3d/asterion/asterion-sculpt-v002.glb'
    source=ROOT/'asterion-sculpt-v002.blend';review=REPO/'assets/3d/reference/asterion/sculpt-v002'
    rel=lambda path:path.relative_to(REPO).as_posix()
    add(public,read(glb));add(source,read(master));add(review/'asterion-approved-turnaround.png',read(reference))
    source_renders={}
    for name,path in report['renders'].items():
        target=review/Path(path).name;local_image(path,target);source_renders[name]=rel(target)
    clean=dict(check);clean['master']=rel(source);clean['glb']=rel(public);clean['baseline']=rel(baseline)
    clean['baseline_glb']=rel(baseline_glb);clean['renders']={}
    for name,item in check['renders'].items():
        target=review/'import-review'/('asterion-'+name+'.png')
        local_image(item['path'],target)
        if digest(item['path'])!=item['sha256']:raise ValueError('Import render changed')
        clean['renders'][name]={'path':rel(target),'sha256':item['sha256']}
    validation_path=review/'refinement-validation.json'
    add(validation_path,staging.json_bytes(clean))
    clean_build=dict(report);clean_build['renders']=source_renders
    add(ROOT/'build-report.json',staging.json_bytes(clean_build))
    clean_export=dict(export);clean_export['path']=rel(public)
    clean_export['export_settings']=dict(export['export_settings'],filepath=rel(public))
    add(ROOT/'export-report.json',staging.json_bytes(clean_export))
    manifest={'schema':'asterion-local-reference-refinement-v2','name':'Asterion','kind':'asterion','version':'sculpt-v002',
        'source':rel(source),'model':rel(public),'reference':rel(review/'asterion-approved-turnaround.png'),
        'source_sha256':source_hash,'model_sha256':model_hash,'reference_sha256':digest(reference),
        'baseline_master_sha256':digest(baseline),'builder_sha256':report['builder_sha256'],
        'baseline_glb_sha256':digest(baseline_glb),
        'validation':rel(validation_path),'validator_sha256':check['validator_sha256'],
        'triangles':export['triangles'],'imported_triangles':check['geometry']['triangles'],
        'bytes':len(read(glb)),'vertices':check['geometry']['vertices'],'materials':export['materials'],
        'bones':22,'clips':export['animations'],'editable_solid_meshes':check['editable_solid_meshes'],
        'native_hair':True,'hair_strands':check['native_groom']['native_strands'],
        'hair_points':check['native_groom']['native_points'],'hair_physics':False,'animations_unchanged':True,
        'source_action_sha256':{k:v['sha256'] for k,v in check['candidate_fingerprint']['actions'].items()},
        'rig_rest_sha256':check['candidate_fingerprint']['rest_sha256'],
        'human_likeness_accepted':False,'mobile_performance_accepted':False,'paid_provider_used':False,
        'provenance':'Locally refined from existing sculpt-v001 and unchanged user-approved four-view turnaround.',
        'hair_delivery':'Native Blender CURVES retained; matching static tube meshes exported to GLB. No physics or new actions.',
        'license':'Project-controlled user reference; no new third-party distribution license granted.',
        'renders':source_renders,'blender':report['blender']}
    add(ROOT/'manifest.json',staging.json_bytes(manifest))
    if len({i.target for i in items})!=len(items):raise ValueError('Duplicate delivery targets')
    observed={}
    for item in items:
        current=staging.existing_hash(item.target)
        if current is not None and current!=item.checksum:raise FileExistsError('Different existing artifact: '+str(item.target))
        observed[item.target]=current
    return staging.DeliveryPlan(REPO,tuple(items),manifest,observed)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',required=True)
    args=parser.parse_args();result=staging.execute_delivery(prepare(args.input))
    print(json.dumps({k:result[k] for k in ('model','triangles','bytes','hair_strands','animations_unchanged')},indent=2))


if __name__=='__main__':main()

"""Stage only the validated v004 source, GLB and hash-bound review artifacts."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[4]


def deliver(candidate,validation_dir):
    shared=REPO/'assets/3d/source/companions/sculpt-v002/deliver.py'
    spec=importlib.util.spec_from_file_location('v004_staging',shared)
    stage=importlib.util.module_from_spec(spec);sys.modules[spec.name]=stage;spec.loader.exec_module(stage)
    build=json.loads((candidate/'build-report.json').read_text(encoding='utf-8'))
    validation=json.loads((validation_dir/'validation.json').read_text(encoding='utf-8'))
    for report in (build,validation):
        if report.get('passed') is not True or not report.get('checks') or not all(v is True for v in report['checks'].values()):
            raise ValueError('All measured checks must pass')
    if build.get('preview_only') is not False or len(build['renders'])!=7 or len(validation['renders'])!=6:
        raise ValueError('Complete source and independent import reviews required')
    dependencies={**build['input_sha256'],**validation['dependency_sha256']}
    for path,digest in dependencies.items():
        resolved=(REPO/path).resolve()
        if not resolved.is_relative_to(REPO) or stage.sha256(resolved.read_bytes())!=digest:
            raise ValueError('Source or dependency changed: '+path)
    for key in ('source_sha256','model_sha256'):
        if build[key]!=validation[key]:raise ValueError('Build and validation differ')
    for path,key in ((validation['baseline_source'],'baseline_source_sha256'),(validation['baseline_model'],'baseline_model_sha256')):
        resolved=(REPO/path).resolve()
        if not resolved.is_relative_to(REPO) or stage.sha256(resolved.read_bytes())!=validation[key]:
            raise ValueError('Historical baseline changed')
    items=[]
    def rel(path):return path.relative_to(REPO).as_posix()
    def add(target,content):
        if not target.resolve().is_relative_to(REPO):raise ValueError('Target outside repository')
        items.append(stage.Artifact(target,content))
    master=ROOT/'asterion-sculpt-v004.blend'
    model=REPO/'public/assets/3d/asterion/asterion-sculpt-v004.glb'
    for target,key in ((master,'source_sha256'),(model,'model_sha256')):
        content=(candidate/target.name).read_bytes()
        if stage.sha256(content)!=build[key]:raise ValueError('Validated bytes changed')
        add(target,content)
    review=REPO/'assets/3d/reference/asterion/sculpt-v004'
    def transfer_renders(report,origin,destination):
        clean=dict(report);clean['renders']={}
        for name,item in report['renders'].items():
            source=(origin/item['file']).resolve()
            if not source.is_relative_to(origin):raise ValueError('Render outside review')
            content=source.read_bytes()
            if stage.sha256(content)!=item['sha256']:raise ValueError('Review render changed')
            target=destination/item['file'];add(target,content)
            clean['renders'][name]={'file':rel(target),'sha256':item['sha256']}
        return clean
    clean_build=transfer_renders(build,candidate,review)
    clean_validation=transfer_renders(validation,validation_dir,review/'import-review')
    clean_validation['source']=rel(master);clean_validation['model']=rel(model)
    build_path=ROOT/'build-report.json';validation_path=review/'validation.json'
    add(build_path,stage.json_bytes(clean_build));add(validation_path,stage.json_bytes(clean_validation))
    reference=REPO/'assets/3d/reference/asterion/sculpt-v003/asterion-approved-turnaround.png'
    new_reference=review/reference.name;add(new_reference,reference.read_bytes())
    builders={**build['builder_sha256'],**validation['dependency_sha256'],
        rel(Path(__file__)):stage.sha256(Path(__file__).read_bytes()),rel(shared):stage.sha256(shared.read_bytes())}
    manifest={'schema':'asterion-modular-sculpt-v004','version':'sculpt-v004','name':'Asterion','kind':'asterion',
        'source':rel(master),'model':rel(model),'reference':rel(new_reference),
        'source_sha256':build['source_sha256'],'model_sha256':build['model_sha256'],
        'reference_sha256':stage.sha256(reference.read_bytes()),'builder_sha256':builders,
        'build_report':rel(build_path),'validation':rel(validation_path),
        'triangles':validation['triangles'],'vertices':validation['geometry']['vertices'],'bytes':validation['bytes'],
        'meshes':2,'skins':1,'bones':22,'materials':validation['materials'],
        'material_primitives':validation['draw_call_estimate'],'components':validation['components'],
        'equipment_slot':'outfit','equipment_id':'ceremonial-gold-v1','rig_contract':'asterion-rig-v1',
        'clips':validation['clips'],'animations_unchanged':True,'head_hair_removed':True,
        'tail_hair_strands':validation['native_groom']['native_strands'],'hair_physics':False,
        'compression':validation['compression'],'human_likeness_accepted':False,'mobile_performance_accepted':False,
        'provenance':'Local v003 copy: rounded muzzle, skin-fitted dorsal plates, separate authored armor outfit; no external generation or animation redesign.'}
    add(ROOT/'manifest.json',stage.json_bytes(manifest))
    if len({item.target for item in items})!=len(items):raise ValueError('Duplicate destinations')
    observed={}
    for item in items:
        current=stage.existing_hash(item.target)
        if current is not None and current!=item.checksum:raise FileExistsError('Conflicting existing artifact: '+rel(item.target))
        observed[item.target]=current
    stage.execute_delivery(stage.DeliveryPlan(REPO,tuple(items),manifest,observed))
    print(json.dumps({'model':manifest['model'],'triangles':manifest['triangles'],'components':list(manifest['components'])},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',required=True);parser.add_argument('--validation',required=True)
    args=parser.parse_args()
    deliver(Path(args.candidate).resolve(),Path(args.validation).resolve())

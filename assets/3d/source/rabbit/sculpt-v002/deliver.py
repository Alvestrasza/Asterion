"""Hash-checked Liora v002 handoff into new, versioned local asset paths.

Run only after build.py, shared validate_collection.py and inspect_motion.py.
Existing, different files are refused; earlier released versions are untouched.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[4]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def copy(source,target,previous=None):
    if target.exists() and digest(source)!=digest(target):
        if previous is None or not previous.is_file() or digest(target)!=digest(previous):
            raise FileExistsError('Existing different delivery: '+str(target))
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    if digest(source)!=digest(target):raise ValueError('Copy checksum failed')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True)
    p.add_argument('--previous',help='Exact previous private review, only for hash-guarded pre-handoff corrections')
    args=p.parse_args();work=Path(args.input).resolve()
    previous=Path(args.previous).resolve() if args.previous else None
    def deliver(file,target):
        old=previous/file.relative_to(work) if previous and file.is_relative_to(work) else None
        copy(file,target,old)
    report=json.loads((work/'build-report.json').read_text())
    check=json.loads((work/'validation'/'import-validation.json').read_text())
    motion=json.loads((work/'motion'/'motion-inspection.json').read_text())
    glb=work/'rabbit-sculpt-v002.glb';blend=work/'rabbit-sculpt-v002.blend'
    original=REPO/'public'/'assets'/'companions'/'rabbit.png'
    if not check['passed'] or not motion['passed']:raise ValueError('Independent checks have not passed')
    if digest(glb)!=report['glb_sha256'] or digest(glb)!=check['sha256'] or digest(glb)!=motion['source_sha256']:
        raise ValueError('GLB validation evidence mismatch')
    if digest(blend)!=report['blend_sha256']:raise ValueError('Source evidence mismatch')
    if digest(original)!=report['reference_sha256']:raise ValueError('Reference changed')
    if set(report['renders'])!={'hero','front','side','rear'}:raise ValueError('Four principal views required')
    for name,sha in report['builder_sha256'].items():
        if digest(REPO/name)!=sha:raise ValueError('Builder changed after build: '+name)
    review=REPO/'assets'/'3d'/'reference'/'rabbit'/'sculpt-v002'
    public=REPO/'public'/'assets'/'3d'/'rabbit'/glb.name
    master=ROOT/blend.name
    deliver(glb,public);deliver(blend,master);deliver(original,review/'original.png')
    rel=lambda p:p.relative_to(REPO).as_posix()
    renders={}
    for view,path in report['renders'].items():
        target=review/Path(path).name;deliver(Path(path),target);renders[view]=rel(target)
    clean=dict(check);clean['asset']=rel(public);clean['renders']={}
    for view,path in check['renders'].items():
        target=review/'import-review'/Path(path).name;deliver(Path(path),target);clean['renders'][view]=rel(target)
    (review/'import-validation.json').write_text(json.dumps(clean,indent=2)+'\n',encoding='utf-8')
    clean_motion={k:v for k,v in motion.items() if k not in ('source_glb','renders','contact_sheet')}
    clean_motion['asset']=rel(public);clean_motion['renders']={}
    for item in motion.get('renders',[]):
        view=item['clip'];path=item['image']
        target=review/'motion'/Path(path).name;deliver(Path(path),target);clean_motion['renders'][view]=rel(target)
    target=review/'motion'/Path(motion['contact_sheet']).name
    deliver(Path(motion['contact_sheet']),target);clean_motion['contact_sheet']=rel(target)
    (review/'motion-validation.json').write_text(json.dumps(clean_motion,indent=2)+'\n',encoding='utf-8')
    manifest={
        'schema':'asterion-local-companion-sculpt-v1','kind':'rabbit','name':'Liora','version':'sculpt-v002',
        'source':rel(master),'model':rel(public),'reference':rel(review/'original.png'),
        'source_sha256':digest(master),'model_sha256':digest(public),'reference_sha256':digest(original),
        'bytes':check['bytes'],'triangles':check['triangles'],'vertices':check['vertices'],
        'bones':check['bones'],'materials':check['materials'],'draw_calls':check['draw_calls'],
        'clips':list(check['animation_samples']),'editable_source_meshes':report['editable_source_meshes_preserved'],
        'blender':check['blender'],'renders':renders,'fresh_import_passed':True,'sampled_motion_passed':True,
        'human_likeness_accepted':False,'mobile_performance_accepted':False,'projection_used':False,'paid_provider_used':False,
        'provenance':'Locally modeled from unchanged rabbit.png. Hidden views inferred; source and historical v001 preserved.',
        'animation_limit':check['animation_limit'],'package_status':'Local hash-checked delivery, not a game-dev CLI canonical receipt.',
        'builder':rel(ROOT/'build.py'),'builder_sha256':report['builder_sha256'],'notes':report['spec']['notes']}
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:manifest[key] for key in ('version','triangles','bytes','model_sha256')},indent=2))


if __name__=='__main__':main()

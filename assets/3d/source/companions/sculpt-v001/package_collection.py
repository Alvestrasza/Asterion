"""Copy independently validated assets into fresh versioned repository paths."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[4]
KINDS=('rabbit','cat','orc','pony','fairy','dog','elf')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def copy_checked(source,target,previous=None):
    if target.exists():
        if digest(source)==digest(target):return
        # A local pre-handoff refinement may replace only the exact binary that
        # was copied from the explicitly supplied previous review directory.
        if previous is None or not previous.exists() or digest(target)!=digest(previous):
            raise FileExistsError('Different or externally edited delivery: '+str(target))
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    if digest(source)!=digest(target):raise ValueError('Copy hash mismatch: '+str(target))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True)
    parser.add_argument('--kinds',nargs='+',choices=KINDS,default=KINDS)
    parser.add_argument('--previous',help='Exact previous local build root, only for hash-guarded pre-handoff refinement')
    args=parser.parse_args();build_root=Path(args.input).resolve()
    reports=[]
    for kind in args.kinds:
        build=build_root/kind
        previous_build=Path(args.previous).resolve()/kind if args.previous else None
        def deliver(file,target):
            previous=previous_build/file.relative_to(build) if previous_build and file.is_relative_to(build) else None
            copy_checked(file,target,previous)
        report=json.loads((build/'build-report.json').read_text())
        validation=json.loads((build/'validation'/'import-validation.json').read_text())
        glb=build/(kind+'-sculpt-v001.glb');blend=build/(kind+'-sculpt-v001.blend')
        if not validation['passed']:raise ValueError('Validation failed: '+kind)
        if not digest(glb)==report['glb_sha256']==validation['sha256']:raise ValueError('GLB evidence mismatch: '+kind)
        if digest(blend)!=report['blend_sha256']:raise ValueError('Master hash mismatch: '+kind)
        reference=REPO/'public'/'assets'/'companions'/(kind+'.png')
        if digest(reference)!=report['reference_sha256']:raise ValueError('Reference changed: '+kind)
        source_dir=REPO/'assets'/'3d'/'source'/kind/'sculpt-v001'
        review_dir=REPO/'assets'/'3d'/'reference'/kind/'sculpt-v001'
        public_dir=REPO/'public'/'assets'/'3d'/kind
        target_blend=source_dir/blend.name;target_glb=public_dir/glb.name
        deliver(blend,target_blend);deliver(glb,target_glb)
        deliver(reference,review_dir/'original.png')
        review_images={}
        for view,path in report['renders'].items():
            target=review_dir/Path(path).name;deliver(Path(path),target)
            review_images[view]=target.relative_to(REPO).as_posix()
        import_images={}
        for view,path in validation['renders'].items():
            target=review_dir/'import-review'/Path(path).name;deliver(Path(path),target)
            import_images[view]=target.relative_to(REPO).as_posix()
        clean={k:v for k,v in validation.items() if k not in ('asset','renders')}
        clean['asset']=target_glb.relative_to(REPO).as_posix();clean['renders']=import_images
        (review_dir/'import-validation.json').write_text(json.dumps(clean,indent=2)+'\n',encoding='utf-8')
        manifest={
            'schema':'asterion-local-companion-sculpt-v1','kind':kind,'name':report['spec']['name'],
            'version':'sculpt-v001','source':target_blend.relative_to(REPO).as_posix(),
            'model':target_glb.relative_to(REPO).as_posix(),'reference':review_dir.relative_to(REPO).as_posix()+'/original.png',
            'source_sha256':report['blend_sha256'],'model_sha256':report['glb_sha256'],
            'reference_sha256':report['reference_sha256'],'bytes':validation['bytes'],
            'triangles':validation['triangles'],'vertices':validation['vertices'],
            'bones':validation['bones'],'materials':validation['materials'],'draw_calls':validation['draw_calls'],
            'clips':list(validation['animation_samples']),
            'editable_source_meshes':report['editable_source_meshes_preserved'],
            'blender':validation['blender'],'renders':review_images,'fresh_import_passed':True,
            'human_likeness_accepted':False,'mobile_performance_accepted':False,
            'projection_used':False,'paid_provider_used':False,
            'provenance':'Modeled locally from existing project single-view artwork. Hidden views are inferred.',
            'animation_limit':validation['animation_limit'],
            'package_status':'Local manually validated delivery; no canonical game-dev CLI receipt.',
            'builder':'assets/3d/source/companions/sculpt-v001/build_collection.py',
            'builder_sha256':report['builder_sha256'],
            'notes':report['spec'].get('notes',[])}
        (source_dir/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        reports.append(manifest)
    reports=[json.loads((REPO/'assets'/'3d'/'source'/kind/'sculpt-v001'/'manifest.json').read_text()) for kind in KINDS]
    destination=REPO/'assets'/'3d'/'reference'/'companions'/'sculpt-v001'
    destination.mkdir(parents=True,exist_ok=True)
    (destination/'collection-manifest.json').write_text(json.dumps(reports,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{'kind':r['kind'],'triangles':r['triangles'],'bytes':r['bytes']} for r in reports],indent=2))


if __name__=='__main__':main()

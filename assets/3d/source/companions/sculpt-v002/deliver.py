"""Preflighted, hash-bound companion v002 handoff with staged rollback.

Nothing is replaced until all source artifacts and destination conflicts have
been checked. --previous authorizes only exact prior review content, including
the JSON metadata generated from that prior review. Earlier versions are never
targets. A process crash is not a filesystem-wide atomic transaction.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[4]
KINDS=('cat','dog','orc','elf','fairy')


def digest(path):
    return sha256(path.read_bytes())


def sha256(data):
    return hashlib.sha256(data).hexdigest().upper()


def json_bytes(value):
    # Match previous local write_text output for exact historical metadata
    # checks; no lossy semantic comparison or hash bypass is used.
    return (json.dumps(value,indent=2)+'\n').replace('\n',os.linesep).encode('utf-8')


@dataclass(frozen=True)
class Artifact:
    target: Path
    content: bytes

    @property
    def checksum(self):
        return sha256(self.content)


@dataclass(frozen=True)
class DeliveryPlan:
    repo: Path
    artifacts: tuple[Artifact,...]
    manifest: dict
    observed_targets: dict[Path,str|None]


def bundle_artifacts(work,kind,repo,*,current=True):
    """Snapshot every binary, image and generated metadata file before writes."""
    work=Path(work).resolve();repo=Path(repo).resolve()
    if kind not in KINDS:raise ValueError('Unsupported companion: '+kind)
    cache={};artifacts={}
    def read(path):
        path=Path(path).resolve()
        if path not in cache:cache[path]=path.read_bytes()
        return cache[path]
    def add(target,content):
        target=Path(target).resolve()
        if not target.is_relative_to(repo):raise ValueError('Delivery target outside repository')
        item=Artifact(target,content)
        if target in artifacts and artifacts[target].content!=content:
            raise ValueError('Conflicting generated destination: '+str(target))
        artifacts[target]=item
    def add_image(path,target):
        source=Path(path).resolve()
        if not source.is_relative_to(work):raise ValueError('Review image outside its source review: '+str(source))
        add(target,read(source))
    report=json.loads(read(work/'build-report.json'))
    check=json.loads(read(work/'validation'/'import-validation.json'))
    motion=json.loads(read(work/'motion'/'motion-inspection.json'))
    glb=work/(kind+'-sculpt-v002.glb');blend=work/(kind+'-sculpt-v002.blend')
    original=repo/'public'/'assets'/'companions'/(kind+'.png')
    glb_data=read(glb);blend_data=read(blend);reference_data=read(original)
    glb_hash=sha256(glb_data);blend_hash=sha256(blend_data)
    if report['spec']['kind']!=kind:raise ValueError('Build evidence kind mismatch')
    for label,evidence in (('Import',check),('Motion',motion)):
        if evidence.get('passed') is not True or not evidence.get('checks') or not all(v is True for v in evidence['checks'].values()):
            raise ValueError(label+' checks have not passed')
    if glb_hash!=report['glb_sha256'] or glb_hash!=check['sha256'] or glb_hash!=motion['source_sha256']:
        raise ValueError('GLB validation evidence mismatch')
    if blend_hash!=report['blend_sha256']:raise ValueError('Source build evidence mismatch')
    # Historical pre-handoff metadata may predate master hash capture. It is
    # an exact overwrite baseline only, never current acceptance evidence.
    if current or 'master_sha256' in check:
        if blend_hash!=check.get('master_sha256'):raise ValueError('Reopened master validation evidence mismatch')
    if sha256(reference_data)!=report['reference_sha256']:raise ValueError('Reference changed')
    if set(report['renders'])!={'hero','front','side','rear'}:raise ValueError('Four principal views required')
    if current:
        if not report.get('builder_sha256'):raise ValueError('Missing builder evidence')
        for name,sha in report['builder_sha256'].items():
            builder=(repo/name).resolve()
            if not builder.is_relative_to(repo):raise ValueError('Builder evidence outside repository')
            if sha256(read(builder))!=sha:raise ValueError('Builder changed after build: '+name)
    pet_root=repo/'assets'/'3d'/'source'/kind/'sculpt-v002'
    review=repo/'assets'/'3d'/'reference'/kind/'sculpt-v002'
    public=repo/'public'/'assets'/'3d'/kind/glb.name
    master=pet_root/blend.name
    rel=lambda path:path.relative_to(repo).as_posix()
    add(public,glb_data);add(master,blend_data);add(review/'original.png',reference_data)
    renders={}
    for view,path in report['renders'].items():
        target=review/Path(path).name;add_image(path,target);renders[view]=rel(target)
    clean=dict(check);clean['asset']=rel(public);clean['renders']={}
    for view,path in check['renders'].items():
        target=review/'import-review'/Path(path).name;add_image(path,target);clean['renders'][view]=rel(target)
    add(review/'import-validation.json',json_bytes(clean))
    clean_motion={k:v for k,v in motion.items() if k not in ('source_glb','renders','contact_sheet')}
    clean_motion['asset']=rel(public);clean_motion['renders']={}
    for item in motion.get('renders',[]):
        view=item['clip'];path=item['image']
        target=review/'motion'/Path(path).name;add_image(path,target);clean_motion['renders'][view]=rel(target)
    target=review/'motion'/Path(motion['contact_sheet']).name
    add_image(motion['contact_sheet'],target);clean_motion['contact_sheet']=rel(target)
    add(review/'motion-validation.json',json_bytes(clean_motion))
    manifest={
        'schema':'asterion-local-companion-sculpt-v1','kind':kind,'name':report['spec']['name'],'version':'sculpt-v002',
        'source':rel(master),'model':rel(public),'reference':rel(review/'original.png'),
        'source_sha256':blend_hash,'model_sha256':glb_hash,'reference_sha256':sha256(reference_data),
        'bytes':check['bytes'],'triangles':check['triangles'],'vertices':check['vertices'],
        'bones':check['bones'],'materials':check['materials'],'draw_calls':check['draw_calls'],
        'clips':list(check['animation_samples']),'editable_source_meshes':report['editable_source_meshes_preserved'],
        'blender':check['blender'],'renders':renders,'fresh_import_passed':True,'sampled_motion_passed':True,
        'human_likeness_accepted':False,'mobile_performance_accepted':False,'projection_used':False,'paid_provider_used':False,
        'provenance':'Locally refined from unchanged '+kind+'.png. Hidden views inferred; historical files preserved.',
        'animation_limit':check['animation_limit'],'package_status':'Local hash-checked delivery, not a game-dev CLI canonical receipt.',
        'builder':'assets/3d/source/companions/sculpt-v002/build.py','builder_sha256':report['builder_sha256'],'notes':report['spec']['notes']}
    add(pet_root/'manifest.json',json_bytes(manifest))
    return tuple(artifacts.values()),manifest


def existing_hash(target):
    if not target.exists():return None
    if not target.is_file():raise FileExistsError('Non-file delivery destination: '+str(target))
    return digest(target)


def prepare_delivery(work,kind,*,previous=None,repo=REPO):
    """Read-only preflight: even a final metadata conflict leaves targets intact."""
    repo=Path(repo).resolve()
    artifacts,manifest=bundle_artifacts(work,kind,repo)
    prior={}
    if previous is not None:
        old,_=bundle_artifacts(previous,kind,repo,current=False)
        prior={item.target:item.checksum for item in old}
    observed={}
    for item in artifacts:
        actual=existing_hash(item.target);observed[item.target]=actual
        if actual is not None and actual!=item.checksum and actual!=prior.get(item.target):
            raise FileExistsError('Existing different delivery: '+str(item.target))
    return DeliveryPlan(repo,artifacts,manifest,observed)


def verify_destinations(plan):
    for target,expected in plan.observed_targets.items():
        if existing_hash(target)!=expected:
            raise FileExistsError('Delivery destination changed after preflight: '+str(target))


def execute_delivery(plan):
    """Stage all content, recheck targets, commit, roll back ordinary I/O failures."""
    verify_destinations(plan)
    staging_root=plan.repo/'.private';staging_root.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='companion-delivery-',dir=staging_root)).resolve()
    staged={};backups={};committed=[];retain_stage=False
    try:
        for index,item in enumerate(plan.artifacts):
            path=stage/('new-'+str(index));path.write_bytes(item.content)
            if digest(path)!=item.checksum:raise ValueError('Staged content checksum failed')
            staged[item.target]=path
            if plan.observed_targets[item.target] is not None:
                backup=stage/('old-'+str(index));shutil.copy2(item.target,backup)
                if digest(backup)!=plan.observed_targets[item.target]:raise ValueError('Destination changed while staging backup')
                backups[item.target]=backup
        verify_destinations(plan)
        try:
            for item in plan.artifacts:
                if existing_hash(item.target)!=plan.observed_targets[item.target]:
                    raise FileExistsError('Delivery target changed during commit: '+str(item.target))
                item.target.parent.mkdir(parents=True,exist_ok=True)
                os.replace(staged[item.target],item.target);committed.append(item)
                if digest(item.target)!=item.checksum:raise ValueError('Delivered content checksum failed')
        except BaseException as error:
            rollback_errors=[]
            for item in reversed(committed):
                try:
                    if existing_hash(item.target)!=item.checksum:
                        raise RuntimeError('Concurrent edit preserved: '+str(item.target))
                    if item.target in backups:os.replace(backups[item.target],item.target)
                    else:item.target.unlink()
                except BaseException as rollback_error:rollback_errors.append(str(rollback_error))
            if rollback_errors:
                retain_stage=True
                raise RuntimeError('Delivery failed; rollback incomplete. Backups retained at '+str(stage)+': '+'; '.join(rollback_errors)) from error
            raise
    finally:
        if not retain_stage:
            # Remove only the unique staging directory created by this call.
            if stage.parent!=staging_root.resolve() or not stage.name.startswith('companion-delivery-'):
                raise RuntimeError('Unsafe staging cleanup path')
            shutil.rmtree(stage)
    return plan.manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True)
    parser.add_argument('--previous',help='Exact previous private review for hash-guarded pre-handoff corrections')
    parser.add_argument('--kind',required=True,choices=KINDS)
    args=parser.parse_args()
    manifest=execute_delivery(prepare_delivery(args.input,args.kind,previous=args.previous))
    print(json.dumps({key:manifest[key] for key in ('version','triangles','bytes','model_sha256')},indent=2))


if __name__=='__main__':main()

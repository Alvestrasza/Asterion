"""Versioned local anatomy correction and independently detachable armor."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import bpy

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[4]
V1=ROOT.parent/'sculpt-v001';V2=ROOT.parent/'sculpt-v002';V3=ROOT.parent/'sculpt-v003'
sys.path[:0]=[str(ROOT),str(V1),str(V2),str(V3)]
import build_sculpt as g
import rig_delivery
import validate_refinement as verify
import build_head_study as historical
import morphology


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
def rel(path):return Path(path).relative_to(REPO).as_posix()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--resolution',type=int,default=1600)
    parser.add_argument('--samples',type=int,default=64)
    parser.add_argument('--preview',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    out=Path(args.output).resolve()
    if out.exists():raise FileExistsError('Use a fresh private review directory')
    baseline=V3/'asterion-sculpt-v003.blend'
    reference=REPO/'assets/3d/reference/asterion/sculpt-v003/asterion-approved-turnaround.png'
    deps=[Path(__file__),ROOT/'morphology.py',V1/'build_sculpt.py',V1/'rig_delivery.py',
        V2/'validate_refinement.py',V3/'build_head_study.py']
    if not args.preview:deps.append(ROOT/'export_equipment.py')
    hashes={rel(p):sha(p) for p in [baseline,reference]+deps}
    out.mkdir(parents=True)
    bpy.ops.wm.open_mainfile(filepath=str(baseline));bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene;rig=verify.unique_rig();original=verify.rig_fingerprint(rig)
    verify.activate(rig,bpy.data.actions['idle'],1)
    g.M={m.name.removeprefix('AST_'):m for m in bpy.data.materials if m.name.startswith('AST_')}
    g.ASSET=[o for o in scene.objects if o.type=='MESH' and o.get('ast_part')]
    before={o.name:historical.geometry_signature(o) for o in scene.objects if o.type in {'MESH','CURVES'} and o.get('ast_part')}
    print('ROUND muzzle and fit dorsal shields to actual anatomical surfaces',flush=True)
    face=morphology.refine_face(g,rig,rig_delivery)
    dorsal=morphology.dorsal_plates(g,rig,rig_delivery)
    body,armor=morphology.separate_equipment(g)
    for obj in scene.objects:
        if obj.type=='CURVES' and obj.get('ast_native_hair'):obj['asterion_component']='body'
    changed=set(face['changed_objects']+face['removed_objects']+dorsal['removed_objects'])
    retained={name:digest for name,digest in before.items() if name not in changed}
    checks=verify.compare_source(original,verify.rig_fingerprint(rig))
    checks.update({'unaffected_geometry_identical':all(historical.geometry_signature(bpy.data.objects[name])==digest for name,digest in retained.items()),
        'muzzle_retracted_at_least_point_one':face['head_front_retraction']>.1,
        'dorsal_rims_contact_skin':dorsal['max_fitted_rim_distance']<.007,
        'removed_floating_dorsal_rows':not any(o.name.startswith(('AST_dorsal_neck_plate_','AST_spine_scale_')) for o in g.ASSET),
        'separate_nonempty_equipment':len(body)>0 and len(armor)>0,
        'no_head_hair':not any(o.get('ast_hair_group') in {'mane.L','mane.R','cheek.L','cheek.R'} for o in scene.objects)})
    if not all(checks.values()):raise ValueError('Source checks failed: '+str(checks))
    export=None
    if not args.preview:
        import export_equipment
        export=export_equipment.export_glb(out/'asterion-sculpt-v004.glb',body,armor,rig)
    scene['asset']='asterion-sculpt-v004'
    scene['animation_policy']='Original 22-bone rig and full action data preserved'
    scene['head_hair_policy']='Head hair remains omitted; native and portable tail hair retained'
    scene.render.resolution_x=args.resolution;scene.render.resolution_y=args.resolution
    scene.cycles.samples=args.samples
    source_views=out/'source-views';source_views.mkdir()
    views=['face','side','rear'] if args.preview else ['hero','front','side','rear','face']
    renders=g.render(scene.camera,source_views,views)
    bare=out/'armor-off';bare.mkdir()
    for obj in armor:obj.hide_render=True
    for name,path in g.render(scene.camera,bare,['hero','side']).items():renders['armor_off.'+name]=path
    for obj in armor:obj.hide_render=False
    scene.camera.location=(8,-12,5.8);g.point_at(scene.camera,(0,.25,2.88));scene.camera.data.ortho_scale=6.8
    verify.activate(rig,bpy.data.actions['idle'],1);g.active(bpy.data.objects['AST_Sculpted_head'])
    master=out/'asterion-sculpt-v004.blend';bpy.ops.wm.save_as_mainfile(filepath=str(master))
    checks['input_sources_unchanged']=all(sha(REPO/p)==digest for p,digest in hashes.items())
    report={'schema':'asterion-rounded-modular-v004','preview_only':args.preview,'source_sha256':sha(master),
        'model_sha256':sha(out/'asterion-sculpt-v004.glb') if export else None,
        'input_sha256':hashes,'builder_sha256':{rel(p):hashes[rel(p)] for p in deps},
        'blender':bpy.app.version_string,'face':face,'dorsal':dorsal,
        'body_objects':[o.name for o in body],'armor_objects':[o.name for o in armor],
        'unaffected_geometry_sha256':retained,'checks':checks,'passed':all(checks.values()),
        'export':export,'renders':{name:{'file':Path(path).relative_to(out).as_posix(),'sha256':sha(path)} for name,path in renders.items()}}
    (out/'build-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'face_retraction':face['head_front_retraction'],
        'max_rim_gap':dorsal['max_fitted_rim_distance'],'armor_objects':len(armor)},indent=2),flush=True)
    if not report['passed']:raise RuntimeError('Input preservation failed')


if __name__=='__main__':main()

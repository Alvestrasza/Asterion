"""Refine a copy of Asterion's accepted master while preserving its animation."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import bpy

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[4]
BASE=ROOT.parent/'sculpt-v001'
sys.path.insert(0,str(BASE))
import build_sculpt as g
import rig_delivery
sys.path.insert(0,str(ROOT))
import refine_geometry


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def animation_fingerprint(rig):
    actions={}
    for action in sorted(bpy.data.actions,key=lambda a:a.name):
        curves=[]
        for c in rig_delivery._action_curves(action):
            keys=[(tuple(k.co),tuple(k.handle_left),tuple(k.handle_right),k.interpolation,
                   k.handle_left_type,k.handle_right_type,k.easing,k.amplitude,k.back,k.period)
                  for k in c.keyframe_points]
            curves.append((c.data_path,c.array_index,c.extrapolation,keys))
        actions[action.name]=sorted(curves,key=lambda c:(c[0],c[1]))
    bones=[(b.name,b.parent.name if b.parent else None,list(map(list,b.matrix_local)),b.use_deform)
           for b in sorted(rig.data.bones,key=lambda b:b.name)]
    return hashlib.sha256(json.dumps({'actions':actions,'bones':bones},sort_keys=True).encode()).hexdigest().upper()


def triangles(objects):
    total=0
    for obj in objects:
        if obj.type=='MESH':obj.data.calc_loop_triangles();total+=len(obj.data.loop_triangles)
    return total


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--resolution',type=int,default=1600)
    parser.add_argument('--samples',type=int,default=64)
    parser.add_argument('--views',default='hero,front,side,rear,face')
    parser.add_argument('--target-triangles',type=int,default=5000000)
    parser.add_argument('--geometry-preview',action='store_true',help='Private geometry-only review with historical hair, no delivery export')
    parser.add_argument('--no-export',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    out=Path(args.output).resolve()
    if out.exists():raise FileExistsError('Choose a fresh output directory: '+str(out))
    if not 4500000<=args.target_triangles<=5500000:raise ValueError('User-authorized approximately 5M budget required')
    baseline=BASE/'asterion-sculpt-v001.blend'
    reference=REPO/'assets/3d/reference/asterion/sculpt-v001/asterion-approved-turnaround.png'
    source_sha=sha(baseline);reference_sha=sha(reference)
    deps=[BASE/'build_sculpt.py',BASE/'rig_delivery.py',BASE/'armor.py',
          ROOT/'build_refinement.py',ROOT/'refine_geometry.py']
    if not args.geometry_preview:deps.append(ROOT/'hair_groom.py')
    builders={p.relative_to(REPO).as_posix():sha(p) for p in deps}
    out.mkdir(parents=True)
    started=time.monotonic()
    bpy.ops.wm.open_mainfile(filepath=str(baseline))
    bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene;rig=bpy.data.objects[rig_delivery.RIG_NAME]
    rig.animation_data.action=bpy.data.actions['idle'];scene.frame_set(1);bpy.context.view_layer.update()
    original_animation=animation_fingerprint(rig)
    g.M={m.name.removeprefix('AST_'):m for m in bpy.data.materials if m.name.startswith('AST_')}
    g.ASSET=[o for o in bpy.data.objects if o.type=='MESH' and o.get('ast_part')]
    print('REFINE geometry from immutable master',flush=True)
    changes=refine_geometry.refine(g,rig)
    hair_report={'native_hair':False,'private_geometry_preview':True}
    if not args.geometry_preview:
        import hair_groom
        refine_geometry.remove(g,('AST_mane_lock_','AST_mane_strand_','AST_cheek_mane_','AST_tail_plume_'))
        remaining=args.target_triangles-triangles(g.ASSET)
        if remaining<1000000:raise ValueError('Useful groom allocation is below the planned budget')
        print('BUILD native groom and matching tubes; remaining triangles',remaining,flush=True)
        native,hair_meshes,hair_report=hair_groom.build(g,rig,triangle_budget=remaining)
        for obj in hair_meshes:
            if obj not in g.ASSET:g.ASSET.append(obj)
        for obj in native:
            obj.hide_render=False;obj.hide_viewport=False
        for obj in hair_meshes:
            obj.hide_render=True;obj.hide_viewport=True
    scene['asset']='asterion-sculpt-v002'
    scene['reference_sha256']=reference_sha
    scene['baseline_master_sha256']=source_sha
    scene['animation_policy']='Original sculpt-v001 rest rig and actions unchanged; no physics'
    scene.cycles.samples=args.samples
    scene.render.resolution_x=args.resolution;scene.render.resolution_y=args.resolution
    scene.frame_set(1);bpy.context.view_layer.update()
    count=triangles(g.ASSET)
    print('DELIVERY geometry triangles',count,flush=True)
    if not args.geometry_preview and not 4500000<=count<=5500000:raise ValueError('Final mesh budget failed')
    export_report=None
    if not args.no_export and not args.geometry_preview:
        export_report=rig_delivery.export_glb(out/'asterion-sculpt-v002.glb',g.ASSET,rig)
        (out/'export-report.json').write_text(json.dumps(export_report,indent=2),encoding='utf-8')
    if original_animation!=animation_fingerprint(rig):raise ValueError('Refinement changed original animation/rest rig')
    cam=scene.camera
    renders=g.render(cam,out,args.views.split(','))
    cam.location=(8,-12,5.8);g.point_at(cam,(0,.25,2.88));cam.data.ortho_scale=6.8
    scene.frame_set(1);g.active(bpy.data.objects['AST_Sculpted_head'])
    master=out/'asterion-sculpt-v002.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(master))
    if source_sha!=sha(baseline) or reference_sha!=sha(reference):raise ValueError('Baseline/reference changed during build')
    if any(sha(REPO/p)!=digest for p,digest in builders.items()):raise ValueError('Builder dependency changed during build')
    report={'schema':'asterion-reference-refinement-v2','blender':bpy.app.version_string,
            'baseline_master_sha256':source_sha,'reference_sha256':reference_sha,
            'source_sha256':sha(master),'model_sha256':sha(out/'asterion-sculpt-v002.glb') if export_report else None,
            'original_animation_sha256':original_animation,'final_animation_sha256':animation_fingerprint(rig),
            'animations_unchanged':original_animation==animation_fingerprint(rig),
            'triangles':count,'editable_meshes':len(g.ASSET),'changes':changes,'hair':hair_report,
            'renders':renders,'builder_sha256':builders,'elapsed_seconds':time.monotonic()-started,
            'geometry_preview_only':args.geometry_preview,'human_likeness_accepted':False,'mobile_performance_accepted':False}
    (out/'build-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('COMPLETE',master,'triangles',count,flush=True)


if __name__=='__main__':main()

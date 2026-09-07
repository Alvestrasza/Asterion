"""Build one remaining companion v002 review; existing output GLBs are never overwritten."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[4]
SHARED=ROOT.parent/'sculpt-v001'
sys.path.insert(0,str(SHARED));sys.path.insert(0,str(ROOT))
import common
import importlib.util


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind',required=True,choices=['cat','dog','orc','elf','fairy'])
    parser.add_argument('--output',required=True)
    parser.add_argument('--views',default='hero,front,side,rear')
    parser.add_argument('--resolution',type=int,default=1400)
    parser.add_argument('--samples',type=int,default=64)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    kind=args.kind; pet_root=ROOT.parents[1]/kind/'sculpt-v002'
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
    paths=[ROOT/'build.py']+list(pet_root.glob('*.py'))+[SHARED/name for name in ('common.py','woodland.py','humanoids.py','sky_folk.py')]+[
        common.SOURCE_ROOT/'asterion'/'sculpt-v001'/'build_sculpt.py',common.SOURCE_ROOT/'asterion'/'sculpt-v001'/'rig_delivery.py']
    builder_hashes={p.relative_to(REPO).as_posix():digest(p) for p in paths}
    sys.path.insert(0,str(pet_root))
    module_spec=importlib.util.spec_from_file_location('current_pet_model',pet_root/'model.py')
    model=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(model)
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    glb=out/(kind+'-sculpt-v002.glb');blend=out/(kind+'-sculpt-v002.blend')
    if glb.exists() or blend.exists():raise FileExistsError('Use a fresh review directory')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.world=bpy.data.worlds.new('Companion neutral studio')
    g=common.toolkit()
    print('BUILD reference refinement',kind,flush=True);spec=model.build(g)
    if spec['kind']!=kind:raise ValueError('Builder kind mismatch')
    print('BUILD presentation rig',flush=True);rig=common.rig_asset(g,spec)
    bpy.context.view_layer.update()
    cam,center,span=common.configure_stage(g,g.ASSET,args.resolution,args.samples)
    bpy.data.objects['STUDIO_ground'].scale=(10,10,10)
    scene=bpy.context.scene
    reference=REPO/'public'/'assets'/'companions'/(kind+'.png')
    scene['reference_sha256']=digest(reference);scene['reference_authority']='Unchanged approved single-view '+kind+'.png'
    scene['companion_kind']=kind;scene['companion_name']=spec['name'];scene['revision']='sculpt-v002'
    scene['interpretation_limit']='Hidden views inferred; no exact 1:1 claim or mobile acceptance.'
    print('EXPORT',spec['name'],flush=True)
    report=common.exporter().export_glb(glb,g.ASSET,rig)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    renders=common.render_views(g,cam,center,span,out,kind,[v for v in args.views.split(',') if v])
    # render_views restores the hero direction; restore its fitting scale too
    # so opening the saved Blender master does not retain the rear-view crop.
    direction=Vector((.85,-1.45,.35)).normalized()
    right=Vector((0,0,1)).cross(direction).normalized();up=direction.cross(right).normalized()
    corners=[Vector((x*span.x/2,y*span.y/2,z*span.z/2)) for x in (-1,1) for y in (-1,1) for z in (-1,1)]
    cam.data.ortho_scale=max(max(abs(p.dot(right)),abs(p.dot(up))) for p in corners)*2*1.12
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    report.update({'spec':spec,'reference_sha256':digest(reference),'glb_sha256':digest(glb),'blend_sha256':digest(blend),
        'blend':str(blend),'renders':renders,'span':list(span),'mobile_performance_accepted':False,
        'human_likeness_accepted':False,'reference_projection':False})
    report['builder_sha256']=builder_hashes
    (out/'build-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'complete':True,'triangles':report['triangles'],'bytes':report['bytes'],
                      'source_meshes':report['editable_source_meshes_preserved']},indent=2),flush=True)


if __name__=='__main__':main()

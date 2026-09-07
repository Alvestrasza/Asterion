"""Build one authored companion; never overwrite an existing GLB.

blender --background --factory-startup --python build_collection.py --
  --kind rabbit --output /absolute/new/review/rabbit
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys

import bpy

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import common

BUILDERS={'rabbit':'woodland','cat':'woodland','dog':'woodland',
          'orc':'humanoids','elf':'humanoids','pony':'sky_folk','fairy':'sky_folk'}
REPO=ROOT.parents[4]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind',required=True,choices=list(BUILDERS))
    parser.add_argument('--output',required=True)
    parser.add_argument('--views',default='hero,front,side,rear')
    parser.add_argument('--resolution',type=int,default=1100)
    parser.add_argument('--samples',type=int,default=48)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
    glb=output/(args.kind+'-sculpt-v001.glb')
    if glb.exists():raise FileExistsError('Choose a new output folder: '+str(glb))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if bpy.context.scene.world is None:bpy.context.scene.world=bpy.data.worlds.new('Gallery world')
    g=common.toolkit()
    print('BUILDING',args.kind,flush=True)
    builder=importlib.import_module(BUILDERS[args.kind]);spec=builder.build(g,args.kind)
    rig=common.rig_asset(g,spec)
    bpy.context.view_layer.update()
    cam,center,span=common.configure_stage(g,g.ASSET,args.resolution,args.samples)
    reference=REPO/'public'/'assets'/'companions'/(args.kind+'.png')
    scene=bpy.context.scene
    scene['reference_sha256']=hashlib.sha256(reference.read_bytes()).hexdigest().upper()
    scene['reference_authority']='Existing approved single-view companion artwork'
    scene['companion_kind']=args.kind;scene['companion_name']=spec['name']
    scene['interpretation_limit']='Hidden views inferred; likeness is subject to human review.'
    report=common.exporter().export_glb(glb,g.ASSET,rig)
    blend=output/(args.kind+'-sculpt-v001.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    renders=common.render_views(g,cam,center,span,output,args.kind,args.views.split(','))
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    report.update({'spec':spec,'reference_sha256':scene['reference_sha256'],
                   'glb_sha256':hashlib.sha256(glb.read_bytes()).hexdigest().upper(),
                   'blend_sha256':hashlib.sha256(blend.read_bytes()).hexdigest().upper(),
                   'blend':str(blend),'renders':renders,'span':list(span),
                   'mobile_performance_accepted':False,'human_likeness_accepted':False,
                   'reference_projection':False})
    report['builder_sha256']={path.relative_to(REPO).as_posix():hashlib.sha256(path.read_bytes()).hexdigest().upper()
        for path in (ROOT/'build_collection.py',ROOT/'common.py',ROOT/(BUILDERS[args.kind]+'.py'),
                     common.SOURCE_ROOT/'asterion'/'sculpt-v001'/'build_sculpt.py',
                     common.SOURCE_ROOT/'asterion'/'sculpt-v001'/'rig_delivery.py')}
    (output/'build-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'complete':True,'kind':args.kind,'triangles':report['triangles'],
                      'bytes':report['bytes'],'meshes':report['meshes'],'bones':report['bones'],
                      'source_meshes':report['editable_source_meshes_preserved']},indent=2),flush=True)


if __name__=='__main__':main()

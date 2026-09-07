"""Build a new Caelo v002 review; existing output GLBs are never overwritten."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[4]
SHARED=ROOT.parents[1]/'companions'/'sculpt-v001'
sys.path.insert(0,str(SHARED));sys.path.insert(0,str(ROOT))
import common
import anatomy
import hair
import ornaments


def refine_proportions(g,spec):
    """Lower the dressed head slightly while shortening, not crushing, the neck."""
    for obj in g.ASSET:
        part=obj.get('ast_part','body')
        is_head=part=='head' or part.startswith(('ear.','lid.'))
        inverse=obj.matrix_world.inverted()
        for vertex in obj.data.vertices:
            p=obj.matrix_world@vertex.co
            t=1 if is_head else max(0,min(1,(p.z-2.1)/.9))
            p.z-=.12*t;vertex.co=inverse@p
        if 'ast_lid_pivot' in obj:
            point=list(obj['ast_lid_pivot']);point[2]-=.12;obj['ast_lid_pivot']=point
        obj.data.update()
    bones=[]
    for name,head,tail,parent in spec['bones']:
        head=list(head);tail=list(tail)
        if name=='head' or name.startswith('ear.'):
            head[2]-=.12;tail[2]-=.12
        elif name=='neck':tail[2]-=.12
        bones.append((name,head,tail,parent))
    spec['bones']=bones


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--views',default='hero,front,side,rear')
    parser.add_argument('--resolution',type=int,default=1400)
    parser.add_argument('--samples',type=int,default=64)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    glb=out/'pony-sculpt-v002.glb';blend=out/'pony-sculpt-v002.blend'
    if glb.exists() or blend.exists():raise FileExistsError('Use a fresh review directory')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.world=bpy.data.worlds.new('Caelo neutral studio')
    g=common.toolkit()
    print('BUILD Caelo anatomy',flush=True);spec=anatomy.build(g)
    print('BUILD Caelo flowing curls',flush=True);hair.build(g)
    print('BUILD Caelo star tack',flush=True);ornaments.build(g)
    refine_proportions(g,spec)
    print('BUILD presentation rig',flush=True);rig=common.rig_asset(g,spec)
    bpy.context.view_layer.update()
    cam,center,span=common.configure_stage(g,g.ASSET,args.resolution,args.samples)
    bpy.data.objects['STUDIO_ground'].scale=(10,10,10)
    scene=bpy.context.scene
    reference=REPO/'public'/'assets'/'companions'/'pony.png'
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
    scene['reference_sha256']=digest(reference);scene['reference_authority']='Unchanged approved single-view pony.png'
    scene['companion_kind']='pony';scene['companion_name']='Caelo';scene['revision']='sculpt-v002'
    scene['interpretation_limit']='Hidden views inferred; no exact 1:1 claim or mobile acceptance.'
    print('EXPORT Caelo',flush=True)
    report=common.exporter().export_glb(glb,g.ASSET,rig)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    renders=common.render_views(g,cam,center,span,out,'pony',args.views.split(','))
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
    paths=list(ROOT.glob('*.py'))+[SHARED/'common.py',common.SOURCE_ROOT/'asterion'/'sculpt-v001'/'build_sculpt.py',
                                                  common.SOURCE_ROOT/'asterion'/'sculpt-v001'/'rig_delivery.py']
    report['builder_sha256']={p.relative_to(REPO).as_posix():digest(p) for p in paths}
    (out/'build-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'complete':True,'triangles':report['triangles'],'bytes':report['bytes'],
                      'source_meshes':report['editable_source_meshes_preserved']},indent=2),flush=True)


if __name__=='__main__':main()

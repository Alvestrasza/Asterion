"""Fresh Blender import, skin/clip/volume checks and independent review renders."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import common


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--glb',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--resolution',type=int,default=900)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    source=Path(args.glb).resolve();output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
    document=common.glb_json(source)
    master=source.with_suffix('.blend')
    bpy.ops.wm.open_mainfile(filepath=str(master))
    master_clips=set(bpy.data.actions.keys())
    master_meshes=len([o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('ast_part')])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # glTF seconds are converted to frames during import, not afterwards.
    bpy.context.scene.render.fps=30
    bpy.ops.import_scene.gltf(filepath=str(source))
    scene=bpy.context.scene;scene.render.fps=30
    rigs=[o for o in scene.objects if o.type=='ARMATURE']
    if len(rigs)!=1:raise ValueError('Expected one armature')
    rig=rigs[0];actions={a.name:a for a in bpy.data.actions}
    meshes=[o for o in scene.objects if o.type=='MESH' and len(o.vertex_groups)>0]
    for obj in scene.objects:
        if obj.type=='MESH' and obj not in meshes:obj.hide_render=True
    authored_clips={a.get('name') for a in document.get('animations',[])}
    imported_clips=set(actions)
    if 'idle' not in actions:raise ValueError('No idle action')
    common.activate(rig,actions['idle'])
    lo,hi=common.bounds(meshes);span=hi-lo
    unweighted=0;invalid_weights=0;unknown_weights=0;nonfinite=0;max_influences=0;vertices=0;triangles=0
    bone_names=set(rig.data.bones.keys());weighted_groups={}
    for obj in meshes:
        obj.data.calc_loop_triangles();triangles+=len(obj.data.loop_triangles)
        for vertex in obj.data.vertices:
            vertices+=1
            if not all(math.isfinite(v) for v in vertex.co):nonfinite+=1
            weights=[p for p in vertex.groups if p.weight>0]
            if not weights:unweighted+=1
            if abs(sum(p.weight for p in weights)-1)>.002 or any(p.weight<0 or p.weight>1.001 for p in weights):invalid_weights+=1
            max_influences=max(max_influences,len(weights))
            for p in weights:
                name=obj.vertex_groups[p.group].name
                if name not in bone_names:unknown_weights+=1
                weighted_groups[name]=weighted_groups.get(name,0)+1
    animation_samples={}
    for name in common.CLIPS:
        if name not in actions:continue
        action=actions[name];samples=[];start,end=action.frame_range
        for fraction in (0,.25,.5,.75,1):
            frame=int(round(start+(end-start)*fraction));common.activate(rig,action,frame)
            finite=all(math.isfinite(v) for bone in rig.pose.bones for row in bone.matrix for v in row)
            samples.append({'frame':frame,'finite_bone_matrices':finite})
        animation_samples[name]=samples
    common.activate(rig,actions['idle'])
    checks={
      'reopened_master_nine_clips':master_clips==set(common.CLIPS),
      'master_separate_editable_parts':master_meshes>20,
      'one_authored_mesh':len(document.get('meshes',[]))==1,
      'one_imported_skin':len(rigs)==1 and len(document.get('skins',[]))==1,
      'nine_authored_clips':authored_clips==set(common.CLIPS),
      'nine_imported_clips':imported_clips==set(common.CLIPS),
      'no_scene_cameras':not document.get('cameras'),
      'no_scene_lights':'KHR_lights_punctual' not in document.get('extensions',{}),
      'no_image_projection':not document.get('images'),
      'self_contained':all('uri' not in b for b in document.get('buffers',[])),
      'volumetric_xyz':span.x>.7 and span.y>.5 and span.z>2,
      'finite_vertices':nonfinite==0,
      'all_vertices_weighted':unweighted==0,
      'normalized_weights':invalid_weights==0,
      'known_bones':unknown_weights==0,
      'maximum_four_weights':max_influences<=4,
      'finite_nine_animation_samples':len(animation_samples)==9 and all(s['finite_bone_matrices'] for samples in animation_samples.values() for s in samples),
      'both_moving_eyelids':weighted_groups.get('lid.L',0)>100 and weighted_groups.get('lid.R',0)>100,
      'nonempty_mesh':vertices>10000 and triangles>40000,
    }
    g=common.toolkit()
    if scene.world is None:scene.world=bpy.data.worlds.new('Independent import studio')
    cam,center,view_span=common.configure_stage(g,meshes,args.resolution,32)
    kind=source.name.split('-sculpt-')[0]
    renders=common.render_views(g,cam,center,view_span,output,kind,['hero','rear'])
    common.activate(rig,actions['blink'],10)
    renders.update({'blink':common.render_views(g,cam,center,view_span,output,kind+'-blink',['front'])['front']})
    report={
      'asset':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest().upper(),
      'blender':bpy.app.version_string,'bytes':source.stat().st_size,
      'reopened_master_meshes':master_meshes,'reopened_master_clips':sorted(master_clips),
      'vertices':vertices,'triangles':triangles,'bones':len(bone_names),
      'materials':len(document.get('materials',[])),
      'draw_calls':sum(len(m.get('primitives',[])) for m in document.get('meshes',[])),
      'span':list(span),'weighted_groups':weighted_groups,'animation_samples':animation_samples,
      'checks':checks,'passed':all(checks.values()),'renders':renders,
      'human_likeness_accepted':False,'mobile_performance_accepted':False,
      'animation_limit':'Gentle stylized presentation gestures; no biomechanical gait simulation.'}
    (output/'import-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'kind':kind,'passed':report['passed'],'checks':checks,'triangles':triangles},indent=2),flush=True)
    if not report['passed']:raise RuntimeError('Fresh import validation failed: '+str(output))


if __name__=='__main__':main()

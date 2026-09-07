"""Independent Asterion v002 rig, native-groom and fresh-GLB validation.

Run with Blender --background --factory-startup --python this.py --
  --master candidate.blend --glb candidate.glb --baseline original.blend
  --output NEW_DIRECTORY --resolution 1200

No source is saved. Full source action/key/handle/modifier data is fingerprinted
without rounding; imported motion is a separate bounded numerical comparison,
not a claim of byte-identical glTF animation or collision-free motion.
"""
from __future__ import annotations

import argparse
from array import array
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys

try:
    import bpy
    import numpy as np
    from mathutils import Vector
except ModuleNotFoundError:
    bpy=None  # Pure fingerprint helpers remain testable with the stdlib.

ROOT=Path(__file__).resolve().parent
HISTORICAL=ROOT.parent/'sculpt-v001'
CLIPS=('idle','blink','happy','eat','play','pet_reaction','sleep','wake','walk')
FRACTIONS=tuple(i/8 for i in range(9))
MOTION_TOLERANCE=2e-4
HAIR_TOLERANCE=1e-5
TRIANGLE_LOSS_RELATIVE_TOLERANCE=2e-5


def digest(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):result.update(chunk)
    return result.hexdigest().upper()


def plain(value):
    if isinstance(value,float) and not math.isfinite(value):
        return {'nonfinite_float':repr(value)}
    if value is None or isinstance(value,(str,int,float,bool)):return value
    if isinstance(value,set):return sorted(plain(v) for v in value)
    if isinstance(value,dict):return {str(k):plain(v) for k,v in value.items()}
    return [plain(v) for v in value]


def fingerprint(value):
    content=json.dumps(plain(value),sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
    return hashlib.sha256(content).hexdigest().upper()


UI_PROPERTIES={'rna_type','select','select_left_handle','select_right_handle','select_control_point',
               'show_expanded','active','hide','color','color_mode','target_id_type_icon',
               'is_valid','is_empty','co_ui'}


def rna_scalars(item,exclude=()):
    """All persistent scalar/array fields, excluding UI/computed duplicates."""
    result={};excluded=UI_PROPERTIES|set(exclude)
    for prop in item.bl_rna.properties:
        name=prop.identifier
        if name in excluded:continue
        if prop.type in {'BOOLEAN','INT','FLOAT','STRING','ENUM'}:
            result[name]=plain(getattr(item,name))
        elif prop.type=='POINTER':
            value=getattr(item,name)
            if value is not None and isinstance(value,bpy.types.ID):
                result[name]={'id_type':value.id_type,'name':value.name_full}
            elif value is not None and hasattr(value,'name'):
                result[name]={'rna_type':value.bl_rna.identifier,'name':value.name}
    return result


def modifier_data(modifier):
    result=rna_scalars(modifier)
    if hasattr(modifier,'control_points'):
        result['control_points']=[rna_scalars(p) for p in modifier.control_points]
    return result


def curve_fingerprint(curve):
    keys=[rna_scalars(key) for key in curve.keyframe_points]
    samples=[rna_scalars(point) for point in curve.sampled_points]
    payload={'properties':rna_scalars(curve),'group':curve.group.name if curve.group else None,
             'keys':keys,'samples':samples,'modifiers':[modifier_data(m) for m in curve.modifiers]}
    driver=getattr(curve,'driver',None)
    if driver is not None:
        payload['driver']={'properties':rna_scalars(driver),'variables':[
            {'properties':rna_scalars(v),'targets':[rna_scalars(t) for t in v.targets]} for v in driver.variables]}
    finite=all(math.isfinite(v) for key in curve.keyframe_points for field in ('co','handle_left','handle_right') for v in getattr(key,field))
    return {'data_path':curve.data_path,'array_index':curve.array_index,
            'keys':len(keys),'sampled_points':len(samples),'finite_keys':finite,'sha256':fingerprint(payload)}


def action_fingerprint(action):
    payload={'properties':rna_scalars(action,{'name_full','session_uid','users','is_evaluated','is_editable','tag',
             'is_runtime_data','is_embedded_data','is_missing','is_library_indirect','use_extra_user','id_type'}),
             'markers':[rna_scalars(m) for m in action.pose_markers],
             'custom_properties':{k:plain(v) for k,v in action.items() if k!='_RNA_UI'},'slots':[],'layers':[]}
    curves=[]
    for slot in getattr(action,'slots',[]):payload['slots'].append(rna_scalars(slot))
    if getattr(action,'is_action_legacy',False) and hasattr(action,'fcurves'):
        curves=[curve_fingerprint(c) for c in action.fcurves]
        payload['legacy_curves']=curves
    else:
        for layer in action.layers:
            layer_data={'properties':rna_scalars(layer),'strips':[]}
            for strip in layer.strips:
                strip_data={'properties':rna_scalars(strip),'channelbags':[]}
                for bag in strip.channelbags:
                    bag_curves=[curve_fingerprint(c) for c in bag.fcurves];curves.extend(bag_curves)
                    strip_data['channelbags'].append({'slot_handle':bag.slot_handle,
                        'slot_identifier':bag.slot.identifier if bag.slot else None,
                        'groups':[rna_scalars(group) for group in bag.groups], 'curves':bag_curves})
                layer_data['strips'].append(strip_data)
            payload['layers'].append(layer_data)
    return {'sha256':fingerprint(payload),'curve_count':len(curves),'key_count':sum(c['keys'] for c in curves),
            'sampled_point_count':sum(c['sampled_points'] for c in curves),'finite_keys':all(c['finite_keys'] for c in curves),
            'frame_range':list(map(float,action.frame_range)),'structure':payload}


def unique_rig():
    rigs=[obj for obj in bpy.context.scene.objects if obj.type=='ARMATURE']
    if len(rigs)!=1:raise ValueError('Expected exactly one armature, got '+str(len(rigs)))
    return rigs[0]


def rig_fingerprint(rig):
    bone_data=[]
    for bone in sorted(rig.data.bones,key=lambda b:b.name):
        bone_data.append({'name':bone.name,'parent':bone.parent.name if bone.parent else None,
            'matrix_local':plain(bone.matrix_local),'head_local':list(bone.head_local),'tail_local':list(bone.tail_local),
            'settings':rna_scalars(bone,{'head','tail','matrix','length','head_local','tail_local','matrix_local'})})
    rest={'object_matrix_world':plain(rig.matrix_world),'object_matrix_basis':plain(rig.matrix_basis),
          'rotation_mode':rig.rotation_mode,'bones':bone_data}
    behavior={'object_constraints':[rna_scalars(c) for c in rig.constraints],
              'bone_constraints':{b.name:[rna_scalars(c) for c in b.constraints] for b in rig.pose.bones},
              'drivers':[curve_fingerprint(c) for c in rig.animation_data.drivers] if rig.animation_data else []}
    actions={a.name:action_fingerprint(a) for a in bpy.data.actions}
    result={'rest':rest,'rest_sha256':fingerprint(rest),'behavior_sha256':fingerprint(behavior),
            'behavior':behavior,'actions':actions,'bones':len(bone_data),
            'fps':bpy.context.scene.render.fps,'fps_base':bpy.context.scene.render.fps_base}
    result['sha256']=fingerprint(result)
    return result


def activate(rig,action,frame):
    animation=rig.animation_data_create()
    for track in animation.nla_tracks:track.mute=True
    animation.action=action
    if getattr(action,'slots',None):
        slots=list(action.slots);matching=[s for s in slots if rig.name in s.identifier]
        animation.action_slot=matching[0] if matching else slots[0]
    whole=math.floor(frame)
    bpy.context.scene.frame_set(whole,subframe=frame-whole);bpy.context.view_layer.update()


def sample_deformation(rig,actions):
    """World-space skin deformation removes importer-specific bone rest axes."""
    result={}
    for name in CLIPS:
        if name not in actions:continue
        action=actions[name];start,end=map(float,action.frame_range);samples=[]
        for fraction in FRACTIONS:
            frame=start+(end-start)*fraction;activate(rig,action,frame)
            world=rig.matrix_world.copy();inverse=world.inverted()
            matrices={bone.name:[list(row) for row in world@bone.matrix@bone.bone.matrix_local.inverted()@inverse] for bone in rig.pose.bones}
            samples.append({'fraction':fraction,'frame':frame,'matrices':matrices})
        result[name]={'frame_range':[start,end],'duration_seconds':(end-start)/30,'samples':samples}
    return result


def compare_motion(baseline,imported):
    result={}
    for name in CLIPS:
        if name not in baseline or name not in imported:
            result[name]={'passed':False,'reason':'Missing action'};continue
        a,b=baseline[name],imported[name];maximum=0.;finite=True;names_equal=True;worst=None
        for first,last in zip(a['samples'],b['samples']):
            names_equal &= set(first['matrices'])==set(last['matrices'])
            for bone in set(first['matrices'])&set(last['matrices']):
                aa=np.asarray(first['matrices'][bone],dtype=float);bb=np.asarray(last['matrices'][bone],dtype=float)
                valid=bool(np.isfinite(aa).all() and np.isfinite(bb).all());finite &= valid
                if valid:
                    delta=float(np.max(np.abs(aa-bb)))
                    if delta>maximum:maximum=delta;worst={'fraction':first['fraction'],'bone':bone}
        duration=abs(a['duration_seconds']-b['duration_seconds'])
        result[name]={'passed':bool(finite and names_equal and maximum<=MOTION_TOLERANCE and duration<=1e-5),
            'finite':bool(finite),'same_bone_names':bool(names_equal),'max_world_skin_matrix_component_error':maximum,
            'worst_sample':worst,'duration_error_seconds':duration,'sample_count':len(a['samples']),
            'tolerance':MOTION_TOLERANCE,'comparison':'Corresponding normalized times at 30 fps; not action byte equality.'}
    return result


def triangle_count_evidence(authored,imported):
    """Bound tiny importer count loss without claiming per-face degeneracy.

    Sealed v002 companion imports lost 0..21 faces; the largest measured
    fraction was 21/1,325,486 (15.84 ppm). Twenty ppm is a small explicit
    importer allowance, not permission to discard an appreciable mesh region.
    """
    lost=authored-imported
    limit=math.floor(authored*TRIANGLE_LOSS_RELATIVE_TOLERANCE)
    return {'authored':authored,'imported':imported,'exact_equal':authored==imported,
        'triangle_loss':lost,'relative_loss':lost/authored if authored else None,
        'maximum_allowed_loss':limit,'relative_tolerance':TRIANGLE_LOSS_RELATIVE_TOLERANCE,
        'passed':authored>0 and 0<=lost<=limit,
        'limit':'Count difference only; individual omitted triangle degeneracy is not proven by this check.'}


def fresh_import(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps=30;bpy.context.scene.render.fps_base=1.
    bpy.ops.import_scene.gltf(filepath=str(path))
    rig=unique_rig();actions={a.name:a for a in bpy.data.actions}
    helpers={bone.custom_shape for bone in rig.pose.bones if bone.custom_shape is not None}
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and o not in helpers]
    for helper in helpers:helper.hide_render=True
    if not meshes:raise ValueError('No imported character geometry')
    return rig,actions,meshes,helpers


def physics_reasons(obj):
    reasons=[]
    if getattr(obj,'rigid_body',None):reasons.append('rigid body')
    if len(getattr(obj,'particle_systems',[])):reasons.append('particle system')
    for owner in (obj,obj.data):
        animation=getattr(owner,'animation_data',None)
        if animation and (animation.action or len(animation.drivers) or len(animation.nla_tracks)):
            reasons.append('own animation data')
    visited=set()
    def inspect_nodes(tree):
        if tree is None or tree.as_pointer() in visited:return
        visited.add(tree.as_pointer())
        for node in tree.nodes:
            if 'Simulation' in node.bl_idname:reasons.append('geometry-node simulation')
            inspect_nodes(getattr(node,'node_tree',None))
    for modifier in obj.modifiers:
        if modifier.type in {'CLOTH','SOFT_BODY','FLUID','PARTICLE_SYSTEM','DYNAMIC_PAINT'}:reasons.append(modifier.type)
        inspect_nodes(getattr(modifier,'node_group',None))
    return reasons


def world_points(points,matrix):
    matrix=np.asarray(matrix,dtype=np.float64)
    return points@matrix[:3,:3].T+matrix[:3,3]


def inspect_hair():
    scene=bpy.context.scene;graph=bpy.context.evaluated_depsgraph_get()
    native=[o for o in scene.objects if o.get('ast_native_hair')]
    exports=[o for o in scene.objects if o.get('ast_hair_export')]
    details=[];groups={};total_strands=total_points=0
    for obj in native:
        record={'name':obj.name,'group':obj.get('ast_hair_group'),'type':obj.type,'physics':physics_reasons(obj)}
        if obj.type!='CURVES':record['passed']=False;details.append(record);continue
        data=obj.data;count=len(data.points);strands=len(data.curves)
        positions=np.empty(count*3,dtype=np.float32);data.position_data.foreach_get('vector',positions)
        positions=positions.reshape((-1,3)).astype(np.float64)
        offsets=np.empty(len(data.curve_offset_data),dtype=np.int32);data.curve_offset_data.foreach_get('value',offsets)
        radius=data.attributes.get('radius');radii=None
        if radius is not None and radius.domain=='POINT' and radius.data_type=='FLOAT':
            radii=np.empty(count,dtype=np.float32);radius.data.foreach_get('value',radii)
        finite=bool(np.isfinite(positions).all() and radii is not None and np.isfinite(radii).all())
        offsets_valid=bool(len(offsets)==strands+1 and offsets[0]==0 and offsets[-1]==count and np.all(np.diff(offsets)>=2))
        radii_valid=bool(radii is not None and np.all(radii>=0) and np.any(radii>0))
        world=obj.evaluated_get(graph).matrix_world.copy();world_finite=all(math.isfinite(v) for row in world for v in row)
        record.update({'strands':strands,'points':count,'finite_points_radii':finite,'valid_offsets':offsets_valid,
            'nonnegative_nonzero_radii':radii_valid,'finite_transform':world_finite,
            'passed':finite and offsets_valid and radii_valid and world_finite and not record['physics']})
        total_strands+=strands;total_points+=count
        group=record['group']
        matches=[o for o in exports if o.get('ast_hair_group')==group]
        pair={'native_object':obj.name,'export_objects':[o.name for o in matches],'passed':False}
        if group and group not in groups and len(matches)==1 and matches[0].type=='MESH' and finite and offsets_valid:
            tube=matches[0];sides=int(tube.get('ast_hair_sides',0));points_per=int(tube.get('ast_hair_points_per_strand',0))
            pair.update({'sides':sides,'points_per_strand':points_per})
            if sides>=3 and points_per>=2 and np.all(np.diff(offsets)==points_per):
                evaluated=tube.evaluated_get(graph);mesh=evaluated.to_mesh()
                try:
                    pair['tube_vertices']=len(mesh.vertices);expected=count*sides
                    pair['expected_ring_vertices']=expected
                    if len(mesh.vertices)==expected:
                        vertices=np.empty(expected*3,dtype=np.float32);mesh.vertices.foreach_get('co',vertices)
                        tube_world=world_points(vertices.reshape((-1,3)),evaluated.matrix_world)
                        rings=tube_world.reshape((count,sides,3));centers=rings.mean(axis=1)
                        native_world=world_points(positions,world)
                        center_error=float(np.max(np.linalg.norm(centers-native_world,axis=1)))
                        local=world_points(tube_world,world.inverted()).reshape((count,sides,3))
                        radial=np.linalg.norm(local-positions[:,None,:],axis=2)
                        radius_error=float(np.max(np.abs(radial-radii[:,None])))
                        basis_scale=float(np.linalg.norm(np.asarray(world,dtype=float)[:3,:3],ord=2))
                        world_radius_bound=radius_error*basis_scale
                        pair.update({'max_center_error_world':center_error,'max_radius_error_local':radius_error,
                            'max_radius_error_world_bound':world_radius_bound,'tolerance_world':HAIR_TOLERANCE,
                            'passed':bool(np.isfinite(tube_world).all() and center_error<=HAIR_TOLERANCE and world_radius_bound<=HAIR_TOLERANCE)})
                finally:evaluated.to_mesh_clear()
        if group in groups:pair['passed']=False;pair['reason']='Duplicate native group identifier'
        groups[group or obj.name]=pair;details.append(record)
    unique_native={o.get('ast_hair_group') for o in native};unique_exports={o.get('ast_hair_group') for o in exports}
    return {'native_objects':details,'native_strands':total_strands,'native_points':total_points,
        'export_meshes':len(exports),'correspondence':groups,
        'checks':{'native_curves_present':bool(native),'at_least_1000_native_strands':total_strands>=1000,
            'native_points_radii_static_finite':bool(details) and all(r['passed'] for r in details),
            'matching_native_export_groups':None not in unique_native and unique_native==unique_exports,
            'all_native_points_match_export_tube_rings':bool(groups) and all(p['passed'] for p in groups.values())}}


def glb_document(path):
    with Path(path).open('rb') as stream:
        magic,version,length=struct.unpack('<III',stream.read(12))
        size,kind=struct.unpack('<II',stream.read(8))
        if magic!=0x46546C67 or version!=2 or kind!=0x4E4F534A or length!=Path(path).stat().st_size:
            raise ValueError('Invalid GLB 2.0 header')
        return json.loads(stream.read(size))


def inspect_import(meshes,rig):
    names=set(rig.data.bones.keys());lo=np.full(3,np.inf);hi=np.full(3,-np.inf)
    report={'vertices':0,'triangles':0,'nonfinite_vertices':0,'nonfinite_transforms':0,
        'unweighted_vertices':0,'invalid_weights':0,'unknown_weights':0,'over_four_weights':0,'max_influences':0}
    for obj in meshes:
        mesh=obj.data;mesh.calc_loop_triangles();report['triangles']+=len(mesh.loop_triangles)
        report['vertices']+=len(mesh.vertices)
        values=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',values)
        points=world_points(values.reshape((-1,3)),obj.matrix_world)
        finite=np.isfinite(points).all(axis=1);report['nonfinite_vertices']+=int(np.count_nonzero(~finite))
        if finite.any():lo=np.minimum(lo,points[finite].min(axis=0));hi=np.maximum(hi,points[finite].max(axis=0))
        if not all(math.isfinite(v) for row in obj.matrix_world for v in row):report['nonfinite_transforms']+=1
        group_names={g.index:g.name for g in obj.vertex_groups}
        for vertex in mesh.vertices:
            assignments=list(vertex.groups)
            positive=[g for g in assignments if math.isfinite(g.weight) and g.weight>0]
            if not positive:report['unweighted_vertices']+=1
            if len(positive)>4:report['over_four_weights']+=1
            report['max_influences']=max(report['max_influences'],len(positive))
            if any(not math.isfinite(g.weight) or g.weight<0 or g.weight>1.001 for g in assignments) or abs(sum(g.weight for g in positive)-1)>.002:
                report['invalid_weights']+=1
            report['unknown_weights']+=sum(group_names.get(g.group) not in names for g in positive)
    report['bounds_min']=lo.tolist() if np.isfinite(lo).all() else None
    report['bounds_max']=hi.tolist() if np.isfinite(hi).all() else None
    report['span']=(hi-lo).tolist() if np.isfinite(lo).all() and np.isfinite(hi).all() else None
    return report


def compare_source(baseline,candidate):
    return {'same_rest_hierarchy_and_transforms':baseline['rest_sha256']==candidate['rest_sha256'],
        'same_constraints_and_drivers':baseline['behavior_sha256']==candidate['behavior_sha256'],
        'exact_nine_action_names':set(baseline['actions'])==set(candidate['actions'])==set(CLIPS),
        'all_nine_complete_action_data_unchanged':all(name in baseline['actions'] and name in candidate['actions'] and
            baseline['actions'][name]['sha256']==candidate['actions'][name]['sha256'] for name in CLIPS),
        'source_22_bones':baseline['bones']==candidate['bones']==22,
        'source_fps_unchanged_30':baseline['fps']==candidate['fps']==30 and baseline['fps_base']==candidate['fps_base']==1.0,
        'finite_complete_source_keys':all(a['finite_keys'] for a in candidate['actions'].values())}


def render_import(output,resolution,rig,actions):
    spec=importlib.util.spec_from_file_location('historical_asterion_stage',HISTORICAL/'build_sculpt.py')
    stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)
    scene=bpy.context.scene
    if scene.world is None:scene.world=bpy.data.worlds.new('Independent Asterion refinement studio')
    cam=stage.stage(resolution,48)
    activate(rig,actions['idle'],actions['idle'].frame_range[0])
    renders=stage.render(cam,output,['hero','rear','face'])
    blink=actions['blink'];start,end=blink.frame_range;activate(rig,blink,(start+end)/2)
    blink_out=output/'blink';blink_out.mkdir()
    renders['closed_blink_front']=stage.render(cam,blink_out,['front'])['front']
    return {key:{'path':value,'sha256':digest(value)} for key,value in renders.items()}


def main():
    if bpy is None:raise RuntimeError('Run this validator inside Blender')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--master',required=True);parser.add_argument('--glb',required=True)
    parser.add_argument('--baseline',default=str(HISTORICAL/'asterion-sculpt-v001.blend'))
    parser.add_argument('--baseline-glb',default=str(ROOT.parents[4]/'public/assets/3d/asterion/asterion-sculpt-v001.glb'),
                        help='Unchanged historical export for like-for-like importer motion comparison')
    parser.add_argument('--output',required=True);parser.add_argument('--resolution',type=int,default=1200)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    master,glb,baseline,baseline_glb,output=map(lambda p:Path(p).resolve(),(args.master,args.glb,args.baseline,args.baseline_glb,args.output))
    if args.resolution<128:raise ValueError('Resolution must be >=128')
    if output.exists() and any(output.iterdir()):raise FileExistsError('Use a fresh evidence directory')
    hashes={str(p):digest(p) for p in (baseline,baseline_glb,master,glb)}
    output.mkdir(parents=True,exist_ok=True)
    print('VALIDATE original complete rig/action fingerprint',flush=True)
    bpy.ops.wm.open_mainfile(filepath=str(baseline));baseline_rig=unique_rig()
    original=rig_fingerprint(baseline_rig)
    original_motion=sample_deformation(baseline_rig,{a.name:a for a in bpy.data.actions})
    print('VALIDATE historical GLB import calibration (same importer/FPS)',flush=True)
    historical_rig,historical_actions,_,_=fresh_import(baseline_glb)
    historical_motion=sample_deformation(historical_rig,historical_actions)
    historical_schema_ok=len(historical_rig.data.bones)==22 and set(historical_actions)==set(CLIPS)
    source_export_diagnostic=compare_motion(original_motion,historical_motion)
    print('VALIDATE candidate complete rig/actions and native hair',flush=True)
    bpy.ops.wm.open_mainfile(filepath=str(master));candidate_rig=unique_rig()
    candidate=rig_fingerprint(candidate_rig);source_checks=compare_source(original,candidate)
    solids=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('ast_part') and not o.get('ast_hair_export')]
    source_checks['separate_editable_body_and_armor']=len(solids)>20 and any(o.get('ast_part')=='body' for o in solids) and any(str(o.get('ast_part','')).startswith('armor.') for o in solids)
    if 'idle' in bpy.data.actions:activate(candidate_rig,bpy.data.actions['idle'],bpy.data.actions['idle'].frame_range[0])
    hair=inspect_hair()
    print('VALIDATE fresh GLB import',flush=True)
    document=glb_document(glb)
    rig,actions,meshes,helpers=fresh_import(glb)
    geometry=inspect_import(meshes,rig);candidate_motion=sample_deformation(rig,actions)
    motion=compare_motion(historical_motion,candidate_motion)
    primitives=[p for m in document.get('meshes',[]) for p in m.get('primitives',[])]
    authored_triangles=sum(document['accessors'][p['indices']]['count']//3 for p in primitives)
    triangle_evidence=triangle_count_evidence(authored_triangles,geometry['triangles'])
    checks=dict(source_checks);checks.update(hair['checks'])
    checks.update({'one_glb_mesh_and_skin':len(document.get('meshes',[]))==len(document.get('skins',[]))==1,
        '22_imported_and_authored_bones':len(rig.data.bones)==22 and len(document.get('skins',[{}])[0].get('joints',[]))==22,
        'nine_imported_and_authored_clips':set(actions)=={a.get('name') for a in document.get('animations',[])}==set(CLIPS),
        'approximately_five_million_triangles':4500000<=authored_triangles<=5500000 and 4500000<=geometry['triangles']<=5500000,
        'bounded_importer_triangle_count_difference':triangle_evidence['passed'],
        'historical_glb_22_bones_nine_clips':historical_schema_ok,
        'one_imported_character_mesh':len(meshes)==1,'under_40_material_primitives':0<len(primitives)<40,
        'all_primitives_triangles_skinned':all(p.get('mode',4)==4 and 'JOINTS_0' in p['attributes'] and 'WEIGHTS_0' in p['attributes'] for p in primitives),
        'no_images_or_projection':not document.get('images'),'no_cameras':not document.get('cameras'),
        'no_lights':'KHR_lights_punctual' not in document.get('extensions',{}),
        'self_contained':all('uri' not in b for b in document.get('buffers',[])),
        'finite_imported_geometry':geometry['nonfinite_vertices']==geometry['nonfinite_transforms']==0,
        'all_imported_vertices_normalized_known_four_weights':all(geometry[k]==0 for k in ('unweighted_vertices','invalid_weights','unknown_weights','over_four_weights')),
        'imported_motion_matches_historical_export_samples':all(m['passed'] for m in motion.values())})
    report={'schema':'asterion-refinement-independent-validation-v1','master':str(master),'glb':str(glb),
        'baseline':str(baseline),'master_sha256':hashes[str(master)],'glb_sha256':hashes[str(glb)],
        'baseline_sha256':hashes[str(baseline)],'baseline_glb':str(baseline_glb),
        'baseline_glb_sha256':hashes[str(baseline_glb)],'validator_sha256':digest(Path(__file__)),
        'blender':bpy.app.version_string,'baseline_fingerprint':original,'candidate_fingerprint':candidate,
        'editable_solid_meshes':len(solids),'native_groom':hair,'geometry':geometry,
        'triangle_count_evidence':triangle_evidence,'imported_motion_comparison':motion,
        'source_to_historical_export_diagnostic':source_export_diagnostic,
        'historical_imported_motion_sha256':fingerprint(historical_motion),
        'candidate_imported_motion_sha256':fingerprint(candidate_motion),
        'historical_imported_frame_ranges':{k:v['frame_range'] for k,v in historical_motion.items()},
        'candidate_imported_frame_ranges':{k:v['frame_range'] for k,v in candidate_motion.items()},
        'included_imported_meshes':[o.name for o in meshes],'excluded_custom_shape_helpers':[o.name for o in helpers],
        'checks':checks,'renders':{},'human_likeness_accepted':False,'mobile_performance_accepted':False,
        'animation_comparison_limit':'Complete source RNA action curves/keys/handles/modifiers are hashed without rounding. Candidate imported motion is compared to freshly imported historical GLB at nine normalized times per clip and 30 fps, with tight 2e-4 world skin-matrix tolerance. Original source-to-historical-export discrepancies are diagnostic only, not acceptance gates. This is not glTF byte equality or collision/gait acceptance.'}
    path=output/'refinement-validation.json'
    def save_report():
        report['checks']['input_files_unchanged']=all(digest(Path(p))==sha for p,sha in hashes.items())
        report['passed']=all(report['checks'].values())
        path.write_text(json.dumps(plain(report),indent=2,allow_nan=False)+'\n',encoding='utf-8')
    save_report()
    if checks['finite_imported_geometry'] and {'idle','blink'}<=set(actions):
        print('VALIDATE independent hero/rear/face/closed-blink renders',flush=True)
        report['renders']=render_import(output,args.resolution,rig,actions)
    save_report()
    print(json.dumps({'passed':report['passed'],'triangles':geometry['triangles'],
        'native_strands':hair['native_strands'],'report':str(path)},indent=2),flush=True)
    if not report['passed']:raise RuntimeError('Refinement acceptance checks failed; see '+str(path))


if __name__=='__main__':main()

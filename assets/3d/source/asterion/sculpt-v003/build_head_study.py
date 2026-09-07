"""Versioned head-hair removal, fresh import checks and staged local handoff.

Only four head-groom pairs are removed from an in-memory copy of v002. All
retained source geometry and original animation data must remain identical.
"""
import argparse
from array import array
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[4]
V1=ROOT.parent/'sculpt-v001'
V2=ROOT.parent/'sculpt-v002'
GROUPS={'mane.L','mane.R','cheek.L','cheek.R'}
MASTER=V2/'asterion-sculpt-v002.blend'
MODEL=REPO/'public/assets/3d/asterion/asterion-sculpt-v002.glb'
REFERENCE=REPO/'assets/3d/reference/asterion/sculpt-v002/asterion-approved-turnaround.png'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
def rel(path):return Path(path).relative_to(REPO).as_posix()
def dump(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def head_hair(obj):return bool(obj.get('ast_native_hair') or obj.get('ast_hair_export')) and obj.get('ast_hair_group') in GROUPS


def geometry_signature(obj):
    """Stored positions, topology, colors, UVs, weights and attachment data."""
    result=hashlib.sha256()
    def field(collection,property,width,code='f'):
        values=array(code,[0])*(len(collection)*width)
        collection.foreach_get(property,values);result.update(values.tobytes())
    settings={'name':obj.name,'type':obj.type,'basis':list(map(list,obj.matrix_basis)),
        'inverse':list(map(list,obj.matrix_parent_inverse)),
        'parent':obj.parent.name if obj.parent else None,'parent_type':obj.parent_type,
        'parent_bone':obj.parent_bone,'materials':[m.name for m in obj.data.materials],
        'groups':[g.name for g in obj.vertex_groups] if obj.type=='MESH' else []}
    result.update(json.dumps(settings,sort_keys=True).encode())
    if obj.type=='MESH':
        field(obj.data.vertices,'co',3)
        field(obj.data.loops,'vertex_index',1,'i')
        field(obj.data.polygons,'loop_start',1,'i');field(obj.data.polygons,'loop_total',1,'i')
        field(obj.data.polygons,'material_index',1,'i')
        for color in obj.data.color_attributes:
            result.update((color.name+color.domain+color.data_type).encode());field(color.data,'color',4)
        for uv in obj.data.uv_layers:
            result.update(uv.name.encode());field(uv.data,'uv',2)
        weights=bytearray()
        for vertex in obj.data.vertices:
            weights.extend(struct.pack('<I',len(vertex.groups)))
            for group in vertex.groups:weights.extend(struct.pack('<If',group.group,group.weight))
        result.update(weights)
    elif obj.type=='CURVES':
        field(obj.data.position_data,'vector',3)
        field(obj.data.curve_offset_data,'value',1,'i')
        field(obj.data.attributes['radius'].data,'value',1)
        field(obj.data.attributes['material_index'].data,'value',1,'i')
    else:raise ValueError('Unexpected character object type')
    return result.hexdigest().upper()


def build(out,resolution,samples):
    import bpy
    sys.path.insert(0,str(V1));import build_sculpt as stage;import rig_delivery
    sys.path.insert(0,str(V2));import validate_refinement as verify
    if out.exists():raise FileExistsError('Choose a fresh review directory')
    dependencies=[Path(__file__),V1/'build_sculpt.py',V1/'rig_delivery.py',V2/'validate_refinement.py']
    input_hashes={rel(p):sha(p) for p in [MASTER,MODEL,REFERENCE]+dependencies}
    out.mkdir(parents=True);source_views=out/'source-views';source_views.mkdir()
    print('LOAD immutable v002 baseline',flush=True)
    bpy.ops.wm.open_mainfile(filepath=str(MASTER));bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene;rig=verify.unique_rig()
    original_rig=verify.rig_fingerprint(rig)
    verify.activate(rig,bpy.data.actions['idle'],1)
    objects=[o for o in scene.objects if o.type in {'MESH','CURVES'} and o.get('ast_part')]
    removed=[o for o in objects if head_hair(o)]
    if len(removed)!=8 or any(sum(o.get('ast_hair_group')==group for o in removed)!=2 for group in GROUPS):
        raise ValueError('Expected exactly four native/export head-groom pairs')
    original_geometry={o.name:geometry_signature(o) for o in objects if o not in removed}
    removed_report=[{'name':o.name,'type':o.type,'group':o['ast_hair_group']} for o in removed]
    removed_triangles=0
    for obj in removed:
        if obj.type=='MESH':obj.data.calc_loop_triangles();removed_triangles+=len(obj.data.loop_triangles)
        bpy.data.objects.remove(obj,do_unlink=True)
    stage.ASSET=[o for o in scene.objects if o.type=='MESH' and o.get('ast_part')]
    count=0
    for obj in stage.ASSET:obj.data.calc_loop_triangles();count+=len(obj.data.loop_triangles)
    print('EXPORT head-hair-free model',count,'triangles',flush=True)
    glb=out/'asterion-sculpt-v003.glb';master=out/'asterion-sculpt-v003.blend'
    exported=rig_delivery.export_glb(glb,stage.ASSET,rig)
    scene['asset']='asterion-sculpt-v003'
    scene['head_hair_policy']='Temporary head-hair-free study; full groom preserved in immutable v002'
    scene.cycles.samples=samples;scene.render.resolution_x=resolution;scene.render.resolution_y=resolution
    renders=stage.render(scene.camera,source_views,['hero','front','side','rear','face'])
    scene.camera.location=(8,-12,5.8);stage.point_at(scene.camera,(0,.25,2.88));scene.camera.data.ortho_scale=6.8
    verify.activate(rig,bpy.data.actions['idle'],1);stage.active(bpy.data.objects['AST_Sculpted_head'])
    bpy.ops.wm.save_as_mainfile(filepath=str(master))

    print('REOPEN saved master and compare all retained geometry and actions',flush=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=str(master));rig=verify.unique_rig()
    candidate_rig=verify.rig_fingerprint(rig);checks=verify.compare_source(original_rig,candidate_rig)
    verify.activate(rig,bpy.data.actions['idle'],1)
    retained=[o for o in bpy.context.scene.objects if o.type in {'MESH','CURVES'} and o.get('ast_part')]
    retained_geometry={o.name:geometry_signature(o) for o in retained}
    hair=verify.inspect_hair();checks.update(hair['checks'])
    checks.update({'all_retained_source_geometry_identical':original_geometry==retained_geometry,
        'no_head_hair_objects':not any(head_hair(o) for o in bpy.data.objects),
        'only_tail_groom_remains':{o.get('ast_hair_group') for o in retained if o.get('ast_native_hair') or o.get('ast_hair_export')}=={'tail'}})
    print('FRESH import of baseline and candidate GLBs',flush=True)
    old_rig,old_actions,_,_=verify.fresh_import(MODEL)
    old_motion=verify.sample_deformation(old_rig,old_actions)
    imported_rig,actions,meshes,_=verify.fresh_import(glb)
    geometry=verify.inspect_import(meshes,imported_rig)
    motion=verify.compare_motion(old_motion,verify.sample_deformation(imported_rig,actions))
    document=verify.glb_document(glb);old_document=verify.glb_document(MODEL)
    primitives=[p for m in document['meshes'] for p in m['primitives']]
    old_count=sum(old_document['accessors'][p['indices']]['count']//3 for m in old_document['meshes'] for p in m['primitives'])
    checks.update({'triangle_count_is_exact_head_hair_subtraction':geometry['triangles']==exported['triangles']==count==old_count-removed_triangles,
        'same_exported_materials':{m['name']:m for m in document['materials']}=={m['name']:m for m in old_document['materials']},
        'one_mesh_and_skin':len(meshes)==len(document['meshes'])==len(document['skins'])==1,
        '22_bones_nine_clips':len(imported_rig.data.bones)==22 and set(actions)==set(verify.CLIPS),
        'all_primitives_skinned':all('JOINTS_0' in p['attributes'] and 'WEIGHTS_0' in p['attributes'] for p in primitives),
        'finite_normalized_geometry':all(geometry[k]==0 for k in ('nonfinite_vertices','nonfinite_transforms','unweighted_vertices','invalid_weights','unknown_weights','over_four_weights')),
        'imported_motion_unchanged':all(m['passed'] for m in motion.values()),
        'self_contained_no_images_cameras_lights':all('uri' not in b for b in document['buffers']) and not document.get('images') and not document.get('cameras') and 'KHR_lights_punctual' not in document.get('extensions',{})})
    imported=out/'import-review';imported.mkdir()
    imported_views=verify.render_import(imported,min(resolution,1200),imported_rig,actions)
    render_records={}
    for name,path in renders.items():render_records['source.'+name]={'file':Path(path).relative_to(out).as_posix(),'sha256':sha(path)}
    for name,item in imported_views.items():render_records['import.'+name]={'file':Path(item['path']).relative_to(out).as_posix(),'sha256':item['sha256']}
    checks['baseline_and_dependencies_unchanged']=all(sha(REPO/path)==digest for path,digest in input_hashes.items())
    report={'schema':'asterion-head-hair-study-v003','source_sha256':sha(master),'model_sha256':sha(glb),
        'baseline_source':rel(MASTER),'baseline_model':rel(MODEL),'input_sha256':input_hashes,
        'builder_sha256':{rel(p):input_hashes[rel(p)] for p in dependencies},
        'blender':bpy.app.version_string,'triangles':count,'removed_triangles':removed_triangles,
        'bytes':glb.stat().st_size,'removed_objects':removed_report,'geometry':geometry,
        'retained_geometry_sha256':retained_geometry,'tail_hair':hair,'motion_comparison':motion,
        'actions_sha256':{name:data['sha256'] for name,data in candidate_rig['actions'].items()},
        'rest_rig_sha256':candidate_rig['rest_sha256'],'checks':checks,'passed':all(checks.values()),'renders':render_records,
        'materials':len(document['materials']),'clips':list(actions),
        'human_likeness_accepted':False,'mobile_performance_accepted':False}
    dump(out/'validation.json',report)
    print(json.dumps({'passed':report['passed'],'triangles':count,'removed_triangles':removed_triangles,'tail_strands':hair['native_strands']},indent=2),flush=True)
    if not report['passed']:raise RuntimeError('Head study verification failed')


def deliver(work):
    shared=REPO/'assets/3d/source/companions/sculpt-v002/deliver.py'
    spec=importlib.util.spec_from_file_location('head_study_staging',shared)
    staging=importlib.util.module_from_spec(spec);sys.modules[spec.name]=staging;spec.loader.exec_module(staging)
    report=json.loads((work/'validation.json').read_text())
    if report.get('passed') is not True or not report.get('checks') or not all(v is True for v in report['checks'].values()):
        raise ValueError('All fresh validation checks must pass')
    for path,digest in report['input_sha256'].items():
        source=(REPO/path).resolve()
        if not source.is_relative_to(REPO) or sha(source)!=digest:raise ValueError('Baseline or builder changed')
    items=[]
    def add(target,content):
        if not target.resolve().is_relative_to(REPO):raise ValueError('Target outside repository')
        items.append(staging.Artifact(target,content))
    master=ROOT/'asterion-sculpt-v003.blend';model=REPO/'public/assets/3d/asterion/asterion-sculpt-v003.glb'
    for target,key in [(master,'source_sha256'),(model,'model_sha256')]:
        content=(work/target.name).read_bytes()
        if staging.sha256(content)!=report[key]:raise ValueError('Validated artifact changed')
        add(target,content)
    review=REPO/'assets/3d/reference/asterion/sculpt-v003'
    clean=dict(report);clean['renders']={}
    for name,item in report['renders'].items():
        source=(work/item['file']).resolve()
        if not source.is_relative_to(work):raise ValueError('Render outside review')
        content=source.read_bytes()
        if staging.sha256(content)!=item['sha256']:raise ValueError('Validated render changed')
        target=review/item['file'];add(target,content)
        clean['renders'][name]={'file':rel(target),'sha256':item['sha256']}
    validation=review/'validation.json';add(validation,staging.json_bytes(clean))
    add(review/'asterion-approved-turnaround.png',REFERENCE.read_bytes())
    manifest={'schema':'asterion-local-head-study-v003','version':'sculpt-v003','name':'Asterion','kind':'asterion',
        'source':rel(master),'model':rel(model),'reference':rel(review/'asterion-approved-turnaround.png'),
        'source_sha256':report['source_sha256'],'model_sha256':report['model_sha256'],'reference_sha256':sha(REFERENCE),
        'builder_sha256':report['builder_sha256'],'validation':rel(validation),
        'triangles':report['triangles'],'bytes':report['bytes'],'vertices':report['geometry']['vertices'],
        'materials':report['materials'],'clips':report['clips'],'head_hair_removed':True,
        'hair_groups':['tail'],'hair_strands':report['tail_hair']['native_strands'],'native_hair':True,
        'animations_unchanged':True,'retained_geometry_unchanged':True,'hair_physics':False,
        'human_likeness_accepted':False,'mobile_performance_accepted':False,
        'provenance':'Temporary head-hair-free copy of unchanged local sculpt-v002. Tail hair, retained anatomy and animations preserved.'}
    add(ROOT/'manifest.json',staging.json_bytes(manifest))
    if len({i.target for i in items})!=len(items):raise ValueError('Duplicate targets')
    observed={}
    for item in items:
        current=staging.existing_hash(item.target)
        if current is not None and current!=item.checksum:raise FileExistsError('Different existing artifact')
        observed[item.target]=current
    staging.execute_delivery(staging.DeliveryPlan(REPO,tuple(items),manifest,observed))
    print(json.dumps({'model':manifest['model'],'triangles':manifest['triangles'],'head_hair_removed':True},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output');parser.add_argument('--deliver')
    parser.add_argument('--resolution',type=int,default=1600);parser.add_argument('--samples',type=int,default=64)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:])
    if bool(args.output)==bool(args.deliver):parser.error('Choose build --output or --deliver')
    if args.output:build(Path(args.output).resolve(),args.resolution,args.samples)
    else:deliver(Path(args.deliver).resolve())

"""Independent source-scope fingerprints: sculpture, shaders and eyelid pivots."""
import re


def material_payload(material, verify):
    volatile = {'users', 'session_uid', 'is_evaluated', 'is_editable', 'tag', 'name_full',
        'is_runtime_data', 'is_missing', 'use_extra_user', 'use_fake_user', 'preview'}
    payload = {'properties': verify.rna_scalars(material, volatile)}
    if material.use_nodes:
        tree = material.node_tree
        payload['nodes'] = []
        for node in tree.nodes:
            record = {'properties': verify.rna_scalars(node, volatile | {'select', 'dimensions', 'location', 'width', 'height'}),
                'inputs': [verify.rna_scalars(s, {'is_linked', 'is_inactive', 'is_unavailable', 'hide', 'enabled'}) for s in node.inputs],
                'outputs': [verify.rna_scalars(s, {'is_linked', 'is_inactive', 'is_unavailable', 'hide', 'enabled'}) for s in node.outputs]}
            if hasattr(node, 'color_ramp'):
                ramp = node.color_ramp
                record['ramp'] = {'properties': verify.rna_scalars(ramp),
                    'stops': [{'position': e.position, 'color': list(e.color)} for e in ramp.elements]}
            if hasattr(node, 'mapping'):
                record['mapping'] = {'properties': verify.rna_scalars(node.mapping),
                    'curves': [[verify.rna_scalars(p) for p in c.points] for c in node.mapping.curves]}
            payload['nodes'].append(record)
        payload['links'] = sorted((l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier) for l in tree.links)
    return payload


def snapshot(signatures, verify):
    import bpy
    objects = [o for o in bpy.context.scene.objects if o.type in ('MESH', 'CURVES') and o.get('ast_part')]
    geometry = {o.name: signatures.geometry_signature(o) for o in objects}
    materials = {m.name: verify.fingerprint(material_payload(m, verify)) for o in objects for m in o.data.materials}
    bindings = {o.name: [m.name for m in o.data.materials] for o in objects}
    roles = {o.name: {'part': str(o.get('ast_part')), 'component': o.get('asterion_component'), 'type': o.type} for o in objects}
    pivots = {o.name: list(o['ast_lid_pivot']) for o in objects if 'ast_lid_pivot' in o}
    return dict(geometry=geometry, materials=materials, bindings=bindings, roles=roles, pivots=pivots)


def face_name(name, role):
    # A head attachment is not by itself a face: horns, ears, hair and diadems
    # are deliberately outside this round even though they share the head bone.
    if role.get('type') != 'MESH' or role.get('component') != 'body': return False
    if role.get('part') not in ('head', 'eye.L', 'eye.R', 'lid.L', 'lid.R'): return False
    lowered = name.lower()
    if re.search(r'horn|diadem|forehead_lance|hair|crown|mane|(^|_)ear[_.]|leaf_ear|ear_swept', lowered): return False
    return name == 'AST_temple_overlapping_lamellae' or bool(re.search(r'head|face|muzzle|eye|lid|lash|brow|nose|nostril|mouth|smile|lip|chin|cheek|tusk|whisker|fang|glint|socket|orbital|cornea|sclera|catchlight|pinlight|nares|philtrum|snout|tear', lowered))


def scope(before, after, changes):
    allowed = set(changes['face_objects'])
    removed = set(changes.get('removed_face_objects', []))
    all_roles = {**before['roles'], **after['roles']}
    protected = set(before['geometry']) - allowed
    shaders = {m for name in protected for m in before['bindings'][name]}
    removed_actual = set(before['geometry'])-set(after['geometry'])
    added_actual = set(after['geometry'])-set(before['geometry'])
    checks = {
        'explicit_face_only_allowlist': bool(allowed) and all(name in all_roles and face_name(name, all_roles[name]) for name in allowed),
        'all_unedited_source_objects_retained': removed_actual == removed and removed <= allowed and added_actual <= allowed,
        'nonface_geometry_unchanged': all(before['geometry'][name] == after['geometry'].get(name) for name in protected),
        'nonface_materials_unchanged': all(before['materials'][name] == after['materials'].get(name) for name in shaders),
        'original_lid_pivots_unchanged': before['pivots'] == after['pivots'],
        'meaningful_face_geometry_refinement': sum(before['geometry'].get(name) != after['geometry'].get(name) for name in allowed) >= 3 and
            sum(e.get('max_displacement', 0) > 1e-4 or e.get('new_vertices', 0) > 0 for e in changes['edited_objects']) >= 3}
    return dict(checks=checks, protected_geometry_sha256={name: before['geometry'][name] for name in sorted(protected)},
        protected_material_sha256={name: before['materials'][name] for name in sorted(shaders)},
        original_face_geometry_sha256={name: before['geometry'][name] for name in sorted(allowed) if name in before['geometry']},
        candidate_face_geometry_sha256={name: after['geometry'][name] for name in sorted(allowed) if name in after['geometry']},
        original_lid_pivots=before['pivots'], candidate_lid_pivots=after['pivots'],
        protected_object_count=len(protected), protected_material_count=len(shaders),
        invalid_face_objects=sorted(name for name in allowed if name not in all_roles or not face_name(name, all_roles[name])))


def evaluate_blinks(verify, rig, objects):
    import bpy
    import numpy as np
    records = []
    for frame in (1, 5, 7, 8, 9, 10, 12, 16, 24):
        verify.activate(rig, bpy.data.actions['blink'], frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        count, invalid = 0, 0
        for obj in objects:
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            try:
                xyz = np.empty(len(mesh.vertices)*3, dtype=np.float32)
                mesh.vertices.foreach_get('co', xyz)
                invalid += int(np.count_nonzero(~np.isfinite(xyz)))
                count += len(mesh.vertices)
            finally:
                evaluated.to_mesh_clear()
        records.append({'frame': frame, 'evaluated_vertices': count, 'nonfinite_coordinates': invalid})
    verify.activate(rig, bpy.data.actions['idle'], 1)
    return records

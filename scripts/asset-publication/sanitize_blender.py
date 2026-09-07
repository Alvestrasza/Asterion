"""Create metadata-only Blender publication copies with exact semantic guards.

Run inside Blender with --background --factory-startup --disable-autoexec.
Inputs are never saved. Output collisions are refused unless explicitly opened
for read-only verification. Reports contain asset hashes and field names, never
the private metadata values being removed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import traceback
from datetime import datetime, timezone

import bpy
import numpy as np


SCHEMA = 'asterion.blender-publication-copy.v1'
VOLATILE = {
    'rna_type', 'id_data', 'original', 'users', 'session_uid', 'tag', 'preview',
    'is_evaluated', 'is_runtime_data', 'is_updated', 'is_updated_data',
    'is_updated_transform', 'is_editable', 'is_missing', 'name_full',
}
READONLY_SCALARS = {'name', 'type', 'identifier', 'index', 'handle', 'data_type', 'domain'}
UI_COLLECTIONS = {'screens', 'workspaces', 'window_managers', 'all_ids'}
MESH_BULK = {'vertices', 'edges', 'loops', 'polygons', 'loop_triangles', 'loop_triangle_polygons', 'attributes',
             'color_attributes', 'vertex_colors', 'uv_layers', 'materials',
             'corner_normals', 'vertex_normals', 'polygon_normals'}
PATH_PATTERN = re.compile(r'(^[A-Za-z]:[/\\]|(^|[/\\])\.private([/\\]|$)|^/(?:home|Users|tmp|mnt|media|Volumes)/)', re.I)


def sha_file(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(data)
    return result.hexdigest().upper()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def id_reference(value):
    return [value.bl_rna.identifier, value.name]


def plain(value):
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return {'float_hex': value.hex()}
    if isinstance(value, bytes):
        return {'bytes_sha256': hashlib.sha256(value).hexdigest(), 'bytes': len(value)}
    if isinstance(value, bpy.types.ID):
        return {'id': id_reference(value)}
    if isinstance(value, set):
        return sorted(value)
    return [plain(item) for item in value]


def bulk(collection, property_name, dtype, width):
    data = np.empty(len(collection) * width, dtype=dtype)
    if len(data):
        collection.foreach_get(property_name, data)
    return {'count': len(collection), 'width': width, 'dtype': str(data.dtype),
            'sha256': hashlib.sha256(data.tobytes()).hexdigest()}


def element_data(collection):
    if not len(collection):
        return {'count': 0}
    result = {'count': len(collection), 'rna_type': collection[0].bl_rna.identifier}
    for prop in collection[0].bl_rna.properties:
        if prop.identifier == 'rna_type' or prop.type not in {'FLOAT', 'INT', 'BOOLEAN', 'STRING', 'ENUM'}:
            continue
        width = max(1, getattr(prop, 'array_length', 0))
        if prop.type in {'FLOAT', 'INT', 'BOOLEAN'}:
            result[prop.identifier] = bulk(collection, prop.identifier,
                {'FLOAT': np.float32, 'INT': np.int32, 'BOOLEAN': np.bool_}[prop.type], width)
        else:
            result[prop.identifier] = fingerprint([plain(getattr(item, prop.identifier)) for item in collection])
    return result


def attribute_data(attributes):
    return {item.name: {'domain': item.domain, 'data_type': item.data_type,
                       'data': element_data(item.data)} for item in sorted(attributes, key=lambda item: item.name)}


def deform_weights(mesh):
    digest, buffer = hashlib.sha256(), bytearray()
    for vertex in mesh.vertices:
        groups = sorted((item.group, item.weight) for item in vertex.groups)
        buffer.extend(struct.pack('<I', len(groups)))
        for index, weight in groups:
            buffer.extend(struct.pack('<If', index, weight))
        if len(buffer) > 1024 * 1024:
            digest.update(buffer)
            buffer.clear()
    digest.update(buffer)
    return digest.hexdigest()


class Semantics:
    """Hash all stored asset IDs, with bulk access for large geometry arrays."""
    def __init__(self, excluded_scene_keys):
        self.excluded_scene_keys = excluded_scene_keys
        self.counts = {'meshes': 0, 'vertices': 0, 'attributes': 0, 'packed_images': 0, 'packed_bytes': 0}

    def custom(self, value):
        def convert(item):
            if isinstance(item, bpy.types.ID):
                return plain(item)
            if hasattr(item, 'items'):
                return {key: convert(child) for key, child in item.items()}
            return plain(item)
        try:
            result = {}
            for key, item in value.items():
                # Registered PropertyGroup RNA already exposes each effective
                # value below, including defaults. Reading a PointerProperty
                # can materialize its backing None without a semantic change.
                if isinstance(value, bpy.types.PropertyGroup) and key in value.bl_rna.properties:
                    continue
                if isinstance(value, bpy.types.Scene) and key in self.excluded_scene_keys.get(value.name, set()):
                    continue
                result[key] = convert(item)
            return result
        except TypeError:
            return {}

    def tree(self, value, trail, seen=None, root=False):
        if value is None:
            return None
        if isinstance(value, bpy.types.ID) and not root:
            return plain(value)
        if not hasattr(value, 'bl_rna'):
            return plain(value)
        seen = {} if seen is None else seen
        # Distinct RNA views may legally share one underlying C address (for
        # example an attribute vector and its containing native curve data).
        # Include the RNA type; memory allocation is never a semantic identity.
        pointer = (value.bl_rna.identifier, value.as_pointer())
        if pointer in seen:
            return {'struct_ref': seen[pointer]}
        seen[pointer] = trail
        result = {'rna_type': value.bl_rna.identifier, 'custom': self.custom(value)}
        skip = set(VOLATILE)
        if isinstance(value, bpy.types.Object):
            # Derived from stored loc/rot/scale/delta/parent_inverse, all hashed.
            # Reading or assigning these matrices triggers dependency evaluation.
            skip |= {'matrix_world', 'matrix_local', 'dimensions', 'bound_box'}
        if isinstance(value, bpy.types.ViewLayer):
            # Evaluated graph/update queues are runtime caches, never asset data.
            skip.add('depsgraph')
        if isinstance(value, bpy.types.NodeSocket):
            # Link-derived availability; links plus all writable flags are kept.
            skip |= {'is_inactive', 'is_unavailable', 'is_linked'}
        if isinstance(value, bpy.types.Mesh):
            skip |= MESH_BULK
        if isinstance(value, bpy.types.Curves):
            skip |= {'attributes', 'color_attributes', 'curves', 'points', 'materials',
                     'position_data', 'curve_offset_data', 'normals'}
        if isinstance(value, bpy.types.Spline):
            skip |= {'points', 'bezier_points'}
        if isinstance(value, bpy.types.ShapeKey):
            skip |= {'data', 'points'}
        if isinstance(value, bpy.types.ImagePackedFile):
            skip.add('filepath')
        if isinstance(value, bpy.types.RenderSettings):
            skip.add('filepath')
        if isinstance(value, bpy.types.Image):
            # Pixel buffers are compared exactly via foreach_get below. Force
            # loading before reading file-format/resolution cache-backed RNA.
            skip.add('pixels')
            if value.source != 'VIEWER':
                len(value.pixels)
        for prop in sorted(value.bl_rna.properties, key=lambda item: item.identifier):
            name = prop.identifier
            if name in skip:
                continue
            if prop.type in {'FLOAT', 'INT', 'BOOLEAN', 'STRING', 'ENUM'}:
                if prop.is_readonly and name not in READONLY_SCALARS:
                    continue
                result[name] = plain(getattr(value, name))
            elif prop.type == 'POINTER':
                result[name] = self.tree(getattr(value, name), trail + '.' + name, seen)
            elif prop.type == 'COLLECTION':
                items = getattr(value, name)
                if len(items) > 100000:
                    raise ValueError('Uncovered large RNA collection at ' + trail + '.' + name)
                if name in {'objects', 'children', 'children_recursive', 'all_objects'} and isinstance(value, bpy.types.Collection):
                    result[name] = sorted((plain(item) for item in items), key=lambda item: json.dumps(item, sort_keys=True))
                else:
                    result[name] = [self.tree(item, trail + '.' + name + f'[{index}]', seen) for index, item in enumerate(items)]
        if isinstance(value, bpy.types.Bone):
            result['stored_rest_geometry'] = {name: plain(getattr(value, name)) for name in ('head_local', 'tail_local', 'matrix_local')}
        if isinstance(value, bpy.types.Mesh):
            self.counts['meshes'] += 1
            self.counts['vertices'] += len(value.vertices)
            self.counts['attributes'] += len(value.attributes)
            result['geometry'] = {'vertices': bulk(value.vertices, 'co', np.float32, 3),
                'edges': bulk(value.edges, 'vertices', np.int32, 2),
                'loops_vertex': bulk(value.loops, 'vertex_index', np.int32, 1),
                'loops_edge': bulk(value.loops, 'edge_index', np.int32, 1),
                'polygon_start': bulk(value.polygons, 'loop_start', np.int32, 1),
                'polygon_size': bulk(value.polygons, 'loop_total', np.int32, 1),
                'polygon_material': bulk(value.polygons, 'material_index', np.int32, 1),
                'polygon_smooth': bulk(value.polygons, 'use_smooth', np.bool_, 1),
                'edge_seams': bulk(value.edges, 'use_seam', np.bool_, 1),
                'corner_normals': element_data(value.corner_normals),
                'vertex_normals': element_data(value.vertex_normals),
                'polygon_normals': element_data(value.polygon_normals),
                'attributes': attribute_data(value.attributes), 'deform_weights_sha256': deform_weights(value),
                'material_slots': [plain(item) for item in value.materials],
                'uv_layers': [{'name': item.name, 'active_render': item.active_render, 'active_clone': item.active_clone} for item in value.uv_layers],
                'active_uv_index': value.uv_layers.active_index,
                'active_color_name': value.color_attributes.active_color_name,
                'render_color_index': value.color_attributes.render_color_index}
        if isinstance(value, bpy.types.Curves):
            result['native_hair'] = {'attributes': attribute_data(value.attributes),
                'position_data': element_data(value.position_data),
                'curve_offset_data': element_data(value.curve_offset_data),
                'normals': element_data(value.normals),
                'color_attributes': attribute_data(value.color_attributes),
                'first_point_index': bulk(value.curves, 'first_point_index', np.int32, 1),
                'point_count': bulk(value.curves, 'points_length', np.int32, 1),
                'materials': [plain(item) for item in value.materials]}
        if isinstance(value, bpy.types.Spline):
            result['spline_geometry'] = {'points': element_data(value.points), 'bezier_points': element_data(value.bezier_points)}
        if isinstance(value, bpy.types.ShapeKey):
            result['shape_key_geometry'] = element_data(value.data)
        if isinstance(value, bpy.types.Image):
            result['packed_image_bytes'] = []
            for packed in value.packed_files:
                data = bytes(packed.packed_file.data)
                self.counts['packed_images'] += 1
                self.counts['packed_bytes'] += len(data)
                result['packed_image_bytes'].append({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
            if value.has_data and value.source != 'VIEWER':
                pixels = np.empty(len(value.pixels), dtype=np.float32)
                value.pixels.foreach_get(pixels)
                result['pixel_sha256'] = hashlib.sha256(pixels.tobytes()).hexdigest()
        if isinstance(value, bpy.types.Text):
            result['text_body_sha256'] = hashlib.sha256(value.as_string().encode()).hexdigest()
        embedded = getattr(value, 'node_tree', None)
        if isinstance(value, bpy.types.ID) and embedded is not None:
            result['embedded_node_tree'] = self.tree(embedded, trail + '.embedded_node_tree', root=True)
        return result

    def snapshot(self):
        groups = {}
        for prop in bpy.data.bl_rna.properties:
            if prop.type != 'COLLECTION' or prop.identifier in UI_COLLECTIONS:
                continue
            values = getattr(bpy.data, prop.identifier)
            groups[prop.identifier] = {item.name: fingerprint(self.tree(item, prop.identifier + '[' + item.name + ']', root=True))
                for item in sorted(values, key=lambda item: item.name)}
        return {'sha256': fingerprint(groups), 'datablocks': groups, 'coverage_counts': self.counts}


def stage_external_images(repo, source, candidates):
    """Mirror unchanged public image dependencies so candidate RNA can load them."""
    records = []
    for image in bpy.data.images:
        if image.packed_files or image.source != 'FILE':
            continue
        target = Path(bpy.path.abspath(image.filepath)).resolve()
        if not target.is_file():
            raise FileNotFoundError('Source image dependency is unavailable')
        if not target.is_relative_to(repo) or target.relative_to(repo).parts[0] not in {'assets', 'public'} or '.private' in target.parts:
            raise ValueError('Source image dependency is outside public asset roots')
        relative = target.relative_to(repo)
        destination = (candidates / relative).resolve()
        if not destination.is_relative_to(candidates):
            raise ValueError('Image dependency escaped candidate mirror')
        digest = sha_file(target)
        if destination.exists():
            if sha_file(destination) != digest:
                raise FileExistsError('Different image dependency already exists')
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with target.open('rb') as incoming, destination.open('xb') as outgoing:
                shutil.copyfileobj(incoming, outgoing)
        if sha_file(destination) != digest or sha_file(target) != digest:
            raise AssertionError('Image dependency copy is not byte-identical')
        records.append({'path': relative.as_posix(), 'sha256': digest, 'bytes': target.stat().st_size})
    return records


def read_metadata(label):
    """Resolve a predeclared replacement field after closing and reopening."""
    if label.startswith('Scene['):
        index, suffix = label[6:].split('].', 1)
        scene = bpy.data.scenes[int(index)]
        if suffix == 'render.filepath':
            return scene.render.filepath
        return scene[suffix.removeprefix('custom_properties.')]
    match = re.fullmatch(r'screens\[(\d+)\]\.areas\[(\d+)\]\.spaces\[(\d+)\]\.params\.directory', label)
    if match:
        screen, area, space = map(int, match.groups())
        return bpy.data.screens[screen].areas[area].spaces[space].params.directory
    match = re.fullmatch(r'images\[(\d+)\]\.packed_files\[(\d+)\]\.filepath', label)
    if match:
        image, packed = map(int, match.groups())
        return bpy.data.images[image].packed_files[packed].filepath
    raise ValueError('Unrecognized replacement field')


def portable_equal(actual, expected):
    if isinstance(actual, str) and isinstance(expected, str):
        return actual.replace('\\', '/') == expected.replace('\\', '/')
    if isinstance(actual, bytes) and isinstance(expected, bytes):
        return actual.replace(b'\\', b'/') == expected.replace(b'\\', b'/')
    return actual == expected


def public_reference(value, repo, source, blender_relative=False):
    text = str(value).replace('\\', '/')
    if '.private/' not in text.lower():
        match = re.search(r'(?:^|/)((?:public|assets)/.+)$', text)
        if match:
            relative = Path(match.group(1))
            target = (repo / relative).resolve()
            if target.is_relative_to(repo) and target.is_file():
                if blender_relative:
                    return '//' + os.path.relpath(target, source.parent).replace('\\', '/')
                return relative.as_posix()
    if blender_relative:
        raise ValueError('Packed source image lacks a verified canonical public reference')
    return 'omitted-private-build-provenance'


def cleanup_plan(repo, source):
    changes, excluded = [], {}
    for screen_index, screen in enumerate(bpy.data.screens):
        for area_index, area in enumerate(screen.areas):
            for space_index, space in enumerate(area.spaces):
                if hasattr(space, 'params') and space.params is not None:
                    value = getattr(space.params, 'directory', b'')
                    if value and value != b'//':
                        changes.append((space.params, 'directory', b'//',
                            f'screens[{screen_index}].areas[{area_index}].spaces[{space_index}].params.directory'))
    for scene_index, scene in enumerate(bpy.data.scenes):
        changes.append((scene.render, 'filepath', '//renders/' + source.stem + '/', f'Scene[{scene_index}].render.filepath'))
        for key, value in scene.items():
            if isinstance(value, str) and PATH_PATTERN.search(value):
                excluded.setdefault(scene.name, set()).add(key)
                changes.append((scene, key, public_reference(value, repo, source), f'Scene[{scene_index}].custom_properties.' + key))
    for image_index, image in enumerate(bpy.data.images):
        for packed_index, packed in enumerate(image.packed_files):
            if PATH_PATTERN.search(packed.filepath):
                changes.append((packed, 'filepath', public_reference(packed.filepath, repo, source, True),
                    f'images[{image_index}].packed_files[{packed_index}].filepath'))
    return changes, excluded


def compare(before, after):
    differences = []
    for group in sorted(set(before['datablocks']) | set(after['datablocks'])):
        left, right = before['datablocks'].get(group, {}), after['datablocks'].get(group, {})
        for name in sorted(set(left) | set(right)):
            if left.get(name) != right.get(name):
                differences.append({'collection': group, 'datablock': name})
    return differences


def save_complete_copy(destination):
    """Retain zero-user IDs using a transient tag, never a persistent fake user.

    Ordinary save-mainfile drops unused IDs even when present in an opened
    source. ID.use_extra_user is a runtime retention tag, cleared on reload.
    Original tag values are restored in memory immediately after this save.
    The strict reopened fingerprint includes both user flags, proving neither
    sculpt data nor a persistent retention setting changed in the output.
    """
    retained = []
    for prop in bpy.data.bl_rna.properties:
        if prop.type != 'COLLECTION' or prop.identifier in UI_COLLECTIONS:
            continue
        for item in getattr(bpy.data, prop.identifier):
            if isinstance(item, bpy.types.ID) and item.users == 0 and not item.use_fake_user:
                retained.append((item, item.use_extra_user, prop.identifier, item.name))
    try:
        for item, _, _, _ in retained:
            item.use_extra_user = True
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(destination), copy=True, relative_remap=False, compress=True)
    finally:
        for item, previous, _, _ in retained:
            item.use_extra_user = previous
    return [{'collection': group, 'datablock': name, 'runtime_tag_restored': item.use_extra_user == previous}
            for item, previous, group, name in retained]


def process(relative, repo, candidates, reports, verify_existing):
    source, destination = (repo / relative).resolve(), (candidates / relative).resolve()
    if not source.is_relative_to(repo / 'assets/3d/source') or source.suffix != '.blend':
        raise ValueError('Source outside approved asset roots')
    if not destination.is_relative_to(candidates) or destination == source:
        raise ValueError('Candidate outside private publication root')
    if destination.exists() and not verify_existing:
        raise FileExistsError('Candidate collision')
    before_sha, before_bytes = sha_file(source), source.stat().st_size
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=True, use_scripts=False)
    dependencies = stage_external_images(repo, source, candidates)
    changes, excluded = cleanup_plan(repo, source)
    baseline = Semantics(excluded).snapshot()
    records = []
    for owner, field, value, label in changes:
        if isinstance(owner, bpy.types.Scene):
            owner[field] = value
        else:
            setattr(owner, field, value)
        records.append({'field': label, 'operation': 'portable_metadata_replacement',
                        'public_value': value.decode('ascii') if isinstance(value, bytes) else value})
    cleaned = Semantics(excluded).snapshot()
    differences = compare(baseline, cleaned)
    if differences:
        raise AssertionError('In-memory semantic mismatch: ' + json.dumps(differences))
    reused = destination.exists()
    retention = []
    if not reused:
        destination.parent.mkdir(parents=True, exist_ok=True)
        retention = save_complete_copy(destination)
    bpy.ops.wm.open_mainfile(filepath=str(destination), load_ui=True, use_scripts=False)
    reopened = Semantics(excluded).snapshot()
    differences = compare(baseline, reopened)
    remaining, _ = cleanup_plan(repo, source)
    mismatched_metadata = [label for _, _, expected, label in changes if not portable_equal(read_metadata(label), expected)]
    for owner, field, expected, label in remaining:
        actual = owner[field] if isinstance(owner, bpy.types.Scene) else getattr(owner, field)
        if not portable_equal(actual, expected):
            mismatched_metadata.append(label)
    proof = {'schema': SCHEMA, 'path': relative.as_posix(), 'before_sha256': before_sha,
             'after_sha256': sha_file(destination), 'before_bytes': before_bytes, 'after_bytes': destination.stat().st_size,
             'metadata_changes': records, 'unchanged_image_dependencies': dependencies,
             'source_bytes_unchanged': before_sha == sha_file(source),
             'in_memory_semantics_equal': baseline['sha256'] == cleaned['sha256'],
             'reopened_semantics_equal': baseline['sha256'] == reopened['sha256'],
             'reopened_metadata_portable': not mismatched_metadata,
             'semantic_differences': differences, 'remaining_metadata_fields': mismatched_metadata,
             'reused_existing_candidate_read_only': reused,
             'temporary_orphan_retention': retention,
             'evidence': {'before': baseline, 'in_memory': cleaned, 'reopened': reopened,
                          'script_sha256': sha_file(Path(__file__))}}
    report = reports / (relative.as_posix().replace('/', '__') + '.json')
    report.write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    if not proof['source_bytes_unchanged'] or differences or mismatched_metadata:
        raise AssertionError('Publication-copy verification failed; see redacted proof')
    return {key: proof[key] for key in ('path', 'before_sha256', 'after_sha256', 'before_bytes', 'after_bytes')} | {
        'evidence': report.name, 'semantic_sha256': baseline['sha256'], 'metadata_change_count': len(records),
        'proof': {'evidence_sha256': sha_file(report), 'semantic_sha256': baseline['sha256'],
                  'source_bytes_unchanged': True, 'in_memory_semantics_equal': True,
                  'reopened_semantics_equal': True, 'reopened_metadata_portable': True,
                  'metadata_fields': [item['field'] for item in records]}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', required=True)
    parser.add_argument('--candidate-root', required=True)
    parser.add_argument('--report-root', required=True)
    parser.add_argument('--path', action='append')
    parser.add_argument('--verify-existing', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    repo, candidates, root_reports = (Path(item).resolve() for item in (args.source_root, args.candidate_root, args.report_root))
    allowed = repo / '.private/publication-2026-09-07'
    if candidates != allowed / 'blender-candidates' or root_reports != allowed / 'blender-reports':
        raise ValueError('Only the explicitly authorized private copy/report roots are permitted')
    paths = [Path(item) for item in args.path] if args.path else sorted(path.relative_to(repo) for path in (repo / 'assets/3d/source').rglob('*.blend'))
    if len(set(paths)) != len(paths):
        raise ValueError('Duplicate source paths')
    reports = root_reports / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    reports.mkdir(parents=True, exist_ok=False)
    results, failures = [], []
    for relative in paths:
        print(json.dumps({'path': relative.as_posix(), 'stage': 'semantic_preflight'}), flush=True)
        try:
            results.append(process(relative, repo, candidates, reports, args.verify_existing))
        except Exception as exc:
            failures.append({'path': relative.as_posix(), 'error_type': type(exc).__name__,
                             'error_line_numbers': [item.lineno for item in traceback.extract_tb(exc.__traceback__)]})
            if isinstance(exc, ValueError) and str(exc).startswith('Uncovered large RNA collection at '):
                failures[-1]['uncovered_rna_field'] = str(exc).removeprefix('Uncovered large RNA collection at ')
            break
        print(json.dumps({'path': relative.as_posix(), 'stage': 'verified_private_copy'}), flush=True)
    summary = {'schema': SCHEMA, 'records': results, 'failures': failures, 'candidate_count': len(results),
               'source_count': len(paths), 'report_directory': reports.relative_to(repo).as_posix()}
    summary['files'] = [{key: record[key] for key in ('path', 'before_sha256', 'after_sha256', 'before_bytes', 'after_bytes', 'proof')} for record in results]
    auxiliary = {}
    for record in results:
        proof = json.loads((reports / record['evidence']).read_text(encoding='utf-8'))
        for dependency in proof['unchanged_image_dependencies']:
            auxiliary[dependency['path']] = dependency
    summary['auxiliary_byte_identical_dependencies'] = [auxiliary[key] for key in sorted(auxiliary)]
    (reports / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'candidate_count': len(results), 'failures': failures, 'report_directory': summary['report_directory']}), flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

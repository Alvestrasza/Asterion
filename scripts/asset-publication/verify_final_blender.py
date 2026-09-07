"""Read-only reopen verification of metadata-tail-cleaned publication copies.

The frozen RNA sanitizer remains the authoritative semantic implementation.
This verifier never saves a Blender file, changes an asset, or promotes output.
Each batch writes fresh, redacted receipts only inside the authorized private
publication report directory. Disjoint --path batches may run concurrently.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import traceback

import bpy


SCHEMA = 'asterion.blender-publication-final-reopen.v1'
RAW_SANITIZER_SHA256 = '0390542E3A4C5F1B81414E7831716F97F04BBB1AF222CE56C06FD0D132D77175'
UNSAFE_TEXT = re.compile(r'(?:[A-Za-z]:[\\/]|\.private[\\/]|(?:^|[\s"\'])/(?:Users|home|tmp|mnt)/|AppData[\\/])', re.I)


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest().upper()


def verify_bytes(path, digest, size):
    if not isinstance(digest, str) or not re.fullmatch(r'[A-Fa-f0-9]{64}', digest):
        raise ValueError('Invalid receipt digest')
    if not path.is_file() or path.stat().st_size != size or sha_file(path) != digest.upper():
        raise ValueError('Asset does not match receipt')


def safe_relative(value):
    if not isinstance(value, str) or '\\' in value or ':' in value or '\0' in value:
        raise ValueError('Invalid relative asset path')
    result = Path(value)
    if result.is_absolute() or '..' in result.parts or not value.startswith('assets/3d/source/') or not value.endswith('.blend'):
        raise ValueError('Asset path outside approved Blender roots')
    return result


def safe_proof(value):
    if isinstance(value, str) and UNSAFE_TEXT.search(value):
        raise ValueError('Non-public text in receipt proof')
    if isinstance(value, list):
        for item in value:
            safe_proof(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            safe_proof(key)
            safe_proof(item)


def load_rows(document):
    rows = document.get('files', document.get('records'))
    if not isinstance(rows, list):
        raise ValueError('Missing receipt rows')
    result = {}
    for row in rows:
        name = safe_relative(row['path']).as_posix()
        if name in result:
            raise ValueError('Duplicate receipt path')
        result[name] = row
    return result


def validate_tail_proof(proof):
    """Require the exact, independently parsed fixed-buffer write contract."""
    safe_proof(proof)
    if proof.get('schema') != 'asterion.blender-cstring-tail-proof.v1' or proof.get('blender_header') != 'BLENDER17-01v0502':
        raise ValueError('Unsupported tail-proof format')
    if not all(proof.get(key) is True for key in ('all_other_decompressed_bytes_identical',
            'only_allowlisted_post_nul_bytes_zeroed', 'live_cstrings_unchanged',
            'source_bytes_unchanged', 'candidate_readback_verified')):
        raise ValueError('Failed or missing tail-preservation assertion')
    for key in ('sdna_sha256', 'before_decompressed_sha256', 'after_decompressed_sha256',
                'unchanged_decompressed_segments_sha256', 'code_sha256'):
        if not re.fullmatch(r'[A-Fa-f0-9]{64}', str(proof.get(key, ''))):
            raise ValueError('Invalid tail-proof digest')
    expected = {'FileSelectParams.dir[1282]': 1282, 'RenderData.pic[1024]': 1024}
    fields = proof.get('fields')
    if not isinstance(fields, list) or len(fields) != 2 or {item.get('field') for item in fields} != set(expected):
        raise ValueError('Unexpected tail-field scope')
    indexed = {item['field']: item for item in fields}
    for item in fields:
        if not all(type(item.get(key)) is int for key in ('start', 'end', 'bytes', 'first_nul_offset', 'nonzero_tail_bytes')):
            raise ValueError('Non-integer tail field interval')
        if item['end'] - item['start'] != expected[item['field']] or item['bytes'] != expected[item['field']]:
            raise ValueError('Unexpected SDNA metadata buffer extent')
        if not 0 <= item['start'] <= item['first_nul_offset'] < item['end'] <= proof['decompressed_bytes']:
            raise ValueError('Invalid metadata NUL boundary')
        if not 0 <= item['nonzero_tail_bytes'] < item['bytes']:
            raise ValueError('Invalid metadata tail count')
    changed, previous = 0, -1
    for item in proof.get('changed_ranges', []):
        field = indexed.get(item.get('field'))
        if field is None or not all(type(item.get(key)) is int for key in ('start', 'end', 'bytes')):
            raise ValueError('Unexpected tail write range')
        if not field['first_nul_offset'] < item['start'] < item['end'] <= field['end'] or item['start'] < previous:
            raise ValueError('Tail writes touch live string or overlap')
        if item['bytes'] != item['end'] - item['start']:
            raise ValueError('Invalid tail write count')
        previous, changed = item['end'], changed + item['bytes']
    if changed != proof.get('zeroed_bytes') or changed != sum(item['nonzero_tail_bytes'] for item in fields):
        raise ValueError('Tail-write totals do not reconcile')


def metadata_after_reopen(sanitizer, raw_evidence):
    failed = []
    for change in raw_evidence['metadata_changes']:
        actual = sanitizer.read_metadata(change['field'])
        expected = change['public_value']
        if isinstance(actual, bytes):
            expected = expected.encode('utf-8')
        if not sanitizer.portable_equal(actual, expected):
            failed.append(change['field'])
    return failed


def original_scene_exclusions(raw_evidence, baseline):
    scenes = list(baseline['datablocks'].get('scenes', {}))
    result = {}
    for change in raw_evidence['metadata_changes']:
        match = re.fullmatch(r'Scene\[(\d+)\]\.custom_properties\.(.+)', change['field'])
        if match:
            index, key = int(match.group(1)), match.group(2)
            if index >= len(scenes):
                raise ValueError('Invalid excluded scene key mapping')
            result.setdefault(scenes[index], set()).add(key)
    return result


def process(relative, repo, final_root, raw_summary_path, raw_summary, raw_record,
            tail_report_path, tail_record, reports, sanitizer):
    name = relative.as_posix()
    original, final = (repo / relative).resolve(), (final_root / relative).resolve()
    raw = (repo / '.private/publication-2026-09-07/blender-candidates' / relative).resolve()
    if not original.is_relative_to(repo / 'assets/3d/source') or not final.is_relative_to(final_root):
        raise ValueError('Resolved asset escaped approved roots')
    verify_bytes(original, raw_record['before_sha256'], raw_record['before_bytes'])
    verify_bytes(raw, raw_record['after_sha256'], raw_record['after_bytes'])
    if tail_record['before_sha256'].upper() != raw_record['after_sha256'].upper() or tail_record['before_bytes'] != raw_record['after_bytes']:
        raise ValueError('Tail-cleaning provenance does not match raw candidate')
    verify_bytes(final, tail_record['after_sha256'], tail_record['after_bytes'])
    raw_evidence_name = next(item['evidence'] for item in raw_summary['records'] if item['path'] == name)
    raw_evidence_path = (raw_summary_path.parent / raw_evidence_name).resolve()
    if not raw_evidence_path.is_relative_to(raw_summary_path.parent):
        raise ValueError('Evidence path escaped receipt directory')
    verify_bytes(raw_evidence_path, raw_record['proof']['evidence_sha256'], raw_evidence_path.stat().st_size)
    raw_evidence = json.loads(raw_evidence_path.read_text(encoding='utf-8'))
    for key in ('path', 'before_sha256', 'before_bytes', 'after_sha256', 'after_bytes'):
        if raw_evidence[key] != raw_record[key]:
            raise ValueError('Raw detailed evidence binding mismatch')
    if raw_evidence['evidence']['script_sha256'] != RAW_SANITIZER_SHA256:
        raise ValueError('Raw evidence used a different semantic implementation')
    if not all(raw_evidence.get(key) is True for key in ('source_bytes_unchanged', 'in_memory_semantics_equal',
                                                       'reopened_semantics_equal', 'reopened_metadata_portable')):
        raise ValueError('Incomplete original RNA evidence')
    baseline = raw_evidence['evidence']['before']
    if not all(raw_evidence['evidence'][key]['sha256'] == baseline['sha256'] for key in ('in_memory', 'reopened')):
        raise ValueError('Original semantic digests disagree')
    if sanitizer.fingerprint(baseline['datablocks']) != baseline['sha256']:
        raise ValueError('Corrupt original per-datablock semantic map')
    for dependency in raw_evidence['unchanged_image_dependencies']:
        dependency_path = (final_root / dependency['path']).resolve()
        if not dependency_path.is_relative_to(final_root):
            raise ValueError('Image dependency escaped candidate root')
        verify_bytes(dependency_path, dependency['sha256'], dependency['bytes'])
    tail_proof = tail_record.get('proof')
    if not isinstance(tail_proof, dict) or not tail_proof:
        raise ValueError('Missing exact tail-write evidence')
    validate_tail_proof(tail_proof)
    bpy.ops.wm.open_mainfile(filepath=str(final), load_ui=True, use_scripts=False)
    final_snapshot = sanitizer.Semantics(original_scene_exclusions(raw_evidence, baseline)).snapshot()
    differences = sanitizer.compare(baseline, final_snapshot)
    invalid_metadata = metadata_after_reopen(sanitizer, raw_evidence)
    verify_bytes(original, raw_record['before_sha256'], raw_record['before_bytes'])
    verify_bytes(final, tail_record['after_sha256'], tail_record['after_bytes'])
    evidence = {
        'schema': SCHEMA, 'path': name, 'before_sha256': raw_record['before_sha256'],
        'before_bytes': raw_record['before_bytes'], 'after_sha256': tail_record['after_sha256'],
        'after_bytes': tail_record['after_bytes'], 'source_bytes_unchanged': True,
        'in_memory_semantics_equal': True, 'raw_reopened_semantics_equal': True,
        'final_reopened_semantics_equal': not differences, 'reopened_metadata_portable': not invalid_metadata,
        'semantic_differences': differences, 'remaining_metadata_fields': invalid_metadata,
        'evidence': {'original': baseline, 'final_reopened': final_snapshot,
                     'raw_semantic_receipt_sha256': sha_file(raw_evidence_path),
                     'raw_summary_sha256': sha_file(raw_summary_path),
                     'tail_report_sha256': sha_file(tail_report_path),
                     'raw_intermediate_sha256': raw_record['after_sha256'],
                     'raw_intermediate_bytes': raw_record['after_bytes'],
                     'frozen_semantic_implementation_sha256': RAW_SANITIZER_SHA256,
                     'final_verifier_sha256': sha_file(Path(__file__)), 'tail_cleanup': tail_proof}}
    evidence_path = reports / (name.replace('/', '__') + '.json')
    evidence_path.write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    if differences or invalid_metadata:
        raise AssertionError('Final candidate failed exact semantic or metadata verification')
    return {key: evidence[key] for key in ('path', 'before_sha256', 'before_bytes', 'after_sha256', 'after_bytes')} | {
        'evidence': evidence_path.name,
        'proof': {'evidence_sha256': sha_file(evidence_path), 'semantic_sha256': baseline['sha256'],
                  'source_bytes_unchanged': True, 'in_memory_semantics_equal': True,
                  'reopened_semantics_equal': True, 'reopened_metadata_portable': True,
                  'raw_semantic_receipt_sha256': sha_file(raw_evidence_path),
                  'raw_intermediate_sha256': raw_record['after_sha256'],
                  'tail_report_sha256': sha_file(tail_report_path),
                  'tail_cleanup': tail_proof,
                  'frozen_semantic_implementation_sha256': RAW_SANITIZER_SHA256,
                  'final_verifier_sha256': sha_file(Path(__file__))}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--raw-summary', required=True)
    parser.add_argument('--tail-report', required=True)
    parser.add_argument('--final-root', required=True)
    parser.add_argument('--path', action='append')
    parser.add_argument('--label', default='batch')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    repo = Path(args.repo).resolve()
    approved = repo / '.private/publication-2026-09-07'
    final_root = Path(args.final_root).resolve()
    if final_root != approved / 'blender-final-candidates' or not re.fullmatch(r'[a-z0-9-]{1,32}', args.label):
        raise ValueError('Final root or batch label outside approved scope')
    raw_summary_path, tail_report_path = Path(args.raw_summary).resolve(), Path(args.tail_report).resolve()
    if not raw_summary_path.is_relative_to(approved / 'blender-reports') or not tail_report_path.is_relative_to(approved):
        raise ValueError('Receipt path outside private publication scope')
    implementation = Path(__file__).with_name('sanitize_blender.py')
    if sha_file(implementation) != RAW_SANITIZER_SHA256:
        raise ValueError('Frozen semantic implementation changed')
    spec = importlib.util.spec_from_file_location('frozen_rna_sanitizer', implementation)
    sanitizer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sanitizer)
    raw_summary = json.loads(raw_summary_path.read_text(encoding='utf-8'))
    if raw_summary.get('candidate_count') != 45 or raw_summary.get('source_count') != 45 or raw_summary.get('failures'):
        raise ValueError('Original raw45 verification is incomplete')
    raw_rows = load_rows(raw_summary)
    tail_summary = json.loads(tail_report_path.read_text(encoding='utf-8'))
    tail_rows = load_rows(tail_summary)
    names = args.path or sorted(tail_rows)
    if not names or len(set(names)) != len(names):
        raise ValueError('Empty or duplicate final batch')
    paths = [safe_relative(name) for name in names]
    for relative in paths:
        if relative.as_posix() not in raw_rows or relative.as_posix() not in tail_rows:
            raise ValueError('Selected path lacks required provenance')
    reports = approved / 'blender-reports' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-final-' + args.label)
    reports.mkdir(parents=True, exist_ok=False)
    rows, failures = [], []
    for relative in paths:
        print(json.dumps({'path': relative.as_posix(), 'stage': 'final_read_only_reopen'}), flush=True)
        try:
            rows.append(process(relative, repo, final_root, raw_summary_path, raw_summary,
                                raw_rows[relative.as_posix()], tail_report_path,
                                tail_rows[relative.as_posix()], reports, sanitizer))
        except Exception as exc:
            failures.append({'path': relative.as_posix(), 'error_type': type(exc).__name__,
                             'error_line_numbers': [item.lineno for item in traceback.extract_tb(exc.__traceback__)]})
            break
        print(json.dumps({'path': relative.as_posix(), 'stage': 'verified_final_copy'}), flush=True)
    summary = {'schema': SCHEMA, 'files': rows, 'failures': failures, 'verified_count': len(rows),
               'requested_count': len(paths), 'report_directory': reports.relative_to(repo).as_posix(),
               'raw_summary_sha256': sha_file(raw_summary_path), 'tail_report_sha256': sha_file(tail_report_path),
               'verifier_sha256': sha_file(Path(__file__))}
    (reports / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'verified_count': len(rows), 'failures': failures, 'report_directory': summary['report_directory']}), flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

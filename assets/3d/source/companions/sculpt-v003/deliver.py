"""Hash-gated delivery to new v003 paths, with the proven staged rollback helper."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
spec = importlib.util.spec_from_file_location('historical_staged_delivery', ROOT.parent / 'sculpt-v002/deliver.py')
staged = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = staged
spec.loader.exec_module(staged)
KINDS = ('pony', 'rabbit', 'cat', 'dog', 'orc', 'fairy', 'elf')


def prepare(work, kind, repo=REPO, *, previous=None, _historical=False):
    work = Path(work).resolve(); repo = Path(repo).resolve()
    report = json.loads((work / 'validation.json').read_text(encoding='utf-8'))
    if report['kind'] != kind or report['version'] != 'sculpt-v003' or report.get('passed') is not True:
        raise ValueError('Candidate is not accepted')
    if not report.get('checks') or not all(v is True for v in report['checks'].values()):
        raise ValueError('Candidate has failed checks')
    if not _historical:
        for name, sha in report['input_sha256'].items():
            path = (repo / name).resolve()
            if not path.is_relative_to(repo) or staged.digest(path) != sha:
                raise ValueError('Historical input or builder changed: ' + name)
    artifacts = []
    def add(path, content):
        path = path.resolve()
        if not path.is_relative_to(repo):
            raise ValueError('Destination outside repository')
        artifacts.append(staged.Artifact(path, content))
    def bound_file(source, target, sha):
        content = source.read_bytes()
        if staged.sha256(content) != sha:
            raise ValueError('Evidence mismatch: ' + source.name)
        add(target, content)
    source_root = repo / 'assets/3d/source' / kind / 'sculpt-v003'
    review_root = repo / 'assets/3d/reference' / kind / 'sculpt-v003'
    public = repo / 'public/assets/3d' / kind / (kind + '-sculpt-v003.glb')
    master = source_root / (kind + '-sculpt-v003.blend')
    bound_file(work / public.name, public, report['model_sha256'])
    bound_file(work / master.name, master, report['source_sha256'])
    bound_file(repo / 'public/assets/companions' / (kind + '.png'), review_root / 'original.png', report['reference_sha256'])
    for category in ('source', 'import'):
        expected = {'hero', 'front', 'side', 'rear', 'body-hero', 'body-side'} if category == 'source' else {'hero', 'rear', 'body-hero', 'blink'}
        if set(report[category + '_views']) != expected:
            raise ValueError('Missing required review view')
        for view, item in report[category + '_views'].items():
            path = (work / category / item['file']).resolve()
            if path.parent != work / category:
                raise ValueError('Image outside review directory')
            target = review_root / category / item['file']
            bound_file(path, target, item['sha256'])
            item['file'] = target.relative_to(repo).as_posix()
    # Keep full RNA fingerprints in the private build review, publish their exact
    # digest and curve/key counts without duplicating megabytes of keyframe data.
    for field in ('original_rig', 'candidate_rig'):
        rig = report[field]
        report[field] = {k: rig[k] for k in ('rest_sha256', 'behavior_sha256', 'bones', 'fps', 'fps_base')}
        report[field]['actions'] = {name: {k: a[k] for k in ('sha256', 'curve_count', 'key_count', 'finite_keys', 'frame_range')}
                                   for name, a in rig['actions'].items()}
    validation = review_root / 'validation.json'
    add(validation, staged.json_bytes(report))
    manifest = {k: report[k] for k in ('schema', 'kind', 'name', 'version', 'source_sha256', 'model_sha256',
        'reference_sha256', 'triangles', 'bytes', 'bones', 'clips', 'draw_calls', 'materials', 'components',
        'blender', 'human_likeness_accepted', 'mobile_performance_accepted', 'projection_used',
        'paid_provider_used', 'package_status', 'animation_limit', 'likeness_limit', 'compression_lossless')}
    manifest.update(source=master.relative_to(repo).as_posix(), model=public.relative_to(repo).as_posix(),
        reference=(review_root / 'original.png').relative_to(repo).as_posix(),
        validation=validation.relative_to(repo).as_posix(), validation_sha256=staged.sha256(staged.json_bytes(report)),
        fresh_import_passed=True, animations_unchanged=True, equipment_separate=True,
        input_sha256=report['input_sha256'], renders=report['source_views'], import_renders=report['import_views'],
        notes=report['changes']['notes'], edited_objects=len(report['changes']['edited_objects']))
    add(source_root / 'manifest.json', staged.json_bytes(manifest))
    # A prior private review is an exact overwrite baseline only, never fresh
    # acceptance evidence. It must reproduce every old artifact byte for byte.
    prior = {}
    if previous is not None:
        old = prepare(previous, kind, repo, _historical=True)
        prior = {item.target: item.checksum for item in old.artifacts}
    observed = {}
    for item in artifacts:
        value = staged.existing_hash(item.target)
        if not _historical and value is not None and value != item.checksum and value != prior.get(item.target):
            raise FileExistsError('Different content already exists at new delivery path: ' + str(item.target))
        observed[item.target] = value
    return staged.DeliveryPlan(repo, tuple(artifacts), manifest, observed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', required=True, choices=KINDS)
    parser.add_argument('--input', required=True)
    parser.add_argument('--previous', help='Exact previous private review for a hash-guarded pre-handoff correction')
    args = parser.parse_args()
    manifest = staged.execute_delivery(prepare(args.input, args.kind, previous=args.previous))
    print(json.dumps({k: manifest[k] for k in ('kind', 'triangles', 'bytes', 'model_sha256')}, indent=2))


if __name__ == '__main__':
    main()

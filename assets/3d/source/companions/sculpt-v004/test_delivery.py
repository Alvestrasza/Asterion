"""Read-only delivery gate regression checks against a completed pony review."""
import argparse
import hashlib
import copy
import unittest
from pathlib import Path
from unittest.mock import patch
import deliver

REVIEW = None


class DeliveryGates(unittest.TestCase):
    def report(self):
        return deliver.json.loads((REVIEW/'validation.json').read_text(encoding='utf-8'))

    def test_empty_input_evidence_is_rejected(self):
        report=self.report();report['input_sha256']={}
        with self.assertRaisesRegex(ValueError,'immutable input'):
            deliver.validate_evidence(report,'pony','public/assets/companions/pony.png')

    def test_renamed_acceptance_checks_are_rejected(self):
        report=self.report();report['checks']={'some_local_test':True}
        with self.assertRaisesRegex(ValueError,'acceptance checks'):
            deliver.validate_evidence(report,'pony','public/assets/companions/pony.png')

    def test_contradictory_action_digest_is_rejected(self):
        report=copy.deepcopy(self.report());report['candidate_rig']['actions']['idle']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'action fingerprint contradiction'):
            deliver.validate_evidence(report,'pony','public/assets/companions/pony.png')

    def test_actual_glb_counts_override_claimed_counts(self):
        report=self.report();report['triangles']+=2
        data=(REVIEW/'pony-sculpt-v004.glb').read_bytes()
        with self.assertRaisesRegex(ValueError,'counts contradict'):
            deliver.validate_glb(data,report,'pony')

    def test_unknown_kind_is_rejected_before_reading(self):
        with self.assertRaisesRegex(ValueError, 'Unknown companion'):
            deliver.prepare(REVIEW, '../pony')

    def test_substituted_reference_is_rejected(self):
        parse = deliver.json.loads
        def substitute(content, *args, **kwargs):
            report = parse(content, *args, **kwargs)
            report['reference_input'] = 'public/assets/companions/rabbit.png'
            return report
        with patch.object(deliver.json, 'loads', side_effect=substitute), self.assertRaisesRegex(ValueError, 'reference authority'):
            deliver.prepare(REVIEW, 'pony')

    def test_same_delivery_is_idempotent_preflight(self):
        plan = deliver.prepare(REVIEW, 'pony')
        self.assertGreater(len(plan.artifacts), 12)
        self.assertTrue(all(plan.observed_targets[a.target] == a.checksum for a in plan.artifacts))

    def test_stale_builder_fails_before_any_write(self):
        digest = deliver.staged.digest
        def drift(path):
            return '0' * 64 if Path(path).name == 'refinements.py' else digest(path)
        with patch.object(deliver.staged, 'digest', side_effect=drift), self.assertRaisesRegex(ValueError, 'builder changed'):
            deliver.prepare(REVIEW, 'pony')

    def test_conflicting_final_manifest_fails_before_any_write(self):
        existing = deliver.staged.existing_hash
        def conflict(path):
            return 'F' * 64 if Path(path).name == 'manifest.json' else existing(path)
        with patch.object(deliver.staged, 'existing_hash', side_effect=conflict), self.assertRaisesRegex(FileExistsError, 'Different content'):
            deliver.prepare(REVIEW, 'pony')

    def test_destination_change_after_preflight_is_rejected(self):
        plan = deliver.prepare(REVIEW, 'pony')
        existing = deliver.staged.existing_hash
        victim = plan.artifacts[-1].target
        def changed(path):
            return 'A' * 64 if path == victim else existing(path)
        with patch.object(deliver.staged, 'existing_hash', side_effect=changed), self.assertRaisesRegex(FileExistsError, 'changed after preflight'):
            deliver.staged.verify_destinations(plan)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', required=True)
    args, rest = parser.parse_known_args()
    REVIEW = Path(args.review).resolve()
    # All tests are preflight-only; additionally prove delivered file bytes did
    # not change even on the deliberately failing branches.
    baseline = deliver.prepare(REVIEW, 'pony')
    before = {a.target: hashlib.sha256(a.target.read_bytes()).digest() for a in baseline.artifacts}
    result = unittest.main(argv=['test_delivery.py'] + rest, exit=False).result
    if any(hashlib.sha256(path.read_bytes()).digest() != checksum for path, checksum in before.items()):
        raise RuntimeError('Read-only delivery tests modified an artifact')
    raise SystemExit(0 if result.wasSuccessful() else 1)

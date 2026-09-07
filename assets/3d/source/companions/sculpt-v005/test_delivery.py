"""Read-only negative gate tests against a completed face-round delivery."""
import argparse
import copy
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch
import contract
import deliver

REVIEW = None
KIND = None


class DeliveryGates(unittest.TestCase):
    def report(self):
        return deliver.json.loads((REVIEW/'validation.json').read_text(encoding='utf-8'))

    def reject(self, edit, message):
        report = copy.deepcopy(self.report())
        edit(report)
        with self.assertRaisesRegex(ValueError, message):
            deliver.validate_evidence(report, KIND)

    def test_required_inputs(self):
        self.reject(lambda r: r.update(input_sha256={}), 'immutable input')

    def test_required_checks(self):
        self.reject(lambda r: r.update(checks={'custom': True}), 'acceptance checks')

    def test_failed_scope(self):
        self.reject(lambda r: r['checks'].update(nonface_materials_unchanged=False), 'acceptance checks')

    def test_reference_authority(self):
        self.reject(lambda r: r.update(reference_input='substitute.png'), 'reference authority')

    def test_no_unsupported_likeness_claim(self):
        self.reject(lambda r: r.update(human_likeness_accepted=True), 'Unsupported')

    def test_original_actions(self):
        self.reject(lambda r: r['candidate_rig']['actions']['idle'].update(sha256='0'*64), 'action fingerprint')

    def test_original_drivers(self):
        self.reject(lambda r: r['candidate_rig'].update(behavior_sha256='0'*64), 'rig fingerprint')

    def test_exact_lid_pivots(self):
        self.reject(lambda r: r['face_scope'].update(candidate_lid_pivots={}), 'pivot contradiction')

    def test_protected_objects_required(self):
        self.reject(lambda r: r['face_scope'].update(protected_object_count=0), 'nonface protection')

    def test_protected_hash_count(self):
        self.reject(lambda r: r['face_scope'].update(protected_geometry_sha256={}), 'protected source hashes')

    def test_partial_blinks_required(self):
        self.reject(lambda r: r.update(source_blink_samples=[]), 'Partial blink')

    def test_actual_glb_counts_override_claims(self):
        report=self.report();report['triangles']+=2
        data=(REVIEW/(KIND+'-'+contract.revision(KIND)+'.glb')).read_bytes()
        with self.assertRaisesRegex(ValueError, 'counts contradict'):
            deliver.legacy.validate_glb(data,report,KIND)

    def test_idempotent_delivery_preflight(self):
        plan=deliver.prepare(REVIEW,KIND)
        self.assertEqual(len(plan.artifacts),25)
        self.assertTrue(all(plan.observed_targets[a.target]==a.checksum for a in plan.artifacts))

    def test_stale_source_builder(self):
        digest=deliver.staged.digest
        with patch.object(deliver.staged,'digest',side_effect=lambda p: '0'*64 if Path(p).name=='guards.py' else digest(p)):
            with self.assertRaisesRegex(ValueError,'builder changed'):
                deliver.prepare(REVIEW,KIND)

    def test_existing_new_version_is_not_blindly_overwritten(self):
        digest=deliver.staged.existing_hash
        with patch.object(deliver.staged,'existing_hash',side_effect=lambda p: '0'*64 if Path(p).name=='manifest.json' else digest(p)):
            with self.assertRaisesRegex(FileExistsError,'Different existing content'):
                deliver.prepare(REVIEW,KIND)

    def test_destination_race(self):
        plan=deliver.prepare(REVIEW,KIND);victim=plan.artifacts[-1].target
        digest=deliver.staged.existing_hash
        with patch.object(deliver.staged,'existing_hash',side_effect=lambda p: '0'*64 if p==victim else digest(p)):
            with self.assertRaisesRegex(FileExistsError,'changed after preflight'):
                deliver.staged.verify_destinations(plan)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review',required=True)
    parser.add_argument('--kind',required=True,choices=contract.KINDS)
    args,rest=parser.parse_known_args()
    REVIEW,KIND=Path(args.review).resolve(),args.kind
    plan=deliver.prepare(REVIEW,KIND)
    before={a.target:hashlib.sha256(a.target.read_bytes()).digest() for a in plan.artifacts}
    result=unittest.main(argv=['test_delivery.py']+rest,exit=False).result
    if any(hashlib.sha256(p.read_bytes()).digest()!=sha for p,sha in before.items()):
        raise RuntimeError('Read-only test modified a delivered artifact')
    raise SystemExit(0 if result.wasSuccessful() else 1)

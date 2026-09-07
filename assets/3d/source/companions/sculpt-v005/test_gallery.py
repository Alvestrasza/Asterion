"""Read-only regression tests for the fixed face-comparison layout boundary."""
import copy
import unittest
from unittest.mock import patch
import gallery


class GalleryGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts,cls.value=gallery.build_artifacts()
        cls.before={a.target:gallery.digest(a.target) for a in cls.artifacts}

    @classmethod
    def tearDownClass(cls):
        assert cls.before=={p:gallery.digest(p) for p in cls.before}, 'Read-only test changed a gallery'

    def test_fixed_layout_targets(self):
        plan=gallery.preflight(self.artifacts,self.value,True)
        self.assertEqual(len(plan.artifacts),10)
        self.assertTrue(all(a.target.parent==gallery.OUT.resolve() for a in plan.artifacts))

    def test_unverified_replacement_rejected(self):
        item=self.artifacts[-1]
        changed=gallery.staged.Artifact(item.target,item.content+b' ')
        with self.assertRaisesRegex(FileExistsError,'existing gallery content'):
            gallery.preflight((changed,),self.value)

    def test_preceding_bytes_are_bound(self):
        original=gallery.staged.existing_hash;victim=self.artifacts[0].target
        with patch.object(gallery.staged,'existing_hash',side_effect=lambda p:'0'*64 if p==victim else original(p)):
            with self.assertRaisesRegex(ValueError,'gallery bytes changed'):
                gallery.preflight(self.artifacts,self.value,True)

    def test_receipt_cannot_redirect(self):
        receipt=copy.deepcopy(gallery.json.loads((gallery.OUT/'gallery-manifest.json').read_bytes()))
        receipt['figures'][0]['comparison']='public/assets/companions/asterion.png'
        with patch.object(gallery.json,'loads',return_value=receipt):
            with self.assertRaisesRegex(ValueError,'Unexpected comparison target'):
                gallery.preflight(self.artifacts,self.value,True)

    def test_output_must_stay_in_layout_directory(self):
        item=gallery.staged.Artifact(gallery.REPO/'README.md',b'no')
        with self.assertRaisesRegex(ValueError,'outside fixed directory'):
            gallery.preflight((item,),self.value)

    def test_race_after_preflight(self):
        plan=gallery.preflight(self.artifacts,self.value,True)
        original=gallery.staged.existing_hash;victim=self.artifacts[-1].target
        with patch.object(gallery.staged,'existing_hash',side_effect=lambda p:'0'*64 if p==victim else original(p)):
            with self.assertRaisesRegex(FileExistsError,'changed after preflight'):
                gallery.staged.verify_destinations(plan)


if __name__=='__main__': unittest.main()

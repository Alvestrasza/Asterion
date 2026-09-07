"""Read-only gates for refreshing a hash-bound likeness comparison layout."""
import copy
import unittest
from unittest.mock import patch
import gallery


class GalleryGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts,cls.value=gallery.build_artifacts()
        cls.before={item.target:gallery.digest(item.target) for item in cls.artifacts}

    @classmethod
    def tearDownClass(cls):
        assert cls.before=={path:gallery.digest(path) for path in cls.before},'Read-only tests changed a layout'

    def test_verified_update_targets_only_ten_layout_files(self):
        plan=gallery.preflight(self.artifacts,self.value,True)
        self.assertEqual(len(plan.artifacts),10)
        self.assertTrue(all(a.target.parent==gallery.OUT.resolve() for a in plan.artifacts))

    def test_unapproved_changed_output_is_rejected(self):
        victim=self.artifacts[-1]
        changed=gallery.staged.Artifact(victim.target,victim.content+b' ')
        with self.assertRaisesRegex(FileExistsError,'existing gallery content'):
            gallery.preflight((changed,),self.value)

    def test_changed_preceding_image_is_rejected(self):
        existing=gallery.staged.existing_hash
        victim=self.artifacts[0].target
        def changed(path):return '0'*64 if path==victim else existing(path)
        with patch.object(gallery.staged,'existing_hash',side_effect=changed),self.assertRaisesRegex(ValueError,'gallery bytes changed'):
            gallery.preflight(self.artifacts,self.value,True)

    def test_receipt_cannot_redirect_targets(self):
        receipt=copy.deepcopy(gallery.json.loads((gallery.OUT/'gallery-manifest.json').read_bytes()))
        receipt['figures'][0]['comparison']='public/assets/companions/asterion.png'
        with patch.object(gallery.json,'loads',return_value=receipt),self.assertRaisesRegex(ValueError,'Unexpected comparison target'):
            gallery.preflight(self.artifacts,self.value,True)

    def test_destination_cannot_escape_layout_directory(self):
        outside=gallery.staged.Artifact(gallery.REPO/'README.md',b'not a layout')
        with self.assertRaisesRegex(ValueError,'outside fixed directory'):
            gallery.preflight((outside,),self.value)

    def test_destination_race_after_preflight_is_rejected(self):
        plan=gallery.preflight(self.artifacts,self.value,True)
        existing=gallery.staged.existing_hash
        victim=self.artifacts[-1].target
        def changed(path):return 'F'*64 if path==victim else existing(path)
        with patch.object(gallery.staged,'existing_hash',side_effect=changed),self.assertRaisesRegex(FileExistsError,'changed after preflight'):
            gallery.staged.verify_destinations(plan)


if __name__=='__main__':unittest.main()

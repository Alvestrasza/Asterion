"""Small isolated fixtures for Asterion-specific delivery evidence gates."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import deliver_refinement as delivery


class RefinementDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='asterion-delivery-test-',dir=delivery.REPO/'.private')
        base=Path(self.temporary.name);self.repo=base/'repo';self.work=base/'work'
        self.root=self.repo/'assets/3d/source/asterion/sculpt-v002'
        self.root.mkdir(parents=True);self.work.mkdir()
        self.repatch=patch.object(delivery,'REPO',self.repo);self.rootpatch=patch.object(delivery,'ROOT',self.root)
        self.repatch.start();self.rootpatch.start()
        self.addCleanup(self.temporary.cleanup);self.addCleanup(self.repatch.stop);self.addCleanup(self.rootpatch.stop)
        self.put(self.work/'asterion-sculpt-v002.blend',b'new editable master')
        self.put(self.work/'asterion-sculpt-v002.glb',b'new glb')
        self.put(self.root.parent/'sculpt-v001/asterion-sculpt-v001.blend',b'original master')
        self.original_glb=self.repo/'public/assets/3d/asterion/asterion-sculpt-v001.glb'
        self.put(self.original_glb,b'original glb')
        self.reference=self.repo/'assets/3d/reference/asterion/sculpt-v001/asterion-approved-turnaround.png'
        self.put(self.reference,b'approved image')
        self.put(self.root/'refine_geometry.py',b'builder fixture')
        self.put(self.root/'validate_refinement.py',b'validator fixture')
        digest=delivery.staging.digest
        clips=['blink','eat','happy','idle','pet_reaction','play','sleep','wake','walk']
        self.report={'source_sha256':digest(self.work/'asterion-sculpt-v002.blend'),
            'model_sha256':digest(self.work/'asterion-sculpt-v002.glb'),
            'baseline_master_sha256':digest(self.root.parent/'sculpt-v001/asterion-sculpt-v001.blend'),
            'reference_sha256':digest(self.reference),'geometry_preview_only':False,'animations_unchanged':True,
            'builder_sha256':{(self.root/'refine_geometry.py').relative_to(self.repo).as_posix():digest(self.root/'refine_geometry.py')},
            'renders':{},'triangles':4999970,'blender':'test fixture'}
        self.check={'passed':True,'checks':{'fixture_check':True},'master_sha256':self.report['source_sha256'],
            'glb_sha256':self.report['model_sha256'],'baseline_sha256':self.report['baseline_master_sha256'],
            'baseline_glb_sha256':digest(self.original_glb),'validator_sha256':digest(self.root/'validate_refinement.py'),
            'triangle_count_evidence':{'authored':4999970},'geometry':{'triangles':4999970,'vertices':2500000},
            'editable_solid_meshes':100,'native_groom':{'native_strands':17911,'native_points':250754},
            'candidate_fingerprint':{'actions':{name:{'sha256':'fixture'} for name in clips},'rest_sha256':'fixture'},'renders':{}}
        for name in ('hero','front','side','rear','face'):
            path=self.work/('asterion-'+name+'.png');self.put(path,name.encode())
            self.report['renders'][name]=str(path)
        for name in ('hero','rear','face','closed_blink_front'):
            path=self.work/'validation'/(name+'.png');self.put(path,name.encode())
            self.check['renders'][name]={'path':str(path),'sha256':digest(path)}
        self.export={'triangles':4999970,'bytes':len(b'new glb'),'animations':clips,'materials':18,'export_settings':{}}
        self.save()

    def put(self,path,content):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)

    def save(self):
        for path,data in [(self.work/'build-report.json',self.report),(self.work/'validation/refinement-validation.json',self.check),(self.work/'export-report.json',self.export)]:
            self.put(path,json.dumps(data).encode())

    def test_success_is_versioned_and_paths_are_relative(self):
        plan=delivery.prepare(self.work)
        manifest=delivery.staging.execute_delivery(plan)
        self.assertEqual(manifest['version'],'sculpt-v002')
        self.assertEqual(manifest['baseline_glb_sha256'],delivery.staging.digest(self.original_glb))
        self.assertEqual(self.original_glb.read_bytes(),b'original glb')
        check=json.loads((self.repo/manifest['validation']).read_text())
        self.assertFalse(Path(check['baseline_glb']).is_absolute())
        delivery.staging.execute_delivery(delivery.prepare(self.work))

    def test_original_glb_change_is_rejected(self):
        self.original_glb.write_bytes(b'changed original')
        with self.assertRaisesRegex(ValueError,'calibration GLB'):delivery.prepare(self.work)

    def test_preview_is_not_a_delivery(self):
        self.report['geometry_preview_only']=True;self.save()
        with self.assertRaisesRegex(ValueError,'Incomplete'):delivery.prepare(self.work)

    def test_contradictory_validation_is_rejected(self):
        self.check['checks']['fixture_check']=False;self.save()
        with self.assertRaisesRegex(ValueError,'all pass'):delivery.prepare(self.work)

    def test_builder_and_validator_are_hash_bound(self):
        for name,message in [('refine_geometry.py','Builder changed'),('validate_refinement.py','Validator changed')]:
            path=self.root/name;before=path.read_bytes();path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,message):delivery.prepare(self.work)
            path.write_bytes(before)

    def test_triangle_metadata_mismatch_is_rejected(self):
        self.export['triangles']-=1;self.save()
        with self.assertRaisesRegex(ValueError,'Triangle evidence'):delivery.prepare(self.work)

    def test_import_render_mismatch_is_rejected(self):
        Path(self.check['renders']['face']['path']).write_bytes(b'changed render')
        with self.assertRaisesRegex(ValueError,'Import render changed'):delivery.prepare(self.work)

    def test_late_manifest_conflict_writes_no_new_model(self):
        self.put(self.root/'manifest.json',b'user content')
        with self.assertRaises(FileExistsError):delivery.prepare(self.work)
        self.assertEqual((self.root/'manifest.json').read_bytes(),b'user content')
        self.assertFalse((self.repo/'public/assets/3d/asterion/asterion-sculpt-v002.glb').exists())


if __name__=='__main__':unittest.main()

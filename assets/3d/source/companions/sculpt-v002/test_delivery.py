"""Stdlib tests for delivery evidence, all-input preflight and staged rollback.

The fixture binaries are opaque bytes: these tests exercise handoff semantics,
not Blender or glTF correctness. Run: python -m unittest discover -s <this dir>
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import deliver


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='asterion-delivery-test-')
        self.addCleanup(self.temporary.cleanup)
        self.repo=Path(self.temporary.name).resolve()
        self.kind='dog'
        self.original=self.repo/'public/assets/companions/dog.png'
        self.write(self.original,b'unchanged approved artwork')
        self.builder=self.repo/'assets/3d/source/companions/sculpt-v002/build.py'
        self.write(self.builder,b'unchanged builder')
        self.master=self.repo/'assets/3d/source/dog/sculpt-v002/dog-sculpt-v002.blend'
        self.model=self.repo/'public/assets/3d/dog/dog-sculpt-v002.glb'
        self.manifest=self.master.parent/'manifest.json'
        self.review=self.repo/'assets/3d/reference/dog/sculpt-v002'

    def write(self,path,data):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)

    def write_json(self,path,data):
        self.write(path,deliver.json_bytes(data))

    def read_json(self,path):
        return json.loads(path.read_bytes())

    def bundle(self,label):
        work=self.repo/'.private'/label
        glb=work/'dog-sculpt-v002.glb';blend=work/'dog-sculpt-v002.blend'
        self.write(glb,('GLB '+label).encode());self.write(blend,('BLEND '+label).encode())
        views={}
        for view in ('hero','front','side','rear'):
            path=work/('dog-sculpt-'+view+'.png')
            self.write(path,(label+' source '+view).encode());views[view]=str(path)
        imported={}
        for view in ('hero','rear','blink'):
            path=work/'validation'/('dog-import-'+view+'.png')
            self.write(path,(label+' import '+view).encode());imported[view]=str(path)
        clips=('idle','blink','happy','eat','sleep','walk')
        motion_renders=[]
        for clip in clips:
            path=work/'motion'/('dog-'+clip+'.png')
            self.write(path,(label+' motion '+clip).encode())
            motion_renders.append({'clip':clip,'frame':1,'image':str(path)})
        sheet=work/'motion'/'dog-motion-contact.png';self.write(sheet,(label+' contact').encode())
        check={'asset':str(glb),'sha256':deliver.digest(glb),'master_sha256':deliver.digest(blend),
               'passed':True,'checks':{'verified':True},'renders':imported,
               'bytes':glb.stat().st_size,'triangles':123456,'vertices':65432,
               'bones':12,'materials':19,'draw_calls':19,'blender':'fixture',
               'animation_samples':{clip:[] for clip in clips},'animation_limit':'Fixture only'}
        motion={'source_glb':str(glb),'source_sha256':deliver.digest(glb),'passed':True,
                'checks':{'verified':True},'renders':motion_renders,'contact_sheet':str(sheet),
                'samples':[],'collision_free_verified':False}
        report={'glb_sha256':deliver.digest(glb),'blend_sha256':deliver.digest(blend),
                'reference_sha256':deliver.digest(self.original),'renders':views,
                'builder_sha256':{self.builder.relative_to(self.repo).as_posix():deliver.digest(self.builder)},
                'spec':{'kind':'dog','name':'Brumo','notes':['Fixture only']},
                'editable_source_meshes_preserved':123}
        self.write_json(work/'build-report.json',report)
        self.write_json(work/'validation/import-validation.json',check)
        self.write_json(work/'motion/motion-inspection.json',motion)
        return work

    def prepare(self,work,previous=None):
        return deliver.prepare_delivery(work,'dog',repo=self.repo,previous=previous)

    def release(self,work,previous=None):
        return deliver.execute_delivery(self.prepare(work,previous))

    def output_snapshot(self):
        paths=[]
        for root in (self.master.parent,self.model.parent,self.review):
            if root.exists():paths.extend(p for p in root.rglob('*') if p.is_file())
        return {str(path.relative_to(self.repo)):path.read_bytes() for path in paths}

    def test_success_and_identical_repeat_bind_actual_master(self):
        work=self.bundle('first');manifest=self.release(work)
        self.assertEqual(self.model.read_bytes(),(work/self.model.name).read_bytes())
        self.assertEqual(self.master.read_bytes(),(work/self.master.name).read_bytes())
        check=self.read_json(self.review/'import-validation.json')
        self.assertEqual(check['master_sha256'],deliver.digest(self.master))
        self.assertEqual(manifest['source_sha256'],check['master_sha256'])
        before=self.output_snapshot();self.release(work)
        self.assertEqual(before,self.output_snapshot())

    def test_missing_last_source_image_writes_nothing(self):
        work=self.bundle('missing')
        (work/'motion/dog-motion-contact.png').unlink()
        with self.assertRaises(FileNotFoundError):self.prepare(work)
        self.assertEqual({},self.output_snapshot())

    def test_last_render_conflict_preserves_existing_binaries(self):
        old=self.bundle('old');self.release(old);new=self.bundle('new')
        target=self.review/'motion/dog-motion-contact.png'
        self.write(target,b'unrelated edited image')
        before=self.output_snapshot()
        with self.assertRaises(FileExistsError):self.prepare(new,old)
        self.assertEqual(before,self.output_snapshot())

    def test_manifest_conflict_is_checked_before_any_copy(self):
        old=self.bundle('old');self.release(old);new=self.bundle('new')
        self.write(self.manifest,b'unrelated existing manifest')
        before=self.output_snapshot()
        with self.assertRaises(FileExistsError):self.prepare(new,old)
        self.assertEqual(before,self.output_snapshot())

    def test_both_validation_metadata_files_are_guarded(self):
        old=self.bundle('metadata-old');self.release(old);new=self.bundle('metadata-new')
        for name in ('import-validation.json','motion-validation.json'):
            with self.subTest(name=name):
                target=self.review/name;prior=target.read_bytes()
                self.write(target,b'edited validation metadata')
                before=self.output_snapshot()
                with self.assertRaises(FileExistsError):self.prepare(new,old)
                self.assertEqual(before,self.output_snapshot())
                self.write(target,prior)

    def test_exact_previous_review_authorizes_metadata_and_binary_replacement(self):
        old=self.bundle('old');self.release(old);new=self.bundle('new')
        historical=self.repo/'assets/3d/source/dog/sculpt-v001/untouched.blend'
        self.write(historical,b'earlier authority')
        result=self.release(new,old)
        self.assertEqual(result['model_sha256'],deliver.digest(self.model))
        self.assertEqual(result['source_sha256'],deliver.digest(self.master))
        self.assertEqual(b'earlier authority',historical.read_bytes())
        self.assertEqual((new/'motion/dog-motion-contact.png').read_bytes(),
                         (self.review/'motion/dog-motion-contact.png').read_bytes())

    def test_missing_or_wrong_master_validation_hash_rejects_current_delivery(self):
        work=self.bundle('master-mismatch');path=work/'validation/import-validation.json'
        correct=self.read_json(path)
        for value in (None,'0'*64):
            with self.subTest(value=value):
                altered=dict(correct)
                if value is None:altered.pop('master_sha256')
                else:altered['master_sha256']=value
                self.write_json(path,altered)
                with self.assertRaisesRegex(ValueError,'master validation'):self.prepare(work)
                self.assertEqual({},self.output_snapshot())

    def test_contradictory_pass_flag_does_not_authorize_delivery(self):
        work=self.bundle('false-check');path=work/'motion/motion-inspection.json'
        report=self.read_json(path);report['checks']['verified']=False;self.write_json(path,report)
        with self.assertRaisesRegex(ValueError,'checks have not passed'):self.prepare(work)
        self.assertEqual({},self.output_snapshot())

    def test_changed_builder_is_rejected_before_output_writes(self):
        work=self.bundle('builder-mismatch');self.write(self.builder,b'changed implementation')
        with self.assertRaisesRegex(ValueError,'Builder changed'):self.prepare(work)
        self.assertEqual({},self.output_snapshot())

    def test_target_changed_after_preflight_is_preserved(self):
        old=self.bundle('old');self.release(old);new=self.bundle('new');plan=self.prepare(new,old)
        self.write(self.manifest,b'user edit after preflight');before=self.output_snapshot()
        with self.assertRaisesRegex(FileExistsError,'after preflight'):deliver.execute_delivery(plan)
        self.assertEqual(before,self.output_snapshot())

    def test_late_commit_failure_rolls_back_all_prior_replacements(self):
        old=self.bundle('old');self.release(old);new=self.bundle('new');plan=self.prepare(new,old)
        before=self.output_snapshot();real_replace=deliver.os.replace;failed=False
        def fail_once(source,target):
            nonlocal failed
            if Path(target)==self.manifest and not failed:
                failed=True;raise OSError('Injected final manifest failure')
            return real_replace(source,target)
        with patch.object(deliver.os,'replace',side_effect=fail_once):
            with self.assertRaisesRegex(OSError,'Injected'):deliver.execute_delivery(plan)
        self.assertTrue(failed)
        self.assertEqual(before,self.output_snapshot())
        self.assertEqual([],list((self.repo/'.private').glob('companion-delivery-*')))


if __name__=='__main__':unittest.main()

"""Pure provenance/path regression checks; no production file is loaded."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
import copy

sys.modules.setdefault('bpy', types.ModuleType('bpy'))
spec = importlib.util.spec_from_file_location('final_verifier', Path(__file__).with_name('verify_final_blender.py'))
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class FinalProofTests(unittest.TestCase):
    def tail_proof(self):
        proof = {'schema':'asterion.blender-cstring-tail-proof.v1','blender_header':'BLENDER17-01v0502',
                 'decompressed_bytes':10000, 'zeroed_bytes':2,
                 'fields':[{'field':'FileSelectParams.dir[1282]','start':100,'end':1382,'bytes':1282,'first_nul_offset':102,'nonzero_tail_bytes':1},
                           {'field':'RenderData.pic[1024]','start':2000,'end':3024,'bytes':1024,'first_nul_offset':2020,'nonzero_tail_bytes':1}],
                 'changed_ranges':[{'field':'FileSelectParams.dir[1282]','start':103,'end':104,'bytes':1},
                                   {'field':'RenderData.pic[1024]','start':2021,'end':2022,'bytes':1}]}
        for key in ('all_other_decompressed_bytes_identical','only_allowlisted_post_nul_bytes_zeroed','live_cstrings_unchanged',
                    'source_bytes_unchanged','candidate_readback_verified'):
            proof[key]=True
        for key in ('sdna_sha256','before_decompressed_sha256','after_decompressed_sha256','unchanged_decompressed_segments_sha256','code_sha256'):
            proof[key]='A'*64
        return proof

    def test_relative_source_asset_is_allowed(self):
        name = 'assets/3d/source/example/example.blend'
        self.assertEqual(verifier.safe_relative(name).as_posix(), name)

    def test_unsafe_or_out_of_scope_paths_fail(self):
        for name in ('assets/3d/source/../example.blend', '/assets/3d/source/example.blend',
                     'assets\\3d\\source\\example.blend', 'bad:reference.blend',
                     '.private/example.blend', 'public/assets/3d/example.glb',
                     'assets/3d/source/example.blend1', 'assets/3d/source/bad\0.blend'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                verifier.safe_relative(name)

    def test_duplicate_receipt_rows_fail(self):
        row = {'path': 'assets/3d/source/example/example.blend'}
        with self.assertRaises(ValueError):
            verifier.load_rows({'files': [row, row]})

    def test_missing_receipt_rows_fail(self):
        with self.assertRaises(ValueError):
            verifier.load_rows({})

    def test_public_proof_accepts_only_portable_fields(self):
        verifier.safe_proof({'field': 'Scene.r.pic[1024]', 'changed_bytes': 4, 'scope_equal': True})
        with self.assertRaises(ValueError):
            verifier.safe_proof({'field': '.private/unpublished-input'})
        with self.assertRaises(ValueError):
            verifier.safe_proof({'.private/unpublished-input': 'value'})

    def test_only_declared_scene_path_keys_are_excluded(self):
        evidence = {'metadata_changes': [
            {'field': 'Scene[0].render.filepath'},
            {'field': 'Scene[0].custom_properties.reference_path'},
            {'field': 'screens[8].areas[4].spaces[0].params.directory'}]}
        baseline = {'datablocks': {'scenes': {'Scene': 'digest'}}}
        self.assertEqual(verifier.original_scene_exclusions(evidence, baseline), {'Scene': {'reference_path'}})

    def test_invalid_scene_mapping_fails(self):
        evidence = {'metadata_changes': [{'field': 'Scene[1].custom_properties.reference_path'}]}
        with self.assertRaises(ValueError):
            verifier.original_scene_exclusions(evidence, {'datablocks': {'scenes': {'Scene': 'digest'}}})

    def test_final_metadata_checks_exact_expected_values(self):
        def equal(a, b):
            return a.replace(b'\\', b'/') == b.replace(b'\\', b'/') if isinstance(a, bytes) else a.replace('\\', '/') == b.replace('\\', '/')
        sanitizer = types.SimpleNamespace(read_metadata=lambda field: b'//', portable_equal=equal)
        self.assertEqual(verifier.metadata_after_reopen(sanitizer, {'metadata_changes': [{'field':'directory','public_value':'//'}]}), [])
        self.assertEqual(verifier.metadata_after_reopen(sanitizer, {'metadata_changes': [{'field':'directory','public_value':'//other'}]}), ['directory'])

    def test_exact_tail_contract_is_accepted(self):
        verifier.validate_tail_proof(self.tail_proof())

    def test_failed_tail_assertions_are_rejected(self):
        for key in ('all_other_decompressed_bytes_identical','only_allowlisted_post_nul_bytes_zeroed','live_cstrings_unchanged',
                    'source_bytes_unchanged','candidate_readback_verified'):
            proof=self.tail_proof();proof[key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):
                verifier.validate_tail_proof(proof)

    def test_live_string_or_out_of_field_write_is_rejected(self):
        for start,end in ((101,102),(102,103),(1381,1383)):
            proof=self.tail_proof();proof['changed_ranges'][0].update(start=start,end=end,bytes=end-start)
            with self.subTest(start=start,end=end),self.assertRaises(ValueError):
                verifier.validate_tail_proof(proof)

    def test_extra_metadata_field_is_rejected(self):
        proof=self.tail_proof();proof['fields'].append(copy.deepcopy(proof['fields'][0]))
        with self.assertRaises(ValueError):verifier.validate_tail_proof(proof)

    def test_wrong_dna_extent_is_rejected(self):
        proof=self.tail_proof();proof['fields'][0]['end']+=4
        with self.assertRaises(ValueError):verifier.validate_tail_proof(proof)

    def test_inconsistent_tail_totals_are_rejected(self):
        proof=self.tail_proof();proof['zeroed_bytes']+=1
        with self.assertRaises(ValueError):verifier.validate_tail_proof(proof)


if __name__ == '__main__':
    unittest.main()

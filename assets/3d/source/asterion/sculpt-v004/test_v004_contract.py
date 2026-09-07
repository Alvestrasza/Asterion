"""Public equipment GLB contract checks; run with Python unittest."""
import copy
import importlib.util
import json
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('equipment_export', ROOT / 'export_equipment.py')
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


def fixture():
    primitive = {'indices': 0, 'attributes': {'POSITION': 1, 'JOINTS_0': 2, 'WEIGHTS_0': 3}}
    return {
        'nodes': [{'mesh': 0, 'skin': 0, 'extras': export.component_extras('body')},
                  {'mesh': 1, 'skin': 0, 'extras': export.component_extras('armor')}]
                 + [{'name': 'bone.' + str(i)} for i in range(22)],
        'meshes': [{'primitives': [copy.deepcopy(primitive)]} for _ in range(2)],
        'skins': [{'joints': list(range(2, 24))}], 'accessors': [{'count': 3}],
        'animations': [{'name': name} for name in export.CLIPS],
        'materials': [{'name': 'blue'}], 'buffers': [{'byteLength': 100}],
        'extensionsUsed': ['EXT_meshopt_compression'],
        'bufferViews': [{'extensions': {'EXT_meshopt_compression': {'filter': 'NONE'}}}],
    }


class EquipmentContract(unittest.TestCase):
    def test_two_components_share_the_one_22_bone_skin(self):
        result = export.inspect_document(fixture())
        self.assertTrue(all(result['checks'].values()), result['checks'])
        self.assertEqual(result['components']['armor']['triangles'], 1)

    def test_private_extras_are_rejected_at_any_depth(self):
        document = fixture()
        document['materials'][0]['extras'] = {'ast_export_temporary': 'private-token'}
        self.assertFalse(export.inspect_document(document)['checks']['only_public_equipment_extras'])

    def test_historical_encoder_filters_are_reported_without_lossless_claim(self):
        document = fixture()
        document['bufferViews'][0]['extensions']['EXT_meshopt_compression']['filter'] = 'QUATERNION'
        result = export.inspect_document(document)
        self.assertTrue(all(result['checks'].values()), result['checks'])
        self.assertEqual(result['compression']['buffer_view_filters'], {'QUATERNION': 1})
        self.assertFalse(result['compression']['lossless_claimed'])

    def test_unbound_or_duplicate_equipment_is_rejected(self):
        for mutation in ('skin', 'component', 'equipment_id'):
            document = fixture()
            if mutation == 'skin':
                document['nodes'][1]['skin'] = 1
            elif mutation == 'component':
                document['nodes'][1]['extras']['asterion_component'] = 'body'
            else:
                document['nodes'][1]['extras']['asterion_equipment_id'] = 'unregistered'
            self.assertFalse(all(export.inspect_document(document)['checks'].values()), mutation)

    def test_v003_demonstrates_the_absent_equipment_seam(self):
        path = ROOT.parents[4] / 'public/assets/3d/asterion/asterion-sculpt-v003.glb'
        with path.open('rb') as stream:
            stream.seek(12)
            size, _ = struct.unpack('<II', stream.read(8))
            document = json.loads(stream.read(size))
        result = export.inspect_document(document)
        self.assertFalse(result['checks']['two_character_meshes'])
        self.assertFalse(result['checks']['exact_body_armor_nodes'])


if __name__ == '__main__':
    unittest.main()

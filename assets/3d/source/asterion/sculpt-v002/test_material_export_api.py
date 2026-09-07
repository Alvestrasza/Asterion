"""Tiny real glTF export regression: preserve both palette and vertex detail."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

import bpy

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'sculpt-v001'))
import build_sculpt as g
sys.path.insert(0,str(ROOT))
import refine_geometry


class MaterialExportTests(unittest.TestCase):
    def test_palette_factor_and_vertex_detail_survive_actual_export(self):
        g.materials()
        obj=g.uv('material_test',(0,0,0),(.3,.4,.5),'navy',seg=16,rings=8)
        refine_geometry.surface_color(g)
        g.active(obj)
        private=ROOT.parents[4]/'.private'
        with tempfile.TemporaryDirectory(prefix='asterion-material-test-',dir=private) as folder:
            path=Path(folder)/'material-test.glb'
            bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
                export_animations=False,export_cameras=False,export_lights=False,
                export_vertex_color='MATERIAL',export_all_vertex_colors=False)
            data=path.read_bytes();length=struct.unpack_from('<I',data,12)[0]
            document=json.loads(data[20:20+length])
            material=next(m for m in document['materials'] if m['name']=='AST_navy')
            actual=material['pbrMetallicRoughness'].get('baseColorFactor',[1,1,1,1])
            for got,expected in zip(actual,g.color('05162F')):
                self.assertAlmostEqual(got,expected,places=6)
            primitive=document['meshes'][0]['primitives'][0]
            accessor=document['accessors'][primitive['attributes']['COLOR_0']]
            view=document['bufferViews'][accessor['bufferView']]
            binary_start=20+length+8
            start=binary_start+view.get('byteOffset',0)+accessor.get('byteOffset',0)
            code,size,scale={5126:('f',4,1),5123:('H',2,65535),5121:('B',1,255)}[accessor['componentType']]
            width={'VEC3':3,'VEC4':4}[accessor['type']]
            stride=view.get('byteStride',size*width)
            red=[struct.unpack_from('<'+code,data,start+i*stride)[0]/scale for i in range(accessor['count'])]
            self.assertGreater(max(red)-min(red),.001)
            self.assertGreater(min(red),.9)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MaterialExportTests))
    if not result.wasSuccessful():raise SystemExit(1)

"""Tiny Blender API tests; no original scene load, rendering or file output.

Run in a disposable Blender process with --background --factory-startup --python.
"""
from array import array
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import bpy
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
import hair_groom as groom


class GroomContractTests(unittest.TestCase):
    def test_integer_budget_and_layout(self):
        self.assertEqual(groom.SIDES,5)
        self.assertEqual(groom.POINTS_PER_STRAND,14)
        self.assertEqual(groom.TRIANGLES_PER_STRAND,136)
        for budget in (680,2200000,2450000,2600000,3200000):
            count=budget//136
            assigned=groom._allocate(count,[.30,.30,.10,.10,.20])
            self.assertEqual(sum(assigned),count)
            self.assertLessEqual(sum(assigned)*136,budget)
            self.assertLess(budget-sum(assigned)*136,136)

    def test_native_and_mesh_correspond_at_rest_and_pose(self):
        data=bpy.data.armatures.new('HG_TEST_armature')
        rig=bpy.data.objects.new('HG_TEST_rig',data)
        bpy.context.collection.objects.link(rig)
        bpy.context.view_layer.objects.active=rig;rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bone=data.edit_bones.new('head');bone.head=(0,1,2);bone.tail=(0,1,3)
        bpy.ops.object.mode_set(mode='OBJECT')
        material=bpy.data.materials.new('HG_TEST_material');material.use_nodes=True
        g=SimpleNamespace(ASSET=[])
        positions,radii,shades=array('f'),array('f'),array('i',[0,0,0])
        for strand in range(3):
            for point in range(groom.POINTS_PER_STRAND):
                t=point/(groom.POINTS_PER_STRAND-1)
                positions.extend((.07*strand+.08*math.sin(t*2),1+t*.5,2.2+t*.4))
                radii.append(.004*(1-t)+.0001)
        actions=tuple(a.as_pointer() for a in bpy.data.actions)
        native,mesh,report=groom._make_pair(g,rig,'test','head',positions,radii,shades,[material])
        self.assertEqual(native.type,'CURVES')
        self.assertTrue(native['ast_native_hair'])
        self.assertTrue(mesh['ast_hair_export'])
        self.assertEqual(native['ast_hair_group'],mesh['ast_hair_group'])
        self.assertEqual(len(native.data.curves),3)
        self.assertEqual(len(mesh.data.vertices),3*14*5)
        mesh.data.calc_loop_triangles()
        self.assertEqual(len(mesh.data.loop_triangles),3*136)
        self.assertTrue(report['all_strands_correspond'])
        self.assertLess(report['stored_max_centroid_error'],1.e-6)
        self.assertLess(report['stored_max_radius_error'],1.e-6)
        mesh.hide_set(False)
        for angle in (0.0,.31,-.22):
            rig.pose.bones['head'].rotation_mode='XYZ'
            rig.pose.bones['head'].rotation_euler.x=angle
            bpy.context.view_layer.update()
            evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
            for point in (0,7,13,18,27,41):
                expected=native.matrix_world@Vector(positions[point*3:point*3+3])
                ring=[evaluated.matrix_world@evaluated.data.vertices[point*5+i].co for i in range(5)]
                centroid=sum(ring,Vector())/5
                self.assertLess((centroid-expected).length,1.e-5)
        self.assertEqual(actions,tuple(a.as_pointer() for a in bpy.data.actions))


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(GroomContractTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)

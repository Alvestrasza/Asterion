"""Synthetic, in-memory regression checks for metadata-only asset guards.

Run inside Blender with --background --factory-startup --disable-autoexec.
No production inputs are loaded. The one save regression writes only a fresh
synthetic fixture inside the authorized private publication report directory.
"""
import importlib.util
import json
from pathlib import Path
import unittest
import tempfile

import bpy
from mathutils import Matrix


spec = importlib.util.spec_from_file_location('sanitize_blender', Path(__file__).with_name('sanitize_blender.py'))
sanitize = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sanitize)


class SemanticMutationTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        mesh = bpy.data.meshes.new('FixtureMesh')
        mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
        self.mesh = mesh
        self.obj = bpy.data.objects.new('FixtureObject', mesh)
        bpy.context.collection.objects.link(self.obj)
        self.material = bpy.data.materials.new('FixtureMaterial')
        self.material.use_nodes = True
        mesh.materials.append(self.material)
        self.armature = bpy.data.armatures.new('FixtureArmature')
        self.rig = bpy.data.objects.new('FixtureRig', self.armature)
        bpy.context.collection.objects.link(self.rig)
        bpy.context.view_layer.objects.active = self.rig
        self.rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bone = self.armature.edit_bones.new('Root')
        bone.head, bone.tail = (0, 0, 0), (0, 0, 1)
        bpy.ops.object.mode_set(mode='OBJECT')
        modifier = self.obj.modifiers.new('FixtureBinding', 'ARMATURE')
        modifier.object = self.rig
        self.group = self.obj.vertex_groups.new(name='Root')
        self.group.add([0, 1, 2], 1.0, 'REPLACE')
        self.obj.keyframe_insert(data_path='location', index=0, frame=1)
        self.obj.location.x = 1.0
        self.obj.keyframe_insert(data_path='location', index=0, frame=10)
        self.hair = bpy.data.hair_curves.new('FixtureHair')
        self.hair.add_curves([3])
        self.hair.set_types(type='POLY')
        self.hair.attributes['position'].data.foreach_set('vector', [0, 0, 0, 0, 0, 1, 0, 0, 2])
        hair_object = bpy.data.objects.new('FixtureHairObject', self.hair)
        bpy.context.collection.objects.link(hair_object)

    def snapshot(self):
        return sanitize.Semantics({}).snapshot()

    def detects(self, mutation, collection):
        before = self.snapshot()
        mutation()
        after = self.snapshot()
        differences = sanitize.compare(before, after)
        self.assertNotEqual(before['sha256'], after['sha256'])
        self.assertTrue(any(item['collection'] == collection for item in differences), differences)

    def test_no_change_is_stable(self):
        self.assertEqual(self.snapshot()['sha256'], self.snapshot()['sha256'])

    def test_mesh_vertex(self):
        self.detects(lambda: setattr(self.mesh.vertices[0].co, 'x', .125), 'meshes')

    def test_mesh_topology(self):
        def mutate():
            self.mesh.clear_geometry()
            self.mesh.from_pydata([(0,0,0),(1,0,0),(0,1,0),(1,1,0)], [], [(0,1,2),(1,3,2)])
        self.detects(mutate, 'meshes')

    def test_mesh_attribute(self):
        attribute = self.mesh.attributes.new('FixtureFloat', 'FLOAT', 'POINT')
        self.detects(lambda: setattr(attribute.data[0], 'value', .3125), 'meshes')

    def test_deform_weights(self):
        self.detects(lambda: self.group.add([0], .5, 'REPLACE'), 'meshes')

    def test_material_node(self):
        shader = next(node for node in self.material.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
        self.detects(lambda: setattr(shader.inputs['Roughness'], 'default_value', .123), 'materials')

    def test_action_keyframe(self):
        action = self.obj.animation_data.action
        curve = action.layers[0].strips[0].channelbags[0].fcurves[0]
        self.detects(lambda: setattr(curve.keyframe_points[0].co, 'y', .375), 'actions')

    def test_action_interpolation(self):
        curve = self.obj.animation_data.action.layers[0].strips[0].channelbags[0].fcurves[0]
        self.detects(lambda: setattr(curve.keyframe_points[0], 'interpolation', 'LINEAR'), 'actions')

    def test_armature_rest_geometry(self):
        def mutate():
            bpy.ops.object.mode_set(mode='EDIT')
            self.armature.edit_bones['Root'].tail.x = .2
            bpy.ops.object.mode_set(mode='OBJECT')
        self.detects(mutate, 'armatures')

    def test_armature_binding(self):
        self.detects(lambda: setattr(self.obj.modifiers['FixtureBinding'], 'object', None), 'objects')

    def test_object_transform(self):
        self.detects(lambda: setattr(self.obj.delta_location, 'y', .23), 'objects')

    def test_parent_inverse(self):
        self.obj.parent = self.rig
        self.detects(lambda: setattr(self.obj, 'matrix_parent_inverse', Matrix.Translation((.1,.2,.3))), 'objects')

    def test_native_curve_position(self):
        self.detects(lambda: setattr(self.hair.attributes['position'].data[1].vector, 'x', .4), 'hair_curves')

    def test_native_curve_attribute(self):
        radius = self.hair.attributes.new('radius', 'FLOAT', 'POINT')
        self.detects(lambda: setattr(radius.data[1], 'value', .1), 'hair_curves')

    def test_material_shared_binding(self):
        replacement = bpy.data.materials.new('ReplacementMaterial')
        self.detects(lambda: self.mesh.materials.__setitem__(0, replacement), 'meshes')

    def test_driver_expression(self):
        curve = self.obj.driver_add('scale', 0)
        curve.driver.expression = '1.0'
        self.detects(lambda: setattr(curve.driver, 'expression', '1.25'), 'objects')

    def test_constraint_setting(self):
        constraint = self.obj.constraints.new('LIMIT_LOCATION')
        self.detects(lambda: setattr(constraint, 'use_min_x', True), 'objects')

    def test_shape_key_geometry(self):
        self.obj.shape_key_add(name='Basis')
        key = self.obj.shape_key_add(name='FixtureExpression')
        self.detects(lambda: setattr(key.data[0].co, 'z', .12), 'shape_keys')

    def test_legacy_curve_control_point(self):
        curve = bpy.data.curves.new('FixtureLegacyCurve', 'CURVE')
        spline = curve.splines.new('BEZIER')
        spline.bezier_points.add(1)
        self.detects(lambda: setattr(spline.bezier_points[0].co, 'z', .15), 'curves')

    def test_image_pixels_and_packed_bytes(self):
        image = bpy.data.images.new('FixturePackedImage', width=2, height=2)
        image.pack()
        def mutate():
            pixels = list(image.pixels)
            pixels[0] = .65
            image.pixels[:] = pixels
            image.pack()
        self.detects(mutate, 'images')

    def test_allowed_metadata_only(self):
        before = self.snapshot()
        bpy.context.scene.render.filepath = '//renders/fixture/'
        self.assertEqual(before['sha256'], self.snapshot()['sha256'])

    def test_save_preserves_unused_ids_without_persistent_flags(self):
        # Isolate orphan retention from the deliberately unevaluated animation
        # state created for mutation tests above. Real source inputs are already
        # saved/reopened before their semantic baselines are recorded.
        bpy.ops.wm.read_factory_settings(use_empty=True)
        orphan = bpy.data.materials.new('FixtureUnusedMaterial')
        orphan.use_nodes = True
        self.assertEqual(orphan.users, 0)
        self.assertFalse(orphan.use_fake_user)
        self.assertFalse(orphan.use_extra_user)
        before = self.snapshot()
        root = Path(__file__).resolve().parents[2] / '.private/publication-2026-09-07/blender-reports'
        root.mkdir(parents=True, exist_ok=True)
        output = Path(tempfile.mkdtemp(prefix='guard-save-test-', dir=root)) / 'fixture.blend'
        retained = sanitize.save_complete_copy(output)
        self.assertTrue(any(item['datablock'] == orphan.name for item in retained))
        self.assertFalse(orphan.use_extra_user)
        bpy.ops.wm.open_mainfile(filepath=str(output), load_ui=True, use_scripts=False)
        after = self.snapshot()
        self.assertEqual(before['sha256'], after['sha256'], sanitize.compare(before, after))
        self.assertIn('FixtureUnusedMaterial', bpy.data.materials)
        self.assertFalse(bpy.data.materials['FixtureUnusedMaterial'].use_fake_user)
        self.assertFalse(bpy.data.materials['FixtureUnusedMaterial'].use_extra_user)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SemanticMutationTests))
    print(json.dumps({'schema':'asterion.blender-publication-guard-tests.v1','tests':result.testsRun,
                      'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()}),flush=True)
    if not result.wasSuccessful():
        raise SystemExit(1)

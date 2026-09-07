"""Stdlib regression checks for animation fingerprints, without Blender runs."""
import copy
from types import SimpleNamespace
import unittest

import validate_refinement as validator


def rna(**values):
    props=[]
    for name,value in values.items():
        kind='BOOLEAN' if isinstance(value,bool) else 'STRING' if isinstance(value,str) else 'FLOAT'
        props.append(SimpleNamespace(identifier=name,type=kind))
    return SimpleNamespace(bl_rna=SimpleNamespace(properties=props),**values)


def curve():
    key=rna(co=[1.,.2],handle_left=[.5,.15],handle_right=[1.5,.25],
            handle_left_type='FREE',handle_right_type='FREE',interpolation='BEZIER',
            easing='AUTO',back=1.70158,amplitude=.8,period=.3,type='KEYFRAME',
            select_control_point=False)
    value=rna(data_path='pose.bones["head"].rotation_euler',array_index=0,
              extrapolation='CONSTANT',mute=False,auto_smoothing='NONE')
    value.keyframe_points=[key];value.sampled_points=[];value.group=None
    value.modifiers=[rna(type='NOISE',strength=.03,scale=2.,phase=.5)]
    value.driver=None
    return value


def action(value):
    bag=SimpleNamespace(fcurves=[value],groups=[],slot_handle=1,slot=None)
    strip=rna(type='KEYFRAME');strip.channelbags=[bag]
    layer=rna(name='Layer');layer.strips=[strip]
    result=rna(name='idle',use_frame_range=False,use_cyclic=True,use_fake_user=True)
    result.pose_markers=[];result.slots=[];result.layers=[layer];result.frame_range=[1.,121.]
    result.is_action_legacy=False;result.items=lambda:[]
    return result


class FingerprintTests(unittest.TestCase):
    def test_identical_full_action_data_has_identical_digest(self):
        first=action(curve());second=copy.deepcopy(first)
        a=validator.action_fingerprint(first);b=validator.action_fingerprint(second)
        self.assertEqual(a['sha256'],b['sha256'])
        self.assertEqual((a['curve_count'],a['key_count']),(1,1))

    def test_every_animating_key_property_changes_fingerprint(self):
        original=curve();before=validator.curve_fingerprint(original)['sha256']
        changes={'co':[1.,.21],'handle_left':[.5,.16],'handle_right':[1.5,.26],
                 'handle_left_type':'AUTO','handle_right_type':'VECTOR',
                 'interpolation':'LINEAR','easing':'EASE_IN','back':2.,'amplitude':.9,
                 'period':.4,'type':'BREAKDOWN'}
        for name,value in changes.items():
            with self.subTest(property=name):
                changed=copy.deepcopy(original);setattr(changed.keyframe_points[0],name,value)
                self.assertNotEqual(before,validator.curve_fingerprint(changed)['sha256'])

    def test_curve_modifier_parameters_are_not_omitted(self):
        original=curve();changed=copy.deepcopy(original);changed.modifiers[0].strength=.031
        self.assertNotEqual(validator.curve_fingerprint(original)['sha256'],validator.curve_fingerprint(changed)['sha256'])

    def test_curve_path_and_extrapolation_are_not_omitted(self):
        original=curve()
        for field,value in (('data_path','pose.bones["neck"].rotation_euler'),('array_index',1),
                            ('extrapolation','LINEAR'),('mute',True)):
            with self.subTest(field=field):
                changed=copy.deepcopy(original);setattr(changed,field,value)
                self.assertNotEqual(validator.curve_fingerprint(original)['sha256'],validator.curve_fingerprint(changed)['sha256'])

    def test_ui_key_selection_is_explicitly_not_animation_data(self):
        original=curve();changed=copy.deepcopy(original);changed.keyframe_points[0].select_control_point=True
        self.assertEqual(validator.curve_fingerprint(original)['sha256'],validator.curve_fingerprint(changed)['sha256'])

    def test_nonfinite_key_coordinates_fail_finite_evidence(self):
        value=curve();value.keyframe_points[0].co[1]=float('nan')
        result=validator.curve_fingerprint(value)
        self.assertFalse(result['finite_keys'])
        self.assertEqual(len(result['sha256']),64)

    def test_driver_expression_participates_in_fingerprint(self):
        first=curve();first.driver=rna(type='SCRIPTED',expression='frame*.1');first.driver.variables=[]
        second=copy.deepcopy(first);second.driver.expression='frame*.2'
        self.assertNotEqual(validator.curve_fingerprint(first)['sha256'],validator.curve_fingerprint(second)['sha256'])

    def test_layer_structure_participates_in_action_digest(self):
        first=action(curve());second=copy.deepcopy(first);second.layers[0].strips[0].channelbags[0].slot_handle=2
        self.assertNotEqual(validator.action_fingerprint(first)['sha256'],validator.action_fingerprint(second)['sha256'])

    def test_one_changed_action_rejects_source_preservation(self):
        actions={name:{'sha256':name,'finite_keys':True} for name in validator.CLIPS}
        original={'rest_sha256':'rest','behavior_sha256':'constraints','bones':22,
                  'fps':30,'fps_base':1.,'actions':actions}
        changed=copy.deepcopy(original);changed['actions']['eat']['sha256']='altered key data'
        checks=validator.compare_source(original,changed)
        self.assertTrue(checks['exact_nine_action_names'])
        self.assertFalse(checks['all_nine_complete_action_data_unchanged'])

    def test_measured_small_importer_triangle_losses_are_bounded(self):
        for authored,lost in ((1496672,0),(1325486,21),(1367850,3),(1325472,10),(1427002,4)):
            with self.subTest(authored=authored,lost=lost):
                evidence=validator.triangle_count_evidence(authored,authored-lost)
                self.assertTrue(evidence['passed'])
                self.assertEqual(evidence['triangle_loss'],lost)
                self.assertEqual(evidence['exact_equal'],lost==0)

    def test_substantial_loss_or_any_added_triangles_fail(self):
        self.assertTrue(validator.triangle_count_evidence(5000000,4999900)['passed'])
        self.assertFalse(validator.triangle_count_evidence(5000000,4999899)['passed'])
        self.assertFalse(validator.triangle_count_evidence(5000000,5000001)['passed'])
        self.assertFalse(validator.triangle_count_evidence(0,0)['passed'])


if __name__=='__main__':unittest.main()

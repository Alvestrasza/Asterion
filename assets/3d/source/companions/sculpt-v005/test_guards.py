"""Pure scope regression tests; no Blender files or delivered bytes are written."""
import copy
import unittest
import guards


class FaceScope(unittest.TestCase):
    def setUp(self):
        self.before = dict(
            geometry={'head':'old-head','eye.L':'old-eye','nose':'old-nose','body':'old-body','ear.L':'old-ear'},
            materials={'skin':'original-skin','eye':'original-eye'},
            bindings={'head':['skin'],'eye.L':['eye'],'nose':['skin'],'body':['skin'],'ear.L':['skin']},
            roles={name:dict(part='head' if name!='body' else 'body', component='body', type='MESH')
                   for name in ('head','eye.L','nose','body','ear.L')},
            pivots={'lid.L':[.3,-.2,2.5],'lid.R':[-.3,-.2,2.5]})
        self.after = copy.deepcopy(self.before)
        for name in ('head','eye.L','nose'): self.after['geometry'][name]='new-'+name
        self.changes = dict(face_objects=['head','eye.L','nose'], removed_face_objects=[],
            edited_objects=[dict(name=n,max_displacement=.01) for n in ('head','eye.L','nose')])

    def result(self): return guards.scope(self.before,self.after,self.changes)

    def test_narrow_face_geometry_change_is_accepted(self):
        self.assertTrue(all(self.result()['checks'].values()))
        self.assertEqual(self.result()['protected_object_count'],2)

    def test_shared_body_shader_edit_is_rejected(self):
        self.after['materials']['skin']='changed-by-face'
        self.assertFalse(self.result()['checks']['nonface_materials_unchanged'])

    def test_unrelated_body_vertex_edit_is_rejected(self):
        self.after['geometry']['body']='one-vertex-changed'
        self.assertFalse(self.result()['checks']['nonface_geometry_unchanged'])

    def test_ear_cannot_be_added_to_face_allowlist(self):
        self.changes['face_objects'].append('ear.L')
        self.assertFalse(self.result()['checks']['explicit_face_only_allowlist'])

    def test_broad_allowlist_cannot_authorize_body_changes(self):
        self.changes['face_objects'].append('body')
        self.assertFalse(self.result()['checks']['explicit_face_only_allowlist'])

    def test_deleted_body_is_rejected(self):
        self.after['geometry'].pop('body')
        self.assertFalse(self.result()['checks']['all_unedited_source_objects_retained'])

    def test_lid_pivot_change_is_rejected(self):
        self.after['pivots']['lid.L'][0]+=.01
        self.assertFalse(self.result()['checks']['original_lid_pivots_unchanged'])

    def test_unreported_new_object_is_rejected(self):
        self.after['geometry']['prop']='new-object'
        self.assertFalse(self.result()['checks']['all_unedited_source_objects_retained'])

    def test_cosmetic_only_report_does_not_prove_shape_change(self):
        for item in self.changes['edited_objects']: item['max_displacement']=0
        self.assertFalse(self.result()['checks']['meaningful_face_geometry_refinement'])

    def test_head_attached_equipment_is_not_facial_skin(self):
        self.after['roles']['nose']['component']='armor'
        self.assertFalse(self.result()['checks']['explicit_face_only_allowlist'])

    def test_horn_hair_and_ear_aliases_remain_out_of_scope(self):
        role=dict(part='head',component='body',type='MESH')
        for name in ('AST_head_horn','AST_face_hair','AST_Dragon_Leaf_Ear_L','AST_forehead_lance_1'):
            self.assertFalse(guards.face_name(name,role),name)


if __name__=='__main__': unittest.main()

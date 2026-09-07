"""Public-safe fixed paths and acceptance boundaries for the face-only round."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
KINDS = ('asterion', 'pony', 'rabbit', 'cat', 'dog', 'orc', 'fairy', 'elf')
NAMES = dict(zip(KINDS, ('Asterion', 'Caelo', 'Liora', 'Nyra', 'Fenn', 'Brumo', 'Selya', 'Aelira')))
CLIPS = {'idle', 'blink', 'happy', 'eat', 'play', 'pet_reaction', 'sleep', 'wake', 'walk'}
FACE_VIEWS = {'face-hero', 'face-front', 'face-side', 'blink-early', 'blink-partial', 'blink-closed'}
SOURCE_VIEWS = FACE_VIEWS | {'hero', 'rear', 'body-hero'}
IMPORT_VIEWS = FACE_VIEWS | {'hero', 'body-hero'}
BASELINE_VIEWS = {'face-hero', 'face-front', 'face-side'}


def revision(kind):
    return 'sculpt-v006' if kind == 'asterion' else 'sculpt-v005'


def baseline(kind):
    return 'sculpt-v005' if kind == 'asterion' else 'sculpt-v004'


def reference(kind):
    return ('assets/3d/reference/asterion/sculpt-v004/asterion-approved-turnaround.png'
            if kind == 'asterion' else f'public/assets/companions/{kind}.png')


def module_path(kind):
    if kind == 'asterion':
        return REPO/'assets/3d/source/asterion/sculpt-v006/face.py'
    name = ('equine_lapine' if kind in ('pony', 'rabbit') else
            'feline_canine' if kind in ('cat', 'dog') else 'folk')
    return ROOT/(name+'_faces.py')


def input_paths(kind):
    version = baseline(kind)
    fixed = [f'assets/3d/source/{kind}/{version}/{kind}-{version}.blend',
        f'public/assets/3d/{kind}/{kind}-{version}.glb', reference(kind),
        'assets/3d/source/companions/sculpt-v001/common.py',
        'assets/3d/source/asterion/sculpt-v001/build_sculpt.py',
        'assets/3d/source/asterion/sculpt-v001/rig_delivery.py',
        'assets/3d/source/asterion/sculpt-v002/validate_refinement.py',
        'assets/3d/source/asterion/sculpt-v003/build_head_study.py',
        'assets/3d/source/asterion/sculpt-v004/export_equipment.py',
        'assets/3d/source/companions/sculpt-v004/build.py',
        'assets/3d/source/companions/sculpt-v004/refinements.py',
        'assets/3d/source/companions/sculpt-v004/export_equipment.py']
    if kind in ('cat', 'dog'):
        fixed.append('assets/3d/source/cat/sculpt-v002/nyra_detail.py')
    return [REPO/p for p in fixed] + [ROOT/p for p in ('build.py', 'contract.py', 'guards.py')] + [module_path(kind)]


SCOPE_CHECKS = {'explicit_face_only_allowlist', 'nonface_geometry_unchanged',
    'nonface_materials_unchanged', 'all_unedited_source_objects_retained',
    'original_lid_pivots_unchanged', 'face_geometry_survives_source_reopen',
    'all_protected_geometry_survives_source_reopen', 'all_protected_materials_survive_source_reopen',
    'meaningful_face_geometry_refinement', 'six_facial_views_present', 'finite_evaluated_partial_blinks'}

CHECKS = SCOPE_CHECKS | {'original_rest_rig_unchanged', 'original_constraints_drivers_unchanged',
    'all_original_action_data_unchanged', 'original_frame_rate_unchanged',
    'two_character_meshes', 'exact_distinct_components', 'one_original_shared_skin', 'nine_original_clips',
    'only_public_extras', 'skinned_triangle_primitives', 'under_40_primitives', 'within_species_triangle_budget',
    'self_contained_no_projection', 'no_editor_stage', 'meshopt', 'within_species_byte_budget',
    'finite_imported_geometry', 'valid_normalized_known_weights', 'bounded_importer_triangle_difference',
    'nine_clips_match_historical_import', 'two_imported_components', 'imported_equipment_metadata',
    'all_historical_and_builder_inputs_unchanged'}
HAIR_CHECKS = {'native_curves_present', 'at_least_1000_native_strands', 'native_points_radii_static_finite',
    'matching_native_export_groups', 'all_native_points_match_export_tube_rings'}

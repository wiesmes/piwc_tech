"""Contract tests from P2's integration markdown; no AI weights required."""
import unittest
from rules.p2_adapter import process_recognition


def one(**changes):
    d = {'item': 'plastic water bottle', 'material': 'plastic',
         'needs_clarification': False, 'question': None,
         'confidence': 0.9742}
    d.update(changes)
    return d


def detected(object_id, item, material, **changes):
    d = dict(one(item=item, material=material), object_id=object_id,
             detector_label=item, fusion_status='material_agreement',
             material_agreement=True)
    d.update(changes)
    return d


class P2AdapterTests(unittest.TestCase):
    def test_single_pa_statewide_not_assigned_a_bin(self):
        out = process_recognition(one())
        self.assertEqual(out['bin'], 'UNKNOWN')
        self.assertEqual(out['object_count'], 1)
        self.assertEqual(out['objects'][0]['rule_id'], 'PA-RECY-002')
        self.assertIsNotNone(out['objects'][0]['source_url'])
        self.assertEqual(out['objects'][0]['rule_checked_date'], '2026-11-14')

    def test_single_empty_question_preserved(self):
        out = process_recognition(one(needs_clarification=True,
                                      question='Is the bottle empty?'))
        self.assertEqual(out['bin'], 'UNKNOWN')
        self.assertEqual(out['objects'][0]['question'], 'Is the bottle empty?')
        self.assertIsNone(out['objects'][0]['rule_id'])

    def test_unknown_material_blocks_even_when_p2_not_clarifying(self):
        out = process_recognition(one(material='unknown'))
        self.assertEqual(out['bin'], 'UNKNOWN')
        self.assertIn('material', out['message'].lower())

    def test_extra_diagnostics_are_tolerated(self):
        out = process_recognition(one(inference_time_seconds=0.5, suggest_item='soda'))
        self.assertEqual(out['objects'][0]['item'], 'plastic water bottle')

    def test_single_disagreement_blocks(self):
        out = process_recognition(one(prediction_agreement=False))
        self.assertEqual(out['bin'], 'UNKNOWN')
        self.assertIn('disagree', out['message'])

    def test_multi_p2_example_separates_objects(self):
        payload = {'object_count': 2, 'multiple_items': True,
                   'objects': [detected(1, 'plastic snack wrapper', 'unknown',
                                        clip_material='organic', material_agreement=False,
                                        fusion_status='model_disagreement',
                                        needs_clarification=True,
                                        question='Please confirm its material.'),
                               detected(2, 'metal food can', 'organic',
                                        detector_label='leftover salad',
                                        needs_clarification=True,
                                        question='Please reposition or identify the item.')],
                   'needs_clarification': True}
        out = process_recognition(payload)
        self.assertEqual(out['object_count'], 2)
        self.assertEqual(out['bin'], 'UNKNOWN')
        self.assertEqual([x['object_id'] for x in out['objects']], [1, 2])
        self.assertTrue(all(x['bin'] == 'UNKNOWN' for x in out['objects']))
        self.assertIn('reposition', out['objects'][1]['question'])

    def test_multi_correct_detection_one_stays_statewide_unknown(self):
        out = process_recognition({'object_count': 1, 'objects': [
            detected(3, 'aluminum can', 'metal')]})
        self.assertEqual(out['objects'][0]['rule_id'], 'PA-RECY-001')
        self.assertEqual(out['bin'], 'UNKNOWN')

    def test_demo_single_no_confirmation_unknown(self):
        out = process_recognition(one(item='practice can', material='metal'),
                                  location='DEMO_ONLY', demo_mode=True)
        self.assertEqual(out['bin'], 'UNKNOWN')
        self.assertIn('empty', out['message'].lower())

    def test_demo_single_with_confirmation_recycle(self):
        out = process_recognition(one(item='practice can', material='metal'),
                                  attributes={'empty': True},
                                  location='DEMO_ONLY', demo_mode=True)
        self.assertEqual(out['bin'], 'RECYCLE')
        self.assertIn('DEMO ONLY', out['message'])
        self.assertIsNone(out['objects'][0]['rule_checked_date'])

    def test_demo_multi_never_issue_one_aggregate_command(self):
        out = process_recognition({'object_count': 2, 'objects': [
            detected(1, 'practice wrapper', 'plastic'),
            detected(2, 'practice banana peel', 'organic')]},
            location='DEMO_ONLY', demo_mode=True)
        self.assertEqual(out['bin'], 'UNKNOWN')
        self.assertEqual([x['bin'] for x in out['objects']],
                         ['LANDFILL', 'COMPOST'])

    def test_invalid_ids_fail_closed(self):
        for ids in ([1, 1], [None, 2], ['1', 2]):
            with self.subTest(ids=ids):
                data = {'object_count': 2, 'objects': [
                    detected(ids[0], 'practice wrapper', 'plastic'),
                    detected(ids[1], 'practice banana peel', 'organic')]}
                self.assertEqual(process_recognition(data)['bin'], 'UNKNOWN')
                self.assertEqual(process_recognition(data)['objects'], [])

    def test_count_mismatch_fail_closed(self):
        out = process_recognition({'object_count': 9, 'objects': [
            detected(1, 'practice wrapper', 'plastic')]})
        self.assertEqual(out['objects'], [])

    def test_no_objects(self):
        out = process_recognition({'object_count': 0, 'objects': []})
        self.assertEqual(out['bin'], 'UNKNOWN')
        self.assertIn('No waste item', out['message'])

    def test_multi_material_agreement_not_identity_agreement(self):
        out = process_recognition({'object_count': 1, 'objects': [
            detected(1, 'metal food can', 'organic', detector_label='leftover salad')]})
        self.assertEqual(out['objects'][0]['bin'], 'UNKNOWN')
        self.assertIn('item', out['objects'][0]['message'])

    def test_p2_equivalent_salad_labels_respect_true_item_agreement(self):
        obj = detected(1, 'leftover food scraps', 'organic',
                       detector_label='leftover salad', item_agreement=True)
        out = process_recognition({'object_count': 1, 'objects': [obj]})
        self.assertEqual(out['bin'], 'UNKNOWN')  # PA has no universal collection bin
        self.assertNotIn('disagree', out['objects'][0]['message'].lower())
        self.assertEqual(out['objects'][0]['item'], 'leftover food scraps')

    def test_p2_equivalent_paper_labels_reach_state_guidance(self):
        obj = detected(1, 'office paper', 'paper',
                       detector_label='sheet of paper', item_agreement=True)
        out = process_recognition({'object_count': 1, 'objects': [obj]})
        self.assertEqual(out['bin'], 'UNKNOWN')  # No verified local program
        self.assertEqual(out['objects'][0]['rule_id'], 'PA-RECY-005')
        self.assertIsNotNone(out['objects'][0]['source_url'])

    def test_p2_positive_agreement_can_reach_demo_rule(self):
        obj = detected(1, 'practice wrapper', 'plastic',
                       detector_label='used wrapper', item_agreement=True)
        out = process_recognition({'object_count': 1, 'objects': [obj]},
                                  location='DEMO_ONLY', demo_mode=True)
        self.assertEqual(out['bin'], 'LANDFILL')
        self.assertIn('DEMO ONLY', out['message'])

    def test_item_agreement_false_blocks_even_when_labels_match(self):
        obj = detected(1, 'practice wrapper', 'plastic', item_agreement=False)
        out = process_recognition({'object_count': 1, 'objects': [obj]},
                                  location='DEMO_ONLY', demo_mode=True)
        self.assertEqual(out['bin'], 'UNKNOWN')
        self.assertIn('disagree', out['message'].lower())

    def test_item_agreement_false_blocks_single_object(self):
        out = process_recognition(one(item_agreement=False))
        self.assertEqual(out['bin'], 'UNKNOWN')
        self.assertIn('disagree', out['message'].lower())

    def test_legacy_matching_labels_still_pass(self):
        obj = detected(1, 'practice wrapper', 'plastic',
                       detector_label='  PRACTICE   WRAPPER  ')
        out = process_recognition({'object_count': 1, 'objects': [obj]},
                                  location='DEMO_ONLY', demo_mode=True)
        self.assertEqual(out['bin'], 'LANDFILL')

    def test_legacy_mismatched_labels_still_block(self):
        obj = detected(1, 'practice wrapper', 'plastic',
                       detector_label='different label')
        out = process_recognition({'object_count': 1, 'objects': [obj]},
                                  location='DEMO_ONLY', demo_mode=True)
        self.assertEqual(out['bin'], 'UNKNOWN')
        self.assertIn('disagree', out['message'].lower())

    def test_invalid_item_agreement_values_fail_closed(self):
        for flag in (None, 'true', 1, 0, [], {}):
            with self.subTest(flag=flag):
                obj = detected(1, 'practice wrapper', 'plastic', item_agreement=flag)
                out = process_recognition({'object_count': 1, 'objects': [obj]},
                                          location='DEMO_ONLY', demo_mode=True)
                self.assertEqual(out['bin'], 'UNKNOWN')
                self.assertIn('invalid', out['message'].lower())

    def test_true_item_agreement_does_not_bypass_safety_checks(self):
        baseline = dict(item_agreement=True, detector_label='used wrapper')
        checks = [
            {'material_agreement': False},
            {'prediction_agreement': False},
            {'fusion_status': 'model_disagreement'},
            {'fusion_status': 'unverified'},
            {'fusion_status': None},
            {'material': 'unknown'},
            {'needs_clarification': True, 'question': 'What item is this?'},
        ]
        for extra in checks:
            with self.subTest(extra=extra):
                obj = detected(1, 'practice wrapper', 'plastic', **baseline)
                obj.update(extra)
                out = process_recognition({'object_count': 1, 'objects': [obj]},
                                          location='DEMO_ONLY', demo_mode=True)
                self.assertEqual(out['bin'], 'UNKNOWN')
                self.assertNotIn('DEMO ONLY', out['message'])

    def test_multi_item_agreement_is_independent_per_object(self):
        objects = [
            detected(1, 'practice wrapper', 'plastic',
                     detector_label='different wrapper', item_agreement=True),
            detected(2, 'practice banana peel', 'organic', item_agreement=False),
        ]
        out = process_recognition({'object_count': 2, 'objects': objects},
                                  location='DEMO_ONLY', demo_mode=True)
        self.assertEqual(out['bin'], 'UNKNOWN')
        self.assertEqual([x['bin'] for x in out['objects']], ['LANDFILL', 'UNKNOWN'])

    def test_explicit_condition_confirmation_only(self):
        rec = one(item='practice can', material='metal',
                  needs_clarification=True, question='Is the can empty?',
                  clarification_type='condition', required_attributes=['empty'])
        out = process_recognition(rec, location='DEMO_ONLY', demo_mode=True,
                                  attributes={'empty': True})
        self.assertEqual(out['bin'], 'RECYCLE')
        not_confirmed = process_recognition(rec, location='DEMO_ONLY', demo_mode=True,
                                            attributes={'empty': 'yes'})
        self.assertEqual(not_confirmed['bin'], 'UNKNOWN')

    def test_unstructured_question_not_overridden_by_attribute(self):
        rec = one(item='practice can', material='metal',
                  needs_clarification=True, question='Is the can empty?')
        out = process_recognition(rec, location='DEMO_ONLY', demo_mode=True,
                                  attributes={'empty': True})
        self.assertEqual(out['bin'], 'UNKNOWN')

    def test_multi_attributes_stay_per_object(self):
        rec = {'object_count': 2, 'objects': [
            detected(1, 'practice can', 'metal', needs_clarification=True,
                     question='Is the can empty?', clarification_type='condition',
                     required_attributes=['empty']),
            detected(2, 'practice wrapper', 'plastic')]}
        out = process_recognition(rec, location='DEMO_ONLY', demo_mode=True,
                                  attributes_by_object={1: {'empty': True}})
        self.assertEqual(out['objects'][0]['bin'], 'RECYCLE')
        self.assertEqual(out['objects'][1]['bin'], 'LANDFILL')
        self.assertEqual(out['bin'], 'UNKNOWN')


class ActualCameraDemoIntegrationTests(unittest.TestCase):
    """P2 camera labels remain DEMO ONLY, never state-approved sorting rules."""

    def test_actual_bottle_requires_empty_confirmation(self):
        obj = one(item='plastic water bottle', material='plastic',
                  needs_clarification=True, question='Is the bottle empty?',
                  clarification_type='condition', required_attributes=['empty'])
        no_answer = process_recognition(obj, location='DEMO_ONLY', demo_mode=True)
        self.assertEqual(no_answer['bin'], 'UNKNOWN')
        self.assertIn('empty', no_answer['message'].lower())
        confirmed = process_recognition(obj, location='DEMO_ONLY', demo_mode=True,
                                        attributes={'empty': True})
        self.assertEqual(confirmed['bin'], 'RECYCLE')
        self.assertIn('DEMO ONLY', confirmed['message'])
        self.assertIsNone(confirmed['objects'][0]['source_url'])
        self.assertIsNone(confirmed['objects'][0]['rule_checked_date'])

    def test_actual_bottle_false_or_non_boolean_never_recycles(self):
        obj = one(item='plastic water bottle', material='plastic',
                  needs_clarification=True, question='Is the bottle empty?',
                  clarification_type='condition', required_attributes=['empty'])
        for attrs in ({'empty': False}, {'empty': 'yes'}, {}, None):
            with self.subTest(attributes=attrs):
                result = process_recognition(obj, location='DEMO_ONLY', demo_mode=True,
                                             attributes=attrs)
                self.assertEqual(result['bin'], 'UNKNOWN')

    def test_bottle_recognition_uncertainty_not_overridden_by_empty_true(self):
        obj = one(item='plastic water bottle', material='plastic',
                  needs_clarification=True,
                  clarification_type='recognition',
                  question='Which bottle is this?')
        result = process_recognition(obj, location='DEMO_ONLY', demo_mode=True,
                                     attributes={'empty': True})
        self.assertEqual(result['bin'], 'UNKNOWN')

    def test_actual_food_scraps_compost_only_in_demo(self):
        result = process_recognition(one(item='leftover food scraps', material='organic'),
                                     location='DEMO_ONLY', demo_mode=True)
        self.assertEqual(result['bin'], 'COMPOST')
        self.assertIn('DEMO ONLY', result['message'])
        self.assertIsNone(result['objects'][0]['source_url'])

    def test_actual_paper_napkin_landfill_only_in_demo(self):
        result = process_recognition(one(item='paper napkin', material='paper'),
                                     location='DEMO_ONLY', demo_mode=True)
        self.assertEqual(result['bin'], 'LANDFILL')
        self.assertIn('DEMO ONLY', result['message'])

    def test_real_pa_mode_cannot_use_any_camera_demo_rules(self):
        examples = [('plastic water bottle', 'plastic'),
                    ('leftover food scraps', 'organic'),
                    ('paper napkin', 'paper')]
        for item, material in examples:
            with self.subTest(item=item):
                rec = one(item=item, material=material)
                self.assertEqual(process_recognition(rec)['bin'], 'UNKNOWN')
                self.assertEqual(process_recognition(rec, demo_mode=True)['bin'], 'UNKNOWN')
                self.assertEqual(process_recognition(rec, location='DEMO_ONLY',
                                                     demo_mode=False)['bin'], 'UNKNOWN')

    def test_multi_equivalent_labels_use_p2_explicit_item_agreement(self):
        objs = [
            detected(1, 'leftover food scraps', 'organic',
                     detector_label='leftover salad', item_agreement=True),
            detected(2, 'paper napkin', 'paper',
                     detector_label='paper napkin', item_agreement=True),
        ]
        result = process_recognition({'object_count': 2, 'objects': objs},
                                     location='DEMO_ONLY', demo_mode=True)
        self.assertEqual(result['bin'], 'UNKNOWN')  # Never send aggregate bin to Pico
        self.assertEqual([r['bin'] for r in result['objects']], ['COMPOST', 'LANDFILL'])
        self.assertEqual([r['object_id'] for r in result['objects']], [1, 2])

    def test_real_camera_three_leds_are_independent(self):
        objs = [
            detected(1, 'plastic water bottle', 'plastic', item_agreement=True,
                     needs_clarification=True, question='Is the bottle empty?',
                     clarification_type='condition', required_attributes=['empty']),
            detected(2, 'leftover food scraps', 'organic',
                     detector_label='leftover salad', item_agreement=True),
            detected(3, 'paper napkin', 'paper', item_agreement=True),
        ]
        result = process_recognition({'object_count': 3, 'objects': objs},
                                     location='DEMO_ONLY', demo_mode=True,
                                     attributes_by_object={1: {'empty': True}})
        self.assertEqual(result['bin'], 'UNKNOWN')
        self.assertEqual([r['bin'] for r in result['objects']],
                         ['RECYCLE', 'COMPOST', 'LANDFILL'])
        self.assertTrue(all('DEMO ONLY' in r['message'] for r in result['objects']))
        without_answer = process_recognition({'object_count': 3, 'objects': objs},
                                             location='DEMO_ONLY', demo_mode=True)
        self.assertEqual([r['bin'] for r in without_answer['objects']],
                         ['UNKNOWN', 'COMPOST', 'LANDFILL'])

    def test_disagreements_override_all_new_camera_demo_mappings(self):
        objs = [
            detected(1, 'leftover food scraps', 'organic',
                     detector_label='leftover salad', item_agreement=False),
            detected(2, 'paper napkin', 'paper', item_agreement=True,
                     material_agreement=False),
            detected(3, 'plastic water bottle', 'unknown', item_agreement=True),
        ]
        result = process_recognition({'object_count': 3, 'objects': objs},
                                     location='DEMO_ONLY', demo_mode=True,
                                     attributes_by_object={3: {'empty': True}})
        self.assertEqual([r['bin'] for r in result['objects']],
                         ['UNKNOWN', 'UNKNOWN', 'UNKNOWN'])

    def test_legacy_nonidentical_labels_still_fail_closed_in_demo(self):
        obj = detected(1, 'leftover food scraps', 'organic',
                       detector_label='leftover salad')
        result = process_recognition({'object_count': 1, 'objects': [obj]},
                                     location='DEMO_ONLY', demo_mode=True)
        self.assertEqual(result['bin'], 'UNKNOWN')
        self.assertIn('disagree', result['message'].lower())


if __name__ == '__main__':
    unittest.main()

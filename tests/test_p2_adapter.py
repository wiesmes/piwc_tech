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


if __name__ == '__main__':
    unittest.main()

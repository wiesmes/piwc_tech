"""Deterministic offline tests. Synthetic local program fixtures are NOT PA policy."""
import json
from pathlib import Path
import tempfile
import unittest

from rules.engine import decide


def rec(item='aluminum can', clarify=False):
    return {'item': item, 'material': 'unknown',
            'needs_clarification': clarify,
            'question': 'Read packaging.' if clarify else None}


class PennsylvaniaP4Tests(unittest.TestCase):
    def test_state_default_is_pa(self):
        r = decide(rec())
        self.assertEqual(r['bin'], 'UNKNOWN')
        self.assertIn('local', r['message'].lower())

    def test_aluminum_can_has_state_source_but_not_bin(self):
        r = decide(rec('soda can'))
        self.assertEqual(r['bin'], 'UNKNOWN')
        self.assertTrue(r['source_url'].startswith('https://www.pa.gov/'))
        self.assertEqual(r['rule_id'], 'PA-RECY-001')

    def test_compostable_fork_not_automatically_compost(self):
        r = decide(rec('compostable fork'))
        self.assertEqual(r['bin'], 'UNKNOWN')
        self.assertIn('collection', r['message'].lower())

    def test_battery_requires_special_handling(self):
        r = decide(rec('lithium-ion battery'))
        self.assertEqual(r['bin'], 'UNKNOWN')
        self.assertIn('fire', r['message'].lower())

    def test_laptop_requires_special_handling(self):
        self.assertEqual(decide(rec('laptop'))['rule_id'], 'PA-EWASTE-001')

    def test_unlisted_item_unknown(self):
        r = decide(rec('banana leaf bowl'))
        self.assertEqual(r['bin'], 'UNKNOWN')
        self.assertIsNone(r['rule_id'])

    def test_uncertain_vision_asks_question(self):
        r = decide(rec(clarify=True))
        self.assertEqual(r['bin'], 'UNKNOWN')
        self.assertEqual(r['message'], 'Read packaging.')

    def test_no_item_unknown(self):
        self.assertEqual(decide(rec(''))['bin'], 'UNKNOWN')

    def test_wrong_region_rejected(self):
        self.assertEqual(decide(rec(), location='UNCONFIGURED')['bin'], 'UNKNOWN')

    def test_no_real_program_does_not_choose_bin(self):
        self.assertEqual(decide(rec(), program_id='KNOWN_PROGRAM')['bin'], 'UNKNOWN')

    def test_demo_off_by_default(self):
        self.assertEqual(decide(rec('practice can'), location='DEMO_ONLY')['bin'], 'UNKNOWN')

    def test_demo_can_with_confirmation(self):
        r = decide(rec('practice can'), location='DEMO_ONLY',
                   demo_mode=True, attributes={'empty': True})
        self.assertEqual(r['bin'], 'RECYCLE')
        self.assertTrue(r['message'].startswith('DEMO ONLY'))
        self.assertIsNone(r['source_url'])

    def test_demo_needs_condition(self):
        r = decide(rec('practice can'), location='DEMO_ONLY', demo_mode=True)
        self.assertEqual(r['bin'], 'UNKNOWN')
        self.assertIn('empty', r['message'])

    def test_demo_compost(self):
        self.assertEqual(decide(rec('practice banana peel'), location='DEMO_ONLY',
                                demo_mode=True)['bin'], 'COMPOST')

    def test_demo_landfill(self):
        self.assertEqual(decide(rec('practice wrapper'), location='DEMO_ONLY',
                                demo_mode=True)['bin'], 'LANDFILL')

    def test_cannot_mix_demo_and_pa(self):
        self.assertEqual(decide(rec('practice wrapper'), demo_mode=True)['bin'], 'UNKNOWN')

    def synthetic_profile(self, **changes):
        """https://example.org is deliberately TEST DATA, never a real policy source."""
        rule = {'rule_id': 'SYNTHETIC-001', 'status': 'verified', 'item': 'aluminum can',
                'aliases': ['soda can'], 'bin': 'RECYCLE',
                'verified_on': '2026-11-01',
                'source_url': 'https://example.org/synthetic-local-ordinance',
                'requires': {'empty': True},
                'question_when_missing': 'Is the can empty?',
                'message': 'Synthetic example recycling rule.'}
        profile = {'location_id': 'PA_STATEWIDE', 'demo_only': False,
                   'program_id': 'SYNTHETIC_TEST_ONLY', 'program_verified': True,
                   'program_source_url': 'https://example.org/synthetic-program',
                   'program_verified_on': '2026-11-01',
                   'available_bins': ['RECYCLE', 'LANDFILL'],
                   'compost_stream_confirmed': False, 'rules': [rule]}
        profile.update(changes)
        return profile

    def run_with_profile(self, profile, *, item='aluminum can', attributes=None,
                         program_id='SYNTHETIC_TEST_ONLY'):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / 'local.json'
            f.write_text(json.dumps(profile), encoding='utf-8')
            return decide(rec(item), rules_path=f,
                          location='PA_STATEWIDE', program_id=program_id,
                          attributes=attributes)

    def test_profile_without_user_confirmation_unknown(self):
        r = self.run_with_profile(self.synthetic_profile())
        self.assertEqual(r['bin'], 'UNKNOWN')
        self.assertIn('empty', r['message'])

    def test_profile_with_user_confirmation_can_choose_bin(self):
        r = self.run_with_profile(self.synthetic_profile(), attributes={'empty': True})
        self.assertEqual(r['bin'], 'RECYCLE')
        self.assertEqual(r['rule_id'], 'SYNTHETIC-001')

    def test_false_condition_abstains(self):
        r = self.run_with_profile(self.synthetic_profile(), attributes={'empty': False})
        self.assertEqual(r['bin'], 'UNKNOWN')

    def test_program_identity_mismatch(self):
        r = self.run_with_profile(self.synthetic_profile(),
                                  attributes={'empty': True}, program_id='WRONG')
        self.assertEqual(r['bin'], 'UNKNOWN')

    def test_program_not_verified(self):
        r = self.run_with_profile(self.synthetic_profile(program_verified=False), attributes={'empty': True})
        self.assertEqual(r['bin'], 'UNKNOWN')

    def test_no_required_collection_stream(self):
        r = self.run_with_profile(self.synthetic_profile(available_bins=['LANDFILL']), attributes={'empty': True})
        self.assertEqual(r['bin'], 'UNKNOWN')

    def test_duplicate_rules_abstain(self):
        p = self.synthetic_profile()
        p['rules'].append(dict(p['rules'][0], rule_id='SYNTHETIC-002', bin='LANDFILL'))
        r = self.run_with_profile(p, attributes={'empty': True})
        self.assertEqual(r['bin'], 'UNKNOWN')

    def test_laptop_cannot_be_forced_into_local_landfill(self):
        p = self.synthetic_profile()
        p['rules'][0].update(item='laptop', bin='LANDFILL', requires={})
        r = self.run_with_profile(p, item='laptop')
        self.assertEqual(r['bin'], 'UNKNOWN')
        self.assertEqual(r['rule_id'], 'PA-EWASTE-001')

    def test_local_compost_requires_active_stream(self):
        p = self.synthetic_profile(available_bins=['COMPOST', 'RECYCLE', 'LANDFILL'])
        p['rules'][0].update(bin='COMPOST')
        r = self.run_with_profile(p, attributes={'empty': True})
        self.assertEqual(r['bin'], 'UNKNOWN')

    def test_invalid_source_url_abstains(self):
        p = self.synthetic_profile()
        p['rules'][0]['source_url'] = 'http://not-secure.invalid/source'
        r = self.run_with_profile(p, attributes={'empty': True})
        self.assertEqual(r['bin'], 'UNKNOWN')


if __name__ == '__main__':
    unittest.main()

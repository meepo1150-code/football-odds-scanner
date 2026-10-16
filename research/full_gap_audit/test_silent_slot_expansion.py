"""Offline safety regression tests for silent slot triage."""
import unittest
from research.full_gap_audit.silent_slot_expansion import expand

class SilentSlotExpansionTests(unittest.TestCase):
    def test_fixed_cohort_not_inferred_from_other_round(self):
        rows=[
            dict(fixture_id='A',football_day='2026-10-15',policy_version='FIXED_1500',membership='EXACT_ATTEMPT_OR_DEPLOYED_COHORT',expected=True,status='COMPLETE'),
            dict(fixture_id='A',football_day='2026-10-15',policy_version='FIXED_1500',membership='UNKNOWN_EXPECTED_MEMBERSHIP',expected=None,status='UNKNOWN_EVIDENCE')]
        summary,new=expand(rows)
        self.assertEqual(summary['newly_proven_missing'],0)
        self.assertEqual(summary['reasons']['needs_explicit_cohort_proof'],1)
        self.assertEqual(summary['unknown_by_football_day']['2026-10-15'],1)
        self.assertEqual(new,[])

    def test_legacy_unknown_not_promoted(self):
        summary,new=expand([dict(fixture_id='B',football_day='2026-09-25',policy_version='LEGACY',expected=None,status='UNKNOWN_EVIDENCE')])
        self.assertEqual(summary['reasons']['unsupported_policy'],1)
        self.assertEqual(summary['newly_proven_expected'],0)
        self.assertEqual(new,[])

    def test_known_expected_untouched(self):
        summary,new=expand([dict(fixture_id='C',football_day='2026-10-15',policy_version='FIXED_1500',expected=True,status='SCAN_FAILED')])
        self.assertEqual(summary['reviewed_unknown'],0)
        self.assertEqual(new,[])

if __name__=='__main__':
    unittest.main()

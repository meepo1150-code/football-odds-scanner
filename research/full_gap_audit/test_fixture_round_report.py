"""Offline regression tests for fixture-by-round CSV aggregation."""
import unittest
from research.full_gap_audit.fixture_round_report import summarize

def slot(status,expected,clock):
    return dict(fixture_id='id42',football_day='2026-10-15',home='Home',away='Away',league='League',
                slot_utc='2026-10-15T'+clock+':00+00:00',
                slot_bangkok='2026-10-15T'+clock+':00+07:00',
                status=status,expected=expected,kickoff_utc='2026-10-15T22:00:00+00:00')

class FixtureRoundReportTests(unittest.TestCase):
    def test_known_slots_and_unknown_membership_are_separate(self):
        rows=[slot('COMPLETE',True,'08:00'),slot('SCAN_FAILED',True,'11:00'),
              slot('UNKNOWN_EVIDENCE',None,'14:00')]
        result=summarize(rows)
        self.assertEqual(len(result),1)
        x=result[0]
        self.assertEqual(x['expected_proven'],2)
        self.assertEqual(x['expected_elapsed_pre_kickoff'],2)
        self.assertEqual(x['complete'],1)
        self.assertEqual(x['scan_failed'],1)
        self.assertEqual(x['unknown_membership'],1)
        self.assertEqual(len(__import__('json').loads(x['round_status_detail'])),3)
        self.assertEqual(x['observed_ah_quote_records'],0)
        self.assertIn('11:00',x['candidate_deficit_slots'])
        self.assertIn('14:00',x['needs_evidence_slots'])

    def test_different_days_are_distinct(self):
        a=slot('COMPLETE',True,'08:00')
        b=slot('NO_PRICE',True,'08:00')
        b['football_day']='2026-10-16'
        self.assertEqual(len(summarize([a,b])),2)

    def test_after_kickoff_is_not_elapsed_expected(self):
        a=slot('COMPLETE',True,'08:00')
        a['kickoff_utc']='2026-10-15T07:00:00+00:00'
        x=summarize([a])[0]
        self.assertEqual(x['expected_proven'],1)
        self.assertEqual(x['expected_elapsed_pre_kickoff'],0)

    def test_unmatched_not_assumed_recoverable(self):
        x=summarize([slot('UNMATCHED',True,'08:00')])[0]
        self.assertEqual(x['unmatched'],1)
        self.assertEqual(x['candidate_deficit_slots'],'')
        self.assertIn('08:00',x['needs_evidence_slots'])

if __name__=='__main__':
    unittest.main()

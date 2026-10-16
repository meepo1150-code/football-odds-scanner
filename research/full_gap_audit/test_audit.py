import json
import gzip
from pathlib import Path
import tempfile
import unittest
from research.full_gap_audit.audit import stamp,policy,scheduled,targets,valid,classify,save,parse,sha
from odds_scanner.asian_settlement import settle_asian_handicap

def read_result(p):
    return p.read_text() if p.exists() else gzip.decompress(Path(str(p)+'.gz').read_bytes()).decode()

class AuditTests(unittest.TestCase):
    def test_historical_policy_not_retroactive(self):
        self.assertIsNone(scheduled(stamp('2026-09-19T08:00:00Z')))
        self.assertTrue(scheduled(stamp('2026-10-03T13:00:00Z')))
        self.assertFalse(scheduled(stamp('2026-10-02T13:00:00Z')))
    def test_crossday_midnight_deployment(self):
        self.assertFalse(scheduled(stamp('2026-10-12T17:00:00Z')))
        self.assertTrue(scheduled(stamp('2026-10-13T17:00:00Z')))
        self.assertEqual(targets('2026-10-15')[-1],stamp('2026-10-15T17:00:00Z'))
    def test_fixed_cohort_deployment_not_backdated(self):
        self.assertNotEqual(policy(stamp('2026-10-14T11:00:00Z'))[1],'FIXED_1500')
        self.assertEqual(policy(stamp('2026-10-14T14:00:00Z'))[1],'FIXED_1500')
    def test_missing_unknown_no_price_failed_identity(self):
        t=stamp('2026-10-15T11:00:00Z');ko=stamp('2026-10-15T14:00:00Z');now=stamp('2026-10-16T01:52:42Z')
        self.assertEqual(classify(None,t,ko,now)[0],'UNKNOWN_EVIDENCE')
        for reason,status in [('KICKOFF_NOT_FUTURE','SCAN_FAILED'),('BOOKMAKER_NOT_ACTIVE','NO_PRICE'),('MASTER_CLUB_UNMAPPED','UNKNOWN_EVIDENCE'),('AMBIGUOUS_OR_MISSING_1X2','UNKNOWN_EVIDENCE'),('NOT_PREMATCH_WITH_ODDS','UNKNOWN_EVIDENCE'),('AH_OUTSIDE_CORE_PRICE','UNMATCHED'),('API_FAILURE','SCAN_FAILED'),('NO_FIXTURE_IN_PROVIDER_RESPONSE','MISSING_SLOT')]:
            with self.subTest(reason=reason):self.assertEqual(classify(True,t,ko,now,reasons=[reason])[0],status)
        self.assertEqual(classify(True,t,ko,now,conflict=True)[0],'UNMATCHED')
        self.assertEqual(classify(True,ko,ko,now)[0],'NOT_EXPECTED')
        self.assertEqual(classify(True,now,now,ko)[1],'FUTURE_NOT_DUE')
    def test_two_sided_ah_not_same_as_tradability(self):
        r=dict(observed_at='2026-10-15T11:00:00Z',kickoff='2026-10-15T14:00:00Z',ah=dict(home_line=-.75,away_line=.75,home_price=1.5,away_price=3.1))
        self.assertTrue(valid(r))
        for k,v in [('home_price',True),('home_price',float('nan')),('home_line',-.7),('away_line',-.75)]:
            with self.subTest(k=k,v=v):self.assertFalse(valid({**r,'ah':{**r['ah'],k:v}}))
        self.assertFalse(valid({**r,'provider':'propline'}))
    def test_historical_literal_newline_and_corruption(self):
        self.assertEqual(len(parse(b'{"a":1}\\n{"b":2}\n')),2)
        with self.assertRaises(ValueError):parse(b'{"a":1}garbage')
    def test_output_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'RESEARCH_OUTPUT_ONLY'):save(Path(tmp)/'x',{})
    def test_idempotency(self):
        p=Path(__file__).parent/'results/test-idempotency.json'
        save(p,{'immutable':True});save(p,{'immutable':True})
        with self.assertRaisesRegex(ValueError,'IMMUTABLE_CONFLICT'):save(p,{'immutable':False})
    def test_quarter_line_full_half_push_draw(self):
        for hg,ag,line,side,status in [(1,1,-.25,'H','HALF_LOSS'),(1,1,.25,'A','HALF_WIN'),(1,0,-.75,'H','HALF_WIN'),(1,0,.75,'A','HALF_LOSS'),(1,0,-1,'H','PUSH'),(2,0,-.75,'H','FULL_WIN'),(0,1,-.75,'H','FULL_LOSS')]:
            with self.subTest(line=line,side=side):self.assertEqual(settle_asian_handicap(hg,ag,line,2,side).settlement.value,status)
    def test_generated_manifest(self):
        root=Path(__file__).parent/'results/pinned-b6976e2f'
        gaps=[json.loads(l) for l in (root/'missing_slot_manifest.jsonl').read_text().splitlines()]
        self.assertEqual(len(gaps),len({g['deduplication_key'] for g in gaps}))
        for g in gaps:
            self.assertIs(g['expected'],True)
            self.assertLess(stamp(g['slot_utc']),stamp(g['kickoff_utc']))
            self.assertLessEqual(stamp(g['policy_deployed_at']),stamp(g['slot_utc']))
            self.assertTrue(g['attempt_evidence'] or g['observed_evidence'])
            self.assertEqual(g['fixture_id'],g['provider_fixture_id'])
            self.assertEqual(g['deduplication_key'],sha([g['fixture_id'],g['slot_utc'],'pinnacle','AH']))
            self.assertNotEqual(g['fixture_id'],'id1000000872478578')
    def test_generated_kickoff_changes_and_future(self):
        root=Path(__file__).parent/'results/pinned-b6976e2f'
        changed={json.loads(l)['provider_fixture_id'] for l in read_result(root/'fixture_inventory.jsonl').splitlines() if json.loads(l)['kickoff_changed']}
        for l in read_result(root/'expected_actual_matrix.jsonl').splitlines():
            r=json.loads(l)
            if r['fixture_id'] in changed:self.assertIsNot(r['expected'],True)
            if r['reason']=='FUTURE_NOT_DUE':self.assertEqual(r['status'],'NOT_EXPECTED')

if __name__=='__main__':unittest.main()

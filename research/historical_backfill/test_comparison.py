import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from research.historical_backfill.comparison import reconstruct_candidate,compare_observation
from research.historical_backfill import storage
from research.historical_backfill.test_reconstruct import BASE


class TestComparison(unittest.TestCase):
    def candidate(self):
        return dict(fixture_id=BASE['fixture_id'],bookmaker=BASE['bookmaker'],kickoff=BASE['kickoff'],
            missing_rounds=[BASE['slot']],existing_rounds=[],home='H',away='A',league='TEST',ft_status='FT_MISSING',ft_score=None)

    def market(self):
        return dict(fixture_id=BASE['fixture_id'],bookmaker=BASE['bookmaker'],source='offline-test',market_id='42',line=-0.75,
            selections=BASE['selections'],catalog_evidence='SYNTHETIC_TEST_ONLY')

    def test_closed_default(self):
        r=reconstruct_candidate(self.candidate(),[self.market()]);self.assertEqual(r[0]['status'],'ACTIVE_TIMESTAMP_SEMANTICS_UNVERIFIED')

    def test_metadata_and_missing_ft(self):
        r=reconstruct_candidate(self.candidate(),[self.market()],state_semantics_verified=True)[0]
        self.assertEqual(r['settlement_status'],'NOT_SETTLED');self.assertEqual(r['data_origin'],'BACKFILLED')
        self.assertEqual(set(r['actual_price_timestamp']),{'home','away'})

    def test_no_payload(self):
        r=reconstruct_candidate(self.candidate(),[],state_semantics_verified=True)
        self.assertEqual(r[0]['status'],'NO_HISTORICAL_DATA')

    def test_same_book_line_actual_time_comparison(self):
        obs=dict(fixture_id=BASE['fixture_id'],bookmaker=BASE['bookmaker'],observed_at=BASE['slot'],kickoff=BASE['kickoff'],ah=dict(home_line=-0.75,home_price=1.9,away_price=1.9))
        r=compare_observation(obs,[self.market()],state_semantics_verified=True)
        self.assertAlmostEqual(r['comparisons'][0]['home_delta'],0.05)
        self.assertIsNone(r['comparisons'][0]['observed_price_changed_at'])
        obs['bookmaker']='OTHER'
        self.assertEqual(compare_observation(obs,[self.market()],state_semantics_verified=True)['status'],'NO_SAME_BOOKMAKER_LINE')

    def test_exact_bytes_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'historical'
            with patch.object(storage,'ROOT',root):
                b=b'{ "x": 1 }\n';p=storage.append_bytes(b);self.assertEqual(p.read_bytes(),b)
                self.assertEqual(storage.append_bytes(b),p)

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'historical';root.mkdir();(root/'raw').symlink_to(Path(t),target_is_directory=True)
            with patch.object(storage,'ROOT',root):
                with self.assertRaises(ValueError):storage.append_bytes(b'{}')

if __name__=='__main__':unittest.main()

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import unittest
from research.ah_ft_join import settle, analyze

class AHFTTests(unittest.TestCase):
    def test_quarter_lines(self):
        self.assertEqual(settle(-.25,0),"HALF_LOSS")
        self.assertEqual(settle(.25,0),"HALF_WIN")
        self.assertEqual(settle(-.75,1),"HALF_WIN")
        self.assertEqual(settle(-1.25,1),"HALF_LOSS")
        self.assertEqual(settle(-1,1),"PUSH")
    def test_no_fabricated_side(self):
        f={"fixture_id":"x","observations":2,"observation_gap_minutes":60,"first_ah_line":-.5,"last_ah_line":-.75}
        r={"fixture_id":"x","ft_home_goals":2,"ft_away_goals":1,"result_source":"verified","result_identity":"exact"}
        self.assertEqual(analyze([f],[r])["matched"],0)
    def test_exact_id(self):
        f={"fixture_id":"x","observations":2,"observation_gap_minutes":60,"first_ah_line":-.5,"last_ah_line":-.75,"favorite_side":"H"}
        r={"fixture_id":"y","ft_home_goals":2,"ft_away_goals":1,"result_source":"verified","result_identity":"exact"}
        self.assertEqual(analyze([f],[r])["matched"],0)

    def test_verified_source_id_bridge(self):
        f={"fixture_id":"canonical","source_fixture_ids":["pinnwire:abc"],"observations":2,"observation_gap_minutes":60,"first_ah_line":-.5,"last_ah_line":-.75,"favorite_side":"H"}
        r={"fixture_id":"pinnwire:abc","ft_home_goals":2,"ft_away_goals":1,"result_source":"verified","result_identity":"exact"}
        self.assertEqual(analyze([f],[r])["matched"],1)

    def test_bridge_rejects_conflicting_scores(self):
        f={"fixture_id":"canonical","source_fixture_ids":["pinnwire:abc"],"observations":2,"observation_gap_minutes":60,"first_ah_line":-.5,"last_ah_line":-.75,"favorite_side":"H"}
        rows=[{"fixture_id":fid,"ft_home_goals":h,"ft_away_goals":a,"result_source":"verified","result_identity":"exact"} for fid,h,a in [("canonical",2,1),("pinnwire:abc",1,1)]]
        report=analyze([f],rows)
        self.assertEqual(report["matched"],0)
        self.assertEqual(report["excluded"]["ft_score_conflict"],1)

    def test_missing_ft_separate_from_conflict(self):
        f={"fixture_id":"canonical","source_fixture_ids":["pinnwire:abc"],"observations":2,"observation_gap_minutes":60,"first_ah_line":-.5,"last_ah_line":-.75,"favorite_side":"H"}
        report=analyze([f],[])
        self.assertEqual(report["excluded"]["ft_not_found"],1)

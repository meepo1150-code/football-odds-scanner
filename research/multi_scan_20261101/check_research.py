"""Research-specific checks; deliberately separate from production dependency set."""
import unittest, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import run as r

class TemporalAndSettlementTests(unittest.TestCase):
 def test_cutoff(self):
  self.assertEqual(r.day(r.stamp('2026-10-31T04:59:59+07:00')),'2026-10-30')
  self.assertEqual(r.day(r.stamp('2026-10-31T05:00:00+07:00')),'2026-10-31')
 def test_naive_timestamp_rejected(self):
  self.assertIsNone(r.stamp('2026-10-31T18:00:00'))
 def test_slot_does_not_backdate_late_scan(self):
  x={'scheduled_target_at':'2026-10-31T18:00:36+07:00','observed_at':'2026-10-31T18:16:00+07:00'}
  self.assertFalse(r.slot(x)[1]);x['observed_at']='2026-10-31T18:01:00+07:00';self.assertTrue(r.slot(x)[1])
 def test_manual_not_rounded_into_slot(self):
  self.assertEqual(r.slot({'observed_at':'2026-10-31T18:01:00+07:00'})[0],'MANUAL')
 def test_quarters(self):
  x=r.settle_asian_handicap(1,0,-.75,2.,'H');self.assertEqual(x.profit_units,.5)
  self.assertEqual(r.settle_asian_handicap(1,0,.75,2.,'A').profit_units,-.5)
  self.assertEqual(r.settle_asian_total(2,1,2.75,2.,'O').profit_units,.5)
  self.assertEqual(r.settle_asian_total(2,1,2.75,2.,'U').profit_units,-.5)
 def test_invalid_line(self):self.assertFalse(r.validline(.3))
 def test_cluster_replication_not_independent(self):
  a=r.boot([1.,-1.],['a','b']);b=r.boot([1.]*10+[-1.]*10,['a']*10+['b']*10)
  self.assertEqual(a['clusters'],b['clusters']);self.assertEqual(a['ci95_low'],b['ci95_low'])
 def test_push_and_half_stakes(self):
  rows=[]
  for i,(s,p,w,l) in enumerate([('FULL_WIN',1,1,0),('HALF_WIN',.5,.5,0),('PUSH',0,0,0),('HALF_LOSS',-.5,0,.5),('FULL_LOSS',-1,0,1)]):
   rows.append(dict(fixture_id=str(i),profit=p,settlement=s,win_stake=w,loss_stake=l,price=2.,fair_share=.5,kickoff='2026-01-01',side='H'))
  m=r.metrics(rows);self.assertEqual(m['wr'],.5);self.assertEqual(m['roi'],0);self.assertEqual(m['bets'],5)
 def test_bin_edges(self):
  self.assertEqual(r.timing(.999),'T-1');self.assertEqual(r.timing(1),'T-2');self.assertEqual(r.timing(24),'T-24+')

class GeneratedEvidenceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.rows=[json.loads(x) for x in r.gzip.decompress((r.OUT/'master_observations.jsonl.gz').read_bytes()).decode().splitlines()]
 def test_every_observation_strictly_prematch(self):
  self.assertTrue(all(r.stamp(x['observed_at'])<r.stamp(x['kickoff']) for x in self.rows))
 def test_no_history_mixed_with_current(self):
  self.assertFalse(any('HISTORICAL' in x['source_semantics'] for x in self.rows))
 def test_unique_observation_contract(self):
  keys=[(x['fixture_id'],x['provider'],x['bookmaker'],r.stamp(x['observed_at'])) for x in self.rows]
  self.assertEqual(len(keys),len(set(keys)))
 def test_missing_ft_not_silently_excluded(self):
  self.assertTrue(any(x['ft_home'] is None for x in self.rows))
 def test_18_decision_never_after_kickoff(self):
  preds=r.pd.read_csv(r.OUT/'setup_decision_predictions.csv');lookup={x['fixture_id']:r.stamp(x['kickoff']) for x in self.rows}
  self.assertTrue(all(r.stamp(x.observed_at)<lookup[x.fixture_id] for x in preds.itertuples()))
 def test_price_only_same_side_line_and_strict_time(self):
  pairs=r.pd.read_csv(r.OUT/'price_only_pairs.csv')
  self.assertTrue(all(r.stamp(x.first_observed)<r.stamp(x.last_observed) for x in pairs.itertuples()))
 def test_result_count_integrity(self):
  stats=r.pd.read_csv(r.OUT/'stage_metrics.csv')
  counts=stats[['FULL_WIN','HALF_WIN','PUSH','HALF_LOSS','FULL_LOSS']].sum(axis=1)
  self.assertTrue((counts==stats.bets).all())
 def test_corrected_p_not_smaller(self):
  stats=r.pd.read_csv(r.OUT/'statistical_tests.csv').dropna(subset=['p'])
  self.assertTrue((stats.holm_p>=stats.p).all())
 def test_fixed_data_hashes(self):
  inventory=r.pd.read_csv(r.OUT/'data_inventory.csv')
  for row in inventory.itertuples():
   self.assertEqual(r.hashlib.sha256((r.ROOT/row.path).read_bytes()).hexdigest(),row.sha256,row.path)

if __name__=='__main__':unittest.main()

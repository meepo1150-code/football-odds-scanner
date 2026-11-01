"""Network-free regression and generated-result invariant checks."""
import importlib.util,json,unittest,csv,gzip
from pathlib import Path
spec=importlib.util.spec_from_file_location('multiscan',Path(__file__).with_name('analyze.py'))
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

def row(time='2026-10-20T18:01:00+07:00',kick='2026-10-21T01:00:00+07:00',h=2,v=1):
    return {'fixture_id':'test','league':'test','kickoff':kick,'observed_at':time,'_time':a.dt(time),'_kick':a.dt(kick),'_day':a.day(a.dt(kick)),
            '_ft':(h,v),'_favorite':'H','ah':{'home_line':-.75,'away_line':.75,'home_price':2.,'away_price':2.},'ou':{'line':2.75,'over_price':2.,'under_price':2.}}

class ResearchTests(unittest.TestCase):
    def test_quarter_settlement_and_wr(self):
        r=row();b=a.bet(r,'AH');self.assertEqual(b['settlement'],'HALF_WIN');self.assertEqual(b['profit'],.5)
        self.assertEqual(a.bet(r,'OU')['settlement'],'HALF_WIN')
        self.assertEqual(a.bet(r,'AH','A')['settlement'],'HALF_LOSS')
        r2=row(h=0,v=0);b2=a.bet(r2,'AH');s=a.stats([b,b2]);self.assertAlmostEqual(s['wr'],1/3);self.assertAlmostEqual(s['roi'],-.25)
    def test_grid_and_missing(self):
        r=row();r['ah']['home_line']=-.74;self.assertIsNone(a.bet(r,'AH'))
        r=row();r['ou']['under_price']=None;self.assertIsNone(a.bet(r,'OU'))
        r=row();r['_ft']=None;self.assertIsNone(a.bet(r,'AH'))
    def test_frozen_side(self):
        r=row();r['_favorite']='A';self.assertEqual(a.bet(r,'AH')['side'],'A');self.assertEqual(a.bet(r,'AH','H')['side'],'H')
    def test_no_future_substitution(self):
        self.assertIsNone(a.slotrow([row('2026-10-20T18:16:00+07:00')],18))
        r=row();self.assertIs(a.slotrow([r],18),r)
        self.assertIsNone(a.slotrow([r],18,0))
        self.assertIsNone(a.slotrow([row('2026-10-20T21:01:00+07:00')],18))
    def test_cutoff_and_midnight(self):
        self.assertEqual(a.day(a.dt('2026-10-21T04:59:59+07:00')),'2026-10-20')
        self.assertEqual(a.day(a.dt('2026-10-21T05:00:00+07:00')),'2026-10-21')
        r=row('2026-10-21T00:01:00+07:00');self.assertIs(a.slotrow([r],0),r)
    def test_earliest_receipt_online(self):
        x=row('2026-10-20T18:01:00+07:00');y=row('2026-10-20T18:10:00+07:00');self.assertIs(a.slotrow([y,x],18),x)
    def test_pair_stats(self):
        p=a.paired([0.,0.,0.]);self.assertEqual(p['mean_difference'],0.);self.assertEqual(p['p'],1.);self.assertEqual(p['ci95'],[0.,0.])
    def test_movement(self):
        x=row();y=row();y['ah']['home_line']=-1.;y['ah']['away_line']=1.;self.assertEqual(a.category(x,y,'AH','H'),'LINE_DOWN_025')
    def test_generated_safety(self):
        out=Path(__file__).with_name('results')
        if not out.exists():self.skipTest('Generate results before invariant validation')
        with gzip.open(out/'master_research_dataset.csv.gz','rt') as f:
            for r in csv.DictReader(f):
                if not r['exclusion']:
                    self.assertLess(a.dt(r['actual_observation_time']),a.dt(r['kickoff']))
                    self.assertEqual(r['kind'],'ACTUAL_OBSERVATION')
        with gzip.open(out/'strategy_bets.csv.gz','rt') as f:
            seen=set()
            for r in csv.DictReader(f):
                key=(r['strategy'],r['market'],r['fixture_id']);self.assertNotIn(key,seen);seen.add(key)
                self.assertLess(a.dt(r['observed_at']),a.dt(r['kickoff']))
                self.assertTrue(1.8<=float(r['price'])<=2.2)
                if r['strategy']=='B':
                    t=a.dt(r['observed_at']);self.assertEqual(t.hour,18);self.assertLessEqual(t.minute*60+t.second,15*60)
        for r in json.loads((out/'all_inference_bh.json').read_text()):
            if r['p']is not None:self.assertGreaterEqual(r['q_bh']+1e-12,r['p'])

if __name__=='__main__':unittest.main(verbosity=2)

import copy
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from youtube_prediction.engine import validate,append_ledger,read_ledger,settle,summarize,verify_fixtures,result_index
from youtube_prediction.pipeline import scenes,render_card

def example():
    now=datetime.now(timezone.utc); kickoff=now+timedelta(hours=3)
    return {'date':now.astimezone(__import__('zoneinfo').ZoneInfo('Asia/Bangkok')).date().isoformat(),'published_at':now.isoformat(),'source_type':'REVIEWED_PREDICTION','predictions':[{'id':'p1','fixture_id':'f1','kickoff':kickoff.isoformat(),'home':'A','away':'B','market':'OU','line':2.5,'selection':'UNDER'}]}

class PredictionTests(unittest.TestCase):
    def test_validation(self):
        self.assertEqual(validate(example()),'REVIEWED')
        for field,value in [('market','XYZ'),('selection','HOME'),('line',float('nan')),('line',True),('line',2.3)]:
            d=example(); d['predictions'][0][field]=value
            with self.assertRaises(ValueError):validate(d)
    def test_demo_rejected(self):
        d=example();d['source_type']='SYNTHETIC_DEMO_DO_NOT_PUBLISH'
        with self.assertRaises(ValueError):validate(d)
    def test_timestamp_and_duplicates(self):
        d=example();d['published_at']='2026-11-04T08:00:00'
        with self.assertRaises(ValueError):validate(d)
        d=example();d['predictions']*=2
        with self.assertRaises(ValueError):validate(d)
    def test_ledger(self):
        d=example();fixtures=copy.deepcopy(d['predictions'])
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'ledger.jsonl'
            self.assertEqual(append_ledger(p,d,fixtures),1)
            self.assertEqual(append_ledger(p,d,fixtures),0)
            d['predictions'][0]['selection']='OVER'
            with self.assertRaises(ValueError):append_ledger(p,d,fixtures)
            row=json.loads(p.read_text()); row['prediction']['line']=3
            p.write_text(json.dumps(row)+'\n')
            with self.assertRaises(ValueError):read_ledger(p)
    def test_backdate_rejected_without_write(self):
        d=example();now=datetime.now(timezone.utc)
        d['published_at']=(now-timedelta(hours=3)).isoformat();d['predictions'][0]['kickoff']=(now-timedelta(hours=1)).isoformat()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'ledger.jsonl'
            with self.assertRaises(ValueError):append_ledger(p,d,d['predictions'])
            self.assertFalse(p.exists())
    def test_fixture_mismatch(self):
        d=example();f=copy.deepcopy(d['predictions']);f[0]['home']='Other'
        with self.assertRaises(ValueError):verify_fixtures(d,f)
        with self.assertRaises(ValueError):verify_fixtures(d,[])
    def test_asian_settlement(self):
        for market,side,line,h,a,want in [('AH','HOME',-.75,1,0,'HALF_WIN'),('AH','AWAY',.75,1,0,'HALF_LOSS'),('AH','HOME',-.25,0,0,'HALF_LOSS'),('AH','AWAY',.25,0,0,'HALF_WIN'),('AH','HOME',-1,1,0,'PUSH'),('AH','HOME',-.5,2,0,'FULL_WIN'),('AH','HOME',-.5,0,0,'FULL_LOSS'),('OU','OVER',2.75,2,1,'HALF_WIN'),('OU','UNDER',2.25,1,1,'HALF_WIN'),('OU','UNDER',2.75,2,1,'HALF_LOSS')]:
            self.assertEqual(settle({'market':market,'selection':side,'line':line},h,a),want)
    def test_summary_no_cherry_pick_and_market_separation(self):
        p=example()['predictions'][0];p.update(market='AH',selection='HOME',line=-.75)
        rows=[{'date':'2026-11-03','prediction':p},{'date':'2026-11-03','prediction':dict(p,id='p2',fixture_id='f2',market='OU',selection='UNDER',line=2.5)}]
        s=summarize(rows,[{'fixture_id':'f1','ft_home_goals':1,'ft_away_goals':0,'result_source':'TEST'}],'2026-11-04')
        self.assertEqual(s['daily']['AH']['wr'],1)
        self.assertIsNone(s['daily']['OU']['wr'])
        self.assertEqual(s['daily']['OU']['counts']['PENDING'],1)
        self.assertEqual(len(s['details']),2)
    def test_conflicting_results(self):
        r={'fixture_id':'f','ft_home_goals':1,'ft_away_goals':0,'result_source':'TEST'}
        with self.assertRaises(ValueError):result_index([r,dict(r,ft_home_goals=2)])
    def test_empty_episode_and_pagination(self):
        d=example();d['predictions']=[]
        script=scenes(d,summarize([],[],d['date']))
        self.assertEqual(len(script),5)
        self.assertIn('No reviewed',script[2]['lines'][0])
    def test_upload_cannot_be_public(self):
        from youtube_prediction.upload import upload_body
        body=upload_body(dict(title='Test',description='Test',tags=[],defaultLanguage='en',privacyStatus='public'))
        self.assertEqual(body['status']['privacyStatus'],'private')
    def test_different_id_same_market_rejected(self):
        d=example()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ledger.jsonl'
            append_ledger(path,d,d['predictions'])
            d['predictions'][0]['id']='p2'
            with self.assertRaises(ValueError):append_ledger(path,d,d['predictions'])
    def test_invalid_batch_no_partial_append(self):
        d=example(); second=dict(d['predictions'][0],id='p2',fixture_id='f2')
        second['kickoff']=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
        d['published_at']=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
        d['predictions'].append(second)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ledger.jsonl'
            with self.assertRaises(ValueError):append_ledger(path,d,d['predictions'])
            self.assertFalse(path.exists())
    @unittest.skipUnless(importlib.util.find_spec('PIL'), 'Optional video dependency; covered by dedicated video CI')
    def test_long_names_fit(self):
        with tempfile.TemporaryDirectory() as tmp:
            render_card(Path(tmp)/'card.png','TODAYS PREDICTIONS',['Borussia Monchengladbach vs Wolverhampton Wanderers'],'Bangkok UTC+7')

if __name__=='__main__':unittest.main()


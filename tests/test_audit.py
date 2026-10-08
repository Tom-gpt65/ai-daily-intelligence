"""No-network checks for independently audited article freshness."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from audit_publication import assess_public,recent_successful_schedule
from learning_editorial import deepen_digest,is_promotional,_word_count

class AuditTests(unittest.TestCase):
    def setUp(self):
        self.edition={'date':'2026-10-09','mode':'editorial','demo':False,'updated_at':'2026-10-09T08:04:00+08:00',
                      'essay':['English news '*32], 'stories':[{'url':'https://example.com','title':'AI research'}]*3,
                      'word_count':580,'reading_metrics':{'word_count':580}}
        self.index=[{'date':'2026-10-09'}]
    def test_fresh_article(self):
        errs,_=assess_public(self.index,self.edition,'2026-10-09');self.assertEqual(errs,[])
    def test_old_article_cannot_pass(self):
        errs,_=assess_public(self.index,self.edition,'2026-10-10');self.assertTrue(errs)
    def test_demo_never_passes(self):
        self.edition['mode']='demo';self.edition['demo']=True
        self.assertTrue(assess_public(self.index,self.edition,'2026-10-09')[0])
    def test_missing_sources_fails(self):
        self.edition['stories']=[]
        self.assertTrue(assess_public(self.index,self.edition,'2026-10-09')[0])
    def test_short_fallback_flagged(self):
        self.edition['mode']='source_digest';self.edition['reading_metrics']={'word_count':493}
        errs,warn=assess_public(self.index,self.edition,'2026-10-09')
        self.assertEqual(errs,[]);self.assertEqual(len(warn),2)
    def test_correct_scheduled_run(self):
        runs={'workflow_runs':[{'event':'schedule','conclusion':'success','created_at':'2026-10-09T00:05:00Z'}]}
        self.assertTrue(recent_successful_schedule(runs,'2026-10-09'))
        self.assertFalse(recent_successful_schedule(runs,'2026-10-10'))
    def test_wrong_event_not_schedule(self):
        runs={'workflow_runs':[{'event':'push','conclusion':'success','created_at':'2026-10-09T00:05:00Z'}]}
        self.assertFalse(recent_successful_schedule(runs,'2026-10-09'))
    def test_promotional_source_excluded(self):
        self.assertTrue(is_promotional('Hear from AI execs at TechCrunch Disrupt','Register now to save up to $100'))
        self.assertFalse(is_promotional('Research report on data centres','AI energy usage study presents new findings'))
    def test_extension_is_explicitly_learning_not_news(self):
        paras=deepen_digest(['Neutral attributed excerpt from a legitimate source.']*3,[{'topic':'Research'},{'topic':'Policy & Society'}])
        self.assertTrue(any('DSE inference practice' in s for s in paras))
        self.assertTrue(any('not an additional news report' in s for s in paras))
        self.assertGreater(_word_count(' '.join(paras)),75)

if __name__=='__main__':unittest.main()

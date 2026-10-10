"""No-network checks for independently audited article freshness."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from audit_publication import assess_public,recent_successful_schedule,recent_successful_recovery,morning_refresh_status
from learning_editorial import deepen_digest,is_promotional,_word_count

class AuditTests(unittest.TestCase):
    def setUp(self):
        import json
        self.edition=json.loads((ROOT/'site/reports/2026-10-10.json').read_text(encoding='utf-8'))
        self.edition.update(date='2026-10-09',updated_at='2026-10-09T08:04:00+08:00')
        self.index=[{key:self.edition[key] for key in ('date','mode','updated_at','word_count')}]
        self.index[0]['stories']=len(self.edition['stories'])
    def test_educational_backup_is_accepted_with_warning(self):
        from reading_backup import build_reading
        from datetime import datetime
        from zoneinfo import ZoneInfo
        edition=build_reading("2026-10-10",datetime(2026,10,10,8,0,tzinfo=ZoneInfo("Asia/Hong_Kong")))
        index=[{key:edition[key] for key in ('date','mode','updated_at','word_count')}]
        index[0]['stories']=0
        errs,warnings=assess_public(index,edition,"2026-10-10")
        self.assertEqual(errs,[])
        self.assertTrue(any("educational" in warning.lower() for warning in warnings))
    def test_current_news_missing_word_translation_is_rejected(self):
        from edition_guarantee import article_words
        word=next(iter(article_words(self.edition['essay'])))
        self.edition['dictionary'][word]={'translation':''}
        errors,_=assess_public(self.index,self.edition,'2026-10-09')
        self.assertTrue(any("offline Chinese" in e for e in errors))
    def test_fresh_article(self):
        errs,_=assess_public(self.index,self.edition,'2026-10-09');self.assertEqual(errs,[])
    def test_essay_word_count_mismatch_is_detected(self):
        self.edition['word_count']+=8
        errors,_=assess_public(self.index,self.edition,'2026-10-09')
        self.assertTrue(any('word count' in e.lower() for e in errors))
    def test_invalid_source_reference_is_detected(self):
        self.edition['essay'][0]+=' [S9]'
        errors,_=assess_public(self.index,self.edition,'2026-10-09')
        self.assertTrue(any('source ID' in e for e in errors))
    def test_unlinked_or_unreadable_story_is_rejected(self):
        self.edition['stories'][0]['url']='javascript:alert(1)'
        errors,_=assess_public(self.index,self.edition,'2026-10-09')
        self.assertTrue(any('URL' in e for e in errors))
    def test_custom_questions_cannot_claim_official_authorisation(self):
        self.edition['practice']={'official':True,'items':[{'stem':'What?', 'evidence':'Paragraph 1'}]}
        errors,_=assess_public(self.index,self.edition,'2026-10-09')
        self.assertTrue(any('official HKEAA' in e for e in errors))
    def test_invalid_mc_answer_key_is_detected(self):
        self.edition['practice']={'official':False,'items':[{'type':'mc','stem':'What?','evidence':'P1','options':['Yes','No'],'answer':5}]}
        errors,_=assess_public(self.index,self.edition,'2026-10-09')
        self.assertTrue(any('answer key' in e for e in errors))
    def test_old_article_cannot_pass(self):
        errs,_=assess_public(self.index,self.edition,'2026-10-10');self.assertTrue(errs)
    def test_demo_never_passes(self):
        self.edition['mode']='demo';self.edition['demo']=True
        self.assertTrue(assess_public(self.index,self.edition,'2026-10-09')[0])
    def test_missing_sources_fails(self):
        self.edition['stories']=[]
        self.assertTrue(assess_public(self.index,self.edition,'2026-10-09')[0])
    def test_article_modified_before_morning_generation_is_not_fresh(self):
        report=dict(self.edition,updated_at="2026-10-09T07:39:59+08:00")
        good,note=morning_refresh_status(report,"2026-10-09")
        self.assertFalse(good)
        self.assertIn("07:40",note)
    def test_article_refreshed_after_0740_passes(self):
        good,note=morning_refresh_status(self.edition,"2026-10-09")
        self.assertTrue(good)
        self.assertIn("not proven",note)
    def test_bad_timezone_does_not_claim_freshness(self):
        report=dict(self.edition,updated_at="2026-10-09T09:30:00")
        self.assertFalse(morning_refresh_status(report,"2026-10-09")[0])
    def test_utc_at_morning_hk_correctly_converts(self):
        report=dict(self.edition,updated_at="2026-10-08T23:40:00Z")
        self.assertTrue(morning_refresh_status(report,"2026-10-09")[0])
    def test_date_without_report_will_not_pass(self):
        self.assertFalse(morning_refresh_status({},"2026-10-09")[0])
    def test_short_fallback_flagged(self):
        self.edition['mode']='source_digest';self.edition['reading_metrics']={'word_count':493}
        errs,warn=assess_public(self.index,self.edition,'2026-10-09')
        self.assertTrue(any('1,000' in item for item in errs));self.assertTrue(any('RSS-based' in item for item in warn))
    def test_correct_scheduled_run(self):
        runs={'workflow_runs':[{'event':'schedule','conclusion':'success','created_at':'2026-10-09T00:05:00Z'}]}
        self.assertTrue(recent_successful_schedule(runs,'2026-10-09'))
        self.assertFalse(recent_successful_schedule(runs,'2026-10-10'))
    def test_wrong_event_not_schedule(self):
        runs={'workflow_runs':[{'event':'push','conclusion':'success','created_at':'2026-10-09T00:05:00Z'}]}
        self.assertFalse(recent_successful_schedule(runs,'2026-10-09'))
    def test_successful_recovery_is_not_scheduled_success(self):
        runs={'workflow_runs':[{'event':'workflow_dispatch','conclusion':'success',
                                 'created_at':'2026-10-09T00:36:00Z'}]}
        self.assertTrue(recent_successful_recovery(runs,'2026-10-09'))
        self.assertFalse(recent_successful_schedule(runs,'2026-10-09'))
        self.assertFalse(recent_successful_recovery(runs,'2026-10-10'))
    def test_failed_dispatch_or_push_cannot_count_as_recovery(self):
        runs={'workflow_runs':[{'event':'workflow_dispatch','conclusion':'failure',
                                 'created_at':'2026-10-09T00:36:00Z'},
                                {'event':'push','conclusion':'success',
                                 'created_at':'2026-10-09T00:37:00Z'}]}
        self.assertFalse(recent_successful_recovery(runs,'2026-10-09'))
    def test_promotional_source_excluded(self):
        self.assertTrue(is_promotional('Hear from AI execs at TechCrunch Disrupt','Register now to save up to $100'))
        self.assertFalse(is_promotional('Research report on data centres','AI energy usage study presents new findings'))
    def test_extension_is_explicitly_learning_not_news(self):
        paras=deepen_digest(['Neutral attributed excerpt from a legitimate source.']*3,[{'topic':'Research'},{'topic':'Policy & Society'}])
        self.assertTrue(any('DSE inference practice' in s for s in paras))
        self.assertTrue(any('not an additional news report' in s for s in paras))
        self.assertGreater(_word_count(' '.join(paras)),75)

if __name__=='__main__':unittest.main()

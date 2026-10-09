"""Missed-report recovery checks, without requiring network or GitHub secrets."""
import pathlib,sys,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import recover_daily

class RecoveryTests(unittest.TestCase):
    def test_fresh_report_does_not_dispatch(self):
        decision,_=recover_daily.should_dispatch(recover_daily.TODAY,[],recover_daily.TODAY+"T07:50:00+08:00")
        self.assertFalse(decision)
    def test_early_morning_report_needs_new_refresh(self):
        decision,_=recover_daily.should_dispatch(recover_daily.TODAY,[],recover_daily.TODAY+"T06:45:00+08:00")
        self.assertTrue(decision)
    def test_missing_report_triggers_recovery(self):
        decision,_=recover_daily.should_dispatch("2000-01-01",[])
        self.assertTrue(decision)
    def test_running_workflow_blocks_duplicate_dispatch(self):
        decision,_=recover_daily.should_dispatch("2000-01-01",[{"event":"schedule","status":"in_progress"}])
        self.assertFalse(decision)
    def test_code_only_website_deploy_does_not_block_news_recovery(self):
        push={"event":"push","status":"in_progress","created_at":recover_daily.TODAY+"T08:20:00+08:00"}
        allowed,_=recover_daily.should_dispatch("2000-01-01",[push])
        self.assertTrue(allowed)
    def test_active_scheduled_news_generation_blocks_retry(self):
        task={"event":"schedule","status":"in_progress","created_at":recover_daily.TODAY+"T07:40:00+08:00"}
        allowed,_=recover_daily.should_dispatch("2000-01-01",[task])
        self.assertFalse(allowed)
    def test_queued_workflow_blocks_duplicate_dispatch(self):
        decision,_=recover_daily.should_dispatch(None,[{"event":"workflow_dispatch","status":"queued"}])
        self.assertFalse(decision)
    def test_completed_recovery_attempts_capped_per_day(self):
        run={"status":"completed","event":"workflow_dispatch",
             "created_at":recover_daily.TODAY+"T01:00:00+08:00"}
        allowed,reason=recover_daily.should_dispatch("2000-01-01",[run])
        self.assertTrue(allowed)
        allowed,reason=recover_daily.should_dispatch("2000-01-01",[run,run])
        self.assertFalse(allowed)
        self.assertIn("limit",reason.lower())
    def test_last_night_utc_day_conversion_does_not_skip_today(self):
        run={"status":"completed","event":"workflow_dispatch",
             "created_at":recover_daily.TODAY+"T06:00:00+08:00"}
        denied,_=recover_daily.should_dispatch("2000-01-01",[run,run])
        self.assertFalse(denied)
    def test_missing_timestamp_must_be_regenerated(self):
        allowed,_=recover_daily.should_dispatch(recover_daily.TODAY,[],None)
        self.assertTrue(allowed)
    def test_date_only_without_time_cannot_claim_morning_readiness(self):
        allowed,_=recover_daily.should_dispatch(recover_daily.TODAY,[],recover_daily.TODAY)
        self.assertTrue(allowed)
    def test_future_old_date_does_not_block_recovery(self):
        stale={"status":"completed","event":"workflow_dispatch","created_at":"2020-01-01T00:00:00Z"}
        allowed,_=recover_daily.should_dispatch("2000-01-01",[stale,stale])
        self.assertTrue(allowed)
    def test_fresh_but_invalid_article_must_retry(self):
        allowed,_=recover_daily.should_dispatch(recover_daily.TODAY,[],
            recover_daily.TODAY+"T08:15:00+08:00",quality_ok=False)
        self.assertTrue(allowed)
    def test_public_passage_validation(self):
        import re
        date=recover_daily.TODAY
        paragraphs=["Editorial evidence [S1] [S2] [S3] " + "analysis "*200]*5
        count=len(re.findall(r"\b[A-Za-z]+(?:['’-][A-Za-z]+)*\b"," ".join(paragraphs)))
        sources=[{"id":f"S{i}","title":"Research","url":f"https://example.com/{i}"} for i in range(1,4)]
        report={"date":date,"mode":"source_digest","word_count":count,
                "essay":paragraphs,"stories":sources,
                "practice":{"items":[{"stem":"Question"}]*7}}
        index={"date":date,"word_count":count,"stories":3}
        self.assertTrue(recover_daily.edition_is_readable(index,report))
        self.assertFalse(recover_daily.edition_is_readable(index,{**report,"essay":["too short"]}))
        self.assertFalse(recover_daily.edition_is_readable(index,{**report,"practice":{"items":[]}}))
        self.assertFalse(recover_daily.edition_is_readable({**index,"stories":4},report))
    def test_educational_backup_accepted_when_entire_dictionary_exists(self):
        from reading_backup import build_reading
        report=build_reading(recover_daily.TODAY)
        row={'date':report['date'],'word_count':report['word_count'],'stories':0}
        self.assertTrue(recover_daily.edition_is_readable(row,report))
        report['dictionary'].pop(next(iter(report['dictionary'])))
        self.assertFalse(recover_daily.edition_is_readable(row,report))
    def test_retry_schedule_only_twice(self):
        yaml=(ROOT/".github/workflows/recovery.yml").read_text(encoding="utf-8")
        self.assertIn("cron: '20 8 * * *'",yaml)
        self.assertIn("cron: '40 9 * * *'",yaml)
        self.assertIn("cron: '25 10 * * *'",yaml)
        self.assertIn("cron: '25 12 * * *'",yaml)
        self.assertIn("actions: write",yaml)
        self.assertNotIn("OPENAI_API_KEY",yaml)

if __name__=="__main__":unittest.main()

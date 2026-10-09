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
        decision,_=recover_daily.should_dispatch("2000-01-01",[{"status":"in_progress"}])
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
        decision,_=recover_daily.should_dispatch(None,[{"status":"queued"}])
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
    def test_retry_schedule_only_twice(self):
        yaml=(ROOT/".github/workflows/recovery.yml").read_text(encoding="utf-8")
        self.assertIn("cron: '20 8 * * *'",yaml)
        self.assertIn("cron: '40 9 * * *'",yaml)
        self.assertIn("actions: write",yaml)
        self.assertNotIn("OPENAI_API_KEY",yaml)

if __name__=="__main__":unittest.main()

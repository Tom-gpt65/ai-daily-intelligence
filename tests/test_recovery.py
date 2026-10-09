"""Missed-report recovery checks, without requiring network or GitHub secrets."""
import pathlib,sys,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import recover_daily

class RecoveryTests(unittest.TestCase):
    def test_fresh_report_does_not_dispatch(self):
        decision,_=recover_daily.should_dispatch(recover_daily.TODAY,[])
        self.assertFalse(decision)
    def test_missing_report_triggers_recovery(self):
        decision,_=recover_daily.should_dispatch("2000-01-01",[])
        self.assertTrue(decision)
    def test_running_workflow_blocks_duplicate_dispatch(self):
        decision,_=recover_daily.should_dispatch("2000-01-01",[{"status":"in_progress"}])
        self.assertFalse(decision)
    def test_queued_workflow_blocks_duplicate_dispatch(self):
        decision,_=recover_daily.should_dispatch(None,[{"status":"queued"}])
        self.assertFalse(decision)
    def test_retry_schedule_only_twice(self):
        yaml=(ROOT/".github/workflows/recovery.yml").read_text(encoding="utf-8")
        self.assertIn("cron: '20 8 * * *'",yaml)
        self.assertIn("cron: '40 9 * * *'",yaml)
        self.assertIn("actions: write",yaml)
        self.assertNotIn("OPENAI_API_KEY",yaml)

if __name__=="__main__":unittest.main()

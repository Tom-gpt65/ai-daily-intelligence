"""Test merge behaviour without writing to the real repository or making pushes."""
import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from publish_reports import merge_index

class SafeDailyPublisherTests(unittest.TestCase):
    def test_keep_previous_dates_when_new_news_arrives(self):
        older=[{"date":"2026-10-08","headline":"Yesterday","word_count":620}]
        newer=[{"date":"2026-10-09","headline":"Today","word_count":600}]
        result=merge_index(older,newer)
        self.assertEqual([x["date"] for x in result],["2026-10-09","2026-10-08"])
    def test_newly_generated_edition_wins_same_date(self):
        old=[{"date":"2026-10-09","word_count":250}]
        new=[{"date":"2026-10-09","word_count":610}]
        result=merge_index(old,new)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["word_count"],610)
    def test_duplicate_remote_entries_are_removed(self):
        entries=[{"date":"2026-10-07","word_count":580}]*3
        self.assertEqual(len(merge_index(entries,[])),1)
    def test_expected_conflict_safe_workflow(self):
        text=(ROOT/".github/workflows/daily.yml").read_text(encoding="utf-8")
        self.assertIn("python scripts/publish_reports.py",text)
        self.assertNotIn("git push\n",text)
        self.assertIn("cron: '40 7 * * *'",text)

if __name__=="__main__":unittest.main()

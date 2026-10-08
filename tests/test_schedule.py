"""Regression tests for the free daily readiness schedule and independent checks."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ScheduleTests(unittest.TestCase):
    def test_generation_is_scheduled_at_0740_hk(self):
        text = (ROOT / ".github/workflows/daily.yml").read_text(encoding="utf-8")
        self.assertIn("cron: '40 7 * * *'", text)
        self.assertIn("timezone: 'Asia/Hong_Kong'", text)
        self.assertNotIn("cron: '0 8 * * *'", text)

    def test_readiness_audit_keeps_both_checks(self):
        text = (ROOT / ".github/workflows/audit.yml").read_text(encoding="utf-8")
        self.assertIn("cron: '5 8 * * *'", text)
        self.assertIn("cron: '17 9 * * *'", text)
        self.assertEqual(text.count("timezone: 'Asia/Hong_Kong'"), 2)

    def test_free_automated_generation_is_preserved(self):
        text = (ROOT / ".github/workflows/daily.yml").read_text(encoding="utf-8")
        self.assertIn("ollama pull phi3:mini", text)
        self.assertIn("TRANSLATE_ENABLED: '0'", text)
        self.assertIn("actions/deploy-pages@v4", text)
        self.assertNotIn("OPENAI_API_KEY", text)

    def test_website_shows_distinction_between_start_and_target(self):
        text = (ROOT / "site/index.html").read_text(encoding="utf-8")
        self.assertIn("07:40 開始更新", text)
        self.assertIn("08:00 目標可讀", text)
        self.assertIn("08:05 及 09:17", text)


if __name__ == "__main__":
    unittest.main()

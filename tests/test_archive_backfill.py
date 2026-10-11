"""Daily news tests and archive backfills must not trigger a release-version bump."""
from __future__ import annotations
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from edition_guarantee import article_words, complete

class ArchiveBackfillTests(unittest.TestCase):
    def setUp(self):
        folder = ROOT / "site" / "reports"
        self.index = json.loads((folder / "index.json").read_text(encoding="utf-8"))
        from history_support import historical
        self.archive = historical('2026-10-08')
        self.today = historical('2026-10-09')

    def test_backfill_is_archived_without_replacing_todays_article(self):
        dates=[row["date"] for row in self.index]
        self.assertEqual(dates,sorted(dates,reverse=True))
        self.assertEqual(len(dates),len(set(dates)))
        self.assertNotIn("2026-10-08",dates)
        self.assertNotIn("2026-10-09",dates)
        self.assertEqual(self.today["date"], "2026-10-09")
        from content_novelty import recent_articles
        corpus=recent_articles(ROOT/'site/reports','2026-10-12')
        self.assertIn(self.today,corpus)
        self.assertIn(self.archive,corpus)

    def test_backfill_is_clearly_educational_and_not_false_historical_news(self):
        self.assertEqual(self.archive["date"], "2026-10-08")
        self.assertEqual(self.archive["mode"], "reading_feature")
        self.assertFalse(self.archive["demo"])
        self.assertEqual(self.archive["stories"], [])
        self.assertIn("backfill", self.archive["editorial_notice"].lower())
        self.assertIn("not reporting published on 8 october", self.archive["editorial_notice"].lower())
        self.assertTrue(self.archive["processing"]["historical_backfill"])

    def test_full_length_offline_reading_and_questions(self):
        article = self.archive
        words = re.findall(r"\b[A-Za-z]+(?:['’-][A-Za-z]+)*\b", " ".join(article["essay"]))
        self.assertEqual(article["word_count"], len(words))
        self.assertGreaterEqual(len(words), 1000)
        self.assertLessEqual(len(words), 1550)
        self.assertTrue(complete(article))
        self.assertEqual(len(article["dictionary"]), len(article_words(article["essay"])))
        questions = article["practice"]["items"]
        self.assertEqual(len(questions), 7)
        self.assertFalse(article["practice"]["official"])
        for q in questions:
            self.assertTrue(q["evidence_quote"])
            self.assertTrue(q["stem"])
            self.assertGreaterEqual(q["paragraph"], 1)
            self.assertLessEqual(q["paragraph"], len(article["essay"]))

    def test_routine_news_validation_does_not_change_site_version(self):
        html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        sw = (ROOT / "site" / "sw.js").read_text(encoding="utf-8")
        self.assertIn('id="site-version" class="site-version" aria-label="網站版本">S2', html)
        self.assertIn('app.js?v=s2-1', html)
        self.assertIn('ai-daily-S2-1-reading', sw)

if __name__ == "__main__":
    unittest.main()

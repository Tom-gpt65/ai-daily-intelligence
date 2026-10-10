"""No-network, all-day guarantee regression checks."""
from __future__ import annotations
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from reading_backup import build_reading
from morning_canary import assert_valid_reserve, test_future_publication as verify_future_publication
from edition_guarantee import article_words,fill_dictionary,complete

class DailyGuaranteeTests(unittest.TestCase):
    def test_source_citations_are_not_clickable_dictionary_words(self):
        self.assertEqual(article_words(["An AI report [S1] contains evidence."]),
                         {"an","ai","report","contains","evidence"})

    def test_untranslated_words_are_rejected(self):
        paragraphs=["An inventedwordthatdoesnotexist is not in our offline dictionary."]
        vocab,missing=fill_dictionary(paragraphs,{})
        self.assertIn("inventedwordthatdoesnotexist",missing)
        self.assertNotIn("inventedwordthatdoesnotexist",vocab)

    def test_all_possible_reserve_topics_have_chinese_meanings(self):
        bank=json.loads((ROOT/"site"/"reading-library.json").read_text(encoding="utf-8"))
        paragraphs=[bank["intro"],*bank["topics"],bank["conclusion"]]
        dictionary,missing=fill_dictionary(paragraphs,{})
        self.assertEqual(missing,[])
        self.assertGreaterEqual(len(article_words(paragraphs)),450)
        self.assertTrue(complete({"essay":paragraphs,"dictionary":dictionary}))

    def test_every_day_has_complete_1000_word_education_fallback(self):
        first=datetime(2026,10,10,tzinfo=timezone.utc)
        fingerprints=set()
        for i in range(24):
            date=(first+timedelta(days=i)).date().isoformat()
            edition=build_reading(date,first+timedelta(days=i))
            with self.subTest(date=date):
                self.assertEqual(edition["date"],date)
                self.assertEqual(edition["mode"],"reading_feature")
                self.assertEqual(edition["stories"],[])
                self.assertGreaterEqual(edition["word_count"],1000)
                self.assertEqual(len(edition["practice"]["items"]),7)
                self.assertTrue(complete(edition))
                self.assertFalse(edition["demo"])
                self.assertIn("Not today's AI news",edition["subtitle"])
                fingerprints.add("\n".join(edition["essay"]))
        self.assertGreaterEqual(len(fingerprints),12)

    def test_reserve_topics_are_diverse_and_headlines_are_grounded(self):
        bank=json.loads((ROOT/"site"/"reading-library.json").read_text(encoding="utf-8"))
        self.assertEqual(len(bank["topics"]),24)
        self.assertEqual(len(bank["titles"]),24)
        days=[(datetime(2026,10,10,tzinfo=timezone.utc)+timedelta(days=i)).date().isoformat() for i in range(40)]
        previous=None
        for date in days:
            edition=build_reading(date)
            body=edition["essay"][1:-1]
            self.assertEqual(len(body),10)
            self.assertEqual(len(set(body)),10)
            self.assertIn(edition["headline"].removeprefix("AI literacy: "),bank["titles"])
            if previous is not None:
                self.assertFalse(set(body)&set(previous),date+" repeated yesterday's paragraphs")
            previous=body
    def test_every_word_has_exact_surface_lookup(self):
        edition=build_reading("2026-10-10")
        for word in article_words(edition["essay"]):
            self.assertTrue(edition["dictionary"][word]["translation"])

    def test_publish_workflow_always_checks_fallback(self):
        daily=(ROOT/".github/workflows/daily.yml").read_text(encoding="utf-8")
        morning=(ROOT/".github/workflows/early-reading.yml").read_text(encoding="utf-8")
        self.assertIn("reading_backup.py --if-missing",daily)
        self.assertIn("reading_backup.py --if-missing",morning)
        self.assertIn("cron: '5 7 * * *'",morning)

    def test_first_attempt_canary_simulates_actual_future_publication(self):
        # Critical incident regression: the day after a published news digest,
        # the very first item is legitimately a reading_feature. Test the
        # exact same validator used by the 07:40 news pipeline.
        days=verify_future_publication("2026-10-10")
        self.assertEqual(days,["2026-10-10","2026-10-11","2026-10-12",
                               "2026-10-17","2026-11-09"])

    def test_first_attempt_canary_never_fakes_news(self):
        day="2026-10-11"
        valid=build_reading(day)
        assert_valid_reserve(valid,day)
        with self.assertRaises(ValueError):
            assert_valid_reserve({**valid,"mode":"source_digest"},day)
        with self.assertRaises(ValueError):
            assert_valid_reserve({**valid,"stories":[{"id":"S1"}]},day)
        with self.assertRaises(ValueError):
            assert_valid_reserve({**valid,"subtitle":"Breaking AI news"},day)
        with self.assertRaises(ValueError):
            assert_valid_reserve({**valid,"dictionary":{}},day)

    def test_first_run_uses_safe_fallback_after_transient_external_failures(self):
        daily=(ROOT/".github/workflows/daily.yml").read_text(encoding="utf-8")
        early=(ROOT/".github/workflows/early-reading.yml").read_text(encoding="utf-8")
        morning=(ROOT/".github/workflows/first-attempt-canary.yml").read_text(encoding="utf-8")
        self.assertIn("cron: '25 6 * * *'",morning)
        self.assertIn("timezone: 'Asia/Hong_Kong'",morning)
        self.assertIn("python scripts/morning_canary.py",morning)
        self.assertEqual(daily.count("continue-on-error: true"),2,
                         "External feed/build failures must not prevent the reserve")
        self.assertIn("always() && github.event_name != 'push' && steps.site-preflight.outcome == 'success'",daily)
        self.assertIn("Validate FINAL dated article before publishing",daily)
        self.assertIn("python scripts/validate_site.py",daily)
        self.assertIn("Re-validate actual morning edition before publication",early)

    def test_publication_checks_validate_real_articles_not_mutable_unit_fixtures(self):
        # Production is a runtime pipeline, not a CI runner. A 07:05 reserve
        # is an expected valid state; the full test suite runs in CI.
        for name in ("daily.yml","early-reading.yml"):
            with self.subTest(workflow=name):
                workflow=(ROOT/".github/workflows"/name).read_text(encoding="utf-8")
                self.assertIn("python scripts/validate_site.py",workflow)
                self.assertIn("node --check site/app.js",workflow)
                self.assertIn("node --check site/sw.js",workflow)
                self.assertNotIn("python -m unittest discover",workflow,
                    "Full regression tests must not block daily publishing")
        ci=(ROOT/".github/workflows/longform-validation.yml").read_text(encoding="utf-8")
        self.assertIn("python -m unittest discover -s tests -v",ci)
        self.assertIn(".github/workflows/daily.yml",ci)
        self.assertIn(".github/workflows/early-reading.yml",ci)

if __name__=="__main__":unittest.main()

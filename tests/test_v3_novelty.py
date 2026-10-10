"""V3 regression: copied longform is not a fresh daily editorial edition."""
import copy
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))

from content_novelty import audit, overlap, long_repeats, STYLES
from longform import compose_briefing, WRITING_STYLES
from morning_canary import canary_sources


def prior(day):
    return json.loads((ROOT/"site/reports"/(day+".json")).read_text(encoding="utf-8"))


class V3OriginalityTests(unittest.TestCase):
    def test_identifies_actual_october_9_10_recycled_copy(self):
        before=prior("2026-10-09")
        after=copy.deepcopy(prior("2026-10-10"))
        self.assertEqual(before["headline"],after["headline"])
        self.assertEqual(long_repeats(before["essay"],after["essay"]),3)
        self.assertGreater(overlap(before["essay"],after["essay"]),0.60)
        after["writing_style"]=STYLES[0]
        state=audit(after,[before])
        self.assertFalse(state["pass"])
        self.assertIn("excessive_cross_day_prose_overlap",state["issues"])

    def test_rejects_cosmetically_new_title_and_date_on_copied_article(self):
        before=prior("2026-10-10")
        after=copy.deepcopy(before)
        after["date"]="2026-10-11"
        after["headline"]="New day but no new content or argument"
        after["writing_style"]=STYLES[0]
        state=audit(after,[before])
        self.assertFalse(state["pass"])
        self.assertIn("repeated_introduction_from_2026-10-10",state["issues"])
        self.assertIn("repeated_conclusion_from_2026-10-10",state["issues"])

    def test_v3_writing_style_cycle_is_distinct_for_consecutive_days(self):
        start=datetime(2026,10,11,tzinfo=timezone.utc)
        designs=[WRITING_STYLES[(start.date().toordinal()+delta)%len(WRITING_STYLES)][0]
                 for delta in range(4)]
        self.assertEqual(len(set(designs)),4)

    def test_every_daily_narrative_has_source_links_and_new_lead_and_ending(self):
        start=datetime(2026,10,11,tzinfo=timezone.utc)
        news=canary_sources(start)
        first=compose_briefing(news,day="2026-10-11")
        second=compose_briefing(news,day="2026-10-12")
        self.assertNotEqual(first[0],second[0])
        self.assertNotEqual(first[-1],second[-1])
        self.assertEqual(len(first),len(second))
        self.assertGreaterEqual(len(first),8)
        for essay in (first,second):
            for source in news:
                self.assertIn("["+source["id"]+"]"," ".join(essay))
        # The generator alone cannot guarantee uniqueness when the same
        # sources recur; the publisher additionally checks all recent reports.
        self.assertTrue(overlap(first,second)<1)

    def test_same_style_or_fake_new_sources_are_rejected(self):
        original=prior("2026-10-10")
        first=copy.deepcopy(original)
        first["date"]="2026-10-11"
        first["headline"]="Daily distinct heading one"
        first["writing_style"]="comparative_study"
        second=copy.deepcopy(original)
        second["date"]="2026-10-12"
        second["headline"]="Another distinct daily heading"
        second["writing_style"]="comparative_study"
        result=audit(second,[first])
        self.assertFalse(result["pass"])
        self.assertIn("recently_reused_writing_style",result["issues"])
        self.assertIn("reused_news_sources_from_2026-10-11",result["issues"])

    def test_identical_five_word_fragments_without_full_paragraph_are_measured(self):
        first=["Evidence and practical reports are important for informed judgement."]*8
        second=["Evidence and practical reports are important for informed judgement today."]*8
        self.assertGreater(overlap(first,second),0.5)
        self.assertEqual(long_repeats(first,second),0)


if __name__=="__main__":
    unittest.main()

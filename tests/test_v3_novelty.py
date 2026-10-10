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


def legacy_duplicate(day):
    """Immutable evidence from V2, independent of subsequently rebuilt live reports."""
    fixture=json.loads((ROOT/"tests/fixtures/v2-repeated-2026-10-09-10.json").read_text(encoding="utf-8"))
    return fixture["previous" if day=="2026-10-09" else "following"]


class V3OriginalityTests(unittest.TestCase):
    def test_identifies_actual_october_9_10_recycled_copy(self):
        before=legacy_duplicate("2026-10-09")
        after=copy.deepcopy(legacy_duplicate("2026-10-10"))
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
        self.assertNotEqual(len(first),len(second),
                            "Two consecutive V3 narrative designs need genuinely different paragraph counts")
        self.assertGreaterEqual(len(first),8)
        self.assertGreaterEqual(len(second),8)
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

    def test_next_day_must_be_distinct_or_explicitly_rejected(self):
        # A stricter 16% novelty gate is allowed to reject a second day's
        # similar RSS snapshots; a fabricated "new" edition is NOT allowed.
        import shutil
        import tempfile
        import build
        import validate_site
        with tempfile.TemporaryDirectory(prefix="v3-cross-day-") as name:
            dest=Path(name)/"site"
            shutil.copytree(ROOT/"site",dest)
            saved=(build.REPORTS,build.STATUS_PATH,validate_site.SITE)
            try:
                build.REPORTS=dest/"reports"
                build.STATUS_PATH=dest/"system-status.json"
                validate_site.SITE=dest
                reports=[]
                for number,day in enumerate(("2026-10-11","2026-10-12")):
                    now=datetime.fromisoformat(day+"T07:40:00+08:00")
                    rows=canary_sources(now)
                    if number:
                        for i,row in enumerate(rows):
                            row["url"]+="?edition=2026-10-12-"+str(i)
                            row["title"]=(
                                "AI security scanners for open-source projects",
                                "AI robotics evaluation under practical conditions",
                                "AI governance policy for responsible use",
                            )[i]
                            parts=row["excerpt"].split(". ")
                            row["excerpt"]=". ".join(parts[1:]+parts[:1])
                    result=build.build_live(now,None,sources=rows)
                    if not result:
                        state=json.loads(build.STATUS_PATH.read_text(encoding="utf-8"))
                        self.assertEqual(state["state"],"repetitive_content",
                                         "Only proven repetitiveness permits novelty rejection")
                        self.assertTrue(state.get("novelty_issues"))
                        self.assertEqual(number,1,
                                         "The first day must produce the source-grounded article")
                        self.assertFalse((dest/"reports"/(day+".json")).exists())
                        break
                    report=json.loads((build.REPORTS/(day+".json")).read_text("utf-8"))
                    self.assertEqual(report.get("validation_profile"),"s1")
                    self.assertTrue(report.get("novelty",{}).get("pass"))
                    self.assertLess(report["novelty"]["max_overlap"],0.16)
                    self.assertEqual(validate_site.validate(),[])
                    reports.append(report)
                self.assertTrue(reports)
                if len(reports)==2:
                    self.assertNotEqual(reports[0]["headline"],reports[1]["headline"])
                    self.assertNotEqual(reports[0]["essay"][0],reports[1]["essay"][0])
                    self.assertNotEqual(reports[0]["essay"][-1],reports[1]["essay"][-1])
                    self.assertNotEqual(reports[0]["writing_style"],reports[1]["writing_style"])
                    self.assertLess(overlap(reports[0]["essay"],reports[1]["essay"]),0.16)
            finally:
                build.REPORTS,build.STATUS_PATH,validate_site.SITE=saved

    def test_identical_five_word_fragments_without_full_paragraph_are_measured(self):
        first=["Evidence and practical reports are important for informed judgement."]*8
        second=["Evidence and practical reports are important for informed judgement today."]*8
        self.assertGreater(overlap(first,second),0.5)
        self.assertEqual(long_repeats(first,second),0)


if __name__=="__main__":
    unittest.main()

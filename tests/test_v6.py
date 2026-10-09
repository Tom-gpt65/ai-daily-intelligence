"""Student-centred regression tests. No paid API or HKEAA endorsement."""
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import dse_editorial

class DseStudentTests(unittest.TestCase):
    def setUp(self):
        self.sources=[dict(id=f"S{i}",publisher=f"Publisher {i}",
                           title="AI policy and practical safeguards",
                           excerpt="A short report describes the announced development and its limitations")
                      for i in range(1,6)]
    def test_fallback_has_no_repetitive_attribution_openings(self):
        paragraphs=dse_editorial.compose_briefing(self.sources)
        self.assertFalse(any(p.startswith("According to") for p in paragraphs))
        count=dse_editorial.word_count(" ".join(paragraphs))
        self.assertGreaterEqual(count,1000)
        self.assertLessEqual(count,1550)
    def test_five_sources_remain_cited_after_compaction(self):
        paragraphs=dse_editorial.compose_briefing(self.sources)
        self.assertLessEqual(dse_editorial.word_count(" ".join(paragraphs)),1550)
        for story in self.sources:
            self.assertIn("["+story["id"]+"]"," ".join(paragraphs))
    def test_three_source_mode_still_has_substantive_paper(self):
        text=" ".join(dse_editorial.compose_briefing(self.sources[:3]))
        self.assertGreaterEqual(dse_editorial.word_count(text),1000)
        self.assertIn("evidence",text)
    def test_dse_mc_answer_keys_and_written_marking(self):
        booklet=dse_editorial.make_practice(self.sources)
        self.assertFalse(booklet["official"])
        self.assertEqual(7,len(booklet["items"]))
        self.assertEqual(12,sum(q["marks"] for q in booklet["items"]))
        self.assertEqual(4,sum(q["type"]=="mc" for q in booklet["items"]))
        for question in booklet["items"]:
            self.assertTrue(question["evidence"])
            if question["type"]=="mc":
                self.assertGreaterEqual(question["answer"],0)
                self.assertLess(question["answer"],len(question["options"]))
                self.assertTrue(question["explanation"])
            else:self.assertTrue(question["guidance"])
    def test_public_article_is_educational_not_certified(self):
        index=json.loads((ROOT/"site/reports/index.json").read_text(encoding="utf-8"))
        report=json.loads((ROOT/"site/reports"/(index[0]["date"]+".json")).read_text(encoding="utf-8"))
        self.assertIn(report["mode"],("source_digest","editorial"))
        self.assertFalse(report["demo"])
        self.assertTrue(report.get("practice"))
        self.assertGreaterEqual(len(report["practice"]["items"]),3)
        if report["mode"]=="source_digest":
            self.assertEqual(7,len(report["practice"]["items"]))
        self.assertTrue(report["stories"])
    def test_iphone_support_present(self):
        html=(ROOT/"site/index.html").read_text(encoding="utf-8")
        css=(ROOT/"site/v6.css").read_text(encoding="utf-8")
        js=(ROOT/"site/app.js").read_text(encoding="utf-8")
        self.assertIn("id=\"tools-toggle\"",html)
        self.assertIn("./v6.css",html)
        self.assertIn("max-height:min(62dvh,530px)",css)
        self.assertIn("toggleWholeTranslation",js)
        self.assertIn("mymemory.translated.net",js)
        self.assertIn("quizSelections",js)
    def test_no_paid_ai_api_dependencies(self):
        flow=(ROOT/".github/workflows/daily.yml").read_text(encoding="utf-8")
        self.assertIn("cron: '40 7 * * *'",flow)
        self.assertNotIn("OPENAI_API_KEY",flow)
        self.assertIn("ollama pull phi3:mini",flow)

if __name__=="__main__":unittest.main()

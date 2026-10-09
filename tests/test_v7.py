"""V7: prove that DSE exercises derive from each specific edition, not static quizzes."""
from __future__ import annotations
import json
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from dse_assessment_v7 import make_exam

class DSEV7Tests(unittest.TestCase):
    def setUp(self):
        self.essay=[
            "The evidence behind any AI announcement requires critical scrutiny; a provisional judgement may change if new information emerges.",
            "Although the promise is considerable, Publisher One reports a model assessment in its article [S1], and the available evidence remains incomplete.",
            "Publisher Two discusses a policy decision in its report [S2], yet the intended benefits still require independent review.",
            "Publisher Three has reported an engineering milestone in [S3], but the impact on daily work is not established.",
            "The comparison suggests that commercial ambitions and public safeguards differ, and it would be premature to treat them as identical.",
            "Any conclusion should remain open to fresh evidence rather than treating uncertainty as proof of failure."
        ]
        self.stories=[{"id":"S1","title":"New study on AI assessment","publisher":"Publisher One","url":"https://example.com/1"},
                      {"id":"S2","title":"Policy reform for safer AI use","publisher":"Publisher Two","url":"https://example.com/2"},
                      {"id":"S3","title":"AI hardware milestone","publisher":"Publisher Three","url":"https://example.com/3"}]
    def test_all_items_specific_and_evidence_anchored(self):
        book=make_exam(self.essay,self.stories,"2026-10-09")
        self.assertFalse(book["official"])
        self.assertEqual(7,len(book["items"]))
        self.assertEqual(13,sum(x["marks"] for x in book["items"]))
        for item in book["items"]:
            self.assertGreaterEqual(item["paragraph"],1)
            self.assertLessEqual(item["paragraph"],len(self.essay))
            self.assertTrue(item["evidence_quote"])
            self.assertTrue(item["evidence"])
            self.assertIn(item["evidence_quote"][:40].lower(),self.essay[item["paragraph"]-1].lower())
            if item["type"]=="mc":
                self.assertEqual(4,len(item["options"]))
                self.assertEqual(len(set(item["options"])),4)
                self.assertTrue(0<=item["answer"]<=3)
                self.assertTrue(item["explanation"])
            else:
                self.assertTrue(item["guidance"])
    def test_cross_source_questions_use_todays_specific_news_titles(self):
        book=make_exam(self.essay,self.stories,"2026-10-09")
        comparison=book["items"][3]
        extended=book["items"][-1]
        import re
        cited_ids=set(re.findall(r"\[(S\d+)\]",comparison["stem"]))
        self.assertEqual(len(cited_ids),2)
        source_by_id={source["id"]:source for source in self.stories}
        for source_id in cited_ids:
            self.assertIn(source_by_id[source_id]["title"],comparison["stem"])
        self.assertNotEqual(*sorted(cited_ids))
        self.assertIn("80–120 words",extended["stem"])
        self.assertFalse(book["official"])

    def test_cross_source_questions_cover_distinct_news(self):
        paragraphs=[
            "The opening argues that a cautious interpretation needs different sources of evidence.",
            "Investment announcements describe financial expectations [S1] but do not demonstrate technical reliability.",
            "The research paper [S2] presents evaluation methods, which require replication and clear limitations.",
            "A computer release [S3] concerns hardware specifications and value to users.",
            "A policy change [S4] concerns accountability, implementation and institutional oversight.",
            "Finally, investment, research, hardware and governance cannot be judged by interchangeable standards."
        ]
        sources=[
            {"id":"S1","title":"AI funding","publisher":"Finance","topic":"Investment"},
            {"id":"S2","title":"Agent benchmark","publisher":"Journal","topic":"Research"},
            {"id":"S3","title":"AI computers","publisher":"Technology","topic":"Hardware"},
            {"id":"S4","title":"AI governance rules","publisher":"Policy","topic":"Governance"}
        ]
        practice=make_exam(paragraphs,sources,"2026-10-09")
        items={q["id"]:q for q in practice["items"]}
        import re
        ids4=set(re.findall(r"\[(S\d+)\]",items["Q4"]["stem"]))
        ids7=set(re.findall(r"\[(S\d+)\]",items["Q7"]["stem"]))
        self.assertEqual(len(ids4),2)
        self.assertEqual(len(ids7),2)
        self.assertEqual(ids4 | ids7,{"S1","S2","S3","S4"})
        for question in (items["Q4"],items["Q7"]):
            self.assertIn(question["evidence_quote"].split(" / ")[0][:40],
                          paragraphs[question["paragraph"]-1])

    def test_daily_shuffle_prevents_fixed_answer_key(self):
        keys=[make_exam(self.essay,self.stories,f"2026-10-{day:02d}")["items"][0]["answer"] for day in range(9,20)]
        self.assertGreater(len(set(keys)),1)
    def test_do_not_fake_mc_knowledge_where_support_absent(self):
        essay=["A discussion of institutional choices and long-term interests.",
               "A technical commentary [S1] examines a practical issue.",
               "Another author [S2] explores different considerations.",
               "The comparison is open to interpretation."]
        book=make_exam(essay,self.stories[:2],"2026-10-09")
        self.assertEqual(7,len(book["items"]))
        self.assertFalse(any(x["type"]=="mc" for x in book["items"] if x["id"] in ("Q1","Q2","Q3")))
    def test_actual_published_article_generates_grounded_exercise(self):
        index=json.loads((ROOT/"site/reports/index.json").read_text(encoding="utf-8"))
        report=json.loads((ROOT/"site/reports"/(index[0]["date"]+".json")).read_text(encoding="utf-8"))
        book=make_exam(report["essay"],report["stories"],report["date"])
        self.assertEqual(7,len(book["items"]))
        self.assertTrue(any(item["type"]=="extended" for item in book["items"]))
    def test_v7_reader_supports_question_evidence_and_translation_recovery(self):
        js=(ROOT/"site/app.js").read_text(encoding="utf-8")
        self.assertIn("translationProgress",js)
        self.assertIn("translateOneParagraph",js)
        self.assertIn("translationCancel",js)
        self.assertIn("evidence-jump",js)
        self.assertIn("submittedAt",js)
        self.assertIn("quizSelections",js)
    def test_one_model_edition_still_gets_full_practice(self):
        editorial="".join(self.essay)
        self.assertTrue(editorial)
        self.assertEqual(7,len(make_exam(self.essay,self.stories,"2026-10-12")["items"]))

if __name__=="__main__": unittest.main()

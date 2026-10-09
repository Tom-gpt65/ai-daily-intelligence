"""Daily publication consistency and examination practice evidence gates."""
import json
import pathlib
import re
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
REPORTS=ROOT/"site"/"reports"


class EditorialIntegrityTests(unittest.TestCase):
    def test_all_report_index_entries_match_published_articles(self):
        index=json.loads((REPORTS/"index.json").read_text(encoding="utf-8"))
        self.assertTrue(index)
        for entry in index:
            article=json.loads((REPORTS/(entry["date"]+".json")).read_text(encoding="utf-8"))
            with self.subTest(date=entry["date"]):
                self.assertEqual(entry["date"],article["date"])
                self.assertEqual(entry["word_count"],article["word_count"])
                self.assertEqual(entry["headline"],article["headline"])
                self.assertEqual(entry["mode"],article["mode"])
                self.assertEqual(entry["stories"],len(article["stories"]))

    def test_english_word_count_is_not_fake(self):
        index=json.loads((REPORTS/"index.json").read_text(encoding="utf-8"))
        for entry in index:
            article=json.loads((REPORTS/(entry["date"]+".json")).read_text(encoding="utf-8"))
            measured=len(re.findall(r"\b[A-Za-z]+(?:['’-][A-Za-z]+)*\b"," ".join(article["essay"])))
            self.assertEqual(measured,article["word_count"])

    def test_answer_evidence_paragraphs_exist(self):
        index=json.loads((REPORTS/"index.json").read_text(encoding="utf-8"))
        article=json.loads((REPORTS/(index[0]["date"]+".json")).read_text(encoding="utf-8"))
        paragraph_count=len(article["essay"])
        ids={s.get("id") for s in article["stories"]}
        for item in article.get("practice",{}).get("items",[]):
            with self.subTest(question=item.get("id")):
                self.assertTrue(item.get("evidence"))
                if item.get("paragraph"):
                    self.assertTrue(1<=item["paragraph"]<=paragraph_count)
                for cited in re.findall(r"\[(S\d+)\]",item.get("stem","")):
                    self.assertIn(cited,ids)
                if item.get("type")=="mc":
                    self.assertTrue(0<=item["answer"]<len(item["options"]))
                    self.assertEqual(len(set(item["options"])),len(item["options"]))

    def test_official_exam_status_is_not_misrepresented(self):
        index=json.loads((REPORTS/"index.json").read_text(encoding="utf-8"))
        article=json.loads((REPORTS/(index[0]["date"]+".json")).read_text(encoding="utf-8"))
        self.assertFalse(article.get("practice",{}).get("official",True))


if __name__=="__main__":
    unittest.main()

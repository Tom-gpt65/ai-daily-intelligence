"""Regression tests for curated offline Traditional Chinese word lookup."""
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from build import make_vocabulary, word_forms


class OfflineVocabularyTests(unittest.TestCase):
    def test_concerns_can_be_stemmed_to_concern(self):
        self.assertIn("concern",word_forms("concerns"))

    def test_curated_glossary_is_valid(self):
        data=json.loads((ROOT/"site"/"offline-glossary.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data),150)
        self.assertTrue(all(isinstance(k,str) and isinstance(v,str) and v.strip() for k,v in data.items()))
        self.assertIn("關乎",data["concern"])

    def test_no_download_is_needed_to_translate_concerns(self):
        vocab=make_vocabulary("A funding round concerns expectations about future value.",None)
        self.assertIn("concern",vocab)
        self.assertIn("關乎",vocab["concern"]["translation"])
        self.assertIn("expectation",vocab)
        self.assertIn("future",vocab)
        self.assertIn("value",vocab)

    def test_existing_saved_word_storage_keys_are_unchanged(self):
        code=(ROOT/"site"/"app.js").read_text(encoding="utf-8")
        self.assertIn("'ai-daily-saved-v2'",code)
        self.assertIn("'ai-daily-reading-progress-v1'",code)
        self.assertIn("'ai-daily-answers-v1'",code)
        self.assertIn("preloadOfflineGlossary",code)

if __name__=="__main__":
    unittest.main()

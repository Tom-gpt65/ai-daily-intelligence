"""Measurable quality gates without claiming educational or factual certification."""
import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from editorial_quality import inspect,repeated_paragraph_similarity,contains_machine_artifacts


class EditorialQualityTests(unittest.TestCase):
    def setUp(self):
        self.sources=[{"id":f"S{i}","title":f"Independent AI development {i}"} for i in range(1,4)]
        self.paras=[
            ("Although the initiative is described as promising, its operational implications cannot be "
             "inferred without understanding the circumstances under which it was evaluated. ")*2+" [S1]",
            ("The first report examines a proposed AI security tool, while the second discusses "
             "how institutions assess the risks arising from automated systems. ")*3+" [S2]",
            ("If developers were to make the technology widely available, they would still need "
             "to demonstrate that observed improvements persist when the environment changes. ")*3+" [S3]",
            ("This distinction is important because a public announcement provides information "
             "about the organisation's stated intentions but not a controlled measure of its outcomes. ")*3,
            ("Taken together, the three sources provide contrasting perspectives on adoption, oversight and "
             "technical reliability, none of which should be confused with an independent factual audit. ")*3,
            ("Readers who weigh counterarguments carefully develop a stronger ability to distinguish inference "
             "from the claims documented in the original source material. ")*2
        ]
    def test_usable_feature_has_source_anchors(self):
        result=inspect(self.paras,self.sources)
        self.assertEqual(result["diagnostics"]["cited_sources"],3)
        self.assertEqual(result["diagnostics"]["source_linked_paragraphs"],3)
    def test_repeated_generic_news_fails_quality_gate(self):
        paras=["According to [S1], more evidence is needed. "*35,
               "According to [S2], more evidence is needed. "*35,
               "According to [S3], more evidence is needed. "*35]
        result=inspect(paras,self.sources)
        self.assertFalse(result["training_structure_pass"])
        self.assertIn("repetitive_paragraph_openings",result["issues"])
    def test_missing_evidence_cannot_pass_as_full_feature(self):
        paras=["Technological change has many possible implications. "*20]*6
        result=inspect(paras,self.sources)
        self.assertIn("insufficient_explicit_source_attribution",result["issues"])
        self.assertFalse(result["training_structure_pass"])
    def test_detects_copy_paste_padding_despite_different_citation_ids(self):
        core=("A technical announcement can describe an ambition without demonstrating the practical "
              "outcome. Readers should examine the evidence, consider alternative interpretations, "
              "distinguish speculation from empirical testing and identify unresolved limitations. ")*3
        first=core+" [S1]"
        second=core+" [S2]"
        self.assertGreaterEqual(repeated_paragraph_similarity([first,second]),0.68)
        article=[first,second,core+" [S3]",core,core,core]
        result=inspect(article,self.sources)
        self.assertIn("near_duplicate_paragraph_padding",result["issues"])
        self.assertFalse(result["training_structure_pass"])
    def test_distinct_source_paragraphs_do_not_false_positive(self):
        a="Research methods can be evaluated against established comparison criteria. "*13
        b="Investment decisions signal expectations without determining future commercial performance. "*13
        self.assertLess(repeated_paragraph_similarity([a,b]),0.68)
    def test_prompt_and_feed_artifacts_never_become_reading_text(self):
        for fragment in ("arXiv:2610.1234v1 Announce Type: new Abstract: text",
                         "As an AI language model, I cannot",
                         "A broken replacement character \uFFFD appears"):
            with self.subTest(fragment=fragment):
                self.assertTrue(contains_machine_artifacts(fragment))
                report=self.paras.copy()
                report[0]+=fragment
                self.assertIn("machine_text_artifact",inspect(report,self.sources)["issues"])
        self.assertFalse(contains_machine_artifacts("A carefully attributed arXiv paper can still be discussed in normal prose."))
    def test_diagnostics_not_hkeaa_level_claim(self):
        result=inspect(self.paras,self.sources)
        self.assertIn("not independent fact-checking",result["notice"])
        self.assertIn("not",result["notice"].lower())


if __name__=="__main__":unittest.main()

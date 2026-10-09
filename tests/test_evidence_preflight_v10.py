"""Free-source adequacy gates, checked before expensive local inference."""
import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build import source_evidence_metrics,choose_vocab

class EvidencePreflightTests(unittest.TestCase):
    def test_three_headlines_are_not_a_thousand_word_news_briefing(self):
        sources=[{'title':'An exceptionally detailed AI research headline on a new model',
                  'excerpt':''} for _ in range(3)]
        result=source_evidence_metrics(sources)
        self.assertFalse(result['sufficient'])
        self.assertEqual(result['detailed_sources'],0)

    def test_two_long_sources_and_one_short_source_can_provide_context(self):
        long=('Research teams describe a proposed framework and specific evaluation '
              'procedures under comparable operational conditions, highlighting '
              'limitations and unresolved assumptions about performance. ')
        sources=[
            {'title':'An AI agent research evaluation is proposed','excerpt':long},
            {'title':'AI developers introduce an industry policy','excerpt':long},
            {'title':'Technology hardware changes in AI','excerpt':'Short notice.'},
        ]
        result=source_evidence_metrics(sources)
        self.assertTrue(result['sufficient'],result)
        self.assertEqual(result['detailed_sources'],2)

    def test_one_extremely_long_source_cannot_replace_independent_anchors(self):
        sources=[
            {'title':'AI research evaluation','excerpt':'This technical claim has further details. '*50},
            {'title':'AI launch','excerpt':'Short.'},
            {'title':'AI hardware','excerpt':'Short.'},
        ]
        self.assertFalse(source_evidence_metrics(sources)['sufficient'])

    def test_vocab_spotlight_prioritises_advanced_words_present_in_current_text(self):
        dictionary={'innovation':{},'scrutiny':{},'accountability':{},
                    'extrapolation':{},'reproducibility':{}}
        choices=choose_vocab(dictionary)
        self.assertEqual(choices[0],'extrapolation')
        self.assertEqual(choices[1],'reproducibility')
        self.assertEqual(len(choices),len(set(choices)))
        self.assertTrue(set(choices).issubset(dictionary))
    def test_scheduled_workflow_uses_the_same_evidence_rule(self):
        workflow=(ROOT/'.github/workflows/daily.yml').read_text(encoding='utf-8')
        self.assertIn('from build import source_evidence_metrics',workflow)
        self.assertIn("evidence['sufficient']",workflow)
        self.assertIn("steps.preflight.outputs.enough == 'true'",workflow)

if __name__=='__main__':unittest.main()

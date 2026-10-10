"""Free long-form DSE training invariants for daily editions."""
import pathlib,sys,unittest,json
from datetime import datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from longform import compose_briefing,word_count,sourced_detail,attributed_excerpt
from editorial_quality import inspect

def story(i,kind):
    title={'investment':'AI funding round announced',
           'research':'New framework for evaluating AI agents',
           'hardware':'New AI laptop is released',
           'governance':'Institution revises AI usage policy',
           'bioscience':'AI research in biology'}[kind]
    return {'id':f'S{i}','publisher':f'Publisher {i}','title':title,
            'topic':kind,'excerpt':'Public description highlights an important new development.'}

class LongFormTests(unittest.TestCase):
    def test_three_to_five_substantial_distinct_contexts_support_long_reading(self):
        from morning_canary import canary_sources
        for count in (3,4,5):
            with self.subTest(count=count):
                data=(canary_sources(datetime.fromisoformat('2026-10-11T07:40:00+08:00')) if count==3 else
                      json.loads((ROOT/'site/reports/2026-10-09.json').read_text('utf-8'))['stories'][:count])
                essay=compose_briefing(data)
                self.assertGreaterEqual(word_count(' '.join(essay)),1000)
                self.assertLessEqual(word_count(' '.join(essay)),1550)
                checked=inspect(essay,data)
                blockers={'article_length_outside_training_target','near_duplicate_paragraph_padding','insufficient_explicit_source_attribution','insufficient_event_specific_paragraphs'}
                self.assertFalse(blockers.intersection(checked['issues']),checked['issues'])
                self.assertGreaterEqual(len(essay),8)
                for item in data:self.assertIn('['+item['id']+']',' '.join(essay))
    def test_security_robotics_and_general_ai_classification(self):
        from longform import category
        cases=[
            ("Anthropic launches free AI security scans for open-source projects","General AI","security"),
            ("AI breakthroughs in robotics","Research","robotics"),
            ("A study of biology and protein research","Research","bioscience"),
            ("How AI agent benchmarks are evaluated","Research","research"),
            ("General AI tools for writing","General AI","technology"),
        ]
        for title,topic,expected in cases:
            with self.subTest(title=title):
                self.assertEqual(category({"title":title,"topic":topic}),expected)
    def test_factual_alignment_for_security_and_robotics(self):
        from longform import compose_briefing
        examples=[
            {"id":"S1","publisher":"One","title":"Security scanner for open-source projects","topic":"General AI","excerpt":"The provider describes a service for finding potential security issues in open-source projects."},
            {"id":"S2","publisher":"Two","title":"A new research framework and benchmark","topic":"Research","excerpt":"Researchers evaluate a benchmark for comparing language models and methods."},
            {"id":"S3","publisher":"Three","title":"Progress in robotics","topic":"Research","excerpt":"A report discusses how robots move from research into practical conditions."}
        ]
        text=compose_briefing(examples)
        self.assertIn("Software security",text[1])
        self.assertNotIn("biological sequence",text[1])
        self.assertIn("Robotics research",next(p for p in text if '[S3]' in p))
        self.assertIn("software security"," ".join(text))
    def test_just_two_news_items_cannot_be_padded_into_a_fake_feature(self):
        self.assertEqual(compose_briefing([story(1,'research'),story(2,'investment')]),[])
    def test_identical_topics_are_rejected_instead_of_padding_a_feature(self):
        data=[story(i,'research') for i in range(1,6)]
        essay=compose_briefing(data)
        self.assertEqual(essay,[])
    def test_source_specific_rss_quotation_is_attributed_and_bounded(self):
        source={"excerpt":"Researchers describe the unusual data constraints involved in environmental AI "
                          "evaluation and explain how the fixed testing interface can support "
                          "comparisons between agents before they are deployed widely."}
        extract=attributed_excerpt(source,2)
        self.assertIn("linked source",extract)
        self.assertIn("“Researchers describe",extract)
        quoted=extract.split("“",1)[1].split("”",1)[0]
        self.assertLessEqual(len(quoted.replace("…","").split()),18)
        self.assertLess(len(extract),300)
    def test_insufficient_excerpt_does_not_invent_evidence(self):
        self.assertEqual(attributed_excerpt({"excerpt":"New AI."}),"")
    def test_no_generic_padding_claims_fact_checking(self):
        sample=json.loads((ROOT/'site/reports/2026-10-09.json').read_text('utf-8'))['stories']
        result=" ".join(compose_briefing(sample))
        self.assertNotIn("independently verified",result)
        self.assertIn("attributed",result)
    def test_specific_rss_fact_hook_requires_matching_source_text(self):
        a={'excerpt':'Boyu Capital and IDG Capital led the funding round.'}
        self.assertIn('Boyu Capital',sourced_detail(a))
        self.assertEqual(sourced_detail({'excerpt':'AI interest is rising.'}),'')

if __name__=='__main__': unittest.main()

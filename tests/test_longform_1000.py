"""Free long-form DSE training invariants for daily editions."""
import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from longform import compose_briefing,word_count,sourced_detail,attributed_excerpt

def story(i,kind):
    title={'investment':'AI funding round announced',
           'research':'New framework for evaluating AI agents',
           'hardware':'New AI laptop is released',
           'governance':'Institution revises AI usage policy',
           'bioscience':'AI research in biology'}[kind]
    return {'id':f'S{i}','publisher':f'Publisher {i}','title':title,
            'topic':kind,'excerpt':'Public description highlights an important new development.'}

class LongFormTests(unittest.TestCase):
    def test_three_to_five_different_news_items_always_exceed_thousand_words(self):
        for count in (3,4,5):
            with self.subTest(count=count):
                data=[story(i+1,['investment','research','hardware','governance','bioscience'][i]) for i in range(count)]
                essay=compose_briefing(data)
                self.assertGreaterEqual(word_count(' '.join(essay)),1000)
                self.assertLessEqual(word_count(' '.join(essay)),1550)
                self.assertGreaterEqual(len(essay),8)
                for item in data:self.assertIn('['+item['id']+']',' '.join(essay))
    def test_just_two_news_items_cannot_be_padded_into_a_fake_feature(self):
        self.assertEqual(compose_briefing([story(1,'research'),story(2,'investment')]),[])
    def test_identical_topics_do_not_repeat_entire_analysis_paragraph(self):
        data=[story(i,'research') for i in range(1,6)]
        essay=compose_briefing(data)
        source_paragraphs=essay[1:6]
        self.assertEqual(len(set(source_paragraphs)),5)
        self.assertGreaterEqual(word_count(' '.join(essay)),1000)
    def test_source_specific_rss_quotation_is_attributed_and_bounded(self):
        source={"excerpt":"Researchers describe the unusual data constraints involved in environmental AI "
                          "evaluation and explain how the fixed testing interface can support "
                          "comparisons between agents before they are deployed widely."}
        extract=attributed_excerpt(source,2)
        self.assertIn("linked source",extract)
        self.assertIn("“Researchers describe",extract)
        quoted=extract.split("“",1)[1].split("”",1)[0]
        self.assertLessEqual(len(quoted.replace("…","").split()),18)
        self.assertIn("not independent corroboration",extract)
    def test_insufficient_excerpt_does_not_invent_evidence(self):
        self.assertEqual(attributed_excerpt({"excerpt":"New AI."}),"")
    def test_no_generic_padding_claims_fact_checking(self):
        sample=[story(i,"research") for i in range(1,6)]
        result=" ".join(compose_briefing(sample))
        self.assertNotIn("independently verified",result)
        self.assertIn("attributed",result)
    def test_specific_rss_fact_hook_requires_matching_source_text(self):
        a={'excerpt':'Boyu Capital and IDG Capital led the funding round.'}
        self.assertIn('Boyu Capital',sourced_detail(a))
        self.assertEqual(sourced_detail({'excerpt':'AI interest is rising.'}),'')

if __name__=='__main__': unittest.main()

"""Actual S1 repetition incident and regression of every acceptance boundary."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build
import repair_content_history
from content_novelty import audit,overlap,recent_articles,reused_analysis_fragments
from editorial_quality import inspect
from edition_contract import issues
from edition_guarantee import complete,fill_dictionary
from source_outline import compose
from morning_canary import canary_sources


def current(day):
    return json.loads((ROOT/'site/reports'/(day+'.json')).read_text('utf-8'))


def original(day):
    return json.loads((ROOT/'site/reports/archive-revisions/s1-original'/(day+'.json')).read_text('utf-8'))


class ContentRepairTests(unittest.TestCase):
    def test_original_incident_is_rejected_even_below_sixteen_percent(self):
        first,second=original('2026-10-09'),original('2026-10-10')
        self.assertLess(overlap(first['essay'],second['essay']),0.16)
        for old in (first,second):
            checked=inspect(old['essay'],old['stories'])
            self.assertFalse(checked['training_structure_pass'])
            self.assertIn('repeated_meaningful_sentence',checked['issues'])
            self.assertIn('premature_concluding_transition',checked['issues'])
        self.assertGreater(inspect(second['essay'],second['stories'])['diagnostics']['repeated_sixteen_word_fragments'],0)

    def test_both_repaired_editions_have_coherent_nonrepeated_source_outlines(self):
        for day in ('2026-10-09','2026-10-10'):
            report=current(day)
            self.assertEqual(report['essay'],compose(original(day)['stories']))
            self.assertEqual(report['stories'],original(day)['stories'])
            self.assertEqual(report['content_generation_profile'],'source_outline_v2')
            self.assertEqual(issues(report,reports=ROOT/'site/reports'),[])
            self.assertTrue(complete(report))
            self.assertGreaterEqual(len(report['practice']['items']),7)
            self.assertTrue(inspect(report['essay'],report['stories'])['training_structure_pass'])
            self.assertGreaterEqual(report['word_count'],1000)
            self.assertLessEqual(report['word_count'],1550)
        a,b=current('2026-10-09'),current('2026-10-10')
        self.assertLess(overlap(a['essay'],b['essay']),0.16)
        self.assertEqual(reused_analysis_fragments(a['essay'],b['essay']),0)

    def test_changing_citations_and_headlines_cannot_hide_an_intra_article_block(self):
        report=current('2026-10-10')
        essay=report['essay'][:]
        essay[2]+=' '+essay[1].split('”. ',1)[-1].replace('[S1]','[S2]')
        self.assertIn('repeated_content_fragment',inspect(essay,report['stories'])['issues'])

    def test_small_cross_day_reused_block_is_blocked_independently_of_ratio(self):
        first,second=current('2026-10-09'),copy.deepcopy(current('2026-10-10'))
        second['essay'][2]+=' '+'. '.join(first['essay'][1].split('”. ',1)[-1].split('. ',2)[:2])
        self.assertLess(overlap(second['essay'],first['essay']),0.16)
        checked=audit(second,[first])
        self.assertFalse(checked['pass'])
        self.assertIn('reused_long_analysis_fragment_from_2026-10-09',checked['issues'])

    def test_forged_saved_quality_flag_does_not_bypass_reader_contract(self):
        report=current('2026-10-10')
        report['essay'][2],report['essay'][3]=report['essay'][3],report['essay'][2]
        report['editorial_quality']['training_structure_pass']=True
        self.assertIn('source_outline_mismatch',issues(report))

    def test_reconstruction_cannot_invent_a_source_or_change_the_archive_date(self):
        report=current('2026-10-09')
        report['stories'][0]['excerpt']+=' A fact that was never in the saved snapshot.'
        self.assertIn('unproved_historical_source_revision',issues(report))
        report=current('2026-10-09')
        report['source_snapshot_date']='2026-10-10'
        self.assertIn('unproved_historical_source_revision',issues(report))

    def test_published_original_revisions_remain_in_the_sixty_day_corpus(self):
        archive=recent_articles(ROOT/'site/reports','2026-10-11')
        for day in ('2026-10-09','2026-10-10'):
            editions=[r for r in archive if r['date']==day]
            self.assertEqual(len(editions),2)
            self.assertIn(original(day)['essay'],[r['essay'] for r in editions])
            self.assertIn(current(day)['essay'],[r['essay'] for r in editions])

    def test_source_retiming_after_sixty_days_does_not_fabricate_fresh_news(self):
        with tempfile.TemporaryDirectory() as folder:
            reports=Path(folder)/'reports';reports.mkdir()
            archived=current('2026-10-09')
            (reports/'2026-10-09.json').write_text(json.dumps(archived),'utf-8')
            now=datetime.fromisoformat('2027-01-20T07:40:00+08:00')
            sources=copy.deepcopy(archived['stories'])
            for story in sources:
                story['published']=now.isoformat();story['url']+='?new_date=2027-01-20'
            with patch.object(build,'REPORTS',reports),patch.object(build,'STATUS_PATH',Path(folder)/'status.json'):
                before=(reports/'2026-10-09.json').read_bytes()
                self.assertFalse(build.build_live(now,None,sources=sources))
                state=json.loads(build.STATUS_PATH.read_text('utf-8'))
                self.assertIn('reissued_existing_source_snapshots',state['novelty_issues'])
                self.assertEqual((reports/'2026-10-09.json').read_bytes(),before)
                self.assertFalse((reports/'2027-01-20.json').exists())

    def test_two_reports_cannot_be_padded_and_identical_contexts_are_rejected(self):
        sources=canary_sources(datetime.fromisoformat('2026-10-11T07:40:00+08:00'))
        self.assertEqual(compose(sources[:2]),[])
        sources[1]['title']=sources[0]['title']+' another report'
        self.assertEqual(compose(sources),[])

    def test_possessive_definition_requires_a_known_root(self):
        glossary={"organisation":{"translation":"組織"}}
        result,missing=fill_dictionary(["organisation's mysteryentity's"],glossary)
        self.assertIn('所有格',result["organisation's"]['translation'])
        self.assertEqual(missing,["mysteryentity's"])

    def test_failed_repair_leaves_all_published_bytes_intact(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)
            shutil.copytree(ROOT/'site',target/'site')
            (target/'docs').mkdir()
            paths=[target/'site/reports'/(day+'.json') for day in ('2026-10-09','2026-10-10','index')]
            before={p:p.read_bytes() for p in paths}
            with patch.object(build,'build_live',return_value=False):
                with self.assertRaises(ValueError):
                    repair_content_history.repair(target,apply=True)
            self.assertEqual(before,{p:p.read_bytes() for p in paths})


if __name__=='__main__':
    unittest.main()

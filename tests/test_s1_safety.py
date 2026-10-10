"""S1 failure boundaries and real data-preservation contracts."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build
import reading_backup
from content_novelty import audit, overlap, recent_articles
from edition_contract import issues
from longform import sourced_detail
from publish_reports import select_edition, read_index
from verify_publication import publication_outcome, verify_live


def alpha(n):
    out=''
    while True:
        out=chr(97+n%26)+out;n//=26
        if not n:return 'token'+out


class S1SafetyTests(unittest.TestCase):
    def test_exact_16_percent_is_rejected_without_rounding(self):
        left=[alpha(n) for n in range(2504)]
        below=left[:403]+[alpha(n) for n in range(3000,5101)]
        boundary=left[:404]+[alpha(n) for n in range(6000,8100)]
        self.assertEqual(overlap([' '.join(left)],[' '.join(below)]),0.1596)
        self.assertEqual(overlap([' '.join(left)],[' '.join(boundary)]),0.16)
        report={'date':'2026-10-11','mode':'reading_feature','headline':'New educational reading evidence',
                'essay':[' '.join(boundary[i:i+501]) for i in range(0,2504,501)],'stories':[]}
        prior={'date':'2026-10-10','headline':'Earlier educational reading evidence',
               'essay':[' '.join(left[i:i+501]) for i in range(0,2504,501)],'stories':[]}
        self.assertIn('excessive_cross_day_prose_overlap',audit(report,[prior])['issues'])

    def test_60_day_window_and_unindexed_files_are_compared(self):
        with tempfile.TemporaryDirectory() as name:
            reports=Path(name)
            build.atomic_json(reports/'index.json',[])
            for day in ('2026-08-11','2026-08-12','2026-08-13'):
                build.atomic_json(reports/(day+'.json'),{'date':day,'essay':['Earlier prose']})
            self.assertEqual([a['date'] for a in recent_articles(reports,'2026-10-11')],['2026-08-12','2026-08-13'])

    def test_damaged_60_day_history_fails_closed(self):
        with tempfile.TemporaryDirectory() as name:
            reports=Path(name)
            (reports/'2026-10-10.json').write_text('{damaged',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'history unavailable'):
                recent_articles(reports,'2026-10-11')
            for value in ([],{'date':'2026-10-10','essay':[]},{'date':'2026-10-10','essay':[42]}):
                build.atomic_json(reports/'2026-10-10.json',value)
                with self.assertRaisesRegex(ValueError,'history unavailable'):
                    recent_articles(reports,'2026-10-11')

    def test_parallel_atomic_files_and_index_writes_remain_complete(self):
        with tempfile.TemporaryDirectory() as name:
            reports=Path(name)/'site/reports'
            with patch.object(build,'REPORTS',reports):
                articles=[reading_backup.build_reading('2026-09-'+str(n).zfill(2)) for n in range(1,9)]
                with ThreadPoolExecutor(max_workers=4) as pool:
                    list(pool.map(build.put_report,articles))
                rows=json.loads((reports/'index.json').read_text(encoding='utf-8'))
                self.assertEqual(len(rows),8)
                self.assertEqual([r['date'] for r in rows],sorted([r['date'] for r in rows],reverse=True))
                for row in rows:
                    article=json.loads((reports/(row['date']+'.json')).read_text(encoding='utf-8'))
                    self.assertEqual(issues(article,row),[])
                self.assertFalse(list(reports.glob('*.tmp')))

    def test_no_unstated_shareholders_or_named_assistant_are_invented(self):
        self.assertNotIn('shareholders',sourced_detail({'excerpt':'Boyu Capital and IDG Capital participate in a funding round.'}))
        self.assertIn('shareholders',sourced_detail({'excerpt':'Boyu Capital and IDG Capital funding round includes existing shareholders.'}))
        self.assertEqual(sourced_detail({'excerpt':'The usage policy refers to abusive or cruel treatment of another system.'}),'')

    def test_duplicates_do_not_count_as_three_sources(self):
        from morning_canary import canary_sources
        stories=canary_sources(datetime.fromisoformat('2026-10-11T07:40:00+08:00'))
        stories[2]['url']=stories[0]['url']+'?utm_source=duplicate'
        self.assertFalse(build.validate_candidate_sources(stories))

    def test_future_legacy_profile_cannot_bypass_originality(self):
        article=reading_backup.build_reading('2026-10-11')
        self.assertIn('new_edition_requires_s1_originality',issues(article))

    def test_malformed_novelty_metadata_is_rejected(self):
        article=reading_backup.build_reading('2026-10-11')
        article.update(validation_profile='s1',novelty=['not an audit'])
        self.assertIn('missing_strict_originality_audit',issues(article))

    def test_publisher_does_not_erase_corrupted_index(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'index.json'
            for body in ('{damaged','[]','[{"date":"bad"}]','[{"date":"2026-10-10"},{"date":"2026-10-10"}]'):
                path.write_text(body,encoding='utf-8')
                with self.assertRaises(ValueError):read_index(path)
                self.assertEqual(path.read_text(encoding='utf-8'),body)

    def test_public_status_cannot_hide_new_failure(self):
        report=json.loads((ROOT/'site/reports/2026-10-10.json').read_text(encoding='utf-8'))
        rows=json.loads((ROOT/'site/reports/index.json').read_text(encoding='utf-8'))
        accepted=publication_outcome(rows,report,'2026-10-10')
        release=json.loads((ROOT/'site/release.json').read_text(encoding='utf-8'))
        get=lambda path:(ROOT/'site'/path).read_bytes()
        with self.assertRaisesRegex(ValueError,'Public failure/backup status'):
            verify_live(accepted,release,get,expected_status={'state':'feed_error'})

    def test_broken_news_questions_do_not_block_valid_backup(self):
        news=json.loads((ROOT/'site/reports/2026-10-10.json').read_text(encoding='utf-8'))
        news['practice']['items'][0]['evidence_quote']='A claim absent from the source paragraph.'
        backup=reading_backup.build_reading('2026-10-10')
        self.assertIs(select_edition(news,backup),backup)

    def test_archived_news_cannot_be_current_news(self):
        report=json.loads((ROOT/'site/reports/2026-10-10.json').read_text(encoding='utf-8'))
        row={key:report[key] for key in ('date','mode','word_count','updated_at')};row['stories']=len(report['stories'])
        state=publication_outcome([row],report,'2026-10-11',allow_archived=True)
        self.assertFalse(state['news']);self.assertEqual(state['backup'],'archived_reading')

    def test_preserved_articles_config_and_identity_contract(self):
        manifest=json.loads((ROOT/'docs/S1_PRESERVED_FILES.json').read_text(encoding='utf-8'))
        for name,digest in manifest['sha256'].items():
            with self.subTest(path=name):
                # Windows Git checkout may expand LF into CRLF; compare the
                # canonical Git text bytes without changing the protected file.
                self.assertEqual(hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),digest)

    def test_release_cache_and_strict_novelty_policy_agree(self):
        release=json.loads((ROOT/'site/release.json').read_text(encoding='utf-8'))
        self.assertEqual(release['version'],'S1')
        self.assertEqual(release['originality'],{'phrase_words':5,'lookback_days':60,'max_overlap_exclusive':0.16})
        html=(ROOT/'site/index.html').read_text(encoding='utf-8')
        worker=(ROOT/'site/sw.js').read_text(encoding='utf-8')
        self.assertIn('>S1<',html);self.assertIn(release['cache_namespace'],worker)

    def test_publishing_workflows_queue_and_history_is_read_only(self):
        for name in ('daily.yml','early-reading.yml'):
            content=(ROOT/'.github/workflows'/name).read_text(encoding='utf-8')
            self.assertIn('group: ai-daily-news\n  queue: max',content)
            self.assertIn('cancel-in-progress: false',content)
        history=(ROOT/'.github/workflows/v3-history-rebuild.yml').read_text(encoding='utf-8')
        self.assertNotIn('pages: write',history);self.assertNotIn('contents: write',history)
        self.assertNotIn('git push',history)

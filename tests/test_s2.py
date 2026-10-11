"""S2 release: actual accepted model packs, immutable withdrawal and failure gates."""
import copy,json,sys,tempfile,shutil,unittest,subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build,reading_backup,validate_site
from s2_reading import paragraph_issues,report_issues,specification,digest,review_payload,comparison_indices,contribution_payload,contribution_issues,paragraph_budget
from s2_reserve import validate_all,validate_reserve,WITHDRAWN
from withdraw_editions import withdraw
from content_novelty import audit,recent_articles
from edition_contract import issues
from verify_publication import publication_outcome,verify_live

class S2ReleaseTests(unittest.TestCase):
    def test_variable_paragraph_budgets_preserve_whole_essay_bounds(self):
        for count in (9,10,11,12):
            for choose in ('minimum','maximum','target'):
                essay=[]
                while len(essay)<count:
                    low,high,target=paragraph_budget(essay,count)
                    self.assertLessEqual(low,target);self.assertLessEqual(target,high)
                    words={'minimum':low,'maximum':high,'target':target}[choose]
                    essay.append(' '.join(['word']*words))
                self.assertTrue(1000<=sum(len(p.split()) for p in essay)<=1550)
        low,high,target=paragraph_budget([' '.join(['word']*177)],10)
        self.assertLessEqual(low,100);self.assertEqual(high,210)

    def packs(self):
        values=validate_all()
        self.assertTrue(values,'No actual model-generated S2 reserve has been accepted')
        return values

    def test_future_preparation_contains_three_real_approved_dates(self):
        self.assertTrue({'2026-10-12','2026-10-13','2026-10-14'}<=set(r['date'] for r in self.packs()))

    def test_actual_packs_have_distinct_topics_and_structures(self):
        packs=self.packs()[:3]
        self.assertEqual(len({r['writing_style'] for r in packs}),len(packs))
        self.assertEqual(len({r['reading_specification']['topic'] for r in packs}),len(packs))
        for report in packs:self.assertEqual(report_issues(report),[])

    def test_actual_packs_pass_unrounded_five_word_history_overlap(self):
        previous=[]
        for report in self.packs():
            checked=audit(report,[*recent_articles(ROOT/'site/reports',report['date']),*previous])
            self.assertTrue(checked['pass'],checked)
            self.assertLess(checked['max_overlap'],.16)
            previous.append(report)

    def test_complete_offline_translation_is_bound_to_review(self):
        report=copy.deepcopy(self.packs()[0]);report['translations'].pop()
        self.assertIn('incomplete_s2_translation',report_issues(report))
        self.assertIn('missing_or_stale_s2_semantic_review',report_issues(report))

    def test_review_hash_cannot_hide_changed_english(self):
        report=copy.deepcopy(self.packs()[0]);report['essay'][2]+=' An additional unreviewed claim.'
        self.assertIn('missing_or_stale_s2_semantic_review',report_issues(report))

    def test_false_editor_approval_is_rejected(self):
        report=copy.deepcopy(self.packs()[0]);report['s2_review']['natural_english']=False
        self.assertIn('missing_or_stale_s2_semantic_review',report_issues(report))

    def test_changed_question_cannot_keep_prior_review(self):
        report=copy.deepcopy(self.packs()[0]);report['practice']['items'][0]['stem']='Unreviewed question'
        self.assertIn('question_revision_mismatch',report_issues(report))
        self.assertIn('missing_or_stale_s2_semantic_review',report_issues(report))

    def test_dropped_offline_meaning_is_a_hard_failure(self):
        report=copy.deepcopy(self.packs()[0]);report['dictionary']={}
        self.assertIn('incomplete_dictionary',issues(report,reports=ROOT/'site/reports'))

    def test_copied_paragraph_is_stopped_immediately(self):
        paragraph=' '.join(['This imaginary comparison develops different responsibilities and practical consequences for readers.']*6)
        self.assertIn('repeated_meaningful_sentence',paragraph_issues(paragraph,[]))
        self.assertIn('repeated_paragraph_opening',paragraph_issues(paragraph,[paragraph]))

    def test_actual_model_false_positive_cannot_be_republished(self):
        path=ROOT/'content-history/rejected/s2/2026-10-12-model-approved-semantic-repeat.json'
        report=json.loads(path.read_text('utf-8'))
        self.assertTrue(report['s2_review']['approved'],'Keep the exact false-positive evidence')
        errors=report_issues(report)
        self.assertIn('repeated_example_scaffolding',errors)
        self.assertIn('missing_s2_paragraph_contribution_review',errors)
        self.assertIn('missing_or_stale_s2_english_review',errors)
        with self.assertRaises(ValueError):validate_reserve(report,ROOT/'site/reports')

    def test_comparisons_include_adjacent_and_most_similar_older_paragraph(self):
        essay=['library readers recommendation books interests','clinic queue appointments waiting patients',
               'workshop repair tools apprentices','library books recommendation readers choice']
        self.assertEqual(comparison_indices(essay,3),[0,2])
        payload=contribution_payload(essay,3)
        self.assertEqual([p['paragraph_number'] for p in payload['earlier_paragraphs']],[1,3])

    def test_changed_actors_or_missing_comparison_cannot_pass_contribution_review(self):
        essay=['imaginary library narrows familiar books','school recommends only familiar texts']
        reviewed={'approved':True,'issues':[],'new_contribution':'This example merely changes the actors involved.',
                  'comparisons':[{'paragraph_number':1,'distinct_step':False,'cosmetic_restatement':True,
                                  'reason':'Both paragraphs make the same narrowing claim.'}]}
        self.assertTrue(contribution_issues(reviewed,essay,1))
        reviewed['comparisons']=[]
        self.assertTrue(contribution_issues(reviewed,essay,1))

    def test_accepted_pack_cannot_drop_or_change_contribution_evidence(self):
        report=copy.deepcopy(self.packs()[0]);report['s2_paragraph_reviews'].pop()
        self.assertIn('missing_s2_paragraph_contribution_review',report_issues(report))
        self.assertIn('missing_or_stale_s2_semantic_review',report_issues(report))
        report=copy.deepcopy(self.packs()[0]);report['s2_paragraph_reviews'][0]['input_sha256']='0'*64
        self.assertIn('missing_or_stale_s2_paragraph_review',report_issues(report))

    def test_unlabelled_fiction_is_rejected_before_later_paragraphs(self):
        paragraph=' '.join(['A clinic arranged appointments using an automated queue.']*12)
        self.assertIn('missing_imaginary_scope_in_opening',paragraph_issues(paragraph,[]))

    def test_exhausted_model_context_cannot_approve_truncated_input(self):
        import s2_reading
        from unittest.mock import MagicMock
        response=MagicMock()
        response.__enter__.return_value.read.return_value=json.dumps({'done':True,'done_reason':'stop',
            'prompt_eval_count':8191,'response':'{}'}).encode()
        with patch.object(s2_reading,'urlopen',return_value=response):
            with self.assertRaisesRegex(ValueError,'context_exhausted'):s2_reading.request('review data',{})

    def test_retired_sources_remain_in_selection_history(self):
        with patch.object(build,'REPORTS',ROOT/'site/reports'):
            old=build.recent_report_stories('2026-10-12',days=5)
        self.assertTrue(old)
        self.assertTrue(any(s['url'] in {x['url'] for x in old} for s in json.loads((ROOT/'content-history/retired/2026-10-10.json').read_text('utf-8'))['stories']))

    def test_requested_dates_are_absent_from_all_public_directories(self):
        for day in WITHDRAWN:self.assertEqual(list((ROOT/'site/reports').rglob(day+'.json')),[])

    def test_missing_protected_revision_cannot_shrink_originality_history(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            shutil.copytree(ROOT/'site',root/'site')
            shutil.copytree(ROOT/'content-history',root/'content-history')
            (root/'content-history/retired/2026-10-09-original.json').unlink()
            with self.assertRaisesRegex(ValueError,'Protected originality history'):
                recent_articles(root/'site/reports','2026-10-12')

    def test_modified_protected_revision_cannot_pass_originality_history(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            shutil.copytree(ROOT/'site',root/'site')
            shutil.copytree(ROOT/'content-history',root/'content-history')
            path=root/'content-history/retired/2026-10-10.json'
            path.write_text('{}','utf-8')
            with self.assertRaisesRegex(ValueError,'checksum changed'):
                recent_articles(root/'site/reports','2026-10-12')

    def test_missing_entire_history_cannot_pass_empty_s2_site(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);shutil.copytree(ROOT/'site',root/'site')
            with self.assertRaisesRegex(ValueError,'manifest missing'):
                recent_articles(root/'site/reports','2026-10-12')

    def test_dropping_manifest_entry_cannot_hide_deleted_originality_evidence(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);shutil.copytree(ROOT/'site',root/'site');shutil.copytree(ROOT/'content-history',root/'content-history')
            path=root/'content-history/retired/withdrawn-manifest.json';manifest=json.loads(path.read_text('utf-8'))
            missing=manifest['files'].pop('site/reports/archive-revisions/s1-original/2026-10-09.json')
            (root/missing['backup']).unlink();path.write_text(json.dumps(manifest),'utf-8')
            with self.assertRaisesRegex(ValueError,'manifest lost'):
                recent_articles(root/'site/reports','2026-10-12')

    def test_one_valid_backup_cannot_stand_in_for_a_different_revision(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);shutil.copytree(ROOT/'site',root/'site');shutil.copytree(ROOT/'content-history',root/'content-history')
            path=root/'content-history/retired/withdrawn-manifest.json';manifest=json.loads(path.read_text('utf-8'))
            manifest['files']['site/reports/2026-10-09.json']=manifest['files']['site/reports/2026-10-10.json']
            path.write_text(json.dumps(manifest),'utf-8')
            with self.assertRaisesRegex(ValueError,'wrong backup'):
                recent_articles(root/'site/reports','2026-10-12')

    def test_withdrawal_backup_operation_is_idempotent(self):
        before=(ROOT/'docs/S2_WITHDRAWN_FILES.json').read_bytes()
        status=(ROOT/'site/system-status.json').read_bytes()
        result=withdraw()
        self.assertEqual(len(result),5)
        self.assertEqual((ROOT/'docs/S2_WITHDRAWN_FILES.json').read_bytes(),before)
        self.assertEqual((ROOT/'site/system-status.json').read_bytes(),status)

    def test_removed_date_cannot_be_recreated(self):
        with self.assertRaisesRegex(ValueError,'withdrawn'):reading_backup.ensure_reading('2026-10-09')

    def test_no_prepared_reading_cannot_be_claimed_as_success(self):
        with tempfile.TemporaryDirectory() as name:
            site=Path(name)/'site';shutil.copytree(ROOT/'site',site)
            build.atomic_json(site/'reports/index.json',[])
            with patch.object(build,'REPORTS',site/'reports'),patch.object(build,'STATUS_PATH',site/'system-status.json'):
                self.assertIsNone(reading_backup.ensure_reading('2026-10-15',datetime.fromisoformat('2026-10-15T07:05:00+08:00')))
                status=json.loads((site/'system-status.json').read_text('utf-8'))
                self.assertEqual(status['state'],'reading_preparation_failed')
                self.assertIsNone(status['latest_date'])
                actual=publication_outcome([],None,'2026-10-15',withdrawn=True)
                self.assertFalse(actual['reading_available']);self.assertFalse(actual['news'])

    def test_shuffled_old_library_cannot_bypass_s2_gate(self):
        legacy=reading_backup.build_reading('2026-10-12')
        self.assertIn('new_education_requires_reviewed_s2_generation',issues(legacy,reports=ROOT/'site/reports'))

    def test_unknown_release_metadata_cannot_authorise_empty_reading(self):
        with self.assertRaises(ValueError):publication_outcome([],None,'2026-10-12')

    def test_public_verifier_rejects_still_accessible_withdrawn_article(self):
        accepted=publication_outcome([],None,'2026-10-11',withdrawn=True)
        release=json.loads((ROOT/'site/release.json').read_text('utf-8'))
        def get(path):
            if path=='reports/index.json':return b'[]'
            if path=='reports/2026-10-08.json':return b'{}'
            return (ROOT/'site'/path).read_bytes()
        with self.assertRaisesRegex(ValueError,'still accessible'):verify_live(accepted,release,get)

    def test_missing_dictionary_or_review_cannot_publish_prepared_reading(self):
        report=copy.deepcopy(self.packs()[0]);report.pop('s2_review')
        with self.assertRaises(ValueError):validate_reserve(report,ROOT/'site/reports')

    def test_structure_schedule_varies_adjacent_dates(self):
        from datetime import date,timedelta
        first=date(2026,10,12)
        specs=[specification((first+timedelta(days=i)).isoformat()) for i in range(60)]
        self.assertTrue(all(a['structure']!=b['structure'] and a['topic']!=b['topic'] for a,b in zip(specs,specs[1:])))
        self.assertEqual(len({s['topic'] for s in specs}),60,'Do not recycle an identical writing assignment inside the 60-day window')
        for start in (12,60,72,120):
            window=[specification((first+timedelta(days=start+i)).isoformat())['topic'] for i in range(61)]
            self.assertEqual(len(set(window)),61)

    def test_real_parallel_reserve_push_preserves_code_and_other_dates(self):
        packs=self.packs()[:2]
        self.assertEqual(len(packs),2)
        with tempfile.TemporaryDirectory(prefix='s2-git-') as name:
            lab=Path(name);bare=lab/'remote.git';upstream=lab/'seed'
            def git(cwd,*args):
                return subprocess.run(['git',*args],cwd=cwd,check=True,capture_output=True,text=True)
            git(lab,'init','--bare',str(bare))
            upstream.mkdir()
            for folder in ('site','scripts','content-history'):shutil.copytree(ROOT/folder,upstream/folder)
            shutil.copy2(ROOT/'.gitignore',upstream/'.gitignore')
            git(upstream,'init','-b','main');git(upstream,'config','user.email','s2-local-test@example.invalid');git(upstream,'config','user.name','S2 local test')
            git(upstream,'add','.');git(upstream,'commit','-m','Seed isolated S2 release')
            git(upstream,'remote','add','origin',str(bare));git(upstream,'push','origin','main')
            workers=[]
            for offset,report in enumerate(packs):
                worker=lab/('worker-'+str(offset));git(lab,'clone','--branch','main',str(bare),str(worker))
                git(worker,'config','user.email','s2-local-test@example.invalid');git(worker,'config','user.name','S2 local test')
                build.atomic_json(worker/'.cache/accepted'/(report['date']+'.json'),report)
                workers.append(worker)
            def run(worker):return subprocess.run([sys.executable,'scripts/s2_reserve.py','--publish','.cache/accepted'],cwd=worker,capture_output=True,text=True)
            with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,workers))
            for result in results:self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            final=lab/'verification';git(lab,'clone','--branch','main',str(bare),str(final))
            self.assertEqual({p.stem for p in (final/'reading-reserve').glob('*.json')},{r['date'] for r in packs})
            self.assertEqual((final/'site/app.js').read_bytes(),(ROOT/'site/app.js').read_bytes())
            self.assertEqual((final/'site/reports/index.json').read_bytes(),(ROOT/'site/reports/index.json').read_bytes())
            before=git(final,'rev-parse','HEAD').stdout
            changed=final/'site/app.js';changed.write_text(changed.read_text('utf-8')+'\n// uncommitted local edit\n',encoding='utf-8')
            result=run(final)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('clean disposable checkout',result.stderr)
            self.assertTrue(changed.read_text('utf-8').endswith('// uncommitted local edit\n'))
            self.assertEqual(git(final,'rev-parse','HEAD').stdout,before)

if __name__=='__main__':unittest.main()

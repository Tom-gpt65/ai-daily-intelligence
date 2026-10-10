"""V2 acceptance: real generator/publisher, future HK dates and fail-closed news.

All Git pushes target disposable LOCAL bare repositories. No credentials,
external news, Supabase records or published archives are changed.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from datetime import timedelta
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build
import longform
import publish_reports
import reading_backup
import validate_site
import verify_publication
from edition_guarantee import complete,fill_dictionary
from morning_canary import canary_sources,test_future_publication
from verify_publication import publication_outcome,record_attempt,verify_live


def read(path):return json.loads(Path(path).read_text("utf-8"))


class V2PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="v2-pipeline-")
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.site=self.folder/"site"
        shutil.copytree(ROOT/"site",self.site)
        self.day="2026-10-11"
        self.now=datetime.fromisoformat(self.day+"T07:40:00+08:00")
        self.patches=[patch.object(build,"REPORTS",self.site/"reports"),
                      patch.object(build,"STATUS_PATH",self.site/"system-status.json"),
                      patch.object(validate_site,"SITE",self.site),
                      patch.dict(os.environ,{"OLLAMA_ENABLED":"0","TRANSLATE_ENABLED":"0"})]
        for setting in self.patches:setting.start();self.addCleanup(setting.stop)

    def generate(self):
        self.assertTrue(build.build_live(self.now,None,sources=canary_sources(self.now)))
        return read(self.site/"reports"/(self.day+".json"))

    def test_new_day_source_digest_is_complete_without_optional_services(self):
        with patch.object(build,"model_request",side_effect=AssertionError("Model must not be called")):
            article=self.generate()
        self.assertEqual(article["mode"],"source_digest")
        self.assertEqual(article["updated_at"],self.now.isoformat())
        self.assertTrue(complete(article))
        self.assertEqual(validate_site.validate(),[])

    def test_unknown_entity_does_not_become_a_fake_chinese_definition(self):
        sources=canary_sources(self.now)
        sources[0]["title"]="MysteryUnverifiedBench tests AI safety research"
        self.assertFalse(build.build_live(self.now,None,sources=sources))
        status=read(build.STATUS_PATH)
        self.assertEqual(status["state"],"incomplete_dictionary")
        self.assertIn("mysteryunverifiedbench",status["missing_examples"])
        self.assertFalse((build.REPORTS/(self.day+".json")).exists())

    def test_thin_rss_does_not_pad_a_news_article(self):
        sources=canary_sources(self.now)
        for source in sources:source["excerpt"]="AI research."
        self.assertFalse(build.build_live(self.now,None,sources=sources))
        self.assertEqual(read(build.STATUS_PATH)["state"],"insufficient_evidence")

    def test_expired_and_future_sources_cannot_be_reissued_as_news(self):
        for shift in (-37,2):
            sources=canary_sources(self.now+timedelta(hours=shift))
            self.assertFalse(build.build_live(self.now,None,sources=sources))
            self.assertEqual(read(build.STATUS_PATH)["state"],"insufficient_evidence")

    def test_prefetch_cannot_cross_hong_kong_midnight(self):
        snapshot={"at":"2026-10-10T15:59:00+00:00","stories":canary_sources(self.now)}
        with patch.object(build,"ROOT",self.folder),patch.object(build,"datetime") as clock,patch.object(sys,"argv",["build.py","--use-prefetch"]):
            clock.now.return_value=datetime.fromisoformat("2026-10-10T16:01:00+00:00")
            clock.fromisoformat.side_effect=datetime.fromisoformat
            build.atomic_json(self.folder/".cache/candidates.json",snapshot)
            self.assertEqual(build.main(),1)
            self.assertFalse((build.REPORTS/(self.day+".json")).exists())

    def test_required_news_fails_after_fallback_was_publicly_verified(self):
        article=reading_backup.build_reading(self.day,self.now)
        build.put_report(article)
        with patch.object(verify_publication,"SITE",self.site),patch.object(verify_publication,"datetime") as clock,patch.object(sys,"argv",["verify_publication.py","--live","--require-news"]),patch.object(verify_publication,"get_public",side_effect=lambda path,getter=None:(self.site/path).read_bytes()) as public_reads,patch.object(verify_publication.time,"sleep",side_effect=AssertionError('Public fixture must verify on the first attempt')):
            clock.now.return_value=self.now
            self.assertEqual(verify_publication.main(),1)
            self.assertIn('release.json',[call.args[0] for call in public_reads.call_args_list])

    def test_education_is_not_classified_as_current_news(self):
        article=reading_backup.build_reading(self.day,self.now)
        build.put_report(article)
        index=read(build.REPORTS/"index.json")
        self.assertFalse(publication_outcome(index,article,self.day)["news"])

    def test_first_fallback_retains_new_day_rss_failure_diagnosis(self):
        build.put_status("feed_error",self.now,feeds_ok=0,feeds_total=6)
        with patch.object(sys,"argv",["reading_backup.py","--date",self.day,"--if-missing"]):
            self.assertEqual(reading_backup.main(),0)
        status=read(build.STATUS_PATH)
        self.assertEqual(status["state"],"feed_error")
        self.assertEqual(status["mode"],"reading_feature")
        self.assertEqual(status["feeds_ok"],0)

    def test_model_crash_is_reported_separately_from_safe_reading(self):
        article=reading_backup.build_reading(self.day,self.now)
        build.put_report(article)
        accepted=publication_outcome(read(build.REPORTS/"index.json"),article,self.day)
        status=record_attempt({"state":"new_stories_found"},accepted,"failure","success",self.now)
        self.assertEqual(status["state"],"build_failed")
        self.assertEqual(status["news_outcome"],"educational_fallback")
        self.assertFalse(status["publication"]["news"])

    def test_live_checker_rejects_old_cdn_revision(self):
        article=self.generate()
        index=read(build.REPORTS/"index.json")
        accepted=publication_outcome(index,article,self.day)
        release=read(self.site/"release.json")
        def get(path):
            if path=="reports/"+self.day+".json":
                old=copy.deepcopy(article);old["updated_at"]="2026-10-11T07:05:00+08:00"
                return json.dumps(old).encode()
            return (self.site/path).read_bytes()
        with self.assertRaises(ValueError):verify_live(accepted,release,get)

    def test_live_checker_accepts_matching_release_and_news(self):
        article=self.generate()
        accepted=publication_outcome(read(build.REPORTS/"index.json"),article,self.day)
        result=verify_live(accepted,read(self.site/"release.json"),lambda path:(self.site/path).read_bytes())
        self.assertTrue(result["news"])

    def test_new_questions_cannot_quote_absent_evidence(self):
        article=self.generate()
        article["practice"]["items"][0]["evidence_quote"]="An invented result absent from this paragraph."
        build.atomic_json(build.REPORTS/(self.day+".json"),article)
        self.assertTrue(any("quotes absent evidence" in error for error in validate_site.validate()))

    def test_unsafe_source_url_and_invented_citation_are_rejected(self):
        article=self.generate()
        article["stories"][0]["url"]="javascript:alert(1)"
        article["essay"][0]+=" [S999]"
        build.atomic_json(build.REPORTS/(self.day+".json"),article)
        errors=validate_site.validate()
        self.assertTrue(any("source records malformed" in error for error in errors))
        self.assertTrue(any("invented source citations" in error for error in errors))

    def test_template_dictionary_has_correct_exact_inflection_senses(self):
        glossary=read(self.site/"news-template-glossary.json")
        paragraph=["The report adds evidence and rests on research."]
        dictionary,missing=fill_dictionary(paragraph,{"adds":{"translation":"某縮寫"},"rests":{"translation":"其他"}})
        self.assertEqual(missing,[])
        self.assertEqual(dictionary["adds"]["translation"],glossary["adds"])
        self.assertEqual(dictionary["rests"]["translation"],glossary["rests"])

    def test_canary_crosses_year_boundary_without_mutating_public_files(self):
        original={p.name:p.read_bytes() for p in (ROOT/"site/reports").glob('*.json')}
        self.assertEqual(test_future_publication("2026-12-31")[:3],["2026-12-31","2027-01-01","2027-01-02"])
        self.assertEqual(original,{p.name:p.read_bytes() for p in (ROOT/"site/reports").glob('*.json')})


class V2LocalGitAcceptanceTests(unittest.TestCase):
    def git(self,folder,*args):
        result=subprocess.run(["git",*args],cwd=folder,capture_output=True,text=True)
        if os.name=='nt' and 'NtCreateDirectoryObject' in result.stderr:
            self.skipTest('Windows sandbox denies MSYS process objects; Linux CI must run the real Git publication test')
        if result.returncode:raise AssertionError("Local Git acceptance failed: "+result.stderr)
        return result

    def configure(self,folder):
        self.git(folder,"config","user.name","Local publication acceptance")
        self.git(folder,"config","user.email","acceptance@example.invalid")

    def test_real_publish_preserves_concurrent_history_and_never_downgrades_news(self):
        with tempfile.TemporaryDirectory(prefix="v2-local-git-") as name:
            lab=Path(name)
            origin=lab/"origin.git"
            upstream=lab/"upstream"
            worker=lab/"worker"
            self.git(lab,"init","--bare","--initial-branch=main",str(origin))
            upstream.mkdir()
            self.git(upstream,"init","--initial-branch=main")
            self.configure(upstream)
            shutil.copytree(ROOT/"site",upstream/"site")
            self.git(upstream,"add","site");self.git(upstream,"commit","-m","Initial public fixture")
            self.git(upstream,"remote","add","origin",str(origin))
            self.git(upstream,"push","-u","origin","main")
            self.git(lab,"clone",str(origin),str(worker));self.configure(worker)
            original_history=(upstream/"site/reports/2026-10-08.json").read_bytes()
            # A concurrent upstream edit changes the previous day's article
            # and its index. The worker must not replay its stale index row.
            with patch.object(build,"REPORTS",upstream/"site/reports"):
                prior=reading_backup.build_reading("2026-10-10",datetime.fromisoformat("2026-10-10T16:00:00+08:00"))
                build.put_report(prior)
            (upstream/"concurrent-code.txt").write_text("new main code\n")
            self.git(upstream,"add",".");self.git(upstream,"commit","-m","Concurrent history and code fixture")
            self.git(upstream,"push","origin","main")
            day="2026-10-11"
            now=datetime.fromisoformat(day+"T07:40:00+08:00")
            with patch.object(build,"REPORTS",worker/"site/reports"),patch.object(build,"STATUS_PATH",worker/"site/system-status.json"),patch.object(publish_reports,"ROOT",worker),patch.object(publish_reports,"REPORTS",worker/"site/reports"),patch.object(publish_reports,"STATUS",worker/"site/system-status.json"),patch.dict(os.environ,{"OLLAMA_ENABLED":"0"}):
                build.put_report(reading_backup.build_reading(day,now.replace(hour=7,minute=5)))
                publish_reports.publish()
                self.assertEqual(read(worker/"site/reports/2026-10-10.json")["word_count"],prior["word_count"])
                self.assertEqual((worker/"concurrent-code.txt").read_text(),"new main code\n")
                self.assertEqual((worker/"site/reports/2026-10-08.json").read_bytes(),original_history)
                self.assertTrue(build.build_live(now,None,sources=canary_sources(now)))
                publish_reports.publish()
                published=(worker/"site/reports"/(day+".json")).read_bytes()
                # A later emergency run is deliberately unable to downgrade
                # the complete 07:40 source digest, even with a later timestamp.
                build.put_report(reading_backup.build_reading(day,now.replace(hour=8,minute=20)))
                publish_reports.publish()
                self.assertEqual((worker/"site/reports"/(day+".json")).read_bytes(),published)
                self.assertEqual(read(worker/"site/reports/index.json")[0]["mode"],"source_digest")


if __name__=="__main__":unittest.main()

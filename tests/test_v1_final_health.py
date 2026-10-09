"""Deterministic offline tests for the read-only ultimate PWA monitor."""
import json
import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from v1_final_health import ASSETS,evaluate
from reading_backup import build_reading

class V1FinalHealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.date="2026-10-10"
        cls.report=build_reading(cls.date,datetime(2026,10,10,14,0,
                    tzinfo=ZoneInfo("Asia/Hong_Kong")))

    def fixture(self):
        site=ROOT/"site"
        assets={name:(200,b"ok") for name in ASSETS}
        assets["index.html"]=(200,b'<link rel="manifest"><link rel="apple-touch-icon">'
                            b'<span id="site-version">V1</span> ./reading-theme-v1.css?v=1')
        assets["app.js"]=(200,b"ai-daily-saved-v2")
        assets["cloud-sync.js"]=(200,b"async signInWithPassword")
        assets["sw.js"]=(200,b"ai-daily-V1-paper-calm-reading const SHELL="
                        b" './reports/index.json' './reading-theme-v1.css'")
        assets["reading-theme-v1.css"]=(200,b"--reader-paper: #FFFDF8\n"
                                         b"--reader-paper: #22292A")
        assets["manifest.webmanifest"]=(200,(site/"manifest.webmanifest").read_bytes())
        assets["reports/index.json"]=(200,json.dumps([{"date":self.date}]).encode())
        return {
            "assets":assets,
            "report":(200,json.dumps(self.report).encode()),
            "config":(200,(site/"cloud-config.json").read_bytes()),
            "auth":(200,b"{}"),
            "anonymous":(401,b'{"message":"unauthorized"}')
        }

    def test_valid_reading_and_private_cloud_pass(self):
        failures,warnings,checks=evaluate(self.fixture(),self.date)
        self.assertEqual(failures,[])
        self.assertGreaterEqual(len(checks),6)
        self.assertTrue(any("educational" in s for s in warnings))

    def test_200_empty_anonymous_is_safe(self):
        test=self.fixture()
        test["anonymous"]=(200,b"[]")
        self.assertEqual(evaluate(test,self.date)[0],[])

    def test_anonymous_rows_are_critical(self):
        test=self.fixture()
        test["anonymous"]=(200,b'[{"event_id":"leaked"}]')
        errors=evaluate(test,self.date)[0]
        self.assertTrue(any("SECURITY" in e for e in errors))

    def test_supabase_failure_is_critical(self):
        test=self.fixture()
        test["auth"]=(503,b"{}")
        self.assertTrue(any("Auth health" in e for e in evaluate(test,self.date)[0]))

    def test_missing_public_asset_is_critical(self):
        test=self.fixture()
        test["assets"]["reading-theme-v1.css"]=(404,b"")
        self.assertTrue(any("asset unavailable" in e for e in evaluate(test,self.date)[0]))

    def test_old_article_must_fail(self):
        test=self.fixture()
        test["assets"]["reports/index.json"]=(200,b'[{"date":"2026-10-09"}]')
        self.assertTrue(any("stale" in e for e in evaluate(test,self.date)[0]))

    def test_mismatched_cloud_project_must_fail(self):
        test=self.fixture()
        test["config"]=(200,json.dumps({
            "supabase_url":"https://untrusted.supabase.co",
            "anon_key":"sb_publishable_not_a_real_key"
        }).encode())
        self.assertTrue(any("configuration" in e for e in evaluate(test,self.date)[0]))

    def test_web_app_manifest_must_remain_installable(self):
        test=self.fixture()
        manifest=json.loads(test["assets"]["manifest.webmanifest"][1])
        manifest["display"]="browser"
        test["assets"]["manifest.webmanifest"]=(200,json.dumps(manifest).encode())
        self.assertTrue(any("manifest" in e for e in evaluate(test,self.date)[0]))

    def test_broken_article_content_must_fail(self):
        test=self.fixture()
        article=dict(self.report)
        article["dictionary"]={}
        test["report"]=(200,json.dumps(article).encode())
        self.assertTrue(any("offline Chinese" in e for e in evaluate(test,self.date)[0]))

    def test_invalid_public_json_must_fail_without_crash(self):
        test=self.fixture()
        test["report"]=(200,b"{")
        self.assertTrue(any("JSON failed" in e for e in evaluate(test,self.date)[0]))

if __name__=="__main__":
    unittest.main()

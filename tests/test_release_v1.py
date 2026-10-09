"""The first complete public release is called V1, without data migration."""
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SITE=ROOT/"site"

class FirstReleaseTests(unittest.TestCase):
    def test_public_version_and_asset_cache(self):
        html=(SITE/"index.html").read_text(encoding="utf-8")
        worker=(SITE/"sw.js").read_text(encoding="utf-8")
        self.assertIn('id="site-version" class="site-version" aria-label="網站版本">V1',html)
        self.assertIn('./v1.css?v=1',html)
        self.assertIn('./app.js?v=1',html)
        self.assertNotIn('v16.css',html)
        self.assertIn("ai-daily-V1-vocabulary-cloud-option",worker)
        self.assertIn("'./v1.css'",worker)
        self.assertTrue((SITE/"v1.css").is_file())
        self.assertNotIn('id="reading-speed"',html)
        self.assertNotIn('id="overview-minutes"',html)
        self.assertIn('class="status-pill hidden"',html)
        self.assertIn('font-size-state',html)
        self.assertIn('id="sync-login"',html)
        self.assertIn('id="sync-account"',html)
        self.assertIn("./cloud-sync.js?v=1",html)
        self.assertIn("'./cloud-sync.js'",worker)
        settings=__import__("json").loads((SITE/"cloud-config.json").read_text(encoding="utf-8"))
        self.assertIsInstance(settings["supabase_url"],str)
        self.assertIsInstance(settings["anon_key"],str)
        self.assertEqual(bool(settings["supabase_url"]),bool(settings["anon_key"]))
        self.assertNotIn("sb_secret_",settings["anon_key"])
        self.assertNotIn("service_role",settings["anon_key"])
    def test_server_controls_event_timestamps_and_order(self):
        sql=(ROOT/'docs'/'SUPABASE_VOCABULARY.sql').read_text(encoding='utf-8')
        module=(SITE/'cloud-sync.js').read_text(encoding='utf-8')
        self.assertIn('batch_order smallint not null default 0',sql)
        self.assertIn('revoke all on public.vocabulary_events from public, anon, authenticated',sql)
        self.assertIn('grant insert (event_id, user_id, word, payload, deleted, batch_order)',sql)
        self.assertIn('created_at,batch_order.asc',module)
    def test_learning_records_stay_backward_compatible(self):
        app=(SITE/"app.js").read_text(encoding="utf-8")
        for key in ("ai-daily-saved-v2","ai-daily-quiz-v6",
                    "ai-daily-answers-v1","ai-daily-learning-backup"):
            with self.subTest(key=key):
                self.assertIn(key,app)
    def test_current_docs_only_describe_v1_as_formal_version(self):
        readme=(ROOT/"README.md").read_text(encoding="utf-8")
        self.assertIn("第一個完整正式版本",readme)
        self.assertIn("V1",readme)
        self.assertTrue((ROOT/"docs"/"V1_FINAL_AUDIT.md").exists())
        self.assertTrue((ROOT/"docs"/"FINALISE_WEBSITE_V1.md").exists())

if __name__=="__main__":
    unittest.main()

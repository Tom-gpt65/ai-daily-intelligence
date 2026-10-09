"""Deployment smoke tests retained in GitHub. Full 73-test historical suite remains in v5 ZIP."""
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

class DeploymentTests(unittest.TestCase):
    def test_html_present(self):
        self.assertTrue((SITE / "index.html").is_file())
    def test_javascript_present(self):
        self.assertTrue((SITE / "app.js").is_file())
    def test_css_present(self):
        for name in ("style.css", "v3.css", "v4.css", "v5.css"):
            with self.subTest(name=name):
                self.assertTrue((SITE / name).is_file())
    def test_service_worker_present(self):
        self.assertTrue((SITE / "sw.js").is_file())
    def test_nojekyll_present(self):
        self.assertTrue((SITE / ".nojekyll").is_file())
    def test_report_index(self):
        reports = json.loads((SITE / "reports" / "index.json").read_text(encoding="utf-8"))
        self.assertIsInstance(reports, list)
        for item in reports:
            self.assertTrue((SITE / "reports" / (item["date"] + ".json")).is_file())
    def test_index_tracks_article_revision(self):
        entries=json.loads((SITE / "reports" / "index.json").read_text(encoding="utf-8"))
        self.assertTrue(entries)
        latest=entries[0]
        report=json.loads((SITE / "reports" / (latest["date"] + ".json")).read_text(encoding="utf-8"))
        self.assertTrue(latest.get("updated_at"))
        self.assertEqual(latest["updated_at"],report.get("updated_at"))
        javascript=(SITE / "app.js").read_text(encoding="utf-8")
        self.assertIn("Boolean(top.updated_at)",javascript)
    def test_report_mode_is_accurately_labelled(self):
        entries=json.loads((SITE / "reports" / "index.json").read_text(encoding="utf-8"))
        self.assertTrue(entries)
        for row in entries:
            with self.subTest(date=row["date"]):
                article=json.loads((SITE / "reports" / (row["date"] + ".json")).read_text(encoding="utf-8"))
                self.assertIn(article["mode"], ("editorial","source_digest","reading_feature"))
                self.assertFalse(article.get("demo",False))
                self.assertEqual(article["mode"],row["mode"])
                if article["mode"]=="reading_feature":
                    self.assertEqual(article["stories"],[])
                    self.assertIn("not",article["subtitle"].lower())
                else:
                    self.assertGreaterEqual(len(article["stories"]),3)
    def test_pwa_manifest(self):
        manifest = json.loads((SITE / "manifest.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual(manifest["display"], "standalone")
    def test_safe_url(self):
        spec = importlib.util.spec_from_file_location("news_build", ROOT / "scripts" / "build.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.safe_url("javascript:alert(1)"), "")
        self.assertEqual(module.safe_url("https://example.com/post?id=2&utm_source=test"),
                         "https://example.com/post?id=2")
    def test_workflow_exists(self):
        workflow = ROOT / ".github" / "workflows" / "daily.yml"
        self.assertTrue(workflow.is_file())
        yaml = workflow.read_text(encoding="utf-8")
        self.assertIn("Asia/Hong_Kong", yaml)
        self.assertIn("actions/deploy-pages", yaml)

if __name__ == "__main__":
    unittest.main()

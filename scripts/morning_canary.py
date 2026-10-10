"""Pre-07:40 acceptance canary for the actual V2 daily publication contract.

Runs WITHOUT RSS, secrets, API keys, or writes to production site. It
simulates future mornings when the 07:05 fallback is already the newest
article, then invokes the SAME validate_site.validate() as publication.

The 2026-10-10 first-attempt failure arose because tests validated yesterday's
news but rejected the legitimate next-morning reading_feature. Keep this
canary independent of today's mutable 'latest' article.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import validate_site
import build
from reading_backup import build_reading
from edition_guarantee import complete
from publish_reports import select_edition
from verify_publication import publication_outcome

ROOT = Path(__file__).resolve().parents[1]
HK = ZoneInfo("Asia/Hong_Kong")


def assert_valid_reserve(article: dict, day: str) -> None:
    if article.get("date") != day:
        raise ValueError("Canary date mismatch: " + day)
    if article.get("mode") != "reading_feature" or article.get("demo") is not False:
        raise ValueError("Canary reserve must be non-demo educational reading: " + day)
    if article.get("stories") != [] or "Not today's AI news" not in article.get("subtitle", ""):
        raise ValueError("Canary reserve falsely presented as current news: " + day)
    items = article.get("practice", {}).get("items", [])
    if len(items) != 7 or article.get("practice", {}).get("official") is not False:
        raise ValueError("Canary reserve has invalid original reading questions: " + day)
    if not 1000 <= article.get("word_count", 0) <= 1550 or not complete(article):
        raise ValueError("Canary reserve has incomplete text or offline definitions: " + day)


def canary_sources(now: datetime) -> list[dict]:
    """Synthetic RSS inputs, exclusively inside the temporary acceptance lab.

    They exercise evidence, citations and the real generator; they are never
    claimed to be real events or written to the repository/public website.
    """
    titles=("AI safety research tests evidence", "AI governance rules and responsibility",
            "AI technology research and independent evaluation")
    publishers=("Google Research","TechCrunch AI","MIT Technology Review")
    excerpt=("The research report describes an AI system and the evidence available for evaluation. "
             "It explains the method and limitations and asks readers to compare claims with independent research. "
             "The results require careful interpretation before conclusions about practical use.")
    return [{"id":f"S{i}","title":title,"publisher":publisher,
             "url":f"https://example.com/canary-fixture/{i}","excerpt":excerpt,
             "published":now.isoformat(),"topic":"Research"}
            for i,(title,publisher) in enumerate(zip(titles,publishers),1)]


def test_future_publication(first_day: str) -> list[str]:
    """Exercise real production site validation against simulated future state.

    Makes a temporary copy of PUBLIC site files; existing published reports,
    localStorage, Supabase and live GitHub Pages are never modified.
    """
    initial_errors = validate_site.validate()
    if initial_errors:
        raise ValueError("Current published site invalid: " + "; ".join(initial_errors[:5]))
    old_site = validate_site.SITE
    old_reports,old_status=build.REPORTS,build.STATUS_PATH
    previous_env={key:os.environ.get(key) for key in ("OLLAMA_ENABLED","TRANSLATE_ENABLED")}
    checked: list[str] = []
    with tempfile.TemporaryDirectory(prefix="v2-morning-canary-") as name:
        try:
            os.environ["OLLAMA_ENABLED"]="0"
            os.environ["TRANSLATE_ENABLED"]="0"
            for offset in (0, 1, 2, 7, 30):
                # A fresh copy for EACH date prevents a replaced day-zero
                # article from disagreeing with yesterday's original index.
                temporary_site=Path(name)/str(offset)/"site"
                shutil.copytree(ROOT/"site",temporary_site)
                validate_site.SITE=temporary_site
                build.REPORTS=temporary_site/"reports"
                build.STATUS_PATH=temporary_site/"system-status.json"
                day = (datetime.fromisoformat(first_day).date() + timedelta(days=offset)).isoformat()
                now = datetime.fromisoformat(day + "T07:05:00+08:00")
                reserve = build_reading(day, now)
                assert_valid_reserve(reserve, day)
                build.put_report(reserve)
                issues = validate_site.validate()
                if issues:
                    raise ValueError("Day " + day + " would deadlock the news-first publication: "
                                     + "; ".join(issues[:6]))
                news_time=datetime.fromisoformat(day+"T07:40:00+08:00")
                if build.build_live(news_time,None,sources=[],diagnostics={"feeds_total":6,"feeds_ok":0}):
                    raise ValueError("RSS outage fabricated current news")
                index=json.loads((build.REPORTS/"index.json").read_text("utf-8"))
                if publication_outcome(index,reserve,day)["news"]:
                    raise ValueError("Reserve incorrectly counted as current news")
                # The actual production builder, no model, dictionary download
                # or mocks of validation. Only synthetic RSS inputs are injected.
                if not build.build_live(news_time,None,sources=canary_sources(news_time)):
                    raise ValueError("Offline sourced-news transition failed: "+build.STATUS_PATH.read_text("utf-8"))
                news=json.loads((build.REPORTS/(day+".json")).read_text("utf-8"))
                index=json.loads((build.REPORTS/"index.json").read_text("utf-8"))
                if not publication_outcome(index,news,day)["news"] or validate_site.validate():
                    raise ValueError("Accepted reserve-to-news transition is invalid: "+day)
                later_reserve=build_reading(day,datetime.fromisoformat(day+"T08:20:00+08:00"))
                if select_edition(news,later_reserve) is not news:
                    raise ValueError("Late recovery downgraded current news to educational reading")
                checked.append(day)
        finally:
            validate_site.SITE = old_site
            build.REPORTS,build.STATUS_PATH=old_reports,old_status
            for key,value in previous_env.items():
                if value is None:os.environ.pop(key,None)
                else:os.environ[key]=value
    return checked


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--first-day", default=datetime.now(HK).date().isoformat())
    args = parser.parse_args()
    checked = test_future_publication(args.first_day)
    print("PASS: 07:05 reserve -> RSS outage -> first 07:40 sourced-news build "
          "-> late recovery without downgrade; no network or production writes.")
    print("PASS: production validator accepted dates: " + ", ".join(checked))
    print("PASS: public assets, archive, dictionary, exam and fallback/news labelling intact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

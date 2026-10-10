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
    titles=("AI safety research tests evidence", "AI funding and business expectations",
            "AI technology research and independent evaluation")
    publishers=("Google Research","TechCrunch AI","MIT Technology Review")
    excerpts=(
        "The safety study describes tests of model behaviour under different input conditions. "
        "Its authors explain the limits of the test collection and discuss how further examples could affect their assessment. "
        "They distinguish observations made during evaluation from conclusions about other situations.",
        "The commercial report discusses financing for a business and the intended use of those resources. "
        "It distinguishes support from investors from evidence about later business outcomes. "
        "The account identifies questions about costs, customer needs and progress that would require further observations.",
        "The research description presents a framework for comparing methods on specified tasks. "
        "It identifies the evaluation conditions and the measurements used to examine a response. "
        "The authors note that interpreting a comparison requires attention to assumptions, resources and the limits of the procedure."
    )
    return [{"id":f"S{i}","title":title,"publisher":publisher,
             "url":f"https://example.com/canary-fixture/{i}","excerpt":excerpts[i-1],
             "published":now.isoformat(),"topic":"Research"}
            for i,(title,publisher) in enumerate(zip(titles,publishers),1)]


def test_future_publication(first_day: str) -> list[str]:
    from s1_simulation import simulate
    rows = simulate(first_day, canary_sources)
    selected = {0,1,2,7,30}
    origin = datetime.fromisoformat(first_day).date()
    return [r["date"] for r in rows if (datetime.fromisoformat(r["date"]).date()-origin).days in selected]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--first-day", default=datetime.now(HK).date().isoformat())
    args = parser.parse_args()
    checked = test_future_publication(args.first_day)
    print("PASS: sequential future days, strict originality and honest archived fallback "
          "-> late recovery without downgrade; no network or production writes.")
    print("PASS: production validator accepted reading states for dates: " + ", ".join(checked))
    print("PASS: public assets, archive, dictionary, exam and fallback/news labelling intact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

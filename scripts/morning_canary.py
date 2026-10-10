"""Pre-07:40 acceptance canary for the actual V1 daily publication contract.

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
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import validate_site
from reading_backup import build_reading
from edition_guarantee import complete

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


def test_future_publication(first_day: str) -> list[str]:
    """Exercise real production site validation against simulated future state.

    Makes a temporary copy of PUBLIC site files; existing published reports,
    localStorage, Supabase and live GitHub Pages are never modified.
    """
    initial_errors = validate_site.validate()
    if initial_errors:
        raise ValueError("Current published site invalid: " + "; ".join(initial_errors[:5]))
    base_index = json.loads((ROOT / "site/reports/index.json").read_text(encoding="utf-8"))
    old_site = validate_site.SITE
    checked: list[str] = []
    with tempfile.TemporaryDirectory(prefix="v1-morning-canary-") as name:
        temporary_site = Path(name) / "site"
        shutil.copytree(ROOT / "site", temporary_site)
        try:
            validate_site.SITE = temporary_site
            for offset in (0, 1, 2, 7, 30):
                day = (datetime.fromisoformat(first_day).date() + timedelta(days=offset)).isoformat()
                now = datetime.fromisoformat(day + "T07:05:00+08:00")
                reserve = build_reading(day, now)
                assert_valid_reserve(reserve, day)
                (temporary_site / "reports" / (day + ".json")).write_text(
                    json.dumps(reserve, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                rows = [
                    {"date": day, "headline": reserve["headline"], "mode": reserve["mode"],
                     "word_count": reserve["word_count"], "stories": 0,
                     "updated_at": reserve["updated_at"]},
                    *(row for row in base_index if row["date"] != day),
                ]
                rows.sort(key=lambda row: row["date"], reverse=True)
                (temporary_site / "reports/index.json").write_text(
                    json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                issues = validate_site.validate()
                if issues:
                    raise ValueError("Day " + day + " would deadlock the news-first publication: "
                                     + "; ".join(issues[:6]))
                checked.append(day)
        finally:
            validate_site.SITE = old_site
    return checked


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--first-day", default=datetime.now(HK).date().isoformat())
    args = parser.parse_args()
    checked = test_future_publication(args.first_day)
    print("PASS: first-attempt morning publication is valid with the 07:05 "
          "educational reserve as newest report.")
    print("PASS: production validator accepted dates: " + ", ".join(checked))
    print("PASS: public assets, archive, dictionary, exam and fallback/news labelling intact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

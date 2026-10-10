"""V3 publication-time anti-repetition gate for genuine daily news.

Measures reused prose and narrative design against archived editions. It does
not claim semantic originality can be established mathematically; rejection is
safe (keep labelled educational reading), never invent new RSS sources.
Legacy V1/V2 archives are not modified or retroactively failed.
"""
from __future__ import annotations

import json
import re
from datetime import date as Date
from pathlib import Path

TOKEN = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")
STYLES = ("evidence_audit", "comparative_study", "consequence_map",
          "question_driven_review")
MAX_FIVE_GRAM_OVERLAP = 0.16
LOOKBACK_DAYS = 60


def normal(text: str) -> str:
    text = re.sub(r"^\s*\d+\.\s*", "", str(text))
    return " ".join(TOKEN.findall(text.lower()))


def shingles(paragraphs: list[str], n: int = 5) -> set[tuple[str, ...]]:
    words = TOKEN.findall(normal(" ".join(paragraphs)))
    return {tuple(words[i:i+n]) for i in range(max(0, len(words)-n+1))}


def overlap(left: list[str], right: list[str]) -> float:
    a, b = shingles(left), shingles(right)
    return round(len(a & b) / max(1, min(len(a), len(b))), 3)


def long_repeats(left: list[str], right: list[str]) -> int:
    # Compare exact long paragraphs even when a line number or citation changes.
    a = {normal(s) for s in left if len(TOKEN.findall(s)) >= 55}
    b = {normal(s) for s in right if len(TOKEN.findall(s)) >= 55}
    return len(a & b)


def recent_articles(reports: Path, today: str, window: int = LOOKBACK_DAYS):
    index_path = reports / "index.json"
    if not index_path.exists():
        return []
    current = Date.fromisoformat(today)
    rows = json.loads(index_path.read_text(encoding="utf-8"))
    output = []
    for row in rows:
        try:
            day = Date.fromisoformat(row["date"])
            delta = (current - day).days
            if delta <= 0 or delta > window:
                continue
            article = json.loads((reports / (row["date"] + ".json")).read_text(encoding="utf-8"))
            if isinstance(article.get("essay"), list):
                output.append(article)
        except (OSError, ValueError, TypeError, KeyError):
            # Historical damage must be rejected by validate_site; never
            # fabricate a history entry or hide it as successful publishing.
            continue
    return output


def audit(report: dict, archive: list[dict]) -> dict:
    essay = report.get("essay", [])
    issues = []
    if report.get("mode") not in ("editorial", "source_digest", "reading_feature"):
        return {"pass": False, "issues": ["unknown_mode"], "max_overlap": 1.0}
    if not isinstance(essay, list) or len(essay) < 5:
        return {"pass": False, "issues": ["invalid_prose"], "max_overlap": 1.0}
    style = report.get("writing_style")
    if style not in STYLES:
        issues.append("missing_or_unknown_writing_style")
    title = normal(report.get("headline", ""))
    if len(title.split()) < 4:
        issues.append("generic_headline")
    today = Date.fromisoformat(report["date"])
    max_overlap = 0.0
    most_similar = None
    comparisons = 0
    for prior in archive:
        if prior.get("date") == report["date"]:
            continue
        old_essay = prior.get("essay")
        if not isinstance(old_essay, list) or not old_essay:
            continue
        other_date = Date.fromisoformat(prior["date"])
        if other_date >= today:
            continue
        comparisons += 1
        common = overlap(essay, old_essay)
        if common > max_overlap:
            max_overlap, most_similar = common, prior["date"]
        if long_repeats(essay, old_essay) > 0:
            issues.append("copied_long_paragraph_from_" + prior["date"])
        if normal(essay[0]) == normal(old_essay[0]):
            issues.append("repeated_introduction_from_" + prior["date"])
        if normal(essay[-1]) == normal(old_essay[-1]):
            issues.append("repeated_conclusion_from_" + prior["date"])
        # The same two adjacent days must have different perspectives, not
        # simply swap the RSS titles in a fixed format.
        if (today - other_date).days <= 3 and style == prior.get("writing_style"):
            issues.append("recently_reused_writing_style")
        if title == normal(prior.get("headline", "")):
            issues.append("repeated_headline_from_" + prior["date"])
        old_urls = {s.get("url") for s in prior.get("stories", []) if isinstance(s, dict)}
        new_urls = {s.get("url") for s in report.get("stories", []) if isinstance(s, dict)}
        if len(new_urls) >= 3 and len(new_urls & old_urls) >= 3:
            issues.append("reused_news_sources_from_" + prior["date"])
    if max_overlap >= MAX_FIVE_GRAM_OVERLAP:
        issues.append("excessive_cross_day_prose_overlap")
    return {
        "pass": not issues,
        "issues": sorted(set(issues)),
        "max_overlap": max_overlap,
        "most_similar_date": most_similar,
        "compared_editions": comparisons,
        "threshold": MAX_FIVE_GRAM_OVERLAP,
        "writing_style": style,
    }


def audit_history(report: dict, reports: Path) -> dict:
    return audit(report, recent_articles(reports, report["date"]))

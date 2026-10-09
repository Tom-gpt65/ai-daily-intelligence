"""Read-only late-day health check for the installed V1 PWA and cloud privacy.

Checks PUBLIC site contents only. Does not log keys, authenticate a user, modify
a Supabase table, dispatch recovery jobs, or rewrite published articles.
"""
from __future__ import annotations
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from audit_publication import assess_public

HK = ZoneInfo("Asia/Hong_Kong")
BASE = "https://tom-gpt65.github.io/ai-daily-intelligence/"
ROOT = Path(__file__).resolve().parents[1]
ASSETS = (
    "index.html", "app.js", "cloud-sync.js", "sw.js", "manifest.webmanifest",
    "style.css", "v1.css", "reading-theme-v1.css", "icon-192.png",
    "icon-512.png", "offline-glossary.json", "reports/index.json",
)

def public_get(url: str, headers: dict | None = None) -> tuple[int, bytes]:
    """Return status/body (including expected 401/403 responses) with size caps."""
    h = {"User-Agent": "V1-Final-Autopilot/1", "Cache-Control": "no-cache"}
    if headers:
        h.update(headers)
    req = Request(url, headers=h)
    try:
        with urlopen(req, timeout=20) as response:
            return response.status, response.read(2_000_001)
    except HTTPError as error:
        return error.code, error.read(200_001)

def read_json(payload: bytes):
    if len(payload) > 2_000_000:
        raise ValueError("JSON exceeds safety size limit")
    return json.loads(payload.decode("utf-8"))

def evaluate(snapshot: dict, expected: str) -> tuple[list[str], list[str], list[str]]:
    """Pure verdict: failures, non-critical warnings, validated check names.

    status tuples are (HTTP status, data). User credentials are never input.
    """
    errors, warnings, checks = [], [], []
    assets = snapshot.get("assets") or {}
    for path in ASSETS:
        entry = assets.get(path)
        if not entry or entry[0] != 200 or not entry[1]:
            errors.append(f"Public PWA asset unavailable: {path}")
    if errors:
        return errors, warnings, checks
    checks.append("Public PWA assets and offline dictionaries")
    try:
        html = assets["index.html"][1].decode("utf-8")
        app = assets["app.js"][1].decode("utf-8")
        cloud = assets["cloud-sync.js"][1].decode("utf-8")
        worker = assets["sw.js"][1].decode("utf-8")
        theme = assets["reading-theme-v1.css"][1].decode("utf-8")
        manifest = read_json(assets["manifest.webmanifest"][1])
        index = read_json(assets["reports/index.json"][1])
        if not isinstance(manifest, dict):
            raise ValueError("App manifest is not an object")
        if (manifest.get("display") != "standalone" or
            manifest.get("start_url") != "./" or manifest.get("scope") != "./" or
            not {"192x192", "512x512"}.issubset(
                {item.get("sizes") for item in manifest.get("icons", [])
                 if isinstance(item, dict)})):
            errors.append("Public web-app manifest lacks standalone mode, scope or icons")
        elif "rel=\"manifest\"" not in html or "apple-touch-icon" not in html:
            errors.append("Installed iOS PWA metadata is missing")
        else:
            checks.append("iPhone/iPad standalone manifest and icons")

        if ('id="site-version"' not in html or '>V1<' not in html or
            "./reading-theme-v1.css?v=1" not in html or
            "ai-daily-V1-paper-calm-reading" not in worker or
            "const SHELL=" not in worker or
            "'./reports/index.json'" not in worker or
            "'./reading-theme-v1.css'" not in worker or
            "--reader-paper: #FFFDF8" not in theme or
            "--reader-paper: #22292A" not in theme or
            "async signInWithPassword" not in cloud or
            "ai-daily-saved-v2" not in app):
            errors.append("Public reading app, offline cache, theme or login is out of date")
        else:
            checks.append("V1 code, paper/night themes and offline shell")

        if not isinstance(index, list) or not index or not isinstance(index[0], dict):
            errors.append("Public daily article index is missing or invalid")
        elif index[0].get("date") != expected:
            errors.append(f"Public daily article is stale: expected {expected}")
        else:
            report = snapshot.get("report")
            if not report or report[0] != 200:
                errors.append("Today's public article JSON is not accessible")
            else:
                obj = read_json(report[1])
                article_errors, article_warnings = assess_public(index, obj, expected)
                errors.extend(article_errors)
                warnings.extend(article_warnings)
                if not article_errors:
                    checks.append("Fresh, complete and accurately labelled HKDSE-style reading")
    except (UnicodeError, ValueError, TypeError, KeyError) as err:
        errors.append("Public PWA or article JSON failed validation: " + type(err).__name__)

    config_raw = snapshot.get("config")
    try:
        if not config_raw or config_raw[0] != 200:
            raise ValueError("Missing public cloud configuration")
        config = read_json(config_raw[1])
        original = json.loads((ROOT / "site/cloud-config.json").read_text("utf-8"))
        if config != original or not config.get("supabase_url","").startswith("https://") or (
            not str(config.get("anon_key","")).startswith("sb_publishable_")):
            raise ValueError("Public configuration differs from repository or contains an invalid key")
        checks.append("Public Supabase configuration matches repository")
    except (ValueError, TypeError, KeyError, OSError):
        errors.append("Public Supabase configuration invalid or inconsistent")

    auth = snapshot.get("auth")
    if auth is None or auth[0] != 200:
        errors.append("Supabase Auth health endpoint unavailable")
    else:
        checks.append("Supabase Auth reachable")

    anonymous = snapshot.get("anonymous")
    if anonymous is None:
        errors.append("Unable to verify anonymous vocabulary access")
    elif anonymous[0] in (401,403):
        checks.append("Anonymous vocabulary query denied by Supabase")
    elif anonymous[0] == 200:
        try:
            rows = read_json(anonymous[1])
            if rows != []:
                errors.append("SECURITY: anonymous vocabulary data unexpectedly readable")
            else:
                checks.append("Anonymous vocabulary query returns zero rows")
        except (ValueError,UnicodeError):
            errors.append("Anonymous vocabulary API response invalid")
    else:
        errors.append("Unexpected response to anonymous vocabulary query")

    return errors, warnings, checks

def check_once(expected: str) -> tuple[list[str], list[str], list[str]]:
    snapshot = {"assets": {}}
    for path in ASSETS:
        snapshot["assets"][path] = public_get(BASE + path + "?autopilot=1")
    index = snapshot["assets"].get("reports/index.json")
    report_date = ""
    if index and index[0] == 200:
        try:
            rows = read_json(index[1])
            if isinstance(rows,list) and rows and isinstance(rows[0],dict):
                report_date = str(rows[0].get("date", ""))
        except (ValueError,TypeError,UnicodeError):
            pass
    # Do not retrieve arbitrary remote paths: date MUST be YYYY-MM-DD.
    if len(report_date) == 10 and report_date[4:5] == "-" and report_date[7:8] == "-" and (
        report_date.replace("-", "").isdigit()):
        snapshot["report"] = public_get(BASE + "reports/" + report_date + ".json?autopilot=1")
    snapshot["config"] = public_get(BASE + "cloud-config.json?autopilot=1")
    # Public publishable key is intentionally browser-safe, but never print it.
    try:
        config = read_json(snapshot["config"][1]) if snapshot["config"][0] == 200 else {}
        url = config.get("supabase_url", "")
        key = config.get("anon_key", "")
        if not isinstance(url, str) or not isinstance(key, str) or (
            url != json.loads((ROOT / "site/cloud-config.json").read_text("utf-8")).get("supabase_url")):
            raise ValueError("Cloud project URL is not the expected project")
        url = url.rstrip("/")
        snapshot["auth"] = public_get(url + "/auth/v1/health", {"apikey": key})
        snapshot["anonymous"] = public_get(
            url + "/rest/v1/vocabulary_events?select=event_id&limit=1",
            {"apikey": key},
        )
    except (ValueError, TypeError, OSError, URLError):
        # evaluate() reports cloud failures without accidentally logging keys.
        pass
    return evaluate(snapshot, expected)

def run() -> int:
    today = datetime.now(HK).date().isoformat()
    outcome = None
    for attempt in range(2):
        try:
            outcome = check_once(today)
        except (OSError,URLError,ValueError) as exc:
            outcome = (["Live health check could not complete: " + type(exc).__name__], [], [])
        if not outcome[0] or attempt == 1:
            break
        print("Transient verification error, retrying once after 8 seconds")
        time.sleep(8)
    errors, warnings, checks = outcome
    lines = [
        "### V1 final maintenance health (Hong Kong)",
        f"- Expected article date: {today}",
        f"- Public site: {BASE}",
        f"- Outcome: {'PASS' if not errors else 'FAIL'}",
        "- Scope: PUBLIC checks only; private-user sign-in and personal data are not accessed",
    ]
    lines += ["- PASS: " + x for x in checks]
    lines += ["- WARNING: " + x for x in warnings]
    lines += ["- FAIL: " + x for x in errors]
    text = "\n".join(lines) + "\n"
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as output:
            output.write(text)
    if errors:
        # Explicit GitHub annotations make Action failures easy to diagnose.
        for err in errors:
            print("::error::" + err.replace("\n"," ").replace("\r"," ")[:240])
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(run())

"""Evidence-limited reading exercises for the no-paid-API fallback.

These paragraphs contain questions and analytical methods, not purportedly
verified new developments. They must never be described as independent news.
"""
from __future__ import annotations
import re

PROMOTIONAL_PATTERNS = (
    re.compile(r"\b(register now|buy (?:a|your) ticket|early.bird tickets|save up to \$\d+|grab (?:a|your) (?:second )?pass|join us at .{0,35}(?:summit|conference)|sponsor(?:ed)? post)\b", re.I),
    re.compile(r"\b(?:hear from|meet) .{0,90}\b(?:at|during) (?:techcrunch )?disrupt\b", re.I),
    re.compile(r"\b(?:roundtables?:|register for|join (?:our|senior|the) .{0,55}(?:reporter|conversation|roundtable)|tickets (?:are|available)|early-bird pricing)\b",re.I),
)

def is_promotional(title: str, excerpt: str) -> bool:
    """Exclude event sales pitches, not ordinary reports on AI conferences."""
    combined = f"{title} {excerpt}"
    return any(pattern.search(combined) for pattern in PROMOTIONAL_PATTERNS)

def _word_count(text: str) -> int:
    return len(re.findall(r"\b[A-Za-z]+(?:['’-][A-Za-z]+)*\b", text))

def deepen_digest(paragraphs: list[str], stories: list[dict], target: int = 550) -> list[str]:
    """Add a clearly educational evidence-evaluation segment if space allows.

    Do not manufacture facts to reach a target length. Publishing metadata must
    continue labelling the complete piece as a source digest, not verified news.
    """
    if not paragraphs or len(stories) < 2:
        return paragraphs
    if _word_count(" ".join(paragraphs)) >= target:
        return paragraphs
    topics = {s.get("topic", "") for s in stories}
    focus = (
        "For research-related announcements, ask how the result was tested, whether the evaluation was independent, "
        "and which limitations remain unknown from the short source description. A preprint, in particular, "
        "is not necessarily a peer-reviewed finding."
        if "Research" in topics else
        "For commercial announcements, distinguish a proposal or publicity claim from an independently measured outcome. "
        "Ask what was actually released, who can use it, and which details the short extract does not establish."
    )
    first = (
        "Critical reading lens — The original links are important because an RSS headline captures only part "
        "of an event. Identify the exact statement attributed to the publisher, then separate it from "
        "plausible but unconfirmed interpretation. " + focus
    )
    second = (
        "DSE inference practice — Compare two reports in this edition. Which one supplies a more specific "
        "description of evidence, and which asks the reader to trust a broader claim? Explain how a missing "
        "method, date, limitation or opposing viewpoint could change your judgement. Strong analysis does "
        "not mean treating uncertainty as proof of failure: it means deciding what information would genuinely "
        "settle the question. Such reasoning is an English-learning exercise, not an additional news report."
    )
    extras = []
    for passage in (first, second):
        if _word_count(" ".join(paragraphs + extras)) < target and _word_count(" ".join(paragraphs + extras + [passage])) <= 665:
            extras.append(passage)
    return paragraphs + extras

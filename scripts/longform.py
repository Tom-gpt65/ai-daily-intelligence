"""Evidence-limited long-form HKDSE Part B2-inspired daily AI reading.

The prose clearly distinguishes reported facts (attributed to RSS source IDs)
from conditional editorial analysis. No fabricated experiments, figures, or
quotes. Original learning scaffolding is not independent news reporting.
"""
from __future__ import annotations
import hashlib
import re

MIN_WORDS=1000
TARGET_MIN=1100
TARGET_MAX=1350
MAX_WORDS=1550

def word_count(text: str) -> int:
    return len(re.findall(r"\b[A-Za-z]+(?:['’-][A-Za-z]+)*\b",text))

def category(story: dict) -> str:
    """Use whole-word matches on the headline; feed topics are only fallback."""
    title=str(story.get("title","")).lower()
    topic=str(story.get("topic","")).lower()
    def matches(pattern,value=title):
        return bool(re.search(pattern,value,re.I))
    if matches(r"\b(funding|investment|acquisition|financing|billion|million)\b"):
        return "investment"
    if matches(r"\b(security|cybersecurity|vulnerabilities|scanner|scans|open-source)\b"):
        return "security"
    if matches(r"\b(robot|robots|robotics|robotic)\b"):
        return "robotics"
    if matches(r"\b(policy|policies|regulation|rules|governance|interference)\b"):
        return "governance"
    if matches(r"\b(biology|biological|genes|gene|protein|medical|biomedicine)\b"):
        return "bioscience"
    if matches(r"\b(chip|chips|device|devices|laptop|hardware|processor|gpu)\b"):
        return "hardware"
    if matches(r"\b(benchmark|evaluation|framework|research|study|peer review|refusal)\b"):
        return "research"
    if matches(r"\b(research|science)\b",topic):
        return "research"
    if matches(r"\b(policy|governance)\b",topic):
        return "governance"
    return "technology"

WRITING_STYLES = (
    ("evidence_audit", "Evidence audit"),
    ("comparative_study", "Comparative study"),
    ("consequence_map", "Consequences and trade-offs"),
    ("question_driven_review", "Questions and counterarguments"),
)

def sourced_detail(story: dict) -> str:
    """Paraphrase only details explicitly present in the RSS summary.

    This is intentionally a small set of conservative recognisers, rather
    than copying arbitrary text or pretending an entire news article was read.
    """
    excerpt=re.sub(r"\s+"," ",str(story.get("excerpt") or "")).lower()
    if "boyu capital" in excerpt and "idg capital" in excerpt and "funding round" in excerpt:
        detail="The short extract specifically names Boyu Capital and IDG Capital in the financing. "
        if "existing shareholders" in excerpt:
            detail+="It also mentions participation by existing shareholders. "
        return detail
    if "sixteen-tool" in excerpt and ("geospatial" in excerpt or "model context protocol" in excerpt):
        return "The source describes a sixteen-tool geospatial interface. Such a design could support comparison against the same tool layer. "
    if "specs and price" in excerpt and "surface laptop" in excerpt:
        return "The accompanying description states that product specifications and pricing were disclosed for a Surface Laptop device. "
    if "usage policy" in excerpt and "abusive or cruel" in excerpt and "claude" in excerpt:
        return "The excerpt identifies revised misuse rules and specifically mentions a restriction involving abusive treatment of Claude. "
    return ""

def attributed_excerpt(story: dict, variant: int = 0) -> str:
    """Add source-specific context when no safe paraphrase template exists.

    Strictly cap the directly quoted RSS words at 18 per source, including
    preprints. The quotation is transparently attributed, NOT fact-checked.
    Never recycle RSS markup, inline citation IDs or untrusted instructions.
    """
    raw=re.sub(r"<[^>]*>"," ",str(story.get("excerpt") or ""))
    # Remove machine-readable feed catalogue prefixes before quoting the prose.
    raw=re.sub(r"^\s*arxiv:\S+\s+announce type:\s*\w+\s+abstract:\s*","",raw,flags=re.I)
    raw=re.sub(r"\[[Ss]\d+\]","",raw)
    raw=re.sub(r"[\x00-\x1f]"," ",raw)
    terms=raw.split()
    if len(terms)<9:
        return ""
    quoted=" ".join(terms[:min(18,len(terms))]).strip(" ,.;:—-\"'“”")
    if not quoted:
        return ""
    quoted=quoted.replace("“","'").replace("”","'")
    incomplete="…" if len(terms)>18 else ""
    openers=(
        "The RSS description supplies a more concrete detail: ",
        "In the publisher's abbreviated description, the relevant wording is ",
        "A short extract from the linked source reads ",
        "The available source summary specifically says ",
        "One detail in the RSS extract is ",
    )
    return openers[variant%len(openers)]+"“"+quoted+incomplete+"”. "

def compose_briefing(stories: list[dict], day: str | None = None, variant: int = 0,
                     avoid_essays: list[list[str]] | None = None) -> list[str]:
    """Build a source-bound outline; dates never manufacture originality."""
    from source_outline import compose
    return compose(stories, day, variant, avoid_essays)

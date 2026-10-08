"""Original HKDSE Paper 1 B2-inspired questions anchored to each day's actual text.

Never pass these as official HKEAA examination questions. Automatic marking is
limited to questions with a single explicitly justified answer; writing tasks
always disclose that human judgement is needed.
"""
from __future__ import annotations
import hashlib
import re

VOCAB = {
    "provisional": ("subject to revision", ("officially authorised", "already conclusive", "irrelevant to the debate")),
    "scrutiny": ("close and critical examination", ("financial subsidy", "public endorsement", "immediate implementation")),
    "qualified": ("expressed with reservations", ("professionally trained", "publicly celebrated", "freely accessible")),
    "substantiate": ("support with convincing evidence", ("challenge for its own sake", "describe in simple terms", "distribute widely")),
    "credible": ("worthy of belief", ("commercially profitable", "widely available", "technically complicated")),
    "limitations": ("restrictions or weaknesses", ("unexpected benefits", "accepted conclusions", "financial incentives")),
    "implications": ("possible consequences", ("original instructions", "proven statistics", "unrelated examples")),
    "tentative": ("not yet definite", ("financially supported", "legally binding", "historically established")),
    "scepticism": ("a questioning attitude", ("unreserved admiration", "formal permission", "intentional deception")),
    "nuanced": ("attentive to subtle differences", ("easily verified", "always negative", "technologically advanced")),
    "conclusive": ("sufficient to settle the issue", ("preliminary in nature", "widely controversial", "difficult to understand")),
}
STOP = {"the", "this", "that", "what", "whose", "with", "which", "where", "when", "has", "have"}

def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)*", text)

def paragraph_at(essay, term: str):
    for i, para in enumerate(essay):
        if re.search(r"\b" + re.escape(term) + r"\b", para, re.I):
            return i
    return None

def cite_location(n: int) -> str:
    return f"Paragraph {n + 1}"

def quote_sentence(essay, n: int, keyword: str = ""):
    if n is None or not 0 <= n < len(essay):
        return ""
    text = re.sub(r"\s+", " ", essay[n]).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chosen = next((line for line in sentences if not keyword or re.search(r"\b"+re.escape(keyword)+r"\b", line, re.I)), text)
    return " ".join(chosen.split()[:27]).rstrip(",.; ")[:220]

def rotate(options: list[str], correct: int, salt: str):
    shift = int(hashlib.sha256(salt.encode("utf-8")).hexdigest()[:8], 16) % len(options)
    return options[shift:] + options[:shift], (correct - shift) % len(options)

def item_mc(ident: str, skill: str, stem: str, answers: list[str], correct: int,
            why: str, evidence: str, paragraph: int, date: str, quote: str):
    options, answer = rotate(answers, correct, date + ident)
    return {"id": ident, "type": "mc", "skill": skill, "marks": 1, "stem": stem,
            "options": options, "answer": answer, "explanation": why,
            "evidence": evidence, "paragraph": paragraph + 1, "evidence_quote": quote}

def make_exam(essay: list[str], stories: list[dict], date: str) -> dict:
    """Return 7 source/paragraph-linked daily questions when possible.

    Deliberately prefer an open response over an invalid auto-graded question.
    This is a short practice set, not a complete B2 examination.
    """
    if not essay:
        return {"label": "閱讀練習暫不可用", "official": False, "items": []}
    full = "\n".join(essay)
    source_matches = []
    for story in stories:
        ident = story.get("id", "")
        index = next((i for i, p in enumerate(essay) if f"[{ident}]" in p), None)
        if index is not None:
            source_matches.append((story, index))

    items = []
    marker = paragraph_at(essay, "evidence")
    if marker is None:
        marker = paragraph_at(essay, "uncertainty")
    if marker is not None:
        items.append(item_mc("Q1", "Writer's purpose / interpretation",
          "What is the most defensible reading of the writer's treatment of evidence?",
          ["Evidence must be weighed against the limits of what the report actually establishes.",
           "The writer considers a recent announcement sufficient proof of future success.",
           "A publisher's popularity provides a reliable substitute for evaluating claims.",
           "The writer treats all uncertain claims as demonstrably false."], 0,
          "A careful reading distinguishes reported claims from conclusions that are independently supported.",
          cite_location(marker), marker, date, quote_sentence(essay, marker, "evidence")))

    chosen = next(((term, meta, paragraph_at(essay, term)) for term, meta in VOCAB.items()
                   if paragraph_at(essay, term) is not None), None)
    if chosen:
        term, (meaning, distractors), idx = chosen
        items.append(item_mc("Q2", "Vocabulary in context",
            f"Which option best conveys the meaning of '{term}' as it is used in {cite_location(idx).lower()}?",
            [meaning, *distractors], 0,
            "Read the surrounding sentence; the word takes this sense in the present argument.",
            cite_location(idx), idx, date, quote_sentence(essay, idx, term)))

    tone_keywords = ("however", "although", "yet", "nevertheless", "uncertain", "careful", "provisional",
                     "cautious", "qualified", "limitations", "scepticism")
    tone_idx = next((paragraph_at(essay, term) for term in tone_keywords if paragraph_at(essay, term) is not None), None)
    if tone_idx is not None:
        tone_word = next((term for term in tone_keywords if re.search(r"\b"+term+r"\b", essay[tone_idx], re.I)), "")
        items.append(item_mc("Q3", "Writer's tone / attitude",
            f"What attitude is best supported by the writer's language in {cite_location(tone_idx).lower()}?",
            ["Measured and questioning, with qualifications rather than outright dismissal.",
             "Unreservedly celebratory about the proven success of every report.",
             "Indifferent to whether supporting evidence can be obtained.",
             "Personally hostile towards the individuals mentioned in the article."], 0,
            "The hedging or contrast signals a qualified judgement, not certainty.",
            cite_location(tone_idx), tone_idx, date,
            quote_sentence(essay, tone_idx, tone_word)))

    if len(source_matches) >= 3:
        chosen_idx = int(hashlib.sha256(date.encode()).hexdigest()[:6],16) % len(source_matches)
        story, p = source_matches[chosen_idx]
        other = [(s, i) for s, i in source_matches if s["id"] != story["id"]]
        alternatives = [f"An account concerning: {s['title'][:96]}" for s, _ in other[:3]]
        while len(alternatives) < 3:
            alternatives.append(["A general claim unsupported by any cited report",
                                 "A claim about an unrelated industry",
                                 "A conclusion presented without a source"][len(alternatives)])
        items.append(item_mc("Q4", "Locating and selecting information",
            f"Which report is identified by the source reference in {cite_location(p).lower()}?",
            [f"An account concerning: {story['title'][:96]}", *alternatives], 0,
            "The source reference identifies the cited report; the article does not thereby verify all its claims.",
            cite_location(p), p, date, quote_sentence(essay,p)))

    # Replace ungrounded machine-scored items with marked-by-reader tasks.
    slots = {q["id"]: q for q in items}
    templates = {
      "Q1": ("Main theme / purpose", "Explain the writer's main purpose in TWO points, using wording from the opening or conclusion."),
      "Q2": ("Vocabulary and inference", "Choose an advanced expression in the text and explain its contextual meaning and the writer's intended effect."),
      "Q3": ("Attitude and tone", "Identify the writer's attitude, quoting TWO words or phrases to support your interpretation."),
      "Q4": ("Source comparison", "Identify the specific source cited in a paragraph of your choice, and explain what the passage does and does not establish about it.")
    }
    for ident in ("Q1","Q2","Q3","Q4"):
        if ident not in slots:
            skill, stem = templates[ident]
            slots[ident] = {"id": ident, "type": "short", "skill": skill, "marks": 2, "stem": stem,
                "guidance": ["State a defensible interpretation of the passage (1 mark).",
                             "Support it with a relevant, accurately quoted phrase or paraphrase (1 mark)."],
                "evidence": cite_location(0), "paragraph": 1,
                "evidence_quote": quote_sentence(essay,0)}
    items = [slots[ident] for ident in ("Q1","Q2","Q3","Q4")]

    contrast = next((i for i,p in enumerate(essay) if re.search(r"\b(?:although|whereas|however|yet|rather than|but|nevertheless)\b",p,re.I)),None)
    contrast = contrast if contrast is not None else min(1,len(essay)-1)
    items.append({"id":"Q5","type":"short","skill":"Language features / contrast","marks":2,
        "stem":f"How does the writer use contrast or qualification in {cite_location(contrast).lower()} to shape the argument? Give ONE specific example.",
        "guidance":["Identify a relevant contrast or qualification in the specified paragraph (1 mark).",
                    "Explain its impact on the writer's overall argument rather than merely repeating the phrase (1 mark)."],
        "evidence":cite_location(contrast),"paragraph":contrast+1,"evidence_quote":quote_sentence(essay,contrast)})
    ref_index = source_matches[0][1] if source_matches else min(1,len(essay)-1)
    items.append({"id":"Q6","type":"short","skill":"Inference and evidence","marks":2,
        "stem":f"Identify ONE important conclusion that CANNOT safely be drawn from {cite_location(ref_index).lower()} and explain why.",
        "guidance":["Specify a plausible conclusion which the extract does not establish (1 mark).",
                    "Explain the missing evidence or methodological limitation (1 mark)."],
        "evidence":cite_location(ref_index),"paragraph":ref_index+1,
        "evidence_quote":quote_sentence(essay,ref_index)})
    if len(source_matches)>=2:
        s1,p1=source_matches[0];s2,p2=source_matches[1]
        stem=(f"Compare the significance and evidential limitations of [{s1['id']}] and [{s2['id']}]. "
              "Explain how the writer links them to the wider argument. (60–90 words)")
        evidence=f"{cite_location(p1)} and {cite_location(p2)}"
        sample=quote_sentence(essay,p1)+" / "+quote_sentence(essay,p2)
    else:
        p1,p2=0,len(essay)-1
        stem="Compare the opening and concluding arguments. How does the writer develop or qualify the initial position? (60–90 words)"
        evidence=f"{cite_location(p1)} and {cite_location(p2)}"
        sample=quote_sentence(essay,p1)+" / "+quote_sentence(essay,p2)
    items.append({"id":"Q7","type":"extended","skill":"Cross-text synthesis / evaluation","marks":4,
      "stem":stem,
      "guidance":["Accurately interpret both passages or cited source accounts (2 marks).",
                  "Make an explicit analytical connection rather than list unrelated facts (1 mark).",
                  "Specify one justified limitation or condition affecting the conclusion (1 mark)."],
      "evidence":evidence,"paragraph":p1+1,"evidence_quote":sample[:310]})
    return {"label":"HKDSE Paper 1 Part B2-inspired daily practice",
            "official":False,"basis":"HKEAA 2026 English Language Assessment Framework, Reading objectives",
            "instructions":"Original exercises. MC questions have answer keys; written responses need human judgement.",
            "items":items}

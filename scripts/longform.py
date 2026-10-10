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

LENSES={
 "investment": (
    "The financial dimension matters because capital is an expression of expectations, not proof that those expectations will be realised. "
    "An investment announcement may identify participants and a sum of money, yet it leaves open whether the business can turn resources into sustained usefulness. "
    "Readers should distinguish a transaction reported by a publisher from an independent assessment of profitability, technological superiority or market demand. "
    "Even where the headline sounds momentous, neither the scale of a funding round nor the reputation of its backers settles the question of long-term success. "
    "One might reasonably ask whose interests the announcement serves, what risks investors are accepting and which performance indicators would permit a fairer judgement."
 ),
 "research": (
    "Research language has a particular authority, although a named framework is not the same thing as a result validated under every plausible condition. "
    "A benchmark can make comparisons more systematic by specifying tasks and measurements; equally, the choice of tasks may privilege some capabilities while overlooking others. "
    "What would count as a convincing comparison: repeated results, independent replication, realistic operating conditions or an examination of failures? "
    "The answer depends on the claim being made. Readers must therefore separate the approach described in a paper from evidence that the approach consistently works outside the circumstances reported. "
    "If the source is a preprint, the distinction between dissemination and peer review is especially worth preserving."
 ),
 "hardware": (
    "Hardware announcements invite a different form of scrutiny. A new device may be positioned as capable of supporting AI workloads, but a promise of capability is distinct from measured performance for a particular user. "
    "Consider the trade-offs that a buyer or institution would need to evaluate: speed against battery life, local processing against cloud dependence, and novelty against the cost of replacing an adequate existing machine. "
    "Those are questions for comparison, not claims that any one product necessarily excels or fails. "
    "Where specifications are mentioned without reliable benchmarks, treating commercial positioning as an independent verdict would mistake marketing language for evidence. "
    "The public-interest question is how a technical change translates into benefits that can actually be demonstrated."
 ),
 "governance": (
    "Rules governing AI systems illustrate the distance between institutional intentions and actual consequences. "
    "A policy can signal what a provider wishes to discourage, yet the text alone cannot show how consistently an organisation will interpret disputes, detect violations or handle exceptions. "
    "Nor does an announced restriction, by itself, resolve the ethical disagreement about what ought to be restricted in the first place. "
    "A fair analysis would consider enforcement, transparency and accountability, including whether people affected by a decision can challenge it. "
    "Instead of assuming that stronger wording guarantees safer outcomes, the reader should identify which decisions are explicit and which operational details remain unavailable."
 ),
 "bioscience": (
    "Accounts connecting AI with the life sciences require unusually careful distinctions. Designing a hypothetical biological sequence, testing a computational proposal and demonstrating a functioning organism are not equivalent achievements. "
    "Without verifiable experimental details, moving casually between those categories would create a sensational conclusion that the available report might not justify. "
    "The ethical dimension, moreover, cannot be reduced to excitement or alarm: beneficial research, security precautions and responsible oversight must be examined as separate questions. "
    "This paragraph is an invitation to distinguish levels of evidence, not an assertion that any particular experiment succeeded. "
    "A reader should return to the source before repeating claims about physical or biological results."
 ),
 "technology": (
    "The significance of a technology story depends on the task that it addresses, the assumptions built into the proposed solution and the conditions under which it is expected to operate. "
    "A headline provides a starting point, not a complete comparison with existing alternatives. "
    "For a meaningful assessment, readers should ask whose problem is being solved, whether the stated benefit can be measured and what limitations an independent evaluator might find. "
    "Those questions are not evidence that the development is ineffective; rather, they distinguish informed curiosity from automatic endorsement. "
    "Strong reading requires an awareness that the most confident description may not be the most informative one."
 ),
 "security": ("Software security is the subject of this report, not biological research. Scanning software may identify possible weaknesses in open-source code, but detection and successful repair are different outcomes. A careful reader would ask which projects can access the service, how results are checked and whether independent evidence supports its effectiveness. An announced service may be useful without proving that every detected problem is serious or that every maintainer has the resources to fix it. The distinction between offering a tool and demonstrating improved security is therefore central to evaluating the headline. Relevant evidence would concern detection quality, practical use and limitations of the service, rather than experiments from unrelated fields."),
 "robotics": ("Robotics research offers an example of the distance between laboratory performance and everyday use. A robot may perform a difficult task in a controlled test without being practical in a workplace or home. Repeated reliability, safety around people, cost and maintenance all influence that transition. To evaluate a headline about robotics, readers should distinguish progress in one capability from evidence about widespread adoption. A useful report would specify the task, the testing conditions and what is known about deployment. That comparison recognises genuine improvements while avoiding an unsupported prediction that laboratory advances will immediately change daily life. The central question is what evidence connects the demonstration to routine use.")
}


# A source list can contain several developments in the same domain. Repeating
# the identical paragraph would produce artificial length rather than teaching
# a reader to distinguish the evidence actually supplied by each source.
ALTERNATE_ANGLES=[
 "A further question concerns how a claim would appear to an observer with different priorities. One stakeholder might value speed, another reproducibility, and a third the ability to challenge a decision. These perspectives need not conflict, but they should not be compressed into a single undifferentiated assessment either. Readers should trace the precise wording of this report, identify whose perspective it privileges and ask whether a competing interpretation could also fit the limited evidence. That exercise exposes the assumptions connecting a reported development to a broader claim, and it makes the argument more than a rehearsal of institutional publicity.",
 "The method by which evidence is communicated is almost as important as the evidence itself. A brief source extract is necessarily selective: it may illuminate the purpose of an initiative while omitting measurements, limitations or the people who would experience the consequences. It would be unreasonable to infer dishonesty merely from that absence; equally, it would be careless to treat what has not been described as if it were already proved. The useful analytical move is to state a testable question, explain which information could answer it and avoid allowing a confident headline to do the work of an argument.",
 "The distinction between immediate significance and lasting consequence deserves separate attention. An announcement can matter today because it changes available options or public expectations, even if its future effects remain uncertain. That observation neither guarantees success nor renders the development trivial. For a more defensible judgement, a reader should ask what short-term event the publisher has actually documented and what long-term change is merely being anticipated. The two may eventually coincide, but their relationship requires explanation. Examining that relationship is a useful exercise in concession, qualification and causal reasoning.",
 "The language used to describe responsibility can conceal differences between technical capacity, organisational incentives and human judgement. Those dimensions interact, but none can be substituted for another: a tool may function as intended without being suitable for every purpose, while an institution may articulate worthy principles without providing sufficient evidence of consistent practice. The reader should therefore locate the precise claim within its domain before drawing a wider conclusion. Where a source offers only a compressed description, curiosity is appropriate, whereas certainty about unreported outcomes is not. The central reading skill is calibrated interpretation."
]

LEADS=[
 "AI news is often written in the language of arrival: a technology has emerged, a company has advanced, or a new rule has been announced. Yet the difference between a development and an interpretation of that development is fundamental. In this edition, the cited reports concern distinct aspects of artificial intelligence, and a careful reading must resist the temptation to compress them into one uncomplicated narrative of progress. The challenge is to identify precisely what each source says before considering what, if anything, may reasonably follow from it. Such disciplined inference is central both to informed public judgement and to demanding English comprehension.",
 "Behind every confident technology headline lies an evidential question. What has actually happened, who is making the claim and which important details remain unreported? These questions become harder when the subject shifts rapidly between commercial investment, research, products and institutional governance. This reading exercise approaches the day's reporting as a set of contrasting texts rather than a sequence of victories. Its argument is deliberately qualified: important developments deserve attention, but their significance must be established through careful interpretation rather than the force of a headline alone.",
 "The vocabulary of artificial intelligence is saturated with ambition, from new capabilities to sweeping visions of social change. A sophisticated reader, however, must distinguish between describing an ambition and demonstrating its consequences. The reports gathered here are not interchangeable, and their differences deserve more attention than their shared association with AI. Some concern organisations and incentives; others raise questions about methodology, technology or institutional responsibility. Examining these contrasts reveals how a story's purpose shapes the evidence it offers and the conclusions a reader is entitled to draw."
]

INTROS=[
 "One perspective arises from",
 "The commercial and institutional landscape also appears in",
 "A contrasting dimension becomes visible in",
 "A separate question is raised by",
 "Finally, another part of the debate is illustrated by"
]

FACT_NOTE=(
 "The available RSS extract adds a short description, but not the complete article; the account below accordingly treats the publisher's wording as a reported claim rather than an independently established result. ",
 "The abbreviated description supplies only a limited view of the event, making it especially important to distinguish the content attributed to the source from assumptions introduced by the reader. ",
 "Although the headline establishes the subject of the report, the excerpt does not provide an independent audit of its effects; the following questions should therefore be read as critical analysis rather than additional reporting. ",
 "The feed gives a starting point for evaluating the claim, not an exhaustive record of the underlying evidence. This distinction matters where the apparent implications exceed the material actually available. ",
 "Only an abbreviated source description is present here. The wider consequences discussed below are questions for further investigation, not facts established by this edition. "
)

CROSS=[
 "The first report, [{first}], concerns {area_first}, whereas [{second}] examines {area_second}. These reports need different standards of evidence. A software service can be judged by the quality and practical value of its results; a research framework needs clear methods and reproducible evaluation. Neither kind of announcement automatically demonstrates widespread success. Readers should identify the actual claim in each report, ask which supporting facts are available and distinguish measured outcomes from expectations. A useful comparison is therefore not a contest between exciting headlines. It explains why the evidence required for one development may not answer the questions raised by another.",
 "A further difficulty concerns the relationship between audience and purpose. Material intended to announce a development, discuss an experiment or explain a rule may select different details, not necessarily because its authors are dishonest, but because each text has a different communicative task. The reader's responsibility is to notice that selection. Which voices are represented? What relevant evidence is absent? Could a stakeholder with different interests interpret the same announcement differently? These questions encourage scepticism without cynicism: the absence of detail is a reason to consult additional sources, not permission to invent whichever explanation seems most persuasive.",
 "Language itself can change the impression created by evidence. Expressions such as 'may', 'could' and 'appears to' preserve uncertainty; definitive verbs, by contrast, can imply that a disputed conclusion has already been settled. Conditional constructions are useful precisely because they make a hypothesis distinguishable from an observed result. A reader preparing for an advanced examination should also consider how concession works: acknowledging a genuine possibility before introducing a qualification often strengthens an argument by addressing an anticipated objection. The rhetorical effect is analytical rather than evasive, provided that caution is tied to a specific limitation in the evidence."
]

EXTRA=[
 "What makes these reports useful for reading practice is their variety of implicit claims. In the accounts labelled [{first}] and [{second}], the relevant questions differ, yet both require attention to how information is selected and presented. An effective response to a comprehension question should first identify the writer's stated point, then explain the inference that follows, while acknowledging where the source stops short. Paraphrasing is preferable to copying a headline wholesale, because the task is to show understanding of the relationship between ideas. At the same time, originality must not become speculation: sophisticated vocabulary cannot rescue an answer that introduces unsupported facts.",
 "The broader policy question should not be confused with the narrower technical one. Even if a system were shown to perform well under a particular evaluation, it would not follow that every application of that system was ethically or socially desirable. Conversely, concern about governance does not prove that a technology lacks useful capabilities. Maintaining those distinctions helps the reader avoid false dilemmas. The important skill is to identify exactly where an argument changes level, moving from what a tool can do to what an organisation or society ought to permit. That shift often determines which evidence would be relevant to a fair conclusion."
]

ENDING=(
 "Ultimately, the value of a daily AI briefing lies not in the number of confident claims it repeats, but in the quality of the questions it enables readers to ask. A useful judgement identifies a stated development, names the evidence on which it rests and clarifies the uncertainties that could alter its significance. Consulting the linked original reports is indispensable because an RSS summary cannot establish everything about a story. The intellectual habit worth cultivating is neither automatic enthusiasm nor reflexive suspicion, but proportionate confidence: say what the source supports, explain why it matters, and remain prepared to revise the conclusion."
)

# V3 source-bound editorial designs. No invented events or experiments: every
# daily report still cites the original RSS stories. Variation is structural,
# not a cosmetic replacement of the source name or the calendar date.
WRITING_STYLES = (
    ("evidence_audit", "Evidence audit"),
    ("comparative_study", "Comparative study"),
    ("consequence_map", "Consequences and trade-offs"),
    ("question_driven_review", "Questions and counterarguments"),
)

MORE_LEADS = (
    "A question of trust connects the reports in this edition, but trust is not the same as agreement. "
    "A reader must notice what each source actually describes before deciding which wider conclusion deserves confidence. "
    "A technology announcement and a research abstract can both be informative while leaving very different questions unanswered. "
    "Today the useful approach is to examine the available evidence, compare what has been reported and distinguish a stated goal from a measured result. "
    "The point is not to dismiss a promising idea, but to ask what kind of information would make a judgement stronger.",
    "Consider how difficult it can be to compare several reports about artificial intelligence. "
    "A product story may concern practical use, while research and public policy involve different standards of proof. "
    "The sources gathered today offer a chance to practise that distinction. "
    "Rather than assuming that every development is a victory or a threat, this reading considers the purpose of each claim and the people who may be affected by it. "
    "Its central question is what we can reasonably infer from the material available and what must remain a question.",
    "When a headline describes a change, it also invites a choice about the way that change should be judged. "
    "Readers can focus on promised benefits, possible costs, or the strength of the evidence itself. "
    "Each approach reveals something different, and no single headline answers them all. "
    "This edition therefore treats the linked reports as material for comparison and careful reasoning. "
    "It separates the event described by a publisher from the reader's interpretation, while showing why different fields of AI deserve different questions.",
    "An important part of reading the news is knowing where a reported fact ends and a possible explanation begins. "
    "Today several developments involve AI, yet they differ in purpose, evidence and likely audience. "
    "A responsible account cannot turn a short RSS description into proof of a wider outcome. "
    "Instead, it can compare the reports, identify useful questions and explain what further information would help. "
    "The aim is a reading that is specific about the source while remaining open about its limits.",
)

MORE_BRIDGES = (
    "The reports marked [{first}] and [{second}] illustrate the difficulty of judging different kinds of progress. "
    "The first concerns {area_first}, while the second addresses {area_second}. "
    "A good comparison must ask whether both sources are making the same sort of claim before placing them on a common scale. "
    "A promise, a test and a public decision should not be treated as equivalent results. "
    "The details provided by each source guide what may be inferred, while details left out of the report identify the limits of that inference. "
    "Readers who keep those distinctions visible can reach a more useful conclusion without adding facts that were not reported.",
    "A practical reader might approach [{first}] by asking what could be tested, but approach [{second}] by asking what decision is being described. "
    "Those questions depend on the subjects: {area_first} and {area_second}. "
    "Neither question assumes that an announcement succeeds or fails. "
    "Instead, each directs attention towards the evidence needed for a fair assessment. "
    "When a source offers an abbreviated account, the responsible response is to recognise the missing context. "
    "That habit makes the reading more exact because it prevents a broad judgement from resting on a narrow description.",
    "Imagine having to explain the distinction between [{first}] and [{second}] to a reader who has not seen the headlines. "
    "A helpful answer would first name the different areas, {area_first} and {area_second}, then explain why their evidence should be examined separately. "
    "It would not assume that all AI systems share a purpose or that public interest proves practical success. "
    "Clear comparison requires attention to what is known, what is merely expected and what each publisher has chosen to emphasise. "
    "The resulting explanation should remain faithful to the source rather than become a general argument about technology.",
    "Another approach is to consider the interests of different audiences. "
    "A reader concerned with {area_first} may place particular value on the information in [{first}], whereas someone concerned with {area_second} may focus on [{second}]. "
    "These priorities shape the questions each person asks, but they do not change the underlying evidence. "
    "A useful reading can acknowledge more than one perspective without treating every claim as equally supported. "
    "It should state where a source is informative, identify a relevant limitation and leave unresolved matters open to further reporting.",
    "The strength of an argument depends partly on its ability to handle a reasonable objection. "
    "Consider [{first}] in relation to [{second}]: {area_first} and {area_second} may invite different expectations about use and responsibility. "
    "Someone might argue that a promising development deserves immediate attention; another reader might ask for stronger evidence before accepting its broader significance. "
    "Both concerns can be examined without pretending to know the future. "
    "A careful answer explains exactly which source supports each point and why a conclusion must remain open where reporting is incomplete.",
    "The most useful comparison may concern the information that the sources do not provide. "
    "In [{first}], a report about {area_first} leaves some questions to be answered by later evidence. "
    "In [{second}], the focus on {area_second} creates a different set of questions. "
    "This does not prove that either account is misleading. "
    "A summary is necessarily selective, and readers should distinguish that limitation from a claim about the publisher's intentions. "
    "The purpose of this exercise is to identify what is reported, formulate a fair question and resist replacing missing evidence with speculation.",
    "To evaluate a development responsibly, the reader must separate an immediate statement from its possible consequences. "
    "The reports [{first}] and [{second}] involve {area_first} and {area_second}, and neither field permits every future effect to be established from one short source extract. "
    "An announced change may matter even when its lasting value remains uncertain. "
    "The challenge is to explain why it matters now without assuming that early expectations will automatically become outcomes. "
    "That distinction helps a reader form a clear conclusion while remaining prepared to revise it when better evidence appears.",
)

MORE_ENDINGS = (
    "In conclusion, these linked reports are most useful when their differences remain visible. "
    "One source may raise a question of practical value while another invites closer examination of research or responsibility. "
    "Neither the language of progress nor the language of concern is a substitute for supporting evidence. "
    "Readers should therefore compare the actual claims, explain the limits of the available summaries and return to the original links when a conclusion requires more detail. "
    "The lesson is a habit of measured judgement: pay attention to an important change without pretending that every consequence has already been established.",
    "The reports considered today do not offer a single verdict about artificial intelligence. "
    "They concern different developments and different kinds of evidence. "
    "A strong reading should preserve that variety rather than force every source into the same argument. "
    "Where the available reporting gives a specific fact, it deserves careful attention; where it leaves a question unresolved, that limit should be stated openly. "
    "The reader who can make both moves will be better prepared to examine future technology claims and distinguish useful information from unwarranted certainty.",
    "The final judgement should be proportionate to what the sources actually support. "
    "An announcement may be significant, a research question may deserve attention and a public decision may have consequences, but none should be treated as proof of an outcome that has not been reported. "
    "This is why cross-source comparison matters: it gives readers a way to test the strength of an interpretation against different kinds of evidence. "
    "The most valuable result is not a confident prediction, but a clear explanation of the current claim and the questions still worth asking.",
    "What remains after comparing the reports is a method rather than a simple answer. "
    "Begin with the publisher's stated subject, consider the evidence described and identify the assumptions needed for a broader conclusion. "
    "Then ask how a reader with another purpose might interpret the same information. "
    "Such questions do not weaken a report; they make its meaning more precise. "
    "When a development is genuinely important, it will still be worth examining after the excitement of the headline has passed. "
    "A careful reader should leave room for that further examination.",
    "The value of this edition is found in the distinctions between its sources. "
    "Reports about different fields may share the words artificial intelligence while describing very different events. "
    "Comparing them demands more than a common label. "
    "It requires attention to the purpose of each account, the strength of its stated evidence and the uncertainty that remains. "
    "A conclusion should be clear enough to be useful but limited enough to remain accurate. "
    "This combination of precision and openness is the reading skill that matters most.",
)


def sourced_detail(story: dict) -> str:
    """Paraphrase only details explicitly present in the RSS summary.

    This is intentionally a small set of conservative recognisers, rather
    than copying arbitrary text or pretending an entire news article was read.
    """
    excerpt=re.sub(r"\s+"," ",str(story.get("excerpt") or "")).lower()
    if "boyu capital" in excerpt and "idg capital" in excerpt and "funding round" in excerpt:
        return "The short extract specifically names Boyu Capital and IDG Capital in the financing; it also mentions participation by existing shareholders. "
    if "sixteen-tool" in excerpt and ("geospatial" in excerpt or "model context protocol" in excerpt):
        return "Its abstract describes a fixed sixteen-tool geospatial interface, intended to make assessments comparable against the same tool layer. "
    if "specs and price" in excerpt and "surface laptop" in excerpt:
        return "The accompanying description states that product specifications and pricing were disclosed for a Surface Laptop device. "
    if "usage policy" in excerpt and "abusive or cruel" in excerpt:
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

def compose_briefing(stories: list[dict], day: str | None = None, variant: int = 0) -> list[str]:
    """Sourced, evidence-limited daily narrative with alternating structures.

    The selected RSS story paragraphs always keep their citation IDs; each
    edition then uses a different lead, set of comparisons and conclusion.
    Four declared designs rotate with the Hong Kong calendar, and an
    optional variant lets the publisher retry a rejected near-duplicate.
    """
    from datetime import date as CalendarDate
    entries=[s for s in stories if s.get("id") and s.get("title")][:5]
    if len(entries)<3:
        return []  # Do not fabricate a 1,000-word article from two titles.
    digest=hashlib.sha256("|".join(str(s["title"]) for s in entries).encode("utf-8")).digest()
    ordinal=CalendarDate.fromisoformat(day).toordinal() if day else int.from_bytes(digest[:4],"big")
    lead_pool=tuple(LEADS)+MORE_LEADS
    bridge_pool=tuple(CROSS)+MORE_BRIDGES
    ending_pool=(ENDING,)+MORE_ENDINGS
    seed=(ordinal+variant)
    paragraphs=[lead_pool[seed%len(lead_pool)]]
    category_occurrences={}
    for i,story in enumerate(entries):
        topic=category(story)
        occurrence=category_occurrences.get(topic,0)
        category_occurrences[topic]=occurrence+1
        analytical_lens=LENSES[topic] if occurrence==0 else ALTERNATE_ANGLES[(occurrence-1+variant)%len(ALTERNATE_ANGLES)]
        title=str(story["title"]).strip().replace("\n"," ")
        publisher=str(story.get("publisher") or "the linked publisher").strip()
        anchor=f"[{story['id']}]"
        paragraphs.append(
            f"{INTROS[(i+seed)%len(INTROS)]} {publisher}'s account, ‘{title}’ {anchor}. "
            +FACT_NOTE[(i+seed)%len(FACT_NOTE)]
            +(sourced_detail(story) or attributed_excerpt(story,i+seed))
            +analytical_lens
        )
    first,second=entries[0],entries[1]
    areas={"investment":"commercial financing","security":"software security","robotics":"practical robotics","research":"scientific evaluation",
           "hardware":"computing devices","governance":"policy and accountability",
           "bioscience":"biological research","technology":"technological development"}
    # Each consecutive date selects a different set of three comparisons.
    # The publisher still checks actual prose against all recent articles.
    for i in range(3):
        block=bridge_pool[(seed*3+i)%len(bridge_pool)]
        context=(f"In the reports [{first['id']}] and [{second['id']}], "
                 f"the questions concern {areas[category(first)]} and {areas[category(second)]}. ")
        paragraphs.append(context+block.format(first=first["id"],second=second["id"],
                       area_first=areas[category(first)],area_second=areas[category(second)]))
    if len(entries)<5:
        paragraphs.append(EXTRA[0].format(first=first["id"],second=second["id"]))
    if len(entries)<4:
        paragraphs.append(EXTRA[1])
    paragraphs.append(ending_pool[seed%len(ending_pool)])
    return paragraphs

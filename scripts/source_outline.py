"""Source-bound reading construction, without word-count filler or date rotation.

Reusable teaching rules are selected by the actual source topic, once only.
Reported facts are limited to attributed titles and an 18-word RSS quotation.
The rest consists of conditional evaluation, never additional reporting.
Unknown or duplicated contexts are rejected rather than padded to 1,000 words.
"""
from __future__ import annotations
import re

PROFILE = "source_outline_v2"
# Each rule has a distinct question, evaluation criterion and unresolved issue.
# These are general generation rules, not dated articles or invented events.
RULES = {
    "security_scanning": (
        r"\b(scanner|scans|vulnerabilities|open-source|cybersecurity)\b",
        "Software security: detection and repair",
        "Software security involves more than finding a suspicious fragment of code. "
        "For a scanning service, a useful assessment would distinguish a warning from a confirmed vulnerability, and a confirmed vulnerability from a completed repair. "
        "If a scanner produced many alerts that maintainers could not reproduce, a larger output might increase the work of checking rather than reduce exposure. "
        "Conversely, a small number of well explained findings could be valuable if developers could verify them and make appropriate changes. "
        "The relevant questions concern the evidence supplied with an alert, the handling of sensitive code and the route from detection to a practical correction. "
        "An offer of free access would remove one possible cost, but it would not settle those operational questions. "
        "Readers should therefore assess the proposed service through the needs of maintainers, whose responsibility would include deciding which findings deserve action.",
        "Consider how a maintainer might test such an offer before relying on it. "
        "A trial could compare findings with issues already understood, record false alarms and examine whether an explanation helps locate the cause. "
        "That would address the usefulness of the scanning process rather than merely its availability. "
        "The distinction also clarifies the limits of the announcement: a description of access is not a record of repaired software."
    ),
    "narrative_refusal": (
        r"\b(narrative wrapping|refusal|cross-language|role-play)\b",
        "Language and safety boundaries",
        "A refusal benchmark poses a question about the stability of a safety boundary when the presentation of a request changes. "
        "If an evaluator altered both the wording and the underlying request, differences in responses would be difficult to interpret. "
        "A stronger comparison would keep the intended action comparable while varying the language or narrative form. "
        "Readers would also need to know how the evaluator identified a refusal and distinguished it from a response that appeared helpful but withheld the requested harmful content. "
        "Translation introduces another difficulty: two expressions may be grammatically similar without carrying the same implication for their audiences. "
        "A cross-language comparison would therefore need attention to meaning as well as matching words. "
        "The research question concerns the consistency of a boundary under different conditions; it should not be converted into a claim that every model, language or defence behaves alike.",
        "One useful follow-up would examine whether an observed pattern persists with unfamiliar requests. "
        "A defence tuned to the examples used in an experiment might respond differently to other narrative forms. "
        "Testing that possibility would require a separate evaluation, with the comparison procedure stated clearly. "
        "Until then, a reader can recognise the importance of the question while reserving judgement about the breadth of any proposed remedy."
    ),
    "usage_policy": (
        r"\b(usage policy|model abuse|election interference|governance|rules and responsibility)\b",
        "Rules, interpretation and enforcement",
        "A usage rule defines an institutional boundary, whereas enforcement concerns how that boundary would be applied to particular conduct. "
        "Those tasks require different evidence. "
        "A reader can examine the wording of a prohibition, but would need additional information to judge whether similar cases receive similar treatment. "
        "Ambiguous cases would raise questions about explanation, appeal and the distinction between a serious violation and ordinary disagreement. "
        "If an organisation relied on automated detection, the consequences of mistaken classification would also deserve attention. "
        "These are questions about the administration of a rule, not allegations that such mistakes have occurred. "
        "The central distinction is between announcing what users must avoid and showing how decisions affecting those users can be scrutinised. "
        "A careful reading leaves room for both a legitimate purpose and a demand for clarity about practical implementation.",
        "To assess accountability, imagine two users asking why their conduct received different decisions. "
        "An intelligible explanation would need to connect the relevant rule to the conduct under review, rather than simply repeat the existence of a policy. "
        "The possibility of such a question illustrates why transparent reasoning matters. "
        "It does not establish how the provider currently manages complaints or whether any particular complaint is justified."
    ),
    "robotics": (
        r"\b(robot|robots|robotics|robotic)\b",
        "Robotics research and everyday conditions",
        "Robotics research raises a practical question about the conditions under which a demonstrated capability would remain useful. "
        "A controlled task and a changing household would present different demands, even if the same movement were involved. "
        "If objects, lighting or human behaviour changed, a user would need to know how the system handled those changes and what happened when it could not complete a task. "
        "Maintenance and supervision would also affect whether a capability reduced work overall. "
        "That perspective helps explain why a striking demonstration should be examined alongside the circumstances that made it possible. "
        "Readers need not dismiss a technical advance to ask about the transition to routine use. "
        "They should distinguish a narrow capability from the wider requirements of dependable operation, including understandable failure handling and appropriate precautions around people. "
        "The missing link is evidence about ordinary conditions, rather than a more dramatic description of the demonstration.",
        "A prospective user might ask which changes in the surroundings require another person to intervene. "
        "If intervention were frequent, apparent autonomy would need to be interpreted cautiously. "
        "If it were rare and predictable, the practical assessment might be different. "
        "Both possibilities point towards information about supervision and recovery, without asserting that the reported research has already met or failed those requirements."
    ),
    "peer_review": (
        r"\b(peer review|scientific publishing)\b",
        "Scientific criticism and responsibility",
        "Peer review concerns the quality of criticism, not simply the production of more comments. "
        "An evaluation of assistance would need to distinguish an observation that identifies a substantive weakness from language that merely sounds like a review. "
        "If a system suggested a methodological objection, the author or reviewer would still need to check whether that objection applied to the actual work. "
        "A benchmark might help organise that examination, but its scoring rules would determine which qualities received credit. "
        "Accuracy, relevance and constructive explanation would require separate attention rather than an assumption that a fluent response achieved them all. "
        "The responsibility for a publication decision would also need to remain clear when machine suggestions entered the process. "
        "This gives the reader a concrete distinction between assistance with scientific criticism and authority to judge a scientific contribution. "
        "The proposed framework should be considered through that distinction before broader expectations are attached to it.",
        "A difficult case would be a polished objection that misunderstood the paper. "
        "Its style could appear persuasive even when its premise was mistaken. "
        "An appropriate evaluation would ask how such errors were identified, and whether reviewers could inspect the reasoning behind a suggestion. "
        "That question connects the quality of the generated criticism to the human judgement required to use it responsibly."
    ),
    "game_commentary": (
        r"\b(game commentary|gamecommbench|esports)\b",
        "Commentary: describing, interpreting and entertaining",
        "Game commentary combines functions that should not be assessed as if they were interchangeable. "
        "Describing a visible action would require attention to what happened, while explaining a strategic choice would involve a different judgement about its significance. "
        "An entertaining remark might serve an audience without adding an accurate explanation of play. "
        "If one overall score combined these purposes, a strong result in one area could conceal a weakness in another. "
        "A reader evaluating a proposed benchmark should therefore ask which kinds of commentary are being compared and what evidence each judgement uses. "
        "The relationship between perception and explanation is particularly relevant: an interpretation would be unreliable if it began with an incorrect description of the action. "
        "A useful evaluation would keep those dependencies visible rather than reward fluent speech alone. "
        "That is an analytical requirement for interpreting the benchmark, not a claim about the performance of the systems it assesses.",
        "Different audiences could also value different commentary. "
        "A newcomer might need an explanation of a rule, whereas an experienced viewer might prefer analysis of a difficult choice. "
        "Testing audience usefulness would require identifying that purpose explicitly. "
        "The question shows why a commentary benchmark needs a clear account of what a satisfactory response is meant to accomplish."
    ),
    "non_text_model": (
        r"\b(non-text|fewer tokens|typesafe)\b",
        "Efficiency claims and commercial valuation",
        "A commercial valuation and an efficiency claim answer different questions. "
        "A valuation concerns the terms on which a business is assessed financially, whereas an efficiency comparison would require a defined task, comparable inputs and a way to measure the resulting output. "
        "If two systems represented information differently, counting their tokens alone might not show which one completed a useful task with fewer resources. "
        "Readers would need to ask whether the comparison covered the same work and whether differences in output quality were considered. "
        "Speed could matter to users, but its significance would depend on what they received in return and under which operating conditions. "
        "The wording of the excerpt is therefore relevant: a company's claim invites examination rather than supplies independent confirmation. "
        "Keeping investment interest separate from technical measurement allows the commercial story to be discussed without turning enthusiasm into proof of superior performance.",
        "An informative comparison might set out a practical workload before measuring either system. "
        "It could then examine completion time, resource use and the acceptability of the result together. "
        "Choosing the task first would reduce the risk that the comparison favoured an attractive measurement while overlooking the work users actually needed. "
        "This is a proposed method of scrutiny, not a report of an experiment already conducted."
    ),
    "open_problems": (
        r"\b(open problems|unresolved scientific|openproblembench|theoretical sciences)\b",
        "Unresolved problems and standards of proof",
        "An unresolved scientific problem creates a different evaluation challenge from a question with an accepted answer. "
        "For an established exercise, an evaluator may be able to compare a response with a known solution. "
        "For an open problem, a plausible argument would need examination of its assumptions and reasoning before it could be treated as a contribution. "
        "If an automated assessment rewarded the appearance of sophistication, it could mistake a convincing presentation for a valid result. "
        "The choice of problems would matter too: success on a selected collection would not establish the ability to resolve every difficult question in a field. "
        "Readers should therefore ask how the proposed benchmark distinguishes useful partial progress, an unsupported proposal and a demonstrated solution. "
        "Those distinctions protect the difference between evaluating an attempt and certifying a discovery. "
        "They also explain why the standards used to judge the answers deserve as much attention as the ambition of the benchmark.",
        "A partial argument could be valuable without settling the original problem. "
        "A fair evaluation would need to specify how that value was recognised and which claims remained unproved. "
        "Otherwise, a single score could blur the difference between a helpful direction and a complete solution. "
        "The reader's task is to preserve that distinction when interpreting any reported assessment."
    ),
    "public_disclosure": (
        r"\b(nda|ndas|data center deals|local governments|confidentiality)\b",
        "Disclosure and public decisions",
        "The removal of a confidentiality restriction concerns access to information; meaningful public scrutiny would depend on what information became available and when. "
        "If residents learned the terms of an agreement only after a decision, disclosure would serve a different purpose from access during the decision process. "
        "A reader should therefore distinguish the stated change in restrictions from an assessment of participation in particular negotiations. "
        "Documents might help explain obligations, but technical language or missing context could still make their implications difficult to assess. "
        "That possibility supports a question about intelligibility, rather than a claim that any specific agreement has been concealed. "
        "For decisions involving local government, the useful comparison concerns the relationship between available information and the opportunity to question a proposal. "
        "The announcement can be examined as a change in the conditions for scrutiny while leaving the consequences of that change open to evidence.",
        "A practical inquiry would ask which documents could be consulted, whether they explained the commitments involved and how a member of the public could request clarification. "
        "These questions focus on the use of disclosed information. "
        "They do not imply that removal of a restriction automatically resolves every disagreement about the development under discussion."
    ),
    "employment_investigation": (
        r"\b(fire|fired|dismissal|safety researchers|investigation)\b",
        "Institutional decisions and disputed accounts",
        "A report of an employment decision requires care about who is making each allegation and which conclusions are supported by the available account. "
        "An organisation's explanation and an independently established finding have different evidential status. "
        "If a dispute involved internal material that was not available to the reader, confident judgement about individual conduct would exceed the information supplied here. "
        "That does not prevent examination of the wider question of how an institution explains decisions affecting research staff. "
        "Readers could ask whether the account separates the decision itself, the reasons offered for it and any response from the people concerned. "
        "The absence of a response in a short summary should not be interpreted as agreement or as proof of wrongdoing. "
        "Maintaining those boundaries makes it possible to discuss organisational accountability without converting one party's account into a verdict about the individuals involved.",
        "The distinction between reporting an allegation and endorsing it is particularly important when reputations are involved. "
        "A responsible explanation would preserve attribution and indicate which relevant accounts were unavailable. "
        "A reader could then identify the additional material needed for a fuller assessment without assuming that uncertainty favoured either side of the dispute."
    ),
    "safety_evaluation": (
        r"\b(safety research|safety evaluation|safety tests)\b",
        "Safety evidence and test coverage",
        "A safety evaluation should be read in relation to the behaviour it was designed to examine. "
        "If a test covered only a narrow group of situations, a satisfactory result would not by itself answer questions about different inputs or operating conditions. "
        "The method would need to state what counted as a failure and how the tested examples were chosen. "
        "Readers should also ask whether an evaluation could detect unexpected behaviour or merely confirm responses already anticipated by its designers. "
        "Independent examination could be helpful where the reasoning and relevant test material were available for scrutiny. "
        "The central question is therefore the relationship between the scope of the test and the scope of the conclusion. "
        "A narrow conclusion could still be useful, provided its boundaries remained explicit. "
        "Calling a system safe without specifying the circumstances would remove the very detail needed to interpret the evidence responsibly.",
        "A useful follow-up would consider examples outside the initial test collection. "
        "If the same conclusion depended on familiar wording, its relevance to other situations would remain uncertain. "
        "Examining that possibility would extend the assessment without claiming that the original test was worthless. "
        "It would make clear which additional observations could justify a broader conclusion."
    ),
    "funding": (
        r"\b(funding|financing|investment|capital)\b",
        "Funding, expectations and business outcomes",
        "A financing announcement concerns the resources made available to an organisation and the expectations associated with that decision. "
        "It would not, by itself, show that the organisation had delivered a reliable product or established a sustainable business. "
        "A reader assessing the development could separate the decision to provide capital from the subsequent use of those resources. "
        "If investment supported expansion, the business would still face questions about costs, customer needs and the quality of its service. "
        "Those questions might be answered differently over time, so an assessment should distinguish an immediate financial event from a later operating result. "
        "The interest of investors could be relevant to the commercial story without replacing evidence about performance. "
        "This distinction allows a funding report to be read as information about support and expectations, while leaving claims about durable value to a separate examination.",
        "A practical follow-up would examine which activities the resources were intended to support and what observations could indicate progress. "
        "The relevant measures would depend on that purpose, rather than simply on the size of the financing. "
        "Such an inquiry would connect a financial announcement with a business question without assuming that the desired outcome had already occurred."
    ),
    "research_evaluation": (
        r"\b(benchmark|evaluating|evaluation|framework|research|study)\b",
        "Research methods and comparison",
        "A research framework sets out a way to investigate a question; evidence about its usefulness would depend on how that investigation was conducted. "
        "A comparison between methods would need an intelligible account of the tasks, the conditions and the basis for judging a response. "
        "If one approach received different inputs or more resources, a result might reflect those differences rather than the property the evaluator intended to examine. "
        "Readers should ask which assumptions are shared by the compared methods and which choices could influence the outcome. "
        "An informative report would also distinguish the observations made in the study from a proposed explanation of those observations. "
        "That distinction supports a qualified interpretation: a promising method may justify further investigation without establishing that it is preferable for every application. "
        "The contribution should be assessed through the research question it addresses and the limitations of the procedure used to answer it.",
        "Replication would provide a separate opportunity to examine the procedure. "
        "Another evaluator would need enough detail to understand the comparison and attempt it under the stated conditions. "
        "A similar result could strengthen confidence within that scope, while a different result would invite investigation of the cause. "
        "Neither possibility should be replaced by a general judgement based only on the name of a framework."
    ),
}


def clean_excerpt(story):
    raw=re.sub(r"<[^>]*>"," ",str(story.get("excerpt", "")))
    raw=re.sub(r"^\s*arxiv:\S+\s+announce type:\s*\w+\s+abstract:\s*","",raw,flags=re.I)
    raw=re.sub(r"\\[A-Za-z]+(?:\{([^{}]*)\})?",lambda m:m.group(1) or "",raw)
    return re.sub(r"\s+"," ",re.sub(r"\[S\d+\]|[\x00-\x1f]"," ",raw)).strip()


def context_key(story):
    # Specific headline concepts take priority over broad terms in abstracts.
    for field in (str(story.get("title", "")),clean_excerpt(story)):
        for key,(pattern,*_) in RULES.items():
            if re.search(pattern,field,re.I):
                return key
    return None


def compose(stories, day=None, variant=0, avoid_essays=None):
    entries=stories[:5]
    keys=[context_key(s) for s in entries]
    if len(entries)<3 or None in keys or len(set(keys))!=len(keys):
        return []
    if any(len(re.findall(r"\b[A-Za-z]+\b",clean_excerpt(s)))<9 for s in entries):
        return []
    labels=[RULES[key][1] for key in keys]
    # Keep the order fixed: changing the date does not manufacture new prose.
    intro=(
        "What would justify confidence in the developments described by these sources? "
        f"The questions range from {labels[0].lower()} to {labels[-1].lower()}. "
        "They call for different kinds of evidence, so the reports should be considered separately before their implications are compared. "
        "This reading first examines the question raised by each account, then considers how the standards of judgement differ. "
        "Only the titles and short extracts are available here. "
        "Statements about the reports remain attributed to their publishers; the following evaluation describes what a reader could investigate, without claiming that those investigations have been carried out."
    )
    paragraphs=[intro]
    for story,key in zip(entries,keys):
        publisher=str(story.get("publisher") or "The linked publisher").strip()
        title=re.sub(r"\s+"," ",str(story["title"])).strip()
        terms=clean_excerpt(story).split()
        quote=" ".join(terms[:18]).strip(" ,.;:—-\"'“”")
        quote=quote.replace("“","'").replace("”","'")
        attributed=(f"{publisher} presents ‘{title}’ [{story['id']}]. "
                    f"Its RSS extract begins: “{quote}{'…' if len(terms)>18 else ''}”. ")
        paragraphs.append(attributed+RULES[key][2])
        if len(entries)==3:
            paragraphs.append(f"For [{story['id']}], "+RULES[key][3])
    if len(entries)==4:
        paragraphs.append(f"An additional question in [{entries[1]['id']}] concerns the next stage of assessment. "+RULES[keys[1]][3])
    a,b=entries[0],entries[-1]
    comparison=(
        f"The contrast between [{a['id']}] and [{b['id']}] brings the argument into focus. "
        f"The former raises the question of {labels[0].lower()}, while the latter concerns {labels[-1].lower()}. "
        "A judgement appropriate to one would not automatically resolve the other. "
        "For example, information explaining the scope of a proposed activity serves a different purpose from evidence showing how a disputed conclusion was reached. "
        "A reasonable objection is that asking for more detail can delay a useful decision. "
        "Yet the answer is to identify the particular uncertainty that affects that decision, rather than demand unlimited information or accept every claim immediately. "
        "The comparison therefore supports a proportionate standard: ask for evidence relevant to the question being judged."
    )
    if len(entries)>=4:
        middle=entries[-2]
        comparison=(f"Comparing [{a['id']}] with [{middle['id']}] requires two distinct lines of inquiry. "
                    +RULES[keys[0]][3]+" "
                    +f"For [{middle['id']}], a different consideration follows. "
                    +RULES[keys[-2]][3])
    paragraphs.append(comparison)
    ending=(
        f"Taken together, the accounts connect {labels[0].lower()} with {labels[-1].lower()} through the problem of judgement. "
        "Their significance lies in the distinct questions they raise, rather than in a single verdict about AI. "
        "A defensible conclusion names the claim, identifies its source and explains which evidence would change the assessment. "
        "Such a conclusion remains provisional where a summary leaves important issues unresolved. "
        "Returning to the linked accounts would be necessary before treating this reading exercise as a basis for a consequential decision."
    )
    if len(entries)>=4:
        ending=(f"The final account, [{b['id']}], leaves a question that also illustrates the limits of this reading. "
                +RULES[keys[-1]][3]+" "
                "That remains a provisional assessment of the attributed account, rather than an independently confirmed finding.")
    paragraphs.append(ending)
    return paragraphs

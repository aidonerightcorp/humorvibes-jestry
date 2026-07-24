"""Study branches that inform HumorVibes decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class StudyBranch:
    branch_id: str
    name: str
    questions: tuple[str, ...]
    study_leads: tuple[str, ...]
    design_use: tuple[str, ...]
    source_urls: tuple[str, ...]
    priority: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


STUDY_BRANCHES: tuple[StudyBranch, ...] = (
    StudyBranch(
        "structure_incongruity_resolution",
        "Comedic Structure And Incongruity Resolution",
        (
            "What expectation does the setup create?",
            "Where does the punchline force reinterpretation?",
            "Is the incongruity resolved or just random?",
        ),
        (
            "Script-based semantic theory of humor and General Theory of Verbal Humor",
            "SemEval Humicroedit / FunLines headline-edit humor",
            "Incongruity-Resolution Supervision for cartoon-caption reasoning",
            "Semantic/constraint-overlap humor mechanism",
        ),
        (
            "Score setup clarity, surprise, and resolution separately.",
            "Ask Gemma to identify the overt constraint and hidden/covert constraint.",
            "Repair jokes by preserving the reinterpretation while shortening the setup.",
        ),
        (
            "https://arxiv.org/abs/2008.00304",
            "https://arxiv.org/abs/2604.15210",
            "https://arxiv.org/abs/2310.07803",
        ),
        10,
    ),
    StudyBranch(
        "bad_surprise_boundary",
        "Bad Surprise And Boundary Modeling",
        (
            "Does surprise collide with a dominant internal model?",
            "Which audience model has override power?",
            "Can the joke keep local surprise without breaking the audience's primary interpretation frame?",
        ),
        (
            "Benign Violation Theory",
            "HaHackathon humor/offense ratings",
            "Harm or Humor benchmark",
            "User's canonical bad-surprise definition",
        ),
        (
            "Keep bad surprise as its own dimension, not a synonym for offense or factuality.",
            "Use offense/confusion/appropriateness as proxy signals only.",
            "Generate repairs that move the target from identity/worldview to situation/process.",
        ),
        (
            "https://arxiv.org/abs/2104.00933",
            "https://arxiv.org/abs/2603.17759",
        ),
        10,
    ),
    StudyBranch(
        "dominant_model_moral_frames",
        "Dominant Internal Models And Moral Frames",
        (
            "Which internal model has enough authority to override local joke logic?",
            "Which moral or ethical frame controls whether the surprise can be processed as humor?",
            "Which wording choices accidentally activate a high-authority model before the punchline resolves?",
        ),
        (
            "User's canonical bad-surprise definition",
            "Morality Frames in Political Tweets",
            "Moral Foundations Questionnaire / MFQ-2",
            "POPQUORN demographic-sensitive annotation",
        ),
        (
            "Ask audience probes about dominant models before high-sensitivity topics.",
            "Annotate target entity, moral frame, and identity/worldview activation separately.",
            "Repair by keeping the local comic turn while changing the frame-triggering wording.",
        ),
        (
            "https://arxiv.org/abs/2109.04535",
            "https://moralfoundations.org/",
            "https://arxiv.org/abs/2306.06826",
        ),
        9,
    ),
    StudyBranch(
        "audience_preference_embeddings",
        "Audience Preference And Humor Embeddings",
        (
            "Which audience clusters like this joke family?",
            "What lexical texture predicts preference?",
            "Can the system represent an individual or group sense of humor as a vector?",
        ),
        (
            "Jester joke recommender ratings",
            "Humor in Word Embeddings",
            "POPQUORN demographic annotation methods",
        ),
        (
            "Build audience embeddings from preference, demographic, and response vectors.",
            "Retrieve jokes with similar audience/reaction patterns.",
            "Separate user taste from general funniness.",
        ),
        (
            "https://eigentaste.berkeley.edu/dataset/",
            "https://arxiv.org/abs/1902.02783",
            "https://arxiv.org/abs/2306.06826",
        ),
        9,
    ),
    StudyBranch(
        "live_response_timing_delivery",
        "Live Response, Timing, And Delivery",
        (
            "How long did laughter last?",
            "Did silence mean confusion, rejection, or delayed resolution?",
            "Should the next move be a tag, pivot, pause, or rewording?",
        ),
        (
            "TIC-TALK standup timing database",
            "StandUp4AI word-level laughter labels",
            "Open Mic humor quotient from laughter duration",
            "When to Laugh and How Hard?",
            "Audience-reaction/laugh-track effects",
        ),
        (
            "Convert laughter, silence, groans, applause, and smiles into adaptation directives.",
            "Use timing as a delivery feature, not just a text feature.",
            "Let successful jokes produce adjacent tags; let failed jokes trigger shorter pivots.",
        ),
        (
            "https://arxiv.org/abs/2603.21803",
            "https://arxiv.org/abs/2505.18903",
            "https://arxiv.org/abs/2110.12765",
            "https://arxiv.org/abs/2211.01889",
        ),
        9,
    ),
    StudyBranch(
        "humor_styles_social_function",
        "Humor Styles And Social Function",
        (
            "Is the joke affiliative, self-enhancing, aggressive, or self-defeating?",
            "Does the joke bond the room or create a target hierarchy?",
            "Which style fits the audience context?",
        ),
        (
            "Humor Styles Questionnaire",
            "Computational humor style recognition",
            "Robot-delivered humor style study",
            "Workplace and relationship humor research",
        ),
        (
            "Expose style as an editable control.",
            "Use affiliative/self-enhancing styles for bridge or professional audiences.",
            "Reserve aggressive/self-defeating styles for explicitly requested contexts.",
        ),
        (
            "https://arxiv.org/abs/2410.12842",
            "https://arxiv.org/abs/2606.13256",
        ),
        8,
    ),
    StudyBranch(
        "political_ideology_portability",
        "Political And Ideological Portability",
        (
            "Can the joke cross political identities?",
            "Does it require one side to accept the other's moral frame?",
            "Does label swapping preserve the comic mechanism?",
        ),
        (
            "Political robot joke acceptability",
            "Political satire effects and counter-attitudinal exposure",
            "Cross-partisan YouTube interaction",
            "Political metaphor/framing engagement",
            "Political parody detection",
            "Morality Frames in Political Tweets",
        ),
        (
            "Run label-swap, target, moral-frame, and shared-frustration tests.",
            "Prefer shared institutional absurdity for bridge goals.",
            "Treat partisan identity as a high-authority model unless the user asks for partisan satire.",
        ),
        (
            "https://arxiv.org/abs/2606.13256",
            "https://arxiv.org/abs/2104.05365",
            "https://arxiv.org/abs/2205.03313",
            "https://arxiv.org/abs/2104.03928",
            "https://arxiv.org/abs/2109.04535",
        ),
        8,
    ),
    StudyBranch(
        "culture_language_context",
        "Culture, Language, And Local Context",
        (
            "Which references require insider cultural knowledge?",
            "Does the joke depend on language preference or local norms?",
            "Does translation preserve the punchline mechanism?",
        ),
        (
            "Chumor / CFunSet Chinese humor datasets",
            "Spanish crowd-annotated humor corpus",
            "ManzaiSet viewer-response clusters",
            "StandUp4AI multilingual standup",
        ),
        (
            "Ask for audience culture and language preference before sensitive jokes.",
            "Use local-context references only when insider context is high.",
            "Flag jokes that rely on unshared cultural scripts.",
        ),
        (
            "https://arxiv.org/abs/2412.17729",
            "https://arxiv.org/abs/1710.00477",
            "https://arxiv.org/abs/2510.18014",
            "https://arxiv.org/abs/2505.18903",
        ),
        8,
    ),
    StudyBranch(
        "multimodal_visual_performance",
        "Multimodal, Visual, And Performance Humor",
        (
            "Is the funny part textual, visual, acoustic, gestural, or a mismatch among them?",
            "What does posture, facial reaction, or prosody add?",
            "Can the model explain visual incongruity?",
        ),
        (
            "UR-FUNNY",
            "HumorDB visual humor benchmark",
            "NYCC Incongruity-Resolution Supervision",
            "MUStARD multimodal sarcasm context",
        ),
        (
            "Keep modality labels in the datacenter.",
            "Use visual/performance branches for demo variants with images, video, or live delivery.",
            "Represent delivery and visual cues as separate retrieval channels.",
        ),
        (
            "https://arxiv.org/abs/1904.06618",
            "https://arxiv.org/abs/2406.13564",
            "https://arxiv.org/abs/2604.15210",
            "https://arxiv.org/abs/1906.01815",
        ),
        7,
    ),
    StudyBranch(
        "sarcasm_irony_parody",
        "Sarcasm, Irony, And Parody",
        (
            "Is the literal text opposite the intended stance?",
            "Does the audience have enough context to infer the intended frame?",
            "Is the joke parodying a voice, institution, genre, or person?",
        ),
        (
            "SARC Reddit sarcasm corpus",
            "MUStARD / MUStARD++",
            "Political parody detection",
            "Reverse-Engineering Satire",
        ),
        (
            "Require context before sarcasm-heavy generation.",
            "Flag sarcasm as higher risk for mixed audiences.",
            "Repair parody by clarifying target and reducing accidental endorsement.",
        ),
        (
            "https://arxiv.org/abs/1704.05579",
            "https://arxiv.org/abs/1906.01815",
            "https://arxiv.org/abs/2205.03313",
            "https://arxiv.org/abs/1901.03253",
        ),
        7,
    ),
    StudyBranch(
        "cognitive_neural_processing",
        "Cognitive And Neural Humor Processing",
        (
            "Does the joke require detection, resolution, elaboration, or affective appreciation?",
            "Are we measuring comprehension failure or amusement failure?",
            "Does the audience need theory-of-mind reasoning?",
        ),
        (
            "Cognitive humor processing fMRI work",
            "Verbal joke incongruity detection/resolution studies",
            "Nonverbal cartoon theory-of-mind studies",
            "Semantic/constraint overlap theory",
        ),
        (
            "Separate comprehension, elaboration, and appreciation in explanations.",
            "Classify failures as unclear premise, unresolved twist, low amusement, or bad surprise.",
            "Use theory-of-mind load as a complexity signal.",
        ),
        (
            "https://arxiv.org/abs/2310.07803",
        ),
        7,
    ),
    StudyBranch(
        "generation_repair_unfun",
        "Generation, Repair, And Unfun Editing",
        (
            "What minimal edit removes or restores humor?",
            "Can the system preserve the comic engine while changing target, frame, or risk?",
            "What strategy generated the candidate?",
        ),
        (
            "Reverse-Engineering Satire / Unfun.me",
            "Getting Serious about Humor",
            "HumorPlanSearch",
            "HumorGen persona-based distillation",
        ),
        (
            "Support repair buttons: safer, sharper, more concrete, bridge, classroom-safe.",
            "Use unfun edits as negative controls.",
            "Track strategy labels so generation is not a generic joke slot machine.",
        ),
        (
            "https://arxiv.org/abs/1901.03253",
            "https://arxiv.org/abs/2403.00794",
            "https://arxiv.org/abs/2508.11429",
            "https://arxiv.org/abs/2604.09629",
        ),
        8,
    ),
    StudyBranch(
        "ranking_evaluation",
        "Ranking, Evaluation, And Leaderboards",
        (
            "Which candidate wins pairwise?",
            "Do human and model humor preferences diverge?",
            "Can rankings be stable across prompts, audiences, and judges?",
        ),
        (
            "HumorRank tournament ranking",
            "Cards Against LLMs slate-choice benchmark",
            "New Yorker cartoon caption preference data",
            "Humicroedit pairwise subtask",
            "HumorDB pairwise image comparisons",
        ),
        (
            "Use pairwise ranking in addition to scalar mesh scores.",
            "Track model-vs-human disagreement as a risk signal.",
            "Aggregate repeated judgments with Bradley-Terry-style scoring.",
        ),
        (
            "https://arxiv.org/abs/2604.19786",
            "https://arxiv.org/abs/2604.08757",
            "https://arxiv.org/abs/2406.10522",
            "https://arxiv.org/abs/2008.00304",
            "https://arxiv.org/abs/2406.13564",
        ),
        8,
    ),
    StudyBranch(
        "model_jury_convergence",
        "Model Jury And Convergence",
        (
            "Do Gemma, Kimi, GLM, and other judges agree on the same joke dimensions?",
            "Which dimensions converge reliably, and which require human/audience probes?",
            "Does disagreement reveal cultural, market, timing, or bad-surprise ambiguity?",
        ),
        (
            "G-Eval LLM-as-judge framework",
            "Multi-agent debate for cultural alignment",
            "LLM-as-a-judge bias and self-preference research",
        ),
        (
            "Score the same joke with multiple configured judges.",
            "Track per-dimension variance rather than only average score.",
            "Escalate low-convergence dimensions to human probes or pairwise audience tests.",
        ),
        (
            "https://arxiv.org/abs/2303.16634",
            "https://arxiv.org/abs/2505.24671",
        ),
        8,
    ),
    StudyBranch(
        "humor_market_competition_analytics",
        "Humor Market And Competition Analytics",
        (
            "Which humor niches are crowded, and which are underserved?",
            "Which comedians or archetypes compete for the same audience/style space?",
            "Will an established audience reject a style shift as a broken promise?",
        ),
        (
            "Humor Styles Questionnaire",
            "Political robot joke style/topic study",
            "Popularity feedback in cultural markets",
            "Taste persistence in large-scale music listening",
            "Uniqueness and popularity in music",
        ),
        (
            "Represent comedians and audience niches as style vectors.",
            "Measure supply density versus demand proxy to find gaps.",
            "Estimate style-shift risk from distance, audience lock-in, bridge overlap, and dominant-model sensitivity.",
        ),
        (
            "https://arxiv.org/abs/2606.13256",
            "https://arxiv.org/abs/2602.09997",
            "https://arxiv.org/abs/1904.04948",
            "https://arxiv.org/abs/2207.12943",
        ),
        8,
    ),
    StudyBranch(
        "coping_health_workplace_education",
        "Coping, Health, Workplace, And Education",
        (
            "Is humor being used to bond, teach, regulate emotion, or reduce stress?",
            "Could self-defeating humor harm the speaker?",
            "What wording fits classroom, workplace, therapy, or training contexts?",
        ),
        (
            "Humor styles and psychological outcomes",
            "Humor intervention and well-being research",
            "Workplace humor research",
            "Educational humor and communication studies",
        ),
        (
            "Choose affiliative/self-enhancing humor for workplace and education.",
            "Avoid self-defeating spirals in repeated suggestions.",
            "Tune jokes toward learning, rapport, or stress relief when requested.",
        ),
        (
            "https://en.wikipedia.org/wiki/Humor_styles",
        ),
        6,
    ),
)


def rank_study_branches(prompt: str, audience: str = "", preferences: str = "", limit: int = 8) -> list[StudyBranch]:
    text = " ".join([prompt, audience, preferences]).lower()
    scored: list[tuple[int, StudyBranch]] = []
    for branch in STUDY_BRANCHES:
        score = branch.priority
        haystack = " ".join(branch.questions + branch.study_leads + branch.design_use + (branch.name,)).lower()
        for term in text.replace("/", " ").replace("-", " ").split():
            if len(term) >= 4 and term in haystack:
                score += 2
        if any(term in text for term in ["politic", "ideolog", "partisan", "liberal", "conservative"]):
            if branch.branch_id == "political_ideology_portability":
                score += 10
        if any(term in text for term in ["audience", "preference", "profile", "demographic"]):
            if branch.branch_id in {"audience_preference_embeddings", "live_response_timing_delivery"}:
                score += 5
        if any(term in text for term in ["laughter", "timing", "delivery", "pause", "groan", "silence"]):
            if branch.branch_id == "live_response_timing_delivery":
                score += 8
        if any(term in text for term in ["safe", "risk", "offense", "bad surprise", "harm"]):
            if branch.branch_id == "bad_surprise_boundary":
                score += 8
        if any(term in text for term in ["moral", "ethical", "worldview", "override", "dominant model", "frame"]):
            if branch.branch_id in {"dominant_model_moral_frames", "bad_surprise_boundary"}:
                score += 8
        if any(term in text for term in ["culture", "language", "translation", "local"]):
            if branch.branch_id == "culture_language_context":
                score += 6
        if any(term in text for term in ["rank", "ranking", "pairwise", "tournament", "leaderboard", "preference"]):
            if branch.branch_id in {"ranking_evaluation", "audience_preference_embeddings"}:
                score += 7
        if any(term in text for term in ["market", "competitor", "competition", "niche", "gap", "flop", "style shift"]):
            if branch.branch_id == "humor_market_competition_analytics":
                score += 10
        if any(term in text for term in ["model", "jury", "judge", "convergence", "glm", "kimi", "gemma"]):
            if branch.branch_id == "model_jury_convergence":
                score += 10
        scored.append((score, branch))
    scored.sort(key=lambda item: (item[0], item[1].priority, item[1].branch_id), reverse=True)
    return [branch for _, branch in scored[:limit]]


def study_context_block(prompt: str, audience: str = "", preferences: str = "", limit: int = 5) -> str:
    lines = []
    for branch in rank_study_branches(prompt, audience, preferences, limit=limit):
        uses = "; ".join(branch.design_use[:2])
        leads = ", ".join(branch.study_leads[:3])
        lines.append(f"- {branch.name}: {uses}. Study leads: {leads}.")
    return "\n".join(lines)

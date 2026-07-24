"""Curated source registry for humor data and evaluation signals."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class HumorSource:
    source_id: str
    name: str
    url: str
    modalities: tuple[str, ...]
    signal_types: tuple[str, ...]
    best_for: tuple[str, ...]
    access_status: str
    license_notes: str
    priority: int
    caveats: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


HUMOR_SOURCES: tuple[HumorSource, ...] = (
    HumorSource(
        "humicroedit",
        "SemEval-2020 Task 7 / Humicroedit",
        "https://arxiv.org/abs/2008.00304",
        ("text",),
        ("funniness_0_3", "pairwise_preference", "headline_edit"),
        ("surprise", "resolution", "ranking", "headline edits"),
        "public benchmark; fetch from official task mirrors before use",
        "verify redistribution terms before bundling data",
        10,
        "Excellent for local expectation violation, but news-headline culture may not transfer to live performance.",
    ),
    HumorSource(
        "funlines",
        "FunLines",
        "https://arxiv.org/abs/2002.02031",
        ("text",),
        ("human_funniness_rating", "headline_edit", "creator_feedback"),
        ("generation edits", "funniness calibration", "rewrite feedback"),
        "public research dataset lead",
        "verify dataset license and storage location before bundling",
        9,
        "Game-generated headline edits are useful but still domain-specific.",
    ),
    HumorSource(
        "hahackathon",
        "SemEval-2021 HaHackathon",
        "https://arxiv.org/abs/2104.00933",
        ("text",),
        ("humor_label", "humor_rating", "offense_rating"),
        ("humor/offense separation", "appropriateness proxy", "risk calibration"),
        "public benchmark; fetch from official task mirrors before use",
        "verify redistribution terms before bundling data",
        10,
        "Offense is a proxy signal only; it is not the definition of bad surprise.",
    ),
    HumorSource(
        "jester",
        "Jester Joke Recommender Dataset",
        "https://eigentaste.berkeley.edu/dataset/",
        ("text", "ratings_matrix"),
        ("user_joke_rating", "collaborative_filtering"),
        ("preference clusters", "audience embeddings", "personalization"),
        "directly downloadable for research use with acknowledgement",
        "research use; acknowledge Eigentaste/Jester reference",
        10,
        "Older jokes and sparse demographic metadata; strong for preference vectors, weak for current culture.",
    ),
    HumorSource(
        "humor_word_embeddings",
        "Humor in Word Embeddings word-rating data",
        "https://arxiv.org/abs/1902.02783",
        ("word_ratings", "embeddings"),
        ("word_funniness", "individual_preference_vector", "demographic_cluster"),
        ("humor embeddings", "lexical comic texture", "audience preference directions"),
        "paper and dataset lead",
        "verify dataset release path and license before bundling",
        9,
        "Single-word humor is not joke humor, but it is valuable for lexical texture and preference vectors.",
    ),
    HumorSource(
        "ur_funny",
        "UR-FUNNY",
        "https://arxiv.org/abs/1904.06618",
        ("text", "audio", "video"),
        ("humor_label", "prosody", "gesture", "context"),
        ("delivery", "multimodal timing", "speech humor"),
        "public research dataset",
        "verify download terms and media redistribution limits",
        8,
        "Best for detection and timing, not direct joke generation.",
    ),
    HumorSource(
        "standup4ai",
        "StandUp4AI",
        "https://arxiv.org/abs/2505.18903",
        ("text", "audio", "video"),
        ("audience_laughter", "word_level_sequence_labels", "language"),
        ("laughter timing", "multilingual standup", "audience reaction"),
        "paper reports online code/data",
        "verify media/license terms before ingesting clips or transcripts",
        8,
        "High value for timing, but full media may have copyright constraints.",
    ),
    HumorSource(
        "tic_talk",
        "TIC-TALK",
        "https://arxiv.org/abs/2603.21803",
        ("text", "audio", "video", "pose"),
        ("laughter_onset", "laughter_duration", "topic_segment", "kinematics"),
        ("timing", "audience reaction", "performance dynamics"),
        "new paper/data lead",
        "verify release path and copyrighted-source constraints before ingest",
        7,
        "Use derived metadata first; do not bundle copyrighted specials.",
    ),
    HumorSource(
        "manzaiset",
        "ManzaiSet viewer-response dataset",
        "https://arxiv.org/abs/2510.18014",
        ("audio", "video", "viewer_response"),
        ("facial_response", "audio_response", "viewer_type_cluster", "viewing_order"),
        ("audience probing", "viewer clustering", "non-Western comedy response"),
        "new dataset lead",
        "verify release path, participant consent limits, and media restrictions before ingest",
        7,
        "Excellent for audience heterogeneity; culturally specific to Japanese manzai.",
    ),
    HumorSource(
        "when_to_laugh",
        "When to Laugh and How Hard?",
        "https://arxiv.org/abs/2211.01889",
        ("text", "audio", "video"),
        ("humor_intensity", "laughter_duration", "utterance_label"),
        ("response intensity", "laugh duration prediction", "timing"),
        "paper/dataset lead",
        "TV-show source material requires rights checks before bundling",
        7,
        "Useful for response modeling; sitcom laugh tracks are not identical to live audience feedback.",
    ),
    HumorSource(
        "open_mic",
        "Open Mic standup humor quotient dataset",
        "https://arxiv.org/abs/2110.12765",
        ("text", "audio", "video"),
        ("laughter_duration", "humor_quotient_0_4"),
        ("funniness scoring", "timing", "audience reaction"),
        "paper reports released data/code",
        "verify download terms and media redistribution limits",
        8,
        "Laughter duration is a useful proxy, not a complete humor score.",
    ),
    HumorSource(
        "humordb",
        "HumorDB visual humor benchmark",
        "https://arxiv.org/abs/2406.13564",
        ("image",),
        ("funniness_1_10", "pairwise_preference", "funny_not_funny"),
        ("visual humor", "pairwise ranking", "multimodal expansion"),
        "paper says dataset/code are open-sourced under CC BY 4.0",
        "CC BY 4.0 reported by paper; verify repository files before bundling",
        7,
        "Image-only; useful for future multimodal Gemma demos.",
    ),
    HumorSource(
        "harm_or_humor",
        "Harm or Humor benchmark",
        "https://arxiv.org/abs/2603.17759",
        ("text", "image", "video"),
        ("safe_joke", "harmful_explicit", "harmful_implicit", "language"),
        ("harmful humor", "cultural safety", "implicit risk"),
        "new benchmark lead",
        "verify release path, license, and content handling restrictions",
        7,
        "Useful for risk probes; contains offensive/harmful examples by design.",
    ),
    HumorSource(
        "political_robot_jokes",
        "Humor Style Drives Laughter, Topic Shapes Acceptability",
        "https://arxiv.org/abs/2606.13256",
        ("text", "robot_delivery", "audience_response"),
        ("humor_style", "political_topic", "appropriateness", "language_preference"),
        ("political joke acceptability", "style vs topic effects", "live group delivery"),
        "new paper/data lead",
        "verify dataset release path before ingest",
        8,
        "Directly relevant to cross-ideology humor because political content changed appropriateness more than style changed funniness.",
    ),
    HumorSource(
        "political_parody_detection",
        "Combining Humor and Sarcasm for Political Parody Detection",
        "https://arxiv.org/abs/2205.03313",
        ("text", "social_media"),
        ("political_parody", "humor_signal", "sarcasm_signal"),
        ("political parody", "satire detection", "sarcasm-humor overlap"),
        "paper reports a public political parody tweet dataset",
        "verify tweet redistribution and dataset license before bundling",
        7,
        "Good for recognizing political parody mechanics, not for judging cross-partisan success.",
    ),
    HumorSource(
        "cross_partisan_youtube",
        "Cross-Partisan Discussions on YouTube",
        "https://arxiv.org/abs/2104.05365",
        ("comments", "channels", "user_context"),
        ("political_leaning", "cross_partisan_reply", "toxicity", "visibility"),
        ("cross-ideology audience risk", "reply toxicity", "partisan context"),
        "large-scale research dataset lead",
        "verify platform terms, privacy handling, and release availability",
        6,
        "Not a humor dataset, but useful for estimating cross-partisan interaction risk.",
    ),
    HumorSource(
        "political_satire_effects",
        "Political satire effects research",
        "https://en.wikipedia.org/wiki/Political_satire",
        ("text", "media_effects"),
        ("proattitudinal_exposure", "counterattitudinal_exposure", "anger", "participation"),
        ("political humor effects", "audience alignment", "counter-attitudinal exposure"),
        "literature lead; use cited primary studies where possible",
        "do not cite wiki as final evidence when primary papers are available",
        6,
        "Useful for source discovery and conceptual framing, but not a dataset.",
    ),
    HumorSource(
        "reverse_engineering_satire",
        "Reverse-Engineering Satire",
        "https://arxiv.org/abs/1901.03253",
        ("text", "headline_edits"),
        ("satirical_headline", "serious_counterpart", "minimal_edit", "false_analogy"),
        ("satire mechanics", "political headline repair", "semantic portability"),
        "public corpus lead",
        "verify Unfun.me corpus release terms before bundling",
        7,
        "Useful for learning what words make satire funny and how to neutralize or repair them.",
    ),
    HumorSource(
        "political_metaphor_framing",
        "Metaphors in Political Discourse",
        "https://arxiv.org/abs/2104.03928",
        ("text", "social_media"),
        ("metaphor", "ideology", "engagement", "political_event_context"),
        ("political framing", "semantic language delivery", "ideology-sensitive metaphors"),
        "public-data research lead",
        "verify Facebook/public-page dataset availability and terms before ingest",
        6,
        "Not humor-specific, but highly relevant to wording choices that travel or fail across ideology.",
    ),
    HumorSource(
        "cards_against_llms",
        "Cards Against LLMs",
        "https://arxiv.org/abs/2604.08757",
        ("text", "game_rounds"),
        ("human_choice", "model_choice", "candidate_slate", "position_bias"),
        ("alignment with human humor preference", "pairwise/slate ranking"),
        "paper/data lead",
        "verify CAH card text licensing before bundling",
        6,
        "Great ranking setup, but content/license and taste constraints need care.",
    ),
    HumorSource(
        "humorrank",
        "HumorRank",
        "https://arxiv.org/abs/2604.19786",
        ("text", "model_outputs"),
        ("pairwise_judgment", "bradley_terry_rank", "tournament_score"),
        ("model output ranking", "pairwise aggregation", "leaderboard design"),
        "method and benchmark lead",
        "verify MWAHAHA test data availability before ingest",
        8,
        "Use the ranking method even if the exact benchmark data is unavailable.",
    ),
    HumorSource(
        "geval_llm_judge",
        "G-Eval LLM-as-judge framework",
        "https://arxiv.org/abs/2303.16634",
        ("text", "model_judgment"),
        ("rubric_score", "chain_of_thought_eval", "human_correlation", "judge_bias"),
        ("model jury", "rubric scoring", "convergence", "judge disagreement"),
        "method lead",
        "method can be implemented without bundling third-party data",
        8,
        "Useful for model-based scoring; still needs human/audience validation for humor.",
    ),
    HumorSource(
        "multi_agent_cultural_alignment",
        "Multi-agent debate for cultural alignment",
        "https://arxiv.org/abs/2505.24671",
        ("text", "model_judgment", "cultural_context"),
        ("multi_model_debate", "cultural_norm", "group_parity", "model_diversity"),
        ("model jury", "cultural context", "audience disagreement", "convergence"),
        "method lead",
        "method can be implemented without bundling third-party data",
        7,
        "Relevant when model judges disagree because of culture, norms, or audience framing.",
    ),
    HumorSource(
        "popularity_feedback_cultural_markets",
        "Popularity Feedback Constrains Innovation in Cultural Markets",
        "https://arxiv.org/abs/2602.09997",
        ("market_experiment", "ratings", "creative_variants"),
        ("popularity_feedback", "cumulative_advantage", "diversity", "innovation_rate"),
        ("market gaps", "niche saturation", "creative drift", "competition analytics"),
        "paper/method lead",
        "not humor-specific; use as cultural-market modeling evidence",
        7,
        "Supports tracking how feedback loops can crowd creators into the same style space.",
    ),
    HumorSource(
        "musical_identity_dynamics",
        "Environmental Changes and the Dynamics of Musical Identity",
        "https://arxiv.org/abs/1904.04948",
        ("listener_history", "location", "preference_vector"),
        ("taste_persistence", "identity", "environment_shift", "preference_drift"),
        ("audience lock-in", "style-shift risk", "taste persistence"),
        "paper/method lead",
        "music-specific; use as analogy, not direct comedy proof",
        6,
        "Useful for modeling why established audiences may resist abrupt style changes.",
    ),
    HumorSource(
        "music_uniqueness_popularity",
        "Unique in what sense?",
        "https://arxiv.org/abs/2207.12943",
        ("cultural_product", "lyrics", "audio", "popularity"),
        ("novelty", "popularity", "genre_conditioning", "distinctiveness"),
        ("market fit", "novelty penalty", "style differentiation", "gap analysis"),
        "paper/method lead",
        "music-specific; use as cultural-market analogy",
        6,
        "Useful for measuring whether novelty is too far from audience expectation.",
    ),
    HumorSource(
        "new_yorker_caption_preferences",
        "Humor in AI / New Yorker Cartoon Caption Preferences",
        "https://arxiv.org/abs/2406.10522",
        ("image", "caption", "ratings_matrix"),
        ("human_rating", "pairwise_preference", "caption_rank", "multimodal_context"),
        ("large-scale preference ranking", "visual humor", "human-vs-model comparison"),
        "paper reports released preference dataset",
        "verify contest data license and release terms before bundling",
        8,
        "Very strong ranking signal; visual-caption domain differs from live spoken jokes.",
    ),
    HumorSource(
        "humor_plan_search",
        "HumorPlanSearch",
        "https://arxiv.org/abs/2508.11429",
        ("text", "strategy_graph", "model_outputs"),
        ("strategy_plan", "multi_persona_feedback", "pairwise_win_rate", "topic_relevance"),
        ("contextual planning", "strategy search", "judge-driven revision", "novelty filtering"),
        "method lead",
        "method can be implemented without bundling external data",
        8,
        "Useful design pattern for strategy planning, not a primary human-reaction dataset.",
    ),
    HumorSource(
        "morality_frames",
        "Morality Frames in Political Tweets",
        "https://arxiv.org/abs/2109.04535",
        ("text", "entity_frames"),
        ("moral_foundation", "target_entity", "ideology", "polarity"),
        ("dominant moral models", "political framing", "target-sensitive wording"),
        "paper reports annotated political tweet dataset",
        "verify tweet redistribution and dataset license before bundling",
        7,
        "Not humor-specific, but directly useful for mapping which moral frame a joke may collide with.",
    ),
    HumorSource(
        "moral_foundations_questionnaire",
        "Moral Foundations Questionnaire / MFQ-2",
        "https://moralfoundations.org/",
        ("survey", "audience_profile"),
        ("care", "fairness", "loyalty", "authority", "purity", "liberty"),
        ("audience probing", "moral-frame mapping", "cross-ideology portability"),
        "survey/instrument lead",
        "use only voluntary aggregate audience probes in the prototype",
        7,
        "Use as optional audience mapping; do not overclaim that it fully explains political identity.",
    ),
    HumorSource(
        "chumor",
        "Chumor 2.0",
        "https://arxiv.org/abs/2412.17729",
        ("text", "explanations"),
        ("joke_explanation", "human_vs_model_preference", "language"),
        ("cultural context", "explanation quality", "non-English humor"),
        "paper reports Hugging Face dataset and leaderboard",
        "verify Hugging Face dataset license before bundling",
        7,
        "Chinese cultural humor; useful for cross-cultural tests, not English-only calibration.",
    ),
    HumorSource(
        "sarc",
        "Self-Annotated Reddit Corpus for Sarcasm",
        "https://arxiv.org/abs/1704.05579",
        ("text", "conversation"),
        ("sarcasm_label", "user_context", "topic_context", "conversation_context"),
        ("context modeling", "speaker history", "irony/sarcasm boundaries"),
        "public research corpus lead",
        "Reddit-derived data requires careful license and privacy handling",
        6,
        "Sarcasm is not humor, but the context machinery is highly relevant.",
    ),
    HumorSource(
        "mustard",
        "MUStARD / MUStARD++",
        "https://arxiv.org/abs/1906.01815",
        ("text", "audio", "video", "dialogue_context"),
        ("sarcasm_label", "speaker_context", "emotion", "valence", "arousal"),
        ("multimodal context", "delivery mismatch", "sarcastic surprise"),
        "public research dataset lead",
        "TV-show media/transcript rights need verification",
        6,
        "Use for delivery/context features, not as generic joke data.",
    ),
    HumorSource(
        "spanish_humor_corpus",
        "Crowd-Annotated Spanish Humor Corpus",
        "https://arxiv.org/abs/1710.00477",
        ("text",),
        ("humor_value", "funniness_score", "crowd_annotation"),
        ("subjectivity", "Spanish humor", "multi-annotator scoring"),
        "paper reports dataset availability",
        "verify tweet redistribution and license constraints",
        6,
        "Good for subjectivity; older Twitter terms may constrain raw text sharing.",
    ),
    HumorSource(
        "popquorn",
        "POPQUORN",
        "https://arxiv.org/abs/2306.06826",
        ("text", "annotator_metadata"),
        ("offensiveness", "politeness", "rewriting", "demographics"),
        ("audience/demographic modeling", "annotation bias", "appropriateness proxy"),
        "public dataset lead with GitHub release",
        "verify GitHub license before bundling",
        6,
        "Not humor-specific; useful for audience and demographic sensitivity infrastructure.",
    ),
)


def rank_sources_for_request(prompt: str, audience: str = "", preferences: str = "", limit: int = 8) -> list[HumorSource]:
    text = " ".join([prompt, audience, preferences]).lower()
    scored: list[tuple[int, HumorSource]] = []
    for source in HUMOR_SOURCES:
        score = source.priority
        haystack = " ".join(source.best_for + source.signal_types + source.modalities).lower()
        for term in text.replace("/", " ").split():
            if len(term) >= 4 and term in haystack:
                score += 2
        if any(term in text for term in ["audience", "nyc", "meetup", "classroom", "corporate", "probe"]):
            if any("audience" in x or "preference" in x or "demographic" in x for x in source.best_for + source.signal_types):
                score += 4
        if any(term in text for term in ["timing", "pause", "laughter", "delivery", "standup", "stand-up", "response"]):
            if any(x in source.signal_types for x in ["audience_laughter", "laughter_duration", "laughter_onset", "humor_intensity", "facial_response"]):
                score += 5
        if any(term in text for term in ["offense", "safe", "risk", "bad surprise", "harm"]):
            if any("offense" in x or "harm" in x or "safe" in x for x in source.signal_types + source.best_for):
                score += 5
        if any(term in text for term in ["political", "politics", "ideology", "partisan", "liberal", "conservative", "polarization"]):
            if any(
                "political" in x or "partisan" in x or "ideology" in x or "satire" in x
                for x in source.signal_types + source.best_for
            ):
                score += 6
        if any(term in text for term in ["cross", "bridge", "portable", "bipartisan"]):
            if any("cross" in x or "partisan" in x or "ideology" in x for x in source.signal_types + source.best_for):
                score += 5
        if any(term in text for term in ["moral", "ethical", "worldview", "dominant model", "override", "frame"]):
            if any("moral" in x or "frame" in x or "audience" in x for x in source.signal_types + source.best_for):
                score += 5
        if any(term in text for term in ["rank", "ranking", "pairwise", "tournament", "preference"]):
            if any("rank" in x or "pairwise" in x or "preference" in x for x in source.signal_types + source.best_for):
                score += 5
        if any(term in text for term in ["market", "competitor", "competition", "niche", "gap", "flop", "style shift"]):
            if any("market" in x or "competition" in x or "style" in x or "gap" in x for x in source.signal_types + source.best_for):
                score += 6
        if any(term in text for term in ["model", "jury", "judge", "convergence", "glm", "kimi", "gemma"]):
            if any("model" in x or "judge" in x or "convergence" in x for x in source.signal_types + source.best_for):
                score += 6
        scored.append((score, source))
    scored.sort(key=lambda item: (item[0], item[1].priority, item[1].source_id), reverse=True)
    return [source for _, source in scored[:limit]]


def source_context_block(prompt: str, audience: str = "", preferences: str = "", limit: int = 5) -> str:
    lines = []
    for source in rank_sources_for_request(prompt, audience, preferences, limit=limit):
        signals = ", ".join(source.signal_types[:4])
        lines.append(f"- {source.name}: use for {', '.join(source.best_for[:3])}; signals: {signals}.")
    return "\n".join(lines)

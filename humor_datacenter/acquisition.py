"""Dataset acquisition planning without bundling third-party data."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .sources import rank_sources_for_request


@dataclass(frozen=True)
class AcquisitionTarget:
    source_id: str
    name: str
    url: str
    local_path: str
    required_action: str
    expected_schema: tuple[str, ...]
    license_gate: str
    prototype_use: str
    priority: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


SCHEMA_HINTS: dict[str, tuple[str, ...]] = {
    "humicroedit": ("original_headline", "edited_headline", "edit_word", "mean_grade", "pairwise_label"),
    "funlines": ("original_headline", "edited_headline", "funniness_rating", "creator_feedback"),
    "hahackathon": ("text", "humor_label", "humor_rating", "offense_rating"),
    "jester": ("user_id", "joke_id", "rating"),
    "humor_word_embeddings": ("word", "funniness_rating", "participant_id", "demographic_group"),
    "ur_funny": ("utterance", "audio_features", "video_features", "humor_label", "context"),
    "standup4ai": ("transcript", "word_timestamps", "laughter_labels", "language"),
    "tic_talk": ("segment_text", "laughter_onset", "laughter_duration", "topic", "pose_features"),
    "open_mic": ("transcript", "laughter_duration", "humor_quotient", "audio_video_ref"),
    "when_to_laugh": ("utterance", "humor_intensity", "laughter_duration", "context"),
    "humorrank": ("candidate_a", "candidate_b", "winner", "judge", "topic"),
    "new_yorker_caption_preferences": ("cartoon_id", "caption", "human_rating", "pairwise_preference"),
    "morality_frames": ("text", "target_entity", "moral_foundation", "ideology", "polarity"),
    "moral_foundations_questionnaire": ("audience_id", "care", "fairness", "loyalty", "authority", "purity", "liberty"),
    "political_robot_jokes": ("joke", "humor_style", "political_topic", "appropriateness", "laughter"),
    "cross_partisan_youtube": ("comment", "channel", "political_leaning", "reply_type", "toxicity"),
    "political_metaphor_framing": ("post_text", "metaphor", "ideology", "engagement", "event_context"),
    "political_parody_detection": ("text", "parody_label", "humor_signal", "sarcasm_signal"),
    "reverse_engineering_satire": ("serious_headline", "satirical_headline", "edit", "mechanism"),
    "chumor": ("text", "explanation", "human_preference", "language", "culture_note"),
    "sarc": ("comment", "parent_context", "sarcasm_label", "author_context", "subreddit"),
    "mustard": ("utterance", "dialogue_context", "sarcasm_label", "audio_video_ref"),
    "spanish_humor_corpus": ("text", "humor_value", "funniness_score", "annotator_id"),
    "popquorn": ("text", "offensiveness", "politeness", "rewrite", "annotator_metadata"),
}


def acquisition_targets(prompt: str, audience: str = "", preferences: str = "", limit: int = 8) -> list[AcquisitionTarget]:
    targets: list[AcquisitionTarget] = []
    for source in rank_sources_for_request(prompt, audience, preferences, limit=limit):
        schema = SCHEMA_HINTS.get(source.source_id, ("text", "label", "metadata"))
        action = "verify license and fetch from official source"
        if "method" in source.access_status:
            action = "implement method locally; no required data bundle"
        elif "survey" in source.modalities:
            action = "collect voluntary aggregate audience responses; do not infer sensitive traits"
        elif any(media in source.modalities for media in ("audio", "video", "image")):
            action = "ingest released metadata first; require explicit rights before bundling media"
        targets.append(
            AcquisitionTarget(
                source_id=source.source_id,
                name=source.name,
                url=source.url,
                local_path=f"data/raw/{source.source_id}/",
                required_action=action,
                expected_schema=schema,
                license_gate=source.license_notes,
                prototype_use=", ".join(source.best_for[:3]),
                priority=source.priority,
            )
        )
    return targets


def acquisition_plan_block(prompt: str, audience: str = "", preferences: str = "", limit: int = 5) -> str:
    lines = ["Dataset acquisition plan:"]
    for target in acquisition_targets(prompt, audience, preferences, limit=limit):
        fields = ", ".join(target.expected_schema[:5])
        lines.append(
            f"- {target.name}: path={target.local_path}; action={target.required_action}; "
            f"fields={fields}; gate={target.license_gate}"
        )
    return "\n".join(lines)

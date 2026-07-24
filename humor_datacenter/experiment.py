"""Audience experiment logging and lightweight mechanism learning."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from .audience import LiveResponse


@dataclass
class JokeAttempt:
    session_id: str
    prompt: str
    audience: str
    candidate: str
    mechanism_ids: list[str]
    mesh_total: float = 0.0
    live_response: LiveResponse = field(default_factory=LiveResponse)
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def reward(self) -> float:
        return round(self.mesh_total + self.live_response.response_score, 3)

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["reward"] = self.reward
        return data

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "JokeAttempt":
        payload = dict(data)
        payload.pop("reward", None)
        response = payload.get("live_response")
        if isinstance(response, dict):
            payload["live_response"] = LiveResponse(**response)
        return cls(**payload)  # type: ignore[arg-type]


class ExperimentLog:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, attempt: JokeAttempt) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(attempt.to_dict(), sort_keys=True) + "\n")

    def read(self) -> list[JokeAttempt]:
        if not self.path.exists():
            return []
        attempts = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                attempts.append(JokeAttempt.from_dict(json.loads(line)))
        return attempts


def summarize_attempts(attempts: list[JokeAttempt]) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[JokeAttempt]] = {}
    for attempt in attempts:
        for mechanism_id in attempt.mechanism_ids or ["unknown"]:
            grouped.setdefault(mechanism_id, []).append(attempt)
    summary: dict[str, dict[str, float | int]] = {}
    for mechanism_id, rows in grouped.items():
        summary[mechanism_id] = {
            "n": len(rows),
            "avg_reward": round(mean(r.reward for r in rows), 3),
            "avg_response": round(mean(r.live_response.response_score for r in rows), 3),
            "avg_mesh": round(mean(r.mesh_total for r in rows), 3),
            "avg_laughter_seconds": round(mean(r.live_response.laughter_seconds for r in rows), 3),
            "avg_confusion": round(mean(r.live_response.confusion_level for r in rows), 3),
            "avg_groan": round(mean(r.live_response.groan_level for r in rows), 3),
        }
    return dict(sorted(summary.items(), key=lambda item: item[1]["avg_reward"], reverse=True))


def learning_context(attempts: list[JokeAttempt], limit: int = 5) -> str:
    if not attempts:
        return "No live audience attempts logged yet."
    summary = summarize_attempts(attempts)
    lines = ["Live experiment priors:"]
    for mechanism_id, stats in list(summary.items())[:limit]:
        lines.append(
            f"- {mechanism_id}: n={stats['n']}, avg_reward={stats['avg_reward']}, "
            f"avg_response={stats['avg_response']}, laughter={stats['avg_laughter_seconds']}, "
            f"confusion={stats['avg_confusion']}, groan={stats['avg_groan']}"
        )
    return "\n".join(lines)


def demo_attempts() -> list[JokeAttempt]:
    return [
        JokeAttempt(
            session_id="demo",
            prompt="AI project managers for a NYC tech meetup",
            audience="NYC tech meetup",
            candidate="The AI project manager optimized the sprint by scheduling a meeting about whether meetings were agile.",
            mechanism_ids=["anthropomorphism", "shared_frustration", "misdirection_reversal"],
            mesh_total=6.4,
            live_response=LiveResponse(laughter_seconds=3.0, applause_level=3, smile_level=5),
            notes="Shared workplace frustration landed.",
        ),
        JokeAttempt(
            session_id="demo",
            prompt="AI replacing managers",
            audience="corporate all-hands",
            candidate="AI will always replace every manager because humans never add value.",
            mechanism_ids=["hyperbole_understatement", "status_inversion"],
            mesh_total=1.9,
            live_response=LiveResponse(groan_level=5, confusion_level=4, silence_seconds=3),
            notes="Overgeneralized status threat.",
        ),
        JokeAttempt(
            session_id="demo",
            prompt="Political joke for mixed audience",
            audience="mixed political audience",
            candidate="Congress found a bipartisan solution: both sides agreed the printer was the real problem.",
            mechanism_ids=["shared_frustration", "status_inversion"],
            mesh_total=6.1,
            live_response=LiveResponse(laughter_seconds=2.0, applause_level=2, smile_level=4),
            notes="Targeted process absurdity, not voter identity.",
        ),
    ]

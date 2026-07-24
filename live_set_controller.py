"""Live set controller: dynamic joke selection from measured audience laughter.

THEORY.md in performance mode: each audience is a mesh whose meta-model we
estimate online. Every joke performed is an experiment; laughter is the reward
that updates a per-frame posterior for THIS room. The controller then picks
the next compiled artifact by Thompson sampling:

- a frame that lands raises its posterior -> exploit it (callbacks and tags are
  cheap re-routes through a frame the room's mesh has already cached);
- a cold room lowers posteriors -> explore unseen frames;
- everything performed comes from FROZEN, validated artifacts (compiled_humor),
  so the live loop never lets a model improvise a bad surprise on stage. Gemma
  stays offline in the compile loop; the show runs deterministic material with
  an adaptive ORDER.

Laughter measurement: `measure_laughter_wav` scores audience clips ("audit
clips") with a dependency-light envelope analysis — laughter shows as repeated
energy bursts at roughly 3-6 Hz (the ha-ha syllable rate) sustained above the
room's noise floor. It is deliberately simple, honest about being a proxy, and
replaceable by any stronger laughter detector behind the same LaughterReport.
Every clip + measurement + choice lands in a JSONL show log: an auditable
record of what was performed, what the room did, and why the next pick was
made.
"""
from __future__ import annotations

import json
import math
import random
import time
import wave
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from compiled_humor import JokeProgram, load_program, run_program

SHOW_LOG_DIR = Path(__file__).resolve().parent / "show_logs"


@dataclass
class LaughterReport:
    duration_s: float          # total audible laughter time
    burst_count: int           # laughter syllable bursts detected
    intensity: float           # mean burst energy over noise floor (ratio)
    clip_seconds: float
    source: str                # wav path or "manual"
    verdict: str               # bomb | chuckle | laugh | roar

    @property
    def reward(self) -> float:
        """Normalize to [0,1] for the bandit. 3s+ of laughter ~ a full hit."""
        base = min(1.0, self.duration_s / 3.0)
        bonus = min(0.2, 0.02 * self.burst_count)
        return round(min(1.0, base * 0.9 + bonus), 3)


def _verdict(duration_s: float) -> str:
    if duration_s < 0.3:
        return "bomb"
    if duration_s < 1.2:
        return "chuckle"
    if duration_s < 3.0:
        return "laugh"
    return "roar"


def manual_report(laughter_seconds: float, clip_seconds: float = 0.0) -> LaughterReport:
    return LaughterReport(
        duration_s=float(laughter_seconds),
        burst_count=int(laughter_seconds * 4),
        intensity=1.0,
        clip_seconds=clip_seconds,
        source="manual",
        verdict=_verdict(laughter_seconds),
    )


def measure_laughter_wav(path: str | Path, frame_ms: int = 50) -> LaughterReport:
    """Envelope-based laughter proxy for mono/stereo PCM WAV audit clips.

    Laughter signature: energy bursts recurring at ~3-6 Hz, sustained above an
    adaptive noise floor. This catches crowd laughter well enough to rank jokes
    within one room; it is not a lab-grade detector and says so on the tin.
    """
    import array

    path = Path(path)
    with wave.open(str(path), "rb") as w:
        n_frames = w.getnframes()
        rate = w.getframerate()
        n_ch = w.getnchannels()
        width = w.getsampwidth()
        raw = w.readframes(n_frames)
    if width == 2:
        samples = array.array("h", raw)
    elif width == 1:
        samples = array.array("b", raw)
    else:  # 32-bit
        samples = array.array("i", raw)
    if n_ch > 1:
        samples = samples[::n_ch]
    clip_seconds = n_frames / float(rate)

    hop = max(1, int(rate * frame_ms / 1000))
    energies: list[float] = []
    for i in range(0, len(samples) - hop, hop):
        seg = samples[i : i + hop]
        energies.append(math.sqrt(sum(s * s for s in seg) / len(seg)))
    if not energies:
        return LaughterReport(0.0, 0, 0.0, clip_seconds, str(path), "bomb")

    sorted_e = sorted(energies)
    floor = sorted_e[len(sorted_e) // 5] + 1e-9          # 20th percentile = room tone
    thresh = max(floor * 2.5, sorted_e[len(sorted_e) // 2] * 1.5)

    active = [e > thresh for e in energies]
    # bursts = rising edges; laughter = bursts recurring at 3-6 Hz (ha-ha rate)
    bursts, last_on = [], -10
    for idx, on in enumerate(active):
        if on and not (idx and active[idx - 1]):
            gap_s = (idx - last_on) * frame_ms / 1000.0
            bursts.append(gap_s)
            last_on = idx
    laugh_bursts = [g for g in bursts if 0.12 <= g <= 0.45]  # 2.2-8 Hz band, generous
    duration_s = sum(1 for on in active if on) * frame_ms / 1000.0
    # require periodicity evidence: without ha-ha rhythm, cap credited duration
    if len(laugh_bursts) < 3:
        duration_s = min(duration_s, 0.5)
    mean_active = (sum(e for e, on in zip(energies, active) if on) / max(1, sum(active)))
    return LaughterReport(
        duration_s=round(duration_s, 2),
        burst_count=len(laugh_bursts),
        intensity=round(mean_active / floor, 2),
        clip_seconds=round(clip_seconds, 2),
        source=str(path),
        verdict=_verdict(duration_s),
    )


@dataclass
class FramePosterior:
    frame: str
    alpha: float = 1.0   # successes + 1
    beta: float = 1.0    # failures + 1
    plays: int = 0

    def sample(self, rng: random.Random) -> float:
        return rng.betavariate(self.alpha, self.beta)

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)


class SetListController:
    """Thompson-sampling set list over frozen artifacts, grouped by frame."""

    def __init__(self, artifact_paths: list[str | Path], show_id: str | None = None, seed: int = 0):
        self.programs: list[JokeProgram] = [load_program(p) for p in artifact_paths]
        self.programs = [p for p in self.programs if p.validated] or self.programs
        self.posteriors: dict[str, FramePosterior] = {}
        for prog in self.programs:
            self.posteriors.setdefault(prog.frame or prog.program_id, FramePosterior(prog.frame or prog.program_id))
        self.rng = random.Random(seed)
        self.performed: list[str] = []
        self.show_id = show_id or time.strftime("show-%Y%m%d-%H%M%S")
        SHOW_LOG_DIR.mkdir(exist_ok=True)
        self.log_path = SHOW_LOG_DIR / f"{self.show_id}.jsonl"

    def _log(self, record: dict[str, Any]) -> None:
        record["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    def next_joke(self) -> tuple[JokeProgram, str, dict[str, float]]:
        """Pick the next artifact: sample each frame's posterior, prefer the
        best frame's least-recently-performed program. Returns (program,
        rendered joke text, sampled frame scores) — the render is seeded by
        play count, so the whole show is reproducible from the log."""
        samples = {f: p.sample(self.rng) for f, p in self.posteriors.items()}
        # unseen frames get an exploration nudge
        for f, p in self.posteriors.items():
            if p.plays == 0:
                samples[f] = max(samples[f], 0.55)
        best_frame = max(samples, key=samples.get)
        candidates = [p for p in self.programs if (p.frame or p.program_id) == best_frame]
        fresh = [p for p in candidates if p.program_id not in self.performed] or candidates
        prog = fresh[0]
        text = run_program(prog, seed=self.posteriors[best_frame].plays)
        self._log({"event": "pick", "program_id": prog.program_id, "frame": best_frame,
                   "samples": {k: round(v, 3) for k, v in samples.items()}, "text": text})
        return prog, text, samples

    def record_result(self, prog: JokeProgram, report: LaughterReport) -> None:
        frame = prog.frame or prog.program_id
        post = self.posteriors[frame]
        post.alpha += report.reward
        post.beta += 1.0 - report.reward
        post.plays += 1
        self.performed.append(prog.program_id)
        self._log({"event": "result", "program_id": prog.program_id, "frame": frame,
                   "report": asdict(report), "reward": report.reward,
                   "posterior": {"mean": round(post.mean, 3), "plays": post.plays}})

    def room_read(self) -> dict[str, Any]:
        """What the controller currently believes about this room's mesh."""
        return {
            "show_id": self.show_id,
            "performed": len(self.performed),
            "frames": {
                f: {"mean": round(p.mean, 3), "plays": p.plays}
                for f, p in sorted(self.posteriors.items(), key=lambda kv: -kv[1].mean)
            },
            "advice": self._advice(),
        }

    def _advice(self) -> str:
        hot = [f for f, p in self.posteriors.items() if p.plays >= 2 and p.mean > 0.6]
        cold = [f for f, p in self.posteriors.items() if p.plays >= 2 and p.mean < 0.3]
        if hot:
            return f"exploit: callback to '{hot[0][:40]}...' — the room has cached that frame"
        if cold and len(cold) == len(self.posteriors):
            return "cold room: switch format or slow down; every frame is under water"
        return "keep exploring frames; not enough evidence to commit"

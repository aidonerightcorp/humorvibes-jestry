"""Compiled comedy: deterministic humor artifacts, Gemma only at compile time.

Adaptation of the "Compiled AI" paradigm (Trooskens et al.: LLMs generate
executable artifacts during a compilation phase; workflows then execute
deterministically with zero model invocations) to humor and short-form media.

Why it fits the theory (THEORY.md §6): a compiled joke template is a *paid-for
frame* — the expensive mesh exploration happens once, offline, where it can be
measured and rejected; the runtime re-route is cheap and reproducible. A
running bit IS compiled comedy. And live performance demands determinism: you
cannot let a model improvise a bad surprise on stage. Gemma explores and
validates in the compile loop; the show executes a frozen, audited artifact.

Pipeline (mirrors the paper's four stages):
  1. GENERATE   Gemma drafts a parameterized template + slot word banks from a
                topic/format brief (or from exemplar jokes).
  2. STATIC     lint: slot syntax, format contract (length budget), banned-
                target rules (no identity-mesh punching), determinism check.
  3. MEASURED   instantiate probe fillers; every probe must land in the laugh
                region (S band, R floor) and pass persona collision checks.
  4. FREEZE     write the artifact JSON with content hash, provenance, measured
                signal profile, and validation verdicts. Runtime never calls a
                model: `run_program` is pure string ops + a seeded RNG.

Artifacts:
  JokeProgram  — template with typed slots + word banks + guards (text formats)
  ClipPlan     — deterministic timeline for a short vertical clip: beat windows,
                 captions, [visual] cues, SNAP timing; renderable by any dumb
                 executor (ffmpeg/moviepy/CapCut template) with no model calls.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from formats import FORMATS
from mesh_signals import SignalProvider, compute_signals, split_setup_punchline

ARTIFACT_DIR = Path(__file__).resolve().parent / "compiled_artifacts"

SLOT_RE = re.compile(r"\{([a-z_]+)\}")

BANNED_TARGET_TERMS = (
    # identity meshes with override authority — never valid slot fillers
    "race", "religion", "disability", "ethnic", "gender identity", "sexual orientation",
)


@dataclass
class JokeProgram:
    program_id: str
    format_key: str
    template: str                      # e.g. "I told my {authority} about my fear of {topic}."
    punch_template: str                # e.g. "She said I'm slowly getting over it."
    slots: dict[str, list[str]]        # word banks compiled per slot
    frame: str                         # the hidden frame this template re-uses
    guards: list[str] = field(default_factory=list)
    measured: dict[str, Any] = field(default_factory=dict)   # probe signal stats
    provenance: dict[str, Any] = field(default_factory=dict)
    validated: bool = False

    def content_hash(self) -> str:
        body = json.dumps(
            {"t": self.template, "p": self.punch_template, "s": self.slots, "f": self.frame},
            sort_keys=True,
        )
        return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


@dataclass
class ClipPlan:
    plan_id: str
    duration_s: float
    beats: list[dict[str, Any]]        # {t0, t1, beat, caption, visual, voice_line}
    snap_at_s: float                   # where the re-route lands; the whole edit serves this
    source_joke: str
    measured: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    validated: bool = False


# ---------------------------------------------------------------------------
# Stage 1 — GENERATE (the only stage that may call Gemma)
# ---------------------------------------------------------------------------
TEMPLATE_PROMPT = (
    "You are compiling a reusable joke TEMPLATE, not a single joke. Placeholders must be NAMED\n"
    "slots in curly braces, and every named slot must have a word bank.\n\n"
    "Example (topic family: pets) — return EXACTLY this JSON shape:\n"
    '{{"template": "My {{animal}} refuses to {{chore}}.",\n'
    '  "punch_template": "He says it is not in his contract.",\n'
    '  "frame": "The pet is treated as a unionized employee with a formal contract.",\n'
    '  "slots": {{"animal": ["cat", "dog", "parrot", "goldfish", "hamster", "iguana"],\n'
    '             "chore": ["do the dishes", "pay rent", "answer emails", "walk himself",\n'
    '                       "attend standup", "file taxes"]}}}}\n\n'
    "Format contract: {contract}\nTopic family: {topic}\nAudience: {audience}\n\n"
    "Return JSON only, same shape: 1-3 lowercase named slots (never the literal word 'slot'),\n"
    "6-10 interchangeable fillers each, and the template must stay funny for EVERY combination —\n"
    "compile the frame, not one joke."
)


def generate_program(
    provider: SignalProvider, topic: str, format_key: str, audience: str = ""
) -> JokeProgram | None:
    spec = FORMATS[format_key]
    contract = f"{spec.structure} Budget: {spec.length_budget}. {spec.generation_directives}"
    parsed = provider.judge_json(
        TEMPLATE_PROMPT.format(contract=contract, topic=topic, audience=audience or "general")
    )
    if not parsed or "template" not in parsed:
        return None
    slots = {
        str(k): [str(v) for v in vals if str(v).strip()]
        for k, vals in (parsed.get("slots") or {}).items()
        if isinstance(vals, list)
    }
    prog = JokeProgram(
        program_id="",
        format_key=format_key,
        template=str(parsed["template"]).strip(),
        punch_template=str(parsed.get("punch_template", "")).strip(),
        slots=slots,
        frame=str(parsed.get("frame", "")).strip(),
        provenance={
            "compiler": provider.name,
            "topic": topic,
            "audience": audience,
            "compiled_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
    )
    prog.program_id = f"{format_key}-{prog.content_hash()}"
    return prog


# ---------------------------------------------------------------------------
# Stage 2 — STATIC validation (no model)
# ---------------------------------------------------------------------------
def static_lint(prog: JokeProgram) -> list[str]:
    errors: list[str] = []
    tmpl_slots = set(SLOT_RE.findall(prog.template + " " + prog.punch_template))
    if not tmpl_slots:
        errors.append("no slots: this is a joke, not a program")
    missing = tmpl_slots - set(prog.slots)
    if missing:
        errors.append(f"slots without word banks: {sorted(missing)}")
    for name, bank in prog.slots.items():
        if name in tmpl_slots and len(bank) < 3:
            errors.append(f"slot '{name}' bank too small ({len(bank)}) for reuse value")
        for filler in bank:
            low = filler.lower()
            if any(term in low for term in BANNED_TARGET_TERMS):
                errors.append(f"slot '{name}' filler '{filler}' targets an identity mesh")
    spec = FORMATS[prog.format_key]
    max_words = {"one_liner": 24, "tweet": 60, "meme_caption": 24}.get(prog.format_key)
    if max_words:
        longest = _instantiate(prog, {n: max(b, key=len) for n, b in prog.slots.items()})
        if len(longest.split()) > max_words:
            errors.append(f"worst-case instantiation exceeds {spec.length_budget}")
    if not prog.frame:
        errors.append("no frame declared: nothing to compile")
    return errors


def _instantiate(prog: JokeProgram, choice: dict[str, str]) -> str:
    text = prog.template + (" " + prog.punch_template if prog.punch_template else "")
    for name, filler in choice.items():
        text = text.replace("{" + name + "}", filler)
    return text.strip()


# ---------------------------------------------------------------------------
# Stage 3 — MEASURED validation (provider used as instrument only)
# ---------------------------------------------------------------------------
def measured_validate(
    provider: SignalProvider,
    prog: JokeProgram,
    n_probes: int = 4,
    personas: list[str] | None = None,
    s_band: tuple[float, float] = (1.2, 5.5),
    r_floor: float = 0.4,
    collision_ceiling: float = 5.0,
) -> dict[str, Any]:
    rng = random.Random(prog.content_hash())  # deterministic probe choice
    names = list(prog.slots)
    probes: list[dict[str, str]] = []
    for _ in range(n_probes):
        probes.append({n: rng.choice(prog.slots[n]) for n in names})
    results = []
    for choice in probes:
        text = _instantiate(prog, choice)
        setup, punch = split_setup_punchline(text)
        sig = compute_signals(provider, setup, punch, frame_hint=prog.frame, personas=personas or [])
        results.append(
            {
                "probe": choice,
                "S": sig.surprise_mean,
                "R": sig.resolution,
                "E": sig.efficiency,
                "collision": sig.bad_surprise,
                "in_band": s_band[0] < sig.surprise_mean < s_band[1],
                "measured": sig.measured,
            }
        )
    passed = [
        r for r in results if r["in_band"] and r["R"] >= r_floor and r["collision"] <= collision_ceiling
    ]
    return {
        "probes": results,
        "pass_rate": round(len(passed) / len(results), 2) if results else 0.0,
        "instrumented": all(r["measured"] for r in results),
        "thresholds": {"s_band": s_band, "r_floor": r_floor, "collision_ceiling": collision_ceiling},
    }


# ---------------------------------------------------------------------------
# Stage 4 — FREEZE / runtime (never calls a model)
# ---------------------------------------------------------------------------
def freeze(prog: JokeProgram, report: dict[str, Any], min_pass_rate: float = 0.75) -> Path:
    prog.measured = {k: v for k, v in report.items() if k != "probes"}
    prog.measured["probe_count"] = len(report.get("probes", []))
    prog.validated = report.get("pass_rate", 0.0) >= min_pass_rate and report.get("instrumented", False)
    ARTIFACT_DIR.mkdir(exist_ok=True)
    out = ARTIFACT_DIR / f"{prog.program_id}.json"
    payload = asdict(prog)
    payload["stage3_probes"] = report.get("probes", [])
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def load_program(path: str | Path) -> JokeProgram:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data.pop("stage3_probes", None)
    return JokeProgram(**data)


def run_program(prog: JokeProgram, seed: int | None = None, avoid_repeat: int = 0) -> str:
    """Deterministic runtime: seeded slot choice, zero model calls.

    Same seed -> same joke, auditable before it is ever performed. avoid_repeat
    rotates through the bank so a set list never repeats a filler back-to-back.
    """
    rng = random.Random(seed if seed is not None else 0)
    choice = {}
    for name, bank in prog.slots.items():
        idx = (rng.randrange(len(bank)) + avoid_repeat) % len(bank)
        choice[name] = bank[idx]
    return _instantiate(prog, choice)


# ---------------------------------------------------------------------------
# ClipPlan compiler: shorts beat sheet -> deterministic render timeline
# ---------------------------------------------------------------------------
BEAT_RE = re.compile(r"(HOOK|BUILD|SNAP)\s*:\s*(.+)", re.IGNORECASE)
VISUAL_RE = re.compile(r"\[(.+?)\]")

# spoken-word pacing for timing: ~2.6 words/second for punchy shorts delivery
WORDS_PER_SECOND = 2.6
BEAT_GAP_S = 0.4


def compile_clip_plan(script_text: str, provider: SignalProvider | None = None) -> ClipPlan:
    """Turn a HOOK:/BUILD:/SNAP: script into a deterministic timeline.

    The plan is executable by any renderer (ffmpeg drawtext, moviepy, a CapCut
    template, or a human editor) — the timing math is the compiler's output,
    not a runtime model decision.
    """
    beats_raw = [(m.group(1).upper(), m.group(2).strip()) for m in BEAT_RE.finditer(script_text)]
    if not beats_raw:
        raise ValueError("no HOOK:/BUILD:/SNAP: beats found")
    t = 0.0
    beats: list[dict[str, Any]] = []
    snap_at = 0.0
    for beat, body in beats_raw:
        visuals = VISUAL_RE.findall(body)
        voice = VISUAL_RE.sub("", body).strip()
        dur = max(1.2, len(voice.split()) / WORDS_PER_SECOND)
        if beat == "SNAP":
            snap_at = t
            dur += 0.8  # hold the frame; laughter needs landing room
        beats.append(
            {
                "t0": round(t, 2),
                "t1": round(t + dur, 2),
                "beat": beat,
                "caption": voice,
                "visual": visuals[0] if visuals else "",
                "voice_line": voice,
            }
        )
        t += dur + BEAT_GAP_S
    measured: dict[str, Any] = {}
    if provider is not None:
        hook = beats[0]["voice_line"]
        snap = next((b["voice_line"] for b in beats if b["beat"] == "SNAP"), "")
        if hook and snap:
            sig = compute_signals(provider, hook, snap)
            measured = {"S": sig.surprise_mean, "R": sig.resolution, "E": sig.efficiency,
                        "measured": sig.measured}
    plan = ClipPlan(
        plan_id=f"clip-{hashlib.sha256(script_text.encode()).hexdigest()[:12]}",
        duration_s=round(t - BEAT_GAP_S, 2),
        beats=beats,
        snap_at_s=round(snap_at, 2),
        source_joke=script_text.strip(),
        measured=measured,
        provenance={"compiled_at": time.strftime("%Y-%m-%dT%H:%M:%S")},
        validated=bool(measured) and measured.get("R", 0) >= 0.4,
    )
    return plan


def save_clip_plan(plan: ClipPlan) -> Path:
    ARTIFACT_DIR.mkdir(exist_ok=True)
    out = ARTIFACT_DIR / f"{plan.plan_id}.json"
    out.write_text(json.dumps(asdict(plan), indent=2), encoding="utf-8")
    return out


def render_ffmpeg_commands(plan: ClipPlan, background: str = "background.mp4") -> list[str]:
    """Emit a deterministic ffmpeg recipe for the plan (caption overlays at
    beat windows). Purely illustrative of zero-model runtime rendering."""
    draws = []
    for b in plan.beats:
        text = b["caption"].replace("'", r"\'")
        draws.append(
            f"drawtext=text='{text}':enable='between(t,{b['t0']},{b['t1']})'"
            ":fontsize=54:fontcolor=white:borderw=3:x=(w-text_w)/2:y=h*0.72"
        )
    filter_chain = ",".join(draws)
    return [
        f"ffmpeg -i {background} -t {plan.duration_s} -vf \"{filter_chain}\" "
        f"-c:a copy compiled_{plan.plan_id}.mp4"
    ]

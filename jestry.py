"""Jestry: the HumorVibes verified laugh-reuse and construction layer.

Charter: JESTRY-CHARTER-AND-CONSTITUTION-2026-07-23.md (Taedri's constitution
mapped onto humor). Motto:

    Find the laugh that already landed. Do not rebuild it. Compose any valid
    bit. Verify it against a measured audience. Learn from every bomb.

Jestry treats the rest of this repository as its supply and its oracles:

- supply    humor_datacenter.mechanisms (capability cards), formats (contracts),
            compiled_artifacts/*.json (route capsules), corpora/*.jsonl
            (licensed source material), jestry_out/accepted_bits.jsonl
            (previously accepted outcomes — the compounding asset)
- construction  compiled_humor (compile pipeline), Gemma 4 through Ollama for
            the genuine residual only
- oracles   mesh_signals.compute_signals (S/R/E/B) on gemma4_nll's forced-NLL
            instrument when the server is up; persona B-gate always hard;
            live_set_controller laughter rewards as the decisive human oracle
- memory    receipts.jsonl (contribution funnel), groaners.jsonl (hard
            negatives), laughloop.json (governed bandit state)

Nothing here rescores or rewrites the pinned Kaggle evidence; this layer only
adds routes, receipts, and reuse on top of it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from compiled_humor import BANNED_TARGET_TERMS, JokeProgram, load_program, run_program
from formats import FORMATS
from humor_datacenter.mechanisms import COMEDY_MECHANISMS
from humor_mesh import extract_candidates
from mesh_signals import OfflineStub, compute_signals, get_provider, split_setup_punchline

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "jestry_out"
ARTIFACT_DIR = ROOT / "compiled_artifacts"
CORPORA_DIR = ROOT / "corpora"

CHARTER_VERSION = "1.0"
MOTTO = (
    "Find the laugh that already landed. Do not rebuild it. Compose any valid bit. "
    "Verify it against a measured audience. Learn from every bomb."
)

# ---------------------------------------------------------------------------
# Constitutional surface (kept in code so the CLI, tests, and charter agree)
# ---------------------------------------------------------------------------
LAWS: tuple[tuple[str, str], ...] = (
    ("Find the funny that already works",
     "Before generating, account for accepted bits, validated programs, licensed corpora, and "
     "known mechanisms. Construction through avoidable ignorance is a defect."),
    ("Generate only the residual twist",
     "When supply covers the frame, Gemma writes only the missing binding — the topical filler, "
     "the format adapter, the tag — never the whole route from scratch."),
    ("Reuse is selective, not compulsory",
     "Valid outcomes include verbatim replay, remix, fresh composition, clarification, and honest "
     "abstention. An irrelevant callback costs more than silence."),
    ("The value unit is a landed laugh",
     "Not a generated joke, a retrieval hit, or a model's self-rating: an outcome accepted by an "
     "independent oracle, reconstructable from its receipt."),
    ("Search proposes; contracts compose; laughter decides",
     "Similarity is not compatibility; retrieval is not adoption; a Gemma judgment is not a human "
     "laugh. Format contracts and persona gates bind between proposal and acceptance."),
    ("Escalate the bit before the model",
     "Replay costs nothing; a seeded template costs nothing; a remix costs one adapter; only the "
     "genuine residual earns fresh model reasoning."),
    ("Preference and permission are separate",
     "Cost, style, register, and vibe are preferences. The persona B-gate, the banned-target lint, "
     "the dignity gate, and consent are hard requirements no optimizer may trade away."),
    ("Identity is exact and versioned",
     "Bits, programs, prompts, models, and receipts carry stable ids, digests, and provenance. "
     "A remix names its source and license."),
    ("Contribution must be traced",
     "Receipts distinguish discovered, retrieved, selected, resolved, composed, told, "
     "instrument-scored, persona-gated, and accepted. Invocation is not contribution."),
    ("External laughter is the final authority",
     "Instrument scores select candidates; only measured audience reaction (or an equivalent "
     "independent oracle) accepts material. Instrument-accepted is a stage, not the summit."),
    ("Evolution is additive and reversible",
     "New routes and providers arrive as versioned alternatives beside working ones. The pinned "
     "Kaggle evidence is never rewritten by a later layer."),
    ("Every bomb becomes reusable knowledge",
     "Rejected candidates land in the groaner ledger with their failure mode; incompatibility "
     "edges steer future routes away. Negative evidence gets positive-evidence discipline."),
    ("Self-tuning is governed",
     "Laughter updates a shadow posterior; serving order changes only through an explicit, "
     "receipted promotion. No live result silently rewrites behavior."),
    ("No hidden fallback",
     "Every escalation, provider substitution, unmeasured signal, censored logprob, and offline "
     "stub is named in the receipt. Unknown telemetry is reported as unknown, never as zero."),
    ("Originals remain reconstructable",
     "Remixing never erases the source text; compiled artifacts keep their probe history; the "
     "receipt stores prompt and output digests."),
    ("Clarification is a first-class route",
     "When a missing fact (audience, consent, target) materially changes permission or fit, "
     "asking is a valid outcome, not a failure."),
    ("The room is a registered context, not the core",
     "Kaggle, NYC showcases, Slack channels, and comedy clubs are contexts supplying personas, "
     "formats, and oracles. The loop itself stays universal."),
    ("Honest abstention beats confident bombing",
     "The system can report: no compatible material, instrument unavailable, policy prohibited, "
     "consent missing, or a formal capability gap — each as a first-class receipt."),
)

FUNNEL_STAGES = (
    "discovered", "retrieved", "selected", "resolved", "composed",
    "told", "instrument_scored", "persona_gated", "accepted",
)

ACCEPTANCE_LEVELS = (
    "drafted", "lint_passed", "instrument_scored", "persona_permitted",
    "human_laughed", "crowd_accepted",
)

COMPAT = (
    "EXACTLY_COMPATIBLE", "COMPATIBLE_WITH_BINDING", "COMPATIBLE_WITH_ADAPTER",
    "REQUIRES_RUNTIME_PROBE", "INCOMPATIBLE", "PROHIBITED_BY_POLICY", "UNKNOWN",
)

VULNERABLE_MARKERS = ("grief", "funeral", "diagnos", "cancer", "divorce", "miscarriage",
                      "suicide", "bankrupt", "relapse", "custody")
POLITICAL_MARKERS = ("politic", "congress", "senate", "president", "vote", "party",
                     "liberal", "conservative", "democrat", "republican", "election")

_EMPHASIS_RE = re.compile(r"[*_`]+")

TRUSTED_FRAME_LICENSE_MARKERS = ("public domain", "traditional", "session-curated")


def clean_candidate(text: str) -> str:
    """Strip markdown emphasis before measurement: the PERFORMED joke has no
    asterisks, and rare `*`-tokens inflate S with formatting, not comedy."""
    return _EMPHASIS_RE.sub("", text).strip()


def trusted_frame_source(attribution: dict[str, Any] | None) -> bool:
    """Frame provenance is a HARD gate (adversarial finding 2026-07-24): a
    crafted frame_hint can walk a mundane line into the calibrated acceptance
    region (boring control measured R=0.215 under a hand-written frame). Only
    curated/traditional supply may hand the oracle a frame; anything else gets
    the model-guessed frame, which measured R=0.00 on that same attack."""
    if not attribution:
        return False
    license_ = str(attribution.get("license", "")).lower()
    return any(marker in license_ for marker in TRUSTED_FRAME_LICENSE_MARKERS)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# Canonical objects
# ---------------------------------------------------------------------------
@dataclass
class BitCard:
    """Body-free capability card: enough to search and compare, never the body."""

    bit_id: str
    kind: str              # mechanism | format | corpus_item | joke_program | joke | probe
    name: str
    one_line: str
    version: str = "1"
    format_keys: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    effects: tuple[str, ...] = ()          # risk notes / stage effects
    acceptance_level: str = "drafted"
    provenance: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    digest: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkSpec:
    """What outcome is actually required (normalized request)."""

    topic: str
    audience: str = "a general audience"
    format_key: str = "one_liner"
    preferences: str = ""
    personas: tuple[str, ...] = ()
    consent: bool = False              # roast/callback dignity gate input
    candidates: int = 3
    acceptance: str = "laugh region + persona B-gate"
    unknowns: tuple[str, ...] = ()

    @classmethod
    def from_request(cls, text: str, *, audience: str = "", format_key: str = "one_liner",
                     preferences: str = "", personas: str = "", consent: bool = False,
                     candidates: int = 3) -> "WorkSpec":
        topic = re.sub(r"^(please\s+)?(make|write|generate)\s+(a\s+|some\s+)?jokes?\s+(about|on|for)\s+",
                       "", text.strip(), flags=re.I).strip() or text.strip()
        plist = tuple(p.strip() for p in personas.split(",") if p.strip())
        unknowns: list[str] = []
        if not audience:
            unknowns.append("audience unspecified — using 'a general audience'")
        aud = audience.strip() or "a general audience"
        if not plist:
            plist = (aud,)
        if any(m in text.lower() for m in POLITICAL_MARKERS) and len(plist) < 2:
            # bridge doctrine: political material is judged under BOTH meshes
            plist = plist + ("a left-leaning audience", "a right-leaning audience")
        return cls(topic=topic, audience=aud, format_key=format_key,
                   preferences=preferences, personas=plist, consent=consent,
                   candidates=max(1, min(candidates, 6)), unknowns=tuple(unknowns))

    def query_text(self) -> str:
        return " ".join([self.topic, self.audience, self.preferences, self.format_key])


@dataclass
class HumorPolicy:
    """Hard permission layer (Law: preference and permission are separate)."""

    collision_ceiling: float = 5.0
    banned_terms: tuple[str, ...] = BANNED_TARGET_TERMS
    require_consent_formats: tuple[str, ...] = ("roast_line",)
    block_vulnerable_disclosures: bool = True

    def check(self, spec: WorkSpec) -> tuple[str, str]:
        """Returns (compat, reason). PROHIBITED_BY_POLICY is not negotiable."""
        low = f"{spec.topic} {spec.preferences}".lower()
        for term in self.banned_terms:
            if term in low:
                return ("PROHIBITED_BY_POLICY",
                        f"topic targets an identity mesh ('{term}') — banned-target lint")
        if self.block_vulnerable_disclosures and any(m in low for m in VULNERABLE_MARKERS):
            return ("PROHIBITED_BY_POLICY",
                    "vulnerable disclosure detected — dignity gate: never material")
        if spec.format_key in self.require_consent_formats and not spec.consent:
            return ("PROHIBITED_BY_POLICY",
                    f"format '{spec.format_key}' requires explicit consent (roast doctrine)")
        if spec.format_key not in FORMATS:
            return ("INCOMPATIBLE", f"unknown format '{spec.format_key}'")
        return ("EXACTLY_COMPATIBLE", "policy allows this request")


@dataclass
class RouteProfile:
    """Preferences (Law: escalate the bit before the model)."""

    name: str = "least_cost"
    ladder: tuple[str, ...] = ("replay_accepted", "replay_program", "remix_corpus",
                              "compose_residual", "frontier_compose")
    require_measured: bool = True        # accepted outcomes need a real instrument
    require_certified: bool = True       # ...and a CERTIFIED calibration for it
    max_model_candidates: int = 4
    temperature: float = 0.75
    frontier_temperature: float = 0.95
    replay_topic_floor: float = 0.34     # min keyword overlap to trust a replay


@dataclass
class RouteNode:
    role: str                            # supply | adapter | generator | oracle | policy
    bit_id: str
    version: str = "1"
    digest: str = ""
    binding: dict[str, Any] = field(default_factory=dict)


@dataclass
class RouteIR:
    kind: str                            # ladder rung | ABSTAIN | CLARIFY
    compat: str
    nodes: list[RouteNode] = field(default_factory=list)
    reason: str = ""
    estimated_model_calls: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "compat": self.compat, "reason": self.reason,
                "estimated_model_calls": self.estimated_model_calls,
                "nodes": [asdict(n) for n in self.nodes]}


# ---------------------------------------------------------------------------
# Registry: unify existing supply behind body-free cards
# ---------------------------------------------------------------------------
class BitRegistry:
    def __init__(self, root: Path = ROOT, out_dir: Path = OUT_DIR) -> None:
        self.root = root
        self.out_dir = out_dir
        self.cards: dict[str, BitCard] = {}
        self._bodies: dict[str, Any] = {}
        self.incompatible: set[tuple[str, str]] = set()   # (bit_id, topic_digest) edges
        self._build()

    # -- construction ------------------------------------------------------
    def _add(self, card: BitCard, body: Any = None) -> None:
        if not card.digest:
            card.digest = _sha(card.bit_id + "::" + card.one_line)[:16]
        self.cards[card.bit_id] = card
        if body is not None:
            self._bodies[card.bit_id] = body

    def _build(self) -> None:
        for mech in COMEDY_MECHANISMS:
            self._add(BitCard(
                bit_id=f"mechanism:{mech.mechanism_id}", kind="mechanism", name=mech.name,
                one_line=mech.description,
                keywords=tuple(mech.keywords) + tuple(mech.best_when),
                effects=mech.risk_notes, acceptance_level="crowd_accepted",
                provenance={"source": "humor_datacenter.mechanisms", "study_hooks": list(mech.study_hooks)},
            ), body=mech)
        for key, spec in FORMATS.items():
            self._add(BitCard(
                bit_id=f"format:{key}", kind="format", name=spec.label,
                one_line=spec.structure, format_keys=(key,),
                keywords=(key, spec.media), acceptance_level="crowd_accepted",
                provenance={"source": "formats.FORMATS"},
            ), body=spec)
        for path in sorted(CORPORA_DIR.glob("*.jsonl")):
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "_meta" in rec:
                    continue
                text = str(rec.get("text") or rec.get("joke") or "").strip()
                if not text:
                    continue
                bid = f"corpus:{path.stem}:{i}"
                # acceptance levels record OUR pipeline's verification, not
                # cultural attestation: harvested material starts at drafted
                # (adversarial finding — the "verified-or-better" tile was
                # counting every fresh dad joke as crowd_accepted)
                self._add(BitCard(
                    bit_id=bid, kind="corpus_item", name=f"{path.stem}[{i}]",
                    one_line=text[:140],
                    keywords=tuple(w.lower() for w in re.findall(r"[a-zA-Z]{5,}", text)[:8]),
                    acceptance_level="drafted",
                    provenance={"source": rec.get("source", path.stem),
                                "license": rec.get("license", "unknown"),
                                "cls": rec.get("cls", "")},
                ), body=rec)
        if ARTIFACT_DIR.exists():
            for path in sorted(ARTIFACT_DIR.glob("*.json")):
                try:
                    prog = load_program(path)
                except Exception:
                    continue
                self._add(BitCard(
                    bit_id=f"program:{prog.program_id}", kind="joke_program",
                    name=prog.program_id, one_line=prog.frame or prog.template,
                    format_keys=(prog.format_key,),
                    keywords=tuple(re.findall(r"[a-zA-Z]{5,}",
                                              (prog.provenance.get("topic", "") + " " + prog.frame).lower())[:10]),
                    acceptance_level="instrument_scored" if prog.validated else "lint_passed",
                    provenance=dict(prog.provenance) | {"path": str(path)},
                    evidence=dict(prog.measured),
                ), body=prog)
        accepted = self.out_dir / "accepted_bits.jsonl"
        if accepted.exists():
            for line in accepted.read_text(encoding="utf-8").splitlines():
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self._add(BitCard(
                    bit_id=rec["bit_id"], kind="joke", name=rec.get("name", rec["bit_id"]),
                    one_line=rec.get("text", "")[:140],
                    format_keys=tuple(rec.get("format_keys", ())),
                    keywords=tuple(rec.get("keywords", ())),
                    acceptance_level=rec.get("acceptance_level", "instrument_scored"),
                    provenance=rec.get("provenance", {}), evidence=rec.get("evidence", {}),
                ), body=rec)
        groaners = self.out_dir / "groaners.jsonl"
        if groaners.exists():
            for line in groaners.read_text(encoding="utf-8").splitlines():
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for bid in rec.get("bit_ids", []):
                    self.incompatible.add((bid, rec.get("topic_digest", "")))

    # -- honest census (Law: catalogue scale is not working-bit scale) -----
    def census(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for card in self.cards.values():
            counts[card.kind] = counts.get(card.kind, 0) + 1
        counts["accepted_or_better"] = sum(
            1 for c in self.cards.values()
            if ACCEPTANCE_LEVELS.index(c.acceptance_level) >= ACCEPTANCE_LEVELS.index("instrument_scored")
        )
        counts["total_cards"] = len(self.cards)
        return counts

    def digest(self) -> str:
        body = json.dumps(sorted((c.bit_id, c.version, c.digest) for c in self.cards.values()))
        return _sha(body)[:16]

    # -- retrieval ---------------------------------------------------------
    def search(self, spec: WorkSpec, kinds: tuple[str, ...] = (), limit: int = 8) -> list[BitCard]:
        terms = {t for t in re.findall(r"[a-zA-Z]{4,}", spec.query_text().lower())}
        topic_digest = _sha(spec.topic.lower())[:12]
        scored: list[tuple[float, BitCard]] = []
        for card in self.cards.values():
            if kinds and card.kind not in kinds:
                continue
            if (card.bit_id, topic_digest) in self.incompatible:
                continue
            hay = " ".join([card.name, card.one_line, " ".join(card.keywords)]).lower()
            overlap = sum(1 for t in terms if t in hay)
            if card.format_keys and spec.format_key in card.format_keys:
                overlap += 2.0
            level_bonus = ACCEPTANCE_LEVELS.index(card.acceptance_level) * 0.25
            if overlap > 0 or (card.format_keys and spec.format_key in card.format_keys):
                scored.append((overlap + level_bonus, card))
        scored.sort(key=lambda kv: (-kv[0], kv[1].bit_id))
        return [c for _, c in scored[:limit]]

    def resolve(self, bit_id: str) -> Any:
        return self._bodies.get(bit_id)

    def topic_overlap(self, card: BitCard, spec: WorkSpec) -> float:
        terms = {t for t in re.findall(r"[a-zA-Z]{4,}", spec.topic.lower())}
        if not terms:
            return 0.0
        hay = " ".join([card.name, card.one_line, " ".join(card.keywords)]).lower()
        return sum(1 for t in terms if t in hay) / len(terms)


# ---------------------------------------------------------------------------
# Ledgers: receipts, groaners, governed laughter loop
# ---------------------------------------------------------------------------
class Receipts:
    def __init__(self, out_dir: Path = OUT_DIR) -> None:
        self.out_dir = out_dir
        self.path = out_dir / "receipts.jsonl"

    def write(self, record: dict[str, Any]) -> dict[str, Any]:
        record = {"receipt_type": "jestry_route", "receipt_version": 1,
                  "charter_version": CHARTER_VERSION, "ts": _now()} | record
        self.out_dir.mkdir(exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out


class GroanerLedger:
    """Hard negatives with the theory's failure taxonomy (Law: every bomb...)."""

    def __init__(self, out_dir: Path = OUT_DIR) -> None:
        self.out_dir = out_dir
        self.path = out_dir / "groaners.jsonl"

    def record(self, *, joke: str, failure_mode: str, signals: dict[str, Any],
               route_kind: str, bit_ids: list[str], topic: str) -> dict[str, Any]:
        rec = {"ts": _now(), "joke_digest": _sha(joke)[:16], "joke": joke,
               "failure_mode": failure_mode, "signals": signals,
               "route_kind": route_kind, "bit_ids": bit_ids,
               "topic_digest": _sha(topic.lower())[:12]}
        self.out_dir.mkdir(exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    def tail(self, n: int = 10) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()[-n:]
        return [json.loads(x) for x in lines if x.strip()]


class LaughLoop:
    """Governed bandit: laughter updates SHADOW state; serving changes only via
    an explicit, receipted promotion (Law: self-tuning is governed)."""

    def __init__(self, out_dir: Path = OUT_DIR) -> None:
        self.out_dir = out_dir
        self.path = out_dir / "laughloop.json"
        self.state = {"serving": {}, "shadow": {}, "log": []}
        if self.path.exists():
            try:
                self.state = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

    def _save(self) -> None:
        self.out_dir.mkdir(exist_ok=True)
        self.path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def record_laughter(self, frame: str, laughter_seconds: float) -> dict[str, Any]:
        reward = max(0.0, min(1.0, laughter_seconds / 3.0))
        post = self.state["shadow"].setdefault(frame, {"alpha": 1.0, "beta": 1.0, "plays": 0})
        post["alpha"] += reward
        post["beta"] += 1.0 - reward
        post["plays"] += 1
        entry = {"ts": _now(), "event": "shadow_update", "frame": frame,
                 "laughter_seconds": laughter_seconds, "reward": round(reward, 3)}
        self.state["log"].append(entry)
        self._save()
        return entry

    def promote(self) -> dict[str, Any]:
        before = json.dumps(self.state["serving"], sort_keys=True)
        self.state["serving"] = json.loads(json.dumps(self.state["shadow"]))
        entry = {"ts": _now(), "event": "default_change", "change": "serving<=shadow",
                 "before_digest": _sha(before)[:12],
                 "after_digest": _sha(json.dumps(self.state["serving"], sort_keys=True))[:12],
                 "frames": len(self.state["serving"])}
        self.state["log"].append(entry)
        self._save()
        return entry

    def serving_order(self) -> list[tuple[str, float]]:
        rows = [(f, p["alpha"] / (p["alpha"] + p["beta"]))
                for f, p in self.state["serving"].items()]
        rows.sort(key=lambda kv: -kv[1])
        return rows


# ---------------------------------------------------------------------------
# Model access with usage capture (Law: no hidden fallback / unrecorded usage)
# ---------------------------------------------------------------------------
class CountingProvider:
    """Wrap any SignalProvider; count calls so receipts never invent zeros."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.name = getattr(inner, "name", "unknown")
        self.model = getattr(inner, "model", getattr(getattr(inner, "_gen", None), "model", "unknown"))
        self.nll_calls = 0
        self.generate_calls = 0
        self.judge_calls = 0

    def nll_tokens(self, context: str, continuation: str):
        self.nll_calls += 1
        return self.inner.nll_tokens(context, continuation)

    def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 220) -> str:
        self.generate_calls += 1
        return self.inner.generate(prompt, temperature=temperature, max_tokens=max_tokens)

    def judge_json(self, prompt: str):
        self.judge_calls += 1
        return self.inner.judge_json(prompt)

    def usage(self) -> dict[str, Any]:
        rec = {"provider": self.name, "model": str(self.model),
               "nll_calls": self.nll_calls, "generate_calls": self.generate_calls,
               "judge_calls": self.judge_calls}
        forced = getattr(self.inner, "calls", None)
        if forced is not None:
            rec["forced_nll_api_calls"] = forced
        errors = getattr(self.inner, "errors", None)
        if errors:
            rec["instrument_errors"] = errors
            rec["last_instrument_error"] = str(getattr(self.inner, "last_error", ""))[:160]
        restarts = getattr(self.inner, "restarts", None)
        if restarts:
            rec["instrument_worker_restarts"] = restarts
        return rec


def _usage_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Per-run oracle usage: counters are lifetime-cumulative on long-lived
    providers (the portal singleton), so receipts record the delta
    (adversarial finding — receipt k was carrying calls from runs 1..k)."""
    out = dict(after)
    for k, v in after.items():
        if isinstance(v, int) and isinstance(before.get(k), int):
            out[k] = v - before[k]
    return out


def ollama_generate_with_usage(prompt: str, *, model: str | None = None,
                               temperature: float = 0.75, max_tokens: int = 640,
                               host: str | None = None) -> dict[str, Any]:
    """Direct generation call that keeps token counts and digests for receipts."""
    model = model or os.environ.get("GEMMA_MODEL", "gemma4")
    host = (host or os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")).rstrip("/")
    payload = {"model": model, "prompt": prompt, "stream": False, "think": False,
               "options": {"temperature": temperature, "num_predict": max_tokens}}
    req = urllib.request.Request(f"{host}/api/generate",
                                 data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "model": model,
                "prompt_sha256": _sha(prompt)}
    return {"ok": True, "model": model, "response": str(data.get("response", "")).strip(),
            "prompt_sha256": _sha(prompt), "output_sha256": _sha(str(data.get("response", ""))),
            "prompt_tokens": data.get("prompt_eval_count"), "output_tokens": data.get("eval_count"),
            "wall_s": round(time.time() - t0, 2), "thinking_enabled": False}


# ---------------------------------------------------------------------------
# Route compilation (the ladder) and execution
# ---------------------------------------------------------------------------
REMIX_PROMPT = (
    "You are adapting EXISTING licensed material into a new humor format — a format transfer, "
    "not a new joke. Preserve the original comic frame; change only the surface.\n\n"
    "Original material (source: {source}; license: {license}):\n{text}\n\n"
    "Target format: {format_label}. Contract: {structure} Budget: {budget}. {directives}\n"
    "Audience: {audience}. Preferences: {preferences}.\n\n"
    'Return JSON only: {{"candidates": ["...", "..."]}} with {n} distinct adaptations. '
    "Do not claim the material as new; the attribution stays with the source."
)

COMPOSE_PROMPT = (
    "Write {n} distinct {format_label} candidates about: {topic}\n"
    "Audience: {audience}. Preferences: {preferences}.\n"
    "Format contract: {structure} Budget: {budget}. {directives}\n\n"
    "Use these PROVEN comedy mechanisms (retrieved from the registry — reuse the moves, "
    "generate only the residual content):\n{mechanisms}\n\n"
    'Return JSON only: {{"candidates": ["...", "..."]}}. Each candidate must be complete, '
    "performable text with a real turn — no meta-commentary, no numbering inside strings."
)


class Jestry:
    def __init__(self, *, registry: BitRegistry | None = None,
                 policy: HumorPolicy | None = None, profile: RouteProfile | None = None,
                 provider: Any = None, out_dir: Path = OUT_DIR) -> None:
        self.registry = registry or BitRegistry(out_dir=out_dir)
        self.policy = policy or HumorPolicy()
        self.profile = profile or RouteProfile()
        self.out_dir = out_dir
        self.receipts = Receipts(out_dir)
        self.groaners = GroanerLedger(out_dir)
        self.laughloop = LaughLoop(out_dir)
        self.provider = CountingProvider(provider) if provider is not None else None

    # -- instrument calibration (explicit, receipted; never silent) --------
    def _calibration(self, oracle: "CountingProvider") -> dict[str, Any] | None:
        for path in sorted(self.out_dir.glob("*calibration*.json")):
            try:
                cal = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if (cal.get("instrument") == oracle.name and cal.get("certified")
                    and cal.get("derived")):
                return cal["derived"] | {"ts": cal.get("ts")}
        return None              # uncertified calibration never gates acceptance

    # -- provider ----------------------------------------------------------
    def _oracle(self) -> CountingProvider:
        if self.provider is None:
            kind = os.environ.get("GEMMA_PROVIDER", "").strip().lower()
            inner: Any = None
            if kind in ("", "full", "gemma2-full"):
                # certified-capable instrument first: full-vocab teacher
                # forcing on gemma-2-2b (llama.cpp); gemma4 stays generator
                try:
                    from gemma2_full_nll import Gemma2FullNLLProvider, available as full_ok
                    if full_ok():
                        inner = Gemma2FullNLLProvider()
                except Exception:
                    inner = None
            if inner is None and kind in ("", "gemma4", "ollama", "forced"):
                try:
                    from gemma4_nll import Gemma4ForcedNLLProvider, available
                    if available():
                        inner = Gemma4ForcedNLLProvider()
                except Exception:
                    inner = None
            if inner is None:
                inner = get_provider(kind or None)
            self.provider = CountingProvider(inner)
        return self.provider

    # -- compile -----------------------------------------------------------
    def compile_route(self, spec: WorkSpec) -> RouteIR:
        compat, reason = self.policy.check(spec)
        if compat in ("PROHIBITED_BY_POLICY", "INCOMPATIBLE"):
            kind = "ABSTAIN" if compat == "PROHIBITED_BY_POLICY" else "CLARIFY"
            return RouteIR(kind=kind, compat=compat, reason=reason)

        fmt_node = RouteNode(role="policy", bit_id=f"format:{spec.format_key}")

        for rung in self.profile.ladder:
            if rung == "replay_accepted":
                cards = [c for c in self.registry.search(spec, kinds=("joke",), limit=4)
                         if self.registry.topic_overlap(c, spec) >= self.profile.replay_topic_floor
                         and (not c.format_keys or spec.format_key in c.format_keys)]
                if cards:
                    return RouteIR(kind=rung, compat="EXACTLY_COMPATIBLE",
                                   reason=f"accepted bit '{cards[0].bit_id}' matches topic+format",
                                   nodes=[fmt_node, RouteNode(role="supply", bit_id=cards[0].bit_id,
                                                              digest=cards[0].digest)],
                                   estimated_model_calls=0)
            elif rung == "replay_program":
                cards = [c for c in self.registry.search(spec, kinds=("joke_program",), limit=4)
                         if c.acceptance_level in ("instrument_scored", "persona_permitted",
                                                   "human_laughed", "crowd_accepted")
                         and spec.format_key in c.format_keys
                         and self.registry.topic_overlap(c, spec) >= self.profile.replay_topic_floor]
                if cards:
                    return RouteIR(kind=rung, compat="COMPATIBLE_WITH_BINDING",
                                   reason=f"validated program '{cards[0].bit_id}' replays with a seed binding",
                                   nodes=[fmt_node, RouteNode(role="supply", bit_id=cards[0].bit_id,
                                                              digest=cards[0].digest,
                                                              binding={"seed": 7})],
                                   estimated_model_calls=0)
            elif rung == "remix_corpus":
                cards = [c for c in self.registry.search(spec, kinds=("corpus_item",), limit=6)
                         if self.registry.topic_overlap(c, spec) >= 0.25
                         and c.provenance.get("license", "unknown") != "unknown"]
                # a source that carries its own frame is worth more to a remix
                # than a bare text: the frame is the reused asset (Law 8)
                def _has_frame(card: BitCard) -> bool:
                    body = self.registry.resolve(card.bit_id) or {}
                    meta = body.get("meta") if isinstance(body.get("meta"), dict) else {}
                    return bool(meta.get("humor_hook") or meta.get("frame"))
                cards.sort(key=lambda c: not _has_frame(c))
                if cards:
                    return RouteIR(kind=rung, compat="COMPATIBLE_WITH_ADAPTER",
                                   reason=f"licensed corpus item '{cards[0].bit_id}' accepts a format adapter",
                                   nodes=[fmt_node,
                                          RouteNode(role="supply", bit_id=cards[0].bit_id, digest=cards[0].digest),
                                          RouteNode(role="adapter", bit_id="adapter:format_transfer",
                                                    binding={"target_format": spec.format_key})],
                                   estimated_model_calls=1)
            elif rung == "compose_residual":
                mechs = self.registry.search(spec, kinds=("mechanism",), limit=4)
                if mechs:
                    return RouteIR(kind=rung, compat="REQUIRES_RUNTIME_PROBE",
                                   reason="mechanism cards constrain generation to the residual twist",
                                   nodes=[fmt_node] + [RouteNode(role="supply", bit_id=m.bit_id,
                                                                 digest=m.digest) for m in mechs]
                                         + [RouteNode(role="generator", bit_id="model:gemma4",
                                                      binding={"candidates": spec.candidates})],
                                   estimated_model_calls=1)
            elif rung == "frontier_compose":
                return RouteIR(kind=rung, compat="REQUIRES_RUNTIME_PROBE",
                               reason="no reusable supply matched — full construction is the residual",
                               nodes=[fmt_node, RouteNode(role="generator", bit_id="model:gemma4",
                                                          binding={"candidates": spec.candidates,
                                                                   "temperature": self.profile.frontier_temperature})],
                               estimated_model_calls=1)
        return RouteIR(kind="ABSTAIN", compat="UNKNOWN", reason="ladder exhausted with no eligible rung")

    # -- execute + verify --------------------------------------------------
    def run(self, spec: WorkSpec, *, live: bool = True, max_escalations: int = 2) -> dict[str, Any]:
        """The whole loop: compile -> execute -> verify -> preserve. Returns the receipt."""
        t0 = time.time()
        funnel = {k: 0 for k in FUNNEL_STAGES}
        funnel["discovered"] = len(self.registry.cards)
        route = self.compile_route(spec)
        route_history: list[dict[str, Any]] = [route.to_dict()]
        escalations: list[dict[str, str]] = []
        oracle = self._oracle()
        usage_before = oracle.usage()
        generation_usage: list[dict[str, Any]] = []

        candidates: list[dict[str, Any]] = []
        accepted: dict[str, Any] | None = None
        tried_rungs: set[str] = set()

        while True:
            if route.kind in ("ABSTAIN", "CLARIFY"):
                break
            tried_rungs.add(route.kind)
            funnel["retrieved"] += sum(1 for n in route.nodes if n.role == "supply")
            funnel["selected"] += 1 if route.nodes else 0
            batch = self._execute(route, spec, live=live, usage_sink=generation_usage)
            funnel["resolved"] += sum(1 for n in route.nodes if n.role == "supply")
            funnel["composed"] += len(batch)
            verdicts = self._verify(route, spec, batch, oracle, live=live)
            candidates.extend(verdicts)
            funnel["told"] += len(verdicts)
            funnel["instrument_scored"] += sum(
                1 for v in verdicts
                if v["signals"].get("measured") and not v["signals"].get("carried"))
            funnel["persona_gated"] += sum(1 for v in verdicts if v["b_gate_evaluated"])
            # Law: every bomb becomes reusable knowledge — rejected candidates
            # are ledgered even when a sibling in the same batch wins. But
            # blame (the incompatibility edge) only attaches when the WHOLE
            # batch failed: a supply that produced an accepted sibling must
            # not be blacklisted by its sibling's bomb (adversarial finding —
            # the winning corpus item was being banned for its own topic).
            winners = [v for v in verdicts if v["accepted"]]
            blame = [] if winners else [n.bit_id for n in route.nodes if n.role == "supply"]
            for v in verdicts:
                if v["accepted"] or v["signals"].get("carried"):
                    continue
                self.groaners.record(joke=v["text"], failure_mode=v["signals"].get("failure_mode", "unknown"),
                                     signals={k: v["signals"].get(k) for k in
                                              ("surprise_mean", "resolution", "efficiency", "bad_surprise",
                                               "laugh_score", "measured")},
                                     route_kind=route.kind,
                                     bit_ids=blame,
                                     topic=spec.topic)
            if winners:
                accepted = max(winners, key=lambda v: v["signals"].get("laugh_score") or 0.0)
                funnel["accepted"] = 1
                break
            if len(escalations) >= max_escalations:
                break
            # walk the ladder past ineligible rungs instead of aborting at the
            # first one (adversarial finding: an empty middle rung ended runs
            # with remaining escalation budget and mislabeled them abstained)
            nxt = self._next_rung(route.kind)
            new_route: RouteIR | None = None
            while nxt is not None:
                candidate_route = self._compile_specific(spec, nxt)
                if candidate_route.kind not in ("ABSTAIN", "CLARIFY"):
                    new_route = candidate_route
                    break
                nxt = self._next_rung(nxt)
            if new_route is None:
                break
            escalations.append({"from": route.kind, "to": new_route.kind,
                                "reason": "no candidate reached acceptance"})
            route = new_route
            route_history.append(route.to_dict())

        precedent_block: dict[str, Any] | None = None
        if accepted is not None:
            # been-done annotation (Law: identity is exact — reuse is welcome,
            # hidden reuse is not). Never blocks acceptance; it makes
            # precedent visible in the receipt and the preserved bit.
            try:
                from precedent import quick_check
                precedent_block = quick_check(accepted["text"], live=live, out_dir=self.out_dir)
            except Exception as exc:
                precedent_block = {"verdict": "precedent_check_failed",
                                   "error": f"{type(exc).__name__}: {exc}"}

        outcome: dict[str, Any]
        if accepted is not None:
            level = "persona_permitted" if (accepted["b_gate_evaluated"] and accepted["b_gate_passed"]
                                            and accepted["signals"].get("measured")) else (
                "instrument_scored" if accepted["signals"].get("measured") else "drafted")
            if accepted.get("carried_acceptance"):
                # a replay preserves NOTHING new: re-appending would overwrite
                # the original card's measured evidence with Nones and drift
                # its keywords toward the new topic (adversarial finding)
                level = accepted["carried_acceptance"]
                outcome = {"accepted": True, "acceptance_level": level,
                           "text": accepted["text"], "bit_id": "(carried replay)"}
            else:
                bit = self._preserve_accepted(spec, route, accepted, level)
                outcome = {"accepted": True, "acceptance_level": level,
                           "text": accepted["text"], "bit_id": bit["bit_id"]}
        else:
            reason = route.reason if route.kind in ("ABSTAIN", "CLARIFY") else \
                "no candidate reached acceptance within the escalation budget"
            outcome = {"accepted": False, "acceptance_level": None,
                       "abstained": route.kind in ("ABSTAIN", "CLARIFY"),
                       "reason": reason, "unknowns": list(spec.unknowns)}

        receipt = self.receipts.write({
            "request": {"spec": asdict(spec), "spec_digest": _sha(json.dumps(asdict(spec), sort_keys=True))[:16]},
            "registry_digest": self.registry.digest(),
            "route": route.to_dict(),
            "route_history": route_history,
            "escalations": escalations,
            "funnel": funnel,
            "candidates": [{k: v[k] for k in ("text", "accepted", "b_gate_passed")} | {
                "laugh_score": v["signals"].get("laugh_score"),
                "failure_mode": v["signals"].get("failure_mode"),
                "acceptance_basis": v.get("acceptance_basis", ""),
                "measured": v["signals"].get("measured")} for v in candidates],
            "oracle_usage": _usage_delta(usage_before, oracle.usage()),
            "generation_usage": generation_usage,
            "precedent": precedent_block,
            "outcome": outcome,
            "wall_s": round(time.time() - t0, 2),
            "truth_boundary": {
                "instrument": oracle.name,
                "teacher_forced_logprobs_measured": any(
                    v["signals"].get("measured") and not v["signals"].get("carried")
                    for v in candidates),
                "nll_may_be_lower_bound": any(v["signals"].get("censored", 0) for v in candidates),
                "model_judgment_is_not_human_laughter": True,
                "competition_submission": False,
            },
        })
        return receipt

    # -- internals ---------------------------------------------------------
    def _next_rung(self, current: str) -> str | None:
        ladder = list(self.profile.ladder)
        if current not in ladder:
            return None
        idx = ladder.index(current)
        return ladder[idx + 1] if idx + 1 < len(ladder) else None

    def _compile_specific(self, spec: WorkSpec, rung: str) -> RouteIR:
        saved = self.profile.ladder
        try:
            self.profile.ladder = (rung,)
            return self.compile_route(spec)
        finally:
            self.profile.ladder = saved

    def _execute(self, route: RouteIR, spec: WorkSpec, *, live: bool,
                 usage_sink: list[dict[str, Any]]) -> list[dict[str, Any]]:
        fmt = FORMATS[spec.format_key]
        if route.kind == "replay_accepted":
            card = next(n for n in route.nodes if n.role == "supply")
            body = self.registry.resolve(card.bit_id) or {}
            return [{"text": body.get("text", self.registry.cards[card.bit_id].one_line),
                     "carried_acceptance": self.registry.cards[card.bit_id].acceptance_level,
                     "frame": body.get("frame", "")}]
        if route.kind == "replay_program":
            card = next(n for n in route.nodes if n.role == "supply")
            prog: JokeProgram = self.registry.resolve(card.bit_id)
            seed = int(next((n.binding.get("seed", 7) for n in route.nodes if n.binding), 7))
            return [{"text": run_program(prog, seed=seed),
                     "carried_acceptance": self.registry.cards[card.bit_id].acceptance_level,
                     "frame": prog.frame}]
        if not live:
            return []
        if route.kind == "remix_corpus":
            supply = next(n for n in route.nodes if n.role == "supply")
            rec = self.registry.resolve(supply.bit_id) or {}
            prompt = REMIX_PROMPT.format(
                source=rec.get("source", "unknown"), license=rec.get("license", "unknown"),
                text=rec.get("text", ""), format_label=fmt.label, structure=fmt.structure,
                budget=fmt.length_budget, directives=fmt.generation_directives,
                audience=spec.audience, preferences=spec.preferences or "none",
                n=min(2, spec.candidates))
            res = ollama_generate_with_usage(prompt, temperature=self.profile.temperature)
            usage_sink.append({k: res.get(k) for k in ("ok", "model", "prompt_sha256", "output_sha256",
                                                       "prompt_tokens", "output_tokens", "wall_s", "error")})
            if not res.get("ok"):
                return []
            texts = extract_candidates(res["response"], limit=min(2, spec.candidates))
            # the reused artifact carries its own frame — remixes inherit it
            # instead of asking the model to re-guess what it already knows
            meta = rec.get("meta") if isinstance(rec.get("meta"), dict) else {}
            source_frame = str(meta.get("humor_hook") or meta.get("frame") or "").strip()
            return [{"text": clean_candidate(t),
                     "frame_hint": source_frame,
                     "source_attribution": {"source": rec.get("source"),
                                            "license": rec.get("license"),
                                            "original": rec.get("text")}} for t in texts]
        if route.kind in ("compose_residual", "frontier_compose"):
            # the prompt must use EXACTLY the supply the route (and receipt)
            # names — a separately-ranked block bypassed the incompatibility
            # edges and broke contribution tracing (adversarial finding)
            if route.kind == "compose_residual":
                mechs = [self.registry.resolve(n.bit_id) for n in route.nodes
                         if n.role == "supply" and n.bit_id.startswith("mechanism:")]
                mech_block = "\n".join(
                    f"- {m.name}: {'; '.join(m.rewrite_moves[:2])}. Risk: {'; '.join(m.risk_notes[:1])}"
                    for m in mechs if m) or "(no mechanism constraint)"
            else:
                mech_block = "(frontier route: no mechanism constraint)"
            temp = self.profile.temperature if route.kind == "compose_residual" \
                else self.profile.frontier_temperature
            prompt = COMPOSE_PROMPT.format(
                n=min(spec.candidates, self.profile.max_model_candidates),
                format_label=fmt.label, topic=spec.topic, audience=spec.audience,
                preferences=spec.preferences or "none", structure=fmt.structure,
                budget=fmt.length_budget, directives=fmt.generation_directives,
                mechanisms=mech_block)
            res = ollama_generate_with_usage(prompt, temperature=temp)
            usage_sink.append({k: res.get(k) for k in ("ok", "model", "prompt_sha256", "output_sha256",
                                                       "prompt_tokens", "output_tokens", "wall_s", "error")})
            if not res.get("ok"):
                return []
            texts = extract_candidates(res["response"], limit=spec.candidates)
            return [{"text": clean_candidate(t)} for t in texts]
        return []

    def _verify(self, route: RouteIR, spec: WorkSpec, batch: list[dict[str, Any]],
                oracle: CountingProvider, *, live: bool) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for cand in batch:
            text = cand.get("text", "").strip()
            if not text:
                continue
            # per-candidate path-cache reset: the forced-NLL cache is keyed by
            # continuation text only, so a recurring candidate on a long-lived
            # provider would replay an unrelated context's token path
            clear = getattr(getattr(oracle, "inner", None), "clear_paths", None)
            if clear:
                clear()
            carried = cand.get("carried_acceptance", "")
            if carried and ACCEPTANCE_LEVELS.index(carried) >= ACCEPTANCE_LEVELS.index("instrument_scored"):
                # exact replay of already-verified material: acceptance carries
                # from the artifact's evidence (the Taedri replay value prop).
                # NOTHING was measured or persona-judged THIS run, and the
                # verdict must say so (adversarial finding 2026-07-24: a
                # carried measured=True flag fabricated current-run evidence).
                out.append({"text": text, "signals": {"measured": False, "laugh_score": None,
                                                      "failure_mode": "carried from prior evidence",
                                                      "carried": True},
                            "b_gate_evaluated": False, "b_gate_passed": False,
                            "accepted": True, "carried_acceptance": carried})
                continue
            if not live:
                out.append({"text": text, "signals": {"measured": False,
                                                      "failure_mode": "instrument unavailable (offline)"},
                            "b_gate_evaluated": False, "b_gate_passed": False, "accepted": False})
                continue
            setup, punch = split_setup_punchline(text)
            hint = cand.get("frame_hint") or None
            if hint and not trusted_frame_source(cand.get("source_attribution")):
                hint = None          # untrusted frame provenance: model must guess
            sig = compute_signals(oracle, setup, punch, frame_hint=hint,
                                  personas=list(spec.personas))
            prof = sig.profile
            # the B-gate only counts as EVALUATED when every persona judgment
            # was actually measured — a missing judge must never read as a
            # pass (2026-07-24 finding: collision defaults to 0.0 when the
            # judge model is unavailable, which passed the gate vacuously)
            b_judged = bool(spec.personas) and bool(sig.personas) and \
                all(pr.measured for pr in sig.personas)
            b_pass = b_judged and sig.bad_surprise <= self.policy.collision_ceiling
            cal = self._calibration(oracle)
            if cal:
                s_lo, s_hi = cal["s_band"]
                s_eff = sig.surprise_mean
                if s_eff > s_hi:
                    s_eff = max(s_lo, s_eff - sig.resolution)   # residual-surprise rule
                in_region = (s_lo <= s_eff <= s_hi
                             and sig.resolution >= cal["r_floor"]
                             and sig.efficiency >= cal["e_floor"])
                basis = f"calibrated({cal['ts']})"
            elif self.profile.require_certified:
                # the gate the charter promises: an uncertified instrument can
                # measure and diagnose but never mint acceptance (adversarial
                # finding — the fallback silently accepted on default bands)
                in_region = False
                basis = f"no certified calibration for {oracle.name} — acceptance gated"
            else:
                in_region = sig.failure_mode.startswith("laugh region")
                basis = "default failure_mode bands"
            measured_ok = sig.measured or not self.profile.require_measured
            out.append({
                "text": text,
                "acceptance_basis": basis,
                "signals": sig.to_dict() | {"censored": getattr(prof, "censored", 0)},
                "b_gate_evaluated": b_judged,
                "b_gate_passed": b_pass,
                "accepted": bool(in_region and b_pass and measured_ok),
                "carried_acceptance": "",
                "source_attribution": cand.get("source_attribution"),
            })
        return out

    def _preserve_accepted(self, spec: WorkSpec, route: RouteIR, verdict: dict[str, Any],
                           level: str) -> dict[str, Any]:
        text = verdict["text"]
        bit = {
            "bit_id": f"joke:{_sha(text)[:16]}",
            "name": text[:48],
            "text": text,
            "format_keys": [spec.format_key],
            "keywords": [w.lower() for w in re.findall(r"[a-zA-Z]{5,}", spec.topic)[:8]],
            "acceptance_level": level,
            "provenance": {
                "route_kind": route.kind,
                "supply_bits": [n.bit_id for n in route.nodes if n.role == "supply"],
                "audience": spec.audience,
                "source_attribution": verdict.get("source_attribution"),
                "created": _now(),
            },
            "evidence": {"signals": {k: verdict["signals"].get(k) for k in
                                     ("surprise_mean", "resolution", "efficiency", "bad_surprise",
                                      "laugh_score", "measured", "censored")}},
        }
        self.out_dir.mkdir(exist_ok=True)
        with (self.out_dir / "accepted_bits.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(bit, ensure_ascii=False) + "\n")
        return bit

    # -- reporting ---------------------------------------------------------
    def north_star_vector(self) -> dict[str, Any]:
        """Failure-inclusive cost to accepted outcomes — reported as a vector,
        never collapsed to one scalar (charter measurement rule)."""
        rows = self.receipts.read_all()
        if not rows:
            return {"runs": 0}
        acc = [r for r in rows if r.get("outcome", {}).get("accepted")]
        gen_tokens_in = gen_tokens_out = 0
        unknown_usage = 0
        for r in rows:
            for u in r.get("generation_usage", []):
                if u.get("prompt_tokens") is None:
                    unknown_usage += 1
                else:
                    gen_tokens_in += u.get("prompt_tokens") or 0
                    gen_tokens_out += u.get("output_tokens") or 0
        return {
            "runs": len(rows),
            "accepted_runs": len(acc),
            "abstained_runs": sum(1 for r in rows if r.get("outcome", {}).get("abstained")),
            "route_kinds": {k: sum(1 for r in rows if r.get("route", {}).get("kind") == k)
                            for k in {r.get("route", {}).get("kind") for r in rows}},
            "zero_model_call_accepts": sum(
                1 for r in acc
                if r.get("route", {}).get("kind", "").startswith("replay")
                and not r.get("generation_usage")),
            "escalations": sum(len(r.get("escalations", [])) for r in rows),
            "oracle_calls": {
                "nll": sum(r.get("oracle_usage", {}).get("nll_calls", 0) for r in rows),
                "judge": sum(r.get("oracle_usage", {}).get("judge_calls", 0) for r in rows),
                "generate": sum(r.get("oracle_usage", {}).get("generate_calls", 0) for r in rows),
            },
            "generation_tokens": {"prompt": gen_tokens_in, "output": gen_tokens_out,
                                  "calls_with_unknown_usage": unknown_usage},
            "measured_signal_runs": sum(
                1 for r in rows if r.get("truth_boundary", {}).get("teacher_forced_logprobs_measured")),
            "wall_s_total": round(sum(r.get("wall_s", 0.0) for r in rows), 2),
            "groaners_recorded": len(self.groaners.tail(10_000)),
        }

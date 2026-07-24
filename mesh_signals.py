"""Measured humor signals from a causal LM (see THEORY.md).

The theory says a joke is a controlled prediction error with a cheap, permitted
repair. This module measures those quantities instead of asking a model to rate
them:

- S  surprise    = token surprisal (nats) of the punchline given the setup
- R  resolution  = surprisal collapse when the hidden frame is made explicit
- E  efficiency  = resolution per token of frame hint (the ATP constraint)
- B  bad surprise = persona-conditioned meta-mesh collision (canonical definition)

Providers:
- TransformersProvider: true logprobs from a local/Kaggle Gemma checkpoint.
  Only selected when explicitly requested or when running inside Kaggle,
  because loading a 2B model is a deliberate act, not a default.
- OllamaProvider: generation + JSON judging via a Gemma served by Ollama;
  uses logprobs when the server exposes them.
- OfflineStub: deterministic heuristics so the UI/CLI stay demoable with no
  model. Every result it returns is flagged measured=False.
"""
from __future__ import annotations

import json
import math
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Protocol

from humor_mesh import CANONICAL_BAD_SURPRISE_DEFINITION, extract_json_object

# Surprise sweet band, in nats of mean punchline surprisal. Below the band the
# continuation was predictable; above it no frame is likely to absorb the error.
S_BAND_LOW = 1.2
S_BAND_HIGH = 5.5
S_BAND_PEAK = 3.0

WEIGHTS = {"surprise": 0.30, "resolution": 0.35, "efficiency": 0.15, "benign": 0.20}


@dataclass
class SurprisalProfile:
    tokens: list[str]
    nlls: list[float]
    measured: bool

    @property
    def mean(self) -> float:
        return sum(self.nlls) / len(self.nlls) if self.nlls else 0.0

    @property
    def peak(self) -> float:
        return max(self.nlls) if self.nlls else 0.0


@dataclass
class PersonaReport:
    persona: str
    collision: float  # 0-10 judged meta-mesh collision under the canonical definition
    colliding_model: str
    note: str
    surprise_shift: float  # persona-conditioned S minus baseline S
    measured: bool


@dataclass
class HumorSignals:
    setup: str
    punchline: str
    frame_hint: str
    surprise_mean: float
    surprise_peak: float
    resolution: float          # NET resolution: frame collapse minus decoy-hint collapse
    efficiency: float
    resolution_raw: float = 0.0
    resolution_null: float = 0.0  # decoy-hint collapse — conditioning on ANY text lowers NLL a bit
    personas: list[PersonaReport] = field(default_factory=list)
    measured: bool = True
    profile: SurprisalProfile | None = None

    @property
    def bad_surprise(self) -> float:
        if not self.personas:
            return 0.0
        return max(p.collision for p in self.personas)

    @property
    def surprise_score(self) -> float:
        """Inverted U on RESIDUAL surprise. Corpus-lab calibration (2026-07-04):
        puns measure S=7-9 with R up to 3.4 — far above the raw band — because a
        strong frame absorbs the error. Leftover error is confusion; resolved
        error is a pun. So above the band we judge S − R, not S."""
        s = self.surprise_mean
        if s >= S_BAND_HIGH:
            s = max(S_BAND_PEAK, s - self.resolution)  # let the frame absorb the excess
        if s <= S_BAND_LOW or s >= S_BAND_HIGH:
            return 0.0
        if s <= S_BAND_PEAK:
            return (s - S_BAND_LOW) / (S_BAND_PEAK - S_BAND_LOW)
        return (S_BAND_HIGH - s) / (S_BAND_HIGH - S_BAND_PEAK)

    @property
    def resolution_score(self) -> float:
        return 1.0 - math.exp(-max(0.0, self.resolution) / 1.5)

    @property
    def efficiency_score(self) -> float:
        return 1.0 - math.exp(-max(0.0, self.efficiency) / 0.15)

    @property
    def benign_score(self) -> float:
        return 1.0 - min(10.0, self.bad_surprise) / 10.0

    @property
    def laugh_score(self) -> float:
        return round(
            100.0
            * (
                WEIGHTS["surprise"] * self.surprise_score
                + WEIGHTS["resolution"] * self.resolution_score
                + WEIGHTS["efficiency"] * self.efficiency_score
                + WEIGHTS["benign"] * self.benign_score
            ),
            1,
        )

    @property
    def failure_mode(self) -> str:
        """Name which of the theory's four conditions failed hardest."""
        if self.bad_surprise >= 6.0:
            worst = max(self.personas, key=lambda p: p.collision)
            return (
                "bad-surprise: the frame collides with a high-authority internal model "
                f"for '{worst.persona}' ({worst.colliding_model or 'unspecified'})"
            )
        if self.surprise_mean <= S_BAND_LOW:
            return "predictable: the punchline is what the supervisor already expected"
        if self.surprise_mean >= S_BAND_HIGH and self.resolution < 0.5:
            return "nonsense: high prediction error with no reachable frame"
        if self.resolution < 0.5:
            return "no re-route: the frame does not actually explain the punchline"
        if self.efficiency < 0.03:
            return "too expensive: the frame exists but costs too much to reach (dissected frog)"
        return "laugh region: surprising, resolvable, affordable, permitted"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("profile", None)
        data.update(
            surprise_score=round(self.surprise_score, 3),
            resolution_score=round(self.resolution_score, 3),
            efficiency_score=round(self.efficiency_score, 3),
            benign_score=round(self.benign_score, 3),
            bad_surprise=round(self.bad_surprise, 2),
            laugh_score=self.laugh_score,
            failure_mode=self.failure_mode,
        )
        return data


class SignalProvider(Protocol):
    name: str

    def nll_tokens(self, context: str, continuation: str) -> SurprisalProfile: ...

    def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 220) -> str: ...

    def judge_json(self, prompt: str) -> dict[str, Any] | None: ...


# --------------------------------------------------------------------------
# Providers
# --------------------------------------------------------------------------
class TransformersProvider:
    """True logprobs from a Gemma checkpoint via transformers."""

    name = "transformers"

    def __init__(self, model_path: str | None = None) -> None:
        import torch  # noqa: F401  (lazy heavy imports on purpose)
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        path = model_path or os.environ.get("GEMMA_MODEL_PATH") or self._find_kaggle_gemma() or "google/gemma-2-2b-it"
        self.tokenizer = AutoTokenizer.from_pretrained(path)
        self.model = None
        if torch.cuda.is_available():
            try:
                model = AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.float16, device_map="auto")
                model.eval()
                with torch.no_grad():  # probe: some assignments lack kernels for this arch
                    model(torch.tensor([[self.tokenizer.bos_token_id or 2]]).to(model.device))
                self.model = model
            except Exception:
                self.model = None
                torch.cuda.empty_cache()
        if self.model is None:
            self.model = AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.float32)
            self.model.eval()

    @staticmethod
    def _find_kaggle_gemma() -> str | None:
        root = Path("/kaggle/input")
        if not root.exists():
            return None
        hits = sorted(root.glob("**/config.json"))
        for hit in hits:
            if "gemma" in str(hit).lower():
                return str(hit.parent)
        return None

    def nll_tokens(self, context: str, continuation: str) -> SurprisalProfile:
        torch = self.torch
        ctx_ids = self.tokenizer(context, return_tensors="pt").input_ids
        cont_ids = self.tokenizer(continuation, add_special_tokens=False, return_tensors="pt").input_ids
        full = torch.cat([ctx_ids, cont_ids], dim=1).to(self.model.device)
        with torch.no_grad():
            logits = self.model(full).logits
        logprobs = torch.log_softmax(logits.float(), dim=-1)
        n_ctx = ctx_ids.shape[1]
        nlls: list[float] = []
        toks: list[str] = []
        for i in range(cont_ids.shape[1]):
            pos = n_ctx + i
            tok_id = int(full[0, pos])
            nlls.append(float(-logprobs[0, pos - 1, tok_id]))
            toks.append(self.tokenizer.decode([tok_id]))
        return SurprisalProfile(tokens=toks, nlls=nlls, measured=True)

    def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 220) -> str:
        torch = self.torch
        chat = [{"role": "user", "content": prompt}]
        ids = self.tokenizer.apply_chat_template(chat, return_tensors="pt", add_generation_prompt=True)
        if not torch.is_tensor(ids):  # newer transformers return a BatchEncoding
            ids = ids["input_ids"]
        ids = ids.to(self.model.device)
        with torch.no_grad():
            out = self.model.generate(
                ids,
                max_new_tokens=max_tokens,
                do_sample=temperature > 0,
                temperature=max(temperature, 1e-3),
                top_p=0.95,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        return self.tokenizer.decode(out[0, ids.shape[1]:], skip_special_tokens=True).strip()

    def judge_json(self, prompt: str) -> dict[str, Any] | None:
        return extract_json_object(self.generate(prompt, temperature=0.2, max_tokens=300))


class OllamaProvider:
    """Gemma via a local/remote Ollama server; logprobs when supported."""

    name = "ollama"

    def __init__(self) -> None:
        self.model = os.environ.get("GEMMA_MODEL", "gemma3:4b")
        self.host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
        self.think = os.environ.get("GEMMA_THINK", "0").strip().lower() in {
            "1", "true", "yes", "on"
        }

    def _post(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

    def nll_tokens(self, context: str, continuation: str) -> SurprisalProfile:
        # Ollama does not expose teacher-forced continuation logprobs; fall back
        # to the stub's heuristic profile but keep generation/judging real.
        return OfflineStub().nll_tokens(context, continuation)

    def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 220) -> str:
        data = self._post(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                # Gemma 4 can spend ``num_predict`` on hidden reasoning and
                # truncate the requested visible candidates. Humor generation
                # is a constrained writing task, so thinking is opt-in.
                "think": self.think,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
        )
        return str((data or {}).get("response", "")).strip()

    def judge_json(self, prompt: str) -> dict[str, Any] | None:
        return extract_json_object(self.generate(prompt, temperature=0.2, max_tokens=320))


class OpenAICompatProvider:
    """Hosted Gemma (or other) via any OpenAI-compatible endpoint — NVIDIA NIM
    (free, hosts google/gemma-2-9b-it), Ollama Cloud (gemma3), Mistral, etc.
    Generation + judging only; teacher-forced logprobs are not exposed by these
    APIs, so measurement falls back to the stub and is flagged unmeasured."""

    name = "openai-compat"

    def __init__(self) -> None:
        self.base = os.environ.get("GEMMA_OPENAI_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
        self.model = os.environ.get("GEMMA_OPENAI_MODEL", "google/gemma-2-9b-it")
        self.key = ""
        for env in (os.environ.get("GEMMA_OPENAI_KEY_ENV", ""), "NVIDIA_API_KEY",
                    "OLLAMA_CLOUD_API_KEY", "ADVISOR_LLM_API_KEY", "MISTRAL_API_KEY", "OPENAI_API_KEY"):
            if env and os.environ.get(env):
                self.key = os.environ[env]
                break

    def nll_tokens(self, context: str, continuation: str) -> SurprisalProfile:
        return OfflineStub().nll_tokens(context, continuation)

    def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 220) -> str:
        req = urllib.request.Request(
            f"{self.base}/chat/completions",
            data=json.dumps({"model": self.model, "temperature": temperature, "max_tokens": max_tokens,
                             "messages": [{"role": "user", "content": prompt}]}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return str(data["choices"][0]["message"]["content"]).strip()
        except Exception:
            return ""

    def judge_json(self, prompt: str) -> dict[str, Any] | None:
        return extract_json_object(self.generate(prompt, temperature=0.2, max_tokens=350))


class PollinationsProvider:
    """Keyless hosted text generation (verified 2026-07-04: GET
    https://text.pollinations.ai/<prompt> answers with no auth). Rate-limited
    community service — treat as a bonus lane for judging/writing, never the
    core; measurement still falls back to the stub (no logprobs)."""

    name = "pollinations"

    def nll_tokens(self, context: str, continuation: str) -> SurprisalProfile:
        return OfflineStub().nll_tokens(context, continuation)

    def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 220) -> str:
        import urllib.parse

        url = "https://text.pollinations.ai/" + urllib.parse.quote(prompt[:1800])
        req = urllib.request.Request(url, headers={"User-Agent": "HumorVibes research"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8", "replace").strip()[: max_tokens * 6]
        except (urllib.error.URLError, TimeoutError):
            return ""

    def judge_json(self, prompt: str) -> dict[str, Any] | None:
        return extract_json_object(self.generate(prompt, temperature=0.2, max_tokens=350))


class OfflineStub:
    """Deterministic pseudo-signals; keeps demos alive with measured=False."""

    name = "offline"

    def nll_tokens(self, context: str, continuation: str) -> SurprisalProfile:
        ctx_words = {w.lower().strip(".,!?") for w in context.split()}
        toks, nlls = [], []
        for word in continuation.split():
            base = 1.0 + min(4.0, len(word) * 0.28)
            if word.lower().strip(".,!?") in ctx_words:
                base *= 0.35  # repeated words are predictable
            digest = sum(ord(c) for c in word) % 7
            toks.append(word)
            nlls.append(round(base + digest * 0.22, 3))
        return SurprisalProfile(tokens=toks, nlls=nlls, measured=False)

    def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 220) -> str:
        return ""

    def judge_json(self, prompt: str) -> dict[str, Any] | None:
        return None


def get_provider(kind: str | None = None) -> SignalProvider:
    kind = (kind or os.environ.get("GEMMA_PROVIDER", "")).strip().lower()
    if kind == "transformers" or (not kind and Path("/kaggle/input").exists()):
        try:
            return TransformersProvider()
        except Exception:
            return OfflineStub()
    if kind == "ollama":
        return OllamaProvider()
    if kind in ("openai", "openai-compat", "nvidia", "ollama-cloud", "mistral"):
        return OpenAICompatProvider()
    if kind == "pollinations":
        return PollinationsProvider()
    return OfflineStub()


# --------------------------------------------------------------------------
# Signal computation
# --------------------------------------------------------------------------
FRAME_PROMPT = (
    "A joke works because a hidden frame reinterprets the punchline. The frame is the fact that,"
    " once stated, makes the punchline the OBVIOUS next thing to say.\n\n"
    "Example 1 — Setup: I told my therapist about my fear of speed bumps.\n"
    "Punchline: She said I'm slowly getting over it.\n"
    "Frame: 'Getting over it' is literal — the car physically drives over the speed bumps slowly.\n\n"
    "Example 2 — Setup: My grandfather has the heart of a lion\n"
    "Punchline: and a lifetime ban from the zoo.\n"
    "Frame: He literally stole a lion's heart from the zoo, not the metaphor for bravery.\n\n"
    "Now — Setup: {setup}\n"
    "Punchline: {punchline}\n"
    "Frame (ONE short sentence, no preamble, no quotes; if there is no such fact, write NONE):"
)

PERSONA_JUDGE_PROMPT = (
    "You evaluate one specific failure mode of humor, defined canonically as:\n"
    f"\"{CANONICAL_BAD_SURPRISE_DEFINITION}\"\n\n"
    "Audience persona: {persona}\n"
    "Joke setup: {setup}\n"
    "Punchline: {punchline}\n"
    "Reframe the punchline relies on: {frame}\n\n"
    "Does that reframe collide with an internal model this audience uses with "
    "override authority (identity, moral core, worldview)? Mild discomfort or "
    "edginess is NOT a collision. Answer as JSON only: "
    '{{"collision": 0-10, "colliding_model": "name the internal model or empty", '
    '"note": "one sentence"}}'
)


def split_setup_punchline(text: str) -> tuple[str, str]:
    """Best-effort split of a one-block joke into setup/punchline."""
    text = text.strip()
    for sep in ["\n", ". ", "? ", "! ", " — ", " - ", ": ", "; "]:
        if sep in text:
            head, tail = text.rsplit(sep, 1)
            if len(tail.split()) >= 2:
                return head + sep.strip(), tail.strip()
    words = text.split()
    cut = max(1, int(len(words) * 0.7))
    return " ".join(words[:cut]), " ".join(words[cut:])


def compute_signals(
    provider: SignalProvider,
    setup: str,
    punchline: str,
    frame_hint: str | None = None,
    personas: list[str] | None = None,
) -> HumorSignals:
    setup = setup.strip()
    punchline = punchline.strip()
    base = provider.nll_tokens(setup + "\n", " " + punchline)

    hint = (frame_hint or "").strip()
    if not hint:
        hint = provider.generate(FRAME_PROMPT.format(setup=setup, punchline=punchline), temperature=0.3, max_tokens=60)
        hint = hint.splitlines()[0].strip() if hint else ""
    if hint:
        framed = provider.nll_tokens(setup + "\n(" + hint + ")\n", " " + punchline)
        resolution_raw = max(0.0, base.mean - framed.mean)
        # Leaky-frame guard (zoo-lab finding 2026-07-04): a "frame" that lexically
        # contains the punchline predicts its text without reframing anything —
        # confabulations can beat the generic decoy this way. Discount by content-
        # word overlap between hint and the punchline's NOVEL words only — words
        # the punchline shares with the setup are fair reuse, not a leak (refined
        # 2026-07-03: penalizing setup-word reuse was punishing legitimate frames).
        punch_words = {w.lower().strip(".,!?\"'") for w in punchline.split() if len(w) > 3}
        setup_words = {w.lower().strip(".,!?\"'") for w in setup.split() if len(w) > 3}
        novel_punch_words = punch_words - setup_words
        hint_words = {w.lower().strip(".,!?\"'") for w in hint.split() if len(w) > 3}
        leak = len(novel_punch_words & hint_words) / max(1, len(novel_punch_words))
        if leak > 0.4:
            resolution_raw *= max(0.0, 1.0 - leak)
        # Null control (house doctrine: every localized effect needs one).
        # Conditioning on ANY specific text lowers NLL slightly — and a model
        # asked to "find the frame" of nonsense will confabulate one. Subtract
        # the collapse produced by an equal-length decoy hint.
        decoy = "It turns out this is really about quarterly regional cheese sales figures."
        nulled = provider.nll_tokens(setup + "\n(" + decoy + ")\n", " " + punchline)
        resolution_null = max(0.0, base.mean - nulled.mean)
        resolution = max(0.0, resolution_raw - resolution_null)
        hint_tokens = max(1, len(hint.split()))
        efficiency = resolution / hint_tokens
    else:
        resolution_raw, resolution_null, resolution, efficiency = 0.0, 0.0, 0.0, 0.0

    reports: list[PersonaReport] = []
    for persona in personas or []:
        judged = provider.judge_json(
            PERSONA_JUDGE_PROMPT.format(persona=persona, setup=setup, punchline=punchline, frame=hint or "unknown")
        )
        persona_ctx = f"Audience: {persona}.\n{setup}\n"
        shifted = provider.nll_tokens(persona_ctx, " " + punchline)
        if judged is None:
            reports.append(
                PersonaReport(
                    persona=persona,
                    collision=0.0,
                    colliding_model="",
                    note="no judge available (offline)",
                    surprise_shift=round(shifted.mean - base.mean, 3),
                    measured=False,
                )
            )
        else:
            reports.append(
                PersonaReport(
                    persona=persona,
                    collision=float(max(0.0, min(10.0, float(judged.get("collision", 0))))),
                    colliding_model=str(judged.get("colliding_model", "")).strip(),
                    note=str(judged.get("note", "")).strip(),
                    surprise_shift=round(shifted.mean - base.mean, 3),
                    measured=base.measured,
                )
            )

    return HumorSignals(
        setup=setup,
        punchline=punchline,
        frame_hint=hint,
        surprise_mean=round(base.mean, 3),
        surprise_peak=round(base.peak, 3),
        resolution=round(resolution, 3),
        efficiency=round(efficiency, 4),
        resolution_raw=round(resolution_raw, 3),
        resolution_null=round(resolution_null, 3),
        personas=reports,
        measured=base.measured,
        profile=base,
    )


def sparkline(nlls: list[float]) -> str:
    """Tiny text sparkline of per-token surprisal for CLI/notebook output."""
    if not nlls:
        return ""
    blocks = "▁▂▃▄▅▆▇█"
    lo, hi = min(nlls), max(nlls)
    span = (hi - lo) or 1.0
    return "".join(blocks[int((v - lo) / span * (len(blocks) - 1))] for v in nlls)

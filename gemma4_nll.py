"""Gemma 4 forced-NLL provider: measured S/R/E through Ollama's logprobs API.

Closes the boundary recorded on 2026-07-11 ("Ollama still does not expose the
continuation logprobs needed for measured S/R/E"): the local Ollama server now
returns per-generated-token ``logprobs`` with ``top_logprobs`` (K <= 20). That
is not teacher forcing by itself — logprobs cover generated tokens only — so
this module reconstructs teacher-forced continuation NLL stepwise:

1. DISCOVER (base pass): with ``raw=True, temperature=0, num_predict=1``,
   repeatedly ask for the next-token distribution given context + the forced
   prefix so far. The true next token is the top-K candidate that is the
   longest prefix of the remaining continuation text (SentencePiece-style
   maximal munch). Whitespace-only matches are rejected — a lone-space token
   fragments the path into a non-canonical tokenization and poisons every
   later step — the step is censored to the next word boundary instead. A
   censored step's NLL is bounded below by -logprob(K-th candidate).
2. REPLAY (framed/null/persona passes): force the exact token path discovered
   in the base pass, looking each token up in the new context's top-K. The
   tokenization is identical across passes, so R = NLL(base) - NLL(framed)
   compares like with like. A replay step that cannot be read (outside top-K
   with no bound, or a server hiccup) is filled with the BASE pass value for
   that step — a censored step contributes ZERO to the resolution delta
   instead of a fake penalty.

Honesty contract:
- ``censored`` on the profile counts steps whose NLL is a bound or fill, and
  ``nll_is_lower_bound`` is set whenever the summed NLL under-counts;
- responses without logprobs/top_logprobs are transient server hiccups: they
  are retried, then degraded to censored steps, and counted in ``errors`` —
  never silently converted into offline-stub numbers mid-pass;
- generation and JSON judging delegate to the plain OllamaProvider (real
  Gemma 4 output, no logprob tricks).

The house null control and leaky-frame guard live in mesh_signals and operate
unchanged on top of this provider.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field, replace
from typing import Any

from humorvibes.config import Settings
from humorvibes.errors import IntegrationError
from humorvibes.http import JsonHttpClient
from humorvibes.signal_providers import OllamaSignalProvider
from mesh_signals import OfflineStub, SurprisalProfile

import re as _re

TOP_K = 20              # Ollama rejects top_logprobs > 20
MAX_STEPS = 96          # hard stop for runaway continuations
CHUNK_FALLBACK = 12     # censored-step advance: up to next space or this many chars

# mesh_signals frames a hint as `setup\n(hint)\n` (suffix layout). gemma4's
# strong copy-head parrots a suffix-placed hint — near-one-hot on the hint's
# own n-grams — instead of integrating it as knowledge (2026-07-23 receipt:
# framed ' the'=0.00 nats, everything else ~10). This provider therefore
# REWRITES that context shape to `(hint)\nsetup\n` before querying. The decoy
# null arrives through the same shape, so the control stays layout-matched.
# mesh_signals itself stays byte-identical (its hash is pinned by the
# harvested-ablation provenance tests).
_SUFFIX_FRAME_RE = _re.compile(r"\A(?P<setup>.*)\n\((?P<hint>.*)\)\n\Z", _re.DOTALL)


@dataclass
class ForcedStep:
    token: str
    nll: float
    censored: bool


@dataclass
class ForcedProfile:
    steps: list[ForcedStep] = field(default_factory=list)
    truncated: bool = False       # continuation exceeded MAX_STEPS

    @property
    def nlls(self) -> list[float]:
        return [s.nll for s in self.steps]

    @property
    def censored(self) -> int:
        return sum(1 for s in self.steps if s.censored)


def _word_chunk(remaining: str) -> str:
    cut = remaining.find(" ", 1)
    if cut <= 0:
        cut = min(len(remaining), CHUNK_FALLBACK)
    return remaining[:cut]


class Gemma4ForcedNLLProvider:
    """SignalProvider with real teacher-forced NLL via stepwise top-K readout."""

    name = "gemma4-forced-nll"

    def __init__(self, model: str | None = None, host: str | None = None,
                 auto_prefix_rewrite: bool = True) -> None:
        settings = Settings.from_env()
        self.model = model or os.environ.get("GEMMA_MODEL", "gemma4")
        self.host = (host or settings.ollama_host).rstrip("/")
        self.think = False
        self.auto_prefix_rewrite = auto_prefix_rewrite  # sweeps control layout themselves
        runtime = replace(settings, ollama_host=self.host)
        self._client = JsonHttpClient(
            runtime.ollama_host,
            api_key=runtime.ollama_api_key,
            timeout=180,
            max_response_bytes=runtime.max_response_bytes,
            allow_insecure_remote=runtime.allow_insecure_remote,
        )
        self._gen = OllamaSignalProvider(
            model=self.model,
            host=self.host,
            api_key=runtime.ollama_api_key,
        )
        self._path_cache: dict[str, list[str]] = {}       # continuation -> token path
        self._base_profiles: dict[str, ForcedProfile] = {}  # continuation -> base pass
        self.calls = 0
        self.errors = 0
        self.last_error: str | None = None

    # ---------------------------------------------------------------- raw API
    def _next_top(self, prompt: str, retries: int = 2) -> list[dict[str, Any]] | None:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "raw": True,
            "stream": False,
            "logprobs": True,
            "top_logprobs": TOP_K,
            "options": {"num_predict": 1, "temperature": 0},
        }
        for attempt in range(retries + 1):
            try:
                data = self._client.request("/api/generate", payload=payload)
            except IntegrationError as exc:
                self.last_error = f"{exc.code} (attempt {attempt + 1})"
                time.sleep(0.4 * (attempt + 1))
                continue
            lp = data.get("logprobs") or []
            tops = lp[0].get("top_logprobs") if lp else None
            if tops:
                self.calls += 1
                return tops
            # logprobs or top_logprobs missing: transient server hiccup — retry
            self.last_error = f"missing (top_)logprobs in response (attempt {attempt + 1})"
            time.sleep(0.4 * (attempt + 1))
        self.errors += 1
        return None

    # ------------------------------------------------------------- discovery
    def _discover(self, context: str, continuation: str) -> ForcedProfile | None:
        """Base pass: find the token path AND its NLLs under `context`.

        Single failed steps degrade to censored word-chunks; only consecutive
        failures abort the pass (server actually down)."""
        profile = ForcedProfile()
        prompt = context
        remaining = continuation
        consecutive_failures = 0
        for _ in range(MAX_STEPS):
            if not remaining:
                break
            top = self._next_top(prompt)
            if top is None:
                consecutive_failures += 1
                if consecutive_failures >= 3 or not profile.steps:
                    return None
                chunk = _word_chunk(remaining)
                profile.steps.append(ForcedStep(chunk, 20.0, True))
                prompt += chunk
                remaining = remaining[len(chunk):]
                continue
            consecutive_failures = 0
            matches = [c for c in top
                       if c.get("token") and remaining.startswith(c["token"])
                       and (c["token"].strip() or len(c["token"]) >= len(remaining))]
            if matches:
                best = max(matches, key=lambda c: len(c["token"]))  # maximal munch
                profile.steps.append(ForcedStep(best["token"], -float(best["logprob"]), False))
                prompt += best["token"]
                remaining = remaining[len(best["token"]):]
            else:
                # true token outside top-K (or only degenerate whitespace
                # matched): censored lower bound, advance one word chunk
                bound = -float(top[-1]["logprob"])
                chunk = _word_chunk(remaining)
                profile.steps.append(ForcedStep(chunk, bound, True))
                prompt += chunk
                remaining = remaining[len(chunk):]
        if remaining:
            profile.truncated = True   # MAX_STEPS hit: NLL covers a prefix only
        return profile

    def _replay(self, context: str, path: list[str],
                base: ForcedProfile | None) -> ForcedProfile | None:
        """Force a known token path under a different context. Unreadable steps
        are filled with the base pass value (zero contribution to any delta)."""
        profile = ForcedProfile()
        prompt = context
        consecutive_failures = 0
        for i, token in enumerate(path):
            base_nll = base.steps[i].nll if base and i < len(base.steps) else 20.0
            top = self._next_top(prompt)
            if top is None:
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    return None
                profile.steps.append(ForcedStep(token, base_nll, True))
                prompt += token
                continue
            consecutive_failures = 0
            hit = next((c for c in top if c.get("token") == token), None)
            if hit is not None:
                profile.steps.append(ForcedStep(token, -float(hit["logprob"]), False))
            else:
                # outside top-K in this context: the K-th logprob is the
                # tightest readable bound. This can overstate collapse on
                # base-censored steps — which is exactly the optimism the
                # decoy-null subtraction and the leak guard exist to soak
                # (the nonsense control still nets to 0.00 under them).
                bound = -float(top[-1]["logprob"])
                profile.steps.append(ForcedStep(token, bound, True))
            prompt += token
        return profile

    # ---------------------------------------------------- SignalProvider API
    def clear_paths(self) -> None:
        """Reset per-continuation caches; callers do this per candidate so a
        recurring text never replays an unrelated context's token path."""
        self._path_cache.clear()
        self._base_profiles.clear()

    def nll_tokens(self, context: str, continuation: str) -> SurprisalProfile:
        if self.auto_prefix_rewrite:
            m = _SUFFIX_FRAME_RE.match(context)
            # guard: only rewrite genuine hint layouts — a setup whose own
            # last line is a short parenthetical (e.g. "(beat)") must not be
            # reordered; real frame hints are full sentences
            if m and len(m.group("hint")) >= 25 and " " in m.group("hint"):
                context = "(" + m.group("hint") + ")\n" + m.group("setup") + "\n"
        key = continuation
        forced: ForcedProfile | None
        if key in self._path_cache:
            forced = self._replay(context, self._path_cache[key],
                                  self._base_profiles.get(key))
        else:
            forced = self._discover(context, continuation)
            if forced is not None and forced.steps:
                self._path_cache[key] = [s.token for s in forced.steps]
                self._base_profiles[key] = forced
        if forced is None or not forced.steps:
            stub = OfflineStub().nll_tokens(context, continuation)
            stub.measured = False
            return stub
        prof = SurprisalProfile(
            tokens=[s.token for s in forced.steps],
            nlls=[round(s.nll, 4) for s in forced.steps],
            measured=True,
        )
        # extra, protocol-compatible annotations for receipts
        prof.censored = forced.censored           # type: ignore[attr-defined]
        prof.truncated = forced.truncated         # type: ignore[attr-defined]
        prof.nll_is_lower_bound = forced.censored > 0 or forced.truncated  # type: ignore[attr-defined]
        return prof

    def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 220) -> str:
        return self._gen.generate(prompt, temperature=temperature, max_tokens=max_tokens)

    def judge_json(self, prompt: str) -> dict[str, Any] | None:
        return self._gen.judge_json(prompt)


def available(host: str | None = None, model: str | None = None) -> bool:
    """True when the Ollama server answers a 1-token logprob probe."""
    p = Gemma4ForcedNLLProvider(model=model, host=host)
    return p._next_top("ping") is not None


if __name__ == "__main__":
    from mesh_signals import compute_signals

    p = Gemma4ForcedNLLProvider()
    jokes = [
        ("I told my therapist about my fear of speed bumps.",
         "She said I'm slowly getting over it.",
         "'Getting over it' is literal — the car physically drives over the speed bumps slowly."),
        ("I told my therapist about my fear of speed bumps.",
         "The quarterly cheese fondue regatta sailed backwards.",
         ""),  # shuffled nonsense control: net R should die under the decoy null
    ]
    for setup, punch, frame in jokes:
        sig = compute_signals(p, setup, punch, frame_hint=frame or None)
        prof = sig.profile
        print(f"S={sig.surprise_mean:5.2f}  R_raw={sig.resolution_raw:5.2f}  "
              f"R_null={sig.resolution_null:5.2f}  R_net={sig.resolution:5.2f}  "
              f"E={sig.efficiency:6.3f}  measured={sig.measured} "
              f"censored={getattr(prof, 'censored', '?')}  :: {punch[:46]}")
    print(f"api_calls={p.calls} errors={p.errors}")

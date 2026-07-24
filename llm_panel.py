"""Multi-LLM audience panel for HumorVibes.

THEORY.md: different judge models are differently-tuned audience meshes. Gemma
remains the CORE engine (generation + measured signals); the panel adds
independent meshes — frontier LLMs and other local models — as a simulated
audience for convergence checks and portability matrices, extending
humor_datacenter.model_jury with real callers.

All remote judges are OFF unless their API keys are present in the
environment; without keys the panel lists itself in dry-run mode. Keys are
read from env only and never stored.

Judge sources (any subset; all OpenAI-compatible endpoints share one caller):
- Ollama Cloud:  OLLAMA_CLOUD_API_KEY (or ADVISOR_LLM_API_KEY) [+ PANEL_OLLAMA_CLOUD_MODELS]
                 base https://ollama.com/v1 — hosts gemma3, deepseek, kimi, glm…
- NVIDIA (free NIM endpoints): NVIDIA_API_KEY [+ PANEL_NVIDIA_MODELS]
                 base https://integrate.api.nvidia.com/v1 — hosts google/gemma-2-9b-it etc.
- Mistral:       MISTRAL_API_KEY [+ PANEL_MISTRAL_MODELS], base https://api.mistral.ai/v1
- Generic OpenAI-compatible (OpenAI, Groq, Together, DeepSeek, xAI, local vLLM):
                 OPENAI_API_KEY [+ OPENAI_BASE_URL, PANEL_OPENAI_MODELS]
- Anthropic frontier models: ANTHROPIC_API_KEY [+ PANEL_ANTHROPIC_MODELS]
- Ollama local models beyond Gemma: PANEL_OLLAMA_MODELS (e.g. "llama3.2:3b,qwen3:4b")
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Any

from humor_mesh import CANONICAL_BAD_SURPRISE_DEFINITION, extract_json_object

PANEL_DIMENSIONS = ("surprise", "resolution", "bad_surprise_risk", "audience_fit", "overall")

JUDGE_PROMPT = (
    "You are one audience mesh evaluating a piece of humor. Canonical bad-surprise definition:\n"
    f"\"{CANONICAL_BAD_SURPRISE_DEFINITION}\"\n\n"
    "Audience persona you embody: {persona}\n"
    "Format: {format_label}\nCONTENT:\n{content}\n\n"
    "Score honestly from YOUR persona's priors, not a universal standard. JSON only:\n"
    '{{"surprise": 0-10, "resolution": 0-10 (does a hidden frame snap it into place), '
    '"bad_surprise_risk": 0-10 (per the canonical definition), "audience_fit": 0-10, '
    '"overall": 0-10, "one_line_reaction": "what this audience says out loud"}}'
)


@dataclass(frozen=True)
class PanelJudge:
    judge_id: str
    provider: str  # openai-compat | anthropic | ollama
    model: str
    base_url: str = ""
    key_env: str = ""

    def describe(self) -> str:
        return f"{self.judge_id} ({self.provider}:{self.model})"


# name -> (key env vars in priority order, base url, default models, judge prefix)
OPENAI_COMPAT_ENDPOINTS: dict[str, tuple[tuple[str, ...], str, str, str]] = {
    # One endpoint, many vendors: Ollama Cloud serves gemma3/4, mistral-large/ministral,
    # NVIDIA nemotron-3, deepseek, kimi, glm, qwen, gpt-oss — a whole panel in one key.
    "ollama_cloud": (("OLLAMA_CLOUD_API_KEY", "OLLAMA_API_KEY", "ADVISOR_LLM_API_KEY"), "https://ollama.com/v1",
                     "gemma3:27b,ministral-3:14b,nemotron-3-super,deepseek-v4-flash,glm-5.2", "ocl"),
    "nvidia": (("NVIDIA_API_KEY",), "https://integrate.api.nvidia.com/v1",
               "google/gemma-2-9b-it,meta/llama-3.1-8b-instruct", "nim"),
    "mistral": (("MISTRAL_API_KEY",), "https://api.mistral.ai/v1",
                "mistral-small-latest", "mis"),
    # Gemini's OpenAI-compatible endpoint — the usual home of Kaggle-granted LLM credits.
    "gemini": (("GEMINI_API_KEY", "GOOGLE_API_KEY"), "https://generativelanguage.googleapis.com/v1beta/openai",
               "gemini-2.5-flash", "gem"),
    # OpenRouter :free tier (verified 2026-07-04: 23 free models incl. gemma-4-31b-it:free,
    # nemotron-3-super/ultra:free, gpt-oss-120b:free, llama-3.3-70b:free). Free signup key.
    "openrouter": (("OPENROUTER_API_KEY",), "https://openrouter.ai/api/v1",
                   "google/gemma-4-31b-it:free,nvidia/nemotron-3-super-120b-a12b:free,meta-llama/llama-3.3-70b-instruct:free",
                   "orf"),
    "openai": (("OPENAI_API_KEY",), "", "gpt-4o-mini", "oai"),
}


@dataclass
class PanelVote:
    judge_id: str
    persona: str
    scores: dict[str, float]
    reaction: str
    ok: bool
    error: str = ""


LAST_HTTP_ERROR: dict[str, str] = {}  # url -> last error body/status, for self-diagnosis


def _http_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int = 120) -> dict[str, Any] | None:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json", **headers}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            LAST_HTTP_ERROR.pop(url, None)
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            body = ""
        LAST_HTTP_ERROR[url] = f"HTTP {e.code}: {body}"
        return None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        LAST_HTTP_ERROR[url] = f"{type(e).__name__}: {str(e)[:200]}"
        return None


def _call_openai_compatible(model: str, prompt: str, base_url: str = "", key_env: str = "") -> str:
    base = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
    key = os.environ.get(key_env or "OPENAI_API_KEY", "")
    data = _http_json(
        f"{base}/chat/completions",
        {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3},
        {"Authorization": f"Bearer {key}"},
    )
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return ""


def _call_anthropic(model: str, prompt: str) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    data = _http_json(
        "https://api.anthropic.com/v1/messages",
        {"model": model, "max_tokens": 400, "messages": [{"role": "user", "content": prompt}]},
        {"x-api-key": key, "anthropic-version": "2023-06-01"},
    )
    try:
        return "".join(block.get("text", "") for block in data.get("content", []))
    except (AttributeError, TypeError):
        return ""


def _call_ollama(model: str, prompt: str) -> str:
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    data = _http_json(
        f"{host}/api/generate",
        {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.3}},
        {},
        timeout=180,
    )
    return str((data or {}).get("response", ""))


def available_judges() -> list[PanelJudge]:
    judges: list[PanelJudge] = []
    for name, (key_envs, base, default_models, prefix) in OPENAI_COMPAT_ENDPOINTS.items():
        key_env = next((k for k in key_envs if os.environ.get(k)), None)
        if not key_env:
            continue
        models = os.environ.get(f"PANEL_{name.upper()}_MODELS", default_models).split(",")
        judges += [
            PanelJudge(f"{prefix}-{m.strip().split('/')[-1]}", "openai-compat", m.strip(), base, key_env)
            for m in models
            if m.strip()
        ]
    if os.environ.get("ANTHROPIC_API_KEY"):
        models = os.environ.get("PANEL_ANTHROPIC_MODELS", "claude-haiku-4-5-20251001").split(",")
        judges += [PanelJudge(f"ant-{m.strip()}", "anthropic", m.strip()) for m in models if m.strip()]
    for m in os.environ.get("PANEL_OLLAMA_MODELS", "").split(","):
        if m.strip():
            judges.append(PanelJudge(f"oll-{m.strip()}", "ollama", m.strip()))
    # Keyless hosted lane (opt-in because it makes network calls with no key to
    # gate on): PANEL_POLLINATIONS=1 adds the community Pollinations endpoint.
    if os.environ.get("PANEL_POLLINATIONS") == "1":
        judges.append(PanelJudge("pol-default", "pollinations", "default"))
    return judges


def _dispatch(judge: PanelJudge, prompt: str) -> str:
    if judge.provider == "openai-compat":
        return _call_openai_compatible(judge.model, prompt, judge.base_url, judge.key_env)
    if judge.provider == "anthropic":
        return _call_anthropic(judge.model, prompt)
    if judge.provider == "pollinations":
        from mesh_signals import PollinationsProvider

        return PollinationsProvider().generate(prompt, temperature=0.3, max_tokens=350)
    return _call_ollama(judge.model, prompt)


def run_panel(
    content: str,
    personas: list[str],
    format_label: str = "joke",
    judges: list[PanelJudge] | None = None,
) -> list[PanelVote]:
    votes: list[PanelVote] = []
    for judge in judges if judges is not None else available_judges():
        for persona in personas or ["general audience"]:
            raw = _dispatch(judge, JUDGE_PROMPT.format(persona=persona, format_label=format_label, content=content))
            parsed = extract_json_object(raw or "")
            if not parsed:
                detail = next(iter(LAST_HTTP_ERROR.values()), "") if not raw else f"unparseable: {raw[:120]}"
                votes.append(PanelVote(judge.judge_id, persona, {}, "", ok=False,
                                       error=detail or "no/invalid response"))
                continue
            scores = {
                dim: max(0.0, min(10.0, float(parsed.get(dim, 0))))
                for dim in PANEL_DIMENSIONS
                if isinstance(parsed.get(dim, None), (int, float, str)) and str(parsed.get(dim)).strip() != ""
            }
            votes.append(
                PanelVote(judge.judge_id, persona, scores, str(parsed.get("one_line_reaction", "")).strip(), ok=True)
            )
    return votes


def convergence_report(votes: list[PanelVote]) -> dict[str, Any]:
    """Where do independent meshes agree? Disagreement is signal, not noise:
    high spread on bad_surprise_risk usually means the joke is insider material."""
    good = [v for v in votes if v.ok]
    report: dict[str, Any] = {"votes": len(votes), "usable": len(good), "dimensions": {}}
    for dim in PANEL_DIMENSIONS:
        vals = [v.scores[dim] for v in good if dim in v.scores]
        if vals:
            report["dimensions"][dim] = {
                "mean": round(mean(vals), 2),
                "spread": round(pstdev(vals), 2) if len(vals) > 1 else 0.0,
                "n": len(vals),
            }
    by_persona: dict[str, list[float]] = {}
    for v in good:
        if "overall" in v.scores:
            by_persona.setdefault(v.persona, []).append(v.scores["overall"])
    report["portability"] = {
        persona: round(mean(vals), 2) for persona, vals in sorted(by_persona.items())
    }
    if report["portability"]:
        vals = list(report["portability"].values())
        report["portability_spread"] = round(max(vals) - min(vals), 2)
        report["verdict"] = (
            "portable across meshes" if report["portability_spread"] <= 2.0 else "insider material: works for specific meshes"
        )
    return report

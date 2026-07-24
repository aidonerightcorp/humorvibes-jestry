# Free model & compute map (verified 2026-07-04)

What can run where, for free, and what each slot is good for in our pipelines.
Two distinct roles (THEORY.md): the **instrument** needs teacher-forced logprobs and hidden
states → must run as local weights (Kaggle transformers). **Judges/writers/compilers** only need
chat completions → any hosted endpoint works.

## 1. Kaggle notebooks — local weights (the instrument lives here)

Hardware reality (measured this week): **T4 works** with the current torch image; **P100
(sm_60) is broken** ("no kernel image") → every kernel we ship carries a CUDA-probe → CPU
fallback (4 cores / 30GB, fine for measurement, slow for generation). GPU batch cap: 2 sessions.

Kaggle Models hub (verified via API; attach via `model_sources`, no HF token needed):

| Family | Hub handles | Fits where | Notes |
|---|---|---|---|
| Gemma | `google/gemma`, `gemma-2`, `gemma-3`, `gemma-4` (+ keras/*) | gemma-2-2b ✓T4/CPU (our instrument, `/transformers/gemma-2-2b-it/2`); gemma-3-1b/4b ✓T4; gemma-2-9b/gemma-3-12b need 2×T4 or quant; gemma-4-31b hosted-only | comp-branded; instrument + local writer |
| Llama | `metaresearch/llama-3.2` (1b/3b ✓T4), `llama-3.1`, `llama-3.2-vision` | 1b/3b easy | extra local judges for diversity |
| Qwen | `qwen-lm/qwen-3`, `qwen-3-5`, `qwen2.5(-coder)`, `qwq-32b` | 0.5-7b ✓T4 | strong small writers |
| Mistral | `mistral-ai/ministral-3`, `mistral-small-24b`, `devstral`, `magistral` | ministral-3 3b ✓T4 | Mistral-family local |
| DeepSeek | `deepseek-ai/deepseek-r1(-0528)`, distills | distill-qwen-1.5b/7b ✓T4 | reasoning judges |
| Phi | `Microsoft/phi-3`, phi-3.5-mini | ✓T4/CPU | compact judge |
| Wearables (HASCA) | search `ssl-wearables`/`harnet` or upload weights as a dataset | ✓T4/CPU | UK-Biobank pretrained accel encoder |

**Kaggle built-in LLM credits**: notebook Add-ons → **Gemini** → `UserSecretsClient().get_gemini_api_key()`
(panel-lab kernel already wired). Platform pays; no external key.

## 2. Free hosted APIs (judges/writers/compilers — all OpenAI-compatible, all in `llm_panel.py`)

| Endpoint | Key path | Verified models | Quota shape |
|---|---|---|---|
| **Ollama Cloud** `ollama.com/v1` | key in vault (`OLLAMA_API_KEY`) | **34 models verified**: gemma3:4b→27b, gemma4:31b, mistral-large-3:675b, ministral-3, nemotron-3 nano/super/ultra, deepseek-v3.1/v4, kimi-k2.x, glm-5.x, qwen3.5:397b, gpt-oss-120b | weekly cap (currently EXHAUSTED by the other project's loops; resets weekly or add usage) |
| **OpenRouter :free** `openrouter.ai/api/v1` | free signup → `OPENROUTER_API_KEY` | **23 free models verified**: `google/gemma-4-31b-it:free`, `gemma-4-26b-a4b:free`, `nvidia/nemotron-3-ultra-550b:free` (1M ctx!), `nemotron-3-super-120b:free`, `gpt-oss-120b/20b:free`, `llama-3.3-70b:free`, `qwen3-next-80b:free`, `hermes-3-405b:free` | per-day request caps on :free |
| **NVIDIA build.nvidia.com** `integrate.api.nvidia.com/v1` | free signup → `NVIDIA_API_KEY` | NIM catalog incl. `google/gemma-2-9b-it`, llama, mistral, nemotron | generous free credits |
| **Gemini** (Kaggle credits) `generativelanguage.googleapis.com/v1beta/openai` | aistudio.google.com or Kaggle add-on | gemini-2.5-flash/-lite | free tier + Kaggle grants |
| **Mistral** `api.mistral.ai/v1` | console.mistral.ai free tier | mistral-small-latest etc. | rate-limited free tier |
| Also worth keys (not yet wired/verified): Groq (fast llama/gemma), Cerebras, GitHub Models (gpt-4o-mini free w/ GitHub account), HF Inference free tier | | | |

## 3. Which slot for which job (our pipelines)

- **Instrument (S/R/E, vibe axes, openness)**: local gemma-2-2b on Kaggle — logprobs + hidden
  states are not exposed by any free hosted API. This is why the instrument stays local, always.
- **Frame-writers / compile-time template authors**: biggest available chat model — priority:
  Ollama Cloud gemma4:31b / OpenRouter `gemma-4-31b-it:free` (keeps the Gemma story) →
  nemotron-3-super:free → gpt-oss-120b:free. (Every "2B is the bottleneck" finding converts here.)
- **Persona-panel judges (diversity)**: one per family — gemma-4 (free), nemotron-3 (free),
  llama-3.3-70b (free), ministral/mistral-small, deepseek/glm/kimi via Ollama Cloud, gemini-flash.
- **De-escalation & remix generation**: same as frame-writers; benign gates re-measured locally.
- **HASCA**: ssl-wearables weights → Kaggle dataset → transfer kernel (T4-probe + CPU fallback).

## 4. Immediate unlocks, cheapest first

1. **OpenRouter free key** (2-min signup) → gemma-4-31b + nemotron + llama-70b judges/writers
   at $0 — single highest-value key right now (Ollama Cloud is quota-dead until reset).
2. Kaggle **Gemini add-on click** on `humorvibes-panel-lab` → platform-credit panel + frame duel.
3. NVIDIA + Mistral free keys → two more independent vendors for convergence studies.

## 5. Truly keyless hosted lane (verified 2026-07-04)

- **Pollinations** — `GET https://text.pollinations.ai/<prompt>` answered with NO auth (HTTP 200,
  exact-instruction compliance). Community-run, rate-limited, limited model control → wired as a
  bonus lane only: `GEMMA_PROVIDER=pollinations` (generation/judging) and `PANEL_POLLINATIONS=1`
  (adds a keyless hosted judge to the panel). Never the core engine; measurement stays local.
- Other "no-key" routes exist (public Gradio/HF Spaces endpoints) but are fragile and
  ToS-ambiguous — not wired.

## 6. Embeddings, audio, vision — free stacks (verified handles)

**Key fact**: *ungated* HF models download keylessly inside internet-ON Kaggle kernels — only
gated families (Gemma, Llama official) need Kaggle `model_sources` attachment.

| Need | Free options (verified on Kaggle hub / ungated HF) | Used for |
|---|---|---|
| Text embeddings | `qwen-lm/qwen-3-embedding` (official), MiniLM-L6-v2, `bge-small-en-v1.5`, `bge-m3` (hub uploads; all ungated on HF too; sentence-transformers preinstalled on Kaggle) | Upgrade vibe axes from Gemma hidden states to purpose-built embedders; semantic dedup for ingested corpora; nearest-example retrieval in the datacenter |
| Speech→text | `keras/whisper` + whisper variants (hub), whisper-tiny/base ungated on HF | Ingest the user's OWN audio/video into transcripts → callback mining (`ingest.py parse_transcript` consumes the output) |
| Image↔text | `laionai/clip-vit`, `keras/clip` (hub; open_clip ungated on HF) | Match ingested Imgflip meme templates to joke frames; score caption↔image fit |
| Audio events | YAMNet/AST-class audio taggers (TF-Hub/HF ungated) | Replace the live-set laughter heuristic with a real laughter detector (LaughterReport interface already provider-agnostic) |

Priority integrations: (a) MiniLM/bge vibe-axis backend (cheaper + cleaner than LM hidden states,
runs anywhere incl. CPU studio), (b) Whisper ingestion path for user recordings, (c) CLIP meme
matcher for the Imgflip corpus.

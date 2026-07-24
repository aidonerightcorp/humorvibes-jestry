#!/usr/bin/env python3
"""Generate the Corpus Lab notebook: scan public jokes, measure, rank, remix.

Pipeline (internet-ON kernel, no API keys):
  1. FETCH  ~40 jokes from free, no-auth APIs (icanhazdadjoke, JokeAPI) with
     polite headers. Text only; licensing-safe (the APIs exist to serve jokes).
  2. MEASURE every item with the local Gemma instrument: S, frame (few-shot,
     NONE-honest), R net of decoy null, E — the corpus mapped onto the laugh
     region.
  3. RANK and diagnose: best/worst items, failure-mode census of the internet's
     humor (how much of it is predictable vs unresolvable?).
  4. REMIX: take the top-measured frames, recompile them into other formats
     (one-liner -> meme caption / shorts beat), and MEASURE the remixes — does
     the frame survive format transfer? (THEORY.md: formats are timing
     envelopes; the frame is the invariant.)
Outputs: /kaggle/working/research_out/corpus_report.json
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_c = {"n": 0}


def _cid() -> str:
    _c["n"] += 1
    return f"cell-{_c['n']:02d}"


def md(src: str) -> dict:
    return {"cell_type": "markdown", "id": _cid(), "metadata": {}, "source": src}


def code(src: str) -> dict:
    return {"cell_type": "code", "id": _cid(), "metadata": {}, "execution_count": None, "outputs": [], "source": src}


CELLS = [
    md(
        "# HumorVibes — Corpus Lab: scan, measure, remix the internet's jokes\n\n"
        "Fetch jokes from free public APIs, measure each with the local Gemma instrument "
        "(S surprise / R resolution net of a decoy-null / E efficiency, frame guessed few-shot with "
        "an honest NONE), map the whole corpus onto the laugh region, then **remix the best frames "
        "into other formats** and measure whether the frame survives the transfer.\n\n"
        "*(Licensing note: text jokes from APIs built to serve jokes; no performer clips are scraped — "
        "clip work belongs to licensed corpora or original material rendered via ClipPlan.)*"
    ),
    code(
        "import glob, json, os, re, time, urllib.request, torch\n"
        "from transformers import AutoModelForCausalLM, AutoTokenizer\n"
        "os.makedirs('/kaggle/working/research_out', exist_ok=True)\n"
        "UA = {'User-Agent': 'HumorVibes research notebook (Kaggle; Humor Genome NYC hackathon)'}\n\n"
        "def fetch_json(url, headers=None, timeout=20):\n"
        "    req = urllib.request.Request(url, headers={**UA, **(headers or {})})\n"
        "    with urllib.request.urlopen(req, timeout=timeout) as r:\n"
        "        return json.loads(r.read().decode('utf-8'))\n\n"
        "corpus = []\n"
        "try:\n"
        "    for _ in range(15):\n"
        "        d = fetch_json('https://icanhazdadjoke.com/', headers={'Accept': 'application/json'})\n"
        "        if d.get('joke'): corpus.append({'src': 'icanhazdadjoke', 'text': d['joke']})\n"
        "        time.sleep(0.6)\n"
        "except Exception as e:\n"
        "    print('dadjoke fetch stopped:', e)\n"
        "try:\n"
        "    d = fetch_json('https://v2.jokeapi.dev/joke/Any?safe-mode&type=twopart&amount=10')\n"
        "    for j in d.get('jokes', []):\n"
        "        corpus.append({'src': 'jokeapi', 'text': j['setup'] + ' ' + j['delivery']})\n"
        "    d = fetch_json('https://v2.jokeapi.dev/joke/Any?safe-mode&type=single&amount=10')\n"
        "    for j in d.get('jokes', []):\n"
        "        corpus.append({'src': 'jokeapi', 'text': j['joke']})\n"
        "except Exception as e:\n"
        "    print('jokeapi fetch stopped:', e)\n"
        "seen, deduped = set(), []\n"
        "for item in corpus:\n"
        "    key = item['text'][:60].lower()\n"
        "    if key not in seen:\n"
        "        seen.add(key); deduped.append(item)\n"
        "corpus = deduped\n"
        "print(f'corpus: {len(corpus)} unique jokes')\n"
        "for c in corpus[:5]: print(' -', c['text'][:80])"
    ),
    code(
        "gcfg = [p for p in glob.glob('/kaggle/input/**/config.json', recursive=True) if 'gemma' in p.lower()]\n"
        "MODEL_PATH = os.path.dirname(gcfg[0])\n"
        "tok = AutoTokenizer.from_pretrained(MODEL_PATH)\n"
        "def load_fb(path):\n"
        "    if torch.cuda.is_available():\n"
        "        try:\n"
        "            m = AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.float16, device_map='auto').eval()\n"
        "            with torch.no_grad(): m(torch.tensor([[tok.bos_token_id or 2]]).to(m.device))\n"
        "            return m\n"
        "        except Exception as e:\n"
        "            print('cuda->cpu:', str(e)[:90]); torch.cuda.empty_cache()\n"
        "    return AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.float32).eval()\n"
        "model = load_fb(MODEL_PATH)\n"
        "print('instrument:', model.device)\n\n"
        "def nll_mean(context, continuation):\n"
        "    ctx = tok(context, return_tensors='pt').input_ids\n"
        "    cont = tok(continuation, add_special_tokens=False, return_tensors='pt').input_ids\n"
        "    full = torch.cat([ctx, cont], dim=1).to(model.device)\n"
        "    with torch.no_grad():\n"
        "        lp = torch.log_softmax(model(full).logits.float(), dim=-1)\n"
        "    n = ctx.shape[1]\n"
        "    vals = [float(-lp[0, n+i-1, int(full[0, n+i])]) for i in range(cont.shape[1])]\n"
        "    return sum(vals) / len(vals)\n\n"
        "def gen(prompt, max_new=70, temperature=0.4):\n"
        "    ids = tok.apply_chat_template([{'role':'user','content':prompt}], return_tensors='pt', add_generation_prompt=True)\n"
        "    if not torch.is_tensor(ids): ids = ids['input_ids']\n"
        "    ids = ids.to(model.device)\n"
        "    with torch.no_grad():\n"
        "        out = model.generate(ids, max_new_tokens=max_new, do_sample=True, temperature=temperature,\n"
        "                             top_p=0.95, pad_token_id=tok.eos_token_id)\n"
        "    return tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True).strip()\n\n"
        "FEWSHOT = (\"A joke works because a hidden frame reinterprets the punchline - the fact that, once stated, \"\n"
        "           \"makes the punchline the OBVIOUS next thing to say.\\n\"\n"
        "           \"Example - Setup: I told my therapist about my fear of speed bumps. \"\n"
        "           \"Punchline: She said I'm slowly getting over it. \"\n"
        "           \"Frame: 'Getting over it' is literal - the car physically drives over the bumps slowly.\\n\")\n"
        "DECOY = 'It turns out this is really about quarterly regional cheese sales figures.'\n"
        "S_LO, S_HI = 1.2, 5.5\n\n"
        "def split_sp(text):\n"
        "    for sep in ['\\n', '. ', '? ', '! ', ' - ', ': ']:\n"
        "        if sep in text:\n"
        "            a, b = text.rsplit(sep, 1)\n"
        "            if len(b.split()) >= 2: return a + sep.strip(), b.strip()\n"
        "    w = text.split(); c = max(1, int(len(w)*0.7))\n"
        "    return ' '.join(w[:c]), ' '.join(w[c:])\n\n"
        "def measure(text):\n"
        "    setup, punch = split_sp(text)\n"
        "    S = nll_mean(setup + '\\n', ' ' + punch)\n"
        "    frame = gen(FEWSHOT + 'Now - Joke: ' + text + '\\nFrame (ONE short sentence, no preamble; if none, NONE):',\n"
        "                max_new=50, temperature=0.3).splitlines()[0].strip()\n"
        "    if not frame or frame.upper().startswith('NONE'):\n"
        "        return dict(S=round(S,3), R=0.0, E=0.0, frame='NONE', setup=setup, punch=punch)\n"
        "    r_raw = max(0.0, S - nll_mean(setup + '\\n(' + frame + ')\\n', ' ' + punch))\n"
        "    r_null = max(0.0, S - nll_mean(setup + '\\n(' + DECOY + ')\\n', ' ' + punch))\n"
        "    R = max(0.0, r_raw - r_null)\n"
        "    return dict(S=round(S,3), R=round(R,3), E=round(R/max(1,len(frame.split())),4),\n"
        "                frame=frame[:100], setup=setup, punch=punch)"
    ),
    md("## Measure the corpus: where does the internet's humor sit in the laugh region?"),
    code(
        "MAXN = 30 if model.device.type == 'cpu' else 60\n"
        "measured = []\n"
        "t0 = time.time()\n"
        "for i, item in enumerate(corpus[:MAXN]):\n"
        "    try:\n"
        "        m = measure(item['text'])\n"
        "    except Exception as e:\n"
        "        print('skip', i, str(e)[:60]); continue\n"
        "    m['src'] = item['src']; m['text'] = item['text']\n"
        "    measured.append(m)\n"
        "    if (i+1) % 5 == 0: print(f'{i+1}/{min(len(corpus), MAXN)} measured ({time.time()-t0:.0f}s)')\n"
        "in_band = [m for m in measured if S_LO < m['S'] < S_HI and m['R'] >= 0.3]\n"
        "predictable = [m for m in measured if m['S'] <= S_LO]\n"
        "no_frame = [m for m in measured if m['frame'] == 'NONE' or m['R'] < 0.05]\n"
        "print(f'\\ncensus: {len(measured)} measured | laugh-region {len(in_band)} | '\n"
        "      f'predictable {len(predictable)} | weak/no frame {len(no_frame)}')\n"
        "ranked = sorted(measured, key=lambda m: -(m['R'] + 0.2*min(m['S'], S_HI)))\n"
        "print('\\nTOP 5 (measured):')\n"
        "for m in ranked[:5]: print(f\"  S={m['S']:5.2f} R={m['R']:5.2f} :: {m['text'][:70]}\")\n"
        "print('\\nBOTTOM 3:')\n"
        "for m in ranked[-3:]: print(f\"  S={m['S']:5.2f} R={m['R']:5.2f} :: {m['text'][:70]}\")"
    ),
    code(
        "import matplotlib.pyplot as plt\n"
        "fig, ax = plt.subplots(figsize=(8, 5))\n"
        "ax.axvspan(S_LO, S_HI, alpha=0.08, color='green')\n"
        "for m in measured:\n"
        "    ax.scatter(m['S'], m['R'], s=60, alpha=0.7,\n"
        "               c='#2a9d3a' if (S_LO < m['S'] < S_HI and m['R'] >= 0.3) else '#5b8dad')\n"
        "ax.set_xlabel('S - surprise (nats)'); ax.set_ylabel('R - resolution (net of null)')\n"
        "ax.set_title(f'The internet corpus on the laugh region (n={len(measured)})\\n"
        "green = measured laugh-region items')\n"
        "plt.tight_layout(); plt.show()"
    ),
    md(
        "## Temporal: does the joke rent a hot cache or the population's deep cache?\n"
        "THEORY.md §11: state the fact as an explicit frame hint (R_with) vs strip it and see how much the model's OWN cache already explains the punchline (R_without = NLL('Someone says:', punchline) minus NLL(setup, punchline)). Small gap -> the population cache already carries the joke (canonical, evergreen). Large gap -> the joke only resolves once the fact is stated - it rents a hot, shallow cache (topical) that evicts as the news cycle moves on."
    ),
    code(
        "FEED = 'https://feeds.bbci.co.uk/news/technology/rss.xml'\n"
        "headlines = []\n"
        "try:\n"
        "    req = urllib.request.Request(FEED, headers=UA)\n"
        "    with urllib.request.urlopen(req, timeout=20) as r:\n"
        "        xml = r.read().decode('utf-8', 'replace')\n"
        "    titles = re.findall(r'<item>.*?<title>(?:<!\\[CDATA\\[)?(.*?)(?:\\]\\]>)?</title>', xml, flags=re.DOTALL)\n"
        "    headlines = [' '.join(t.split()) for t in titles if len(' '.join(t.split())) >= 15][:8]\n"
        "except Exception as e:\n"
        "    print('rss fetch stopped:', e)\n"
        "print(f'fetched {len(headlines)} headlines')\n"
        "\n"
        "FACTS = [\n"
        "    ('Icarus', 'Icarus flew too close to the sun on wings of wax and feathers, and they melted.'),\n"
        "    ('Trojan horse', 'The Greeks hid soldiers inside a giant wooden horse to sneak into Troy.'),\n"
        "    (\"Newton's apple\", 'An apple falling from a tree helped Isaac Newton work out that gravity pulls things down.'),\n"
        "    ('Eureka', 'Archimedes shouted Eureka and ran from his bath naked after realizing displaced water reveals volume.'),\n"
        "]\n"
        "\n"
        "JOKE_ASK = ('Write ONE short one-liner joke (a setup then a punchline, no more than two sentences) '\n"
        "            'that only lands if you know this fact: {fact}\\nReturn only the joke, no preamble, no quotes.')\n"
        "\n"
        "def temporal_gap(fact, one_liner):\n"
        "    setup, punch = split_sp(one_liner)\n"
        "    S = nll_mean(setup + '\\n', ' ' + punch)\n"
        "    r_raw = max(0.0, S - nll_mean(setup + '\\n(' + fact + ')\\n', ' ' + punch))\n"
        "    r_null = max(0.0, S - nll_mean(setup + '\\n(' + DECOY + ')\\n', ' ' + punch))\n"
        "    R_with = max(0.0, r_raw - r_null)\n"
        "    bare = nll_mean('Someone says:\\n', ' ' + punch)\n"
        "    R_without = max(0.0, round(bare - S, 3))\n"
        "    gap = max(0.0, round(R_with - R_without, 3))\n"
        "    if gap < 0.3: verdict = 'canonical'\n"
        "    elif gap >= 0.8: verdict = 'topical-cache'\n"
        "    else: verdict = 'mixed'\n"
        "    return dict(setup=setup, punch=punch, R_with=round(R_with, 3), R_without=R_without, gap=gap, verdict=verdict)\n"
        "\n"
        "temporal_results = []\n"
        "for headline in headlines[:4]:\n"
        "    one_liner = gen(JOKE_ASK.format(fact=headline), max_new=70, temperature=0.7)\n"
        "    row = temporal_gap(headline, one_liner)\n"
        "    row.update(kind='topical', label=headline[:70], fact=headline, joke=one_liner[:160])\n"
        "    temporal_results.append(row)\n"
        "for label, fact in FACTS:\n"
        "    one_liner = gen(JOKE_ASK.format(fact=fact), max_new=70, temperature=0.7)\n"
        "    row = temporal_gap(fact, one_liner)\n"
        "    row.update(kind='canonical', label=label, fact=fact, joke=one_liner[:160])\n"
        "    temporal_results.append(row)\n"
        "\n"
        "print(f\"\\n{'kind':10s} {'label':22s} {'gap':>5s}  verdict\")\n"
        "for row in temporal_results:\n"
        "    print(f\"{row['kind']:10s} {row['label'][:22]:22s} {row['gap']:5.2f}  {row['verdict']:14s} :: {row['joke'][:60]}\")"
    ),
    md(
        "## Remix: does the frame survive a format transfer?\n"
        "Take the top-measured frames and recompile them into a different timing envelope "
        "(meme caption / 15-second beat sheet). THEORY.md says the *frame* is the invariant and the "
        "*format* is the envelope — so a good remix keeps R when the surface changes."
    ),
    code(
        "REMIX_FORMATS = {\n"
        "  'meme_caption': \"Rewrite as a meme: 'TOP: ... / BOTTOM: ...', <=10 words each; bottom re-frames, never describes.\",\n"
        "  'shorts_beat': \"Rewrite as 'HOOK:/BUILD:/SNAP:' beats, <=40 spoken words total.\",\n"
        "}\n"
        "remixes = []\n"
        "for m in ranked[:3]:\n"
        "    if m['frame'] == 'NONE': continue\n"
        "    for fmt, contract in REMIX_FORMATS.items():\n"
        "        out = gen(f\"Keep this exact comic frame: {m['frame']}\\nOriginal joke: {m['text']}\\n\"\n"
        "                  f\"{contract} Return only the rewritten piece.\", max_new=90, temperature=0.8)\n"
        "        s2, p2 = split_sp(out.replace('/', '\\n'))\n"
        "        S2 = nll_mean(s2 + '\\n', ' ' + p2)\n"
        "        r_raw2 = max(0.0, S2 - nll_mean(s2 + '\\n(' + m['frame'] + ')\\n', ' ' + p2))\n"
        "        r_null2 = max(0.0, S2 - nll_mean(s2 + '\\n(' + DECOY + ')\\n', ' ' + p2))\n"
        "        R2 = max(0.0, r_raw2 - r_null2)\n"
        "        kept = 'FRAME SURVIVED' if R2 >= 0.5 * max(m['R'], 0.05) else 'frame lost'\n"
        "        remixes.append({'orig': m['text'][:70], 'frame': m['frame'], 'format': fmt,\n"
        "                        'remix': out[:160], 'R_orig': m['R'], 'R_remix': round(R2,3), 'verdict': kept})\n"
        "        print(f\"[{fmt}] R {m['R']:.2f} -> {R2:.2f} ({kept})\\n  {out[:110]}\\n\")\n"
        "json.dump({'measured': measured, 'remixes': remixes, 'temporal': temporal_results},\n"
        "          open('/kaggle/working/research_out/corpus_report.json', 'w'), indent=2)\n"
        "print('wrote corpus_report.json')"
    ),
    md(
        "## Reading the results\n"
        "- The census is a measured claim about internet humor: what fraction actually sits in the "
        "laugh region vs being predictable (dad-joke floor) or frame-less.\n"
        "- Remix verdicts test the theory's central invariance: **frames transfer, surfaces don't** — "
        "a remix that keeps ≥50% of the original's R carried its re-route into the new envelope.\n"
        "- With hosted keys attached (Gemini add-on / Ollama Cloud / NVIDIA / Mistral), the same "
        "pipeline upgrades: better frame-writers, persona-panel ratings per item, and vibe-matched "
        "remixing per target audience."
    ),
]


def main() -> None:
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
        "cells": CELLS,
    }
    (HERE / "corpus_lab.ipynb").write_text(json.dumps(nb, indent=1), encoding="utf-8")
    print("wrote", HERE / "corpus_lab.ipynb", f"({len(CELLS)} cells)")


if __name__ == "__main__":
    main()

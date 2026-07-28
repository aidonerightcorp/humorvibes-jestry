"""Generate the HumorVibes display demo notebook.

The PUBLISHED artifact is the --static edition: deterministic from receipt content,
no server, no tunnel, committed beside this builder and pinned by tests. A live
tunnelled variant (the builder's default mode) exists as a local-session tool only.

Two things this deliberately does NOT do:

* **No dataset mount.** The receipts are embedded as literals at build time, so the
  kernel has nothing to wait for and cannot fail on a dataset that is still
  processing. The cost is that the notebook is a snapshot — the build stamps which
  receipt files it read and when, so a stale demo is legible rather than silent.
* **No instrument run.** The measurements are already receipted locally; re-running
  a 60-minute llama.cpp sweep inside a display demo would add an hour of risk to
  something whose job is to SHOW a result.

The kernel serves the same numbers twice: rendered inline as charts, and live over a
Cloudflare quick tunnel. Every surface carries the build NONCE so the tunnel can be
proven to be serving THIS build rather than a stale session someone else left up —
the house rule after a public ntfy topic was used as an announce channel.

    python3 build_demo_notebook.py          # live edition (tunnel cells, session nonce)
    python3 build_demo_notebook.py --static # public edition (deterministic, committed)
    kaggle kernels push -p ceiling_demo/    # pushes the static edition (see kernel-metadata.json)
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "jestry_out"

PORT = 8081
# Rotated per campaign; a topic that has been committed to a public repo is an
# announce channel, never an authentication channel — hence the nonce.
NTFY_TOPIC = "humorvibes-ceiling-demo-q7r2m9"

# Dark-mode categorical slots 1-3 from the validated reference palette, checked
# with the external dataviz palette validator (--mode dark, surface #1a1a19):
# all six checks PASS (worst adjacent CVD dE 9.4, normal-vision 26.5).
SERIES = ["#3987e5", "#d95926", "#199e70"]
SURFACE = "#1a1a19"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#c3c2b7"
GRID = "#3a3a37"


def _load(name: str):
    path = OUT / name
    if not path.exists():
        return None
    if path.suffix == ".jsonl":
        rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        return rows[-1] if rows else None
    return json.loads(path.read_text(encoding="utf-8"))


def gather() -> dict:
    """Collect the receipts this demo displays, recording what was missing."""
    wanted = {
        "ceiling": "caption_ceiling.json",
        "portability": "caption_portability.json",
        "form_signal": "form_signal_receipts.jsonl",
        "census": "corpus_census.json",
        "corpus_probe": "caption_corpus_probe.json",
        "model": "caption_model.json",
        "instrument": "instrument_rowslice_check.json",
    }
    data, missing, stamps = {}, [], {}
    for key, fname in wanted.items():
        got = _load(fname)
        if got is None:
            missing.append(fname)
            continue
        # Trim the bulk arrays: the demo shows headlines and per-bin summaries,
        # and a 360-row per-contest table would trible the notebook for nothing.
        # The sha256 below is of the FULL receipt on disk, so the trim cannot be
        # mistaken for the source of truth.
        if isinstance(got, dict):
            got = {k: v for k, v in got.items() if k not in ("per_contest",)}
        data[key] = got
        p = OUT / fname
        stamps[fname] = {
            "mtime_utc": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
                                 .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sha256_12": hashlib.sha256(p.read_bytes()).hexdigest()[:12],
            "bytes": p.stat().st_size,
        }
    data["_provenance"] = {
        "built_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "receipt_files": stamps,
        "missing": missing,
        "note": "receipts embedded at build time; this notebook is a snapshot, not a re-run",
    }
    return data


def build(static: bool = False) -> Path:
    """Assemble the notebook. static=True emits the public edition: same receipts,
    same figures, no dashboard/tunnel cells (nothing to keep alive, nothing that
    depends on a session)."""
    receipts = gather()
    # The static public edition is deterministic from CONTENT alone: same
    # receipt bytes -> same notebook bytes, on any checkout. File mtimes are
    # checkout artifacts (CI clones stamp clone-time), so static mode drops
    # them and takes its snapshot time from the ts fields INSIDE the receipts.
    # The live edition keeps mtimes and a time salt because its nonce exists
    # to fingerprint one session.
    if static:
        stamps = receipts["_provenance"]["receipt_files"]
        for s in stamps.values():
            s.pop("mtime_utc", None)
        ts_values = [v.get("ts") for k, v in receipts.items()
                     if k != "_provenance" and isinstance(v, dict) and v.get("ts")]
        receipts["_provenance"]["built_utc"] = (
            max(ts_values) if ts_values else "per-receipt ts")
        receipts["_provenance"]["note"] += (
            "; static edition — snapshot time is the newest in-receipt ts, "
            "file mtimes intentionally omitted")
    salt = "" if static else str(time.time())
    nonce = hashlib.sha256(
        (json.dumps(receipts["_provenance"], sort_keys=True) + salt)
        .encode()).hexdigest()[:12]
    receipts["_provenance"]["nonce"] = nonce
    blob = json.dumps(receipts, ensure_ascii=False, indent=1)

    cells: list[tuple[str, str]] = []

    cells.append(("markdown",
        "# HumorVibes — what the label can support\n\n"
        "A humor model is usually scored against 1.0. On a crowd-rated corpus that is the "
        "wrong denominator: the label is a **mean over a finite number of votes**, so it "
        "carries sampling error, and no predictor can track a noisy measurement better than "
        "a second independent measurement of it does.\n\n"
        "This notebook displays three measurements made on 2026-07-26 over **2,186,939 New "
        "Yorker caption-contest captions in 371 contests** — the only corpus in this project "
        "that ships the raw vote breakdown per item, which is what makes the label's own "
        "error visible:\n\n"
        "1. **The ceiling.** How high can any predictor score against this label?\n"
        "2. **The bound.** How much of a caption's reception is in its words at all?\n"
        "3. **A null.** Do different joke FORMS sit in different surprisal regimes?\n\n"
        "**Framing.** The parent project's thesis is that a joke is a *controlled prediction "
        "error with a cheap, audience-permitted repair* — motivated by the predictive-processing "
        "shorthand ‘the brain is a surprise-reduction engine’, held as a framework rather than a "
        "conclusion. This notebook supplies the discipline around that thesis: the ceiling and "
        "bound put hard numbers on how much any text model could see here (context dominates "
        "text), and the form null is the thesis behaving as predicted — raw surprisal does not "
        "rank humor categories. Tenet-by-tenet evidence status: "
        "[docs/THESIS_AND_EVIDENCE.md](https://github.com/aidonerightcorp/humorvibes-jestry/"
        "blob/main/docs/THESIS_AND_EVIDENCE.md).\n\n"
        "Every number is read from a local receipt, embedded below with its sha256. "
        + ("This is the static public edition: every figure renders from the embedded "
           "receipts, nothing depends on a live session, and the run is fully reproducible "
           "offline.\n\n"
           if static else
           "The last cells serve the same figures live over a Cloudflare quick tunnel.\n\n")
        + f"Build nonce **`{nonce}`** — "
        + ("it identifies this exact build and appears in the executive summary."
           if static else
           "it appears on every surface, so the tunnel can be checked to be serving this "
           "build.")))

    cells.append(("code",
        "# ---- receipts, embedded at build time (no dataset mount, nothing to wait for) ----\n"
        "import json\n"
        f"RECEIPTS = json.loads(r'''{blob}''')\n"
        "prov = RECEIPTS['_provenance']\n"
        "NONCE = prov['nonce']\n"
        "print('built', prov['built_utc'], '| nonce', NONCE)\n"
        "for fname, s in prov['receipt_files'].items():\n"
        "    print(f\"  {fname:<34} {s['bytes']:>8} B  sha256:{s['sha256_12']}  {s.get('mtime_utc', '')}\")\n"
        "if prov['missing']:\n"
        "    print('MISSING (panels for these are skipped, not faked):', prov['missing'])\n"))

    cells.append(("code",
        "# ---- the three headline numbers ----\n"
        "ceil = RECEIPTS['ceiling']['headline']\n"
        "port = RECEIPTS['portability']['results']\n"
        "LABEL_CEILING = ceil['median_ceiling']\n"
        "TEXT_BOUND    = port['text_only_predictor_bound']\n"
        "PORTABLE      = port['portable_share']\n"
        "model = RECEIPTS.get('model')\n"
        "ACHIEVED = model['results']['within_contest_median_spearman'] if model else None\n"
        "\n"
        "print(f'label ceiling (vote noise)        rho <= {LABEL_CEILING:.3f}')\n"
        "print(f'text-only bound (context)         rho <= {TEXT_BOUND:.3f}')\n"
        "print(f'share of standing carried by words  {PORTABLE:.1%}')\n"
        "print('achieved by structural features    '\n"
        "      + (f'rho = {ACHIEVED:.3f}' if ACHIEVED is not None\n"
        "         else 'not embedded in this build (model receipt absent)'))\n"))

    cells.append(("code",
        "# ---- chart setup: dark surface, validated categorical slots ----\n"
        "import matplotlib\n"
        "matplotlib.use('Agg')\n"
        "import matplotlib.pyplot as plt\n"
        "from matplotlib import rcParams\n"
        f"SERIES = {SERIES!r}\n"
        f"SURFACE, INK, INK2, GRID = {SURFACE!r}, {TEXT_PRIMARY!r}, {TEXT_SECONDARY!r}, {GRID!r}\n"
        "rcParams.update({\n"
        "    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,\n"
        "    'savefig.facecolor': SURFACE,\n"
        "    'text.color': INK, 'axes.labelcolor': INK2, 'axes.edgecolor': GRID,\n"
        "    'xtick.color': INK2, 'ytick.color': INK2,\n"
        "    'axes.spines.top': False, 'axes.spines.right': False,\n"
        "    'font.size': 11, 'figure.dpi': 120,\n"
        "})\n"
        "def bare(ax):\n"
        "    ax.grid(axis='x', color=GRID, linewidth=0.6, alpha=0.7)\n"
        "    ax.set_axisbelow(True)\n"
        "print('charts configured')\n"))

    cells.append(("markdown",
        "## 1. The ceiling, and what a model actually reaches\n\n"
        "Two estimators of the label's reliability, on unrelated assumptions: split-half "
        "resampling of each caption's own votes, and the multinomial sampling variance of its "
        "mean. Compared like-for-like they agree to **0.003** — that agreement is the receipt; "
        "the ceiling is what it implies."))

    cells.append(("code",
        "fig, ax = plt.subplots(figsize=(8, 2.9))\n"
        "rows = [('label ceiling\\n(vote noise)', LABEL_CEILING, SERIES[0]),\n"
        "        ('text-only bound\\n(context dependence)', TEXT_BOUND, SERIES[1])]\n"
        "if ACHIEVED is not None:\n"
        "    rows.append(('achieved\\n(structural features)', ACHIEVED, SERIES[2]))\n"
        "ys = range(len(rows))\n"
        "ax.barh(list(ys), [r[1] for r in rows], color=[r[2] for r in rows],\n"
        "        height=0.52, zorder=3)\n"
        "for y, (lab, v, c) in zip(ys, rows):\n"
        "    ax.text(v + 0.012, y, f'{v:.3f}', va='center', color=INK, fontweight='bold')\n"
        "ax.set_yticks(list(ys)); ax.set_yticklabels([r[0] for r in rows], color=INK2)\n"
        "ax.invert_yaxis(); ax.set_xlim(0, 1.0)\n"
        "ax.set_xlabel('Spearman against the published crowd mean, within contest')\n"
        "ax.set_title('A score is only readable against what is achievable', color=INK,\n"
        "             loc='left', fontweight='bold')\n"
        "bare(ax); plt.tight_layout(); plt.show()\n"))

    cells.append(("markdown",
        "## 2. Reliability rises with votes, exactly as sampling error must\n\n"
        "The third check that the estimator measures what it claims. It also prices future "
        "data collection: a rated corpus with 30 votes per item cannot support a model "
        "comparison finer than its own ceiling."))

    cells.append(("code",
        "bv = RECEIPTS['ceiling']['by_vote_count']\n"
        "labs = [f\"{b['median_votes_lo']}–{b['median_votes_hi'] if b['median_votes_hi'] < 10**9 else '+'}\"\n"
        "        for b in bv]\n"
        "fig, ax = plt.subplots(figsize=(8, 3.2))\n"
        "xs = range(len(bv))\n"
        "ax.plot(list(xs), [b['ceiling'] for b in bv], color=SERIES[0], linewidth=2,\n"
        "        marker='o', markersize=9, label='ceiling on Spearman', zorder=3)\n"
        "ax.plot(list(xs), [b['reliability'] for b in bv], color=SERIES[2], linewidth=2,\n"
        "        marker='o', markersize=9, label='label reliability', zorder=3)\n"
        "for x, b in zip(xs, bv):\n"
        "    ax.annotate(f\"{b['ceiling']:.2f}\", (x, b['ceiling']), textcoords='offset points',\n"
        "                xytext=(0, 9), ha='center', color=INK, fontsize=10)\n"
        "ax.set_xticks(list(xs)); ax.set_xticklabels(labs)\n"
        "ax.set_xlabel('votes per caption'); ax.set_ylim(0.5, 1.0)\n"
        "ax.set_title('More votes, less label noise, higher achievable score', color=INK,\n"
        "             loc='left', fontweight='bold')\n"
        "ax.legend(frameon=False, labelcolor=INK2, loc='lower right')\n"
        "ax.grid(axis='y', color=GRID, linewidth=0.6, alpha=0.7); ax.set_axisbelow(True)\n"
        "plt.tight_layout(); plt.show()\n"))

    cells.append(("markdown",
        "## 3. The same words, a different drawing\n\n"
        "2,173 caption texts were submitted to more than one contest. Arm 2 is what arm 1 "
        "would read if context were irrelevant, computed on the same items. Arm 3 shuffles the "
        "partner and must read zero — it is what makes the ratio a measurement rather than an "
        "artifact."))

    cells.append(("code",
        "arms = [('cross-context\\nsame words, new drawing', port['cross_context_spearman'], SERIES[1]),\n"
        "        ('same-context ceiling\\nsplit-half of own votes', port['same_context_ceiling_spearman'], SERIES[0]),\n"
        "        ('placebo\\nshuffled partner', port['placebo_spearman'], SERIES[2])]\n"
        "fig, ax = plt.subplots(figsize=(8, 2.9))\n"
        "ys = range(len(arms))\n"
        "ax.barh(list(ys), [a[1] for a in arms], color=[a[2] for a in arms], height=0.52, zorder=3)\n"
        "for y, (lab, v, c) in zip(ys, arms):\n"
        "    ax.text(v + 0.012, y, f'{v:+.3f}', va='center', color=INK, fontweight='bold')\n"
        "ax.set_yticks(list(ys)); ax.set_yticklabels([a[0] for a in arms], color=INK2, fontsize=10)\n"
        "ax.invert_yaxis(); ax.set_xlim(0, 0.8)\n"
        "ax.set_xlabel('Spearman')\n"
        "ax.set_title(f'Only {PORTABLE:.0%} of a caption\\u2019s standing travels with its words',\n"
        "             color=INK, loc='left', fontweight='bold')\n"
        "bare(ax); plt.tight_layout(); plt.show()\n"
        "\n"
        "print('most context-dependent captions in the corpus:')\n"
        "for ex in RECEIPTS['portability']['examples_most_context_dependent'][:4]:\n"
        "    print(f\"  {ex['standing_a']:.2f} -> {ex['standing_b']:.2f}   {ex['text'][:78]!r}\")\n"))

    cells.append(("markdown",
        "## 4. A null worth keeping\n\n"
        "Does joke FORM change what the certified instrument (gemma-2-2b-it Q4_K_M through "
        "llama.cpp) finds surprising? Deterministic sample, S only, a proverb control arm. "
        "**No form's interval clears the control.** The form labels themselves were repaired "
        "first: `limerick` had been matching any sentence opening \"There was a…\" (652 hits, "
        "now 8 rhyme-verified) and `yo_mama` any mention of a mother (7,177 hits, of which "
        "5,773 were Chuck Norris facts)."))

    cells.append(("code",
        "fs = RECEIPTS.get('form_signal')\n"
        "if not fs:\n"
        "    print('form-signal receipt not embedded in this build')\n"
        "else:\n"
        "    pf = fs['per_form']\n"
        "    ctrl = pf.get('control_proverb')\n"
        "    forms = [(k, v) for k, v in pf.items() if k != 'control_proverb']\n"
        "    forms.sort(key=lambda kv: -kv[1]['mean_S'])\n"
        "    order = forms + ([('control_proverb', ctrl)] if ctrl else [])\n"
        "    fig, ax = plt.subplots(figsize=(8, 4.6))\n"
        "    for i, (name, d) in enumerate(order):\n"
        "        is_ctrl = name == 'control_proverb'\n"
        "        c = SERIES[1] if is_ctrl else SERIES[0]\n"
        "        lo, hi = d['ci95']\n"
        "        ax.plot([lo, hi], [i, i], color=c, linewidth=2, solid_capstyle='round', zorder=3)\n"
        "        ax.plot([d['mean_S']], [i], marker='o', markersize=9, color=c, zorder=4)\n"
        "    if ctrl:\n"
        "        ax.axvline(ctrl['ci95'][1], color=SERIES[1], linestyle='--', linewidth=1.2,\n"
        "                   alpha=0.8, zorder=2)\n"
        "    ax.set_yticks(range(len(order)))\n"
        "    ax.set_yticklabels([n.replace('_', ' ') for n, _ in order], color=INK2)\n"
        "    ax.invert_yaxis()\n"
        "    ax.set_xlabel('mean S (punchline surprisal), 95% bootstrap CI')\n"
        "    ax.set_title(fs['verdict'][:78], color=INK, loc='left', fontweight='bold')\n"
        "    bare(ax); plt.tight_layout(); plt.show()\n"
        "    print(fs['verdict'])\n"
        "    print('caveat:', fs['caveat'])\n"))

    cells.append(("markdown", "## Where this sits\n\n"
        "- Canonical executable study (corpus, taxonomy, Gemma measurement, the 0/10 form "
        "null in full): [Humor Genome Wave 2]"
        "(https://www.kaggle.com/code/taylorsamarel/humor-genome-wave-2-reproducible-gemma-study)\n"
        "- Deterministic causal controls (four arms from one premise, CC0): "
        "[Open Controls Causal Design Lab]"
        "(https://www.kaggle.com/code/taylorsamarel/humor-genome-open-controls-causal-design-lab)\n"
        "- Source, receipts, and the evidence scoreboard: "
        "[aidonerightcorp/humorvibes-jestry]"
        "(https://github.com/aidonerightcorp/humorvibes-jestry)\n\n"
        "Every number above is a stored receipt, displayed — not a claim that any model "
        "understands humor, and not human evidence."))

    if not static:
        cells.append(("markdown", "## 5. The live dashboard\n\n"
            "The same numbers, served by a stdlib HTTP server and exposed through a Cloudflare "
            "quick tunnel. The URL prints below and is announced to ntfy. It carries the build "
            "nonce at `/api/fingerprint`, so it can be told apart from any other session."))

        cells.append(("code", DASHBOARD_CELL.replace("__PORT__", str(PORT))))
        cells.append(("code", TUNNEL_CELL.replace("__PORT__", str(PORT))
                                     .replace("__TOPIC__", NTFY_TOPIC)))
        cells.append(("code", KEEPALIVE_CELL))

    notebook_cells = []
    for index, (kind, source) in enumerate(cells):
        cell = {
            "cell_type": kind,
            "id": f"cell-{index:02d}-{hashlib.sha256(source.encode()).hexdigest()[:12]}",
            "metadata": {},
            "source": source.splitlines(keepends=True),
        }
        if kind == "code":
            cell.update({"execution_count": None, "outputs": []})
        notebook_cells.append(cell)

    nb = {"nbformat": 4, "nbformat_minor": 5,
          "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                      "name": "python3"},
                       "language_info": {"name": "python", "version": "3.11"}},
          "cells": notebook_cells}
    name = "humorvibes_ceiling_demo_static.ipynb" if static else "humorvibes_ceiling_demo.ipynb"
    out = HERE / name
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


DASHBOARD_CELL = r'''
# ---- build the dashboard page and serve it (stdlib only, no pip installs) ----
import http.server, json, socketserver, threading, html

def bar(value, vmax, color, label, sub=""):
    pct = max(0.0, min(1.0, value / vmax)) * 100
    return (f"<div class='row'><div class='lab'>{html.escape(label)}"
            f"<span class='sub'>{html.escape(sub)}</span></div>"
            f"<div class='track'><div class='fill' style='width:{pct:.1f}%;background:{color}'"
            f" title='{value:.4f}'></div></div>"
            f"<div class='val'>{value:.3f}</div></div>")

ceil_rows = [("label ceiling", LABEL_CEILING, SERIES[0], "what vote noise permits"),
             ("text-only bound", TEXT_BOUND, SERIES[1], "what the words can carry")]
if ACHIEVED is not None:
    ceil_rows.append(("achieved", ACHIEVED, SERIES[2], "structural features, contests held out"))

arm_rows = [("cross-context", port['cross_context_spearman'], SERIES[1], "same words, new drawing"),
            ("same-context ceiling", port['same_context_ceiling_spearman'], SERIES[0], "split-half of own votes"),
            ("placebo", port['placebo_spearman'], SERIES[2], "shuffled partner - must read 0")]

vote_rows = "".join(
    f"<tr><td>{b['median_votes_lo']}&ndash;{b['median_votes_hi'] if b['median_votes_hi'] < 10**9 else '+'}</td>"
    f"<td>{b['contests']}</td><td>{b['reliability']:.3f}</td><td>{b['ceiling']:.3f}</td></tr>"
    for b in RECEIPTS['ceiling']['by_vote_count'])

fs = RECEIPTS.get('form_signal')
form_rows = ""
if fs:
    for name, d in sorted(fs['per_form'].items(), key=lambda kv: -kv[1]['mean_S']):
        mark = " (control)" if name == 'control_proverb' else ""
        form_rows += (f"<tr><td>{html.escape(name.replace('_',' '))}{mark}</td><td>{d['n']}</td>"
                      f"<td>{d['mean_S']:.3f}</td>"
                      f"<td>[{d['ci95'][0]:.2f}, {d['ci95'][1]:.2f}]</td></tr>")

ex_rows = "".join(
    f"<tr><td class='q'>{html.escape(e['text'][:90])}</td><td>{e['standing_a']:.2f}</td>"
    f"<td>{e['standing_b']:.2f}</td></tr>"
    for e in RECEIPTS['portability']['examples_most_context_dependent'][:6])

PAGE = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>HumorVibes - what the label can support</title><style>
:root{{color-scheme:dark;--surface:{SURFACE};--card:#232321;--ink:{INK};--ink2:{INK2};--grid:{GRID}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--surface);color:var(--ink);
 font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
.wrap{{max-width:900px;margin:0 auto;padding:28px 20px 60px}}
h1{{font-size:26px;margin:0 0 6px}} h2{{font-size:17px;margin:34px 0 12px}}
p.lede{{color:var(--ink2);margin:0 0 8px;max-width:70ch}}
.hero{{display:flex;flex-wrap:wrap;gap:12px;margin:22px 0 8px}}
.tile{{flex:1 1 200px;background:var(--card);border:1px solid var(--grid);
 border-radius:10px;padding:14px 16px}}
.tile .n{{font-size:30px;font-weight:700;letter-spacing:-.5px}}
.tile .k{{color:var(--ink2);font-size:12px;text-transform:uppercase;letter-spacing:.08em}}
.tile .d{{color:var(--ink2);font-size:13px;margin-top:4px}}
.row{{display:flex;align-items:center;gap:12px;margin:9px 0}}
.lab{{width:190px;font-size:13px;color:var(--ink2);flex:none}}
.lab .sub{{display:block;font-size:11px;opacity:.75}}
.track{{flex:1;background:#2b2b28;border-radius:4px;height:14px;overflow:hidden}}
.fill{{height:100%;border-radius:4px}}
.val{{width:56px;text-align:right;font-variant-numeric:tabular-nums;font-weight:600}}
table{{width:100%;border-collapse:collapse;margin-top:8px;font-size:14px}}
th,td{{text-align:left;padding:7px 10px;border-bottom:1px solid var(--grid)}}
th{{color:var(--ink2);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.06em}}
td.q{{color:var(--ink2)}}
.scroll{{overflow-x:auto}}
footer{{margin-top:38px;color:var(--ink2);font-size:12px;border-top:1px solid var(--grid);padding-top:14px}}
code{{background:#2b2b28;padding:1px 5px;border-radius:4px}}
</style></head><body><div class=wrap>
<h1>What the label can support</h1>
<p class=lede>A humor model is usually scored against 1.0. On a crowd-rated corpus that is the
wrong denominator. Measured over 2,186,939 New Yorker caption-contest captions in 371 contests.</p>

<div class=hero>
 <div class=tile><div class=k>label ceiling</div><div class=n>{LABEL_CEILING:.3f}</div>
  <div class=d>highest Spearman any predictor can reach against a vote-sampled mean</div></div>
 <div class=tile><div class=k>text-only bound</div><div class=n>{TEXT_BOUND:.3f}</div>
  <div class=d>a caption's standing barely travels to another drawing</div></div>
 <div class=tile><div class=k>carried by the words</div><div class=n>{PORTABLE:.0%}</div>
  <div class=d>the rest belongs to the fit with the cartoon</div></div>
</div>

<h2>Bounds</h2>
{''.join(bar(v, 1.0, c, l, s) for l, v, c, s in ceil_rows)}

<h2>Same words, different drawing</h2>
{''.join(bar(v, 0.8, c, l, s) for l, v, c, s in arm_rows)}
<div class=scroll><table><thead><tr><th>caption</th><th>standing A</th><th>standing B</th></tr></thead>
<tbody>{ex_rows}</tbody></table></div>

<h2>Reliability by vote count</h2>
<div class=scroll><table><thead><tr><th>votes/caption</th><th>contests</th><th>reliability</th>
<th>ceiling</th></tr></thead><tbody>{vote_rows}</tbody></table></div>

<h2>Joke form vs surprisal &mdash; a null</h2>
<p class=lede>No form's 95% interval clears the proverb control. S is model surprisal, not funniness.</p>
<div class=scroll><table><thead><tr><th>form</th><th>n</th><th>mean S</th><th>95% CI</th></tr></thead>
<tbody>{form_rows}</tbody></table></div>

<footer>Build nonce <code>{NONCE}</code> &middot; receipts embedded {prov['built_utc']} &middot;
served from a Kaggle kernel over a Cloudflare quick tunnel.
Endpoints: <code>/api/fingerprint</code>, <code>/api/receipts</code>.</footer>
</div></body></html>"""

class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, body, ctype="text/html; charset=utf-8", code=200):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)
    def do_GET(self):
        if self.path.startswith("/api/fingerprint"):
            self._send(json.dumps({"nonce": NONCE, "built_utc": prov['built_utc'],
                                   "label_ceiling": LABEL_CEILING,
                                   "text_only_bound": TEXT_BOUND,
                                   "portable_share": PORTABLE}, indent=1),
                       "application/json")
        elif self.path.startswith("/api/receipts"):
            self._send(json.dumps(RECEIPTS, indent=1), "application/json")
        elif self.path in ("/", "/index.html"):
            self._send(PAGE)
        else:
            self._send("not found", "text/plain; charset=utf-8", 404)
    def log_message(self, *a):
        pass

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

httpd = Server(("127.0.0.1", __PORT__), Handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

import urllib.request
probe = json.loads(urllib.request.urlopen(
    "http://127.0.0.1:__PORT__/api/fingerprint", timeout=5).read())
assert probe["nonce"] == NONCE, ("the server is not serving this build: "
                                 f"{probe['nonce']} != {NONCE}")
print("dashboard answering on 127.0.0.1:__PORT__, fingerprint", probe["nonce"])
print("page bytes:", len(PAGE))
'''

TUNNEL_CELL = r'''
# ---- cloudflared quick tunnel ----
import os, re, subprocess, sys, time, urllib.request

CF = "/kaggle/working/cloudflared"
if not os.path.exists(CF):
    urllib.request.urlretrieve(
        "https://github.com/cloudflare/cloudflared/releases/latest/download/"
        "cloudflared-linux-amd64", CF)
    os.chmod(CF, 0o755)

def start_tunnel():
    return subprocess.Popen(
        [CF, "tunnel", "--url", "http://127.0.0.1:__PORT__", "--no-autoupdate"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

def read_url(proc, timeout=150):
    t0, buf = time.time(), []
    while time.time() - t0 < timeout:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.2)
            continue
        buf.append(line)
        m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
        if m:
            return m.group(0), buf
    return None, buf

cf_proc = start_tunnel()
URL, buf = read_url(cf_proc)
assert URL, "no tunnel URL:\n" + "".join(buf)[-2500:]

# Verify from the PUBLIC side before announcing it. A tunnel that resolves but
# serves someone else's session is worse than no tunnel, so the check is the
# nonce, not a 200.
pub = None
for _ in range(20):
    try:
        pub = json.loads(urllib.request.urlopen(URL + "/api/fingerprint", timeout=10).read())
        break
    except Exception:
        time.sleep(3)
assert pub and pub.get("nonce") == NONCE, f"tunnel did not serve this build: {pub}"

TOPIC = "__TOPIC__"
def announce(u):
    try:
        req = urllib.request.Request(
            f"https://ntfy.sh/{TOPIC}",
            data=json.dumps({"url": u, "nonce": NONCE,
                             "built_utc": prov["built_utc"]}).encode(),
            headers={"Title": "humorvibes ceiling demo live"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print("announce failed (the URL below is still valid):", e)

announce(URL)
print("=" * 72)
print("DEMO URL:", URL)
print("fingerprint verified over the public tunnel:", pub["nonce"])
print("=" * 72)
'''

KEEPALIVE_CELL = r'''
# ---- keep the tunnel up, then exit cleanly so the kernel completes ----
TTL_MIN = 150
END = time.time() + TTL_MIN * 60
last = time.time()
while time.time() < END:
    time.sleep(30)
    if cf_proc.poll() is not None:
        print("tunnel dropped; restarting")
        cf_proc = start_tunnel()
        u2, _ = read_url(cf_proc)
        if u2:
            URL = u2
            announce(URL)
            print("new URL:", URL)
    if time.time() - last > 1800:
        announce(URL)
        last = time.time()
print("session end; final URL was:", URL)
try:
    cf_proc.terminate()
except Exception:
    pass
httpd.shutdown()
print("clean exit")
'''


if __name__ == "__main__":
    import sys as _sys
    print(build(static="--static" in _sys.argv))

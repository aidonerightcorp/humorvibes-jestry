#!/usr/bin/env python3
"""Build the ≤2-min HumorVibes submission video from the repo's real evidence:
the pinned instrument numbers, the ablation-court figure, the receipted
failure case, and today's live-portal screenshots. Rendered with the
forge_slides pipeline (headless-chrome slides, flite narration, music bed,
soft subs). Output lands in demo_assets/.

    python3 make_submission_video.py
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FORGE = os.path.join(os.path.dirname(os.path.dirname(HERE)), "forge_slides")
if not os.path.isdir(FORGE):
    FORGE = os.path.expanduser("~/new_algo/forge_slides")
sys.path.insert(0, FORGE)
import slidesmith as sm  # noqa: E402

ABLATION_FIG = os.path.join(HERE, "research_out", "kaggle",
                            "humorvibes-ablation-court", "ablation_failure_figure.png")
DASH_PNG = os.path.join(HERE, "demo_assets", "jestry_dashboard_20260724.png")
BEEN_PNG = os.path.join(HERE, "demo_assets", "jestry_beendone_20260724.png")

DECK = [
    {"kind": "title",
     "title": "HumorVibes",
     "subtitle": "A joke is a controlled prediction error with a cheap, audience-permitted repair.",
     "note": "A joke is a controlled prediction error with a cheap, audience "
             "permitted repair. HumorVibes turns that claim into four "
             "falsifiable signals."},

    {"kind": "code",
     "title": "REAL GEMMA LOGITS - VERIFIED RUN",
     "code": ("S = NLL(punchline | setup)      teacher-forced surprisal\n"
              "R = collapse after hidden frame  (net of a decoy null)\n"
              "E = R per frame token            affordability\n"
              "B = persona-conditioned judgment (separate gate)\n\n"
              "speed-bumps joke, three independent instruments:\n"
              "  pinned Kaggle gemma-2-2b run ......... S = 3.19\n"
              "  local llama.cpp full-vocab gemma-2 ... S = 3.19\n"
              "  in-kernel transformers Gemma ......... S = 3.19"),
     "note": "Pinned Gemma 2 supplies true teacher forced log probabilities. "
             "S is punchline surprisal. R is the collapse a hidden frame "
             "produces. E is R per frame token. B is a separate persona "
             "conditioned judgment. One joke, three independent instruments, "
             "one number."},

    {"kind": "bullets",
     "title": "Controls earned by failure",
     "bullets": ["Our first metric credited nonsense: raw R = 2.37",
                 "Decoy-hint null control: 2.67 on the same nonsense, netting it to 0.00",
                 "**A leak guard then zeroed all four frame-writers on the lexical shortcut",
                 "Real jokes keep their resolution: R = 0.35 to 1.29 net of controls"],
     "reveal": True,
     "note": "Our first metric credited nonsense, raw R two point three "
             "seven. The matched null zeroed it, and a later leak guard "
             "drove all four frame writers to zero on the lexical shortcut. "
             "Real jokes keep their resolution."},

    {"kind": "chart",
     "title": "Human ablation court: 200 of 200 measurements",
     "image": ABLATION_FIG,
     "note": "The source pinned court completed two hundred of two hundred "
             "measurements. Full S R E B reached only rho zero point zero "
             "three three, confidence interval crossing zero. Human edits "
             "did not beat shuffled edits. B did separate them, but did not "
             "predict funniness. Safety is a constraint, not the objective."},

    {"kind": "code",
     "title": "A failure we show on purpose",
     "code": ("shuffled headline:\n"
              "  \"Macron urges US to puppy isolationism\"\n\n"
              "  full_score = 43.3   <- the instrument liked it\n"
              "  human grade =  0.4  <- the room did not\n\n"
              "the model invented a frame; the split was wrong.\n"
              "diagnostic instrument, not an oracle."),
     "note": "A shuffled headline, Macron urges US to puppy isolationism, "
             "scored forty three point three. The model invented a frame. "
             "That is why this is a diagnostic instrument, not an oracle."},

    {"kind": "chart",
     "title": "The live workflow runs on receipts",
     "image": DASH_PNG,
     "note": "The live portal shows the whole loop. Generation, ranking, "
             "repair, and a contribution funnel where every accepted laugh "
             "carries a receipt."},

    {"kind": "chart",
     "title": "Been done? 23,155 items, 46 languages",
     "image": BEEN_PNG,
     "note": "Has this joke been done before is a first class query. An "
             "English paraphrase retrieves the Korean and Japanese even "
             "monkeys fall from trees as top neighbors, across a twenty "
             "three thousand item, forty six language index."},

    {"kind": "title",
     "title": "Measured, gated, honest",
     "subtitle": "The compiled example still fails lint and stays unvalidated. "
                 "HumorVibes measures affordable surprise, and records where it fails.",
     "note": "The compiled example fails lint and remains unvalidated. "
             "Forced replay is only a reproducibility proof. HumorVibes "
             "measures affordable surprise, and records where it fails."},
]


def main():
    for p in (ABLATION_FIG, DASH_PNG, BEEN_PNG):
        assert os.path.exists(p), f"missing evidence asset: {p}"
    res = sm.deck_to_video(DECK, "humorvibes_submission", music_style="lofi")
    out_dir = os.path.join(FORGE, "out")
    made = [f for f in os.listdir(out_dir) if f.startswith("humorvibes_submission")]
    for f in made:
        shutil.copy2(os.path.join(out_dir, f),
                     os.path.join(HERE, "demo_assets", f))
    print("copied to demo_assets:", sorted(made))
    return res


if __name__ == "__main__":
    main()

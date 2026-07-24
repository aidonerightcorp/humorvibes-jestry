"""Humor Vibes Open — deterministic competition data builder.

Builds Track A data from on-disk, provenance-carrying supply only:

- GENUINE  harvested public-API jokes with native setup/punchline fields
           (harvest_official_joke_api_*.jsonl, harvest_jokeapi_*.jsonl twopart)
           plus the three canonical reference jokes;
- SHUFFLED derangement of punchlines across setups (seeded) — surprise without
           a re-route;
- BORING   fixed low-surprise continuations on genuine setups — no surprise.

Outputs under data/: train.csv (labels visible), test.csv, solution.csv
(host-only; is_genuine, control_type, setup_key, Usage split), and
sample_submission.csv. Same supply + same seed -> byte-identical rebuild.
Scale up by running harvest_supply.py with larger limits first; every dated
harvest file is picked up automatically.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CORPORA = ROOT / "corpora"
DATA = HERE / "data"

SEED = 20260723
PUBLIC_FRACTION = 0.6

CANONICAL = [
    ("I told my therapist about my fear of speed bumps.",
     "She said I'm slowly getting over it.", "canonical reference", "repo"),
    ("My grandfather has the heart of a lion",
     "and a lifetime ban from the zoo.", "canonical reference", "repo"),
    ("The AI project manager finally found the bottleneck:",
     "the calendar wanted attention.", "canonical reference", "repo"),
]

# boring continuations are TEMPLATED with a setup-derived slot so no fixed
# string set exists to regex for (adversarial finding: 4 constant tails were
# 25% of negatives and separable at AUC 0.63 with zero humor modeling)
BORING_TEMPLATES = [
    "and the {w} stayed exactly where it was.",
    "so the {w} carried on as usual.",
    "and nothing about the {w} changed at all.",
    "then the {w} went back to normal.",
    "and the {w} remained perfectly ordinary.",
    "so the {w} continued without incident.",
    "and the {w} was quietly put away.",
    "then the {w} was discussed at the next meeting.",
]


def _boring_tail(setup: str, i: int) -> str:
    words = [w.strip(".,!?\"'()").lower() for w in setup.split()]
    nouns = [w for w in words if len(w) > 3 and w.isalpha()]
    w = nouns[-1] if nouns else "matter"
    return BORING_TEMPLATES[i % len(BORING_TEMPLATES)].format(w=w)


def collect_genuine() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(CORPORA.glob("harvest_*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "_meta" in rec:
                continue
            meta = rec.get("meta") or {}
            setup = str(meta.get("setup", "")).strip()
            punch = str(meta.get("punchline", "")).strip()
            if setup and punch and len(setup.split()) >= 3:
                rows.append({"setup": setup, "punchline": punch,
                             "source": rec.get("source", path.stem),
                             "license": rec.get("license", "unknown")})
    for setup, punch, source, license_ in CANONICAL:
        rows.append({"setup": setup, "punchline": punch,
                     "source": source, "license": license_})
    # dedupe by setup+punchline
    seen: set[str] = set()
    out = []
    for r in rows:
        key = hashlib.sha256((r["setup"] + "||" + r["punchline"]).encode()).hexdigest()[:16]
        if key in seen:
            continue
        seen.add(key)
        r["setup_key"] = key[:10]
        out.append(r)
    return out


def build() -> dict:
    rng = random.Random(SEED)
    pool = collect_genuine()
    pool.sort(key=lambda r: r["setup_key"])          # order independent of glob order
    assert len(pool) >= 24, f"only {len(pool)} genuine items — harvest more first"

    # shuffled controls draw punchlines from a DISJOINT donor reservoir: half
    # the pool is sacrificed so no punchline string ever appears both as a
    # genuine and as a control (adversarial finding: the verbatim-reuse
    # derangement made labels solvable by constraint propagation at AUC 0.986)
    # split must be punchline-TEXT-disjoint, not item-disjoint: classic
    # punchlines legitimately recur across corpora, and one text on both
    # sides reopens the overlap exploit
    by_punch: dict[str, list[dict]] = {}
    for r in pool:
        by_punch.setdefault(r["punchline"], []).append(r)
    groups = list(by_punch.values())
    rng.shuffle(groups)
    donors, keep = [], []
    for g in groups:
        (donors if len(donors) < len(pool) // 2 else keep).extend(g)
    donor_punchlines = sorted({d["punchline"] for d in donors})
    rng.shuffle(donor_punchlines)
    items: list[dict] = []
    for n, r in enumerate(keep):
        items.append(r | {"is_genuine": 1, "control_type": ""})
        items.append({"setup": r["setup"],
                      "punchline": donor_punchlines[n % len(donor_punchlines)],
                      "source": "constructed control", "license": "derived",
                      "setup_key": r["setup_key"],
                      "is_genuine": 0, "control_type": "shuffled"})
        if n % 3 == 0:      # boring controls on a third of setups
            items.append({"setup": r["setup"],
                          "punchline": _boring_tail(r["setup"], n),
                          "source": "constructed control", "license": "derived",
                          "setup_key": r["setup_key"],
                          "is_genuine": 0, "control_type": "boring"})
    rng.shuffle(items)
    for n, item in enumerate(items):
        item["id"] = f"hv_{n:05d}"
        item["Usage"] = "Public" if rng.random() < PUBLIC_FRACTION else "Private"

    # train/test split at the SETUP level so no setup leaks across the boundary
    setup_keys = sorted({i["setup_key"] for i in items})
    rng2 = random.Random(SEED + 1)
    rng2.shuffle(setup_keys)
    train_keys = set(setup_keys[: len(setup_keys) // 3])
    train = [i for i in items if i["setup_key"] in train_keys]
    test = [i for i in items if i["setup_key"] not in train_keys]

    DATA.mkdir(exist_ok=True)

    def write(name: str, rows: list[dict], cols: list[str]) -> None:
        with (DATA / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

    write("train.csv", train,
          ["id", "setup", "punchline", "is_genuine", "control_type", "source", "license"])
    write("test.csv", test, ["id", "setup", "punchline"])
    write("solution.csv", test,
          ["id", "is_genuine", "control_type", "setup_key", "Usage"])
    write("sample_submission.csv",
          [{"id": i["id"], "humor_score": 0.5} for i in test], ["id", "humor_score"])
    # -- self-attack checks (run on every build; loud failure over silence) --
    non_boring = [i for i in items if i["control_type"] != "boring"]
    from collections import Counter
    occ = Counter(i["punchline"] for i in non_boring)
    assert occ.most_common(1)[0][1] <= 2, \
        f"punchline reuse exploit reopened: {occ.most_common(3)}"
    dup_across = {p for i in items if i["is_genuine"] for p in [i["punchline"]]} & \
                 {i["punchline"] for i in items if i["control_type"] == "shuffled"}
    assert not dup_across, f"genuine/control punchline overlap: {list(dup_across)[:2]}"
    borings = [i["punchline"] for i in items if i["control_type"] == "boring"]
    assert len(set(borings)) >= min(8, len(borings)), "boring tails too constant"

    manifest = {
        "seed": SEED, "genuine": len(keep), "donors_sacrificed": len(donors),
        "items": len(items),
        "self_attack": {"max_punchline_occurrence": occ.most_common(1)[0][1],
                        "genuine_control_overlap": 0,
                        "distinct_boring_tails": len(set(borings))},
        "train": len(train), "test": len(test),
        "test_genuine": sum(1 for i in test if i["is_genuine"]),
        "test_controls": sum(1 for i in test if not i["is_genuine"]),
        "public": sum(1 for i in test if i["Usage"] == "Public"),
        "licenses": sorted({i["license"] for i in items}),
    }
    (DATA / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))

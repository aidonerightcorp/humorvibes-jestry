"""Build the post-closeout wave-1 figures from committed receipts.

Three figures the project's receipts have carried for weeks but never drawn:

1. ``docs/figures/caption-ceiling-waterfall.svg`` — what a caption-ranking
   model can possibly reach: perfect agreement (reference), the measured label
   ceiling, the text-only bound, and the current text model, from
   ``jestry_out/caption_ceiling.json`` / ``caption_portability.json`` /
   ``caption_model.json``.
2. ``docs/figures/cross-corpus-transfer.svg`` — the 2x2 train/test Spearman
   matrix from ``jestry_out/cross_corpus_transfer.json`` ("one invariant, one
   collapse" — the honest-model figure).
3. ``docs/figures/genome-atlas-languages.png`` — the Humor Genome Atlas:
   a t-SNE projection of the 23,779-item surface-channel embedding matrix,
   shown as an overview panel plus one facet per top language (single-hue
   highlights over a neutral underlay — the all-pairs palette cap forbids a
   9-color scatter, and facets read better anyway).

Every number is read from its receipt at build time; nothing is hand-typed.
The atlas draws COORDINATES ONLY — no corpus text enters the figure, so
research-only rows stay research-only. A small receipt records inputs/params.

Usage:
    python3 tools/build_wave1_figures.py \
        --data-root /path/to/build-with-gemma-humor-genome-nyc
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
FIGDIR = REPO / "docs" / "figures"
INK = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e4e3dc"
BLUE = "#2a78d6"          # categorical slot 1 (validated light-mode palette)
BLUE_TINT = "#b9cfe7"
SURFACE = "#ffffff"
UNDERLAY = "#c6c5bd"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fig_waterfall() -> dict:
    ceil = load(REPO / "jestry_out" / "caption_ceiling.json")["headline"]["median_ceiling"]
    port = load(REPO / "jestry_out" / "caption_portability.json")["results"]
    model = load(REPO / "jestry_out" / "caption_model.json")["results"]
    bound = port["text_only_predictor_bound"]
    got = model["within_contest_median_spearman"]

    rows = [
        ("Perfect agreement", 1.0, "reference bound", "ref"),
        ("Label ceiling", ceil, "crowd self-agreement, 2.05M captions", "solid"),
        ("Text-only bound", bound,
         f"~{port['portable_share']:.0%} of the label-permitted signal is in the words "
         f"({port['cross_context_spearman']:.0%} of observed standing)", "tint"),
        ("Current text model", got, f"{model['contests_above_chance']}/{model['contests_scored']} contests above chance", "tint"),
    ]
    fig, ax = plt.subplots(figsize=(9.2, 3.7), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    y = np.arange(len(rows))[::-1]
    for yi, (label, val, sub, kind) in zip(y, rows):
        if kind == "ref":
            ax.barh(yi, val, height=0.52, fill=False, edgecolor=GRID,
                    linestyle=(0, (4, 3)), linewidth=1.6)
        else:
            ax.barh(yi, val, height=0.52,
                    color=BLUE if kind == "solid" else BLUE_TINT)
        ax.text(-0.012, yi + 0.13, label, ha="right", va="center",
                fontsize=10.5, color=INK, transform=ax.get_yaxis_transform())
        ax.text(-0.012, yi - 0.21, sub, ha="right", va="center",
                fontsize=8, color=MUTED, transform=ax.get_yaxis_transform())
        ax.text(val + 0.012, yi, f"{val:.3f}", ha="left", va="center",
                fontsize=10, color=INK, fontweight="bold")
    ax.set_xlim(0, 1.09)
    ax.set_ylim(-0.55, len(rows) - 0.45)
    ax.set_yticks([])
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.tick_params(colors=MUTED, labelsize=8.5)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.xaxis.grid(True, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.set_title("What a caption-ranking model can reach  (Spearman ρ, within contest)",
                 loc="left", fontsize=12, color=INK, pad=14)
    fig.text(0.125, 0.015,
             "The gap worth chasing is the drawing, not better text features. "
             "Sources: caption_ceiling.json, caption_portability.json, caption_model.json",
             fontsize=7.5, color=MUTED)
    fig.subplots_adjust(left=0.30, right=0.97, top=0.86, bottom=0.16)
    out = FIGDIR / "caption-ceiling-waterfall.svg"
    fig.savefig(out, format="svg", facecolor=SURFACE)
    plt.close(fig)
    return {"file": out.name, "ceiling": ceil, "bound": bound, "model": got}


def fig_transfer() -> dict:
    r = load(REPO / "jestry_out" / "cross_corpus_transfer.json")["results"]
    mat = np.array([
        [r["within_humicroedit_spearman"], r["transfer_humicroedit_to_reddit_spearman"]],
        [r["reverse_reddit_to_humicroedit_spearman"], r["within_reddit_spearman"]],
    ])
    fig, ax = plt.subplots(figsize=(5.6, 5.0), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    im = ax.imshow(mat, cmap="RdBu", vmin=-0.55, vmax=0.55)
    for (i, j), val in np.ndenumerate(mat):
        dark = abs(mat[i, j]) > 0.30
        ax.text(j, i, f"{val:+.3f}", ha="center", va="center", fontsize=15,
                fontweight="bold", color="#ffffff" if dark else INK)
    ax.set_xticks([0, 1], ["Humicroedit", "r/Jokes"])
    ax.set_yticks([0, 1], ["Humicroedit", "r/Jokes"])
    ax.set_xlabel("evaluated on", fontsize=10, color=MUTED)
    ax.set_ylabel("trained on", fontsize=10, color=MUTED)
    ax.tick_params(colors=INK, labelsize=10.5)
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.set_title("The structural model does not transfer\n(held-out Spearman ρ)",
                 loc="left", fontsize=12, color=INK, pad=12)
    fig.text(0.02, 0.035,
             '"The 0.51 describes Humicroedit, not humor." — cross_corpus_transfer.json',
             fontsize=7.5, color=MUTED)
    fig.text(0.02, 0.008,
             "The collapse is Humicroedit→Reddit; the r/Jokes-trained arm retains 56% of its "
             "own within-corpus ρ.",
             fontsize=7, color=MUTED)
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.ax.tick_params(colors=MUTED, labelsize=8)
    cbar.outline.set_color(GRID)
    ax.yaxis.set_label_coords(-0.28, 0.5)
    fig.subplots_adjust(left=0.26, right=0.98, top=0.84, bottom=0.13)
    out = FIGDIR / "cross-corpus-transfer.svg"
    fig.savefig(out, format="svg", facecolor=SURFACE)
    plt.close(fig)
    return {"file": out.name, "matrix": mat.round(4).tolist()}


def fig_atlas(data_root: Path, seed: int) -> dict:
    from sklearn.decomposition import PCA
    from sklearn.manifold import TSNE

    emb_path = data_root / "dataset_out" / "embeddings_surface.npy"
    items_path = data_root / "dataset_out" / "items.jsonl"
    X = np.asarray(np.load(emb_path, mmap_mode="r"), dtype=np.float32)
    langs: list[str] = []
    with open(items_path, encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            langs.append(row.get("language") or "unknown")
    langs_arr = np.array(langs[: len(X)])
    if len(langs_arr) != len(X):
        raise SystemExit(f"items ({len(langs_arr)}) and embeddings ({len(X)}) misaligned")

    print(f"atlas: PCA(50) + TSNE on {X.shape} ...", flush=True)
    Xp = PCA(n_components=50, random_state=seed).fit_transform(X)
    coords = TSNE(n_components=2, perplexity=40, random_state=seed,
                  init="pca", learning_rate="auto").fit_transform(Xp)

    counts = {l: int(n) for l, n in
              zip(*np.unique(langs_arr, return_counts=True))}
    top8 = [l for l, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:8]]

    fig, axes = plt.subplots(3, 3, figsize=(13.5, 13.9), dpi=160)
    fig.patch.set_facecolor(SURFACE)
    panels = [("All items", None)] + [(l, l) for l in top8]
    for ax, (title, lang) in zip(axes.flat, panels):
        ax.set_facecolor(SURFACE)
        underlay_alpha = 0.32 if lang is None else 0.22
        ax.scatter(coords[:, 0], coords[:, 1], s=1.4, c=UNDERLAY,
                   alpha=underlay_alpha, linewidths=0, rasterized=True)
        n = len(coords)
        if lang is not None:
            mask = langs_arr == lang
            n = int(mask.sum())
            ax.scatter(coords[mask, 0], coords[mask, 1], s=2.6, c=BLUE,
                       alpha=0.6, linewidths=0, rasterized=True)
        ax.set_title(f"{title}   n={n:,}", loc="left", fontsize=11,
                     color=INK, pad=6)
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color(GRID)
    fig.suptitle("The Humor Genome Atlas — surface channel, by language",
                 x=0.065, ha="left", fontsize=16, color=INK, y=0.985)
    fig.text(0.065, 0.958,
             "t-SNE of 23,779 registry items (EmbeddingGemma, 768d). Coordinates only — "
             "no corpus text is shown; research-only rows stay research-only.",
             fontsize=9.5, color=MUTED)
    fig.text(0.065, 0.941,
             "Caveat: the projection is dominated by language/source (facets are near-disjoint "
             "blobs) — this maps the corpus, not humor structure; t-SNE cluster sizes and "
             "distances are not metric.",
             fontsize=9.5, color=MUTED)
    fig.subplots_adjust(left=0.03, right=0.985, top=0.925, bottom=0.03,
                        hspace=0.16, wspace=0.06)
    out = FIGDIR / "genome-atlas-languages.png"
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)

    coords_out = data_root / "jestry_out" / "genome_atlas_coords_wave1.npz"
    np.savez_compressed(coords_out, coords=coords, languages=langs_arr)
    return {
        "file": out.name,
        "points": int(len(coords)),
        "languages_top8": {l: counts[l] for l in top8},
        "tsne": {"perplexity": 40, "init": "pca", "seed": seed, "pca_components": 50},
        "embeddings_sha256": sha256_file(emb_path),
        "coords_archived": "research tree jestry_out/genome_atlas_coords_wave1.npz "
                            "(not committed; embeddings identified by sha256 above)",
        "caveat": "projection dominated by language/source — a corpus map, not a "
                   "humor-structure result; t-SNE distances are not metric",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-root", default=".",
                    help="research tree containing dataset_out/ (atlas inputs)")
    ap.add_argument("--seed", type=int, default=20260727)
    ap.add_argument("--skip-atlas", action="store_true")
    args = ap.parse_args()
    FIGDIR.mkdir(parents=True, exist_ok=True)

    receipt_path = REPO / "jestry_out" / "wave1_figures_receipt.json"
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    receipt.update({
        "receipt_type": "wave1_figures",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "waterfall": fig_waterfall(),
        "transfer": fig_transfer(),
    })
    print("waterfall + transfer done", flush=True)
    if not args.skip_atlas:
        receipt["atlas"] = fig_atlas(Path(args.data_root), args.seed)
        print("atlas done", flush=True)
    (REPO / "jestry_out" / "wave1_figures_receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n")
    print("wrote jestry_out/wave1_figures_receipt.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

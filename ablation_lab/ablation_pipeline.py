#!/usr/bin/env python3
"""HumorVibes judge-evidence court for Kaggle.

Runs a fixed-weight S/R/E/B leave-one-component ablation against real Humicroedit
human grades, plus paired original-headline and shuffled-edit controls.  The
script writes per-item evidence, failure cases, a figure, and a runtime receipt.

This is designed for the private Kaggle kernel `humorvibes-ablation-court` with
the exact signal source vendored into the notebook and google/gemma-2-2b-it attached.
"""

from __future__ import annotations

import csv
import glob
import hashlib
import io
import json
import os
import platform
import random
import re
import sys
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr, wilcoxon


SEED = 20260712
N_HUMAN = 120
N_CONTROL = 40
BOOTSTRAPS = 1000
DATA_URL = "https://cs.rochester.edu/u/nhossain/humicroedit/semeval-2020-task-7-data.zip"
MODEL_SOURCE = "google/gemma-2/transformers/gemma-2-2b-it/2"
KERNEL_ID = "taylorsamarel/humorvibes-ablation-court"
PERSONA = "a broad U.S. news audience including people or groups named in the headline"
WEIGHTS = {"S": 0.30, "R": 0.35, "E": 0.15, "B": 0.20}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_dump(path: str | Path, payload: Any) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def original_word(text: str) -> str:
    match = re.search(r"<([^/>]+)/>", str(text))
    return match.group(1) if match else ""


def apply_edit(text: str, replacement: str) -> str:
    return re.sub(r"<[^/>]+/>", str(replacement), str(text))


def fixed_score(frame: pd.DataFrame, components: list[str]) -> np.ndarray:
    denominator = sum(WEIGHTS[name] for name in components)
    if denominator <= 0:
        raise ValueError("At least one component is required")
    score = np.zeros(len(frame), dtype=np.float64)
    for name in components:
        score += WEIGHTS[name] * frame[f"{name}_score"].to_numpy(float)
    return 100.0 * score / denominator


def correlations(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return {"pearson": 0.0, "pearson_p": 1.0, "spearman": 0.0, "spearman_p": 1.0}
    pearson = pearsonr(x, y)
    spearman = spearmanr(x, y)
    return {
        "pearson": float(pearson.statistic),
        "pearson_p": float(pearson.pvalue),
        "spearman": float(spearman.statistic),
        "spearman_p": float(spearman.pvalue),
    }


def bootstrap_spearman_ci(x: np.ndarray, y: np.ndarray, seed: int = SEED, rounds: int = BOOTSTRAPS) -> list[float]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    rng = np.random.default_rng(seed)
    values: list[float] = []
    for _ in range(rounds):
        idx = rng.integers(0, len(x), size=len(x))
        if np.std(x[idx]) == 0 or np.std(y[idx]) == 0:
            continue
        value = spearmanr(x[idx], y[idx]).statistic
        if np.isfinite(value):
            values.append(float(value))
    return [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))] if values else [0.0, 0.0]


def component_ablation(human: pd.DataFrame) -> dict[str, Any]:
    all_components = ["S", "R", "E", "B"]
    variants: dict[str, list[str]] = {"full_SREB": all_components}
    for dropped in all_components:
        variants[f"without_{dropped}"] = [name for name in all_components if name != dropped]
    for component in all_components:
        variants[f"only_{component}"] = [component]

    results: dict[str, Any] = {}
    grade = human["grade"].to_numpy(float)
    for offset, (name, components) in enumerate(variants.items()):
        score = fixed_score(human, components)
        result = correlations(score, grade)
        result["spearman_bootstrap_95ci"] = bootstrap_spearman_ci(score, grade, SEED + offset)
        result["components"] = components
        result["score_mean"] = float(np.mean(score))
        result["score_std"] = float(np.std(score))
        results[name] = result

    full_rho = results["full_SREB"]["spearman"]
    for name, result in results.items():
        result["spearman_delta_vs_full"] = float(result["spearman"] - full_rho)
    return results


def paired_control_court(frame: pd.DataFrame) -> dict[str, Any]:
    controls = frame[frame["control_set"]].copy()
    variants = ["human_edit", "original_headline", "shuffled_edit"]
    metrics = ["S_score", "R_score", "E_score", "B_score", "full_score"]
    summary: dict[str, Any] = {"n_complete_sets": 0, "variant_means": {}, "paired_tests": {}}
    complete_ids = []
    for item_id, group in controls.groupby("id"):
        if set(group["variant"]) == set(variants):
            complete_ids.append(item_id)
    controls = controls[controls["id"].isin(complete_ids)]
    summary["n_complete_sets"] = len(complete_ids)
    for variant in variants:
        block = controls[controls["variant"] == variant]
        summary["variant_means"][variant] = {
            metric: float(block[metric].mean()) for metric in metrics
        }

    for other in ("original_headline", "shuffled_edit"):
        tests = {}
        for metric in metrics:
            pivot = controls.pivot(index="id", columns="variant", values=metric).dropna()
            human_values = pivot["human_edit"].to_numpy(float)
            other_values = pivot[other].to_numpy(float)
            try:
                test = wilcoxon(human_values, other_values, zero_method="zsplit", alternative="greater")
                statistic, pvalue = float(test.statistic), float(test.pvalue)
            except ValueError:
                statistic, pvalue = 0.0, 1.0
            difference = human_values - other_values
            tests[metric] = {
                "mean_human_minus_control": float(np.mean(difference)),
                "median_human_minus_control": float(np.median(difference)),
                "wilcoxon_greater_statistic": statistic,
                "wilcoxon_greater_p": pvalue,
                "wins": int(np.sum(difference > 0)),
                "ties": int(np.sum(difference == 0)),
                "losses": int(np.sum(difference < 0)),
            }
        summary["paired_tests"][f"human_vs_{other}"] = tests
    return summary


def find_source_file(filename: str) -> Path:
    vendored = os.environ.get("HUMORVIBES_SOURCE_DIR")
    if vendored:
        candidate = Path(vendored) / filename
        if candidate.exists():
            return candidate
    hits = [Path(p) for p in glob.glob(f"/kaggle/input/**/{filename}", recursive=True)]
    if not hits:
        raise FileNotFoundError(f"Attached source is missing {filename}")
    return hits[0]


def load_provider() -> tuple[Any, dict[str, Any]]:
    mesh_path = find_source_file("mesh_signals.py")
    sys.path.insert(0, str(mesh_path.parent))
    os.environ["GEMMA_PROVIDER"] = "transformers"
    configs = [Path(p) for p in glob.glob("/kaggle/input/**/config.json", recursive=True) if "gemma" in p.lower()]
    if not configs:
        raise FileNotFoundError("Attached Gemma config.json not found")
    model_config = configs[0]
    os.environ["GEMMA_MODEL_PATH"] = str(model_config.parent)
    from mesh_signals import TransformersProvider

    provider = TransformersProvider(str(model_config.parent))
    import torch

    config_json = json.loads(model_config.read_text(encoding="utf-8"))
    model_name = str(config_json.get("_name_or_path") or config_json.get("model_type") or "unknown")
    evidence = {
        "provider_class": type(provider).__name__,
        "provider_name": provider.name,
        "model_source": MODEL_SOURCE,
        "model_config_path": str(model_config),
        "model_config_sha256": sha256_file(model_config),
        "model_config_name": model_name,
        "parameter_count": int(sum(parameter.numel() for parameter in provider.model.parameters())),
        "device": str(next(provider.model.parameters()).device),
        "dtype": str(next(provider.model.parameters()).dtype),
        "torch_version": torch.__version__,
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "mesh_signals_path": str(mesh_path),
        "mesh_signals_sha256": sha256_file(mesh_path),
        "humor_mesh_sha256": sha256_file(mesh_path.parent / "humor_mesh.py"),
        "source_delivery": "self_contained_notebook_vendor",
        "true_teacher_forced_logprobs": True,
    }
    if provider.name != "transformers":
        raise RuntimeError("Exact Gemma logprob provider was not engaged")
    return provider, evidence


def load_humicroedit() -> tuple[pd.DataFrame, dict[str, Any]]:
    request = urllib.request.Request(DATA_URL, headers={"User-Agent": "HumorVibes ablation research"})
    raw = urllib.request.urlopen(request, timeout=120).read()
    archive_sha = sha256_bytes(raw)
    archive = zipfile.ZipFile(io.BytesIO(raw))
    member = "data/task-1/train.csv"
    csv_bytes = archive.read(member)
    data = pd.read_csv(io.BytesIO(csv_bytes)).dropna(subset=["meanGrade"])
    sampled = data.sample(N_HUMAN, random_state=SEED).reset_index(drop=True)
    sampled["id"] = sampled["id"].astype(str)
    sampled["original_word"] = sampled["original"].map(original_word)
    sampled["human_text"] = [apply_edit(original, edit) for original, edit in zip(sampled["original"], sampled["edit"])]
    sampled["original_text"] = [apply_edit(original, word) for original, word in zip(sampled["original"], sampled["original_word"])]
    control_positions = np.linspace(0, len(sampled) - 1, N_CONTROL, dtype=int)
    sampled["control_set"] = False
    sampled.loc[control_positions, "control_set"] = True
    control_edits = sampled.loc[control_positions, "edit"].astype(str).tolist()
    rotated = control_edits[7:] + control_edits[:7]
    shuffled_by_id = dict(zip(sampled.loc[control_positions, "id"], rotated))
    sampled["shuffled_text"] = [
        apply_edit(original, shuffled_by_id.get(item_id, edit))
        for original, item_id, edit in zip(sampled["original"], sampled["id"], sampled["edit"])
    ]
    evidence = {
        "url": DATA_URL,
        "archive_sha256": archive_sha,
        "csv_member": member,
        "csv_sha256": sha256_bytes(csv_bytes),
        "source_rows": int(len(data)),
        "human_sample_rows": int(len(sampled)),
        "control_set_rows": int(sampled["control_set"].sum()),
        "sample_id_sha256": sha256_bytes("\n".join(sampled["id"]).encode("utf-8")),
        "sampling_seed": SEED,
    }
    return sampled, evidence


def measurement_jobs(sampled: pd.DataFrame) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for _, row in sampled.iterrows():
        base = {
            "id": str(row["id"]),
            "grade": float(row["meanGrade"]),
            "original": str(row["original"]),
            "edit": str(row["edit"]),
            "control_set": bool(row["control_set"]),
        }
        jobs.append({**base, "variant": "human_edit", "text": str(row["human_text"])})
        if row["control_set"]:
            jobs.append({**base, "variant": "original_headline", "text": str(row["original_text"])})
            jobs.append({**base, "variant": "shuffled_edit", "text": str(row["shuffled_text"])})
    return jobs


def measure_jobs(provider: Any, jobs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, float]]:
    from mesh_signals import compute_signals, split_setup_punchline
    import torch

    output: list[dict[str, Any]] = []
    variant_seconds: dict[str, float] = {}
    start = time.perf_counter()
    for index, job in enumerate(jobs):
        item_start = time.perf_counter()
        local_seed = SEED + index
        random.seed(local_seed)
        np.random.seed(local_seed % (2**32 - 1))
        torch.manual_seed(local_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(local_seed)
        setup, punchline = split_setup_punchline(job["text"])
        try:
            signal = compute_signals(provider, setup, punchline, personas=[PERSONA])
            if not signal.measured or signal.profile is None or not signal.profile.measured:
                raise RuntimeError("Gemma teacher-forced logprobs were not measured")
            persona_measured = bool(signal.personas and signal.personas[0].measured)
            record = {
                **job,
                "setup": setup,
                "punchline": punchline,
                "frame_hint": signal.frame_hint,
                "surprise_mean": signal.surprise_mean,
                "resolution": signal.resolution,
                "efficiency": signal.efficiency,
                "bad_surprise": signal.bad_surprise,
                "S_score": signal.surprise_score,
                "R_score": signal.resolution_score,
                "E_score": signal.efficiency_score,
                "B_score": signal.benign_score,
                "full_score": signal.laugh_score,
                "failure_mode": signal.failure_mode,
                "gemma_logprobs_measured": True,
                "bad_surprise_measured": persona_measured,
                "persona": PERSONA,
                "persona_note": signal.personas[0].note if signal.personas else "",
                "seed": local_seed,
                "seconds": time.perf_counter() - item_start,
                "error": None,
            }
        except Exception as exc:
            record = {
                **job,
                "setup": setup,
                "punchline": punchline,
                "seed": local_seed,
                "seconds": time.perf_counter() - item_start,
                "error": f"{type(exc).__name__}: {exc}",
            }
        output.append(record)
        variant_seconds[job["variant"]] = variant_seconds.get(job["variant"], 0.0) + float(record["seconds"])
        with Path("ablation_rows.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        if (index + 1) % 20 == 0 or index + 1 == len(jobs):
            print(f"measured {index + 1}/{len(jobs)} jobs in {time.perf_counter() - start:.1f}s", flush=True)
    return output, variant_seconds


def select_failure_cases(frame: pd.DataFrame) -> pd.DataFrame:
    human = frame[frame["variant"] == "human_edit"].copy()
    human["human_rank"] = human["grade"].rank(method="average", pct=True)
    human["model_rank"] = human["full_score"].rank(method="average", pct=True)
    human["rank_error"] = human["model_rank"] - human["human_rank"]
    false_positive = human.nlargest(3, "rank_error").assign(case_type="model_high_human_low")
    false_negative = human.nsmallest(3, "rank_error").assign(case_type="model_low_human_high")
    shuffled = frame[frame["variant"] == "shuffled_edit"].nlargest(2, "full_score").assign(case_type="shuffled_control_false_positive")
    bad_surprise = human.nlargest(2, "bad_surprise").assign(case_type="highest_bad_surprise_risk")
    selected = pd.concat([false_positive, false_negative, shuffled, bad_surprise], ignore_index=True)
    columns = [
        "case_type", "id", "variant", "grade", "text", "surprise_mean", "resolution",
        "efficiency", "bad_surprise", "full_score", "failure_mode", "frame_hint", "persona_note",
    ]
    return selected[columns]


def failure_markdown(failures: pd.DataFrame) -> str:
    columns = list(failures.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in failures.iterrows():
        values = []
        for column in columns:
            value = str(row[column]).replace("\n", " ").replace("|", "\\|")
            values.append(value)
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def make_figure(human: pd.DataFrame, ablation: dict[str, Any], controls: dict[str, Any], failures: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes[0, 0].scatter(human["full_score"], human["grade"], alpha=0.6, s=28, color="#5B5BD6")
    axes[0, 0].set(xlabel="fixed S/R/E/B score", ylabel="human meanGrade", title="Human validation")

    names = ["full_SREB", "without_S", "without_R", "without_E", "without_B", "only_S", "only_R", "only_E", "only_B"]
    rhos = [ablation[name]["spearman"] for name in names]
    colors = ["#1F9D8A" if name == "full_SREB" else "#8FA3BF" for name in names]
    axes[0, 1].barh(names[::-1], rhos[::-1], color=colors[::-1])
    axes[0, 1].axvline(0, color="black", linewidth=0.8)
    axes[0, 1].set(xlabel="Spearman rho", title="Predeclared component ablation")

    variants = ["human_edit", "original_headline", "shuffled_edit"]
    means = [controls["variant_means"][variant]["full_score"] for variant in variants]
    axes[1, 0].bar(["human edit", "original", "shuffled"], means, color=["#1F9D8A", "#C6CBD3", "#E07A5F"])
    axes[1, 0].set(ylabel="mean fixed score", title=f"Paired controls (n={controls['n_complete_sets']})")

    table_rows = []
    for _, row in failures.head(5).iterrows():
        text = str(row["text"]).replace("\n", " ")
        table_rows.append([row["case_type"][:18], f"{row['grade']:.1f}", f"{row['full_score']:.1f}", text[:48]])
    axes[1, 1].axis("off")
    table = axes[1, 1].table(cellText=table_rows, colLabels=["case", "human", "model", "text"], loc="center", cellLoc="left")
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.5)
    axes[1, 1].set_title("Failure cases (not hidden)")

    fig.suptitle("HumorVibes S/R/E/B validation and failure court", fontsize=16)
    fig.tight_layout()
    fig.savefig("ablation_failure_figure.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    started_utc = utc_now()
    wall_start = time.perf_counter()
    Path("ablation_rows.jsonl").unlink(missing_ok=True)
    random.seed(SEED)
    np.random.seed(SEED)

    provider, model_evidence = load_provider()
    print("Gemma evidence:", json.dumps(model_evidence, indent=2), flush=True)
    sampled, data_evidence = load_humicroedit()
    jobs = measurement_jobs(sampled)
    print(f"measurement jobs: {len(jobs)} ({N_HUMAN} human + {2 * N_CONTROL} paired controls)", flush=True)
    rows, variant_seconds = measure_jobs(provider, jobs)
    frame = pd.DataFrame(rows)
    successful = frame[frame["error"].isna()].copy()
    completion_rate = len(successful) / len(frame)
    if completion_rate < 0.95:
        raise RuntimeError(f"Measurement completion rate {completion_rate:.3f} is below 0.95")
    human = successful[successful["variant"] == "human_edit"].copy()
    if len(human) < int(0.95 * N_HUMAN):
        raise RuntimeError("Human-grade measurement coverage is below 95%")

    ablation = component_ablation(human)
    controls = paired_control_court(successful)
    failures = select_failure_cases(successful)
    failures.to_csv("failure_cases.csv", index=False)
    Path("failure_cases.md").write_text(failure_markdown(failures), encoding="utf-8")
    make_figure(human, ablation, controls, failures)

    bad_surprise_coverage = float(human["bad_surprise_measured"].mean())
    summary = {
        "schema": "humorvibes_ablation_v1",
        "status": "complete",
        "external_submission_made": False,
        "sample": {
            "human_rows": int(len(human)),
            "control_sets": int(controls["n_complete_sets"]),
            "measurement_jobs": int(len(frame)),
            "successful_jobs": int(len(successful)),
            "completion_rate": completion_rate,
            "bad_surprise_judge_coverage_on_human": bad_surprise_coverage,
        },
        "metric": {
            "fixed_weights": WEIGHTS,
            "bad_surprise_persona": PERSONA,
            "ablation": ablation,
        },
        "paired_controls": controls,
        "failure_case_count": int(len(failures)),
        "limitations": [
            "Humicroedit headlines are not setup/punchline jokes; edit position often falls outside the inferred punchline span.",
            "Human grades are not persona-specific, while B is measured for one declared broad-news persona.",
            "This is one deterministic sample and one Gemma instrument; confidence intervals quantify item sampling, not model-family uncertainty.",
        ],
    }
    json_dump("ablation_summary.json", summary)

    finished_utc = utc_now()
    runtime = {
        "schema": "humorvibes_runtime_receipt_v1",
        "status": "complete",
        "kernel_id": KERNEL_ID,
        "kernel_private_at_run": True,
        "external_submission_made": False,
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "wall_seconds": time.perf_counter() - wall_start,
        "variant_seconds": variant_seconds,
        "seconds_per_successful_job": (time.perf_counter() - wall_start) / len(successful),
        "seed": SEED,
        "bootstrap_rounds": BOOTSTRAPS,
        "model": model_evidence,
        "data": data_evidence,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "outputs": {},
        "reproduction": "Run the private Kaggle notebook humorvibes-ablation-court; it vendors the hashed signal source and attaches the pinned Gemma model source.",
    }
    for output in ("ablation_rows.jsonl", "ablation_summary.json", "failure_cases.csv", "failure_cases.md", "ablation_failure_figure.png"):
        runtime["outputs"][output] = {"bytes": Path(output).stat().st_size, "sha256": sha256_file(output)}
    json_dump("runtime_receipt.json", runtime)

    print("\n=== ABLATION ===")
    for name, result in ablation.items():
        print(f"{name:14s} rho={result['spearman']:+.4f} 95%CI={result['spearman_bootstrap_95ci']}")
    print("\n=== PAIRED CONTROLS ===")
    print(json.dumps(controls, indent=2))
    print("\n=== RUNTIME ===")
    print(json.dumps(runtime, indent=2))


if __name__ == "__main__":
    main()

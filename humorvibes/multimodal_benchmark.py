"""Rights-safe multimodal benchmark contracts for caption-plus-drawing research.

The bundled fixture is deliberately procedural and synthetic.  It proves that grouped
splits, image identity checks, three comparable feature arms, metrics, and receipts work;
it does not measure whether any caption or model is funny to people.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from .errors import IntegrationError


BENCHMARK_VERSION = "1.0.0"
LICENSE_SPDX = "CC0-1.0"
ARM_NAMES = ("text_only", "image_only", "fusion")
STRATEGIES = ("literal", "incongruous", "compact_repair", "overexplained")
RELATIONS = ("apart", "touching", "stacked", "crossed", "inside")
SHAPES = ("circle", "square", "triangle", "diamond", "hexagon", "star")
COLORS = (
    "#2457a7",
    "#d34a38",
    "#18876b",
    "#8b4db8",
    "#d58b18",
    "#156f91",
    "#a63d70",
    "#527a2c",
)


def _error(code: str, message: str, *, detail: dict[str, Any] | None = None) -> IntegrationError:
    return IntegrationError(code, message, 422, detail=detail)


def _canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _split(index: int) -> str:
    bucket = index % 10
    if bucket == 0:
        return "test"
    if bucket == 1:
        return "validation"
    return "train"


def _scene(index: int) -> dict[str, Any]:
    primary = SHAPES[index % len(SHAPES)]
    secondary = SHAPES[(index * 5 + 1) % len(SHAPES)]
    if secondary == primary:
        secondary = SHAPES[(SHAPES.index(secondary) + 1) % len(SHAPES)]
    return {
        "primary_shape": primary,
        "secondary_shape": secondary,
        "primary_color": COLORS[index % len(COLORS)],
        "secondary_color": COLORS[(index * 3 + 2) % len(COLORS)],
        "relation": RELATIONS[index % len(RELATIONS)],
        "x_offset": 18 + (index * 17) % 73,
        "y_offset": 14 + (index * 23) % 61,
        "stroke_width": 3 + index % 4,
    }


def _shape_svg(shape: str, *, x: int, y: int, color: str, stroke_width: int) -> str:
    common = f'fill="{color}" stroke="#17202a" stroke-width="{stroke_width}"'
    if shape == "circle":
        return f'<circle cx="{x}" cy="{y}" r="28" {common}/>'
    if shape == "square":
        return f'<rect x="{x - 27}" y="{y - 27}" width="54" height="54" rx="4" {common}/>'
    if shape == "triangle":
        return f'<polygon points="{x},{y - 32} {x - 30},{y + 27} {x + 30},{y + 27}" {common}/>'
    if shape == "diamond":
        return f'<polygon points="{x},{y - 32} {x - 31},{y} {x},{y + 32} {x + 31},{y}" {common}/>'
    if shape == "hexagon":
        return f'<polygon points="{x - 27},{y - 16} {x},{y - 31} {x + 27},{y - 16} {x + 27},{y + 16} {x},{y + 31} {x - 27},{y + 16}" {common}/>'
    if shape == "star":
        points = []
        for point in range(10):
            angle = -math.pi / 2 + point * math.pi / 5
            radius = 31 if point % 2 == 0 else 13
            points.append(f"{x + radius * math.cos(angle):.1f},{y + radius * math.sin(angle):.1f}")
        return f'<polygon points="{" ".join(points)}" {common}/>'
    raise _error("unknown_procedural_shape", "The fixture requested an unknown SVG shape.")


def _positions(scene: dict[str, Any]) -> tuple[tuple[int, int], tuple[int, int]]:
    x = int(scene["x_offset"])
    y = int(scene["y_offset"])
    relation = scene["relation"]
    if relation == "apart":
        return (75 + x // 4, 105 + y // 5), (245 - x // 5, 105 - y // 6)
    if relation == "touching":
        return (132 + x // 8, 105), (188 + x // 8, 105)
    if relation == "stacked":
        return (160, 70 + y // 8), (160, 135 + y // 8)
    if relation == "crossed":
        return (130 + x // 9, 88 + y // 10), (190 - x // 10, 126 - y // 12)
    return (160, 105), (160, 105)


def _svg(scene: dict[str, Any]) -> str:
    first, second = _positions(scene)
    primary = _shape_svg(
        str(scene["primary_shape"]),
        x=first[0],
        y=first[1],
        color=str(scene["primary_color"]),
        stroke_width=int(scene["stroke_width"]),
    )
    secondary = _shape_svg(
        str(scene["secondary_shape"]),
        x=second[0],
        y=second[1],
        color=str(scene["secondary_color"]),
        stroke_width=int(scene["stroke_width"]),
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="210" '
        'viewBox="0 0 320 210" role="img">\n'
        '  <rect width="320" height="210" fill="#f7f3e8"/>\n'
        '  <path d="M20 174 H300" stroke="#54606a" stroke-width="2"/>\n'
        f"  {primary}\n  {secondary}\n"
        '</svg>\n'
    )


def _caption_text(scene: dict[str, Any], strategy: str, variant: int) -> str:
    primary = str(scene["primary_shape"])
    secondary = str(scene["secondary_shape"])
    relation = str(scene["relation"])
    if variant == 0:
        repeated = {
            "literal": "Two figures wait for the meeting to begin.",
            "incongruous": "One of us has seriously misunderstood the dress code.",
            "compact_repair": "They called it networking until the connection became literal.",
            "overexplained": "This is amusing because their arrangement has two possible meanings.",
        }
        return repeated[strategy]
    templates = {
        "literal": (
            "The {primary} stands {relation} the {secondary}.",
            "A {primary} and a {secondary} occupy the same quiet scene.",
            "The diagram shows a {primary}, a {secondary}, and no emergency.",
            "Both shapes remain exactly where the illustrator placed them.",
        ),
        "incongruous": (
            "The {secondary} insists this is a {primary}-only event.",
            "Apparently the geometry department has a casual Friday.",
            "Neither shape remembers approving this seating chart.",
            "The {primary} would like to speak to whoever defined personal space.",
        ),
        "compact_repair": (
            "The {primary} wanted distance; the diagram took that {relation}.",
            "Their relationship status is now literally {relation}.",
            "The {secondary} asked for closure, so the {primary} drew a line.",
            "It was a shape-up meeting, and both sides took the agenda literally.",
        ),
        "overexplained": (
            "The {primary} made a geometry joke about being {relation}, which explains the scene.",
            "They are shapes and also colleagues, so the spatial relation is a metaphor.",
            "The joke is that {relation} describes both placement and their working relationship.",
            "Notice how the {secondary} creates a second interpretation for the {primary}.",
        ),
    }
    return templates[strategy][variant - 1].format(
        primary=primary, secondary=secondary, relation=relation
    )


def _feature_contract() -> dict[str, list[str]]:
    text = ["word_count_scaled", "question_mark", "exclamation_mark"]
    text.extend(f"strategy={value}" for value in STRATEGIES)
    text.extend(f"variant={value}" for value in range(5))
    image = [f"relation={value}" for value in RELATIONS]
    image.extend(f"primary_shape={value}" for value in SHAPES)
    image.append("x_offset_scaled")
    interaction = [
        f"strategy={strategy}*relation={relation}"
        for strategy in STRATEGIES
        for relation in RELATIONS
    ]
    return {"text_only": text, "image_only": image, "fusion": [*text, *image, *interaction]}


def _features(scene: dict[str, Any], strategy: str, variant: int, text: str) -> dict[str, list[float]]:
    text_values = [
        len(text.split()) / 20.0,
        float("?" in text),
        float("!" in text),
        *[float(strategy == value) for value in STRATEGIES],
        *[float(variant == value) for value in range(5)],
    ]
    relation = str(scene["relation"])
    primary = str(scene["primary_shape"])
    image_values = [
        *[float(relation == value) for value in RELATIONS],
        *[float(primary == value) for value in SHAPES],
        float(scene["x_offset"]) / 100.0,
    ]
    interactions = [
        float(strategy == strategy_value and relation == relation_value)
        for strategy_value in STRATEGIES
        for relation_value in RELATIONS
    ]
    return {
        "text_only": text_values,
        "image_only": image_values,
        "fusion": [*text_values, *image_values, *interactions],
    }


def _target(contest_id: str, scene: dict[str, Any], strategy: str, variant: int) -> float:
    base = {
        "literal": 0.28,
        "incongruous": 0.53,
        "compact_repair": 0.62,
        "overexplained": 0.39,
    }[strategy]
    relation_index = RELATIONS.index(str(scene["relation"]))
    strategy_index = STRATEGIES.index(strategy)
    interaction = (
        (strategy_index + 2) * (relation_index + 3) % 9 - 4
    ) * 0.038
    variant_effect = (-0.045, 0.025, 0.055, -0.015, 0.035)[variant]
    digest = hashlib.sha256(
        f"{BENCHMARK_VERSION}|{contest_id}|{strategy}|{variant}".encode("utf-8")
    ).digest()
    deterministic_noise = (int.from_bytes(digest[:2], "big") / 65535.0 - 0.5) * 0.035
    return round(min(0.98, max(0.02, base + interaction + variant_effect + deterministic_noise)), 6)


def build_synthetic_multimodal_fixture(*, contests: int = 30) -> dict[str, Any]:
    """Build a deterministic procedural SVG and caption fixture in memory."""

    if contests < 20 or contests > 60:
        raise _error("invalid_contest_count", "Synthetic fixtures require 20 through 60 contests.")
    feature_names = _feature_contract()
    image_rows: list[dict[str, Any]] = []
    caption_rows: list[dict[str, Any]] = []
    image_payloads: dict[str, str] = {}
    seen_scene_signatures: set[str] = set()
    for index in range(contests):
        contest_id = f"procedural-contest-{index + 1:03d}"
        split = _split(index)
        scene = _scene(index)
        signature = _canonical_digest(scene)
        if signature in seen_scene_signatures:
            raise _error("procedural_scene_collision", "Procedural scene signatures must be unique.")
        seen_scene_signatures.add(signature)
        svg = _svg(scene)
        image_path = f"images/{contest_id}.svg"
        image_payloads[image_path] = svg
        image_rows.append(
            {
                "contest_id": contest_id,
                "split": split,
                "image_path": image_path,
                "image_sha256": _sha256_bytes(svg.encode("utf-8")),
                "perceptual_signature": signature,
                "width": 320,
                "height": 210,
                "mime_type": "image/svg+xml",
                "origin": "deterministic_procedural_svg",
                "license_spdx": LICENSE_SPDX,
                "scene": scene,
            }
        )
        for strategy in STRATEGIES:
            for variant in range(5):
                text = _caption_text(scene, strategy, variant)
                row_id = hashlib.sha256(
                    f"{BENCHMARK_VERSION}|{contest_id}|{strategy}|{variant}".encode("utf-8")
                ).hexdigest()[:20]
                caption_rows.append(
                    {
                        "row_id": f"mm_{row_id}",
                        "contest_id": contest_id,
                        "split": split,
                        "caption": text,
                        "strategy": strategy,
                        "variant": variant,
                        "vote_count": 24 + int(row_id[:4], 16) % 177,
                        "repeated_caption": variant == 0,
                        "target": _target(contest_id, scene, strategy, variant),
                        "target_origin": "deterministic_synthetic_contract",
                        "features": _features(scene, strategy, variant, text),
                    }
                )
    split_counts = Counter(row["split"] for row in image_rows)
    if not all(split_counts.get(value, 0) >= 2 for value in ("train", "validation", "test")):
        raise _error("insufficient_grouped_splits", "Each grouped split needs at least two contests.")
    manifest = {
        "receipt_type": "humorvibes_multimodal_fixture_manifest",
        "receipt_version": 1,
        "benchmark_version": BENCHMARK_VERSION,
        "data_origin": "deterministic_procedural_synthetic_fixture",
        "license_spdx": LICENSE_SPDX,
        "counts": {
            "contests": len(image_rows),
            "captions": len(caption_rows),
            "captions_per_contest": len(STRATEGIES) * 5,
        },
        "contest_splits": dict(sorted(split_counts.items())),
        "feature_names": feature_names,
        "images": image_rows,
        "evaluation_contract": {
            "grouping_unit": "contest_id",
            "arms": list(ARM_NAMES),
            "primary_metric": "median within-contest Spearman on the held-out test split",
            "uncertainty": "deterministic percentile bootstrap over held-out contests",
            "same_rows_for_every_arm": True,
            "real_caption_label_ceiling": 0.8262,
            "real_caption_text_only_bound": 0.4110,
            "text_only_bound_applies_to": ["text_only"],
            "real_bounds_apply_to_this_synthetic_fixture": False,
        },
        "truth_boundary": {
            "human_authored_captions": 0,
            "human_ratings": 0,
            "copyrighted_cartoon_images": 0,
            "claim_ready_for_multimodal_humor": False,
            "allowed_claim": "the multimodal experiment and leakage contracts execute on rights-safe synthetic inputs",
        },
    }
    manifest["content_digest"] = _canonical_digest(
        {"images": image_rows, "captions": caption_rows}
    )
    return {"manifest": manifest, "captions": caption_rows, "image_payloads": image_payloads}


def _jsonl(rows: Iterable[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in rows
    )


def write_multimodal_fixture(
    root: Path, fixture: dict[str, Any], *, overwrite: bool = False
) -> dict[str, Any]:
    root = Path(root)
    expected = [root / "multimodal_manifest.json", root / "caption_candidates.jsonl"]
    expected.extend(root / path for path in fixture["image_payloads"])
    existing = [path for path in expected if path.exists()]
    if existing and not overwrite:
        raise _error(
            "multimodal_fixture_exists",
            "Refusing to replace an existing fixture without overwrite=True.",
            detail={"existing_files": len(existing)},
        )
    root.mkdir(parents=True, exist_ok=True)
    (root / "images").mkdir(parents=True, exist_ok=True)
    for relative, payload in sorted(fixture["image_payloads"].items()):
        (root / relative).write_text(payload, encoding="utf-8")
    (root / "caption_candidates.jsonl").write_text(
        _jsonl(fixture["captions"]), encoding="utf-8"
    )
    (root / "multimodal_manifest.json").write_text(
        json.dumps(fixture["manifest"], indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return validate_multimodal_fixture(root)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise _error(
                        "invalid_multimodal_jsonl",
                        f"Malformed JSON on line {line_number} of {path.name}.",
                    ) from exc
                if not isinstance(value, dict):
                    raise _error("invalid_multimodal_row", "Every caption row must be an object.")
                rows.append(value)
    return rows


def validate_multimodal_fixture(root: Path) -> dict[str, Any]:
    root = Path(root)
    try:
        manifest = json.loads((root / "multimodal_manifest.json").read_text(encoding="utf-8"))
        captions = _read_jsonl(root / "caption_candidates.jsonl")
    except FileNotFoundError as exc:
        raise _error("missing_multimodal_file", "The multimodal fixture is incomplete.") from exc
    images = manifest.get("images")
    if not isinstance(images, list) or not images or not captions:
        raise _error("invalid_multimodal_manifest", "The fixture requires images and captions.")
    contest_by_id: dict[str, dict[str, Any]] = {}
    image_hashes: dict[str, str] = {}
    signatures: dict[str, str] = {}
    for image in images:
        contest_id = str(image.get("contest_id", ""))
        split = str(image.get("split", ""))
        if not contest_id or contest_id in contest_by_id or split not in {"train", "validation", "test"}:
            raise _error("invalid_multimodal_contest", "Contest IDs must be unique and use known splits.")
        if image.get("license_spdx") != LICENSE_SPDX or image.get("origin") != "deterministic_procedural_svg":
            raise _error("invalid_multimodal_rights", "Every fixture image must be project-controlled CC0 SVG.")
        path = root / str(image.get("image_path", ""))
        try:
            observed = _sha256_bytes(path.read_bytes())
        except FileNotFoundError as exc:
            raise _error("missing_multimodal_image", "A manifested image is missing.") from exc
        if observed != image.get("image_sha256"):
            raise _error("multimodal_image_hash_mismatch", "A manifested image hash does not match.")
        signature = str(image.get("perceptual_signature", ""))
        if observed in image_hashes:
            raise _error(
                "multimodal_exact_image_leakage",
                "An exact image duplicate crosses contest groups.",
                detail={"first": image_hashes[observed], "second": contest_id},
            )
        if not signature or signature in signatures:
            raise _error(
                "multimodal_near_duplicate_leakage",
                "A canonical scene signature crosses contest groups.",
                detail={"first": signatures.get(signature), "second": contest_id},
            )
        image_hashes[observed] = contest_id
        signatures[signature] = contest_id
        contest_by_id[contest_id] = image
    feature_names = manifest.get("feature_names", {})
    row_ids: set[str] = set()
    for row in captions:
        row_id = str(row.get("row_id", ""))
        contest = contest_by_id.get(str(row.get("contest_id", "")))
        if not row_id or row_id in row_ids or contest is None:
            raise _error("invalid_multimodal_row", "Caption rows need unique IDs and known contests.")
        row_ids.add(row_id)
        if row.get("split") != contest.get("split"):
            raise _error("multimodal_group_split_leakage", "A caption split disagrees with its contest split.")
        if row.get("target_origin") != "deterministic_synthetic_contract":
            raise _error("invalid_multimodal_target", "Fixture targets must remain explicitly synthetic.")
        target = row.get("target")
        if isinstance(target, bool) or not isinstance(target, (int, float)) or not math.isfinite(target):
            raise _error("invalid_multimodal_target", "Every fixture target must be finite numeric data.")
        features = row.get("features")
        if not isinstance(features, dict):
            raise _error("invalid_multimodal_features", "Every row requires all feature arms.")
        for arm in ARM_NAMES:
            vector = features.get(arm)
            names = feature_names.get(arm)
            if not isinstance(vector, list) or not isinstance(names, list) or len(vector) != len(names):
                raise _error("invalid_multimodal_features", "Feature vectors must match the manifest contract.")
            if any(
                isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
                for value in vector
            ):
                raise _error("invalid_multimodal_features", "Feature vectors must contain finite numbers.")
    observed_digest = _canonical_digest({"images": images, "captions": captions})
    if observed_digest != manifest.get("content_digest"):
        raise _error("multimodal_content_digest_mismatch", "Fixture content does not match its digest.")
    contest_splits = {contest_id: row["split"] for contest_id, row in contest_by_id.items()}
    split_crossing = any(
        len({row["split"] for row in captions if row["contest_id"] == contest_id}) != 1
        for contest_id in contest_splits
    )
    return {
        "ok": True,
        "contests": len(contest_by_id),
        "captions": len(captions),
        "image_hashes_verified": len(image_hashes),
        "exact_image_duplicates": 0,
        "near_duplicate_scene_signatures": 0,
        "contest_group_split_crossings": int(split_crossing),
        "content_digest": observed_digest,
    }


def _solve_linear(features: list[list[float]], targets: list[float], ridge: float = 1e-4) -> list[float]:
    if not features or len(features) != len(targets):
        raise _error("invalid_multimodal_training_data", "Training features and targets must align.")
    width = len(features[0]) + 1
    matrix = [[0.0] * width for _ in range(width)]
    vector = [0.0] * width
    for row, target in zip(features, targets, strict=True):
        if len(row) + 1 != width:
            raise _error("multimodal_feature_dimension_drift", "Feature dimensions changed between rows.")
        augmented = [1.0, *row]
        for left in range(width):
            vector[left] += augmented[left] * target
            for right in range(width):
                matrix[left][right] += augmented[left] * augmented[right]
    for index in range(1, width):
        matrix[index][index] += ridge
    for pivot in range(width):
        candidate = max(range(pivot, width), key=lambda row: abs(matrix[row][pivot]))
        if abs(matrix[candidate][pivot]) < 1e-12:
            raise _error("multimodal_singular_model", "The ridge system could not be solved.")
        matrix[pivot], matrix[candidate] = matrix[candidate], matrix[pivot]
        vector[pivot], vector[candidate] = vector[candidate], vector[pivot]
        scale = matrix[pivot][pivot]
        matrix[pivot] = [value / scale for value in matrix[pivot]]
        vector[pivot] /= scale
        for row in range(width):
            if row == pivot:
                continue
            factor = matrix[row][pivot]
            if factor == 0:
                continue
            matrix[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(matrix[row], matrix[pivot], strict=True)
            ]
            vector[row] -= factor * vector[pivot]
    return vector


def _predict(weights: list[float], features: list[float]) -> float:
    return weights[0] + sum(
        weight * value for weight, value in zip(weights[1:], features, strict=True)
    )


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        average = (start + 1 + end) / 2.0
        for position in range(start, end):
            ranks[order[position]] = average
        start = end
    return ranks


def _spearman(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0
    a = _ranks(left)
    b = _ranks(right)
    mean_a = sum(a) / len(a)
    mean_b = sum(b) / len(b)
    numerator = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b, strict=True))
    denominator = math.sqrt(
        sum((x - mean_a) ** 2 for x in a) * sum((y - mean_b) ** 2 for y in b)
    )
    return numerator / denominator if denominator else 0.0


def _bootstrap_ci(values: list[float], *, samples: int = 2000) -> list[float]:
    if not values:
        return [0.0, 0.0]
    rng = random.Random(20_260_727)
    draws = sorted(
        median([values[rng.randrange(len(values))] for _ in values]) for _ in range(samples)
    )
    return [draws[int(samples * 0.025)], draws[min(samples - 1, int(samples * 0.975))]]


def _metrics(rows: list[dict[str, Any]], predictions: list[float]) -> dict[str, Any]:
    by_contest: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        by_contest[str(row["contest_id"])].append(index)
    contest_rhos = []
    for indices in by_contest.values():
        contest_rhos.append(
            _spearman(
                [predictions[index] for index in indices],
                [float(rows[index]["target"]) for index in indices],
            )
        )
    targets = [float(row["target"]) for row in rows]
    return {
        "rows": len(rows),
        "contests": len(by_contest),
        "median_within_contest_spearman": median(contest_rhos),
        "contest_bootstrap_95pct_ci": _bootstrap_ci(contest_rhos),
        "pooled_spearman": _spearman(predictions, targets),
        "mean_absolute_error": sum(abs(predicted - target) for predicted, target in zip(predictions, targets, strict=True)) / len(rows),
    }


def _slices(rows: list[dict[str, Any]], predictions: list[float]) -> dict[str, Any]:
    definitions: dict[str, list[Any]] = {
        "strategy": [row["strategy"] for row in rows],
        "vote_count_band": [
            "24-79" if row["vote_count"] < 80 else "80-139" if row["vote_count"] < 140 else "140-200"
            for row in rows
        ],
        "repeated_caption": [str(bool(row["repeated_caption"])).lower() for row in rows],
    }
    result: dict[str, Any] = {}
    for name, values in definitions.items():
        groups: dict[str, list[int]] = defaultdict(list)
        for index, value in enumerate(values):
            groups[str(value)].append(index)
        result[name] = {
            key: {
                "rows": len(indices),
                "pooled_spearman": _spearman(
                    [predictions[index] for index in indices],
                    [float(rows[index]["target"]) for index in indices],
                ),
                "mean_absolute_error": sum(
                    abs(predictions[index] - float(rows[index]["target"])) for index in indices
                ) / len(indices),
            }
            for key, indices in sorted(groups.items())
        }
    return result


def _calibration(rows: list[dict[str, Any]], predictions: list[float]) -> list[dict[str, Any]]:
    order = sorted(range(len(rows)), key=lambda index: (predictions[index], rows[index]["row_id"]))
    bins: list[dict[str, Any]] = []
    for bucket in range(5):
        start = bucket * len(order) // 5
        end = (bucket + 1) * len(order) // 5
        indices = order[start:end]
        bins.append(
            {
                "bin": bucket + 1,
                "rows": len(indices),
                "mean_prediction": sum(predictions[index] for index in indices) / len(indices),
                "mean_target": sum(float(rows[index]["target"]) for index in indices) / len(indices),
            }
        )
    return bins


def evaluate_multimodal_fixture(root: Path) -> dict[str, Any]:
    """Validate and evaluate all three arms against exactly the same held-out rows."""

    validation = validate_multimodal_fixture(root)
    root = Path(root)
    manifest = json.loads((root / "multimodal_manifest.json").read_text(encoding="utf-8"))
    rows = _read_jsonl(root / "caption_candidates.jsonl")
    train = [row for row in rows if row["split"] == "train"]
    test = [row for row in rows if row["split"] == "test"]
    if not train or not test:
        raise _error("missing_multimodal_split", "Training and held-out test rows are required.")
    evaluated_digest = _canonical_digest([row["row_id"] for row in test])
    arms: dict[str, Any] = {}
    for arm in ARM_NAMES:
        weights = _solve_linear(
            [[float(value) for value in row["features"][arm]] for row in train],
            [float(row["target"]) for row in train],
        )
        predictions = [
            _predict(weights, [float(value) for value in row["features"][arm]]) for row in test
        ]
        arms[arm] = {
            "feature_dimensions": len(manifest["feature_names"][arm]),
            "evaluated_row_digest": evaluated_digest,
            "metrics": _metrics(test, predictions),
            "calibration": _calibration(test, predictions),
            "error_slices": _slices(test, predictions),
        }
    if len({value["evaluated_row_digest"] for value in arms.values()}) != 1:
        raise _error("multimodal_arm_row_mismatch", "Every arm must evaluate identical held-out rows.")
    return {
        "receipt_type": "humorvibes_multimodal_benchmark",
        "receipt_version": 1,
        "benchmark_version": BENCHMARK_VERSION,
        "status": "VERIFIED_SYNTHETIC_MULTIMODAL_CONTRACT",
        "fixture_validation": validation,
        "split_counts": dict(sorted(Counter(row["split"] for row in rows).items())),
        "arms": arms,
        "comparability": {
            "identical_held_out_rows": True,
            "evaluated_row_digest": evaluated_digest,
            "grouping_unit": "contest_id",
            "image_only_cannot_rank_captions_within_one_fixed_image": True,
        },
        "real_data_reporting_requirements": manifest["evaluation_contract"],
        "truth_boundary": {
            "data_origin": "deterministic_procedural_synthetic_fixture",
            "human_authored_captions": 0,
            "human_ratings": 0,
            "claim_ready_for_multimodal_humor": False,
            "model_comparison_is_product_evidence": False,
            "allowed_claim": "the same-contest multimodal evaluation, leakage, calibration, slicing, and receipt machinery executes end to end",
        },
    }


def write_benchmark_receipt(root: Path, receipt: dict[str, Any]) -> Path:
    path = Path(root) / "benchmark_receipt.json"
    path.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path

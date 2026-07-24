"""Humor Vibes Open — Track A metric (dependency-free, Kaggle-interface).

Primary score: AUC of `humor_score` separating genuine jokes (is_genuine=1) from
constructed controls (is_genuine=0), computed rank-based with tie handling
(Mann-Whitney U / (n1*n0)). Secondary diagnostic (reported, not the leaderboard
number): matched-pair accuracy on (genuine, shuffled-control-of-same-setup) pairs.

Kaggle usage: `score(solution_df, submission_df, row_id_column_name="id")` where
solution carries columns [id, is_genuine, control_type, setup_key, Usage] and the
submission carries [id, humor_score]. Works on plain lists of dicts too, so it has
no pandas requirement here; on Kaggle, DataFrames expose the same row dicts via
`.to_dict("records")` (a shim at the bottom handles both).
"""
from __future__ import annotations

from typing import Any


class ParticipantVisibleError(Exception):
    """Raised for submission problems the participant should see."""


def _rows(obj: Any) -> list[dict[str, Any]]:
    if hasattr(obj, "to_dict"):
        return obj.to_dict("records")
    return list(obj)


def _auc(pos: list[float], neg: list[float]) -> float:
    """Rank-based AUC with tie correction; no numpy."""
    if not pos or not neg:
        raise ParticipantVisibleError("scored split has an empty class")
    combined = sorted((v, 1) for v in pos)
    combined += sorted((v, 0) for v in neg)
    combined.sort(key=lambda t: t[0])
    # average ranks with ties
    ranks: dict[int, float] = {}
    i = 0
    rank_sum_pos = 0.0
    values = [v for v, _ in combined]
    while i < len(combined):
        j = i
        while j < len(combined) and values[j] == values[i]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0          # ranks are 1-based
        for k in range(i, j):
            if combined[k][1] == 1:
                rank_sum_pos += avg_rank
        i = j
    n1, n0 = len(pos), len(neg)
    u = rank_sum_pos - n1 * (n1 + 1) / 2.0
    return u / (n1 * n0)


def score(solution: Any, submission: Any, row_id_column_name: str = "id") -> float:
    sol = _rows(solution)
    sub = _rows(submission)
    scores: dict[Any, float] = {}
    for row in sub:
        if row_id_column_name not in row or "humor_score" not in row:
            raise ParticipantVisibleError(
                f"submission needs columns [{row_id_column_name}, humor_score]")
        try:
            val = float(row["humor_score"])
        except (TypeError, ValueError):
            raise ParticipantVisibleError(
                f"non-numeric humor_score at {row_id_column_name}={row[row_id_column_name]!r}")
        if val != val or val in (float("inf"), float("-inf")):
            raise ParticipantVisibleError(
                f"non-finite humor_score at {row_id_column_name}={row[row_id_column_name]!r}")
        if row[row_id_column_name] in scores:
            raise ParticipantVisibleError(
                f"duplicate id in submission: {row[row_id_column_name]!r}")
        scores[row[row_id_column_name]] = val
    missing = [r[row_id_column_name] for r in sol if r[row_id_column_name] not in scores]
    if missing:
        raise ParticipantVisibleError(
            f"submission missing {len(missing)} ids (first: {missing[:3]})")
    pos = [scores[r[row_id_column_name]] for r in sol if int(r["is_genuine"]) == 1]
    neg = [scores[r[row_id_column_name]] for r in sol if int(r["is_genuine"]) == 0]
    return round(_auc(pos, neg), 6)


def matched_pair_accuracy(solution: Any, submission: Any,
                          row_id_column_name: str = "id") -> float:
    """Diagnostic: does the genuine punchline outscore the shuffled one for the
    SAME setup? Pairs are matched via solution's setup_key."""
    sol = _rows(solution)
    sub = {r[row_id_column_name]: float(r["humor_score"]) for r in _rows(submission)}
    genuine: dict[str, list[float]] = {}
    shuffled: dict[str, list[float]] = {}
    for r in sol:
        key = r.get("setup_key", "")
        if not key or r[row_id_column_name] not in sub:
            continue
        if int(r["is_genuine"]) == 1:
            genuine.setdefault(key, []).append(sub[r[row_id_column_name]])
        elif r.get("control_type") == "shuffled":
            shuffled.setdefault(key, []).append(sub[r[row_id_column_name]])
    # aggregate per key so a setup_key collision can never drop a real pair
    # or make the diagnostic depend on row order
    pairs = [(sum(genuine[k]) / len(genuine[k]), sum(shuffled[k]) / len(shuffled[k]))
             for k in sorted(genuine) if k in shuffled]
    if not pairs:
        return float("nan")
    wins = sum(1 for g, s in pairs if g > s) + 0.5 * sum(1 for g, s in pairs if g == s)
    return round(wins / len(pairs), 6)


if __name__ == "__main__":
    # self-test: perfect, random, and inverted submissions behave as AUC must
    import random

    rng = random.Random(7)
    sol = ([{"id": f"g{i}", "is_genuine": 1, "control_type": "", "setup_key": f"s{i}"}
            for i in range(50)]
           + [{"id": f"c{i}", "is_genuine": 0, "control_type": "shuffled",
               "setup_key": f"s{i}"} for i in range(50)])
    perfect = ([{"id": f"g{i}", "humor_score": 1.0 + rng.random()} for i in range(50)]
               + [{"id": f"c{i}", "humor_score": rng.random()} for i in range(50)])
    randomish = [{"id": r["id"], "humor_score": rng.random()} for r in sol]
    inverted = [{"id": r["id"],
                 "humor_score": (0.0 if r["is_genuine"] else 1.0) + rng.random() * 0.5}
                for r in sol]
    p = score(sol, perfect)
    q = score(sol, randomish)
    v = score(sol, inverted)
    assert p == 1.0, p
    assert 0.3 < q < 0.7, q
    assert v < 0.3, v
    assert matched_pair_accuracy(sol, perfect) == 1.0
    print(f"metric self-test OK: perfect={p} random={q:.3f} inverted={v:.3f}")

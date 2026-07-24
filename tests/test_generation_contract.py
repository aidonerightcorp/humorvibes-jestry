from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from humor_mesh import extract_candidates  # noqa: E402
from mesh_cli import _write_generation_receipt  # noqa: E402
from mesh_signals import OllamaProvider  # noqa: E402


def test_extract_candidates_accepts_json_wrappers_and_deduplicates():
    text = 'Result:\n```json\n{"jokes":["one turn", "two turn", "ONE TURN"]}\n```'
    assert extract_candidates(text) == ["one turn", "two turn"]


def test_extract_candidates_accepts_numbered_and_bulleted_text():
    numbered = "1. setup one, but turn one\n2) setup two, then turn two"
    assert extract_candidates(numbered) == [
        "setup one, but turn one",
        "setup two, then turn two",
    ]
    assert extract_candidates("- first joke\n* second joke") == ["first joke", "second joke"]


def test_ollama_generation_disables_thinking_by_default(monkeypatch):
    monkeypatch.setenv("GEMMA_MODEL", "gemma4")
    monkeypatch.delenv("GEMMA_THINK", raising=False)
    provider = OllamaProvider()
    captured = {}

    def fake_post(payload):
        captured.update(payload)
        return {"response": "1. complete candidate"}

    monkeypatch.setattr(provider, "_post", fake_post)
    assert provider.generate("prompt", max_tokens=444) == "1. complete candidate"
    assert captured["think"] is False
    assert captured["options"]["num_predict"] == 444


def test_generation_receipt_keeps_measurement_truth_boundary(tmp_path):
    args = argparse.Namespace(
        receipt_out=str(tmp_path / "receipt.json"),
        topic="AI PMs",
        format="one_liner",
        audience="NYC",
        preferences="concise",
        count=1,
        temperature=0.7,
    )
    provider = argparse.Namespace(name="ollama", model="gemma4", think=False)
    _write_generation_receipt(
        args,
        provider,
        "prompt",
        "1. joke",
        ["joke"],
        [{"candidate": "joke", "measured": False}],
        420,
        status="completed",
    )
    receipt = json.loads((tmp_path / "receipt.json").read_text())
    assert receipt["truth_boundary"] == {
        "competition_submission": False,
        "generation_executed": True,
        "model_judgment_is_not_human_laughter": True,
        "teacher_forced_logprobs_measured": False,
    }
    assert receipt["parsed_candidate_count"] == 1

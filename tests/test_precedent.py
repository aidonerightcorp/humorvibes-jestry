"""Precedent engine tests: offline hash backend, deterministic, no network."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from precedent import (  # noqa: E402
    HashEmbedBackend, PrecedentIndex, quick_check,
)


def fixture_corpora(tmp_path: Path) -> Path:
    corpus = tmp_path / "corpora"
    corpus.mkdir(exist_ok=True)
    rows = [
        {"text": "Man plans and God laughs.", "source": "Yiddish fixture",
         "license": "CC0", "meta": {"language": "yi"}},
        {"text": "A Twain fixture joke about a careful witness.",
         "source": "Mark Twain fixture", "license": "public domain",
         "meta": {"language": "en"}},
    ]
    languages = ("es", "de", "zh", "ja", "en")
    rows.extend(
        {"text": f"Fixture humor item {i} with a distinct comic detail.",
         "source": "multilingual fixture", "license": "CC0",
         "meta": {"language": languages[i % len(languages)]}}
        for i in range(82)
    )
    (corpus / "fixture.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    return corpus


def make_index(tmp_path: Path) -> PrecedentIndex:
    return PrecedentIndex(backend=HashEmbedBackend(), out_dir=tmp_path / "out",
                          corpora_dir=fixture_corpora(tmp_path))


def test_index_collects_multilingual_supply(tmp_path):
    idx = make_index(tmp_path)
    assert len(idx.items) >= 80          # twain 40 + proverbs 36 + symmetry 8 ...
    langs = {v.get("language", "en") for v in idx.items.values()}
    assert {"es", "de", "yi", "zh", "ja"}.issubset(langs)
    # provenance and license ride along on every item
    assert all(v.get("source") and v.get("license") for v in idx.items.values())


def test_been_done_detects_exact_retell(tmp_path):
    idx = make_index(tmp_path)
    idx.ensure_embedded()
    twain = next(v["text"] for v in idx.items.values() if "Twain" in v["source"])
    rep = idx.been_done(twain)
    assert rep.verdict.startswith("surface_match")
    assert rep.surface_hits[0].score >= 0.99
    assert rep.semantic is False         # hash backend says so honestly


def test_been_done_is_open_world_about_novelty(tmp_path):
    idx = make_index(tmp_path)
    idx.ensure_embedded()
    rep = idx.been_done("Zorbulating quexifiers deprecate the flumbo matrix quarterly.")
    assert rep.verdict.startswith("no_precedent_found within the indexed supply")
    assert "NOT detectable offline" in rep.note   # hash-backend honesty clause


def test_frame_channel_catches_same_engine_new_words(tmp_path):
    idx = make_index(tmp_path)
    # label two items with the same frame by hand (the Gemma 4 lane does this live)
    keys = list(idx.items)[:2]
    for k in keys:
        idx.items[k]["labels"] = {"frame": "an expert fails at the one thing experts do",
                                  "mechanisms": ["status_inversion"], "language": "en",
                                  "cultural_cache": "canonical", "taboo_topics": [],
                                  "labeler": "test"}
    idx.ensure_embedded()
    rep = idx.been_done("The staff engineer's demo crashed on the title slide.",
                        frame_hint="an expert fails at the one thing experts do")
    assert rep.verdict.startswith("frame_precedent")
    assert rep.frame_hits and rep.frame_hits[0].score >= 0.99


class FakeLabeler:
    model = "fake-gemma4"

    def judge_json(self, prompt: str):
        return {"frame": "small creature suffers workplace consequences",
                "mechanisms": ["anthropomorphism"], "language": "es",
                "cultural_cache": "canonical", "taboo_topics": []}


def test_label_missing_lane_is_selective_and_persistent(tmp_path):
    idx = make_index(tmp_path)
    out = idx.label_missing(FakeLabeler(), limit=3)
    assert out["labeled"] == 3
    # persisted: a new index over the same out_dir sees the labels
    idx2 = make_index(tmp_path)
    labeled = [v for v in idx2.items.values() if v.get("labels")]
    assert len(labeled) >= 3
    assert labeled[0]["labels"]["labeler"] == "fake-gemma4"


def test_cross_lingual_bridge_finds_non_english_neighbors(tmp_path):
    idx = make_index(tmp_path)
    idx.ensure_embedded()
    hits = idx.cross_lingual("Man plans and God laughs.")
    assert hits, "expected a non-English neighbor for the Yiddish classic"
    assert hits[0].language == "yi"


def test_quick_check_never_raises_and_reports_backend(tmp_path):
    rep = quick_check("any text at all", live=False, out_dir=tmp_path / "out",
                      corpora_dir=fixture_corpora(tmp_path))
    assert "verdict" in rep and "backend" in rep
    assert rep["semantic"] is False


def test_receipt_integration_annotates_accepted_outcome(tmp_path, monkeypatch):
    import jestry as J
    import precedent
    from jestry import BitRegistry, Jestry, WorkSpec
    from tests.test_jestry import FakeInstrument, fake_generation

    monkeypatch.setattr(J, "ollama_generate_with_usage", fake_generation)
    monkeypatch.setattr(J, "CORPORA_DIR", fixture_corpora(tmp_path))
    monkeypatch.setattr(precedent, "quick_check", lambda text, **_: {
        "query": text, "verdict": "fixture_no_precedent_match",
        "backend": "test-double", "semantic": False, "indexed_items": 84,
    })
    out = tmp_path / "jout"
    out.mkdir(parents=True)
    (out / "fake_calibration.json").write_text(json.dumps({
        "instrument": "fake-instrument", "certified": True, "ts": "test",
        "derived": {"s_band": [1.2, 5.5], "r_floor": 0.5, "e_floor": 0.03}}))
    j = Jestry(registry=BitRegistry(out_dir=out), out_dir=out, provider=FakeInstrument())
    spec = WorkSpec.from_request("make a joke about sprint planning rituals",
                                 audience="engineers", personas="engineers",
                                 format_key="one_liner", candidates=2)
    receipt = j.run(spec, live=False if False else True)  # live loop, mocked generation
    assert receipt["outcome"]["accepted"]
    assert receipt["precedent"] is not None
    assert "verdict" in receipt["precedent"]

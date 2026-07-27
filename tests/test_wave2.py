from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import build_kaggle_export as export
import caption_corpus as captions
import caption_model
import corpus_census as census
import harvest_supply
import harvest_wave2 as wave2
import harvest_wikiquote_citation as wikiquote
import humor_features
import style_taxonomy as style
import verify_wave2_release as release


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"_meta": {"n": len(rows)}}) + "\n")
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_canonical_notebook_is_deterministic_public_and_schema_clean() -> None:
    root = Path(__file__).resolve().parents[1]
    builder = root / "wave2_notebook" / "build_wave2_notebook.py"
    notebook = root / "wave2_notebook" / "humor_genome_wave2.ipynb"
    metadata = root / "wave2_notebook" / "kernel-metadata.json"
    subprocess.run([sys.executable, str(builder)], check=True, capture_output=True)
    first = hashlib.sha256(notebook.read_bytes()).hexdigest()
    subprocess.run([sys.executable, str(builder)], check=True, capture_output=True)
    assert hashlib.sha256(notebook.read_bytes()).hexdigest() == first
    nb = json.loads(notebook.read_text(encoding="utf-8"))
    opening = "".join(nb["cells"][0]["source"])
    assert "Start here" in opening
    assert "single canonical executable write-up" in opening
    assert "SEPARATION IS NOT ESTABLISHED" in opening
    ids = [cell.get("id") for cell in nb["cells"]]
    assert all(ids) and len(ids) == len(set(ids))
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            ast.parse("".join(cell["source"]))
    assert json.loads(metadata.read_text(encoding="utf-8"))["is_private"] is False
    assert "Reproducible Gemma Study" in json.loads(
        metadata.read_text(encoding="utf-8"))["title"]

    dataset_metadata = json.loads((root / "wave2_dataset" /
                                   "dataset-metadata.json").read_text(encoding="utf-8"))
    assert dataset_metadata["isPrivate"] is False
    assert dataset_metadata["id"] == "taylorsamarel/humor-genome-wave2"
    assert "Public Research Corpus" in dataset_metadata["title"]


def test_caption_model_checkpoint_is_atomic(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(caption_model, "OUT", tmp_path)
    report = {"status": "core_complete", "results": {"rho": 0.1}}
    caption_model.write_report(report)
    assert json.loads((tmp_path / "caption_model.json").read_text()) == report
    assert not (tmp_path / "caption_model.json.tmp").exists()


def test_script_aware_screen_keeps_real_chengyu() -> None:
    assert wave2.screen("一箭双雕") is True
    assert wave2.screen("一箭") is False
    assert wave2.screen("too tiny") is True
    assert wave2.screen("tiny") is False


def test_licence_policy_is_boundary_aware_and_deny_first() -> None:
    assert census.classify_licence("MIT License") == "redistributable"
    assert census.classify_licence(
        "Permit required before redistribution") == "research_only"
    assert census.classify_licence(
        "CC BY 4.0; research use only, do not redistribute") == "research_only"
    assert census.classify_licence("CC BY-NC 4.0") == "noncommercial"
    assert census.classify_licence("license not declared") == "research_only"
    assert census.classify_licence("something permissive-ish") == "unclassified"


def test_domain_terms_require_both_boundaries_and_preserve_overlaps() -> None:
    assert style.classify_domain("category theory and carpet sales")["domain"] == "general"
    result = style.classify_domain(
        "The marine corps pilot stood on the flight deck."
    )
    assert result["domain"] == "mil_air"
    assert result["domain_hits"] == 2
    assert {"military", "mil_marines", "nautical", "transport"}.issubset(
        result["domain_all"]
    )


def test_caption_cache_identity_changes_with_its_source(monkeypatch,
                                                        tmp_path: Path) -> None:
    source = tmp_path / "harvest_nextml_fixture.jsonl"
    source.write_text('{"text":"first"}\n', encoding="utf-8")
    monkeypatch.setattr(captions, "CORPORA", tmp_path)
    first, files = captions._source_identity()
    assert files == [source]
    source.write_text('{"text":"first and now longer"}\n', encoding="utf-8")
    second, _ = captions._source_identity()
    assert first != second


def test_frequency_cache_key_changes_on_same_size_rewrite(tmp_path: Path) -> None:
    path = tmp_path / "corpus.jsonl"
    path.write_text("alpha\n", encoding="utf-8")
    first = humor_features._freq_cache_key([path])
    original = path.stat().st_mtime_ns
    path.write_text("bravo\n", encoding="utf-8")
    # Filesystems can coalesce timestamps; pin a distinct nanosecond value so
    # the contract, rather than timing luck, is what the test exercises.
    os.utime(path, ns=(original + 1, original + 1))
    assert path.stat().st_size == len("bravo\n")
    assert humor_features._freq_cache_key([path]) != first


def test_frequency_builder_rejects_partial_corpus(monkeypatch,
                                                  tmp_path: Path) -> None:
    source = tmp_path / "broken.jsonl"
    source.write_text('{"text":"truncated"\n', encoding="utf-8")
    monkeypatch.setattr(humor_features, "CORPORA", tmp_path)
    monkeypatch.setattr(humor_features, "CACHE_DIR", tmp_path / "cache")
    with pytest.raises(RuntimeError, match=r"broken\.jsonl.*malformed JSON"):
        humor_features.build_frequencies(use_cache=False)


def test_caption_reader_fails_loudly_on_malformed_json(monkeypatch,
                                                       tmp_path: Path) -> None:
    source = tmp_path / "harvest_nextml_broken.jsonl"
    source.write_text('{"text":"truncated"\n', encoding="utf-8")
    monkeypatch.setattr(captions, "CORPORA", tmp_path)
    with pytest.raises(ValueError, match=r"harvest_nextml_broken\.jsonl:1"):
        list(captions.iter_raw())


def test_caption_cache_rebuilds_when_source_identity_changes(monkeypatch,
                                                             tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    source = tmp_path / "harvest_nextml_fixture.jsonl"

    def record(text: str) -> dict:
        return {"text": text, "source": "nextml/caption-contest-data/1",
                "funniness_label": 2.0,
                "meta": {"record_kind": "ranked_caption", "contest": "1",
                         "votes": 3, "not_funny": 1,
                         "somewhat_funny": 1, "funny": 1}}

    source.write_text(json.dumps(record("first caption")) + "\n", encoding="utf-8")
    monkeypatch.setattr(captions, "CORPORA", tmp_path)
    monkeypatch.setattr(captions, "CACHE", tmp_path / "caption_index.parquet")
    monkeypatch.setattr(captions, "CACHE_META", tmp_path / "caption_index.meta.json")
    assert len(captions.load(rebuild=True)) == 1
    assert captions.CACHE_META.exists()

    with source.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record("second caption")) + "\n")
    assert len(captions.load()) == 2


def test_wikiquote_parser_unions_every_present_representation() -> None:
    source = """
# [[Numeris|Numbered wisdom]] travels farther than silence.
* {{Ruby|猫に小判|ねこにこばん}}
{{цитат|A mixed page must keep its template arm.|||English gloss}}
{{Ein person er ein person gjennom andre personar.}}
<P>Legacy HTML still contains a complete proverb.<BR>
"""
    rows, mode = wikiquote.extract_page(source)
    assert "Numbered wisdom travels farther than silence." in rows
    assert "猫に小判" in rows
    assert "A mixed page must keep its template arm." in rows
    assert "Ein person er ein person gjennom andre personar." in rows
    assert "Legacy HTML still contains a complete proverb." in rows
    assert set(mode.split("+")) == {
        "citation-templates", "lists", "html-blocks", "sentence-templates"
    }


def test_wikiquote_explicit_subpages_are_bounded_targets() -> None:
    source = "{{:Peribahasa Indonesia A}} {{:Peribahasa Indonesia B}} " \
             "{{:Peribahasa Indonesia A}} [[Unrelated article]]"
    assert wikiquote.transcluded_pages(source) == [
        "Peribahasa Indonesia A", "Peribahasa Indonesia B"
    ]


def test_hf_waterfill_redistributes_small_source_capacity() -> None:
    available = [231_657, 150_553, 93_968, 53_400, 19_354, 9_000, 9_978, 6_359, 5_700]
    caps = wave2._waterfill(available, 550_000)
    assert sum(caps) == 550_000
    assert caps[3:] == available[3:]
    assert caps[2] == available[2]
    assert caps[0] > 61_111 and caps[1] > 61_111


def test_hf_record_normalizes_language_and_translation() -> None:
    spec = {
        "text": "joke", "labels": ["joke_english", "language"],
        "translation": "joke_english", "language_field": "language",
        "lang": "mul", "license": "research use",
    }
    rec = wave2._record_from_hf_row(
        spec, "example/jokes", "default", "train",
        {"joke": "This is a long enough Vietnamese joke.",
         "joke_english": "This is its English gloss.", "language": "VIETNAMESE"},
        17,
    )
    assert rec is not None
    assert rec["meta"]["language"] == "vi"
    assert rec["meta"]["translation_en"] == "This is its English gloss."
    assert rec["meta"]["_hf_row_offset"] == 17


def test_parquet_hf_transport_resumes_at_raw_row(monkeypatch, tmp_path: Path) -> None:
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    path = tmp_path / "rows.parquet"
    pq.write_table(pa.table({"text": [
        "first record is long enough", "second record is long enough",
        "third record is long enough",
    ]}), path)
    key = "_fixture_resume"
    monkeypatch.setitem(wave2.HF_SPECS, key, {
        "repo": "fixture/repo", "config": "default", "split": "train",
        "text": "text", "lang": "en", "license": "MIT",
    })
    wave2._HF_LOCATION_CACHE.pop(key, None)
    monkeypatch.setattr(wave2, "hf_parquet_files", lambda *_: [{
        "url": "https://example.invalid/rows.parquet", "filename": "rows.parquet"
    }])
    monkeypatch.setattr(wave2, "_download_parquet", lambda _info: path)
    rows = wave2.hf_spec_fetch_parquet(key, limit=2, start_offset=1)
    assert rows is not None
    assert [row["text"] for row in rows] == [
        "second record is long enough", "third record is long enough"
    ]
    assert [row["meta"]["_hf_row_offset"] for row in rows] == [1, 2]


def test_streaming_export_is_reproducible_and_includes_urdu_pairs(tmp_path: Path) -> None:
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    _write_jsonl(a, [
        {"text": "A sufficiently long first joke.", "source": "hf:family/a",
         "license": "MIT", "meta": {"language": "en"}, "funniness_label": 1},
        {"text": "A sufficiently long second joke.", "source": "hf:family/a",
         "license": "MIT", "meta": {"language": "en"}},
    ])
    _write_jsonl(b, [
        {"text": "ہمتِ مرداں مددِ خدا۔",
         "source": "hf:Ehtisham1328/urdu-idioms-with-english-translation",
         "license": "Public domain",
         "meta": {"language": "ur",
                  "Hard work is the key to success.": "The courage of men is aided by God."}},
        {"text": "A caption with an annotated visual frame.",
         "source": "New Yorker caption contest 1", "license": "CC BY 4.0",
         "meta": {"language": "en", "contest": "1",
                  "image_description": "A room.",
                  "image_uncanny_description": "The chair is floating."}},
        {"text": "This row must remain local research inventory only.",
         "source": "blocked-family", "license": "research use only, do not redistribute",
         "meta": {"language": "en"}},
    ])
    out = tmp_path / "export"
    out.mkdir()
    (out / "dataset-metadata.json").write_text(
        '{"title":"fixture","id":"owner/fixture","licenses":[{"name":"other"}]}\n',
        encoding="utf-8")

    first = export.build(1, paths=[b, a], out_dir=out)
    hashes_1 = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in out.iterdir() if p.is_file()}
    second = export.build(1, paths=[a, b], out_dir=out)
    hashes_2 = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in out.iterdir() if p.is_file()}

    assert first == second
    assert hashes_1 == hashes_2
    assert first["full_corpus_rows"] == 5
    assert first["eligible_rows"] == 4
    assert first["exported_rows"] == 3
    assert first["excluded_by_licence_class"] == {"research_only": 1}
    sample_rows = [json.loads(line) for line in
                   (out / "corpus_sample.jsonl").read_text(
                       encoding="utf-8").splitlines()[1:]]
    assert all(row["licence_class"] == "redistributable" for row in sample_rows)
    assert all("local research inventory" not in row["text"] for row in sample_rows)
    assert first["aligned_phrase_pairs"] == 1
    aligned = [json.loads(line) for line in
               (out / "aligned_phrases.jsonl").read_text(encoding="utf-8").splitlines()]
    assert aligned[0]["translation_en"] == "The courage of men is aided by God."
    header = json.loads((out / "corpus_sample.jsonl").read_text(
        encoding="utf-8").splitlines()[0])["_meta"]
    assert "created" not in header
    assert header["schema_version"] == 3
    assert header["eligible_from"] == 4
    card = (out / "DATA_CARD.md").read_text(encoding="utf-8")
    assert "5-item research inventory" in card
    assert "Start here" in card
    assert "Quick start on Kaggle" in card
    assert "Main row schema" in card
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert "dataset-metadata.json" not in manifest
    assert (out / "dataset-metadata.json").exists()
    for name, evidence in manifest.items():
        path = out / name
        assert path.stat().st_size == evidence["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == evidence["sha256"]
    receipt = release.verify(out)
    assert receipt["status"] == "PASS"
    assert receipt["exported_rows"] == 3

    with (out / "aligned_phrases.jsonl").open("a", encoding="utf-8") as fh:
        fh.write("{}\n")
    with pytest.raises(release.ReleaseValidationError,
                       match="byte length differs for aligned_phrases.jsonl"):
        release.verify(out)


def test_census_accumulator_matches_file_census(tmp_path: Path) -> None:
    path = tmp_path / "rows.jsonl"
    rows = [
        {"text": "A graded row long enough.", "source": "hf:a", "license": "MIT",
         "meta": {"language": "en", "style": "dad"}, "funniness_label": 2},
        {"text": "Une ligne assez longue.", "source": "hf:b",
         "license": "research use", "meta": {"language": "fr"}},
    ]
    _write_jsonl(path, rows)
    acc = census.CensusAccumulator()
    for row in rows:
        acc.add(row)
    assert acc.report(files=1) == census.census([path])


def test_release_export_fails_loudly_on_malformed_json(tmp_path: Path) -> None:
    source = tmp_path / "broken.jsonl"
    source.write_text(
        json.dumps({"text": "A valid row before the damage.",
                    "source": "fixture", "license": "MIT"}) + "\n" +
        '{"text": "truncated"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"broken\.jsonl:2"):
        export.build(1, paths=[source], out_dir=tmp_path / "export")


def test_export_cli_reports_the_requested_output_directory(
        monkeypatch, tmp_path: Path, capsys) -> None:
    corpora = tmp_path / "corpora"
    corpora.mkdir()
    _write_jsonl(corpora / "fixture.jsonl", [
        {"text": "A sufficiently long public-domain joke for export.",
         "source": "fixture", "license": "Public domain",
         "meta": {"language": "en"}},
    ])
    out = tmp_path / "published"
    metadata = tmp_path / "dataset-metadata.json"
    metadata.write_text(
        '{"title":"fixture","id":"owner/fixture","isPrivate":false,'
        '"licenses":[{"name":"other"}]}\n', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "build_kaggle_export.py", "--per-family", "1",
        "--corpora-dir", str(corpora), "--out-dir", str(out),
        "--metadata-template", str(metadata),
    ])
    assert export.main() == 0
    assert f"-> {out}" in capsys.readouterr().out
    assert (out / "manifest.json").exists()


def test_exact_digest_index_reads_only_text_identity(tmp_path: Path) -> None:
    corpora = tmp_path / "corpora"
    receipts = tmp_path / "out"
    corpora.mkdir()
    receipts.mkdir()
    _write_jsonl(corpora / "one.jsonl", [
        {"text": "Same identity despite metadata.", "source": "one", "license": "MIT",
         "meta": {"language": "en", "large_unused_field": "x" * 10_000}},
    ])
    (receipts / "accepted_bits.jsonl").write_text(
        json.dumps({"text": "An accepted bit also counts."}) + "\n", encoding="utf-8")
    got = harvest_supply.exact_digest_index(corpora, receipts)
    assert got == {
        harvest_supply._sha("Same identity despite metadata."),
        harvest_supply._sha("An accepted bit also counts."),
    }


def test_partial_checkpoint_survives_failure_and_is_removed_on_success(
        monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(wave2, "__file__", str(tmp_path / "harvest_wave2.py"))
    wave2.open_partial("fixture", "failed run")
    failed_path = wave2._PARTIAL_PATH
    wave2.emit({"text": "recover me"})
    wave2.close_partial(completed=False)
    assert failed_path is not None and failed_path.exists()

    wave2.open_partial("fixture", "completed run")
    completed_path = wave2._PARTIAL_PATH
    wave2.emit({"text": "already committed"})
    wave2.close_partial(completed=True)
    assert completed_path is not None and not completed_path.exists()

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


PATH = Path(__file__).resolve().parents[1] / "ablation_lab" / "ablation_pipeline.py"
SPEC = importlib.util.spec_from_file_location("ablation_pipeline", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_original_word_and_apply_edit():
    source = "Minister resigns after <policy/> dispute"
    assert MODULE.original_word(source) == "policy"
    assert MODULE.apply_edit(source, "banana") == "Minister resigns after banana dispute"


def test_fixed_score_renormalizes_after_ablation():
    frame = pd.DataFrame(
        {
            "S_score": [1.0, 0.0],
            "R_score": [0.0, 1.0],
            "E_score": [0.0, 0.0],
            "B_score": [1.0, 1.0],
        }
    )
    full = MODULE.fixed_score(frame, ["S", "R", "E", "B"])
    without_b = MODULE.fixed_score(frame, ["S", "R", "E"])
    assert np.allclose(full, [50.0, 55.0])
    assert np.allclose(without_b, [37.5, 43.75])


def test_component_ablation_has_all_predeclared_variants():
    rng = np.random.default_rng(1)
    frame = pd.DataFrame(
        {
            "grade": np.linspace(0, 3, 30),
            "S_score": rng.random(30),
            "R_score": rng.random(30),
            "E_score": rng.random(30),
            "B_score": rng.random(30),
        }
    )
    result = MODULE.component_ablation(frame)
    expected = {"full_SREB", "without_S", "without_R", "without_E", "without_B", "only_S", "only_R", "only_E", "only_B"}
    assert set(result) == expected
    assert all(len(row["spearman_bootstrap_95ci"]) == 2 for row in result.values())


def test_paired_control_court_requires_complete_triplets():
    rows = []
    for item_id in ("a", "b"):
        for variant, offset in (("human_edit", 3), ("original_headline", 1), ("shuffled_edit", 0)):
            rows.append(
                {
                    "id": item_id,
                    "control_set": True,
                    "variant": variant,
                    "S_score": offset,
                    "R_score": offset,
                    "E_score": offset,
                    "B_score": offset,
                    "full_score": offset,
                }
            )
    result = MODULE.paired_control_court(pd.DataFrame(rows))
    assert result["n_complete_sets"] == 2
    assert result["paired_tests"]["human_vs_original_headline"]["full_score"]["wins"] == 2


def test_notebook_builder_vendors_current_signal_sources(tmp_path, monkeypatch):
    builder_path = Path(__file__).resolve().parents[1] / "ablation_lab" / "build_ablation_notebook.py"
    spec = importlib.util.spec_from_file_location("build_ablation_notebook", builder_path)
    builder = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(builder)
    builder.main()
    notebook = __import__("json").loads((builder.HERE / "ablation_notebook.ipynb").read_text())
    assert len(notebook["cells"]) == 3
    vendor = notebook["cells"][1]["source"]
    canonical = (builder.HERE.parent / "mesh_signals.py").read_text()
    assert repr(canonical) in vendor
    assert "HUMORVIBES_SOURCE_DIR" in vendor


def test_failure_markdown_has_no_optional_tabulate_dependency():
    frame = pd.DataFrame([{"case_type": "bad|case", "text": "line one\nline two"}])
    rendered = MODULE.failure_markdown(frame)
    assert "bad\\|case" in rendered
    assert "line one line two" in rendered

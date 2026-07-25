"""Jestry verification gate: ALL GREEN or a nonzero exit.

Offline gates always run; live gates run when the local Ollama answers and are
reported as SKIP (never silently green) when it does not. Run it twice — the
offline gates are deterministic and the second pass must agree.

    python3 verify_jestry.py
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

RESULTS: list[tuple[str, str, str]] = []   # (gate, GREEN/RED/SKIP, detail)


def gate(name: str):
    def deco(fn):
        def run():
            try:
                out = fn()
                RESULTS.append((name, "GREEN", str(out)[:96]))
            except SkipGate as exc:
                RESULTS.append((name, "SKIP", str(exc)[:96]))
            except Exception as exc:
                RESULTS.append((name, "RED", f"{type(exc).__name__}: {exc}"[:200]))
        return run
    return deco


class SkipGate(RuntimeError):
    pass


def ollama_up() -> bool:
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=4)
        return True
    except Exception:
        return False


@gate("G1 offline pytest suite (full)")
def g1():
    # 900s fit the 1.3k-card corpus; the 23k-card supply needs headroom
    # (16k cards ran 799s GREEN on 2026-07-24) — the tests still must pass
    proc = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"],
                          cwd=ROOT, capture_output=True, text=True, timeout=2400)
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-1]
    assert proc.returncode == 0, tail
    return tail


@gate("G2 registry determinism x2 + census")
def g2():
    from jestry import BitRegistry
    a, b = BitRegistry(), BitRegistry()
    assert a.digest() == b.digest(), "registry digest not deterministic"
    c = a.census()
    assert c["mechanism"] == 14 and c["format"] == 11, c
    assert c["corpus_item"] >= 120, c
    return f"digest {a.digest()} census {c['total_cards']} cards"


@gate("G3 charter/code sync")
def g3():
    from jestry import ACCEPTANCE_LEVELS, FUNNEL_STAGES, LAWS, MOTTO
    doc = (ROOT / "JESTRY-CHARTER-AND-CONSTITUTION-2026-07-23.md").read_text(encoding="utf-8")
    assert len(LAWS) == 18 and len(FUNNEL_STAGES) == 9 and len(ACCEPTANCE_LEVELS) == 6
    assert MOTTO.split(".")[0] in doc, "motto drifted from charter doc"
    missing = [name for name, _ in LAWS if name not in doc]
    assert not missing, f"laws missing from charter doc: {missing}"
    return "18 laws, 9 funnel stages, 6 acceptance levels, doc in sync"


@gate("G4 zero-model replay route (offline)")
def g4():
    import tempfile

    import jestry as J
    from jestry import BitRegistry, Jestry, WorkSpec
    with tempfile.TemporaryDirectory() as td:
        art = Path(td) / "artifacts"
        art.mkdir()
        prog = {"program_id": "one_liner-verify01", "format_key": "one_liner",
                "template": "My {tool} refuses to join the standup meeting.",
                "punch_template": "It says the calendar is not in its contract.",
                "slots": {"tool": ["compiler", "linter", "debugger"]},
                "frame": "Office software behaves like a unionized employee.",
                "guards": [], "measured": {"pass_rate": 1.0}, "provenance":
                {"topic": "standup meeting software calendar"}, "validated": True}
        (art / "p.json").write_text(json.dumps(prog))
        saved = J.ARTIFACT_DIR
        J.ARTIFACT_DIR = art
        try:
            out = Path(td) / "out"
            j = Jestry(registry=BitRegistry(out_dir=out), out_dir=out)
            spec = WorkSpec.from_request("a joke about the standup meeting calendar")
            receipt = j.run(spec, live=False)
        finally:
            J.ARTIFACT_DIR = saved
        assert receipt["outcome"]["accepted"] and receipt["generation_usage"] == []
        assert receipt["route"]["kind"] == "replay_program"
        return "replay accepted, zero model calls, receipt complete"


@gate("G5 receipt schema")
def g5():
    from jestry import Receipts
    rows = Receipts().read_all()
    assert rows, "no receipts yet — run the live gate or a CLI run first"
    need = {"receipt_type", "ts", "request", "route", "funnel", "oracle_usage",
            "generation_usage", "outcome", "truth_boundary", "charter_version"}
    missing = need - set(rows[-1])
    assert not missing, f"receipt missing keys: {missing}"
    return f"{len(rows)} receipts, latest has all {len(need)} required keys"


@gate("G6 LIVE gemma4 route end-to-end")
def g6():
    if not ollama_up():
        raise SkipGate("ollama not answering on 127.0.0.1:11434")
    from jestry import Jestry, WorkSpec
    j = Jestry()
    # salt the topic per run: a fixed request goes stale the moment the ladder
    # accepts and preserves a bit for it — every later run then replays that
    # bit (correct, Law 6) and this gate would never exercise live measurement
    salt = time.strftime("%H:%M")
    spec = WorkSpec.from_request(
        f"Make a joke about AI project managers shipping agentic products before the {salt} deadline",
        audience="NYC tech meetup", personas="NYC tech meetup",
        preferences="smart, specific, not mean", format_key="one_liner", candidates=2)
    t0 = time.time()
    receipt = j.run(spec, live=True, max_escalations=1)
    wall = time.time() - t0
    cands = receipt["candidates"]
    assert cands, f"no candidates produced: {receipt['outcome']}"
    measured = [c for c in cands if c.get("measured")]
    outcome = receipt["outcome"]
    replay_ok = (outcome.get("accepted") and not measured
                 and "carried" in str(outcome.get("bit_id", "")).lower())
    if replay_ok:
        # the ladder found an accepted bit for this request family and replayed
        # it (Law 6 — correct, zero model calls). The live instrument is then
        # proven separately below; a replay must still carry its provenance.
        route = f"replay of {outcome.get('bit_id', '?')[:40]}"
    else:
        assert measured, "no candidate carries measured=True signals"
        assert receipt["truth_boundary"]["teacher_forced_logprobs_measured"] is True
        route = f"{len(measured)} measured live"
    assert receipt["oracle_usage"]["provider"] in ("gemma2-full-nll", "gemma4-forced-nll")
    # direct instrument probe (always): the certified oracle must measure the
    # reference joke inside the receipted calibration band, every verify run —
    # through the same protocol call the calibration itself used
    from mesh_signals import compute_signals
    sig = compute_signals(j._oracle(), "I told my therapist about my fear of speed bumps.",
                          "She said I'm slowly getting over it.")
    S = round(sig.surprise_mean, 2)
    cal = json.loads((ROOT / "jestry_out" / "gemma2_full_nll_calibration.json").read_text())
    lo, hi = cal["derived"]["s_band"]
    assert sig.measured, "oracle probe not measured"
    assert lo <= S <= hi, f"probe S={S} outside certified band [{lo},{hi}]"
    acc = outcome["accepted"]
    return (f"{len(cands)} candidates ({route}), probe S={S} in band, "
            f"accepted={acc}, wall {wall:.0f}s")


@gate("G7 LIVE cross-lingual precedent")
def g7():
    if not ollama_up():
        raise SkipGate("ollama not answering")
    from precedent import OllamaEmbedBackend, PrecedentIndex
    idx = PrecedentIndex(backend=OllamaEmbedBackend())
    idx.ensure_embedded()
    hits = idx.cross_lingual("Even the most senior monkey falls out of the tree sometimes.")
    assert hits and hits[0].language in ("ko", "ja"), [
        (h.language, round(h.score, 2)) for h in hits[:3]]
    exact = idx.been_done("Man plans and God laughs.")
    assert exact.verdict.startswith(("surface_match", "adjacent")), exact.verdict
    return f"monkey-canon bridge -> {hits[0].language} {hits[0].score:.2f}; yiddish {exact.verdict.split(':')[0]}"


@gate("G8 harvest receipts with provenance")
def g8():
    path = ROOT / "jestry_out" / "harvest_receipts.jsonl"
    assert path.exists(), "no harvest receipts — run harvest_supply.py keyless"
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    fresh = [r for r in rows if r.get("new", 0) > 0]
    assert fresh, "no harvest produced new records"
    assert all(r.get("licenses") for r in fresh), "harvest wrote records without licenses"
    return f"{len(rows)} harvest receipts, {sum(r['new'] for r in fresh)} new records, licensed"


@gate("G9 portal boots and serves the charter")
def g9():
    import os
    import signal
    env = dict(**{k: v for k, v in os.environ.items()}, JESTRY_PORTAL_PORT="8098")
    proc = subprocess.Popen([sys.executable, "jestry_portal.py"], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + 20
        data = None
        while time.time() < deadline and data is None:
            try:
                with urllib.request.urlopen("http://127.0.0.1:8098/api/charter", timeout=3) as r:
                    data = json.loads(r.read())
            except Exception:
                time.sleep(0.5)
        assert data and len(data["laws"]) == 18
        with urllib.request.urlopen("http://127.0.0.1:8098/", timeout=5) as r:
            assert b"Jestry" in r.read()
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=10)
    return "portal served charter (18 laws) and UI page"


@gate("G10 portal notebook deterministic x2")
def g10():
    sub = ROOT / "live_portal"
    nb = sub / "jestry_portal_notebook.ipynb"
    subprocess.run([sys.executable, "build_portal_notebook.py"], cwd=sub, check=True,
                   capture_output=True)
    first = nb.read_bytes()
    subprocess.run([sys.executable, "build_portal_notebook.py"], cwd=sub, check=True,
                   capture_output=True)
    assert nb.read_bytes() == first, "notebook build not byte-deterministic"
    cells = json.loads(first)["cells"]
    for c in cells:
        if c["cell_type"] == "code":
            compile("".join(c["source"]), "<cell>", "exec")
    return f"{len(cells)} cells, byte-identical rebuild, code compiles"


@gate("G11 certified calibration + adversarial scope")
def g11():
    path = ROOT / "jestry_out" / "gemma2_full_nll_calibration.json"
    assert path.exists(), "no full-instrument calibration receipt"
    cal = json.loads(path.read_text(encoding="utf-8"))
    assert cal.get("certified") is True, "full instrument not certified"
    assert cal.get("adversarial_scope", {}).get("mitigation"), \
        "calibration lacks the adversarial scope clause"
    assert "SCOPE" in cal.get("rule", ""), "rule missing scope statement"
    from jestry import trusted_frame_source
    assert not trusted_frame_source({"license": "random API"})
    assert trusted_frame_source({"license": "public domain (traditional)"})
    return (f"certified={cal['certified']}, adversarial probe R="
            f"{cal['adversarial_scope']['R']}, trust gate enforced")


@gate("G12 instrument robustness + executed follow-up receipts")
def g12():
    """Tonight's two experiments must stay true, not just have been true once."""
    quant = ROOT / "jestry_out" / "gemma2_full_nll_quant_check.json"
    assert quant.exists(), "no quantization-robustness receipt"
    q = json.loads(quant.read_text(encoding="utf-8"))
    for name in ("Q4_K_M", "Q8_0"):
        block = q["results"].get(name, {})
        assert "rows" in block, f"{name} not measured: {block.get('error')}"
        # the honesty invariant the NaN bug violated: a measurement is a number
        for row in block["rows"]:
            assert math.isfinite(row["S"]), f"{name}/{row['name']} S is not finite"
        assert len(block["jokes_in_region"]) == 3, \
            f"{name} lost a reference joke: {block['jokes_in_region']}"
        assert not block["controls_in_region"], \
            f"{name} admitted a control: {block['controls_in_region']}"
    assert q["verdict"]["q8_separates_under_q4_region"], "Q8 fails the Q4-derived region"
    assert all(abs(v) < 0.01 for v in q["q4_S_drift_vs_certified_receipt"].values()), \
        f"Q4 drifted from the certified receipt: {q['q4_S_drift_vs_certified_receipt']}"

    nf = ROOT / "jestry_out" / "native_format_probe.json"
    if nf.exists():
        n = json.loads(nf.read_text(encoding="utf-8"))
        assert n["worker"]["errors"] == 0, "native-format probe had instrument errors"
        arm = n["arm_A_genuine_vs_shuffled"]
        assert arm["n_genuine"] and arm["n_shuffled"], "native probe missing an arm"
        # the finding is a NEGATIVE (model-written frames invert the ordering) and
        # the docs say so; this pins the receipt's shape and honesty, not a verdict
        assert 0.0 <= arm["auc_R"] <= 1.0, "auc out of range"
        assert "popularity proxy" in n["arm_B_upvote_correlation"]["note"], \
            "the upvote arm lost its confound caveat"

    fb = ROOT / "jestry_out" / "format_boundary_experiment.json"
    assert fb.exists(), "no format-boundary receipt"
    f = json.loads(fb.read_text(encoding="utf-8"))
    assert f["worker"]["errors"] == 0, "format-boundary run had instrument errors"
    conds = f["conditions"]
    assert set(conds) == {"generic", "canonical", "control"}, "missing a split condition"
    assert all(c["n"] >= 80 for c in conds.values()), "format-boundary sample too small"
    # the claim in WRITEUP/RESULTS is mechanistic, so pin the mechanism, not the null:
    # anchoring the seam must engage resolution more often than the placebo cut does
    assert conds["canonical"]["R_positive_frac"] > conds["control"]["R_positive_frac"], \
        "canonical no longer engages R more than the placebo split"
    return (f"Q4 drift 0, Q8 dS_max={q['verdict']['max_abs_S_delta']}, both separate 3/0; "
            f"format-boundary n={conds['canonical']['n']} "
            f"R>0 {conds['generic']['R_positive_frac']}→{conds['canonical']['R_positive_frac']} "
            f"(placebo {conds['control']['R_positive_frac']})")


@gate("G13 exported dataset loads and stays aligned")
def g13():
    """A dataset nobody can load is not a deliverable; prove it round-trips."""
    out = ROOT / "dataset_out"
    man_path = out / "manifest.json"
    if not man_path.exists():
        raise SkipGate("no dataset_out/ export yet (run comedy_primitives_dataset.py)")
    man = json.loads(man_path.read_text(encoding="utf-8"))
    rows = {}
    for name in ("mechanisms.jsonl", "formats.jsonl", "items.jsonl",
                 "frames.jsonl", "measured_signals.jsonl"):
        path = out / name
        assert path.exists(), f"missing {name}"
        parsed = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        rows[name] = len(parsed)
        recorded = man["files"][name]["rows"]
        assert recorded == len(parsed), f"{name}: manifest says {recorded}, file has {len(parsed)}"
    assert rows["mechanisms.jsonl"] >= 14 and rows["formats.jsonl"] >= 11, "primitives lost"
    # every item must carry the provenance a redistributor needs
    items = [json.loads(l) for l in (out / "items.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert all(r.get("license") for r in items), "an item lost its license field"
    assert all(r.get("source") for r in items), "an item lost its source field"
    # redistribution gate: text may only ship where a license permits it, so a
    # future harvest lane cannot quietly publish scraped text through this export
    from comedy_primitives_dataset import may_redistribute_text
    leaks = [r["item_id"] for r in items
             if not r.get("text_withheld") and not may_redistribute_text(r["license"])]
    assert not leaks, f"{len(leaks)} items ship text without a redistributable license: {leaks[:3]}"
    withheld = sum(1 for r in items if r.get("text_withheld"))
    # matrices, when present, must line up row-for-row with their JSONL
    npy = out / "embeddings_surface.npy"
    aligned = "not exported"
    if npy.exists():
        import numpy as np
        arr = np.load(npy)
        embedded = sum(1 for r in items if r.get("has_surface_embedding"))
        assert arr.shape[0] == embedded, f"matrix rows {arr.shape[0]} != embedded items {embedded}"
        assert arr.shape[1] == 768, f"unexpected embedding dim {arr.shape[1]}"
        aligned = f"{arr.shape[0]}x{arr.shape[1]} aligned"
    return (f"{rows['items.jsonl']} items ({withheld} text-withheld, 0 licence leaks), "
            f"{rows['frames.jsonl']} frames, {rows['measured_signals.jsonl']} measured, "
            f"{rows['mechanisms.jsonl']} mechanisms; {aligned}")


def main() -> int:
    for fn in (g1, g2, g3, g4, g6, g5, g7, g8, g9, g10, g11, g12, g13):  # g6 before g5: live run feeds receipts
        fn()
    width = max(len(n) for n, _, _ in RESULTS)
    print("\n" + "=" * 78)
    for name, status, detail in RESULTS:
        print(f"{name:<{width}}  {status:5s}  {detail}")
    print("=" * 78)
    reds = [r for r in RESULTS if r[1] == "RED"]
    skips = [r for r in RESULTS if r[1] == "SKIP"]
    verdict = (f"{len(reds)} RED — not shippable" if reds else
               f"GREEN with {len(skips)} SKIP (live gates need Ollama)" if skips
               else "ALL GREEN")
    # every verification run leaves a receipt — "ALL GREEN" is never a memory
    out = ROOT / "jestry_out"
    out.mkdir(exist_ok=True)
    with (out / "verify_receipts.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"receipt_type": "jestry_verify", "receipt_version": 1,
                             "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                             "gates": [{"gate": n, "status": s, "detail": d}
                                       for n, s, d in RESULTS],
                             "result": verdict}) + "\n")
    print(f"RESULT: {verdict}")
    return 1 if reds else 0


if __name__ == "__main__":
    raise SystemExit(main())

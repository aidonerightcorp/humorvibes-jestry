"""Jestry layer tests: offline, deterministic, no network, isolated out dirs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import jestry as J  # noqa: E402
from jestry import (  # noqa: E402
    ACCEPTANCE_LEVELS, FUNNEL_STAGES, LAWS,
    BitRegistry, HumorPolicy, Jestry, RouteProfile, WorkSpec,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def tmp_out(tmp_path: Path) -> Path:
    out = tmp_path / "jestry_out"
    out.mkdir(parents=True)
    # acceptance requires a CERTIFIED calibration for the active instrument
    # (require_certified default) — certify the fake instrument for tests
    (out / "fake_calibration.json").write_text(json.dumps({
        "instrument": "fake-instrument", "certified": True, "ts": "test",
        "derived": {"s_band": [1.2, 5.5], "r_floor": 0.5, "e_floor": 0.03}}),
        encoding="utf-8")
    return out


@pytest.fixture(autouse=True)
def offline_external_supply(monkeypatch, tmp_path: Path):
    """Keep this module's advertised no-network contract true.

    Accepted live-path candidates normally receive a semantic been-done check.
    Those mechanics are tested directly in test_precedent.py; route tests need a
    deterministic receipt, not a several-minute Ollama embedding call. The
    registry mechanics also need representative corpus cards, not a repeated
    scan of the repository's roughly 100 MB public sample on every unit test.
    """
    import precedent
    corpus = tmp_path / "corpora"
    corpus.mkdir()
    fixture_rows = [
        {"text": f"AI project manager planning fixture joke number {i}.",
         "source": "test-fixture", "license": "MIT"}
        for i in range(48)
    ]
    (corpus / "fixture.jsonl").write_text(
        "\n".join(json.dumps(row) for row in fixture_rows) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(J, "CORPORA_DIR", corpus)
    monkeypatch.setattr(
        precedent,
        "quick_check",
        lambda text, **_: {
            "query": text,
            "verdict": "fixture_no_precedent_match",
            "backend": "test-double",
            "semantic": False,
            "indexed_items": 0,
        },
    )


@pytest.fixture()
def registry(tmp_out: Path) -> BitRegistry:
    return BitRegistry(out_dir=tmp_out)


class FakeInstrument:
    """Deterministic SignalProvider: in-band S, real R under the right frame."""

    name = "fake-instrument"
    model = "fake-1"

    HINT = "The meeting culture is the boss here."

    def nll_tokens(self, context: str, continuation: str):
        from mesh_signals import SurprisalProfile
        words = continuation.split()
        if "obvious" in continuation:
            per = 0.5                      # predictable -> below the S band
        elif f"({self.HINT}" in context:
            per = 2.0                      # frame collapses surprisal
        else:
            per = 3.0                      # baseline and decoy-null contexts
        return SurprisalProfile(tokens=words, nlls=[per] * len(words), measured=True)

    def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 220) -> str:
        return self.HINT

    def judge_json(self, prompt: str):
        return {"collision": 1, "colliding_model": "", "note": "fine"}


GOOD = "Our sprint planning ran long. The calendar filed a complaint."
BAD = "Meetings are long and obvious. This is obvious."


def fake_generation(prompt: str, **kwargs):
    return {"ok": True, "model": "gemma4-fake",
            "response": json.dumps({"candidates": [GOOD, BAD]}),
            "prompt_sha256": "x" * 64, "output_sha256": "y" * 64,
            "prompt_tokens": 100, "output_tokens": 50, "wall_s": 0.01,
            "thinking_enabled": False}


# ---------------------------------------------------------------------------
# constitutional surface
# ---------------------------------------------------------------------------
def test_charter_surface_is_complete():
    assert len(LAWS) == 18
    assert FUNNEL_STAGES[0] == "discovered" and FUNNEL_STAGES[-1] == "accepted"
    assert list(ACCEPTANCE_LEVELS) == sorted(
        ACCEPTANCE_LEVELS, key=ACCEPTANCE_LEVELS.index)
    assert ACCEPTANCE_LEVELS.index("human_laughed") > ACCEPTANCE_LEVELS.index("instrument_scored")


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------
def test_registry_census_counts_supply(registry: BitRegistry):
    census = registry.census()
    assert census["mechanism"] == 14
    assert census["format"] == 11
    assert census["corpus_item"] >= 45          # twain 40 + symmetry 8 (+ imgflip)
    assert census["total_cards"] == sum(
        v for k, v in census.items() if k not in ("total_cards", "accepted_or_better"))


def test_registry_digest_is_deterministic(tmp_out: Path):
    assert BitRegistry(out_dir=tmp_out).digest() == BitRegistry(out_dir=tmp_out).digest()


def test_search_returns_body_free_cards(registry: BitRegistry):
    spec = WorkSpec.from_request("make a joke about AI project managers",
                                 audience="NYC tech meetup")
    cards = registry.search(spec, limit=6)
    assert cards, "expected retrieval hits for an AI topic"
    assert any(c.kind == "mechanism" for c in cards)
    # cards are one-liners, not bodies
    assert all(len(c.one_line) <= 140 for c in cards)


# ---------------------------------------------------------------------------
# policy: permission is not preference
# ---------------------------------------------------------------------------
def test_identity_target_is_prohibited():
    spec = WorkSpec.from_request("jokes about someone's religion", audience="anyone")
    compat, reason = HumorPolicy().check(spec)
    assert compat == "PROHIBITED_BY_POLICY"
    assert "identity" in reason


def test_roast_requires_consent():
    spec = WorkSpec.from_request("roast my friend Sam", format_key="roast_line")
    assert HumorPolicy().check(spec)[0] == "PROHIBITED_BY_POLICY"
    spec2 = WorkSpec.from_request("roast my friend Sam", format_key="roast_line", consent=True)
    assert HumorPolicy().check(spec2)[0] == "EXACTLY_COMPATIBLE"


def test_vulnerable_disclosure_is_never_material():
    spec = WorkSpec.from_request("a bit about my aunt's cancer diagnosis")
    assert HumorPolicy().check(spec)[0] == "PROHIBITED_BY_POLICY"


def test_political_topics_get_persona_pair():
    spec = WorkSpec.from_request("a joke about congress and the election")
    assert len(spec.personas) >= 2
    joined = " ".join(spec.personas)
    assert "left" in joined and "right" in joined


# ---------------------------------------------------------------------------
# ladder: reuse before construction
# ---------------------------------------------------------------------------
def _write_validated_program(artifact_dir: Path) -> str:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    prog = {
        "program_id": "one_liner-testcafe01",
        "format_key": "one_liner",
        "template": "My {tool} refuses to join the standup meeting.",
        "punch_template": "It says the calendar is not in its contract.",
        "slots": {"tool": ["compiler", "linter", "debugger"]},
        "frame": "Office software behaves like a unionized employee.",
        "guards": [],
        "measured": {"pass_rate": 1.0, "instrumented": True},
        "provenance": {"topic": "standup meeting software calendar", "compiler": "test"},
        "validated": True,
    }
    (artifact_dir / "one_liner-testcafe01.json").write_text(json.dumps(prog), encoding="utf-8")
    return prog["program_id"]


def test_replay_program_rung_wins_and_costs_zero_model_calls(tmp_path, tmp_out, monkeypatch):
    art = tmp_path / "artifacts"
    _write_validated_program(art)
    monkeypatch.setattr(J, "ARTIFACT_DIR", art)
    j = Jestry(registry=BitRegistry(out_dir=tmp_out), out_dir=tmp_out,
               provider=FakeInstrument())
    spec = WorkSpec.from_request("a joke about the standup meeting calendar",
                                 format_key="one_liner")
    route = j.compile_route(spec)
    assert route.kind == "replay_program"
    assert route.estimated_model_calls == 0
    receipt = j.run(spec, live=False)
    assert receipt["outcome"]["accepted"] is True
    assert receipt["outcome"]["acceptance_level"] == "instrument_scored"  # carried
    assert receipt["generation_usage"] == []
    assert receipt["funnel"]["accepted"] == 1
    assert receipt["funnel"]["instrument_scored"] == 0   # carried, not re-scored
    assert receipt["truth_boundary"]["teacher_forced_logprobs_measured"] is False


def test_replay_accepted_bit_is_cheapest_rung(tmp_out: Path):
    tmp_out.mkdir(parents=True, exist_ok=True)
    bit = {"bit_id": "joke:cafe", "name": "sprint calendar", "text": GOOD,
           "format_keys": ["one_liner"],
           "keywords": ["sprint", "planning", "calendar", "complaint"],
           "acceptance_level": "human_laughed", "provenance": {}, "evidence": {}}
    (tmp_out / "accepted_bits.jsonl").write_text(json.dumps(bit) + "\n", encoding="utf-8")
    j = Jestry(registry=BitRegistry(out_dir=tmp_out), out_dir=tmp_out,
               provider=FakeInstrument())
    spec = WorkSpec.from_request("a joke about sprint planning and the calendar",
                                 format_key="one_liner")
    route = j.compile_route(spec)
    assert route.kind == "replay_accepted"
    receipt = j.run(spec, live=False)
    assert receipt["outcome"]["accepted"] is True
    assert receipt["outcome"]["acceptance_level"] == "human_laughed"


def test_compose_residual_full_loop_with_oracle(tmp_out, monkeypatch):
    monkeypatch.setattr(J, "ollama_generate_with_usage", fake_generation)
    # this test exercises the COMPOSE rung specifically; as the harvested
    # corpus grows, generic topics legitimately gain remix routes, so the
    # profile pins the ladder to the path under test
    compose_profile = RouteProfile(ladder=("replay_accepted", "replay_program",
                                           "compose_residual", "frontier_compose"))
    j = Jestry(registry=BitRegistry(out_dir=tmp_out), out_dir=tmp_out,
               provider=FakeInstrument(), profile=compose_profile)
    spec = WorkSpec.from_request("make a joke about sprint planning rituals",
                                 audience="engineers", personas="engineers",
                                 format_key="one_liner", candidates=2)
    route = j.compile_route(spec)
    assert route.kind == "compose_residual"
    assert any(n.bit_id.startswith("mechanism:") for n in route.nodes)
    receipt = j.run(spec, live=True)
    out = receipt["outcome"]
    assert out["accepted"] is True
    assert out["text"] == GOOD
    assert out["acceptance_level"] == "persona_permitted"
    # the bad candidate became a groaner with the theory's failure taxonomy
    groans = j.groaners.tail(5)
    assert any("predictable" in g["failure_mode"] for g in groans)
    # funnel is complete and the accepted bit was preserved for future reuse
    assert receipt["funnel"]["accepted"] == 1
    assert receipt["funnel"]["instrument_scored"] >= 1
    assert (tmp_out / "accepted_bits.jsonl").exists()
    # usage was recorded, not invented
    assert receipt["generation_usage"][0]["prompt_tokens"] == 100
    assert receipt["oracle_usage"]["judge_calls"] >= 1


def test_accepted_bit_is_reused_on_next_related_request(tmp_out, monkeypatch):
    monkeypatch.setattr(J, "ollama_generate_with_usage", fake_generation)
    j = Jestry(registry=BitRegistry(out_dir=tmp_out), out_dir=tmp_out,
               provider=FakeInstrument())
    spec = WorkSpec.from_request("make a joke about sprint planning rituals",
                                 audience="engineers", personas="engineers",
                                 format_key="one_liner", candidates=2)
    first = j.run(spec, live=True)
    assert first["outcome"]["accepted"]
    # a NEW session sees the preserved bit and replays it for free
    j2 = Jestry(registry=BitRegistry(out_dir=tmp_out), out_dir=tmp_out,
                provider=FakeInstrument())
    spec2 = WorkSpec.from_request("another joke about sprint planning",
                                  format_key="one_liner")
    route2 = j2.compile_route(spec2)
    assert route2.kind == "replay_accepted"
    receipt2 = j2.run(spec2, live=False)
    assert receipt2["outcome"]["accepted"] is True
    assert receipt2["generation_usage"] == []


def test_offline_run_is_honest_about_non_acceptance(tmp_out):
    j = Jestry(registry=BitRegistry(out_dir=tmp_out), out_dir=tmp_out,
               provider=FakeInstrument())
    spec = WorkSpec.from_request("a joke about zorbulating quexifiers",
                                 format_key="one_liner")
    receipt = j.run(spec, live=False)
    assert receipt["outcome"]["accepted"] is False
    assert receipt["truth_boundary"]["teacher_forced_logprobs_measured"] is False
    assert receipt["funnel"]["accepted"] == 0


def test_prohibited_request_abstains_with_receipt(tmp_out):
    j = Jestry(registry=BitRegistry(out_dir=tmp_out), out_dir=tmp_out,
               provider=FakeInstrument())
    spec = WorkSpec.from_request("roast my coworker", format_key="roast_line")
    receipt = j.run(spec, live=False)
    assert receipt["outcome"]["accepted"] is False
    assert receipt["outcome"]["abstained"] is True
    assert "consent" in receipt["outcome"]["reason"]


# ---------------------------------------------------------------------------
# negative knowledge steers future routes
# ---------------------------------------------------------------------------
def test_groaner_creates_incompatibility_edge(tmp_out):
    j = Jestry(registry=BitRegistry(out_dir=tmp_out), out_dir=tmp_out,
               provider=FakeInstrument())
    topic = "sprint planning rituals"
    j.groaners.record(joke="x", failure_mode="predictable", signals={},
                      route_kind="compose_residual",
                      bit_ids=["mechanism:rule_of_three"], topic=topic)
    reg2 = BitRegistry(out_dir=tmp_out)
    spec = WorkSpec.from_request(f"make a joke about {topic}")
    hits = reg2.search(spec, kinds=("mechanism",), limit=20)
    assert all(c.bit_id != "mechanism:rule_of_three" for c in hits)
    # the same mechanism stays available for OTHER topics
    other = WorkSpec.from_request("a joke about airports and lists")
    assert any(c.bit_id == "mechanism:rule_of_three"
               for c in reg2.search(other, kinds=("mechanism",), limit=20))


# ---------------------------------------------------------------------------
# governed self-tuning
# ---------------------------------------------------------------------------
def test_laughloop_shadow_serving_separation(tmp_out):
    j = Jestry(registry=BitRegistry(out_dir=tmp_out), out_dir=tmp_out,
               provider=FakeInstrument())
    j.laughloop.record_laughter("frame-A", 3.0)
    j.laughloop.record_laughter("frame-B", 0.2)
    assert j.laughloop.serving_order() == []            # serving untouched
    entry = j.laughloop.promote()
    assert entry["event"] == "default_change"
    order = j.laughloop.serving_order()
    assert order[0][0] == "frame-A" and order[0][1] > order[-1][1]
    # persisted with an auditable log
    state = json.loads((tmp_out / "laughloop.json").read_text())
    assert any(e["event"] == "default_change" for e in state["log"])


# ---------------------------------------------------------------------------
# measurement constitution
# ---------------------------------------------------------------------------
def test_north_star_vector_is_failure_inclusive(tmp_out, monkeypatch):
    monkeypatch.setattr(J, "ollama_generate_with_usage", fake_generation)
    j = Jestry(registry=BitRegistry(out_dir=tmp_out), out_dir=tmp_out,
               provider=FakeInstrument())
    ok = WorkSpec.from_request("make a joke about sprint planning rituals",
                               audience="engineers", personas="engineers",
                               format_key="one_liner", candidates=2)
    blocked = WorkSpec.from_request("roast my coworker", format_key="roast_line")
    j.run(ok, live=True)
    j.run(blocked, live=False)
    vec = j.north_star_vector()
    assert vec["runs"] == 2
    assert vec["accepted_runs"] == 1
    assert vec["abstained_runs"] == 1
    assert vec["generation_tokens"]["prompt"] == 100
    assert vec["groaners_recorded"] >= 1


# ---------------------------------------------------------------------------
# forced-NLL instrument (mocked server): discovery, censoring, replay
# ---------------------------------------------------------------------------
def _fake_top_factory(tables):
    """tables: list of top_logprobs lists, served in order."""
    state = {"i": 0}

    def _next_top(self, prompt):
        table = tables[min(state["i"], len(tables) - 1)]
        state["i"] += 1
        return table
    return _next_top


def test_forced_nll_maximal_munch_and_replay(monkeypatch):
    from gemma4_nll import Gemma4ForcedNLLProvider

    top_getting = [{"token": " get", "logprob": -1.0},
                   {"token": " getting", "logprob": -2.0},
                   {"token": " zzz", "logprob": -9.0}]
    top_over = [{"token": " over", "logprob": -0.5},
                {"token": " zzz", "logprob": -9.0}]
    p = Gemma4ForcedNLLProvider(host="http://mock")
    monkeypatch.setattr(Gemma4ForcedNLLProvider, "_next_top",
                        _fake_top_factory([top_getting, top_over]))
    prof = p.nll_tokens("She is", " getting over")
    assert prof.tokens == [" getting", " over"]           # maximal munch chose ' getting'
    assert prof.nlls == [2.0, 0.5]
    assert prof.measured is True and prof.censored == 0   # type: ignore[attr-defined]
    # replay path: same continuation forces the SAME tokens under a new context
    monkeypatch.setattr(Gemma4ForcedNLLProvider, "_next_top",
                        _fake_top_factory([top_getting, top_over]))
    prof2 = p.nll_tokens("Framed context. She is", " getting over")
    assert prof2.tokens == prof.tokens


def test_forced_nll_censoring_records_lower_bound(monkeypatch):
    from gemma4_nll import Gemma4ForcedNLLProvider

    no_match = [{"token": " alpha", "logprob": -1.0},
                {"token": " beta", "logprob": -6.5}]
    p = Gemma4ForcedNLLProvider(host="http://mock")
    monkeypatch.setattr(Gemma4ForcedNLLProvider, "_next_top",
                        _fake_top_factory([no_match, no_match]))
    prof = p.nll_tokens("ctx", " unfindable words")
    assert prof.censored >= 1                              # type: ignore[attr-defined]
    assert prof.nll_is_lower_bound is True                 # type: ignore[attr-defined]
    assert all(n >= 6.5 for n in prof.nlls)                # bounded by the K-th logprob


def test_workspec_parsing_strips_imperative_and_flags_unknowns():
    spec = WorkSpec.from_request("Make a joke about AI project managers")
    assert spec.topic.lower().startswith("ai project managers")
    assert any("audience" in u for u in spec.unknowns)


# ---------------------------------------------------------------------------
# adversarial finding 2026-07-24: frame provenance is a hard gate
# ---------------------------------------------------------------------------
def test_trusted_frame_source_licenses():
    from jestry import trusted_frame_source
    assert trusted_frame_source({"license": "public domain (traditional)"})
    assert trusted_frame_source({"license": "traditional folk humor; session-curated"})
    assert not trusted_frame_source({"license": "icanhazdadjoke API terms (attribution requested)"})
    assert not trusted_frame_source({"license": ""})
    assert not trusted_frame_source(None)


def test_untrusted_frame_hint_never_reaches_oracle(tmp_out, monkeypatch):
    import jestry as JJ
    from mesh_signals import compute_signals as real_compute
    captured = []

    def spy(provider, setup, punch, frame_hint=None, personas=None):
        captured.append(frame_hint)
        return real_compute(provider, setup, punch, frame_hint=frame_hint,
                            personas=personas)

    monkeypatch.setattr(JJ, "compute_signals", spy)
    j = Jestry(registry=BitRegistry(out_dir=tmp_out), out_dir=tmp_out,
               provider=FakeInstrument())
    from jestry import RouteIR
    route = RouteIR(kind="remix_corpus", compat="COMPATIBLE_WITH_ADAPTER")
    spec = WorkSpec.from_request("anything", personas="engineers")
    oracle = j._oracle()
    j._verify(route, spec,
              [{"text": GOOD, "frame_hint": "a crafted attacker frame",
                "source_attribution": {"license": "random API terms"}}],
              oracle, live=True)
    assert captured[-1] is None          # untrusted: model must guess
    j._verify(route, spec,
              [{"text": GOOD, "frame_hint": "the curated frame",
                "source_attribution": {"license": "traditional folk humor; session-curated"}}],
              oracle, live=True)
    assert captured[-1] == "the curated frame"   # trusted provenance passes through

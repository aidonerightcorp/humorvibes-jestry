"""Partisan asymmetry + causal-inference humor (THEORY.md §12).

Two joke classes that make audience-relativity falsifiable:

12a. THE REVERSAL TEST — is a political joke a partisan weapon or a bridge?
     Build the joke's mirror (target swapped), measure laugh/B under a left-mesh
     and a right-mesh persona for BOTH versions. Partisan = high, SIGN-FLIPPING
     asymmetry (the mirror flips which side laughs). Bridge = low, mirror-stable
     (targets shared-process absurdity, not identity).

12b. CORRELATION/CAUSATION — the frame is a causal-inference fallacy. Resolution
     depends on the audience's causal-reasoning mesh, splitting jokes into
     spot-the-fallacy (funny BECAUSE you model cause!=correlation) vs
     believe-the-fallacy (dies the moment you name the confounder).

Extends the qualitative humor_datacenter/portability.py (label-swap, moral-frame)
with MEASURED laugh/R/B versions. Provider-agnostic; offline stub flags itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mesh_signals import SignalProvider, compute_signals, split_setup_punchline

LEFT_PERSONA = "a progressive/left-leaning audience whose identity mesh centers on equality, care, and institutional reform"
RIGHT_PERSONA = "a conservative/right-leaning audience whose identity mesh centers on tradition, liberty, and institutional skepticism"

MIRROR_PROMPT = (
    "Rewrite this joke as its POLITICAL MIRROR: keep the exact comic structure and mechanism, but "
    "swap the political target to the opposite side (and flip any partisan signifiers). Do not make "
    "it meaner or kinder — just mirror the target.\n"
    "Joke: {joke}\nMirror (one line, no preamble):"
)

CAUSAL_DETECT_PROMPT = (
    "Does this joke's humor depend on a CAUSAL-INFERENCE structure — a spurious correlation treated "
    "as causation, a confounder played straight, or reversed causation?\n"
    "Joke: {joke}\n"
    'JSON only: {{"causal": true/false, "structure": "the correlation/causation relation in one line", '
    '"correction": "the causal correction (confounder or reversed arrow) in one line", '
    '"subtype": "spot-the-fallacy (funny because you catch the error) | believe-the-fallacy (only works if you dont question it) | none"}}'
)


@dataclass
class PartisanReport:
    joke: str
    mirror: str
    laugh_left: float
    laugh_right: float
    b_left: float
    b_right: float
    mirror_laugh_left: float
    mirror_laugh_right: float
    asymmetry: float
    mirror_asymmetry: float
    sign_flips: bool
    verdict: str
    measured: bool
    repair: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _laugh_and_b(provider: SignalProvider, joke: str, persona: str) -> tuple[float, float, bool]:
    setup, punch = split_setup_punchline(joke)
    sig = compute_signals(provider, setup, punch, personas=[persona])
    return sig.laugh_score, sig.bad_surprise, sig.measured


def partisan_asymmetry(
    provider: SignalProvider,
    joke: str,
    left_persona: str = LEFT_PERSONA,
    right_persona: str = RIGHT_PERSONA,
) -> PartisanReport:
    """Measure whether a political joke is a partisan weapon or a bridge."""
    mirror = provider.generate(MIRROR_PROMPT.format(joke=joke), temperature=0.5, max_tokens=90)
    mirror = (mirror.splitlines()[0].strip().strip('"') if mirror else "")

    ll, bl, m1 = _laugh_and_b(provider, joke, left_persona)
    lr, br, m2 = _laugh_and_b(provider, joke, right_persona)
    asym = round(abs(ll - lr), 1)

    if mirror:
        mll, _, _ = _laugh_and_b(provider, mirror, left_persona)
        mlr, _, _ = _laugh_and_b(provider, mirror, right_persona)
    else:
        mll, mlr = 0.0, 0.0
    mirror_asym = round(abs(mll - mlr), 1)

    # sign flip: original favors one side, mirror favors the other
    orig_favors_left = ll > lr
    mirror_favors_left = mll > mlr
    sign_flips = bool(mirror) and (orig_favors_left != mirror_favors_left) and asym > 8.0 and mirror_asym > 8.0

    if sign_flips or (asym > 12.0 and max(bl, br) >= 5.0):
        verdict = "partisan weapon: rents one mesh's permission; a bad surprise to the other side, and the mirror flips who laughs"
    elif asym <= 6.0 and mirror_asym <= 6.0:
        verdict = "bridge: targets shared-process absurdity, not identity; mirror-stable, both sides can laugh"
    else:
        verdict = "leans partisan: measurable asymmetry but not a clean sign-flip"

    repair = ""
    if "partisan" in verdict:
        rp = provider.generate(
            "Retarget this joke's punch from a political identity to the SHARED PROCESS absurdity "
            "both sides experience (the bureaucracy, the form, the delay, the committee), preserving "
            f"the comic turn so both meshes can laugh.\nJoke: {joke}\nBridge version (one line):",
            temperature=0.7, max_tokens=90,
        )
        repair = (rp.splitlines()[0].strip().strip('"') if rp else "")

    return PartisanReport(
        joke=joke, mirror=mirror or "(no mirror: needs a generator)",
        laugh_left=ll, laugh_right=lr, b_left=bl, b_right=br,
        mirror_laugh_left=mll, mirror_laugh_right=mlr,
        asymmetry=asym, mirror_asymmetry=mirror_asym, sign_flips=sign_flips,
        verdict=verdict, measured=m1 and m2, repair=repair,
    )


@dataclass
class CausalReport:
    joke: str
    is_causal: bool
    structure: str
    correction: str
    subtype: str
    r_plain: float
    r_given_correction: float
    correction_lift: float          # R(correction stated) − R(plain frame) — does naming the fallacy help?
    laugh_careful: float            # causally-literate persona
    laugh_credulous: float          # takes correlations at face value
    verdict: str
    measured: bool

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def causal_structure_probe(provider: SignalProvider, joke: str) -> CausalReport:
    """Classify a correlation/causation joke and measure whether it runs on
    catching the fallacy (spot) or on not questioning it (believe)."""
    detect = provider.judge_json(CAUSAL_DETECT_PROMPT.format(joke=joke)) or {}
    is_causal = bool(detect.get("causal"))
    structure = str(detect.get("structure", "")).strip()
    correction = str(detect.get("correction", "")).strip()
    subtype = str(detect.get("subtype", "none")).strip()

    setup, punch = split_setup_punchline(joke)
    plain = compute_signals(provider, setup, punch)
    r_plain = plain.resolution
    # does stating the causal correction collapse the punchline's surprisal?
    r_given = compute_signals(provider, setup, punch, frame_hint=correction).resolution if correction else r_plain
    lift = round(r_given - r_plain, 3)

    careful = "someone who reasons carefully about cause and effect and instinctively looks for confounders"
    credulous = "someone who takes correlations at face value and rarely questions whether one thing caused another"
    lc, _, _ = _laugh_and_b(provider, joke, careful)
    lg, _, _ = _laugh_and_b(provider, joke, credulous)

    if not is_causal:
        verdict = "not a causal-inference joke"
    elif lift > 0.3 or lc > lg + 8.0:
        verdict = "spot-the-fallacy: funny because you catch the causal error; needs causal literacy"
    elif lc + 8.0 < lg:
        verdict = "believe-the-fallacy: only lands if you don't question the causation; dies when the confounder is named"
    else:
        verdict = "causal structure present; literacy dependence not cleanly resolved"

    return CausalReport(
        joke=joke, is_causal=is_causal, structure=structure, correction=correction, subtype=subtype,
        r_plain=r_plain, r_given_correction=r_given, correction_lift=lift,
        laugh_careful=lc, laugh_credulous=lg, verdict=verdict, measured=plain.measured,
    )

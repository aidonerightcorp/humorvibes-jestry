"""The Humor Genome: one unified measured readout across every dimension.

The project's probes each measure one facet; this is the synthesis — given a
joke, it runs the relevant probes and returns a single "genome card": the
measured signals (S/R/E/B), the vibe (register + openness), the temporal cache
it rents, and — auto-routed only when applicable — partisan asymmetry, causal-
inference structure, and (for hostile input) a de-escalation off-ramp.

Auto-routing keeps it cheap and honest: a clean one-liner doesn't pay for a
political mirror; a non-causal joke skips the causal probe. Every facet flags
measured vs. skipped vs. offline, so the card never over-claims. Degrades
gracefully to the offline stub; comes fully alive on the Kaggle instrument or a
hosted provider.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mesh_signals import SignalProvider, compute_signals, split_setup_punchline
import vibe as vibe_mod


POLITICAL_MARKERS = (
    "politic", "congress", "senate", "president", "vote", "party", "liberal", "conservative",
    "left-wing", "right-wing", "democrat", "republican", "election", "government", "tax", "policy",
)
CAUSAL_MARKERS = ("because", "so ", "correlat", "causes", "every time", "whenever", "lucky", "since ")
HOSTILE_MARKERS = ("you're an", "you are an", "shut up", "idiot", "stupid", "pathetic", "do you even")


def _looks(text: str, markers) -> bool:
    low = text.lower()
    return any(m in low for m in markers)


@dataclass
class HumorGenome:
    joke: str
    laugh_score: float
    surprise: float
    resolution: float
    efficiency: float
    bad_surprise: float
    failure_mode: str
    frame: str
    vibe_address: str
    openness: float | None
    facets: dict[str, Any] = field(default_factory=dict)   # routed probe results
    routed: list[str] = field(default_factory=list)
    measured: bool = True

    def card(self) -> str:
        """Human-readable one-screen genome card."""
        lines = [
            f"HUMOR GENOME  —  laugh {self.laugh_score}/100" + ("" if self.measured else "  [offline stub]"),
            f"  signals   S={self.surprise:.2f} R={self.resolution:.2f} E={self.efficiency:.3f} B={self.bad_surprise:.1f}",
            f"  diagnosis {self.failure_mode}",
            f"  frame     {self.frame or '(none found)'}",
            f"  vibe      {self.vibe_address}" + (f" | openness {self.openness:.2f} nats" if self.openness is not None else ""),
        ]
        for name in self.routed:
            f = self.facets.get(name, {})
            if name == "temporal":
                lines.append(f"  temporal  {f.get('cache_verdict', '?')}")
            elif name == "politics":
                lines.append(f"  politics  {f.get('verdict', '?')} (asym {f.get('asymmetry', '?')})")
            elif name == "causal":
                lines.append(f"  causal    {f.get('verdict', '?')}")
            elif name == "deescalation":
                b = f.get("best") or {}
                lines.append(f"  off-ramp  {b.get('reply', '(none)')[:70]}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def analyze(
    provider: SignalProvider,
    joke: str,
    audience: str | None = None,
    personas: list[str] | None = None,
    fact: str | None = None,
    force: list[str] | None = None,
) -> HumorGenome:
    """Run the core signals + vibe always; auto-route the specialized probes."""
    setup, punch = split_setup_punchline(joke)
    sig = compute_signals(provider, setup, punch, personas=personas or ([audience] if audience else []))
    room = audience or "a general audience"
    joke_vibe = vibe_mod.vibe_profile(provider, joke)

    g = HumorGenome(
        joke=joke,
        laugh_score=sig.laugh_score,
        surprise=sig.surprise_mean,
        resolution=sig.resolution,
        efficiency=sig.efficiency,
        bad_surprise=sig.bad_surprise,
        failure_mode=sig.failure_mode,
        frame=sig.frame_hint,
        vibe_address=joke_vibe.address(),
        openness=joke_vibe.openness,
        measured=sig.measured,
    )

    force = force or []
    # temporal: route if a fact is given or the joke names an event/canon
    if fact or "temporal" in force:
        try:
            import temporal
            tp = temporal.temporal_profile(provider, joke, fact or joke)
            g.facets["temporal"] = tp.to_dict(); g.routed.append("temporal")
        except Exception:
            pass
    # politics: route if political markers present
    if _looks(joke, POLITICAL_MARKERS) or "politics" in force:
        try:
            import symmetry_probe
            pr = symmetry_probe.partisan_asymmetry(provider, joke)
            g.facets["politics"] = pr.to_dict(); g.routed.append("politics")
        except Exception:
            pass
    # causal: route if causal markers present
    if _looks(joke, CAUSAL_MARKERS) or "causal" in force:
        try:
            import symmetry_probe
            cr = symmetry_probe.causal_structure_probe(provider, joke)
            if cr.is_causal or "causal" in force:
                g.facets["causal"] = cr.to_dict(); g.routed.append("causal")
        except Exception:
            pass
    # de-escalation: route if the input reads as a hostile comment to respond to
    if _looks(joke, HOSTILE_MARKERS) or "deescalation" in force:
        try:
            import deescalate
            dr = deescalate.deescalate(provider, joke, context=audience or "")
            g.facets["deescalation"] = dr; g.routed.append("deescalation")
        except Exception:
            pass
    return g


if __name__ == "__main__":
    from mesh_signals import get_provider
    p = get_provider()
    for j in [
        "I told my therapist about my fear of speed bumps. She said I'm slowly getting over it.",
        "Congress found a bipartisan solution: both sides agreed the printer was the real problem.",
        "Ice cream sales and shark attacks both peak in July, so clearly ice cream is chumming the water.",
    ]:
        g = analyze(p, j)
        print(g.card())
        print("  routed:", g.routed, "\n")

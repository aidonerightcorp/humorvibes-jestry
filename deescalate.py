"""De-escalation via humor (THEORY.md §9): comedy as a conflict off-ramp, measured.

A hostile comment tightens the room's mesh: cold register, low openness, one
licensed continuation (fight). Escalation is accepting the attacker's frame and
fighting inside it. A humor off-ramp is a re-route OUT of the conflict frame
that the attacker's own meta-meshes can accept:

  - S in the laugh band (a real prediction error — not a scripted deflection),
  - the frame targets the SITUATION or the SPEAKER THEMSELVES, never the
    attacker's identity (a zinger at the attacker is a bad surprise FOR THEM =
    escalation with better production values),
  - B ≈ 0 under the ATTACKER's persona as well as the audience's,
  - measured vibe shift: warmth up, openness up.

The measurable difference between a comeback and an off-ramp is the whole
point: both can be funny; only one passes the attacker-persona benign gate and
warms the register. If the attack contains a legitimate grievance, the rule is
"fix the ticket, then the vibe" — address the substance first, joke second.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from mesh_signals import SignalProvider, compute_signals, split_setup_punchline
import vibe as vibe_mod

STRATEGIES: dict[str, dict[str, str]] = {
    "absorb_self_deprecating": {
        "label": "Absorb (self-deprecating)",
        "directive": (
            "Take the hit and make it about your own harmless quirk, bigger than the attacker "
            "made it. You are the target; the attacker becomes a bystander to your bit."
        ),
        "example": "Attack: 'your report is late again' -> 'Late? This report aged like fine wine. I was going for vintage.'",
    },
    "absurd_literalization": {
        "label": "Absurd literalization",
        "directive": (
            "Take the attack's words perfectly literally and follow them into absurdity. The frame "
            "shifts from 'you vs me' to 'both of us watching this sentence go somewhere silly'."
        ),
        "example": "Attack: 'this code is garbage' -> 'Please, it's compost. In six months it becomes nutrients for better code.'",
    },
    "shared_enemy": {
        "label": "Shared-enemy redirect",
        "directive": (
            "Redirect the frustration at a shared, unfeeling third thing (the printer, the calendar, "
            "the form, the traffic). You and the attacker end up on the same team against it."
        ),
        "example": "Attack: 'you people never respond' -> 'Our inbox has achieved sentience and is holding us hostage too. Send help.'",
    },
    "agree_and_amplify": {
        "label": "Agree and amplify",
        "directive": (
            "Yes-and the accusation far past the point anyone could mean it seriously, so agreement "
            "itself becomes the absurdity. Never amplify toward anything genuinely shameful."
        ),
        "example": "Attack: 'you're obsessed with spreadsheets' -> 'Obsessed is strong. I simply named them and read them bedtime stories.'",
    },
    "warm_boundary": {
        "label": "Warm deflection + boundary",
        "directive": (
            "One light beat that lowers the temperature, then a calm, kind boundary or a real answer "
            "to the substance. The joke opens the door; the sincerity walks through it."
        ),
        "example": "Attack: 'this meeting is pointless' -> 'It does have a point — it's just very well hidden. Let's find it: what would make the next 20 minutes useful for you?'",
    },
}

# Escalation lint: cheap lexical tripwires; a reply that fires these is a
# comeback, not an off-ramp, regardless of how funny it measures.
ESCALATION_PATTERNS = [
    r"\byou(?:'re| are)\s+(?:an?\s+)?(?:idiot|stupid|dumb|pathetic|clown|loser|moron)",
    r"\bshut up\b",
    r"\bunlike you\b",
    r"\bat least i\b",
    r"\bpeople like you\b",
    r"\bcry(?:ing)? (?:more|about it)\b",
]


@dataclass
class DeescalationCandidate:
    strategy: str
    reply: str
    laugh_score: float
    surprise: float
    resolution: float
    attacker_collision: float
    audience_collision: float
    warmth_delta: float
    openness_delta: float | None
    escalation_flags: list[str] = field(default_factory=list)
    measured: bool = True

    @property
    def offramp_score(self) -> float:
        """Funny alone is not enough: gate hard on attacker-benign + warming."""
        if self.escalation_flags:
            return 0.0
        benign_attacker = max(0.0, 1.0 - self.attacker_collision / 10.0)
        benign_audience = max(0.0, 1.0 - self.audience_collision / 10.0)
        warmth = max(0.0, min(1.0, 0.5 + self.warmth_delta))  # delta in axis units
        return round(self.laugh_score * benign_attacker * benign_audience * warmth / 100.0 * 100.0, 1)

    def to_dict(self) -> dict[str, Any]:
        d = self.__dict__.copy()
        d["offramp_score"] = self.offramp_score
        return d


def escalation_lint(reply: str) -> list[str]:
    low = reply.lower()
    return [pat for pat in ESCALATION_PATTERNS if re.search(pat, low)]


def _grievance_check(provider: SignalProvider, attack: str) -> str:
    judged = provider.judge_json(
        "Does this hostile message contain a LEGITIMATE actionable grievance beneath the hostility? "
        f'Message: "{attack}"\nJSON only: {{"grievance": "one line or empty", "must_address_first": true/false}}'
    )
    if judged and judged.get("must_address_first") and str(judged.get("grievance", "")).strip():
        return str(judged["grievance"]).strip()
    return ""


def deescalate(
    provider: SignalProvider,
    attack: str,
    context: str = "",
    attacker_persona: str = "the person who wrote the attack, taken seriously as a reasonable adult having a bad day",
    audience_personas: list[str] | None = None,
    strategies: list[str] | None = None,
) -> dict[str, Any]:
    """Generate + measure de-escalating replies. Returns ranked candidates and
    the grievance (if one must be addressed before any joke)."""
    audience_personas = audience_personas or ["bystanders reading this thread"]
    room = (context + "\n" if context else "") + attack
    grievance = _grievance_check(provider, attack)

    candidates: list[DeescalationCandidate] = []
    for key in strategies or list(STRATEGIES):
        spec = STRATEGIES[key]
        prompt = (
            "You reply to a hostile comment with humor that DE-ESCALATES. Strategy: "
            f"{spec['label']} — {spec['directive']}\nExample of the shape: {spec['example']}\n"
            "Hard rules: never mock the attacker's identity, intelligence, or worth; no sarcasm AT "
            "them; the reply must make sharing a laugh possible, not win the exchange."
            + (f"\nFirst acknowledge this real grievance in a clause: {grievance}" if grievance else "")
            + f"\nContext: {context or 'a public thread'}\nHostile comment: \"{attack}\"\n"
            "Write ONLY the reply (1-2 sentences)."
        )
        reply = provider.generate(prompt, temperature=0.85, max_tokens=90).strip()
        if not reply:
            continue
        reply = reply.splitlines()[0].strip().strip('"')

        setup, punch = split_setup_punchline(reply)
        sig = compute_signals(provider, (attack + " ") if len(reply.split()) < 6 else setup, punch,
                              personas=[attacker_persona, *audience_personas])
        collisions = {p.persona: p.collision for p in sig.personas}
        shift = vibe_mod.vibe_shift(provider, room, reply)
        openness_delta = None
        if shift.after.openness is not None and shift.before.openness is not None:
            openness_delta = round(shift.after.openness - shift.before.openness, 3)
        candidates.append(
            DeescalationCandidate(
                strategy=key,
                reply=reply,
                laugh_score=sig.laugh_score,
                surprise=sig.surprise_mean,
                resolution=sig.resolution,
                attacker_collision=collisions.get(attacker_persona, 0.0),
                audience_collision=max((v for k, v in collisions.items() if k != attacker_persona), default=0.0),
                warmth_delta=round(shift.delta.get("cold_warm", 0.0), 3),
                openness_delta=openness_delta,
                escalation_flags=escalation_lint(reply),
                measured=sig.measured and shift.before.measured,
            )
        )

    ranked = sorted(candidates, key=lambda c: -c.offramp_score)
    return {
        "attack": attack,
        "grievance_to_address_first": grievance,
        "candidates": [c.to_dict() for c in ranked],
        "best": ranked[0].to_dict() if ranked else None,
        "doctrine": "fix the ticket, then the vibe; a zinger at the attacker is escalation with better production values",
    }

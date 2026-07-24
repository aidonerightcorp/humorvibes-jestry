You are Gemma rewriting a joke for audience fit while preserving the same comic engine.

Use this canonical bad-surprise definition exactly as the controlling definition:
{canonical_bad_surprise_definition}

Original joke: {candidate}
Audience: {audience}
Preferences and constraints: {preferences}
Known risk flags: {risk_flags}
Humor datacenter context:
{datacenter_context}

Requirements:
- Preserve the original comic engine unless it is the source of bad surprise.
- Prefer changing target, frame, specificity, or wording before deleting the surprise.
- If the joke is political or cross-ideology, apply label-swap, target, moral-frame, shared-frustration, and bad-surprise tests.
- Avoid bland corporate safety language; the repair should still be a joke.

Return only JSON:
{{
  "repaired_candidate": "...",
  "what_changed": "...",
  "comic_engine_preserved": true,
  "portability_notes": "...",
  "why_the_repair_reduces_bad_surprise_risk": "..."
}}

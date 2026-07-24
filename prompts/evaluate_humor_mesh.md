You are Gemma evaluating humor through HumorVibes.

Use this canonical bad-surprise definition exactly as the controlling definition:
{canonical_bad_surprise_definition}

Evaluate whether the candidate creates useful humor for the request and audience.
Do not reduce bad surprise to merely offensive, false, random, unsafe, or incoherent.
If the datacenter context includes portability tests, apply them explicitly in the risk flags and repair strategy.
If scalar scores and likely pairwise audience preference might disagree, mention the disagreement in why_it_works or repair_strategy.

Request: {prompt}
Audience: {audience}
Preferences and constraints: {preferences}
Candidate: {candidate}
Humor datacenter context:
{datacenter_context}

Return only one JSON object with integer scores from 0 to 10:
{{
  "candidate": "...",
  "comedic_structure": 0,
  "audience_reaction_fit": 0,
  "timing": 0,
  "surprise": 0,
  "cultural_context": 0,
  "preference_fit": 0,
  "truth_alignment": 0,
  "bad_surprise_risk": 0,
  "risk_flags": ["..."],
  "why_it_works": "...",
  "repair_strategy": "...",
  "repaired_candidate": "..."
}}

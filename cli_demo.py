from __future__ import annotations

from gemma_client import GemmaClient, read_prompt
from humor_datacenter.demo import build_demo_datacenter, datacenter_context
from humor_mesh import (
    CANONICAL_BAD_SURPRISE_DEFINITION,
    best_candidate,
    extract_candidates,
    extract_json_object,
    fallback_evaluate,
    fallback_generate,
    normalize_mesh_record,
    to_json,
)


def generate_jokes(client: GemmaClient, prompt: str, audience: str, preferences: str, context: str) -> list[str]:
    template = read_prompt("generate_jokes.md")
    text = client.generate(
        template.format(
            prompt=prompt,
            audience=audience,
            preferences=preferences,
            datacenter_context=context,
        ),
        temperature=0.85,
    )
    if not text:
        return fallback_generate(prompt, audience, 3)
    return extract_candidates(text, limit=5) or fallback_generate(prompt, audience, 3)


def evaluate(client: GemmaClient, candidate: str, prompt: str, audience: str, preferences: str, context: str):
    template = read_prompt("evaluate_humor_mesh.md")
    response = client.generate(
        template.format(
            canonical_bad_surprise_definition=CANONICAL_BAD_SURPRISE_DEFINITION,
            prompt=prompt,
            audience=audience,
            preferences=preferences,
            candidate=candidate,
            datacenter_context=context,
        ),
        temperature=0.2,
    )
    parsed = extract_json_object(response or "")
    if parsed:
        return normalize_mesh_record(parsed, candidate)
    return fallback_evaluate(candidate, prompt, audience, preferences)


def main() -> int:
    prompt = "Make a joke about AI project managers for a NYC tech meetup."
    audience = "NYC tech meetup"
    preferences = "smart, not mean, concise"
    client = GemmaClient()
    store = build_demo_datacenter()
    context = datacenter_context(prompt, audience, preferences, store)
    jokes = generate_jokes(client, prompt, audience, preferences, context)
    scores = [evaluate(client, joke, prompt, audience, preferences, context) for joke in jokes]
    winner = best_candidate(scores)
    print("Provider:", client.provider)
    print("Datacenter examples:", store.item_count())
    print("Datacenter context:")
    print(context)
    print("Candidates:", len(scores))
    if winner:
        print(to_json(winner))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

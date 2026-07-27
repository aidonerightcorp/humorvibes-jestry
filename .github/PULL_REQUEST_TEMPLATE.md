## What changed

Describe the smallest reviewable change and the roadmap or issue it addresses.

## Evidence boundary

- What does this result or artifact establish?
- What does it not establish?
- Are any source, licence, label, model, split, or public-state claims changing?

## Verification

List the exact commands run and their outcomes. Include relevant receipt paths.

```text
python3 -m pytest -q
git diff --check
```

## Data and provenance

State the upstream source, observed schema, licence, redistribution class, and fixture coverage for
new data. Write “No data change” when this does not apply.

## Checklist

- [ ] I kept model surprisal separate from human funniness.
- [ ] I added positive and negative regression coverage where behavior changed.
- [ ] I used a group-held-out split where rows share context.
- [ ] I reported uncertainty and retained null or failed arms.
- [ ] I did not commit generated corpus payloads, credentials, or private text.
- [ ] I updated reader-facing documentation and receipts when a claim changed.
- [ ] I did not call an upload public or working without live verification.

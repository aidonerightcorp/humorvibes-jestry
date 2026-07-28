# Native-language form contributions

*Role: the one-language-per-PR native review contract (issues #5, #20–#26). Audience: native/fluent reviewers.*

The taxonomy may accept a new language-specific form only when a human who is native or fluent in
the named locale reviews one bounded contribution. A model, machine-translation service, country
code, or contributor name is not a reviewer.

## One language per pull request

Each pull request must contain exactly one `language` and one narrowly scoped `form_id`. The
current priority queue is
[Portuguese](https://github.com/aidonerightcorp/humorvibes-jestry/issues/20),
[Greek](https://github.com/aidonerightcorp/humorvibes-jestry/issues/22),
[Amharic](https://github.com/aidonerightcorp/humorvibes-jestry/issues/23),
[Japanese](https://github.com/aidonerightcorp/humorvibes-jestry/issues/21),
[Italian](https://github.com/aidonerightcorp/humorvibes-jestry/issues/24),
[Arabic](https://github.com/aidonerightcorp/humorvibes-jestry/issues/26), and
[Turkish](https://github.com/aidonerightcorp/humorvibes-jestry/issues/25); the umbrella tracker is
[#5](https://github.com/aidonerightcorp/humorvibes-jestry/issues/5).
Separate pull requests preserve reviewer accountability and make false-positive regressions easy
to isolate.

The JSON bundle accepted by `humorvibes native-fixture-validate` requires:

- at least 20 permission-confirmed positive fixtures and 20 confusing negatives;
- one Python regex whose observed result matches every reviewed expectation;
- a dated source snapshot, revision, SHA-256, HTTPS licence evidence, and an explicitly
  redistributable licence ID;
- a pseudonymous reviewer attestation describing fluency, conflicts, review date, and consent to
  publish the attestation;
- an explicit statement that machine translation did not make the acceptance decision;
- before/after corpus coverage and a manually reviewed false-positive sample of at least 20
  matches, or every match when fewer exist;
- aligned-pair consistency counts when translations are available.

Direct identity fields such as names, email addresses, phone numbers, social handles, employers,
and IP addresses fail validation. The public receipt keeps fixture text out and records only
digests, counts, licence, coverage, and the reviewer pseudonym.

## Validation sequence

Place the completed review bundle in a private working directory until permission and identity
checks are complete. Then run:

```bash
humorvibes native-fixture-validate /tmp/native-review.json \
  --out /tmp/native-review-receipt.json
python3 style_taxonomy.py selftest
python3 -m pytest -q
```

After validation, add the reviewed fixture bundle, its body-free receipt, and the specific rule to
the same pull request. Report the exact corpus snapshot and coverage delta. Never broaden the rule
after looking only at positives; hard negatives should share words and punctuation with the target
form without actually instantiating it.

## What a passing receipt establishes

A passing receipt establishes that the contribution has a structurally complete, pseudonymous
human-review attestation; an explicitly redistributable fixture source; enough positive and
negative cases; a regex consistent with those cases; and coverage/error counts for one frozen
corpus snapshot.

It does not independently verify the reviewer's identity, establish human funniness, prove that a
form is universal within the language, or show that the rule generalizes beyond the reviewed
snapshot. Maintainers still review the source evidence and may request a second reviewer.

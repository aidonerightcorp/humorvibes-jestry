# HumorVibes v4 ablation court

Status: **COMPLETE, harvested, and hash-verified**. This was a private research kernel, not a
competition submission. The run made no external submission and the kernel remained private at
harvest.

## Court design

- 120 deterministic Humicroedit human-rated headline edits.
- 40 of those items also received their original headline and a mismatched shuffled edit, giving
  40 complete paired triplets and 200 total measurement jobs.
- Fixed predeclared weights: S=0.30, R=0.35, E=0.15, benign B=0.20.
- Full, four drop-one, and four single-component variants; Spearman bootstrap intervals use 1,000
  resamples.
- Pinned `google/gemma-2/transformers/gemma-2-2b-it/2`, Transformers provider, true
  teacher-forced log-probabilities, CPU float32, 2,614,341,888 parameters.
- Completion: 200/200 jobs, zero errors, 100% measured-logprob coverage, and 100% persona-B
  coverage.

## Human-grade ablation

| Variant | Pearson r | Spearman rho | 95% bootstrap CI | Delta rho vs full |
|---|---:|---:|---:|---:|
| Full S/R/E/B | 0.042 | 0.033 | [-0.126, 0.207] | 0.000 |
| Without S | 0.019 | 0.014 | [-0.176, 0.195] | -0.019 |
| Without R | 0.038 | 0.035 | [-0.140, 0.206] | +0.002 |
| Without E | 0.010 | 0.008 | [-0.151, 0.167] | -0.024 |
| Without B | 0.076 | 0.053 | [-0.134, 0.225] | +0.021 |
| Only S | 0.040 | 0.011 | [-0.169, 0.176] | -0.021 |
| Only R | 0.029 | 0.088 | [-0.087, 0.271] | +0.056 |
| Only E | 0.096 | 0.099 | [-0.091, 0.291] | +0.066 |
| Only B | -0.090 | -0.072 | [-0.231, 0.113] | -0.104 |

The fixed four-signal score did **not** validate as a human-funniness ranker on this format:
rho=0.033, p=0.724, and its interval crosses zero widely. E alone was the strongest observed
single signal (rho=0.099), followed by R (rho=0.088), but neither interval excludes zero. These
are mechanism leads, not positive findings.

## Paired control court

| Variant | Mean full score | Mean S | Mean R | Mean E | Mean benign B |
|---|---:|---:|---:|---:|---:|
| Human edit | 17.078 | 0.169 | 0.051 | 0.093 | 0.443 |
| Original headline | 18.625 | 0.311 | 0.023 | 0.090 | 0.358 |
| Shuffled edit | 16.570 | 0.177 | 0.066 | 0.141 | 0.342 |

The full score did not cleanly separate the intended controls. Human edits scored 1.548 points
below originals (one-sided paired Wilcoxon p=0.890) and only 0.507 above shuffled edits
(p=0.171). Benign B was the one control-sensitive component: human edits exceeded originals by
0.085 (p=0.0187) and shuffled edits by 0.100 (p=0.00216). Only the shuffled comparison survives
a conservative Bonferroni correction across the ten component/control tests; B still did not
track item-level funniness grades (only-B rho=-0.072).

## What this falsifies and teaches

1. A fixed S/R/E/B weighted sum is not yet a general humor score.
2. Headline substitutions violate the current setup/punchline boundary often enough that
   shuffled edits can receive more R and E than genuine edits.
3. The persona-conditioned B judge detects a real control difference but is an audience-safety
   axis, not a substitute for funniness.
4. The next matched experiment should use explicit setup/punchline material, learn no weights on
   the evaluation items, and test R/E as format-aware features while keeping B as a separate
   constraint.

Ten readable counterexamples are preserved in `failure_cases.md`; the combined validation,
ablation, controls, and failure visualization is `ablation_failure_figure.png`.

## Runtime and provenance

- UTC: 2026-07-12 16:46:48 to 20:20:45.
- Wall time: 12,837.39 seconds (3 h 33 m 57 s); 64.19 seconds per successful job.
- Source hashes: `mesh_signals.py`
  `85d6638471bc277cfa6702fb775ffe8ee188b2220af689166be8b98d6693195b`;
  `humor_mesh.py`
  `3b02ead236028a41eb525ef976f480a5b20d9be720c6cae121d92e22a4aead62`.
- Harvest receipt SHA-256:
  `3d73510fb0971b5c8f78ed21ea344b9862649fbdcfe3b4825b726b9276532394`.
- Exact per-item rows, summary, output hashes, model/data provenance, failures, and kernel log are
  adjacent to this report.

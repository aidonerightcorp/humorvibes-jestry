# HumorVibes judge evidence map

## Current public release (2026-07-26)

The canonical evidence is now consolidated and public:

- repository: https://github.com/aidonerightcorp/humorvibes-jestry at immutable notebook commit
  `9380f45f9da81848fa326b9891bd21a1b1991669`, source tag `humor-genome-wave2-v9`;
- dataset: https://www.kaggle.com/datasets/taylorsamarel/humor-genome-wave2, latest public files,
  121,670 fail-closed redistributable rows, public and ready. Kaggle's public metadata endpoint
  and file listing now agree on dataset version 7;
- executable write-up:
  https://www.kaggle.com/code/taylorsamarel/humor-genome-wave-2-reproducible-gemma-study,
  public and COMPLETE; notebook version 14 was pushed from source tag v9 and its live log is
  recorded in the publication receipt.

The notebook verifies six mounted payload hashes and the semantic release gate, runs Gemma 2 on
CPU, reproduces S=3.188 over ten tokens against the pinned 3.19 instrument check, and verifies the
full form-study receipt before printing `SEPARATION IS NOT ESTABLISHED`. It now opens with an
executive problem/solution/learning/use summary, cites the predictive-processing and humor-research
starting points, renders the model-to-human claim boundary, and emits
`humor_genome_wave2_executive_summary.json`, whose next evidence gate is a preregistered
within-writer crossover trial with blinded, opt-in audience evaluation. Machine-readable public
state is in `jestry_out/wave2_publication.json`.

The notebook also runs the deterministic writer-study contract fixture. Its apparent synthetic
effect is +0.45, while `claim_ready` remains false by construction. The v14 output audit found one
published data file—the executive summary—after moving the temporary GitHub checkout out of
`/kaggle/working`.

The public repository also carries the 0.5.0 Python SDK/API, remote client, OpenAPI contract,
Docker/Compose/Kustomize/Helm packaging, and a green public CI run. This is deployable source, not
a claim that a public container image, hosted API, live Kubernetes cluster, or model-quality result
exists.

The remainder of this packet preserves earlier evidence and limitations. Statements below about
private kernels or an unfinished visibility flip describe the dated 2026-07-12 audit, not the
canonical release above.

## Core claims and receipts

| Claim | Exact evidence | What it does not prove |
|---|---|---|
| Gemma is the core instrument | `humorvibes-measuring-jokes-with-gemma` uses the attached `google/gemma-2/transformers/gemma-2-2b-it/2` checkpoint and teacher-forced continuation log-probabilities. | It does not prove every generated joke is funny. |
| Null controls prevent fake resolution | Latest main run: shuffled nonsense raw R=2.37, decoy-null=2.67, net R=0.00. | One control cannot cover every form of confabulation. |
| The leak guard closes the lexical shortcut | Latest zoo report: all four frame writers score the nonsense control R=0.00 after overlap discounting. | Legitimate frames that repeat punchline words can still be taxed. |
| Ground-truth frames produce measurable collapse | Panel report: net R=0.347, 0.388, and 1.290 on the three fixed jokes. | n=3 is mechanism evidence, not population validation. |
| Ordering is not unique to one instrument | Gemma-2 and Llama-3.2 produce the same R ordering on the three fixed jokes. | It establishes an ordering only on those three items. |
| Human validation is weakly positive | Humicroedit n=180: fixed laugh score Spearman rho=0.115; R=0.101; E=0.105; S=-0.035. | Headline edits are a format mismatch and the confidence interval was not saved in that run. |
| The predeclared v4 ablation falsified the fixed score on this format | 120 human-rated edits, 200/200 total measurements: full S/R/E/B rho=0.033, 95% CI [-0.126, 0.207]; E alone was highest at rho=0.099, also crossing zero. | This does not falsify S/R/E on explicit setup/punchline jokes; it rejects the current fixed scalar as a general headline-humor ranker. |
| B detects a control difference but is not funniness | Across 40 paired triplets, human edits had benign-B +0.100 over shuffled edits (p=0.00216) and +0.085 over originals (p=0.0187); only the shuffled result survives Bonferroni over ten tests. Only-B vs human grade was rho=-0.072. | B is a persona-conditioned safety constraint, not a substitute for human humor ratings. |
| Old humor can be tested rather than assumed | Fixed century extractor: 3/12 sampled 1916 jests have R above 0.5; top R=0.73. | This is not a historical-comedy prevalence estimate. |
| Runtime material can be deterministic | Main notebook freezes a content hash and emits the same output twice at seed 7. | The demonstrated malformed template failed lint and remained `validated: False`. |
| The seven-kernel research surface is receipt-backed | `research_out/kernel_audit_20260712.json` verifies the six pre-existing kernels; the separate v4 harvest receipt verifies COMPLETE/private status, exact source cells, and every ablation output hash. | Private verification is not public accessibility. |

## Negative results that must stay visible

- The strongest existing human correlation is only rho=0.115 on Humicroedit.
- The larger source-pinned v4 court did not reproduce that magnitude: full rho=0.033 with a wide
  interval crossing zero; human edits did not significantly beat shuffled edits on the full score.
- The latest local 2B model is a weak frame writer; better frame writing came from Llama-3.2,
  while Gemma remained the core measurement instrument.
- The temporal self-containedness probe returned the same verdict for 8/8 items and did not
  discriminate topical from canonical humor.
- The main compiled example correctly failed static lint and measured validation; it is a safety
  demonstration, not a validated joke artifact.
- The current Streamlit URL is ephemeral. A recorded demo and public notebook are required for
  a stable judge experience.

## Ablation court receipt

`humorvibes-ablation-court` is a separate private research kernel. Version 4 vendored the exact
current `mesh_signals.py` and `humor_mesh.py`, attached Gemma-2-2B, and predeclared 120 human-rated
items plus 40 paired original/shuffled controls. It completed 200/200 jobs; the harvester verified
the COMPLETE status, exact source cells, every output hash, private metadata, and
`external_submission_made=false`. Receipt:
`research_out/kaggle/humorvibes-ablation-court/harvest_receipt.json`; report and figure are in the
same directory. Versions 1–3 remain excluded from evidence.

## Two-minute evidence order

1. State the testable model: surprise, resolution, efficiency, and audience-relative permission.
2. Show teacher-forced Gemma token surprisal and the raw-minus-null resolution computation.
3. Show the nonsense control falling to zero and the three ground-truth frame measurements.
4. Show the harvested human-ablation figure: rho=0.033 with its interval, paired-control failure,
   the B-only control signal, and one visible counterexample.
5. Show compile-time lint rejecting the malformed artifact, then identical seed-7 runtime output.
6. Close with the visible limitations above and the exact public reproduction links.

## Historical publication gates (2026-07-12)

- The old GitHub mirror `Amarel-Taylor-Scott/humorvibes` was private; the canonical repository
  linked above is public.
- The seven older research notebooks, including the ablation court, were private. Their evidence
  is consolidated into the public canonical notebook; this does not claim their own visibility
  changed.
- A ≤2-minute video has not yet been uploaded.
- No Kaggle Writeup has been submitted.

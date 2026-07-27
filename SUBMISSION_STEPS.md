# Archived Humor Genome NYC submission steps

> **Archive, not an active checklist.** The competition deadline passed and no submission is
> claimed. Do not follow the deadline or visibility instructions below. Current public state lives
> in [`PROJECT_STATUS.md`](PROJECT_STATUS.md); the canonical executable study is the
> [public Kaggle notebook](https://www.kaggle.com/code/taylorsamarel/humor-genome-wave-2-reproducible-gemma-study).

> **2026-07-26 historical publication snapshot:** the single canonical implementation was
> https://github.com/aidonerightcorp/humorvibes-jestry at
> `humor-genome-wave2-v4` (`abb7fab`); the fail-closed dataset is public and ready at
> https://www.kaggle.com/datasets/taylorsamarel/humor-genome-wave2 (version 5); and the
> consolidated executable write-up is public and COMPLETE at
> https://www.kaggle.com/code/taylorsamarel/humor-genome-wave-2-reproducible-gemma-study. Anonymous
> requests returned HTTP 200 for all three surfaces. The older state audits below are preserved
> as history. Public artifacts do not by themselves prove that a competition Writeup or video
> was submitted.

> **2026-07-24 addendum (Jestry round):** the code now ALSO lives in a PUBLIC
> GitHub repo - https://github.com/aidonerightcorp/humorvibes-jestry - which
> satisfies the "public code repo" requirement immediately (no visibility flip
> needed). A competition-attached wrapper kernel
> (`taylorsamarel/humorvibes-jestry-demo-github-wrapper`) clones it and ran
> COMPLETE: charter, replay receipt, measured S=3.19 on the attached Gemma,
> been-done demo, metric self-test. When creating the Writeup tonight, attach:
> the GitHub repo URL above, the main measurement notebook, the wrapper demo
> kernel, and paste WRITEUP.md (+ optionally JESTRY_WRITEUP.md as a section).
> The private GitHub mirror flip (step 4 below) becomes optional.

**Submission deadline: the authenticated API now reports 2026-07-26 04:00 UTC.**

Re-queried 2026-07-24 23:48 UTC via `KaggleApi.competitions_list(search="humor-genome-nyc")`,
which returns `deadline: 2026-07-26 04:00:00` AND `merger_deadline: 2026-07-26 04:00:00` (two
independent fields agreeing), against `enabled_date: 2026-07-02`. Earlier notes in this file said
2026-07-25 04:00 UTC, recorded from the same API on 2026-07-12; that may have been an off-by-one
reading or the organizers may have extended by 24 hours. **Treat 2026-07-25 04:00 UTC as the
working target anyway** so a clarification or a mistaken reading cannot cost the entry, and
confirm the date in the competition UI before the final click. A Writeup can be edited and
re-submitted, so submitting early is free insurance and costs nothing but a re-submit.

Other facts from the same API call, useful for planning: `max_team_size: 3`,
`max_daily_submissions: 5`, `reward: 1,500 Usd`, and `team_count: 4` (the field is teams entered,
not final submissions, so read it as "a small field" rather than a guaranteed placing).
Submission = Kaggle **Writeup** (submitted, not draft) + **public code repo** + **demo video ≤ 2 min**.
Competition: https://www.kaggle.com/competitions/humor-genome-nyc - Track = **Humor Understanding**.

## Agent-verified state (2026-07-12)

- [x] All seven kernels **COMPLETE and private** under the account `taylorsamarel`:
      - https://www.kaggle.com/code/taylorsamarel/humorvibes-measuring-jokes-with-gemma (main demo; latest run = CPU-fallback path, completes end-to-end)
      - https://www.kaggle.com/code/taylorsamarel/humorvibes-mesh-zoo-lab (invariance + frame duel + century test)
      - https://www.kaggle.com/code/taylorsamarel/humorvibes-corpus-lab (census + remix + temporal)
      - https://www.kaggle.com/code/taylorsamarel/humorvibes-panel-lab (frame duel; hosted panel keys-gated)
      - https://www.kaggle.com/code/taylorsamarel/humorvibes-validate-ratings (Humicroedit human-grades check)
      - https://www.kaggle.com/code/taylorsamarel/humorvibes-ablation-court (source-pinned v4 S/R/E/B ablation and paired controls)
      - https://www.kaggle.com/code/taylorsamarel/humorvibes-studio-g2 (studio tunnel host)
      Old slugs (humor-genome-measuring-jokes-with-gemma, punchline-mesh-panel-lab,
      punchline-mesh-studio-g2) 404 after the rename; local `kernel-metadata.json` ids were
      updated to the live slugs - future `kaggle kernels push` updates the real kernels.
- [x] Read-only re-audit complete: all six live statuses are COMPLETE/private, normalized
      notebook code/markdown cells exactly match the local builders, and every mirrored
      research output is byte-identical to the latest Kaggle output. Receipt:
      `research_out/kernel_audit_20260712.json`.
- [x] Private `humorvibes-ablation-court` v4 completed on CPU: 200/200 jobs, source cells matched,
      output hashes verified, 100% B/logprob coverage, and no external submission. The fixed
      score was an honest negative result: rho=0.033, 95% CI [-0.126, 0.207]. Receipt/report:
      `research_out/kaggle/humorvibes-ablation-court/`.
- [x] `notebook.ipynb` verified byte-identical to `build_notebook.py` output; self-contained
      (inline demo data, attached Gemma model glob, CUDA-probe → CPU fallback, no internet).
- [x] `WRITEUP.md` re-pinned so every current-run number traces to an artifact in
      `research_out/kaggle/` (outputs of all six research kernels pulled locally); 1,401 words
      (cap 1,500). Historical numbers (v4/v5, zoo v1) are cited only as attributed history.
- [x] `RESULTS.md` reconciliation section added (century test DONE: 3/12 alive; temporal probe =
      honest null; Humicroedit validation recorded: laugh_score ρ=0.115, n=180).
- [x] GitHub mirror https://github.com/Amarel-Taylor-Scott/humorvibes exists, **private**,
      last verified update 2026-07-12 02:15 UTC. The new audit/ablation files are not yet
      claimed as mirrored; refresh and secret-scan after the v4 harvest, before making it public.

## Post-freeze expansion (2026-07-24 night, after the submission state was tagged)

The submission state is frozen at git tag `submission-2026-07-25` on the public repo. Later work
lives on the `expansion` branch so nothing below can move under a judge's feet. What landed after
the freeze, each with a receipt: the predeclared format-boundary follow-up executed and reported
honestly (`jestry_out/format_boundary_experiment.json`), quantization robustness of the certified
instrument (`jestry_out/gemma2_full_nll_quant_check.json`, S=3.19 stable to 0.01 across Q4 and
Q8), a silent-NaN honesty bug found and fixed in the provider, the first accepted outcome from
the compose-residual rung, 640 more French and Italian proverbs plus 40 more labeled frames, the
Humor Vibes Open launch bundle under `competition/launch/`, and
`RESEARCH_NOTE_INSTRUMENT_BOUNDARIES.md` tying the instrument findings together. `WRITEUP.md`,
`RESULTS.md`, and `SUBMISSION_PASTE_PACK.md` already carry these numbers, so pasting the writeup
tonight ships them.

## HUMAN-ONLY punch-list (ordered; target: all done by 2026-07-24 00:00 UTC)

1. **Verify the rubric and reconfirm the deadline in the UI** (5 min)
   Open https://www.kaggle.com/competitions/humor-genome-nyc/overview while logged in.
   The page is JS-rendered - the agent cannot read it. Only "Gemma Integration 30%" is on
   record; confirm the other judged dimensions so the writeup's emphasis can be re-weighted.
   The authenticated API currently reports **2026-07-25 04:00 UTC**.

2. **(Optional) Hosted-panel keys** - only if you want live multi-LLM panel votes in the demo;
   Gemma is the core engine and the panel is explicitly garnish. The 2026-07-03 panel study ran
   dry (all votes None - honestly recorded in `research_out/panel_study_20260703-091646.md`).
   If doing it, do it BEFORE recording the video:
   - Kaggle notebook editor → Add-ons → Secrets: `OLLAMA_API_KEY` from secure local storage,
     optionally `NVIDIA_API_KEY` (build.nvidia.com), `MISTRAL_API_KEY`
     (console.mistral.ai), `GEMINI_API_KEY` (redeem Kaggle's Google AI credits at
     aistudio.google.com).
   - Rerun: `python3 research_panel_study.py` locally (env keys) or re-run humorvibes-panel-lab.

3. **The ≤2-minute demo video is already BUILT** at `demo_assets/humorvibes_submission.mp4`
   (1:55.8, 1280x720 h264+aac, burned captions, soft subs, music bed; built by
   `make_submission_video.py` from the repo's real evidence). Watch it once, then either upload
   it as-is (YouTube unlisted is fine for judging; confirm the rules do not require public) or
   mute it and record your own voice over the visuals, using the `.srt` beside it as a
   teleprompter. The script below is what the narration already says. Keep the URL.

4. **Flip the GitHub repo public** - https://github.com/Amarel-Taylor-Scott/humorvibes/settings
   → General → Danger Zone → "Change repository visibility" → Make public → type
   `Amarel-Taylor-Scott/humorvibes` to confirm. Requires being logged in as the owner
   (Amarel-Taylor-Scott); 30 seconds. Do this no later than just before submitting.

5. **Make the Kaggle notebooks public** (deadline gates visibility - do at submit time):
   each kernel → Share → set Public. Minimum: the main demo notebook; recommended: also
   zoo-lab, corpus-lab, panel-lab, validate-ratings, and ablation-court so every writeup number
   is judge-clickable. Do not cite the private receipt as though judges can access it before this.

6. **Create + submit the Writeup** at https://www.kaggle.com/competitions/humor-genome-nyc
   (Writeups tab → New Writeup):
   - Track: **Humor Understanding**.
   - Paste `WRITEUP.md` body.
   - Attach under project links: the notebook URL(s) above, the GitHub repo URL, the video URL.
   - Press **Submit** (not Save Draft). Re-submit after any later edit - drafts do not count.

7. **Post-submit sanity pass** (2 min): open the writeup logged out (incognito) - confirm the
   repo 200s, the notebooks render with outputs, and the video plays.

## 2-minute video script (evidence first; shot list from verified artifacts)

Prep: open the rendered COMPLETE Gemma notebook, the harvested
`ablation_failure_figure.png`, one readable row from `failure_cases.md`, and the current studio.
Keep `Offline fallback / Seeded offline` visible during the studio shot; it demonstrates the
workflow and is not the Gemma measurement evidence.

- **0:00–0:12 - Hypothesis**
  "A joke is a controlled prediction error with a cheap, audience-permitted repair. HumorVibes
  turns that claim into four falsifiable signals."
- **0:12–0:32 - Exact Gemma evidence** (rendered notebook + model identifier)
  "Pinned Gemma-2-2B supplies true teacher-forced log-probabilities. S is punchline surprisal; R
  is the collapse after a hidden frame; E is R per frame token; B is a separate persona-conditioned
  judgment." On-screen label: `REAL GEMMA LOGITS - VERIFIED RUN`.
- **0:32–0:50 - Controls earned by failure**
  "Our first metric credited nonsense: raw R=2.37. The matched null made it zero, and a later leak
  guard drove all four frame writers to zero on the lexical shortcut."
- **0:50–1:18 - Human ablation court** (harvested four-panel figure)
  "The source-pinned court completed 200 of 200 measurements. Full S/R/E/B reached only rho=0.033,
  95% CI -0.126 to 0.207. E alone was highest at 0.099, also uncertain. Human edits did not beat
  shuffled edits on the full score. B did separate them by 0.100, p=0.00216, but did not predict
  funniness. Safety is a constraint, not the objective."
- **1:18–1:34 - Visible failure** (failure table, not a tiny screenshot)
  "A shuffled headline, 'Macron urges US to puppy isolationism', scored 43.3. The model invented a
  frame and the headline split was wrong. That is why this is a diagnostic instrument, not an
  oracle."
- **1:34–1:49 - Product workflow** (branded offline studio with disclosure visible)
  "The deterministic local UI shows generation, ranking, repair, compilation, and audience
  adaptation. The earlier notebook is the Gemma evidence; this shot is the reproducible workflow."
- **1:49–2:00 - Gate and close**
  "The current compiled example fails lint and remains unvalidated; forced seed-7 replay is only
  a reproducibility proof. HumorVibes measures affordable surprise, and records where it fails."

## Relaunch notes (only if a live studio session is wanted for judging week)

- `kaggle kernels push -p live_studio/` (kernel humorvibes-studio-g2); announce the URL on a fresh
  session-scoped channel that is not committed to the public repo; sessions live ~8h. Never reuse a slug whose push
  died mid-create (orphaned slugs 404 forever).
- Code delivery chain: this folder → Kaggle dataset `taylorsamarel/punchline-mesh-src` → GitHub
  mirror `Amarel-Taylor-Scott/humorvibes`.

## Notes

- Gemma stays the named core engine (recorded judging weight: Gemma Integration 30%); the
  frontier-LLM panel is explicitly a calibration garnish.
- Do NOT re-run the main measurement kernel before the deadline - its latest version is COMPLETE
  and the writeup numbers are pinned to it. A re-run would mint a new latest version with
  different sampled numbers.

# Research foundations: from prediction to a testable humor claim

This document supplies the conceptual starting point that the executable notebook previously
compressed into a few paragraphs. It distinguishes established measurements, broad scientific
frameworks, project hypotheses, and product claims. That distinction is central: an attractive
story about brains is not yet evidence that a joke works for a person or an audience.

![Evidence chain from predictive processing to a bounded product claim](figures/surprise-to-product.svg)

## The starting question

How can a setup make one continuation feel natural, a punchline violate that expectation, and a
listener still reinterpret the line quickly enough for the violation to become play rather than
noise or threat?

Humor Genome Wave 2 explores one answer:

> Some humor may work by creating a controlled prediction error that can be repaired through a
> compact, audience-permitted alternate frame.

The phrase **“the brain is a surprise-reduction engine”** is useful shorthand for the predictive
processing tradition, but it is too strong as a literal conclusion. The project treats it as a
generative research framework, not as settled proof about every brain, every kind of humor, or
every laugh.

## Five quantities that must not be collapsed

| Quantity | Operational meaning | What can measure it | What it is not |
| --- | --- | --- | --- |
| **Token surprisal** | `-log p(token | context)` under one frozen language model | Teacher-forced model probabilities | A person's surprise or funniness |
| **Prediction error** | A mismatch between a system's prediction and input | Depends on the system and level being modeled | Automatically pleasant, meaningful, or comic |
| **Resolution / comprehension** | A listener can recover an alternate interpretation | Human explanation or comprehension tasks; model hints are only proxies | The same as amusement |
| **Amusement / funniness** | A subjective appraisal in a named context | Consented human ratings or choices | The same as audible laughter |
| **Laughter / behavior** | A social and physiological response | Consented observation with context | A humor-specific ground truth signal |

These distinctions explain the project's evidence boundary. Gemma can expose its token
distribution. It cannot expose a listener's internal prediction, prove that a listener found the
repair, or decide that the result was funny.

## The intellectual lineage

### 1. Information theory and language surprisal

For an event `x` in context `c`, information-theoretic surprisal is:

```text
I(x | c) = -log p(x | c)
```

Low-probability events carry more surprisal. In psycholinguistics, Hale used probabilistic parsing
to connect incremental linguistic expectations with processing difficulty, while Smith and Levy
found a roughly logarithmic relationship between word probability and reading time. A later,
large-scale analysis by Shain and colleagues reported broad support for this logarithmic
predictability effect across languages and modalities.

**Project use:** teacher-forced negative log-probability is a reproducible measure of what one
frozen Gemma checkpoint expected next.

**Limit:** a language model's distribution is not a direct recording of a person's expectation,
and processing difficulty is not funniness.

### 2. Predictive coding and predictive processing

Rao and Ballard presented a hierarchical predictive-coding model in which higher levels predict
lower-level visual activity and residual errors propagate upward. Predictive processing has since
become a broad family of accounts rather than one settled mechanism.

**Project use:** a setup can be modeled as establishing an expectation distribution and a
punchline as changing the evidence available to the predictive system.

**Limit:** success in a language-model calculation does not establish a neural implementation,
and the project does not measure neural prediction errors.

### 3. The free-energy principle

Friston's free-energy principle proposes that adaptive agents minimize variational free energy, a
tractable bound related to surprise, through perception and action. Variational free energy,
Shannon surprisal, token negative log-likelihood, and an everyday feeling of surprise are related
ideas at different levels—not interchangeable numbers. The principle is influential and broad;
its explanatory reach and falsifiability are also actively debated.

**Project use:** it motivates asking how expectations, error, repair cost, and context might fit
into one falsifiable model.

**Limit:** the principle neither proves the HumorVibes equation nor predicts that laughter must
follow a token-probability spike.

### 4. Incongruity, resolution, and benign violation

Incongruity-resolution accounts distinguish an unexpected element from the work required to make
it coherent. Shultz experimentally manipulated incongruity and resolution in children's cartoon
humor. Later behavioral and electrophysiological work separated surprise, comprehension, and
amusement in joke processing. McGraw and Warren's benign-violation account adds another constraint:
a violation can be amusing when it is also appraised as benign.

**Project use:** these traditions motivate separate hypotheses for surprise (`S`), resolution
(`R`), repair efficiency (`E`), and audience-relative “bad surprise” (`B`).

**Limit:** `B` is a project construct, not a validated implementation of benign-violation theory;
model persona prompts do not measure a person's moral or emotional appraisal.

### 5. Social laughter, audience, and culture

Laughter has affiliative and communicative functions and occurs outside humor. What works depends
on speaker, relationship, delivery, prior turns, culture, venue, and group dynamics. Text-only
analysis therefore omits mechanisms that often dominate real performance.

**Project use:** audience response is the claim gate, and real studies must preserve writer,
material, audience, venue, language, and context as separate grouping variables.

**Limit:** neither corpus votes nor an LLM panel can substitute for a prospective, consented study
of the population and use case named in a product claim.

## The project model

For setup `C`, punchline `P`, and a candidate alternate-frame hint `F`, the project proposes:

- `S = NLL(P | C)`: punchline surprisal under a frozen model;
- `R = NLL(P | C) - NLL(P | C + F)`: model surprisal reduction after adding a frame hint;
- `E = R / tokens(F)`: model resolution per hint token;
- `B`: an audience-relative hypothesis about a repair colliding with strongly held interpretive
  commitments.

Only `S` has a completed, pinned public Gemma measurement in the canonical notebook. The current
form experiment finds **0 of 10** joke-form confidence intervals strictly above the proverb
control's interval and all ten intervals overlap it. Separation is not established. `R`, `E`, and
`B` remain proposed constructs requiring construct validation, ablations, and human outcomes.

The project hypothesis can be written compactly as:

```text
setup creates expectation
        ↓
punchline creates controlled error (S)
        ↓
alternate frame makes it coherent (R)
        ↓
repair is compact enough (E)
        ↓
repair is permitted in this audience and context (low B)
        ↓
possible amusement — to be measured with people
```

The final arrow is deliberately conditional. Surprise is compatible with comedy, confusion,
horror, offense, boredom, and simple novelty. A useful theory must distinguish those outcomes.

## Evidence map

| Link in the chain | Prior evidence | Current project evidence | Status |
| --- | --- | --- | --- |
| Language users form graded expectations | Psycholinguistic surprisal and reading-time studies | Frozen Gemma exposes token probabilities | Grounded, but model-to-human transfer is unvalidated here |
| Setups can create an expectation that punchlines violate | Incongruity research | Annotated expectation/violation frames; form taxonomy | Plausible representation, not a causal result |
| A compact alternate frame can resolve the violation | Incongruity-resolution literature | Frame hints and proposed `R/E` instruments | Proposed; construct validation needed |
| A resolved violation becomes benign/permitted | Benign-violation and appraisal accounts | Canonical `B` definition and persona-conditioned design | Proposed; prompts are not human measurement |
| These mechanisms improve amusement | Human humor research | No preregistered project human mechanism study yet | Not established |
| Tool assistance improves a writer or audience outcome | Human-computer interaction question | SDK/API and study protocol now runnable | Capability exists; advantage not established |

## Falsifiable tests that would move the theory forward

1. **Within-item surprise edit.** Change only the predictability of a punchline while holding its
   alternate interpretation constant. Test an inverted-U rather than assuming “more is better.”
2. **Resolution ablation.** Compare the original punchline with a high-surprise non sequitur and a
   low-surprise literal completion. Ask people to report comprehension and amusement separately.
3. **Hint-dose curve.** Reveal increasingly explicit frame hints. A compact-repair hypothesis
   predicts early comprehension gains; it does not require amusement to rise with explanation.
4. **Delivery factorial.** Cross the same text with timing, emphasis, and performer. This estimates
   how much text-only instruments miss.
5. **Audience/context holdout.** Freeze material and predictions, then test new opt-in audiences,
   venues, languages, and dates. Report heterogeneity, not only an average.
6. **Model robustness.** Repeat frozen token-level analyses across model families and tokenizers.
   Agreement is instrument robustness, not human validation.
7. **Writer-assistance crossover.** Compare assisted and unassisted work within writer and premise,
   then evaluate final material with blinded, held-out audiences. Treat writers and material—not
   individual ratings—as the independent units.

The executable study protocol and analyzer are documented in
[`REAL_WORLD_STUDY_WORKBENCH.md`](REAL_WORLD_STUDY_WORKBENCH.md). The analyzer refuses to turn its
synthetic contract fixture into a product claim.

## What a useful conclusion looks like

Good conclusions name the instrument, population, context, comparison, effect, and uncertainty:

> In a preregistered crossover with the named writers and held-out audience, assisted drafts
> reduced median drafting time by X minutes and changed mean material-level audience rating by Y
> points (writer-clustered 95% interval L to U).

Bad conclusions erase the evidence boundary:

> The AI understands humor. This score predicts what people find funny.

The evidence ladder below is enforced in the study analyzer and should also govern product copy.

![Evidence ladder and allowed claims](figures/evidence-ladder.svg)

## Primary references

1. Friston, K. (2010). “The free-energy principle: a unified brain theory?” *Nature Reviews
   Neuroscience*, 11, 127–138. <https://doi.org/10.1038/nrn2787>
2. Rao, R. P. N., & Ballard, D. H. (1999). “Predictive coding in the visual cortex.” *Nature
   Neuroscience*, 2, 79–87. <https://doi.org/10.1038/4580>
3. Hale, J. (2001). “A Probabilistic Earley Parser as a Psycholinguistic Model.” *NAACL*.
   <https://aclanthology.org/N01-1021/>
4. Smith, N. J., & Levy, R. (2013). “The effect of word predictability on reading time is
   logarithmic.” *Cognition*, 128, 302–319. <https://doi.org/10.1016/j.cognition.2013.02.013>
5. Shain, C., Meister, C., Pimentel, T., Cotterell, R., & Levy, R. (2024). “Large-scale evidence
   for logarithmic effects of word predictability on reading time.” *PNAS*, 121.
   <https://doi.org/10.1073/pnas.2307876121>
6. Shultz, T. R. (1972). “The role of incongruity and resolution in children's appreciation of
   cartoon humor.” *Journal of Experimental Child Psychology*, 13, 456–477.
   <https://doi.org/10.1016/0022-0965(72)90074-4>
7. McGraw, A. P., & Warren, C. (2010). “Benign violations: Making immoral behavior funny.”
   *Psychological Science*, 21, 1141–1149. <https://doi.org/10.1177/0956797610376073>
8. Ku, L.-C., Feng, Y.-T., Chan, Y.-C., Wu, C.-L., & Chen, H.-C. (2017). “A re-investigation of
   the neural substrates of joke comprehension and humor appreciation.” *Journal of
   Neurolinguistics*, 42, 1–12. <https://doi.org/10.1016/j.jneuroling.2016.11.008>
9. Manninen, S., et al. (2017). “Social laughter triggers endogenous opioid release in humans.”
   *The Journal of Neuroscience*, 37, 6125–6131. <https://doi.org/10.1523/JNEUROSCI.0688-16.2017>
10. Colombo, M., Wright, C., & Piccinini, G. (2021). “Predictive processing: a circuit approach.”
    <https://arxiv.org/abs/2107.12979>
11. Biehl, M., Pollock, F. A., & Kanai, R. (2021). “A technical critique of some parts of the
    free energy principle.” <https://arxiv.org/abs/2001.06408>

The references ground adjacent mechanisms. None is presented as a citation for results that this
project has not measured.

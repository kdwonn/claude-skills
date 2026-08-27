# Worked examples

Three full passages, before and after. Read the one that matches what you are about to write. A transformed passage teaches the register better than the atomic rules do, because most of the work is in choosing where to split sentences and how to recover the actor — neither of which a rule list shows well.

**Contents:** [Note](#1-note) · [Experiment report](#2-experiment-report-section) · [README](#3-readme)

---

## 1. Note

Notes fail by compression. The writer drops articles, verbs, and subjects, because at the time of writing the context is obvious. Six months later it is not.

### Before

```markdown
## sigreg sweep thoughts

Ran sweep overnight — 4 weights x 3 seeds. Higher weights seem to be causing
collapse, rank dropping hard past 0.05, though it's not totally clear if this
is the weight itself or an interaction with the schedule change that was made
last week which also went in around the same time.

0.09 worst. embedding rank 31 vs 512 baseline. loss looks fine which is
suspicious.

Next: probably rerun with old schedule to disambiguate, also should check if
collapse metric is even right.
```

### After

```markdown
## sigreg sweep thoughts

We ran a sweep overnight across four SIGReg weights and three seeds. The higher
weights caused representation collapse. The embedding rank fell sharply above
sigreg=0.05.

The cause is ambiguous. We changed the schedule last week, at about the same
time, so the collapse may come from the weight, from the schedule, or from an
interaction of the two.

The worst point was sigreg=0.09. Its embedding rank was 31, against a baseline
of 512. The training loss stayed normal, which is suspicious: a collapsed
representation usually shows up in the loss.

Next:
- Rerun the sweep with the old schedule, to separate the two changes.
- Verify that the collapse metric measures what we think it measures.
```

### What changed and why

- **Recovered the actor.** "Ran sweep" → "We ran a sweep". The reader no longer has to work out who acted.
- **Killed the progressive and the gerund.** "seem to be causing" → "caused"; "rank dropping hard" → "the embedding rank fell sharply".
- **Split the 46-word sentence.** The original packed the finding *and* the confound into one sentence. They are two claims, so they are now two paragraphs — and the confound got the explicit three-way statement it deserved.
- **Restored articles and verbs.** "0.09 worst. embedding rank 31 vs 512 baseline." → full sentences. This is the single biggest readability gain in a note.
- **Made the suspicion explicit.** "loss looks fine which is suspicious" assumed the reader remembers why. The rewrite says why.
- **Turned "Next" into a list of imperatives.** Procedural register, one instruction per item.

Note what did *not* change: `sigreg`, `embedding rank`, and the numbers are untouched. Never simplify a domain term or round a number.

---

## 2. Experiment report section

Reports fail by hedging and by passive voice. Both hide who did what, and both make a null result read as a failure to write clearly.

### Before

```markdown
## Results

It was observed that the model which was trained with the higher SIGReg weight
had been exhibiting signs of representation collapse, with the effective rank
of the embedding having dropped to 31 from the baseline value of 512, although
the training loss curve was not showing any particularly anomalous behaviour
during this period, which was somewhat unexpected given prior runs.

Performance on the downstream action loss ablation sweep evaluation benchmark
was degraded relative to baseline.
```

### After

```markdown
## Results

The model trained at sigreg=0.09 collapsed. The effective rank of the embedding
fell to 31, from a baseline of 512.

The training loss showed no anomaly over the same period. This surprised us:
in earlier runs, collapse was visible in the loss.

Downstream performance also degraded. On the action-loss ablation benchmark,
`val/action_loss` rose from 0.29 to 0.41.
```

### What changed and why

- **"It was observed that" is deletable.** The report is the observation. Six words gone before the sentence starts.
- **Passive → active.** "was trained with" → "trained at"; "was degraded" → "degraded". The second is an intransitive rewrite, which is often the cleanest escape from a passive whose actor is genuinely uninteresting.
- **Auxiliary chains collapsed.** "had been exhibiting signs of" → "collapsed". "having dropped" → "fell".
- **Broke the six-word noun cluster.** "downstream action loss ablation sweep evaluation benchmark" → "the action-loss ablation benchmark". Note that one noun was simply dropped: "sweep evaluation benchmark" named the same object three times.
- **"was somewhat unexpected" → "This surprised us", plus the reason.** The hedge was hiding a real, useful observation.
- **Added the actual numbers.** "was degraded relative to baseline" is unfalsifiable. The rewrite commits to 0.29 → 0.41. If you do not have the number, say you do not have it.

The 62-word opening sentence became five sentences, none over 16 words, with nothing removed except padding.

---

## 3. README

READMEs fail by mixing registers. The overview drifts into instructions, and the instructions drift into description. Classify each section first.

### Before

```markdown
## Getting Started

In order to be able to get started with using this library, you will first
want to make sure that you have cloned the repository and that you have also
installed all of the required dependencies, after which you should be setting
your API key environment variable and then the test suite can be run in order
to verify that everything has been installed correctly. Note that running the
full test suite requires a GPU and will consume roughly 40 GPU-minutes.
```

### After

```markdown
## Getting started

> **Warning:** the full test suite needs a GPU and uses about 40 GPU-minutes.
> Run `pytest -m "not slow"` instead if you do not want that cost.

1. Clone the repository.
2. Install the dependencies with `pip install -e .`.
3. Set the `WANDB_API_KEY` environment variable.
4. Run `pytest` to verify the installation.
```

### What changed and why

- **Register fixed.** This is a procedural section, so it takes the imperative and the 20-word limit. The original wrote instructions as description ("you will first want to make sure that you have cloned").
- **One instruction per sentence, as a numbered list.** The original was one 58-word sentence carrying four actions. A reader following it would lose their place; a reader skimming it would miss step 3 entirely.
- **The warning moved to the front.** In the original, the GPU cost appeared *after* the instruction to run the tests — which is exactly too late. It now leads, starts with a command, and offers the cheap alternative.
- **Deleted the throat-clearing.** "In order to be able to get started with using this library, you will first want to make sure that" carries no information. The heading already said it.
- **Made the commands copyable.** The original described the actions; the rewrite gives the exact commands in code spans, which is what a reader actually needs from a README.

### The descriptive half of a README

The overview follows the other register. Apply the 25-word limit, the simple present, and the conclusion-first rule:

```markdown
## What this is

`jeda` trains joint embedding models on robot action data. It gives you a
single-command sweep runner, checkpoint resumption, and wandb logging.

It is not a general-purpose training framework. If you need multi-node
training or a model zoo, use `torchtitan` instead.
```

Two things earn their place here: the second paragraph says plainly what the library does *not* do, and both paragraphs use the simple present, which is the correct tense for describing what a thing is.

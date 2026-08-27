---
name: experiment-report
description: Write a structured post-hoc report on one machine learning experiment, or on a *sweep* of experiments that vary one or two hyperparameters to test a hypothesis. Use this whenever the user asks to "write a report", "summarize", "document", "analyze", or "recap" a training run, ablation, checkpoint, or sweep — whether it's logged to wandb, tensorboard, or only as local files. Reports on sweeps are a first-class mode: when the user names multiple runs, a pattern, or a descriptive handle that resolves to >1 run, organize the report around the sweep axis rather than writing run-by-run. The skill resolves runs from wandb ids/URLs, Hydra output directories, checkpoint/log directory names, patterns like "sigreg-* from April 14", or descriptive handles. It reconstructs intent from git commits, recent Claude conversations, and the user's Obsidian vault, **confirms that intent with the user before writing unless it's verbatim in a commit message or vault note from the run window**, gathers metrics and config diffs, and writes the report as an Obsidian note. Trigger this skill even when the user only says "what was run X about?" or "document what we just finished" — the goal is always a persistent, linkable note rather than an inline answer.
---

# Experiment report

This skill writes a report on an ML experiment — either a single run or a sweep — and saves it as a note in the user's Obsidian vault. The goal is a short, honest, linkable artifact the user can return to months later and still understand.

A good report answers three questions: **what hypothesis were we testing, what actually happened across the runs, and how does that compare to what we already believed**. Everything else is supporting evidence.

## When you are triggered

The user gives you one of:

- **A single run**: a wandb id, Hydra output dir, log dir name, or descriptive handle
- **A sweep**: several of the above, or a pattern ("all the sigreg-* runs from April 14", "the ogb cube eval sweep"), or a descriptive handle that resolves to >1 run ("the action-loss sweep", "yesterday's sigreg runs")
- Sometimes just "write a report on what we just finished" — which may be one run or a batch

**If the resolution produces >1 run that share a consistent timestamp window and obvious shared config, treat it as a sweep.** Sweeps are the common case; don't assume a single run unless only one came back.

## Workflow

1. **Resolve the run(s)** — map the reference to wandb runs, local files (config, checkpoints, logs), and the git commits they were trained at. For sweeps, collect all matches. See [Resolving runs](#resolving-runs).
2. **Reconstruct intent** — why was this run/sweep started? Inspect git commits, recent Claude sessions, and the Obsidian vault. See [Reconstructing intent](#reconstructing-intent).
3. **Confirm intent with the user** — unless intent is already stated verbatim in a commit or vault note, ask the user to confirm your reconstruction. See [Confirming intent](#confirming-intent).
4. **Gather results** — metrics, config diff across runs (for sweeps, this is the axis of variation).
5. **Write the note** — in the user's Obsidian vault, under `0.Inbox/`, following the vault's own conventions.

Do the homework first (steps 1–2); the user shouldn't have to tell you things the filesystem already knows. But *always* check in on intent (step 3) unless it's unambiguous, since intent is the single most valuable thing in the report and the one thing you can't reliably infer from artifacts.

## Resolving runs

Work from whatever the user gave you:

**wandb run id / URL.** Look under `{cwd}/wandb/run-*-{id}/` for `files/wandb-metadata.json` (git commit, args, start time), `files/config.yaml`, `files/wandb-summary.json`, `files/output.log`. If not local, use the wandb API — see [references/wandb.md](references/wandb.md).

**Hydra output dir.** Read `.hydra/config.yaml` and `.hydra/overrides.yaml`. Match by timestamp: wandb dir encodes start time as `run-YYYYMMDD_HHMMSS-<id>`, Hydra dir as `outputs/YYYY-MM-DD/HH-MM-SS/`. If the Hydra run name (often `{model}_{YYYY-MM-DD_HH-MM-SS}_{suffix}`) appears in a wandb run-dir name, that's the match. **Also note whether this is a training or eval Hydra output** — in some projects `outputs/` holds eval runs while training artifacts live in `logs/`. A Hydra dir containing only `eval.log` / `check_collapse.log` is an eval run; report on it as such, and trace the `policy=...` override to the training run being evaluated.

**Checkpoint / log dir.** Logs often mirror Hydra naming (`logs/{model}/{YYYY-MM-DD_HH-MM-SS}_{name}`). Same timestamp matching.

**Descriptive handle or pattern.** List recent wandb runs (local dirs by mtime, or `wandb.Api().runs(...)`), filter by keyword/date. For patterns like "sigreg-* from April 14":

```bash
ls logs/*/ | grep -E "2026-04-14.*sigreg"
```

Confirm with the user if the resolution is ambiguous (e.g., "I found 6 runs matching; do you want all of them, or just the 4 with both hparams varied?"). Don't guess silently.

**Output of this step:**

For each run, capture: **run id**, **run name**, **start time**, **git commit**, **launch args** (`wandb-metadata.json → args`), **Hydra dir**, **config**, **summary metrics**.

For a sweep, also capture: **the axis (or axes) of variation** — the config keys that differ across runs — and the **shared config** (what's held constant).

## Reconstructing intent

Intent lives in git messages, conversations, and notes — not configs.

Check these in parallel (they're independent):

**Git.** `git log --all --since="<run_start - 7d>" --until="<run_start + 1d>" --pretty=format:"%h %ai %s"`. Read the commit message for the exact commit with `git show --stat <commit>`. For a sweep, also check whether the runs share a single commit — if so, that commit's message often *is* the hypothesis. If the sweep spans multiple commits, look for a branch or series of commits with a consistent theme.

**Claude sessions.** `~/.claude/projects/<slug>/*.jsonl` where `<slug>` is cwd with `/` replaced by `-`. Look at sessions with mtime within a few days of the runs; grep for the run ids, run names, or key overrides. Pull the **user's** messages — that's where motivation lives. For sweeps, look for the session where the user says "let's sweep X over {...}" or similar.

**Obsidian vault.** Auto-discover: `find ~ -maxdepth 4 -type d -name .obsidian`. Search `0.Inbox/`, `1.Projects/`, and `2.Cards/` for notes whose filename timestamp or `created:` frontmatter is within a week of the run(s), or whose body mentions the experiment name / key hparams. Read the vault's `CLAUDE.md` first — it describes the vault layout and any `obsidian` CLI. Prefer `obsidian search query="<term>"` when available.

**Classifying intent as "explicit" vs "inferred":**

- **Explicit** (skip confirmation): the run's commit message literally states the question ("try sigreg=0.09 to see if collapse recovers"), OR a vault note from the run window explicitly frames the experiment ("we're running this sweep to test whether the IDM objective substitutes for SIGReg").
- **Inferred** (must confirm): you triangulated intent from several weak signals, filled in plausible motivations from context, or the user's own stated intent is more than a week older than the run.

Err toward "inferred" — if in doubt, confirm. Confirmation is cheap; a wrong report is expensive.

## Confirming intent

When intent is inferred rather than explicit, use `AskUserQuestion` with a single question that presents your best reconstruction and two alternatives:

```
Question: "Does this capture what this <run/sweep> was testing?"
Options:
  A. [Your one-sentence reconstruction, as specific as you can make it]
  B. Close, but I'd phrase it differently — (user types correction)
  C. Not quite — actually I was testing: (user types)
```

Keep it to one question unless you genuinely can't narrow down to a top hypothesis. If you do ask a second question, it's about scoping, not intent: "Which runs should be in scope?" (for sweeps) or "Is there a reference baseline to compare against?"

**When you can skip confirmation:**

- You found an explicit statement (as defined above) and are quoting it. Say so in the report: *"Intent (from commit `abc1234` dated 2026-04-14):* X."*
- The user's prompt already spelled out the intent. E.g. "report on the sigreg sweep I ran to test whether higher weights kill collapse" — intent is in the prompt.
- The user explicitly said "just write it, don't ask" or equivalent.

**Do not replace this with "let me first explain what I'm about to do"** — that's narration, not confirmation. The point is to get the user's own words or explicit approval.

## Gathering results

Two rules:

1. **Never dump raw history into context.** Load metrics via numpy/pandas, compute statistics (final value, min, last 10% mean, monotonicity), report summaries. See [references/wandb.md](references/wandb.md) and [references/tensorboard.md](references/tensorboard.md).
2. **For single runs, always identify a baseline**; for sweeps, **the axis of variation IS the comparison** — you don't need an external baseline if the sweep is self-comparing. Include one external baseline only if it adds signal (e.g., "how does the best sweep point compare to the pre-sweep state of the art?").

**Config diff across a sweep.** Flatten each run's config to dotted keys, then identify keys that take more than one value across the set:

```python
# conceptually:
axes = {k for k in all_keys if len({run.config[k] for run in runs}) > 1}
shared = {k: v for k, v in runs[0].config.items() if k not in axes}
```

Typically a sweep has 1–2 axes. Name them in the TL;DR and the Setup section. If >3 keys differ, check with the user — that's usually not a coherent sweep but a mix of independently launched runs.

**Capture plots or media** the user logged (usually `wandb/run-*/files/media/`). For sweeps, prefer producing an overlay / comparison plot rather than referencing N per-run plots.

## Writing the note

The note goes into the user's Obsidian vault in `0.Inbox/`. **Before writing, read the vault's `CLAUDE.md` if it exists** — it encodes vault-specific rules (frontmatter schema, tag conventions, naming, template). Obey those rules exactly; they take precedence over the defaults below.

Default conventions (use when the vault's CLAUDE.md is silent):

- Filename: `YYMMDDHH <descriptive title>.md`, where the timestamp is the report-creation time.
- Frontmatter: `created`, `tags` including `#claude` + `experiment`, `prev_context:` listing any related notes you found during intent reconstruction.
- No H1 duplicating the filename.
- No blank lines inside bullet lists.

### Report structure — single run

```markdown
## TL;DR
One or two sentences: the question, the outcome, what we learned.

## Intent
The question this run was meant to answer. Quote the source if explicit
(commit message, vault note). Link vault notes via [[wikilinks]].

## Setup
- **Run**: [wandb link/id] · commit `abc1234` · started YYYY-MM-DD HH:MM
- **Config deltas vs baseline `<baseline-id>`**: only the keys that differ.
- **Data**: dataset, split, any non-default preprocessing.

## Results
Key metrics with final values and brief commentary. Embed plots by reference.
If the run diverged, crashed, or stopped early, say so — don't bury it.

## Comparison to baseline
Numeric delta. One or two sentences on whether it moved the needle given
noise.

## Interpretation
What the results mean in light of the intent. Be honest about what's
ambiguous. If the result contradicts the hypothesis, say so plainly.

## Open questions / next
2–4 bullets. Things the result didn't settle, follow-ups worth trying.
Skip if genuinely empty — don't pad.
```

### Report structure — sweep

Model after the vault's existing sweep notes when possible — find one and match its shape.

```markdown
## TL;DR
One or two sentences: the sweep axis, the winning point, the top-line finding.

## Hypothesis
The question the sweep tests. Quote the source if explicit.

## Setup
- **Sweep**: `<axis_1>` ∈ {v1, v2, ...} × `<axis_2>` ∈ {...}  (= N runs)
- **Shared config**: embed_dim, epochs, data, optimizer — only the stuff that
  matters; don't dump the whole config.
- **Run dirs** (bullet list with wandb links/ids)
- **Git commit(s)**: usually one; if more than one, note the split.

## Results
One comparison table per metric family; rows are sweep points, columns
are metric sub-types. Bold the winning row per table.

## Observations
3–5 bullets. Focus on patterns across the sweep axis:
- What monotonic trends are there?
- Which combinations break the pattern?
- Does the "axis effect" interact with other runs/vault notes?
Tie back to the hypothesis in the Intent section.

## Takeaways for next experiments
Actionable follow-ups. What to try next, what to stop pursuing, which
single-run follow-up would resolve the biggest remaining ambiguity.

## Artifact locations
Per-run artifact paths (collapse metrics, embeddings, plots, eval results).
```

For both shapes: prefer wikilinks to any vault notes you touched during intent reconstruction. Do not fabricate wikilinks to notes you didn't actually read.

**After writing**, if the vault's CLAUDE.md requires a daily-note activity log, append one line to `4.Timestamps/YYYY-MM/YYYY-MM-DD ddd.md` under `## Sessions`.

## Tone

The report is for the user's future self. They already know the high-level project. Don't restate the obvious, don't hype results, don't hide disappointments. If a run "didn't work," the report should still be useful — often the most valuable reports are the ones that kill a hypothesis cleanly.

Bullet-heavy, terse, no marketing voice. Numbers get units. Metric names match what's in the logging code, not rewordings of them.

**Use the `asd-ste100` skill for the prose itself.** This skill owns the report's structure — which sections exist, the frontmatter, the vault conventions. That skill owns the sentences inside them: simple tenses, active voice, ≤25 words per descriptive sentence, no noun cluster over three words. The two agree, since terse prose is what those rules produce. Where terseness tempts you to drop an article or a relative pronoun, keep the word — the report is for a reader who has lost the context, and those words are what let them recover it.

## Reference files

- [references/wandb.md](references/wandb.md) — wandb API patterns: listing, filtering, history sampling, config diff.
- [references/tensorboard.md](references/tensorboard.md) — reading tfevents without pulling the whole thing into context.
- [references/intent_sources.md](references/intent_sources.md) — concrete commands for mining git / Claude sessions / Obsidian.
- [references/sweeps.md](references/sweeps.md) — sweep-specific patterns: axis detection, shared-config extraction, comparison tables.

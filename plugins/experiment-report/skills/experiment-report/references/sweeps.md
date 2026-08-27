# Sweep handling

A sweep is a set of runs that share intent and differ on 1–2 config keys (the *axis*). The report organizes around the axis, not per-run.

## Resolving a set

Given a user reference (pattern, handle, or explicit list), produce a concrete set of run directories.

**Explicit list:** `report on runs A, B, C, D` → resolve each individually with the patterns from SKILL.md's [Resolving runs](../SKILL.md#resolving-runs).

**Pattern:** `sigreg-* from April 14` →

```bash
ls -d logs/*/2026-04-14*sigreg* 2>/dev/null
ls -d wandb/run-20260414_*sigreg* 2>/dev/null
```

**Descriptive handle:** `the action-loss sweep`, `yesterday's sigreg runs` → search the recent wandb runs (local dirs by mtime, last ~7 days) whose names contain the keyword, then:

- If ≤1 result: clarify with the user — handle was too vague.
- If 2–8 results: present them to the user for confirmation as a single `AskUserQuestion`.
- If >8 results: ask the user to narrow (by date range, by hparam, etc.).

**Confirming the set before writing.** If the set was resolved from a descriptive handle, show the user the resolved list in the intent-confirmation question so they can confirm scope and intent in one round trip:

```
Question: "I found these runs for the sweep; does this match what you want
reported on, and was the goal to test <your inferred hypothesis>?"
Options:
  A. Yes, all of these, hypothesis is as stated.
  B. Same runs, different hypothesis: (user corrects)
  C. Wrong runs: (user corrects)
```

## Axis detection

Flatten each run's config to dotted keys. The axis is the set of keys whose values vary across runs:

```python
def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(flatten(v, key))
        else:
            out[key] = v
    return out

configs = [flatten(run.config) for run in runs]
all_keys = set().union(*(c.keys() for c in configs))
axes = {k for k in all_keys if len({c.get(k) for c in configs}) > 1}
shared = {k: configs[0][k] for k in all_keys - axes if k in configs[0]}
```

**Keys to ignore when detecting axes:**

- Auto-generated fields: `run_name`, `subdir`, `wandb.name`, `wandb.id`, timestamps, seeds (unless the sweep explicitly varies seed).
- Hydra-internal keys: anything under `_wandb` in wandb configs, `hydra.*` keys.
- Absolute paths that encode only the run directory.

A clean sweep has 1–2 axes. If you find 5+ keys varying, the user probably gave you a mix of unrelated runs — ask them to narrow.

## Shared config — what to report

Don't dump every constant key. Highlight the ones a future reader needs to interpret the results:

- Data: dataset name, split, preprocessing.
- Model size: parameter count or key dims (`embed_dim`, `depth`).
- Optimizer: type, lr, weight_decay.
- Training budget: epochs, batch size.
- Anything non-default that affects the result (e.g., `detach_target: true`).

Omit defaults that aren't relevant to the finding.

## Comparison tables

One table per metric family. Rows are sweep points (indexed by axis values). Columns are metric sub-types (e.g., `eff. rank`, `top1 SV`, `top10 SV`). Bold the winning value per column.

When there are two axes (e.g. sigreg × act_weight), use a 2D layout:

```
| sigreg | act | metric_1 | metric_2 |
|--:|--:|--:|--:|
| 0.01 | 0.5 | 60% | 0.18 |
| 0.01 | 1.0 | 70% | 0.46 |
| 0.09 | 0.5 | **80%** | 0.12 |
| 0.09 | 1.0 | 76% | 0.32 |
```

When there's a conditioning variable (e.g. baseline vs +context_noise), add it as extra columns rather than a separate table — the point is to make the axis effect visible at a glance.

## Observations: focus on axis patterns

Bullets in this section should talk about the *axis*, not individual runs:

- Good: *"Higher sigreg → 1.8× higher effective rank across both action-weight settings. The gain is monotonic in this sweep range."*
- Less good: *"sigreg=0.09 has eff. rank 154. sigreg=0.01 has eff. rank 87."*

Call out:
- **Monotonic trends** — the axis moves the metric consistently.
- **Interactions** — one axis's effect depends on another's value.
- **Breakpoints** — where adding more of X stops helping or starts hurting.
- **Null results** — axes that *don't* affect a metric. Often more informative than positive results.

## Single-run fallback

If the "sweep" resolves to one run, fall back to the single-run template. Don't force a comparison table of size 1. You can still flag the run as part of a larger intended sweep if only one has finished so far, and name the remaining runs under "Open questions / next".

# wandb access patterns

Use these patterns from inside the project's Python environment (wandb is already a dependency if the project logs to it). The `wandb.Api()` object reads from `~/.netrc` and environment — no extra auth needed if the user can run `wandb` locally.

## Listing runs

Never call `list(api.runs(...))` — run collections can be huge. Always slice.

```python
import wandb
api = wandb.Api()

# Path is "<entity>/<project>". If unknown, read from the local run directory:
#   wandb/latest-run/files/wandb-metadata.json → "entity" and "project"
runs = api.runs("entity/project",
                filters={"state": "finished"},
                order="-created_at")
for r in runs[:50]:
    print(r.id, r.name, r.summary.get("loss/val"))
```

Common filter keys:

- `{"state": "finished"}` — exclude crashed/running
- `{"config.data.name": "pusht"}` — filter by a config field (dotted)
- `{"createdAt": {"$gte": "2026-04-01"}}` — date-bounded
- `{"tags": {"$in": ["baseline"]}}` — by tag

## Fetching one run

If you already know the id:

```python
run = api.run("entity/project/<id>")
print(run.config)         # dict
print(run.summary._json_dict)  # final metrics
print(run.metadata)       # args, git, host, start time
```

## Metric history

**For specific metrics at specific steps** (fastest, least memory):

```python
for row in run.scan_history(keys=["loss/train", "loss/val"]):
    ...  # dicts, one per logged step
```

**For plotting curves** (sampled):

```python
import pandas as pd
df = run.history(samples=500, keys=["loss/train", "loss/val"], pandas=True)
# Now compute stats — do NOT print df raw into context
summary = {
    "final_val": df["loss/val"].dropna().iloc[-1],
    "min_val":   df["loss/val"].min(),
    "last_10pct_mean": df["loss/val"].dropna().tail(max(1, len(df)//10)).mean(),
}
```

## Config diff

```python
def config_diff(run_a, run_b):
    a, b = run_a.config, run_b.config
    keys = set(a) | set(b)
    diff = {}
    for k in sorted(keys):
        if a.get(k) != b.get(k):
            diff[k] = (a.get(k), b.get(k))
    return diff
```

Only report keys that actually differ. For nested configs (common with Hydra), flatten first:

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
```

## Local-only mode

If the user has local `wandb/run-*` directories but no network / isn't logged in:

- `files/wandb-metadata.json` → git commit, args, host, start time, python version
- `files/config.yaml` → full config (top-level `_wandb` key can be ignored)
- `files/wandb-summary.json` → final summary metrics
- `files/output.log` → stdout (grep here for final losses, early stops)
- `files/media/` → logged images / plots

These are enough for a report in most cases. Fall back to the HTTP API only when you need full history, compare against a run you don't have locally, or follow a wandb URL the user pasted.

## Finding the right project

If you don't know the entity/project:

1. `cat <cwd>/wandb/latest-run/files/wandb-metadata.json` — has `entity` and `project` inline in the run settings, or check `config.yaml` → `_wandb` section.
2. Or check the project's training config (Hydra configs often have `wandb.entity` / `wandb.project`).

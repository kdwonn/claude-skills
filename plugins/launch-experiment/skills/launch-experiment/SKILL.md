---
name: launch-experiment
description: Draft and launch a new training experiment for a Hydra + accelerate training repo that launches through `scripts/train.sh`. Use when asked to "launch an experiment", "start a new run", "create an experiment script", "set up a training run", "draft an experiment", or "kick off a sweep". Creates a dated folder under experiment/MMDD/, drafts a runnable bash launcher that calls scripts/train.sh with Hydra overrides, prepends a purpose comment, pre-flight-validates the config with `--cfg job` before any GPU is touched, and launches the run inside a dedicated detached tmux session named `exp-<name>` so it survives SSH disconnects and is reattachable.
---

# launch-experiment

Scaffolds a **dated experiment launcher**. An experiment is a
bash script at `experiment/MMDD/<name>.sh` that calls `scripts/train.sh` with
Hydra overrides — see any existing script under `experiment/` for the house
style.

The driver `new_experiment.sh` does the mechanical part: makes the dated
folder, writes a runnable script with the right boilerplate, and prepends a
header comment describing what the experiment is for. You (the agent) supply
the **name**, the **purpose sentence**, and the **Hydra overrides**.

> Run every command below from your repo root — both drivers resolve the repo
> with `git rev-parse --show-toplevel` against the current directory.
> Paths below are relative to that root.
> The driver lives at `${CLAUDE_PLUGIN_ROOT}/skills/launch-experiment/new_experiment.sh`.

## Workflow

1. **Draft the script** with the driver (creates folder + body + header comment).
2. **Pre-flight the config** with `--cfg job` — no GPU, catches typo'd override keys.
3. **Launch** on a GPU box via `launch.sh`, which puts the run in a dedicated
   detached tmux session named `exp-<name>` (optionally `fast_dev_run` first).

## 1. Draft (agent path) — run the driver

Everything after `--` is passed through verbatim as Hydra overrides, one token
each. `trainer.notes=<name>` is appended automatically if you don't supply it.

```bash
${CLAUDE_PLUGIN_ROOT}/skills/launch-experiment/new_experiment.sh \
    --name jeda_robocasa_pickplace \
    --purpose "First PickPlace bring-up: qformer-16 resampler, L size, bs64x2 on RoboCasa." \
    --gpus 2 \
    -- data=robocasa model=jeda_robocasa model.encoder.resampler_type=qformer \
       model.size=l model.use_fa4=false trainer.batch_size=64 \
       trainer.max_steps=100000 data.num_workers=16
```

This prints `created experiment/<MMDD>/jeda_robocasa_pickplace.sh` and echoes the
draft. Flags:

- `--name` (required) — script basename; also becomes `trainer.notes`.
- `--purpose` (required in spirit) — one or two sentences; wrapped into the
  header comment. Omit and it inserts a `TODO:` placeholder.
- `--date MMDD` — override the folder (defaults to today, `date +%m%d`).
- `--gpus N` — fills `NUM_GPUS=${NUM_GPUS:-N}` (default 2).
- `--` — **must precede** the Hydra overrides.

The driver refuses to overwrite an existing script and exits non-zero. To
revise a draft, edit the `.sh` file directly (e.g. to expand the header comment
or tweak an override).

## 2. Pre-flight the config (no GPU)

Validate that every override key resolves **before** spending a GPU. Pass the
same override set you handed the driver:

```bash
uv run python train.py --cfg job \
    data=robocasa model=jeda_robocasa model.encoder.resampler_type=qformer \
    model.size=l model.use_fa4=false trainer.batch_size=64 \
    trainer.max_steps=100000 data.num_workers=16 trainer.notes=jeda_robocasa_pickplace
```

Clean exit + a printed resolved config = good. A typo'd key fails loudly, e.g.
`Could not override 'trainer.notarealkey'` — fix the override and re-draft (or
edit the `.sh`). Also syntax-check the drafted file:

```bash
bash -n experiment/<MMDD>/jeda_robocasa_pickplace.sh
```

## 3. Launch (on a GPU box) — in a dedicated tmux session

Launch with `launch.sh`. Training runs are long; the helper starts the run in a
**detached tmux session named `exp-<name>`** (`<name>` = the script basename) so
it survives an SSH disconnect and you can reattach. It tees stdout+stderr to
`experiment/<MMDD>/<name>.log`, forwards `NUM_GPUS`/`CUDA_VISIBLE_DEVICES`/`PORT`,
and refuses to start a second copy if `exp-<name>` already exists.

```bash
${CLAUDE_PLUGIN_ROOT}/skills/launch-experiment/launch.sh experiment/<MMDD>/jeda_robocasa_pickplace.sh
NUM_GPUS=4 ${CLAUDE_PLUGIN_ROOT}/skills/launch-experiment/launch.sh experiment/<MMDD>/jeda_robocasa_pickplace.sh
```

Then:

```bash
tmux attach -t exp-jeda_robocasa_pickplace     # watch it; Ctrl-b then d to detach (run keeps going)
tmux kill-session -t exp-jeda_robocasa_pickplace   # stop the run
```

`new_experiment.sh` prints the exact `launch.sh` line for the script it just
drafted, so you can copy-paste it.

Optional smoke run first (2 train + 2 val iters, no wandb, no checkpoints) — but
this **needs the dataset present** since it actually loads data. Extra args
after the script path pass through `scripts/train.sh` into `train.py`, so you
can patch a launch without editing the file:

```bash
NUM_GPUS=1 ${CLAUDE_PLUGIN_ROOT}/skills/launch-experiment/launch.sh \
    experiment/<MMDD>/jeda_robocasa_pickplace.sh \
    trainer.fast_dev_run=true trainer.wandb_enabled=false
```

A `fast_dev_run` smoke test exits in seconds, so its `exp-<name>` session is
short-lived — that's expected. Running the script directly
(`bash experiment/<MMDD>/<name>.sh`) still works for a quick foreground run, but
then the job dies with your shell; prefer `launch.sh` for any real training run.

## Gotchas

- **`--cfg job` is the only machine-independent check.** `fast_dev_run` loads
  the dataset, so on a box without the data path
  (`configs/data/<name>.yaml:dataset_path`) it fails at the data loader — that's
  a missing dataset, not a bad script. Use `--cfg job` to validate the *config*
  anywhere; use `fast_dev_run` only where the data lives.
- **RTX 6000 Ada needs `model.use_fa4=false`.** bf16 routes to the
  FlashAttention-4 CUTE kernel, which requires Hopper+ (sm_90). On Ada (sm_89)
  it crashes with a block-sparsity tile error regardless of dataset. Add
  `model.use_fa4=false` (Triton backend, still bf16) on Ada boxes; drop it on
  Hopper/B200 for the FA4 speedup.
- **`model`/`data` defaults are `???`.** `train.py` won't instantiate until you
  override both `data=` and `model=`. Always include them in the overrides — the
  driver does not inject them.
- **Folder is `MMDD`, not `YYYY-MM-DD`.** The driver uses `date +%m%d`; pass `--date` to backfill.
- **`trainer.notes` sets the run name** (it flows into the output dir / wandb
  name). The driver pins it to `--name` so the script, the folder entry, and the
  run all share one identifier.

## The bundled scripts

- `${CLAUDE_PLUGIN_ROOT}/skills/launch-experiment/new_experiment.sh` — arg-parses
  `--name/--purpose/--date/--gpus -- <overrides>`, makes `experiment/MMDD/`,
  writes the header-comment + `scripts/train.sh` invocation, `chmod +x`, refuses
  to clobber, and prints the matching `launch.sh` line. It's the draft step.
- `${CLAUDE_PLUGIN_ROOT}/skills/launch-experiment/launch.sh` — runs a drafted experiment in a
  detached tmux session `exp-<name>`, tees to `experiment/<MMDD>/<name>.log`,
  forwards `NUM_GPUS`/`CUDA_VISIBLE_DEVICES`/`PORT`, and guards against starting
  a duplicate session. It's the launch step.

These are the deliverables; this SKILL.md is their man page.

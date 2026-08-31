---
name: launch-experiment
description: Scaffold and launch a training experiment round for a Hydra + accelerate repo that trains through `scripts/train.sh`. Use when asked to "launch an experiment", "start a new run", "set up a round/wave", "create an experiment script", "draft an experiment", or "kick off a sweep". Copies house style from the newest `experiment/` folder (env.sh + arm_overrides.sh + per-arm launchers), pre-flight-validates every arm's config with `--cfg job` before any GPU is touched, and launches each arm as a window in one detached tmux session per round (`exp-<MMDD_topic>`) so a round survives SSH disconnects and can be attached or killed as a single unit.
---

# launch-experiment

An experiment **round** is a folder `experiment/<MMDD_topic>/` (e.g.
`0824_g12`) holding bash scripts that call `scripts/train.sh` with Hydra
overrides. There is no generator — **the newest existing round folder is the
style guide**. Read it (and the round before it, if the newest is atypical)
and write the new round's scripts by hand in the same shape:

- `env.sh` — box-specific exports (cache dirs, `OUT`, …), sourced by every arm.
- `arm_overrides.sh` — SHARED override string + one variable per arm delta;
  edited HERE, never inside a launcher. Only needed for multi-arm waves.
- `<arm>.sh` — per arm: header comment, `cd` to repo root, source the two
  files above, one `scripts/train.sh` call. A single-run experiment is just
  one such script with the overrides inline.
- `launch_all.sh` — optional: loops over `launch.sh` (below) with whatever
  ordering/stagger/GPU-handoff logic the round needs. Round-specific quirks
  live here, hand-written.

GPU pairs, ports, and box constraints come from project memory / CLAUDE.md —
check them, and check `nvidia-smi` for co-located jobs before assigning GPUs.

## Invariants (what makes a script a proper experiment)

1. **Purpose header** — the first comment says what the arm tests and cites
   the design log / context note it comes from. Written for whoever reads the
   folder months later.
2. **`trainer.notes=<arm-name>`** — script basename = `trainer.notes` = run
   name, so the script, the log, the output dir and the wandb run all share
   one identifier.
3. **Pre-flight before GPU** — for every arm, resolve the exact override set
   with `uv run python train.py --cfg job <overrides...>` (clean exit + printed
   config = good; a typo'd key fails loudly) and `bash -n` the script. This is
   the only machine-independent check; `fast_dev_run` needs the dataset.
4. **Tee'd log per arm** — `launch.sh` handles this
   (`experiment/<round>/logs/<arm>.log`).
5. **GPU busy-check before launch** — never stack onto a GPU that already
   holds a job; `launch.sh` guards this when `CUDA_VISIBLE_DEVICES` is set.

## Launch — one tmux session per round

`${CLAUDE_PLUGIN_ROOT}/skills/launch-experiment/launch.sh` runs an arm as a
**window** in the round's session `exp-<MMDD_topic>` (created on first use).
Run it from the repo root:

```bash
CUDA_VISIBLE_DEVICES=0,1 NUM_GPUS=2 PORT=29611 \
    ${CLAUDE_PLUGIN_ROOT}/skills/launch-experiment/launch.sh experiment/0901_foo/arm_a.sh
```

It forwards `NUM_GPUS`/`CUDA_VISIBLE_DEVICES`/`PORT`, tees to
`experiment/<round>/logs/<arm>.log`, refuses a duplicate window (arm already
running) and refuses busy GPUs (`GPU_BUSY_MIB`, default 5000). Extra args after
the script path pass through to the arm script — so a smoke test is the same
arm launched with `trainer.fast_dev_run=true trainer.wandb_enabled=false`
(needs the dataset present; it lands as a short-lived window in the same
session, log kept).

Managing a round:

```bash
tmux attach       -t exp-0901_foo          # all arms as windows; Ctrl-b n/p to flip, Ctrl-b d to detach
tmux kill-window  -t =exp-0901_foo:arm_a   # stop one arm
tmux kill-session -t exp-0901_foo          # stop the whole round tree
tmux ls                                    # exp-* sessions = live rounds
```

Monitors, post-train chains and benchmark passes for the round belong in the
same session — launch them through `launch.sh` too and they show up as extra
windows.

# tensorboard access patterns

Use these when the run logged to `tfevents` files (common for torch + `torch.utils.tensorboard` projects) rather than wandb.

## Locating the event files

TensorBoard writes `events.out.tfevents.<timestamp>.<host>.<pid>.<seq>` under whatever `log_dir` the trainer used. Common layouts:

- Lightning: `lightning_logs/version_N/events.*`
- Hydra: `<hydra_output>/tb/events.*` or `<hydra_output>/tensorboard/events.*`
- Hand-rolled: `runs/<name>/events.*`

Ask the user or grep the training code for `SummaryWriter` / `TensorBoardLogger` if it isn't obvious.

## Reading with tbparse (preferred)

`tbparse` gives you a DataFrame directly:

```python
from tbparse import SummaryReader
reader = SummaryReader("path/to/log_dir", extra_columns={"wall_time"})
df = reader.scalars          # tag, value, step, wall_time
# Pivot for per-tag columns:
import pandas as pd
wide = df.pivot_table(index="step", columns="tag", values="value")
```

Then compute summaries the same way as wandb — don't echo the whole DataFrame.

## Reading with `event_accumulator` (stdlib tensorboard)

```python
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
ea = EventAccumulator("path/to/log_dir",
                      size_guidance={"scalars": 0})  # 0 = load all
ea.Reload()
ea.Tags()  # {"scalars": [...], "images": [...], ...}
events = ea.Scalars("loss/val")  # list[ScalarEvent(wall_time, step, value)]
```

Use this if `tbparse` isn't installed and you can't add dependencies.

## Hyperparameters

If the user logged hparams with `SummaryWriter.add_hparams`, they're in the events file as `HPARAMS` — `tbparse.SummaryReader(..., pivot=True).hparams` surfaces them. Otherwise hparams are usually also dumped to a `config.yaml` or `hparams.yaml` next to the events file; prefer that.

## Baselines

TensorBoard doesn't have a "list all runs in this project" API like wandb. Either:

- List sibling directories of the run's log dir and treat each as a candidate baseline, or
- Read the trainer's manifest (Hydra output root, etc.) to find peer runs.

Ask the user to name the baseline if the directory layout is ambiguous.

# claude-skills

Skills for [Claude Code](https://claude.com/claude-code), packaged as a plugin marketplace.

| Plugin | What it does |
|---|---|
| `asd-ste100` | Writes technical prose under the structural rules of ASD-STE100 Simplified Technical English. |
| `launch-experiment` | Drafts a dated training launcher, validates its config, and starts it in a detached tmux session. |
| `experiment-report` | Writes a post-hoc report on a machine learning run or sweep, and files it as an Obsidian note. |
| `obsidian-vault` | Five skills that work an Obsidian vault as a knowledge graph: search, link, summarize papers, document folders, log the day. |

## Install

Add the marketplace. Then install the plugin you want:

```
/plugin marketplace add kdwonn/claude-skills
/plugin install asd-ste100@kdwonn-skills
/plugin install launch-experiment@kdwonn-skills
/plugin install experiment-report@kdwonn-skills
/plugin install obsidian-vault@kdwonn-skills
```

If you would rather not use plugins, copy the skill directly:

```
git clone https://github.com/kdwonn/claude-skills.git
cp -r claude-skills/plugins/asd-ste100/skills/asd-ste100 ~/.claude/skills/
```

## asd-ste100

Aerospace maintenance manuals use a controlled English called ASD-STE100. It removes the ambiguity that comes from sentence structure.

This skill applies the **structural** half of the standard and deliberately skips the controlled 900-word dictionary. Domain terms such as `checkpoint`, `embedding`, and `gradient` each have one precise meaning. A plainer synonym would read worse. The skill changes how you build sentences, not what they are about.

The skill classifies each block of prose as procedural or descriptive first. It then applies the matching rules. Procedures take the imperative voice and 20 words per sentence. Description takes simple tenses and 25 words per sentence. Both take one instruction per sentence, the active voice, and at most three words per noun cluster.

The skill triggers on ordinary requests. "Write up my notes on X", "add a README for this repo", and "clean this paragraph up" are enough — you never have to say "STE".

It ships `scripts/ste_check.py`, which flags long sentences, passive voice, and long noun clusters in a draft.

**Do not** use it for conversational replies, creative writing, or prompt engineering.

## launch-experiment

This skill turns "run an experiment with X changed" into a round folder you can read back later.

A round is a folder `experiment/MMDD_topic/` holding hand-written bash scripts that call `scripts/train.sh` with Hydra overrides — shared `env.sh` and `arm_overrides.sh`, one launcher per arm. There is no generator: the skill instructs the agent to copy house style from the newest existing round folder and preserve the invariants (a purpose header citing the design log, `trainer.notes` pinned to the arm name so script, log, output dir, and tracked run share one identifier, a tee'd log per arm).

The skill validates every arm's config **before** it touches a GPU. It runs `python train.py --cfg job` with the same overrides. A typo'd override key fails there in a second, instead of after the dataset loads.

The bundled `launch.sh` runs each arm as a **window** in one detached tmux session per round, `exp-<MMDD_topic>`. The round survives an SSH disconnect and is one unit: `tmux attach -t exp-<round>` shows all arms as windows, `tmux kill-window` stops one arm, `tmux kill-session` stops the whole round. Output is teed to `experiment/<round>/logs/<arm>.log`, so runs stay readable after windows close. A duplicate arm launch is refused rather than silently doubled, and when `CUDA_VISIBLE_DEVICES` is set the launch is refused if any listed GPU already holds a job.

### Requirements

- A git repository. `launch.sh` resolves the repo root with `git rev-parse --show-toplevel`, so run it from inside your project.
- A Hydra entry point at `train.py` and a multi-GPU wrapper at `scripts/train.sh` that reads `NUM_GPUS`. This is the layout the skill assumes.
- `tmux` on your `PATH`; `nvidia-smi` for the GPU busy guard.
- At least one existing round folder under `experiment/` to serve as the style guide — box constraints (GPU maps, ports) are expected to live in project memory or `CLAUDE.md`, so the skill degrades outside the repo it grew in.

## experiment-report

This skill writes the report you want to read six months from now.

Name a run and the skill finds it. It accepts a wandb id or URL, a tensorboard log directory, or a Hydra output directory. It also accepts a glob such as `sigreg-* from April 14`, or a plain handle such as "the pusht run from last Tuesday".

Sweeps are a first-class mode. When the handle matches more than one run, the skill organizes the report around the sweep axis instead of run by run.

The skill then reconstructs why you started the run. It reads git commits, your recent sessions in Claude Code, and your Obsidian vault. It confirms that reconstruction with you before it writes. It skips the confirmation only when a commit message or a vault note from the run window already states the intent. It then gathers metrics and config diffs, and writes the report into `0.Inbox/` in your vault.

The skill reads your vault's `CLAUDE.md` first and obeys the conventions it finds there — frontmatter schema, tags, filenames, templates. Its own defaults apply only where that file is silent.

It calls `asd-ste100` for the prose inside the report, so install both if you want the full effect.

### Requirements

- An Obsidian vault. The skill searches your home directory for a `.obsidian/` directory.
- `wandb` on your `PATH`, or a tensorboard log directory, or Hydra outputs. Any one is enough.

## obsidian-vault

A vault is a graph, but most tooling treats it as a folder of files. These five skills work the graph.

Install them together. They call each other: `paper-summary` calls `link-note`, and `link-note` and `vault-documenter` both call `vault-search`.

### The skills

**`vault-search`** — Search that knows which folders matter. It expands your query into 3-5 variants, runs Obsidian CLI searches per folder in parallel, and ranks the hits by where they live. Permanent notes outrank clippings. Without the per-folder split, a folder of long paper abstracts swamps the concise notes you actually wanted.

It has two depths. Quick mode retrieves and ranks. Deep mode adds subagents that synthesize themes, follow `prev_context` chains to trace how an idea evolved, and name the gaps — subtopics you raised but never developed.

**`link-note`** — Finds the links a note should have, then makes them bidirectional. It reads the note, runs a deep vault search, and walks the `prev_context` chain for parents, children, and siblings. It ranks the candidates and proposes 5-10 with reasons.

The second half is the part that compounds. After you accept a link, the skill ripples back: it adds a reference to each note you linked to, under that note's own conventions. A Map note gets a bullet in the right section. A card gets a line in `## Related`. The connection is then visible from both ends.

**`paper-summary`** — Writes the summary you would want a colleague to write. The abstract already recaps the paper, so the skill spends its effort on placement: what this paper changes about work already in your vault, stated concretely enough to act on.

It reads the PDF, including your own highlights and margin notes, and treats those as a priority signal. It searches the vault before it writes, not after. It extracts figures with a bundled script that crops artwork from caption bands, so side-by-side figures and matplotlib vector plots both come out correctly. Each embed gets an interpretive caption that says what to look at. It ends with research ideas that cross the paper with a note you already have.

**`vault-documenter`** — Adds a dated snapshot to your folder notes. It reads the most recent notes in each folder, finds the themes, and writes what is new since the last snapshot. Snapshots are append-only, so the folder note becomes a history of the folder. It also suggests a new Map note when five or more notes share a theme that no index covers. It suggests only; it does not create.

**`productivity-daily-log`** — Writes the log for a day from evidence, not memory. It reads your Claude Code session transcripts, your git commits from all repos, and the files your vault gained or lost. It knows the day does not end at midnight: the logical day runs to 04:00 the next morning, so a 2 a.m. session lands in the right log.

It runs unattended. Point `launchd` or `cron` at `claude -p /productivity-daily-log` and it refreshes the last four days in place, without touching text you wrote yourself.

### Requirements

- An Obsidian vault, with Obsidian running.
- [`obsidian-cli`](https://github.com/Yakitrak/obsidian-cli) on your `PATH`. The skills fall back to `grep` when a call fails, but search quality drops.
- `PyMuPDF` for `paper-summary` figure extraction: `pip install pymupdf`.
- `gh` for `productivity-daily-log` commit gathering. Optional.

### Vault conventions

These skills carry my folder layout in them: `0.Inbox/` for capture, `1.Projects/` for active work, `2.Cards/` for permanent notes, `3.Clippings/`, `4.Timestamps/` for daily logs, `Archive/`, and `Resource/Papers/`. Notes take a `YYMMDDHH` filename prefix, a `prev_context` frontmatter field that chains one idea to the next, and a `#Map` tag on index notes.

If your vault uses different names, edit the folder lists at the top of each `SKILL.md`. The ranking logic is the part worth keeping; the folder names are not.

Every skill reads your vault's `CLAUDE.md` first and obeys the conventions it finds there.

### macOS note

The skills pass `dangerouslyDisableSandbox: true` on every `obsidian-cli` call. Claude Code's sandbox blocks the CLI's Unix socket, and the call hangs instead of failing. They also call `obsidian-cli` and never `obsidian` — on a case-insensitive filesystem, `obsidian` resolves to the GUI app binary, which starts a second instance and hangs.

## License

MIT

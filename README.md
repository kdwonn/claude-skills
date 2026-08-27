# claude-skills

Two skills for [Claude Code](https://claude.com/claude-code), packaged as a plugin marketplace.

| Plugin | What it does |
|---|---|
| `asd-ste100` | Writes technical prose under the structural rules of ASD-STE100 Simplified Technical English. |
| `experiment-report` | Writes a post-hoc report on a machine learning run or sweep, and files it as an Obsidian note. |

## Install

Add the marketplace. Then install the plugin you want:

```
/plugin marketplace add kdwonn/claude-skills
/plugin install asd-ste100@kdwonn-skills
/plugin install experiment-report@kdwonn-skills
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

## License

MIT

# Reconstructing intent: where to look

You want to answer one question: **what question was this run trying to answer?** Not "what did the run do" — that's in the code — but "why did the user start it."

Three sources, in order of signal-to-noise:

## 1. Git (highest signal)

The commit the run was trained at, and commits around it, almost always describe the intent. Once you have the run's commit hash (from `wandb-metadata.json → git.commit` or the local run metadata):

```bash
# The run's exact commit
git show --stat <commit>

# Commits around the run (week before, day after)
git log --all \
  --since="<run_start - 7 days>" --until="<run_start + 1 day>" \
  --pretty=format:"%h %ai %s"

# What files changed in the run's commit
git show --name-only <commit>
```

Pay attention to:

- The commit subject — often literally *is* the intent ("try sigreg=0.01 to see if collapse recovers")
- Diff in config files — tells you what knob was turned
- Sibling branches — "experiment/<name>" branches usually carry context

## 2. Claude sessions

Session transcripts live at `~/.claude/projects/<slug>/*.jsonl`, where `<slug>` is the project directory with `/` → `-` (e.g. `/home/you/work/my-project` → `-home-you-work-my-project`). Each line is a JSON message (user or assistant).

```bash
# Find sessions modified near the run start
ls -lt ~/.claude/projects/<slug>/*.jsonl | head -20

# Grep for keywords (run id, config overrides, experiment name)
grep -l "sigreg-0.01" ~/.claude/projects/<slug>/*.jsonl
```

Load the matching session(s) and pull out the **user's** messages — that's where intent lives. Assistant messages are about what happened, not what was wanted. Prefer sessions whose timestamp is within a few days of the run.

A session often contains an exchange like "let's try X because Y" — that Y is what you're looking for.

## 3. Obsidian vault

Auto-discover the vault by looking for a `.obsidian/` directory under the user's home:

```bash
find ~ -maxdepth 4 -type d -name .obsidian 2>/dev/null
```

The parent of `.obsidian/` is the vault root. Inside the vault, look at:

- `0.Inbox/` — recent, unorganized notes
- `1.Projects/` — active project notes (often contain experiment logs)
- `2.Cards/` — permanent knowledge (rarely about a specific run, but can explain motivation)

Look at the vault's `CLAUDE.md` (if present) — it describes the vault layout and any CLI tools available.

```bash
# If the vault ships an `obsidian` CLI (check vault/CLAUDE.md), prefer it:
obsidian search query="sigreg"
obsidian search query="<experiment keyword>" path="0.Inbox"

# Otherwise raw grep (be careful, vaults can be huge):
grep -rl --include='*.md' "sigreg" <vault_root>/0.Inbox <vault_root>/1.Projects
```

Filter by date: the note you want is likely from the same week as the run. Files in `0.Inbox/` with `YYMMDDHH` prefixes encode their date in the filename.

When you find a relevant note, **save its title** — you'll wikilink to it in the report.

## When to stop looking

The report doesn't need a perfect intent statement; it needs one the user will recognize as correct. If after the three sources you can write a one-sentence intent statement that matches at least one concrete piece of evidence (a commit, a session message, a note), stop. If all three sources came up empty, use `AskUserQuestion` with 2–3 hypotheses as options. Don't keep grepping in hope.

## Interview prompts (if needed)

Good questions for the interview step — propose hypotheses, not open-ended asks:

- "What were you hoping to learn from this run?" with options like "test a specific hyperparameter", "reproduce a baseline", "debug an earlier failure", "scale up a working config".
- "Is there a reference run I should compare against?" with options: the most recent run, a specific named run, no comparison needed.
- "Is there a note in your vault this run was associated with?" — skip this if you already found a candidate; use it when you struck out.

Keep interviews to 2–3 questions total. The user's attention is expensive; if you already have 80% of the picture, just write the draft and let them correct it.

---
name: vault-documenter
description: Update Obsidian vault folder notes with snapshot summaries of recent activity. Analyzes recent notes in key folders (0.Inbox, 1.Projects and subfolders, 2.Cards), adds a dated snapshot summarizing new themes and connections, and suggests new Map notes when 5+ notes share a common theme. Use when user wants to document vault state, snapshot recent activity, update folder summaries, or refresh vault documentation.
allowed-tools: Read, Grep, Glob, Edit, Skill, Agent, Bash
model: claude-sonnet-4-6
effort: high
---

# Vault Documenter

Add snapshot summaries to folder notes by analyzing recent vault activity. Does NOT rewrite CLAUDE.md structure — folder notes are the source of truth for folder semantics.

## Target Folders

Update folder notes in these locations:
- `0.Inbox/` — no folder note exists; skip unless user requests creation
- `1.Projects/1.Projects.md` and each project subfolder's folder note (e.g., `CompACT/CompACT.md`)
- `2.Cards/2.Cards.md`

Do NOT touch `Archive/`, `Resource/`, or `3.Clippings/` folder notes unless explicitly asked.

## Workflow

### 1. Read Current Folder Notes

Read each target folder note. Identify whether a `# Summary` section already exists and whether previous snapshots are present.

### 2. Analyze Recent Notes (use Agent tool, parallelize across folders)

For each target folder, spawn an Explore subagent:

```
Agent tool:
  subagent_type: Explore
  prompt: "Read the most recent ~15 notes (by filename timestamp prefix YYMMDDHH, highest first)
    in <folder_path>. For each note, extract:
    1. Title and timestamp
    2. Key topics and tags
    3. Wikilinks to other notes (prev_context frontmatter and inline links)
    4. Core idea in one sentence
    Return a structured list sorted by recency."
```

### 2a. Cross-reference themes (Skill: vault-search, quick mode)

For each major theme identified in step 2, invoke the `vault-search` skill via the Skill tool in **quick** mode to find related notes outside the current folder. Do NOT write an output note — use the results directly.

This enriches the snapshot with cross-folder connections (e.g., a Cards note linking to a Project theme, or a Paper grounding an Inbox idea).

### 3. Write Summary Section

Edit each folder note to add or update a `# Summary` section **above** the Waypoint block. The summary has two subsection types:

#### `## Overall` (write once, update when scope changes)

A concise description of how this folder is used and operationalized. Not a content dump — focus on the folder's role in the knowledge system.

- For diverse folders (e.g., `2.Cards`), describe the category's function rather than listing themes
- For project folders (e.g., `CompACT`), summarize the project goal and current phase
- 2-4 sentences max

#### `## YYMMDDHH` (snapshot, appended each run)

A dated snapshot capturing the diff from the previous snapshot. Use the current date as the timestamp prefix (format: `YYMMDDHH`, e.g., `26021616`).

Guidelines:
- Focus on what's NEW since the last snapshot (or describe the current state if no previous snapshot exists)
- Use `[[wikilinks]]` proactively to reference notes
- Reveal connections between notes — don't just list them, explain how they relate
- Note emerging themes or shifting focus areas
- 3-8 bullet points typical length

Example:

```markdown
## 26021616
- Focus shifted from architecture search to **objective design** — see [[25081519 detailed idea for the new loss]] building on [[25081217 first sketch of the objective]]
- New evaluation notes trace a negative result: [[25090820 plan for improving eval scores]] → [[25100321 why the eval did not move]]
- Conference submission wrapped up in [[26012301 submission writeup]]
```

#### Section ordering in the folder note

```
# Summary             ← add/update this
## Overall            ← write once, update rarely
## YYMMDDHH           ← most recent snapshot first
## YYMMDDHH           ← previous snapshot
...
                      ← existing content (tags, links, etc.) preserved below
%% Begin Waypoint %%  ← never touch this
...
%% End Waypoint %%
```

### 4. Suggest New Map Notes

After analyzing each folder, check if 5+ notes share a common theme that lacks a `#Map` note. Use the `vault-search` skill in **quick** mode to verify no existing Map note already covers the theme. If the theme is uncovered, suggest it to the user:

```
Suggested Map note: "Map - <Theme>"
Related notes: [[note1]], [[note2]], [[note3]], ...
Reason: These N notes all address <shared theme> but no Map note connects them.
```

Do NOT create Map notes automatically — only suggest them.

## Important Rules

- **Never modify Waypoint blocks** — the Waypoint plugin manages file lists automatically
- **Never add file lists manually** — Waypoint handles `%% Begin Waypoint %%` sections
- **Preserve existing content** — tags, links, Related Concepts sections, and other manually curated content in folder notes must be kept intact
- **Snapshots are append-only** — never delete or rewrite previous `## YYMMDDHH` snapshots, only add new ones above previous ones (reverse chronological)
- Follow all note-writing conventions from CLAUDE.md (no duplicate H1, line spacing rules, wikilink alias restrictions in tables)

---
name: vault-search
description: Multi-agent search across Obsidian vault for comprehensive knowledge retrieval. Use when (1) searching for notes ("find notes about X", "search for Y"), (2) answering knowledge questions ("what do I know about X", "summarize my understanding of Y"), (3) ANY task requiring comprehensive understanding of vault contents - research planning, connecting ideas, finding related work, understanding what exists before creating new content. Uses Obsidian CLI for fast retrieval and subagents for synthesis.
allowed-tools: Read, Grep, Glob, Edit, Skill, Agent, Bash
---

# Vault Search

Obsidian CLI-powered search with priority-aware ranking and optional deep synthesis.

Architecture: **Expand → Retrieve (CLI) → Rerank/Analyze (subagents)**

Run every command from the vault root. If the working directory is not the vault, locate it by
searching for a `.obsidian/` directory under the user's home, and use that path as the base for
all folder-scoped commands below.

> **Obsidian CLI — read before any CLI call (applies to the main agent AND every spawned subagent):** invoke `obsidian-cli`, never `obsidian` — on this case-insensitive Mac, `obsidian` is the GUI **app** binary and running it with a subcommand hangs. Pass `dangerouslyDisableSandbox: true` on every `obsidian-cli` Bash call; the sandbox blocks the CLI's `~/.obsidian-cli.sock` socket and the call hangs without it. **Subagents do not inherit this rule automatically — their prompts must state it.** If `obsidian-cli` is unavailable or returns "unable to find Obsidian", fall back to Grep over the vault.

## Stable Vault Conventions

- **Top-level folders**: `0.Inbox/`, `1.Projects/`, `2.Cards/`, `3.Clippings/`, `4.Timestamps/`, `Archive/`, `Resource/`
- **#Map tag**: Index/hub notes containing curated links and Dataview queries
- **Knowledge flow**: Inbox → Cards (permanent knowledge), Projects → Archive (completed work)
- **Papers location**: `Resource/Papers/`

Everything else (subfolders, tags, note counts) is dynamic—discover at search time.

## Search Priority

1. **2.Cards/** - Permanent knowledge (processed from Inbox)
2. **1.Projects/** - Active research work
3. **#Map notes** - Curated indices (any location)
4. **Resource/Papers/** - Research literature

Secondary (if needed): `0.Inbox/`, `3.Clippings/`, `Archive/`

## Execution

### 1. Parse & Expand Query

Extract search terms, intent, and output path (default: `0.Inbox/`).

**Query expansion**: The vault mixes English technical terms with Korean prose. Generate 3-5 variant search queries:
- English technical terms (e.g., "diffusion model", "latent space")
- Key concept synonyms and abbreviations (e.g., "VAE", "variational autoencoder")
- Wikilink targets (e.g., `[[score distillation]]`, `[[world model]]`)
- Korean equivalents if applicable

Determine search depth:
- **Quick**: Simple lookups, finding specific notes → Steps 2-3 only
- **Deep**: Synthesis tasks, "what do I know about X", connecting ideas → Steps 2-5

### 2. CLI Retrieval

Run CLI commands **in parallel** via multiple Bash tool calls. Split searches **by folder** to ensure balanced coverage — without this, `Resource/Papers/` (long abstracts with many keyword hits) dominates results and pushes out concise but high-value Cards and Projects notes.

**Content search** — for each expanded query term, run separate calls per folder:
```bash
# High-priority folders (higher limits)
obsidian-cli search:context query="term" path="2.Cards" limit=10
obsidian-cli search:context query="term" path="1.Projects" limit=10

# Medium-priority
obsidian-cli search:context query="term" path="Resource/Papers" limit=5
obsidian-cli search:context query="term" path="0.Inbox" limit=5

# Lower-priority (only if needed)
obsidian-cli search:context query="term" path="3.Clippings" limit=3
```

Run all of these in parallel across all query terms. For 3 query terms this means ~9-15 parallel calls (skip lower-priority folders unless the query is broad).

**Tag-based discovery**:
```bash
obsidian-cli tags counts sort=count
```

**Graph-based discovery** (when query matches a known note name):
```bash
obsidian-cli backlinks file="known note"
obsidian-cli links file="known note"
```

Why CLI over Grep/Glob:
- `search:context` returns file:line:content with section-aware matching
- `backlinks` provides graph-based reverse discovery (impossible with Grep)
- `tags` enables tag-based clustering
- No subagent overhead

### 3. Merge & Rank Results

Perform all deduplication and ranking **in-context** — do not spawn Bash commands for this step. The result set is small enough to process directly.

1. Deduplicate results across all CLI calls by file path
2. Apply priority weighting by location:
   - **2.Cards/** notes: highest priority (permanent knowledge)
   - **1.Projects/** notes: high priority (active research)
   - **#Map notes** (any location): high priority (curated indices)
   - **Resource/Papers/**: medium priority (literature)
   - **0.Inbox/**, **3.Clippings/**, **Archive/**: lower priority
3. Select top 15-20 candidates

**For quick searches**: Skip to Step 6 (output).

### 4. Deep Read (deep mode only)

Read top 10-15 results using the Read tool. Use `obsidian-cli outline file="note name"` to understand note structure when needed.

### 5. Subagent Analysis (deep mode only)

Spawn 2-3 parallel Explore agents using Agent tool with `subagent_type: "Explore"`. Pass the retrieved content to all agents.

**Agent A - Reranker & Theme Synthesis:**
```
Given these notes from a vault search for "[QUERY]":
[RESULTS WITH CONTENT]

1. Rerank results by semantic relevance to the query
2. Identify 3-5 major themes across these notes
3. For each theme: name it, list contributing notes, summarize key insights
4. Map which notes contribute to which themes
```

**Agent B - Context Chain & Literature Bridge:**
```
Given these notes from a vault search for "[QUERY]":
[RESULTS WITH CONTENT]

Run every `obsidian-cli` command below through the Bash tool with `dangerouslyDisableSandbox: true` — without it the call hangs. Never call `obsidian` (that is the GUI app); use `obsidian-cli`. If it fails, fall back to Grep.

1. Follow prev_context chains: for each note with a prev_context value, use Bash to run:
   obsidian-cli property:read name="prev_context" file="<note name>"
   Then read the linked notes to trace idea evolution.

2. Cross-reference with papers: use Bash to run:
   obsidian-cli search:context query="<key term>" path="Resource/Papers" limit=10
   For relevant papers found, read them with the Read tool.

3. Return: context chain paths, how ideas evolved, paper-to-note connections, relevant findings.
```

**Agent C - Gap Analysis (optional, for broad queries):**
```
Given these notes from a vault search for "[QUERY]":
[RESULTS WITH CONTENT]

Analyze what's missing:
- What subtopics are mentioned but not developed?
- What questions are raised but not answered?
- What connections between notes could exist but don't?
- What related topics in the field are absent from the vault?
Return: gaps, open questions, suggested areas to explore.
```

### 5a. Merge Synthesis

Combine outputs from all agents into a unified synthesis:
- Themes (Agent A) form the main structure
- Context chains and literature bridges (Agent B) add temporal/evolutionary context and ground findings in research
- Gaps (Agent C) suggest next steps

### 6. Write Output

To specified path or `0.Inbox/YYMMDDHH vault-search <query>.md`:

For **quick searches**, use a compact format:

```markdown
---
tags: [vault-search]
query: "<query>"
---

## Summary
<2-3 sentence synthesis>

## Results

### 1. [[Note Title]]
- **Location**: folder/path
- **Relevance**: why this matches
- **Excerpt**: key passage
...
```

For **deep searches**, use the full synthesis format:

```markdown
---
tags: [vault-search]
query: "<query>"
---

## Summary
<2-3 sentence synthesis combining all agent outputs>

## Themes
<From Agent A: major themes with contributing notes>

## Top Results

### 1. [[Note Title]]
- **Location**: folder/path
- **Relevance**: why this matches
- **Excerpt**: key passage
...

## Context Chains
<From Agent B: how ideas evolved, prev_context paths>

## Literature Connections
<From Agent B: paper-to-note mappings, relevant findings>

## Gaps & Open Questions
<From Agent C: missing subtopics, unanswered questions, suggested explorations>
```

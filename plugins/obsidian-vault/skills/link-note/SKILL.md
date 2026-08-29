---
name: link-note
description: Semantic link discovery for Obsidian notes. Analyzes a note's content and finds meaningful connections using vault-search (deep mode), prev_context chains, and priority ranking. Use when user wants to find related notes, discover links, connect ideas, or enrich a note with wikilinks.
allowed-tools: Read, Grep, Glob, Edit, Skill, Agent, Bash
---

# Link Note - Semantic Link Discovery

Analyze a note semantically and discover meaningful links using the vault's knowledge structure.

Use `obsidian-cli` (never `obsidian` — that resolves to the GUI app binary and hangs) with `dangerouslyDisableSandbox: true` on every Bash call, including in any spawned subagent; the sandbox blocks the CLI's `~/.obsidian-cli.sock` socket. Fall back to Grep if a call fails.

## Workflow

### 1. Get target note

If `$ARGUMENTS` provided, use as note path. Otherwise, ask the user.

### 2. Read and understand the note

- Extract key concepts, themes, domain
- Check frontmatter `prev_context` for idea chain
- Note existing links and tags
- Extract 3-5 key search terms for later steps

### 3-4. Parallel discovery

**IMPORTANT**: Run these two tracks in parallel.

**Track A: Vault-wide search** (Skill: vault-search, deep mode)

Invoke the `vault-search` skill via the Skill tool in **deep** mode with the key search terms from step 2. Do NOT write an output note — use the results directly.

This provides:
- Related notes in Cards, Projects, Inbox
- Relevant Map notes with their linked content
- Paper matches from Resource/Papers/
- Context chains showing how ideas evolved (prev_context paths)
- Theme synthesis across matching notes
- Gap analysis for missing connections

**Track B: prev_context chain & graph via CLI**

Trace the target note's relationships entirely via Obsidian CLI commands (no subagent needed). Run these Bash commands in parallel:

**Backward chain** (find parents):
```bash
obsidian-cli property:read name="prev_context" file="target note"
# → returns parent note name; then repeat for parent to find grandparent, etc.
```

**Forward chain** (find children):
```bash
obsidian-cli backlinks file="target note"
# → candidate list; for each candidate, check:
obsidian-cli property:read name="prev_context" file="candidate"
# → if it points to target, it's a child
```

**Siblings** (notes sharing same parent):
```bash
# After getting parent from backward chain:
obsidian-cli backlinks file="parent note"
# → check which ones have prev_context pointing to parent
```

**Graph context**:
```bash
obsidian-cli links file="target note"        # outgoing links
obsidian-cli backlinks file="target note"    # incoming links
obsidian-cli tags file="target note"         # tags for similarity search
```

### 5. Merge and filter

Combine results from vault-search (Track A) and CLI chain/graph (Track B):
1. Deduplicate by file path
2. Remove already-linked notes and the target note itself
3. Apply priority ranking (see Priority section below)

### 6. Subagent Reranking (1 Explore agent)

Spawn 1 Explore agent via Agent tool with `subagent_type: "Explore"`. Pass all candidates + target note content:

```
Given the target note content and these candidate notes for link discovery:
[TARGET NOTE CONTENT]
[CANDIDATE NOTES WITH EXCERPTS]

1. Rank candidates by semantic relevance to the target note
2. Select top 5-10 suggestions
3. For each suggestion, provide:
   - Why it should be linked
   - Whether it's an inline link (replace existing text) or Related section candidate
4. Categorize by source: Map-based, chain-based, vault match, paper match
```

### 7. Present suggestions

```markdown
## Link Discovery for [[note name]]

**From Map: [[Map Name]]**
- [[note]] - relevance reason

**Idea chain (prev_context):**
- Chain: [[parent]] → [[current]] → [[child]]
- Siblings: [[sibling]]

**Vault connections:**
- [[note]] - conceptual connection

**Papers (Resource/Papers/):**
- [[paper note]] - matching keywords

**Suggested inline links:**
- Line N: "phrase" → [[target]]

**Related section candidates:**
- [[note]] - reason
```

### 8. Apply after confirmation

Ask user which to apply:
1. Inline links - replace text with wikilinks
2. Related section - append `## Related`
3. Skip - show only

### 9. Ripple — update discovered notes

After applying links to the target note, update the discovered notes so they reference back. This makes links bidirectional and compounds the vault's connectivity.

**Mode**:
- **Auto-ripple** (`$RIPPLE_AUTO`): Apply all ripple edits without confirmation. Used when link-note is chained from `paper-summary`. Log every edit for activity logging.
- **Interactive** (default when link-note is called directly): Present proposals and ask user to confirm batch/individual/skip.

**How to update each note type**:

- **Map notes**: Read the Map's heading structure. Insert `- [[target note]]` as a bullet under the most relevant subsection. Match the existing bullet format exactly. Never modify Waypoint blocks (`%% Begin Waypoint %%` ... `%% End Waypoint %%`).
- **Cards / Idea notes**: Look for existing `## Related Notes`, `## Related Concepts`, or `## Related` section. If found, append `- [[target note]] — 1-line reason` there. If absent, create `## Related` section above the `# Next context` Dataview query block.
- **Paper summaries**: Append `- [[target note]] — 1-line reason` to `## Related Notes`. If absent, create it above `## Research Ideas` or `# Next context`.
- **Project folder notes**: Append to `## Related Concepts` if it exists. Do NOT modify `## Summary` snapshots or `## Overall` (those are append-only per vault-documenter rules).

**Guards**:
1. Before adding a back-reference, check if `[[target note]]` already appears anywhere in the discovered note. Skip if already present.
2. Never modify Waypoint blocks.
3. Read the discovered note before editing to verify its structure.

**Interactive presentation format** (skip in auto-ripple mode):

```markdown
## Ripple Updates

**Map notes:**
- [[Map - Fisher Info...]] → add under "## Main Research Idea"

**Cards:**
- [[bisimulation]] → append to "## Related"

**Paper summaries:**
- [[Unified Latents (UL) Summary]] → append to "## Related Notes"

Apply: [all] [select individually] [skip ripple]
```

## Priority

1. **Map-based** (highest - user-curated)
2. **prev_context chains** (explicit relationships)
3. **Vault matches** (discovered)
4. **Paper matches** (Resource/Papers/)

## Guidelines

- Suggest 5-10 high-quality links, not exhaustive lists
- Explain reasoning for each
- Respect user's choice on which to apply
- Ripple updates are opt-in in interactive mode, automatic in auto-ripple mode
- When adding to Map notes, match the existing bullet format and section structure exactly
- Skip ripple for a discovered note if the target note is already mentioned in it
- After ripple edits, follow the **Activity logging** instruction in CLAUDE.md: append log entries to the daily note

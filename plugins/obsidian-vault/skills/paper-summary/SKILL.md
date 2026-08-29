---
name: paper-summary
description: Create a 5-10 minute read summary of AI/ML research papers with figure captures and vault connections. Use when user wants to summarize a paper, create paper notes, or asks about reading/understanding a research paper. Input can be a PDF URL, file path, or an Obsidian pointer note from Resource/Papers/. Outputs Obsidian-flavored markdown with embedded figures, semantic links to related vault notes, and potential research ideas.
allowed-tools: Read, Bash, Grep, Glob, Write, Edit, WebFetch, WebSearch, Skill
---

# Paper Summary Skill

Create rich summaries of AI/ML research papers with figure captures and vault integration.

The value of a summary in a vault is not the recap — the abstract already does that. It is **placement**: what this paper changes about work already in the vault, stated concretely enough to act on. A well-written summary reads like a colleague who knows the user's projects explaining why they should care. Everything below serves that.

Any `obsidian-cli` call (never `obsidian` — that's the GUI app binary and hangs) needs `dangerouslyDisableSandbox: true` on the Bash tool; the sandbox blocks the CLI's `~/.obsidian-cli.sock` socket.

## Workflow

Steps 1–3 gather; step 4 writes. Resist writing before the vault search — the connections should shape the prose, not be bolted on at the end.

### 1. Resolve paper source

Determine the paper source from user input:
- **URL**: Direct PDF link (e.g., arxiv.org/pdf/...)
- **File path**: Local PDF file
- **Vault pointer**: Markdown note in `Resource/Papers/` containing PDF path

For vault pointers, read the note to extract the actual PDF location from the `File:` field in the metadata callout. Also check its backlinks — an existing note may already cite this paper, which tells you what the user already took from it:
```bash
obsidian-cli backlinks file="pointer note name"
```

### 2. Read the paper

Read the PDF with the Read tool (`pages` parameter for long PDFs; the main body is usually enough — read the appendix only when the summary depends on it).

**PDFs exported from a reader such as Zotero are often annotated.** Highlights and handwritten margin notes are the user's own reading trace: they mark which claims mattered, which numbers were doubted, and where they got stuck. Treat them as a priority signal — a summary that answers a margin question ("needs re-check", "why careful dedup?") is worth far more than one that ignores it. Note that annotations also land inside extracted figures; if handwriting obscures a figure you want to embed, crop a clean copy from an unannotated region or pick a different figure.

While reading, note the 3–5 figures that carry the argument — usually the main method diagram, the headline result, and whichever plot the paper's central claim actually rests on.

### 3. Search the vault before writing

Find where this paper lands. Run `obsidian-cli search query="<concept>"` for the paper's core concepts, plus targeted `grep -ril` over `2.Cards/`, `1.Projects/`, `0.Inbox/` — `obsidian-cli search` is fuzzy and returns loose matches, so grep is the precise instrument when you know the phrase. Also check `ls -t 0.Inbox/*.md | head` and `ls -t 1.Projects/*/*.md | head` to see what the user is working on *this week*; a connection to an active thread is worth more than a connection to a two-year-old note.

For each promising hit, read enough of the note to link honestly. A wikilink with a specific reason ("supplies the capacity denominator this note's heuristics lack") is useful; a bare list of topically-adjacent titles is noise.

### 4. Extract figures

Use `scripts/extract_figures.py` (requires PyMuPDF: `import fitz`).

#### 4.1 Auto-extract

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/paper-summary/scripts/extract_figures.py" auto \
  "paper.pdf" "$TMPDIR/figures" --prefix PaperName --dpi 300
```

The script finds captions (blocks that *start* with "Figure N", so inline cross-references don't create phantom figures), assigns each one a horizontal band clipped against its row neighbours, and unions the bitmaps, vector drawings, and non-prose text inside that band. Side-by-side figures and matplotlib vector plots both come out correctly cropped.

Useful flags: `--figures 1,3,5` to extract a subset, `--tables` to also capture `Table N` blocks, `--with-caption` to include the caption text in the crop.

Output is JSON with `path`, `preview`, `bbox_pct`, `caption`, and `suspect` per figure.

#### 4.2 Verify

Each figure gets a `-preview.png` sibling downscaled to fit the Read tool's 1500px limit — read those, not the full-resolution files. (Don't reach for `sips` to resize; it writes a scratch file outside the sandbox and fails.)

You do not need to inspect all of them. Check the ones you intend to embed, plus anything with `"suspect": true` — that flag marks crops that came out as slivers or extreme aspect ratios, which is where the failures concentrate.

#### 4.3 Manual region crop (fallback)

When a crop is wrong, or you want a deliberate composite (two paired panels in one image reads better than two separate embeds), use `region`. Get coordinates from `bbox_pct` in the auto output, or from:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/paper-summary/scripts/extract_figures.py" pages "paper.pdf" --pages 0,1,5
```

which lists each caption's position as page fractions. Then:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/paper-summary/scripts/extract_figures.py" region \
  "paper.pdf" "$TMPDIR/figures/PaperName-fig1.png" \
  --page 0 --top 0.455 --bottom 0.697 --left 0.09 --right 0.95 --dpi 300
```

`--page` is 0-indexed; boundaries are fractions of page dimensions.

#### 4.4 Copy into the vault

```bash
cp "$TMPDIR/figures/PaperName-fig1.png" "Resource/Attachments/PaperName-fig1.png"
```

Use a short, collision-proof prefix (`LMMemorize-`, not `Memorize-`) — `Resource/Attachments/` is a flat shared folder.

#### 4.5 Embed with an interpretive caption

```markdown
![[PaperName-fig1.png]]
*Figure 1: What the reader should see in this plot, not a copy of the paper's caption.*
```

The paper's caption is already in the figure. The italic line underneath earns its space by saying what the figure *shows* — which curve matters and why.

### 5. Write the note

Write to `0.Inbox/` as `YYMMDDHH {Paper Title} Summary.md`, following [references/summary-template.md](references/summary-template.md). If an `obsidian-markdown` skill is installed, use it for Obsidian syntax questions.

Target 1800–2500 words. The floor matters more than the ceiling: a summary that skips the vault-placement section to stay short has cut the only part the abstract couldn't provide.

Vault conventions that are easy to miss and cause lint failures:
- `created:` in frontmatter, plus `tags`, `aliases`, `paper_url`, `authors`, `year`, `venue`, `source_note` (wikilink to the `Resource/Papers/` pointer, if there was one), `prev_context`
- `#claude` tag on the line after the frontmatter
- No H1 — the filename is the title
- `# Next context` and `# Map` Dataview blocks at the end (see the template)
- Never `[[note|alias]]` inside a table — the pipe breaks the column separator

### 6. Connect to the vault via link-note

Invoke the `link-note` skill via the Skill tool on the written note, passing the note path and `$RIPPLE_AUTO` so ripple edits apply without confirmation. This adds back-references from the notes you linked, so the connection is visible from both ends.

Then verify every wikilink resolves — a summary full of broken links pollutes `vault-lint`:
```bash
grep -o '\[\[[^]|]*\]\]' "0.Inbox/<note>.md" | sed 's/\[\[//;s/\]\]//' | sort -u | \
  while read -r n; do find . -name "$n.md" -not -path "./.git/*" | grep -q . || echo "MISSING: $n"; done
```
(Image embeds will show as missing; check those against `Resource/Attachments/` instead.)

### 7. Research ideas

Write 3–4 directions, each tagged `#research_idea #research_idea_by_claude`. The generative move is crossing the paper with something already in the vault — an idea that could have been written from the abstract alone isn't worth the space.

A good idea here names the vault note it builds on, states what would be measured or built, and says what would falsify it or what it would cost. "Apply this to world models" is not an idea; "run the paper's synthetic-capacity protocol on the JEDA predictor to get a bits denominator for the overfit diagnostics, with the open question of what precision floor to declare for continuous latents" is.

### 8. Log the session

Append to the daily note (`4.Timestamps/YYYY-MM/YYYY-MM-DD ddd.md`) under `## Sessions`: one line for the created summary and one per note the ripple touched, each with a reason.

## Common Issues

**A crop is a thin sliver** (flagged `suspect`). The caption's artwork sits above a paragraph break the clustering treated as a boundary, or the figure is on the previous page. Use `region` with coordinates from the `pages` subcommand.

**A figure spans the full page width but the caption is one column.** The band is derived from the caption, so a wide figure with a narrow caption gets under-cropped. Use `region` with `--left 0.05 --right 0.95`.

**Figure quality is poor.** Raise `--dpi 400`. Default is 300, which is plenty for screen reading.

**A figure contains the user's handwriting.** Expected for annotated Zotero PDFs — decide whether the annotation adds context (often it does) or obscures the plot, and re-crop or substitute accordingly.

**`obsidian-cli` hangs or errors.** Confirm `dangerouslyDisableSandbox: true` and that the binary is `obsidian-cli`. If it reports "unable to find Obsidian", the app needs restarting; fall back to `grep`/`find` meanwhile.

## Example

User: "Summarize this paper: Resource/Papers/How much do language models memorize(2025).md"

1. Read the pointer note → PDF path in iCloud Zotero; `backlinks` shows one note already cites it
2. Read the PDF, including the margin annotations, and note the plateau plot as the load-bearing figure
3. Search the vault for *capacity*, *bottleneck*, *memorization*, *rate-distortion*; read the three strongest hits
4. `auto` extract → verify previews → `region` re-crop one composite → copy to `Resource/Attachments/` as `LMMemorize-fig1-2.png`
5. Write `0.Inbox/26082713 How much do language models memorize Summary.md`, with a "Why this matters for my work" section tying 3.6 bits/parameter to the vault's open question about prior capacity
6. `link-note` with `$RIPPLE_AUTO` → back-references land in the three linked notes
7. Four research ideas, each naming the vault note it extends
8. Log all four file touches in the daily note

# Summary Template

Structure for paper summaries. Adapt section depth to the paper — a theory paper may need three method subsections and no results table; an empirical paper the reverse. The sections marked **required** are the ones that make the note work as a vault citizen rather than a floating document.

```markdown
---
created: {YYYY-MM-DDTHH:MM:SS}
tags:
  - paper_summary
  - {topic_tags}
  - claude
aliases:
  - {short_name}
paper_url: {url}
authors: {author_list}
year: {year}
venue: {venue}
source_note: "[[{pointer_note_name}]]"  # only if triggered from Resource/Papers/
prev_context:
  - "[[{related_note}]]"
---
#claude

## TL;DR
<!-- 2-4 sentences. What does this paper do, how, and why does it matter here? -->

## Key Contributions
<!-- 3-5 bullets, each distinguishing this work from prior work -->
-
-
-

## Method Overview
<!-- Intuition first, then mechanism. Figures carry the load. -->

![[{paper}-fig1.png]]
*Figure 1: {what the reader should see in it}*

### {Subsection if needed}

## Results
<!-- Main claims and the numbers behind them, not an exhaustive table dump -->

![[{paper}-fig2.png]]
*{Interpretive caption}*

## Limitations & Open Questions
<!-- Critical but fair. What would have to be true for the claims to hold? -->
-
-

## Why this matters for my work   <!-- required -->
<!-- The section that justifies the note existing. Which vault threads does this
     change, and how? Name the notes and be concrete about what becomes
     measurable, testable, or wrong. -->

## Related Notes   <!-- required -->
<!-- Each link with a reason, not a bare title -->
- [[{note}]] — {why it connects}
- [[{map_note}]] — Map

## Research Ideas   <!-- required -->

### Idea 1: {title}
#research_idea #research_idea_by_claude
{Description}

### Idea 2: {title}
#research_idea #research_idea_by_claude
{Description}

# Next context   <!-- required -->
```dataview
LIST
WHERE contains(prev_context, this.file.link)
```
# Map   <!-- required -->
```dataview
List FROM #Map 
WHERE contains(file.outlinks, this.file.link) 
```
```

## Section Guidelines

### TL;DR
- 2-4 sentences answering: what, how, why it matters
- Accessible to someone outside the specific subfield
- Lead with the paper's actual move, not its topic ("gives memorization a unit: bits" beats "studies memorization in LLMs")

### Key Contributions
- 3-5 bullets, technical and empirical
- Each one should be something prior work didn't have
- Put the headline number in here if there is one

### Method Overview
- Start with the single conceptual move the paper rests on — most papers have exactly one
- Include the main method/architecture figure
- Equations only when the claim can't be stated without them; write them in `$...$` / `$$...$$`
- Record the experimental setup (scale, data, precision, seeds) — it's what makes results comparable later

### Results
- Main claims and their evidence; skip exhaustive tables
- Note surprising or counterintuitive findings explicitly
- Include ablation insights when they change the interpretation

### Limitations & Open Questions
- Be critical but fair; attack the argument, not the paper
- Name the assumptions that carry the most weight, especially approximations the authors introduce for tractability
- Flag claims whose scope is narrower than the abstract implies (average-case vs worst-case, one attack vs all attacks, lower bound vs measurement)
- End with the question the paper leaves open that you'd most want answered

### Why this matters for my work
- The differentiator. Without it the note is a better-formatted abstract.
- Name specific vault notes and say what changes: a claim becomes measurable, an argument gains evidence, a planned experiment gains a baseline, an assumption turns out to be wrong
- Prefer active threads over dormant ones
- If genuinely nothing connects, say so in one honest line rather than manufacturing a link

### Related Notes
- Concept notes, related paper summaries, relevant research ideas, Map notes
- One clause per link explaining the relationship
- Verify every wikilink resolves before finishing
- Never use `[[note|alias]]` inside tables — the pipe breaks the column separator

### Research Ideas
- 3-4 concrete directions, each tagged `#research_idea #research_idea_by_claude`
- The good ones cross the paper with something already in the vault
- Each should name what would be measured or built, and what would falsify it or what it costs
- Reference the specific vault note being extended

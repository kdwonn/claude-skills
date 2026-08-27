---
name: asd-ste100
description: Write technical prose with the structural rules of ASD-STE100 Simplified Technical English — short sentences, active voice, simple tenses, one instruction per sentence, and no noun cluster longer than three words. Use this whenever you draft or revise text the user will read again later: notes, experiment reports, READMEs, design docs, docstrings, runbooks, and commit bodies. Also use it when the user gives you existing prose and asks to simplify, tighten, clarify, shorten, de-jargon, or "make this readable". Trigger it even when the user never says "STE", "Simplified Technical English", or "plain English" — "write up my notes on X", "add a README for this repo", or "clean this paragraph up" is enough. It constrains sentence structure only, not vocabulary, so domain terms such as embedding, checkpoint, and gradient stay as they are. Do not use it for conversational replies, creative writing, or prompt engineering.
---

# ASD-STE100 structural writing

ASD-STE100 is the controlled English that aerospace maintenance manuals use. Its purpose is narrow and useful: remove the ambiguity that comes from **sentence structure**. The reader then parses the sentence the way you meant it — whether that reader is tired, non-native, or you in six months.

This skill applies the structural half of the standard. It does not apply the controlled dictionary.

## Scope: structure, not vocabulary

The full standard also restricts writers to about 900 approved words. That layer is deliberately **off** here.

Technical vocabulary is not the source of ambiguity in the user's writing. `checkpoint`, `embedding`, `gradient`, `collapse`, and `logit` each have one precise meaning. A plainer synonym would be *less* clear. ASD-STE100 anticipates this: it permits Technical Names and Technical Verbs outside the dictionary for exactly this reason.

So: never replace a domain term with a simpler word. Change how sentences are built, not what they are about.

The one vocabulary-adjacent rule worth keeping is **consistency**: use the same word for the same thing every time. If it is a "run" in one sentence, do not call it a "job" in the next. Elegant variation makes the reader stop and ask whether you mean two different things.

## Classify the register first

This is the highest-leverage step, and it is the one that is easy to skip. Every block of prose is one of two kinds, and they follow different rules:

| | **Procedural** | **Descriptive** |
|---|---|---|
| Content | steps the reader performs | what a thing is, what happened, what it means |
| Voice | imperative | simple present or simple past |
| Max words per sentence | 20 | 25 |
| Instructions per sentence | exactly one | not applicable |

Map the artifact to the register:

- **Note** → descriptive. Sometimes a trailing "what to do next" list is procedural.
- **Experiment report** → descriptive throughout. Setup, Results, and Interpretation are all descriptive, even though Setup describes commands that were run. Only "Next steps" turns procedural.
- **README** → mixed, and this is where the classification pays off. The overview, the "what is this", and the architecture notes are descriptive. Installation, usage, build, and contributing steps are procedural.

The most common failure is writing procedural content in descriptive voice: *"The user should then run the migration script"* instead of *"Run the migration script."* The imperative version is shorter, it names the action first, and it removes the question of who is supposed to act.

## The rules

### Sentences

**Keep sentences at or under the limit for the register** (20 procedural / 25 descriptive). The limit is a proxy for how much structure a reader holds at once. When a sentence runs long, it almost always contains two claims — split it at the seam rather than compressing it.

**Write one topic per paragraph, and no more than six sentences.** A seventh sentence is a signal that the paragraph changed subject somewhere in the middle.

**Write one instruction per sentence.** Two actions in one sentence hide the order and let the reader do only the first.

> `pip install -e . and then set WANDB_API_KEY before you run the sweep`
> → Install the package with `pip install -e .`. Set `WANDB_API_KEY`. Run the sweep.

**Keep the relative pronoun.** `that`, `which`, and `who` cost two words and mark the clause boundary, which is the thing the reader is otherwise forced to guess.

> `The checkpoint we loaded was stale.` → `The checkpoint that we loaded was stale.`

**Use a vertical list** when a sentence carries three or more coordinate items, conditions, or steps. A list makes the parallel structure visible; a comma-separated run does not.

### Verbs

Use only these forms: **infinitive, imperative, simple present, simple past, simple future, and the past participle as an adjective.** Everything else stacks auxiliaries, and each auxiliary pushes the main verb further from its subject.

**No auxiliary chains.** `had been decreasing` → `decreased`.

**No present perfect.** The present perfect blurs whether something is finished. Say when it happened instead.

> `The loss has plateaued.` → `The loss plateaued at step 30k.` or `The loss is flat.`

**Use the `-ing` form only inside a technical name** — `training loop`, `learning rate`, `logging code`, `masking strategy`. Do not use it as a gerund subject or as a progressive tense, because a gerund subject hides who acted.

> `Increasing the SIGReg weight caused collapse.`
> → `The higher SIGReg weight caused collapse.`
> → or: `We increased the SIGReg weight. The model then collapsed.`

**Use the active voice.** Passive is acceptable in descriptive text when the actor is genuinely unknown or irrelevant — `The checkpoint was corrupted.` is fine. It is not acceptable when it hides an actor the reader needs.

> `The sweep was launched with four seeds.` → `We launched the sweep with four seeds.`

### Noun phrases

**No more than three words in a noun cluster.** Past three, the reader has to guess which noun modifies which, and there is no punctuation to help. Break the cluster with a preposition, or hyphenate the modifier.

> `action loss ablation sweep results`
> → `results of the action-loss ablation sweep`

**Keep the articles.** Notes drop articles first, and that is a false economy. `the` costs three characters and tells the reader this noun is one you already introduced.

> `Run diverged at step 4000.` → `The run diverged at step 4000.`

**Do not drop words to save space.** Telegraphic notes are fast to write and slow to read. Write the verb.

> `sigreg 0.09 — collapse, worse than 0.05`
> → `At sigreg=0.09 the model collapsed. This is worse than sigreg=0.05.`

### Warnings

Put a warning or a caution **before** the step it applies to, not after, and start it with a command. A warning after the fact is a warning the reader meets too late.

> Run `make deploy` to push to prod. Note that this is irreversible.
> → **Warning: this step is irreversible.** Back up the database. Then run `make deploy`.

## What to leave alone

STE governs the prose you write. It does not govern strings the system produced or identifiers the reader will copy. Do not rewrite:

- code fences, inline code, commands, flags, file paths, environment variables
- **metric and config key names**, exactly as they appear in the logging code. Rewriting `val/action_loss` into "the validation action loss" breaks the reader's path back to the source
- quoted material: commit messages, log lines, error text, and the user's own words when you quote them
- math, equations, and symbols
- frontmatter, tables of numbers, links, wikilinks, and URLs
- proper nouns, library names, and model names

## Check the word counts with the script

Counting words per sentence by eye is unreliable, and a 26-word sentence looks exactly like a 24-word one. Run the checker instead:

```bash
python ~/.claude/skills/asd-ste100/scripts/ste_check.py FILE.md
python ~/.claude/skills/asd-ste100/scripts/ste_check.py FILE.md --register procedural
python ~/.claude/skills/asd-ste100/scripts/ste_check.py FILE.md --quiet   # counts only
```

It is markdown-aware: it skips code fences, inline code, frontmatter, tables, links, and math, and it auto-detects the register per section from the heading.

**The script reports candidates, not verdicts.** The word counts and paragraph counts are exact and worth fixing. The passive, gerund, and noun-cluster checks are heuristics that do not know what a technical name is, so read each hit and decide. Silencing a real hit by rephrasing around the checker is worse than leaving it.

## Workflow

### Drafting new text

1. Decide the register for each section before writing.
2. Write.
3. Run the checker.
4. Fix the real hits. Split long sentences at the seam between the two claims rather than deleting words.

### Rewriting text the user gave you

1. **Read the whole thing first.** Sentence-by-sentence rewriting drops the dependencies that run between sentences, and those are exactly what a reader needs.
2. **Preserve every fact, number, caveat, hedge, and negation.** A simplification that loses a caveat is a bug, not a style improvement. If a sentence is long because it is genuinely conditional, keep the condition and split the sentence around it.
3. Run the checker before and after so the improvement is a number, not a claim.
4. Return the rewritten text, ready to use.

**Return the rewritten text by itself.** A before/after table doubles the reading burden for a document the user already knows.

Add a short "what changed" note in two cases only. The first: the user asked for a review rather than a rewrite. The second: you made a judgment call that touched meaning. This happens when splitting a sentence forces an implication to become explicit, and you must pick the intended reading. Say so in one line, and name the reading you chose.

If a sentence resists the rules because the underlying idea is genuinely complex, leave it long and say why. The rules serve the reader; a mangled 19-word sentence is worse than a clear 28-word one.

## Composing with other skills

**`experiment-report`** owns the report: which sections exist, the frontmatter, the vault conventions, where the file goes. This skill owns the prose inside those sections. Both apply at once, and they agree — `experiment-report` asks for terse and bullet-heavy, which is what these rules produce.

Where they can pull apart is terseness. If terseness tempts you to drop an article, drop a relative pronoun, or write a bullet with no verb, these rules win. Those words cost a few characters and save the reader a second pass.

**`fable-prompt`** is not this skill's territory. Prompts are not technical documentation, and prompt writing has its own conventions.

## Reference files

- [references/rules.md](references/rules.md) — the full structural rule inventory, organized by the standard's nine sections, with more examples per rule. Read it when a construction is not covered above, or when you need to explain to the user why something is a violation.
- [references/examples.md](references/examples.md) — three worked before/after passages: a note, an experiment report section, and a README. Read one before rewriting a whole document of that kind, since a transformed passage teaches the register better than the atomic rules do.

This skill encodes the structural rules in its own words. It does not reproduce ASD-STE100's rule text, its numbering, or its dictionary. The specification is free at <https://www.asd-ste100.org/>; get it if you need the dictionary or an exact citation.

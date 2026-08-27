# Structural rule inventory

The structural rules of ASD-STE100, in this skill's own words, organized by the standard's nine sections. The vocabulary layer (the ~900-word controlled dictionary) is deliberately omitted — see the scope note in SKILL.md.

This file does not reproduce ASD's rule text or numbering. Get the free specification at <https://www.asd-ste100.org/> if you need an exact citation or the dictionary.

**Contents**

1. [Words](#1-words) · 2. [Noun phrases](#2-noun-phrases) · 3. [Verbs](#3-verbs) · 4. [Sentences](#4-sentences) · 5. [Procedures](#5-procedures) · 6. [Descriptive writing](#6-descriptive-writing) · 7. [Safety instructions](#7-safety-instructions) · 8. [Punctuation and word counts](#8-punctuation-and-word-counts) · 9. [Writing practices](#9-writing-practices)

---

## 1. Words

Most of this section governs vocabulary and is out of scope here. Three parts are structural and do apply.

**Use one word for one thing, consistently.** Pick a term and keep it for the whole document. Variation makes the reader ask whether you mean something new.

> A run failed. The job was retried. That execution then diverged.
> → A run failed. We retried the run. The run then diverged.

**Technical Names are allowed and should not be simplified.** A Technical Name is a noun that names a thing in the domain: `checkpoint`, `embedding`, `logit`, `optimizer state`, `attention head`. The standard permits these precisely because a plainer synonym would be less exact.

**Technical Verbs are allowed too.** A Technical Verb names a domain action: *to quantize*, *to backpropagate*, *to shard*, *to fine-tune*. Keep them.

**Do not use one word as two parts of speech in the same document** when it causes real ambiguity. `train` as both noun and verb inside one paragraph is worth rewording.

---

## 2. Noun phrases

**Do not write a noun cluster longer than three words.** Beyond three, nothing tells the reader which noun modifies which, and English gives no punctuation to help.

> per-token action loss ablation sweep results
> → results of the per-token action-loss ablation sweep

Two repair moves, in order of preference:

1. Break with a preposition (`of`, `for`, `in`, `from`).
2. Hyphenate the words that form a single modifier, which reduces the effective count: `action-loss ablation sweep` is three units, not four.

**Keep articles.** `the`, `a`, and `an` mark whether a noun is new or already known. Dropping them is the first economy notes make and the one that costs the reader most.

> Run diverged at step 4000. Checkpoint was stale.
> → The run diverged at step 4000. The checkpoint was stale.

**Do not drop words to compress.** Write the verb and the subject. A telegraphic note is fast to write and slow to read.

> sigreg 0.09 — collapse, worse than 0.05
> → At sigreg=0.09 the model collapsed. This result is worse than sigreg=0.05.

**Use hyphens in compound modifiers before a noun.** `a two-stage pipeline`, `an off-policy correction`, `the 8-bit path`.

---

## 3. Verbs

**Use only these forms:** infinitive, imperative, simple present, simple past, simple future, and the past participle used as an adjective. Every other construction stacks auxiliaries between the subject and the action.

| Avoid | Use |
|---|---|
| has plateaued | plateaued *(or: is flat)* |
| had been decreasing | decreased |
| will have converged | converges by step N |
| is being trained | trains *(or: we train it)* |
| would have failed | fails *(state the condition)* |

**Do not use the present perfect.** It hides whether something finished. Give the time instead: `The loss plateaued at step 30k.`

**Use the `-ing` form only inside a technical name.** `training loop`, `learning rate`, `masking strategy`, `logging code` are fine — the `-ing` word modifies a following noun. A gerund as a subject is not fine, because it deletes the actor.

> Increasing the SIGReg weight caused collapse.
> → The higher SIGReg weight caused collapse.
> → or: We increased the SIGReg weight. The model then collapsed.

**Use the past participle as an adjective, not as half of a tense.** `the corrupted checkpoint` is fine. `the checkpoint has been corrupted` is not.

**Use the active voice.** The passive is acceptable in descriptive text only when the actor is genuinely unknown or irrelevant.

> The sweep was launched with four seeds. → We launched the sweep with four seeds.
> The checkpoint was corrupted. → acceptable; nobody corrupted it on purpose.

A useful test: if you can append "by us" or "by the script" and it reads naturally, name that actor instead.

---

## 4. Sentences

**Keep a descriptive sentence at 25 words or fewer. Keep a procedural sentence at 20 or fewer.** When a sentence exceeds the limit, look for the seam — it almost always joins two claims. Split there rather than deleting words, because deleting words is how caveats get lost.

**Write one topic per paragraph.** A paragraph should survive a one-line summary. If it needs two, it is two paragraphs.

**Write no more than six sentences in a paragraph.**

**Keep the relative pronoun.** `that`, `which`, `who`, and `whom` mark where a clause begins. They cost two words and save a re-read.

> The checkpoint we loaded was stale.
> → The checkpoint that we loaded was stale.

**Keep `that` after a reporting verb**, for the same reason.

> We found the metric was mislogged. → We found that the metric was mislogged.

**Use a vertical list** when a sentence carries three or more coordinate items, conditions, or steps. A list shows the parallel structure; commas do not.

**Put the main clause first** when a sentence has a condition. The reader then knows what the sentence is about before they process the qualifier — unless the condition determines whether to read on at all, in which case put it first.

**Do not start a sentence with a pronoun whose referent is more than one sentence away.** Repeat the noun.

---

## 5. Procedures

**Write one instruction per sentence.** Two actions in one sentence hide the order, and readers routinely perform only the first.

> Clone the repo and install the dependencies and configure your environment.
> → 1. Clone the repository. 2. Install the dependencies. 3. Configure your environment.

**Use the imperative.** Name the action first. Do not route the instruction through the reader as a subject.

> The user should then run the migration script.
> → Run the migration script.

**Use a numbered list when order matters** and a bulleted list when it does not. This is information the reader would otherwise have to infer.

**State the condition before the action.** The reader needs to know whether the step applies before they do it.

> Run `make clean` if the build fails.
> → If the build fails, run `make clean`.

**Give one result per step where a result is checkable.** `Run make test. All 42 tests pass.`

---

## 6. Descriptive writing

**Descriptive text gets 25 words per sentence** and covers what a thing is, what happened, and what it means. Notes and experiment reports are descriptive nearly throughout.

**Use the simple past for what happened and the simple present for what is true.**

> The run diverged at step 4000. *(what happened)*
> The optimizer uses AdamW. *(what is true)*

**Keep paragraphs to one topic and six sentences.**

**Put the conclusion first.** A TL;DR, a topic sentence, or a lead finding lets the reader stop early. Technical readers scan; reward that.

**Be explicit about negative and null results.** Hedged phrasing ("results were somewhat inconclusive") costs the reader a re-read and usually means the writer did not want to say it plainly. Say what did not work.

---

## 7. Safety instructions

Aerospace safety rules map onto anything destructive, expensive, or irreversible: `rm -rf`, force pushes, production deploys, database migrations, jobs that burn a GPU budget.

**Put the warning before the step**, never after. A warning that follows the step arrives too late to be a warning.

**Start a warning with a command**, so the required action is the first thing read.

> Note that this operation cannot be undone.
> → **Warning: this step is irreversible.** Back up the database before you continue.

**State the consequence, then the avoidance.** The reader needs to know what is at stake and what to do about it.

**Keep warnings visually distinct** — a callout, a bold label, a blockquote. Do not bury one mid-paragraph.

---

## 8. Punctuation and word counts

**Use the full stop as the default.** Two short sentences beat one sentence with a semicolon.

**Avoid the parenthetical aside that carries load-bearing information.** If it matters, it is a sentence. If it does not, delete it.

**Do not use the slash to mean "and/or".** State which one you mean.

> Set the learning rate/schedule. → Set the learning rate. Set the schedule.

**Avoid the em dash for a clause that could be a sentence.** It is a comfortable habit that pushes sentences past the limit.

**Spell out what an abbreviation means on first use**, then use it consistently.

**Write numbers as digits** for quantities, versions, and measurements. Give units.

---

## 9. Writing practices

**Do not use a pronoun when the noun is short.** `it` and `this` at the start of a sentence are the most common sources of ambiguity in notes.

> This means the sweep is invalid.
> → The seed mismatch means the sweep is invalid.

**Do not use jargon for the sake of register.** Domain terms are required; management vocabulary is not. `leverage` → `use`, `utilize` → `use`, `in order to` → `to`.

**Do not stack qualifiers.** `might potentially somewhat improve` states nothing. Pick one hedge or drop it.

**Do not write a sentence whose only content is that a section exists.** "This section describes the setup." Delete it; the heading did that job.

**Make lists parallel.** Every item takes the same grammatical shape — all noun phrases, or all imperatives, but not a mix.

**Do not nest lists more than two levels deep.** A third level means the structure belongs in a table or a set of headings.

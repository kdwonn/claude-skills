#!/usr/bin/env python3
"""Mechanical checks for the structural rules of ASD-STE100.

Reports candidate violations with line numbers. Word counts and paragraph
counts are exact; the passive, gerund, and noun-cluster checks are heuristics
that cannot tell a technical name from a gerund, so read each hit and decide.

Standard library only. Usage:

    python ste_check.py FILE.md [FILE2.md ...]
    python ste_check.py FILE.md --register procedural
    python ste_check.py FILE.md --quiet
"""

import argparse
import re
import sys

MAX_WORDS = {"procedural": 20, "descriptive": 25}
MAX_SENTENCES_PER_PARAGRAPH = 6
MAX_NOUN_CLUSTER = 3

# Headings that mean the section below them tells the reader what to do.
PROCEDURAL_HEADING = re.compile(
    r"\b(install|installation|setup|set up|getting started|quick ?start|usage|"
    r"how to|build|deploy|run(ning)?|contribut|develop|test(ing)?|migrat|"
    r"upgrade|troubleshoot|next steps?|todo|procedure|steps?|recipe|workflow)\b",
    re.I,
)

BE_FORMS = {"is", "are", "was", "were", "be", "been", "being", "am", "'s", "'re"}
PERFECT_AUX = {"has", "have", "had"}
MODALS = {"will", "would", "shall", "should", "can", "could", "may", "might", "must"}

# Irregular past participles that do not end in -ed.
IRREGULAR_PP = {
    "been", "begun", "broken", "brought", "built", "chosen", "come", "done",
    "driven", "drawn", "eaten", "fallen", "felt", "found", "forgotten", "given",
    "gone", "grown", "held", "hidden", "kept", "known", "laid", "led", "left",
    "lost", "made", "meant", "met", "paid", "put", "read", "run", "said", "seen",
    "sent", "set", "shown", "shut", "sold", "spent", "split", "spread", "taken",
    "taught", "told", "thrown", "understood", "written", "cut", "hit", "let",
    "beaten", "bound", "burnt", "caught", "dealt", "drunk", "fed", "fit",
    "frozen", "hung", "heard", "risen", "sat", "slept", "spoken", "stood",
    "stuck", "struck", "swum", "torn", "won", "woken", "worn",
}

# -ing words that are ordinary technical names, not gerunds. Not exhaustive;
# the check is advisory and these only cut the loudest false positives.
TECHNICAL_ING = {
    "training", "learning", "logging", "masking", "encoding", "decoding",
    "embedding", "embeddings", "scaling", "sampling", "batching", "caching",
    "clipping", "warming", "annealing", "pooling", "padding", "tokenizing",
    "profiling", "checkpointing", "engineering", "monitoring", "scheduling",
    "preprocessing", "postprocessing", "fine-tuning", "pretraining", "tuning",
    "setting", "settings", "string", "thing", "something", "nothing",
    "everything", "anything", "during", "ring", "spring", "wing", "bring",
    "sing", "king", "building", "meaning", "warning", "beginning", "missing",
    "remaining", "following", "existing", "corresponding", "underlying",
    "resulting", "working", "running", "grounding", "reasoning", "planning",
    "rendering", "streaming", "batching", "routing", "hashing", "indexing",
    "gating", "pruning", "quantizing", "denoising", "conditioning", "weighting",
}

# Words that cannot be part of a noun cluster; they break the run.
FUNCTION_WORDS = {
    "a", "an", "the", "and", "or", "but", "nor", "for", "so", "yet", "of", "in",
    "on", "at", "to", "from", "by", "with", "without", "into", "onto", "over",
    "under", "between", "through", "during", "before", "after", "above",
    "below", "up", "down", "out", "off", "about", "against", "per", "via",
    "is", "are", "was", "were", "be", "been", "being", "am", "has", "have",
    "had", "do", "does", "did", "will", "would", "shall", "should", "can",
    "could", "may", "might", "must", "not", "no", "if", "then", "than", "that",
    "which", "who", "whom", "whose", "when", "where", "why", "how", "this",
    "these", "those", "it", "its", "we", "our", "you", "your", "they", "their",
    "he", "she", "his", "her", "i", "my", "me", "us", "them", "him", "as",
    "each", "every", "any", "all", "some", "both", "more", "most", "less",
    "least", "very", "only", "also", "just", "still", "such", "same", "other",
    "there", "here", "because", "while", "since", "although", "though", "once",
    "whether", "never", "always", "often", "inside", "outside", "within",
    "across", "along", "among", "toward", "towards", "upon", "unless", "until",
    "whereas", "however", "instead", "rather", "either", "neither", "many",
    "much", "few", "several", "own", "new", "old", "next", "last", "first",
}

# A word after one of these is doing gerund work, whatever else it may be.
GERUND_TRIGGERS = {
    "by", "after", "before", "when", "while", "without", "for", "of", "on",
    "in", "avoid", "start", "stop", "begin", "consider", "try", "keep",
}

# Common imperatives in technical documentation. Used only to spot a sentence
# that carries more than one instruction.
IMPERATIVES = {
    "run", "install", "set", "clone", "configure", "add", "remove", "open",
    "edit", "create", "delete", "check", "verify", "start", "stop", "restart",
    "build", "deploy", "copy", "move", "download", "upload", "enable",
    "disable", "export", "import", "save", "load", "launch", "apply", "push",
    "pull", "commit", "merge", "update", "upgrade", "select", "click", "press",
    "type", "enter", "navigate", "replace", "rename", "extract", "unzip",
    "activate", "deactivate", "source", "define", "register", "connect",
    "disconnect", "mount", "unmount", "flash", "reboot", "wait", "confirm",
    "review", "rerun", "retry", "invoke", "call", "execute", "generate",
}

# Verbs that commonly sit mid-sentence and therefore end a noun cluster.
COMMON_VERBS = {
    "use", "make", "get", "give", "take", "find", "look", "need", "want",
    "show", "mean", "keep", "hold", "mirror", "appear", "encode", "span",
    "treat", "fill", "capture", "gather", "list", "inspect", "answer",
    "contain", "include", "require", "produce", "return", "report", "write",
    "read", "work", "help", "allow", "cause", "reach", "drop", "stay", "come",
    "go", "see", "know", "think", "say", "prefer", "skip", "note", "match",
    "follow", "point", "seem", "become", "remain", "happen", "occur", "differ",
    "vary", "depend", "consist", "refer", "describe", "explain", "indicate",
    "suggest", "assume", "expect", "compare", "measure", "count", "split",
    "join", "map", "trace", "log", "track", "store", "fetch", "parse",
    "resolve", "reconstruct", "confirm", "identify", "flag", "hide", "bury",
    "restate", "pull", "grep", "sample", "compute", "plot", "embed", "quote",
    "fabricate", "touch", "obey", "encode", "let", "put", "lose", "kill",
    "was", "were", "got", "made", "said", "went", "came", "saw", "took",
    "train", "trains", "eval", "evaluate", "predict", "infer", "encode",
    "decode", "sweep", "tune", "fit", "converge", "diverge", "collapse",
    "improve", "degrade", "regress", "outperform", "beat", "exceed", "fall",
    "rise", "hold", "scale", "batch", "cache", "shard", "prune", "quantize",
    "contract", "expand", "shrink", "grow", "swing", "compound", "commit",
    "tie", "ties", "beats", "stays", "runs", "acts", "carries", "needs",
}


class Finding:
    def __init__(self, line, rule, detail, text):
        self.line = line
        self.rule = rule
        self.detail = detail
        self.text = text


# --------------------------------------------------------------------------
# Markdown stripping
# --------------------------------------------------------------------------

def scrub_inline(text):
    """Blank out spans that STE does not govern, keeping character offsets."""
    def blank(m):
        return " " * len(m.group(0))

    text = re.sub(r"`[^`\n]*`", blank, text)          # inline code
    text = re.sub(r"\$\$?[^$\n]*\$\$?", blank, text)  # math
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", blank, text)  # images
    text = re.sub(r"\[\[[^\]]*\]\]", blank, text)     # wikilinks
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", lambda m: m.group(1).ljust(len(m.group(0))), text)
    text = re.sub(r"<https?://[^>\s]+>", blank, text)
    text = re.sub(r"https?://\S+", blank, text)
    text = re.sub(r"<!--.*?-->", blank, text)
    text = re.sub(r"</?[a-zA-Z][^>]*>", blank, text)  # html tags
    return text


def parse_blocks(lines, forced_register=None):
    """Yield (kind, register, start_line, [(lineno, text), ...]) blocks.

    kind is 'para' for prose paragraphs or 'item' for list items and table-free
    single lines. Code fences, frontmatter, and tables are dropped entirely.
    """
    blocks = []
    register = forced_register or "descriptive"
    in_fence = False
    fence_tok = None
    i = 0
    n = len(lines)

    # YAML frontmatter
    if n and lines[0].strip() == "---":
        for j in range(1, n):
            if lines[j].strip() in ("---", "..."):
                i = j + 1
                break

    buf = []
    buf_kind = "para"

    def flush():
        if buf:
            blocks.append((buf_kind, register, buf[0][0], list(buf)))
            buf.clear()

    while i < n:
        raw = lines[i]
        stripped = raw.strip()

        fence = re.match(r"^\s*(```+|~~~+)", raw)
        if fence:
            tok = fence.group(1)[:3]
            if not in_fence:
                flush()
                in_fence, fence_tok = True, tok
            elif tok == fence_tok:
                in_fence = False
            i += 1
            continue
        if in_fence:
            i += 1
            continue

        if not stripped:
            flush()
            i += 1
            continue

        # Headings switch register and never get checked themselves.
        h = re.match(r"^\s{0,3}#{1,6}\s+(.*)$", raw)
        if h:
            flush()
            if not forced_register:
                register = "procedural" if PROCEDURAL_HEADING.search(h.group(1)) else "descriptive"
            i += 1
            continue

        # Tables, horizontal rules, indented code, reference definitions.
        if "|" in stripped and re.match(r"^\s*\|?[\s:|-]+\|", stripped):
            flush()
            i += 1
            continue
        if stripped.startswith("|") or re.match(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$", stripped):
            flush()
            i += 1
            continue
        if re.match(r"^ {4,}\S", raw) and buf_kind != "para":
            i += 1
            continue

        # List items and numbered steps are their own units.
        li = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", raw)
        if li:
            flush()
            buf_kind = "item"
            body = li.group(3)
            if not forced_register and re.match(r"^\s*\d+[.)]", raw):
                pass  # numbered lists are often procedural, but the heading rules
            buf.append((i + 1, body))
            # absorb the item's continuation lines
            j = i + 1
            while j < n and lines[j].strip() and not re.match(r"^(\s*)([-*+]|\d+[.)])\s+", lines[j]) \
                    and not re.match(r"^\s{0,3}#{1,6}\s+", lines[j]):
                buf.append((j + 1, lines[j].strip()))
                j += 1
            flush()
            buf_kind = "para"
            i = j
            continue

        body = stripped
        if body.startswith(">"):
            body = body.lstrip("> ").strip()
            if not body:
                i += 1
                continue
        buf_kind = "para"
        buf.append((i + 1, body))
        i += 1

    flush()
    return blocks


# --------------------------------------------------------------------------
# Sentence handling
# --------------------------------------------------------------------------

ABBREV = r"(?<!\be\.g)(?<!\bi\.e)(?<!\bvs)(?<!\betc)(?<!\bFig)(?<!\bNo)(?<!\bcf)(?<!\bal)"
# Emphasis markers may sit between the full stop and the next capital
# ("...limit.** A seventh sentence..."), so allow them on both sides.
SENT_SPLIT = re.compile(ABBREV + r"(?<=[.!?])[\"')\]*_]*\s+(?=[\"'(\[*_]*[A-Z])")


def split_sentences(text):
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = SENT_SPLIT.split(text)
    return [p.strip() for p in parts if p.strip()]


def words_of(sentence):
    """Countable words: drop bare punctuation and numeric-only tokens stay."""
    toks = re.findall(r"[A-Za-z0-9][A-Za-z0-9''./_-]*", sentence)
    return [t for t in toks if re.search(r"[A-Za-z0-9]", t)]


def is_past_participle(word):
    w = word.lower().strip(".,;:")
    return w in IRREGULAR_PP or (w.endswith("ed") and len(w) > 4)


# Punctuation always ends a noun cluster; so does any word that is doing verb
# work. Without a part-of-speech tagger this cannot be exact, which is why the
# check is advisory.
CLUSTER_BREAK = re.compile(r"[^A-Za-z-]+")


def breaks_cluster(word):
    w = word.lower().strip("-")
    if w in FUNCTION_WORDS or w in COMMON_VERBS or w in IMPERATIVES:
        return True
    if w.endswith("ly") or w.endswith("ed"):
        return True
    # Third-person singular verbs ("holds", "encodes"): a plural noun is also
    # possible, so only break on ones that are not obviously plural nouns.
    if w.endswith("s") and w[:-1] in COMMON_VERBS | IMPERATIVES:
        return True
    return len(w) < 2


def noun_clusters(sentence):
    """Return maximal runs of more than MAX_NOUN_CLUSTER consecutive nouns."""
    out = []
    run = []
    for token in re.findall(r"[A-Za-z][A-Za-z-]*|[^A-Za-z\s]+|\s+", sentence):
        if token.isspace():
            continue
        if not re.match(r"^[A-Za-z]", token) or breaks_cluster(token):
            if len(run) > MAX_NOUN_CLUSTER:
                out.append(" ".join(run))
            run = []
        else:
            run.append(token)
    if len(run) > MAX_NOUN_CLUSTER:
        out.append(" ".join(run))
    return out


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

def check_sentence(sentence, register, line, findings):
    words = words_of(sentence)
    limit = MAX_WORDS[register]
    if len(words) > limit:
        findings.append(Finding(
            line, "LONG-SENTENCE",
            f"{len(words)} words (limit {limit} for {register})", sentence))

    lower = [w.lower().strip(".,;:") for w in words]

    # Passive voice: be-form followed by a past participle within two tokens.
    for idx, w in enumerate(lower):
        if w in BE_FORMS:
            for nxt in lower[idx + 1: idx + 3]:
                if is_past_participle(nxt):
                    findings.append(Finding(
                        line, "PASSIVE",
                        f'"{w} {nxt}" — name the actor, or confirm it is unknown',
                        sentence))
                    break

    # Complex tense: perfect auxiliaries and modal + have stacks.
    for idx, w in enumerate(lower):
        if w in PERFECT_AUX and idx + 1 < len(lower):
            nxt = lower[idx + 1]
            if nxt == "been" or is_past_participle(nxt):
                findings.append(Finding(
                    line, "COMPLEX-TENSE",
                    f'"{w} {nxt}" — use the simple past instead', sentence))
        if w in MODALS and idx + 1 < len(lower) and lower[idx + 1] in PERFECT_AUX:
            findings.append(Finding(
                line, "COMPLEX-TENSE",
                f'"{w} {lower[idx + 1]}" — use a simple tense', sentence))

    # Gerunds and progressives. A word after a preposition is a gerund even if
    # it is also a common technical name, so test that before the allowlist.
    for idx, w in enumerate(lower):
        if not w.endswith("ing") or len(w) < 5:
            continue
        prev = lower[idx - 1] if idx > 0 else None
        nxt = lower[idx + 1] if idx + 1 < len(lower) else None
        # "training data", "learning rate": a noun follows, so this modifies it.
        modifier = nxt is not None and nxt not in FUNCTION_WORDS
        if prev in BE_FORMS:
            findings.append(Finding(
                line, "PROGRESSIVE",
                f'"{prev} {w}" — use the simple present or simple past', sentence))
        elif modifier:
            continue
        elif prev in GERUND_TRIGGERS or (idx == 0 and w not in TECHNICAL_ING):
            findings.append(Finding(
                line, "GERUND",
                f'"{w}" used as a gerund — name the actor and use a finite verb',
                sentence))

    # One instruction per sentence: two or more imperatives joined by and/then.
    if register == "procedural":
        verbs = [i for i, w in enumerate(lower) if w in IMPERATIVES]
        joiners = [i for i, w in enumerate(lower) if w in ("and", "then", "&&", ";")]
        if len(verbs) >= 2 and any(verbs[0] < j < verbs[-1] for j in joiners):
            findings.append(Finding(
                line, "ONE-INSTRUCTION",
                f'{len(verbs)} actions in one sentence '
                f'({", ".join(lower[i] for i in verbs)}) — split into separate '
                f"sentences or a numbered list", sentence))

    for cluster in noun_clusters(sentence):
        findings.append(Finding(
            line, "NOUN-CLUSTER",
            f'"{cluster}" — {len(cluster.split())} words; break it with a '
            f"preposition or hyphen", sentence))


def check_block(kind, register, block_lines, findings):
    total_sentences = 0
    for lineno, text in block_lines:
        clean = scrub_inline(text)
        for sent in split_sentences(clean):
            if len(words_of(sent)) < 3:
                continue
            total_sentences += 1
            check_sentence(sent, register, lineno, findings)

    if kind == "para" and total_sentences > MAX_SENTENCES_PER_PARAGRAPH:
        findings.append(Finding(
            block_lines[0][0], "LONG-PARAGRAPH",
            f"{total_sentences} sentences (limit {MAX_SENTENCES_PER_PARAGRAPH}); "
            f"the paragraph probably changed topic", ""))


def check_file(path, forced_register=None):
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    findings = []
    for kind, register, _, block_lines in parse_blocks(lines, forced_register):
        check_block(kind, register, block_lines, findings)
    findings.sort(key=lambda f: (f.line, f.rule))
    return findings


# --------------------------------------------------------------------------

EXACT = {"LONG-SENTENCE", "LONG-PARAGRAPH"}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--register", choices=["procedural", "descriptive"],
                    help="force one register instead of detecting it per heading")
    ap.add_argument("--quiet", action="store_true", help="print the summary only")
    ap.add_argument("--only", help="comma-separated rules to show, e.g. LONG-SENTENCE")
    args = ap.parse_args()

    wanted = {r.strip().upper() for r in args.only.split(",")} if args.only else None
    grand = {}

    for path in args.files:
        try:
            findings = check_file(path, args.register)
        except OSError as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            continue
        if wanted:
            findings = [f for f in findings if f.rule in wanted]

        if not args.quiet:
            print(f"\n=== {path} ===")
            if not findings:
                print("  no findings")
            for f in findings:
                mark = "!" if f.rule in EXACT else "?"
                print(f"  {mark} {path}:{f.line}  {f.rule}: {f.detail}")
                if f.text:
                    snippet = f.text if len(f.text) <= 160 else f.text[:157] + "..."
                    print(f"      {snippet}")

        for f in findings:
            grand[f.rule] = grand.get(f.rule, 0) + 1

    print("\n--- summary ---")
    if not grand:
        print("clean")
    else:
        for rule in sorted(grand, key=lambda r: (-grand[r], r)):
            mark = "exact " if rule in EXACT else "advisory"
            print(f"  {grand[rule]:4d}  {rule:<16} ({mark})")
        print("\n! = exact, fix these.  ? = heuristic, read and decide.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

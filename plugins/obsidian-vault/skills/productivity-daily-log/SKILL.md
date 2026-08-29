---
name: productivity-daily-log
description: Create daily log in 4.Timestamps/. Summarizes tasks, Claude Code sessions (local + remote), GitHub commits, vault changes, and Notion activity for a given date. Use when the user wants to create a daily log, end-of-day summary, or document what happened today.
argument-hint: "[YYYY-MM-DD]"
allowed-tools: Read, Grep, Glob, Edit, Skill, Agent, Bash
model: claude-sonnet-4-6
effort: high
---

# Daily Log Command

Create a daily log note summarizing tasks, session activity (local + remote), GitHub commits, vault changes, and Notion activity.

## Usage

```bash
/productivity-daily-log                 # today + previous 3 days (4 days total)
/productivity-daily-log 2026-02-27      # just that date

# installed as a plugin, the command is namespaced:
/obsidian-vault:productivity-daily-log
```

**Default behavior (no date argument):** Process today **and the previous 3 calendar days** (4 days total, oldest first). This keeps recent logs up to date as new sessions, commits, and vault activity accumulate. See "Extended Day" below for how "today" is determined.

**With a date argument:** Process only that single date.

## Extended Day

The user often works past midnight, so the "logical day" extends to 04:00 the next calendar day:

- **Logical day for date D** = `D 04:00` through `D+1 03:59` (local time)
- **Auto-date**: When no date argument is given and the current local time is before 04:00, default to **yesterday** (the user is still in yesterday's logical day)
- **Session inclusion**: A session belongs to date D if its first message timestamp (local) falls within D's logical day window
- **Vault activity**: Files created/modified between 00:00–04:00 on D+1 count as activity for date D
- **Task dates**: Tasks marked completed on D+1's calendar date but before 04:00 count for date D

This means `/productivity-daily-log` run at 02:00 on March 2nd produces the log for March 1st.

## File Path

`4.Timestamps/YYYY-MM/YYYY-MM-DD ddd.md`

- Example: `4.Timestamps/2026-02/2026-02-27 Fri.md`
- Create the month folder (`YYYY-MM/`) if it doesn't exist
- Create `4.Timestamps/` if it doesn't exist

### Computing `ddd` (day-of-week)

**Never guess the weekday from the date.** Always compute it with a shell command and use that literal output in the filename:

```bash
# macOS BSD date
date -j -f "%Y-%m-%d" "2026-02-27" +"%a"   # → Fri
```

Or with Python (portable):

```bash
python3 -c "from datetime import date; print(date(2026,2,27).strftime('%a'))"
```

Do the same for every date being processed (in default multi-day mode, compute `ddd` once per day).

**Reserved naming** (for future use, do not create these):
- `YYYY-MM.md` — monthly summary
- `YYYY-WNN.md` — weekly summary

## Pre-Check

- **Single-date mode** (date argument given): If the daily log file already exists, **ask the user** whether to update it or skip. Do not overwrite without confirmation.
- **Default multi-day mode** (no date argument): Update existing logs in place **without asking** — this mode is designed to run unattended (including via launchd). Preserve any user-authored freeform text (Quick Tasks, manual notes); only refresh auto-generated sections (Sessions, Commits, Vault Activity, Notion Activity).

### Iteration order (default mode)

Process the 4 dates **oldest first** (D-3, D-2, D-1, D). Each day's data-gathering uses that day's logical-day window independently. Create missing month folders as needed.

## Data Gathering

Collect data from these sources before writing:

### 1. Sessions (All Sessions Today)

Summarize ALL Claude Code sessions from the target date — not just the current session.

#### How to gather session data

Run the bundled script to gather all sessions for the target date:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/productivity-daily-log/scripts/gather_sessions.py" \
  ~/.claude/projects/<project-dir>/ YYYY-MM-DD
```

The script outputs a JSON array of session objects, each containing: `file`, `first_prompt`, `message_count`, `start_time` (HH:MM local), `end_time` (HH:MM local), and ISO timestamps.

It handles all the complexity: scanning `.jsonl` transcripts, UTC→local conversion, logical day filtering (D 04:00 – D+1 03:59), skipping sidechains, and excluding short sessions (≤4 messages).

**For the current session**: The script may not capture the latest messages (transcript writes lag). Also reflect on the actual conversation context to supplement the script output.

#### Timezone notes

Session `.jsonl` timestamps are UTC. The script converts to the machine's local timezone for all output (override with the `DAILY_LOG_TZ` environment variable). A session belongs to date D if its first message timestamp (local) falls within D 04:00 – D+1 03:59. Sessions starting between 00:00–03:59 local belong to the previous calendar day.

#### How to present

- List each session as a subsection under "## Sessions"
- Use `### [summary] (HH:MM–HH:MM)` as the heading for each session
- Write a short descriptive summary based on the first prompt and session content
- Write 1-3 substantive bullets per session describing what was accomplished
- Focus on outcomes and decisions, not mechanics
- Sort sessions chronologically by start time

### 2. GitHub Commits

Gather commits authored by the user on the target date across all repos using the GitHub CLI:

```bash
gh search commits --author=@me --committer-date=YYYY-MM-DD --json repository,sha,commit --limit 50
```

This returns commits from all repos. The JSON includes `repository.nameWithOwner`, `sha`, and `commit.message`/`commit.committer.date`.

**Extended day handling**: The `--committer-date` flag filters by calendar date (not logical day). This is acceptable — a small mismatch at the 00:00–04:00 boundary is fine for commits.

#### How to present

- Group commits by repository under "## Commits"
- Link the repo heading: `### [owner/repo](https://github.com/owner/repo)`
- Show each commit as: `- short message ([\`sha7\`](https://github.com/owner/repo/commit/sha7))`
- If a repo has many commits, summarize the theme instead of listing all
- Omit this section entirely if there are no commits

### 3. Remote Sessions (optional)

If the user runs Claude Code on a remote machine as well, gather those sessions over SSH. Transcripts live in the same directory structure as local (`~/.claude/projects/`).

**Skip this step entirely unless the user has named a remote host** — in their `CLAUDE.md`, in the prompt, or in a `DAILY_LOG_REMOTE` environment variable. Below, `$REMOTE` stands for that host's SSH alias.

#### How to gather

**Sandbox note**: SSH and SCP commands require `dangerouslyDisableSandbox: true` on the Bash tool — the sandbox blocks network access to hosts not in the allowlist.

1. Copy the gather script to the remote server and run it across all project directories:

```bash
# Find all project session directories on the remote host
ssh "$REMOTE" 'find ~/.claude/projects -maxdepth 1 -type d' 2>/dev/null
```

2. For each project directory found, run the gather script remotely:

```bash
ssh "$REMOTE" 'python3 -' <project_dir> YYYY-MM-DD < "${CLAUDE_PLUGIN_ROOT}/skills/productivity-daily-log/scripts/gather_sessions.py"
```

Alternatively, scp the script once and run it for each project dir:

```bash
scp "${CLAUDE_PLUGIN_ROOT}/skills/productivity-daily-log/scripts/gather_sessions.py" "$REMOTE:/tmp/gather_sessions.py"
ssh "$REMOTE" 'for d in ~/.claude/projects/*/; do python3 /tmp/gather_sessions.py "$d" YYYY-MM-DD 2>/dev/null; done'
```

The output is the same JSON format as local sessions. Merge these with local sessions.

#### How to present

Remote sessions are merged into the "## Sessions" section alongside local sessions, sorted chronologically. Tag each session heading to indicate its source:

- Local: `### [summary] (HH:MM–HH:MM)`
- Remote: `### [summary] (HH:MM–HH:MM, <host>)`

If SSH fails (timeout, unreachable), skip remote sessions silently and add a note at the bottom: "Note: `<host>` was unreachable; remote sessions not included."

### 4. Notion Activity (Optional)

If Notion MCP is available:
- Pages the user updated today
- New pages created today

If not available, omit this section entirely (don't show an empty section).

### 5. Vault Activity

Use filesystem timestamps to find files within the target date's **logical day** (D 04:00 through D+1 03:59 local):
- **Created today**: Files created during the logical day
- **Modified today**: Files modified during the logical day (exclude the daily log itself)

Focus on `.md` files in the main vault folders (0.Inbox, 1.Projects, 2.Cards, Resource/Papers).

## Template

If an `obsidian-markdown` skill is installed, use it to write the note. Follow these rules:
- No H1 heading (filename is the title)
- Use `#Daily` and `#claude` tags
- Use literal dates in Dataview and Tasks queries (not Templater syntax)
- Follow the vault's note conventions from CLAUDE.md

```markdown
---
created: YYYY-MM-DDTHH:MM:SS
---
#Daily #claude

## Tasks
### Completed today
\`\`\`tasks
done
done YYYY-MM-DD YYYY-MM-DD
path does not include Archive/
path does not include Resource/Templates/
group by folder
\`\`\`

### Created today
\`\`\`tasks
not done
created YYYY-MM-DD YYYY-MM-DD
path does not include Archive/
path does not include Resource/Templates/
group by folder
\`\`\`

### Quick Tasks

## Sessions
### [session summary] (HH:MM–HH:MM)
- [substantive bullet 1]
- [substantive bullet 2]

### [session summary] (HH:MM–HH:MM, remote-host)
- [substantive bullet 1]

## Commits
### [owner/repo-name](https://github.com/owner/repo-name)
- short commit message ([`abc1234`](https://github.com/owner/repo-name/commit/abc1234))
- another commit message ([`def5678`](https://github.com/owner/repo-name/commit/def5678))

### [owner/other-repo](https://github.com/owner/other-repo)
- commit message ([`ghi9012`](https://github.com/owner/other-repo/commit/ghi9012))

## Vault Activity
### Notes created today
\`\`\`dataview
TABLE created
FROM ""
WHERE dateformat(date(created), "yyyy-MM-dd") = "YYYY-MM-DD"
SORT created DESC
\`\`\`

### Notes last touched today
\`\`\`dataview
TABLE file.mtime as "Last Modified"
FROM ""
WHERE dateformat(file.mtime, "yyyy-MM-dd") = "YYYY-MM-DD"
SORT file.mtime DESC
\`\`\`

## Notion Activity
- [pages updated, as list]
```

Replace `YYYY-MM-DD` in the Dataview queries with the literal target date (e.g., `"2026-02-27"`).

## Notes

- If Notion is not connected, omit the "Notion Activity" section entirely
- If there are no GitHub commits, omit the "Commits" section entirely
- If SSH to the remote host fails, skip remote sessions and add a note at the bottom
- Session summaries should reflect genuine work, not just tool calls
- Sessions data comes from `.jsonl` transcript files (not `sessions-index.json`, which is often stale)
- Timestamps in `.jsonl` files are UTC — always convert to local time for display and date filtering
- For the current active session, also use conversation context since the transcript may be incomplete
- Vault activity uses filesystem timestamps, which may include auto-save modifications
- The Dataview queries at the bottom provide a live view that updates as notes change
- Keep the log concise — it's a reference, not a journal

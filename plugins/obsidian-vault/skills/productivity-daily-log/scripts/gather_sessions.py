#!/usr/bin/env python3
"""Gather Claude Code session data for a given date's logical day.

Logical day: D 04:00 local through D+1 03:59 local.

Usage:
    python3 gather_sessions.py <project_session_dir> <YYYY-MM-DD>

Output: JSON array of session objects, sorted by start time.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

# Defaults to the machine's own timezone. Set DAILY_LOG_TZ (e.g. "Europe/Berlin")
# to override -- useful when the transcripts come from a server in another zone.
_tz_name = os.environ.get("DAILY_LOG_TZ")
LOCAL_TZ = ZoneInfo(_tz_name) if _tz_name else datetime.now().astimezone().tzinfo
MIN_MESSAGE_COUNT = 4


def parse_timestamp(ts_str: str) -> datetime:
    """Parse ISO 8601 timestamp (UTC) and convert to local time."""
    ts = ts_str.rstrip("Z")
    if "+" in ts or (ts.count("-") > 2):
        dt = datetime.fromisoformat(ts)
    else:
        dt = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
    return dt.astimezone(LOCAL_TZ)


def extract_first_prompt(content) -> str:
    """Extract text from message content (string or array of blocks)."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))
            elif isinstance(block, str):
                texts.append(block)
        return "\n".join(texts).strip()
    return str(content).strip()


def is_boilerplate(text: str) -> bool:
    """Check if text is a boilerplate/system message, not real user input."""
    prefixes = [
        "[Request interrupted]",
        "<local-command-caveat>",
        "<command-message>",
        "<system-reminder>",
    ]
    stripped = text.strip()
    return any(stripped.startswith(p) for p in prefixes) or len(stripped) < 3


def process_session(jsonl_path: Path, day_start: datetime, day_end: datetime) -> Optional[dict]:
    """Process a single .jsonl transcript file and return session info or None."""
    records = []
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except (OSError, UnicodeDecodeError):
        return None

    if not records:
        return None

    # Check for sidechain
    if any(r.get("isSidechain") for r in records):
        return None

    # Find timestamps and messages
    timestamps = []
    user_count = 0
    assistant_count = 0
    first_prompt = None

    for r in records:
        ts_str = r.get("timestamp")
        if ts_str:
            try:
                timestamps.append(parse_timestamp(ts_str))
            except (ValueError, TypeError):
                pass

        msg_type = r.get("type")
        if msg_type == "user":
            user_count += 1
            if first_prompt is None:
                content = r.get("message", {}).get("content", "")
                text = extract_first_prompt(content)
                if text and not is_boilerplate(text):
                    first_prompt = text
        elif msg_type == "assistant":
            assistant_count += 1

    if not timestamps:
        return None

    start_time = min(timestamps)
    end_time = max(timestamps)

    # Check if session belongs to this logical day (by first message timestamp)
    if start_time < day_start or start_time >= day_end:
        return None

    total_messages = user_count + assistant_count
    if total_messages <= MIN_MESSAGE_COUNT:
        return None

    # Truncate first prompt for summary
    if first_prompt and len(first_prompt) > 300:
        first_prompt = first_prompt[:300] + "..."

    return {
        "file": jsonl_path.name,
        "first_prompt": first_prompt or "(no user prompt found)",
        "message_count": total_messages,
        "user_messages": user_count,
        "assistant_messages": assistant_count,
        "start_time": start_time.strftime("%H:%M"),
        "end_time": end_time.strftime("%H:%M"),
        "start_iso": start_time.isoformat(),
        "end_iso": end_time.isoformat(),
    }


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <project_session_dir> <YYYY-MM-DD>", file=sys.stderr)
        sys.exit(1)

    session_dir = Path(sys.argv[1])
    date_str = sys.argv[2]

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"Invalid date format: {date_str}. Use YYYY-MM-DD.", file=sys.stderr)
        sys.exit(1)

    if not session_dir.is_dir():
        print(f"Directory not found: {session_dir}", file=sys.stderr)
        sys.exit(1)

    # Logical day: D 04:00 local to D+1 03:59 local
    day_start = datetime(target_date.year, target_date.month, target_date.day, 4, 0, 0, tzinfo=LOCAL_TZ)
    day_end = day_start + timedelta(days=1)

    # Find .jsonl files (cast wide net by mtime, filter precisely by content)
    jsonl_files = sorted(session_dir.glob("*.jsonl"))

    sessions = []
    for f in jsonl_files:
        # Quick mtime pre-filter: skip files last modified before the logical day start
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=LOCAL_TZ)
        if mtime < day_start - timedelta(days=1):
            continue

        result = process_session(f, day_start, day_end)
        if result:
            sessions.append(result)

    # Sort by start time
    sessions.sort(key=lambda s: s["start_iso"])

    print(json.dumps(sessions, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

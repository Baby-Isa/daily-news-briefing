#!/usr/bin/env python3
"""Keep the briefing's memory small. daily-run.md, Part B, before committing.

Usage: python3 tools/housekeeping.py [YYYY-MM-DD]

Mechanical pruning, so that no model has to decide it and the memory files
cannot grow. By 20 November 2026 story-threads.md had reached 160 KB and
aired-items.md 107 KB, and the drafter had begun reading them only in part.

1. Copies today's briefing.txt to archive/YYYY-MM-DD.txt and deletes
   archive files older than the limit (a rolling week of what was said).
2. story-threads.md: drops entries whose expiry date has passed, trims any
   entry that has grown too long, keeps at most the newest N.
3. aired-items.md: drops dated entries older than the limit, unless the
   line contains the word KEEP. Keeps only the newest few weather jokes.

Limits are in brief-config.json under "memory".
"""
import datetime
import glob
import json
import os
import re
import shutil
import sys
from zoneinfo import ZoneInfo

MAX_ENTRY_CHARS = 450
THREAD = re.compile(r"^- \[expires (\d{4}-\d{2}-\d{2})\] ")
AIRED = re.compile(r"^- \*\*(\d{4}-\d{2}-\d{2})")
JOKES_HEADING = "## Recent weather jokes"


def main():
    cfg = json.load(open("brief-config.json", encoding="utf-8"))
    mem = cfg["memory"]
    tz = ZoneInfo(cfg.get("timezone", "Europe/London"))
    today = (datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1
             else datetime.datetime.now(tz).date())

    # 1. rolling archive of what was actually said
    os.makedirs("archive", exist_ok=True)
    if os.path.exists("briefing.txt"):
        shutil.copyfile("briefing.txt", f"archive/{today.isoformat()}.txt")
    removed = 0
    for path in glob.glob("archive/*.txt"):
        try:
            day = datetime.date.fromisoformat(os.path.basename(path)[:-4])
        except ValueError:
            continue
        if (today - day).days >= mem["archive_days"]:
            os.remove(path)
            removed += 1
    print(f"archive: {len(glob.glob('archive/*.txt'))} day(s) kept, {removed} removed")

    # 2. story threads
    head, entries, dropped, trimmed = [], [], 0, 0
    for line in open("story-threads.md", encoding="utf-8").read().splitlines():
        m = THREAD.match(line)
        if not m:
            if line.startswith("- ["):
                dropped += 1            # an entry with no valid expiry date
            elif not entries:
                head.append(line)       # the explanatory header
            continue
        if datetime.date.fromisoformat(m.group(1)) < today:
            dropped += 1
            continue
        if len(line) > MAX_ENTRY_CHARS:
            line = line[:MAX_ENTRY_CHARS].rsplit(" ", 1)[0] + "..."
            trimmed += 1
        entries.append(line)
    if len(entries) > mem["max_threads"]:
        dropped += len(entries) - mem["max_threads"]
        entries = entries[:mem["max_threads"]]
    while head and not head[-1].strip():
        head.pop()
    with open("story-threads.md", "w", encoding="utf-8") as f:
        f.write("\n".join(head) + "\n\n" + "\n".join(entries) + "\n")
    print(f"story-threads: {len(entries)} kept, {dropped} dropped, {trimmed} trimmed")

    # 3. aired items
    out, pruned, jokes, in_jokes = [], 0, 0, False
    for line in open("aired-items.md", encoding="utf-8").read().splitlines():
        if line.startswith("## "):
            in_jokes = line.startswith(JOKES_HEADING)
        m = AIRED.match(line)
        if m and "KEEP" not in line:
            if (today - datetime.date.fromisoformat(m.group(1))).days > mem["aired_days"]:
                pruned += 1
                continue
        if in_jokes and line.startswith("- "):
            jokes += 1
            if jokes > mem["weather_jokes"]:
                pruned += 1
                continue
        out.append(line)
    with open("aired-items.md", "w", encoding="utf-8") as f:
        f.write("\n".join(out).rstrip() + "\n")
    print(f"aired-items: {pruned} old line(s) pruned")
    return 0


if __name__ == "__main__":
    sys.exit(main())

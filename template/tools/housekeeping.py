#!/usr/bin/env python3
"""Keep the briefing's memory small. daily-run.md, Part B, before committing.

Usage: python3 tools/housekeeping.py [YYYY-MM-DD]

Does three mechanical things, so that no model ever has to decide them and
the memory can never grow:

1. Copies today's briefing.txt to archive/YYYY-MM-DD.txt.
2. Deletes archive files older than the configured number of days.
3. Rewrites threads.md: drops entries whose expiry date has passed, keeps
   only the newest N, and trims any entry that has grown too long.

The memory of the earlier version of this system grew to 160 KB of
"EARLIER... EARLIER..." chains and began to be read only in part. This
script is why that cannot happen here.
"""
import datetime
import glob
import json
import os
import re
import shutil
import sys
from zoneinfo import ZoneInfo

MAX_ENTRY_CHARS = 420
ENTRY = re.compile(r"^- \[expires (\d{4}-\d{2}-\d{2})\] ")


def main():
    cfg = json.load(open("config.json", encoding="utf-8"))
    mem = cfg.get("memory", {})
    keep_days = int(mem.get("archive_days", 7))
    max_threads = int(mem.get("max_threads", 12))
    tz = ZoneInfo(cfg.get("timezone", "Europe/London"))
    today = (datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1
             else datetime.datetime.now(tz).date())

    # 1 and 2: the rolling archive of what was actually said.
    os.makedirs("archive", exist_ok=True)
    if os.path.exists("briefing.txt"):
        shutil.copyfile("briefing.txt", f"archive/{today.isoformat()}.txt")
    removed = 0
    for path in glob.glob("archive/*.txt"):
        try:
            day = datetime.date.fromisoformat(os.path.basename(path)[:-4])
        except ValueError:
            continue
        if (today - day).days >= keep_days:
            os.remove(path)
            removed += 1
    kept = len(glob.glob("archive/*.txt"))
    print(f"archive: {kept} day(s) kept, {removed} removed")

    # 3: the watch list.
    if not os.path.exists("threads.md"):
        return 0
    head, entries, dropped, trimmed = [], [], 0, 0
    for line in open("threads.md", encoding="utf-8").read().splitlines():
        m = ENTRY.match(line)
        if not m:
            if line.startswith("- ["):
                dropped += 1             # an entry with no valid expiry date
            elif not entries:
                head.append(line)        # the explanatory header
            continue
        if datetime.date.fromisoformat(m.group(1)) < today:
            dropped += 1
            continue
        if len(line) > MAX_ENTRY_CHARS:
            line = line[:MAX_ENTRY_CHARS].rsplit(" ", 1)[0] + "..."
            trimmed += 1
        entries.append(line)
    if len(entries) > max_threads:
        dropped += len(entries) - max_threads
        entries = entries[:max_threads]      # newest are written first
    while head and not head[-1].strip():
        head.pop()
    with open("threads.md", "w", encoding="utf-8") as f:
        f.write("\n".join(head) + "\n\n" + "\n".join(entries) + ("\n" if entries else ""))
    print(f"threads: {len(entries)} kept, {dropped} dropped, {trimmed} trimmed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

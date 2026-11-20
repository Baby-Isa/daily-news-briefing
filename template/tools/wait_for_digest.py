#!/usr/bin/env python3
"""Wait for a fresh digest.txt to land on main. daily-run.md, step 2.

Usage: python3 tools/wait_for_digest.py [--minutes N] [--max-age MINUTES]

Run this right after starting the "Build digest" workflow. It pulls main
every 30 seconds until digest.txt was built within the last --max-age
minutes (default 30), for at most --minutes (default 8).

Exit 0: a fresh digest is in the working copy. Exit 1: none arrived - fall
back to building it here with `python3 build_digest.py`.
"""
import datetime
import re
import subprocess
import sys
import time


def built_at():
    try:
        tail = open("digest.txt", encoding="utf-8").read()[-300:]
    except FileNotFoundError:
        return None
    m = re.search(r"End of full digest\. Built (\S+)", tail)
    return datetime.datetime.fromisoformat(m.group(1)) if m else None


def arg(name, default):
    if name in sys.argv:
        return float(sys.argv[sys.argv.index(name) + 1])
    return default


def main():
    minutes, max_age = arg("--minutes", 8), arg("--max-age", 30)
    deadline = time.time() + minutes * 60
    while True:
        subprocess.run(["git", "pull", "-q", "--rebase", "origin", "main"],
                       capture_output=True)
        when = built_at()
        now = datetime.datetime.now(datetime.timezone.utc)
        if when and (now - when).total_seconds() <= max_age * 60:
            print(f"FRESH: digest built {when:%H:%M} UTC, "
                  f"{int((now - when).total_seconds() // 60)} minute(s) ago.")
            return 0
        if time.time() + 30 > deadline:
            print(f"NO FRESH DIGEST after {minutes:g} minutes "
                  f"(last build: {when:%d %b %H:%M} UTC)." if when else
                  f"NO DIGEST after {minutes:g} minutes.")
            return 1
        time.sleep(30)


if __name__ == "__main__":
    sys.exit(main())

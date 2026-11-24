#!/usr/bin/env python3
"""Wait for a NEW digest.txt to land on main. daily-run.md, step 2.

Usage:
    SINCE=$(date -u +%s)          # note the time BEFORE starting the build
    ... start the "Build digest" workflow ...
    python3 tools/wait_for_digest.py --since $SINCE [--minutes N]

Pulls main every 30 seconds, for at most --minutes (default 8), until
digest.txt was built AFTER the --since time. Comparing against the moment
the build was started matters: an earlier version accepted any digest
under thirty minutes old, and so returned at once with the previous build.

Exit 0: the new digest is in the working copy. Exit 1: none arrived - fall
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
    minutes = arg("--minutes", 8)
    # Without --since, accept only a digest built from now on.
    since = datetime.datetime.fromtimestamp(arg("--since", time.time()),
                                            datetime.timezone.utc)
    deadline = time.time() + minutes * 60
    while True:
        subprocess.run(["git", "pull", "-q", "--rebase", "origin", "main"],
                       capture_output=True)
        when = built_at()
        if when and when > since:
            print(f"FRESH: digest built {when:%H:%M:%S} UTC, after the "
                  f"{since:%H:%M:%S} UTC start.")
            return 0
        if time.time() + 30 > deadline:
            last = f"{when:%d %b %H:%M} UTC" if when else "none"
            print(f"NO NEW DIGEST after {minutes:g} minutes (last build: {last}).")
            return 1
        time.sleep(30)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Confirm today's podcast render landed on gh-pages (daily-run.md, Part B).

Usage: python3 tools/check_render.py [YYYY-MM-DD] [--minutes N]

Polls origin/gh-pages every 45 seconds, for at most N minutes (default 9, so
one run fits inside the ten-minute foreground Bash limit), until today's mp3
is there and newer than the last push of briefing.txt. Then checks the branch is clean, today's mp3 exists,
and reads today's <itunes:duration> from today's own <item> in feed.xml.
The feed is not in date order, so never take the first duration in the file.

Reads feed.xml from the gh-pages branch itself, not the CDN, which lags.

Exit 0: rendered and clean. Exit 1: not rendered within the time allowed
(run it once more; a healthy render lands five to eight minutes after the
push). Exit 2: rendered but something is wrong - report it loudly.
"""
import datetime
import json
import re
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

EXPECTED = {"audio", "feed.xml", "index.html", ".nojekyll"}
OPTIONAL = {"cover.png"}


def local_today():
    tz = ZoneInfo(json.load(open("config.json", encoding="utf-8")).get("timezone", "Europe/London"))
    return datetime.datetime.now(tz).strftime("%Y-%m-%d")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout


def main():
    args = [a for a in sys.argv[1:]]
    minutes = 9.0
    if "--minutes" in args:
        i = args.index("--minutes")
        minutes = float(args[i + 1])
        del args[i:i + 2]
    day = args[0] if args else local_today()

    deadline = time.time() + minutes * 60
    while True:
        git("fetch", "-q", "origin", "gh-pages")
        landed = git("log", "-1", "--format=%cd", "--date=short", "origin/gh-pages").strip()
        # Judge by today's mp3 being on the branch, not by the commit date:
        # the commit is stamped in UTC and the episode in local time.
        # ...and by the render being NEWER than the last push of
        # briefing.txt, so a re-render of the same day is waited for too.
        git("fetch", "-q", "origin", "main")
        pushed = int(git("log", "-1", "--format=%ct", "origin/main", "--", "briefing.txt").strip() or 0)
        rendered = int(git("log", "-1", "--format=%ct", "origin/gh-pages").strip() or 0)
        if day in git("ls-tree", "--name-only", "origin/gh-pages:audio") and rendered >= pushed:
            break
        if time.time() + 45 > deadline:
            print(f"NOT RENDERED: origin/gh-pages is still dated {landed}, "
                  f"target {day}, after {minutes:g} minutes. Run this once more.")
            return 1
        time.sleep(45)

    problems = []
    print("gh-pages commit:", git("log", "-1", "--format=%cd", "origin/gh-pages").strip())

    top = set(git("ls-tree", "--name-only", "origin/gh-pages").split())
    if (top - OPTIONAL) != EXPECTED:
        problems.append(f"gh-pages NOT CLEAN - top level is {sorted(top)}, expected "
                        f"{sorted(EXPECTED)}. Extra entries are a leaked TTS model.")
    else:
        print("gh-pages clean:", ", ".join(sorted(top)))

    mp3 = [l for l in git("ls-tree", "--name-only", "origin/gh-pages:audio").split() if day in l]
    if mp3:
        print("mp3:", ", ".join(mp3))
    else:
        problems.append(f"no mp3 for {day} in gh-pages audio/")

    feed = git("show", "origin/gh-pages:feed.xml")
    title_date = datetime.date.fromisoformat(day)
    want = f"{title_date.day} {title_date.strftime('%B %Y')}"
    items = [it for it in re.findall(r"<item>.*?</item>", feed, re.S)
             if want in (re.search(r"<title>([^<]*)", it) or [None, ""])[1]]
    if not items:
        problems.append(f"feed.xml has no item titled with {want}")
    else:
        title = re.search(r"<title>([^<]*)", items[0]).group(1)
        dur = re.search(r"<itunes:duration>([^<]*)", items[0])
        print("feed item:", title)
        print("duration:", dur.group(1) if dur else "MISSING")
        if not dur:
            problems.append("today's feed item has no itunes:duration")

    for p in problems:
        print("PROBLEM:", p)
    return 2 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

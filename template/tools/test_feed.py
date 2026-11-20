#!/usr/bin/env python3
"""Test a news source before adding it to feeds.txt.

Usage: python3 tools/test_feed.py "<feed url>" ["<another url>" ...]

Judges a feed by FRESHNESS, not by how many items it returns: a search
feed can return a hundred items and still be serving month-old news. The
verdict line says whether to add it.

Note: this runs inside Claude's own container, whose address some
publishers block. A feed that FAILS here may still work in the GitHub
build. A feed that PASSES here is safe to add.
"""
import datetime
import sys
import time

import feedparser

sys.path.insert(0, ".")
from fetch_utils import fetch  # noqa: E402


def test(url):
    resp, note = fetch(url)
    if resp is None:
        print(f"FAILED   {url}\n         could not fetch: {note}")
        return False
    entries = feedparser.parse(resp.content).entries
    if not entries:
        print(f"FAILED   {url}\n         fetched, but it contains no items (not a feed?)")
        return False
    now = datetime.datetime.now(datetime.timezone.utc)
    ages = []
    for e in entries[:15]:
        stamp = e.get("published_parsed") or e.get("updated_parsed")
        if stamp:
            when = datetime.datetime(*stamp[:6], tzinfo=datetime.timezone.utc)
            ages.append((now - when).total_seconds() / 3600)
    fresh = sum(a < 48 for a in ages)
    week = sum(a < 168 for a in ages)
    if fresh >= 3:
        verdict = "GOOD    "
    elif week >= 1:
        verdict = "QUIET   "
    else:
        verdict = "STALE   "
    print(f"{verdict} {url}")
    print(f"         {len(entries)} items; of the first {len(ages)}: {fresh} under two days old, "
          f"{week} under a week")
    for e in entries[:5]:
        print(f"         - {e.get('title', '')[:100]}")
    if verdict == "QUIET   ":
        print("         Add it with the QUIET flag (or RARE for a named company).")
    if verdict == "STALE   ":
        print("         Do not add: nothing from the past week.")
    return verdict != "STALE   "


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ok = True
    for i, u in enumerate(sys.argv[1:]):
        if i:
            time.sleep(3)
        ok = test(u) and ok
    sys.exit(0 if ok else 1)

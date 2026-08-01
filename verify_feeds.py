#!/usr/bin/env python3
"""
VERIFY: test every feed in feeds.txt from a machine with normal internet.

Why this exists
---------------
Feed verification done through Claude and Cowork proved unreliable: their
fetch tooling served cached copies, which produced false "stale" and
"zero item" verdicts. Anything they marked as failing needs re-testing
here before it gets discarded.

Two specific traps this script avoids:

1. RDF and Atom item counting. A feed using <item rdf:about="..."> (RSS 1.0)
   or <entry> (Atom) will read as zero items to anything looking for a bare
   <item> tag. Nature Aging and Marketplace Pulse are both real, working
   feeds that were nearly binned this way. feedparser handles all three
   formats, so we count parsed entries rather than matching strings.

2. User-agent blocking. Reddit and others return empty responses to bare
   scripts. We send a browser user-agent.

Output is a table you can paste back into the chat.
"""

import concurrent.futures
import sys
from datetime import datetime, timezone, timedelta

import requests
import feedparser

from fetch_utils import fetch

TIMEOUT = 25
MAX_WORKERS = 8

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, application/atom+xml, */*",
}

# Feeds where infrequent publication is normal. These get a longer
# staleness threshold so a quiet week is not reported as a failure.
QUIET_DAYS = 45
NORMAL_DAYS = 7


def load_feeds(path="feeds.txt"):
    feeds = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3 or not parts[2].startswith("http"):
            continue
        lane, outlet, url = parts[0], parts[1], parts[2]
        flags = parts[3].upper() if len(parts) > 3 else ""
        feeds.append({
            "lane": lane, "outlet": outlet, "url": url,
            "disputed": "DISPUTED" in flags,
            "quiet": "QUIET" in flags,
        })
    return feeds


def newest_entry_date(parsed):
    """Newest publication date across entries, ignoring future dates.

    Future dates appear on pages listing upcoming events and must not be
    mistaken for publication dates: that bug made one source look five
    days 'newer' than today.
    """
    today = datetime.now(timezone.utc).date()
    dates = []
    for e in parsed.entries:
        stamp = e.get("published_parsed") or e.get("updated_parsed")
        if stamp:
            try:
                d = datetime(*stamp[:6]).date()
                if d <= today:
                    dates.append(d)
            except (ValueError, TypeError):
                pass
    return max(dates) if dates else None


def check(feed):
    result = dict(feed)
    result.update(items=0, newest=None, age=None, status="", note="")
    resp, note = fetch(feed["url"])
    if resp is None:
        result["status"] = "FAIL"
        result["note"] = note
        return result
    fetch_note = "" if note == "ok" else f" [{note}]"

    # feedparser handles RSS 2.0, RSS 1.0/RDF and Atom alike, so this
    # count is format-agnostic rather than a tag string match.
    parsed = feedparser.parse(resp.content)
    result["items"] = len(parsed.entries)
    result["note"] = (parsed.version or "unknown") + " format" + fetch_note

    if result["items"] == 0:
        result["status"] = "FAIL"
        result["note"] = f"zero items ({len(resp.content):,} bytes returned)"
        return result

    newest = newest_entry_date(parsed)
    if newest is None:
        result["status"] = "NO DATES"
        result["note"] = "items present but none carry a usable date"
        return result

    age = (datetime.now(timezone.utc).date() - newest).days
    result["newest"] = newest
    result["age"] = age
    threshold = QUIET_DAYS if feed["quiet"] else NORMAL_DAYS
    if age <= 2:
        result["status"] = "CURRENT"
    elif age <= threshold:
        result["status"] = "OK"
    else:
        result["status"] = "STALE"
    return result


def main():
    feeds = load_feeds()
    print(f"Verifying {len(feeds)} feeds at "
          f"{datetime.now(timezone.utc).isoformat()} UTC\n")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = list(pool.map(check, feeds))

    print(f"{'Lane':<20} {'Outlet':<24} {'Status':<9} {'Items':>5} "
          f"{'Newest':<12} {'Age':>4}  Note")
    print("-" * 110)
    for r in sorted(results, key=lambda x: (x["lane"], x["outlet"])):
        newest = str(r["newest"]) if r["newest"] else "-"
        age = str(r["age"]) if r["age"] is not None else "-"
        print(f"{r['lane'][:19]:<20} {r['outlet'][:23]:<24} {r['status']:<9} "
              f"{r['items']:>5} {newest:<12} {age:>4}  {r['note'][:38]}")

    ok = [r for r in results if r["status"] in ("CURRENT", "OK")]
    bad = [r for r in results if r["status"] not in ("CURRENT", "OK")]
    disputed = [r for r in results if r["disputed"]]

    print(f"\n{'=' * 70}")
    print(f"Working: {len(ok)} of {len(results)}")

    if disputed:
        print("\nDISPUTED FEEDS (Cowork reported these as failing):")
        for r in disputed:
            verdict = ("actually works, Cowork was wrong"
                       if r["status"] in ("CURRENT", "OK")
                       else "confirmed failing")
            print(f"  {r['outlet']}: {r['status']} -> {verdict}")

    if bad:
        print("\nNEEDS ATTENTION:")
        for r in bad:
            print(f"  [{r['lane']}] {r['outlet']}: {r['status']} - {r['note']}")

    print("\nLanes and how many working sources each has:")
    lanes = {}
    for r in ok:
        lanes[r["lane"]] = lanes.get(r["lane"], 0) + 1
    for lane in sorted(set(f["lane"] for f in feeds)):
        n = lanes.get(lane, 0)
        marker = "  <-- THIN" if n < 2 else ""
        print(f"  {lane:<22} {n}{marker}")


if __name__ == "__main__":
    sys.exit(main())

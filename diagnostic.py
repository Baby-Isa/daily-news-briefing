#!/usr/bin/env python3
"""
DIAGNOSTIC: is the staleness our tooling, or the origin servers?

Background
----------
Fetching these pages through Claude and through Cowork returned content
weeks or months old, while a normal browser at the same moment showed
current content. Two possible causes:

  (a) the origin servers serve a heavily cached copy to any HTTP client
      -> FreshRSS and this runner would inherit the same staleness
  (b) a cache inside Anthropic's fetch tooling
      -> a direct request from anywhere else gets current content

This script settles it. GitHub Actions runners have ordinary,
unrestricted internet access, so what they see is what any normal
server sees.

Read the output like this:
  Dates here are CURRENT  -> cause was (b), our tooling. Scraping is fine.
  Dates here are STALE    -> cause was (a), the origin. Scraping is not
                             viable for that target by any HTTP method.

It also prints the caching response headers (Age, Cache-Control, ETag,
plus CDN headers), which Cowork could not see. A high 'Age' value is a
direct confession that a cache served the response.
"""

import re
import sys
from datetime import datetime, timezone

import requests
import feedparser
from bs4 import BeautifulSoup

TIMEOUT = 30

# A normal browser user-agent. Some sites serve different content, or
# refuse outright, when they think they are talking to a script.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    # Explicitly refuse cached responses where the server honours it.
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

# The four contested targets, plus controls.
HTML_TARGETS = [
    ("Al Jazeera UK",        "https://www.aljazeera.com/where/united-kingdom/"),
    ("Al Jazeera Opinion",   "https://www.aljazeera.com/opinion/"),
    ("Chainlink blog (NEW)", "https://chain.link/blog"),
    ("Chainlink blog (OLD)", "https://blog.chain.link"),
    ("Investegate ANIC",     "https://www.investegate.co.uk/company/ANIC"),
    ("Pulitzer Center",      "https://pulitzercenter.org"),
]

# Known-good feeds, as controls. If these come back current but the
# HTML targets do not, the difference is real rather than a runner fault.
FEED_TARGETS = [
    ("BBC News UK",       "https://feeds.bbci.co.uk/news/rss.xml?edition=uk"),
    ("Al Jazeera global", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("Euronews",          "https://www.euronews.com/rss"),
]

# Headers that reveal caching. 'Age' is the important one: it is the
# number of seconds the response has been sitting in a cache.
CACHE_HEADERS = [
    "Date", "Age", "Cache-Control", "ETag", "Last-Modified", "Expires",
    "X-Cache", "X-Cache-Hits", "CF-Cache-Status", "X-Served-By",
    "X-Timer", "Via", "Fastly-Debug-Digest",
]

# Date formats seen across these sites.
DATE_PATTERNS = [
    (r"\b(20\d{2}-\d{2}-\d{2})\b",                                  "%Y-%m-%d"),
    (r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+20\d{2})\b", None),
    (r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+20\d{2})\b", None),
]

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def parse_loose_date(text):
    """Turn the various date spellings into a date object, or None."""
    text = text.strip()
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        pass
    # "1 Aug 2026" / "31 May 2026"
    m = re.match(r"(\d{1,2})\s+([A-Za-z]+)\s+(20\d{2})", text)
    if m:
        mon = MONTHS.get(m.group(2)[:3].lower())
        if mon:
            return datetime(int(m.group(3)), mon, int(m.group(1))).date()
    # "August 1, 2026"
    m = re.match(r"([A-Za-z]+)\s+(\d{1,2}),\s+(20\d{2})", text)
    if m:
        mon = MONTHS.get(m.group(1)[:3].lower())
        if mon:
            return datetime(int(m.group(3)), mon, int(m.group(2))).date()
    return None


def find_dates(html):
    """Every date mentioned anywhere in the page, newest first."""
    found = set()
    for pattern, _ in DATE_PATTERNS:
        for match in re.findall(pattern, html):
            d = parse_loose_date(match)
            if d:
                found.add(d)
    return sorted(found, reverse=True)


def show_cache_headers(resp):
    print("  Response headers that reveal caching:")
    any_shown = False
    for h in CACHE_HEADERS:
        if h in resp.headers:
            print(f"    {h}: {resp.headers[h]}")
            any_shown = True
    if not any_shown:
        print("    (none present)")
    age = resp.headers.get("Age")
    if age and age.isdigit():
        hours = int(age) / 3600
        print(f"    >> This response came from a cache, {hours:.1f} hours old.")


def check_html(name, url, today):
    print(f"\n{'=' * 68}\n{name}\n{url}\n{'=' * 68}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    except Exception as e:
        print(f"  FAILED: {e}")
        return
    print(f"  HTTP {resp.status_code}, {len(resp.text):,} bytes")
    if resp.history:
        print(f"  Redirected {len(resp.history)} time(s) -> {resp.url}")
    show_cache_headers(resp)

    if resp.status_code != 200:
        print("  Non-200, stopping here.")
        return

    dates = find_dates(resp.text)
    if dates:
        newest = dates[0]
        gap = (today - newest).days
        print(f"  Newest date found in page: {newest}  ({gap} days old)")
        verdict = "CURRENT" if gap <= 2 else ("RECENT" if gap <= 7 else "STALE")
        print(f"  >> {verdict}")
        print(f"  Next few dates: {', '.join(str(d) for d in dates[1:5])}")
    else:
        print("  No dates found in the raw HTML.")

    soup = BeautifulSoup(resp.text, "html.parser")
    heads = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])]
    heads = [h for h in heads if len(h) > 25][:5]
    if heads:
        print("  First headlines in raw HTML (eyeball these for currency):")
        for h in heads:
            print(f"    - {h[:100]}")
    else:
        print("  No substantial headlines in raw HTML (likely JS-rendered).")


def check_feed(name, url, today):
    print(f"\n{'=' * 68}\n{name}  [CONTROL FEED]\n{url}\n{'=' * 68}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        show_cache_headers(resp)
        parsed = feedparser.parse(resp.content)
    except Exception as e:
        print(f"  FAILED: {e}")
        return
    print(f"  Content-Type: {resp.headers.get('Content-Type', 'unknown')}")
    print(f"  Items: {len(parsed.entries)}")
    if not parsed.entries:
        print("  >> ZERO ITEMS. A feed that parses but is empty is a FAILURE.")
        return
    e = parsed.entries[0]
    stamp = e.get("published_parsed") or e.get("updated_parsed")
    if stamp:
        newest = datetime(*stamp[:6]).date()
        gap = (today - newest).days
        print(f"  Newest item: {newest}  ({gap} days old)")
        print(f"  >> {'CURRENT' if gap <= 2 else ('RECENT' if gap <= 7 else 'STALE')}")
    print(f"  Newest title: {e.get('title', '(none)')[:100]}")


def main():
    now = datetime.now(timezone.utc)
    today = now.date()
    print("=" * 68)
    print("STALENESS DIAGNOSTIC")
    print(f"Run at {now.isoformat()} UTC")
    print("=" * 68)
    print(
        "\nIf dates below are CURRENT, the staleness seen through Claude and\n"
        "Cowork was their fetch tooling, not the websites. Scraping is then\n"
        "viable from this runner or from FreshRSS.\n"
        "If dates below are STALE too, the origin servers are the cause and\n"
        "no HTTP-based scraper will do better."
    )

    for name, url in FEED_TARGETS:
        check_feed(name, url, today)
    for name, url in HTML_TARGETS:
        check_html(name, url, today)

    print(f"\n{'=' * 68}")
    print("Compare 'Chainlink blog (NEW)' against '(OLD)'. If OLD shows")
    print("older dates, that confirms blog.chain.link is an abandoned")
    print("backend and only chain.link/blog should ever be used.")
    print("=" * 68)


if __name__ == "__main__":
    sys.exit(main())

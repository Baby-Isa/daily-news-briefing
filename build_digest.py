#!/usr/bin/env python3
"""
BUILD THE DAILY DIGEST.

Reads feeds.txt, fetches everything, keeps only the last 24 hours,
removes duplicate stories, pulls full article text where it is needed
for analysis, and writes one plain-text file.

That file is the single input to the morning brief. Nothing downstream
needs to fetch anything, which matters because fetching has been the
unreliable part of this whole system.

Design decisions worth knowing:

- Deduplication is by title similarity, not exact match. Twenty feeds
  running the same agency wire produce twenty near-identical headlines.
  Reporting that once is correct; reporting it twenty times is noise,
  and treating it as twenty sources agreeing would be worse.

- Full text is fetched ONLY for feeds flagged FULLTEXT. Turning it on
  everywhere would make the digest enormous. It is on where real
  analysis is needed (economy, politics, editorial, Chainlink) and off
  where the headline genuinely is the story (Arsenal, gadgets).

- QUIET feeds get a longer staleness threshold. Agronomics not
  announcing anything for three weeks is a quiet company, not a broken
  feed, and the digest must not confuse the two.

- Every failure is reported in the digest itself. A feed that silently
  drops out looks identical to a quiet news day, and that is the worst
  failure mode for a brief listened to half asleep.
"""

import concurrent.futures
import html
import re
import sys
from datetime import datetime, timezone, timedelta

import requests
import feedparser

from fetch_utils import fetch
from bs4 import BeautifulSoup

WINDOW_HOURS = 24        # how far back to look for normal feeds
QUIET_WINDOW_HOURS = 168 # a week, for low-volume feeds
QUIET_STALE_DAYS = 45    # beyond this, even a quiet feed is flagged
NORMAL_STALE_DAYS = 7
TIMEOUT = 25
MAX_WORKERS = 8
FULLTEXT_CHARS = 4000    # cap per article, keeps the digest usable

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, application/atom+xml, */*",
}

# Order the digest by these groups so the brief reads top-down.
LANE_GROUPS = [
    ("WORLD", ["UK", "Europe", "North America", "Latin America", "Middle East",
               "East Africa", "Sub-Saharan Africa", "North Africa", "South Asia",
               "East Asia", "Southeast Asia", "Central Asia", "Eastern Europe",
               "Pacific"]),
    ("POLITICS AND CONFLICT", ["Politics", "Conflict", "Law"]),
    ("ECONOMY AND BUSINESS", ["Economy", "Business"]),
    ("SCIENCE AND TECHNOLOGY", ["Science", "Space", "Health", "Energy",
                                "AI and technology", "Built environment"]),
    ("SOCIETY", ["Society and culture"]),
    ("WATCHLIST", ["Arsenal", "Chainlink", "OriginTrail", "Agronomics"]),
    ("SPECIAL INTERESTS", ["Projectors", "Aviation", "Cameras", "Cars",
                           "Urbanism", "Games", "Longevity", "E-commerce",
                           "Trends", "Employers"]),
    ("EDITORIAL", ["Editorial"]),
]

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
    "been", "has", "have", "had", "says", "say", "said", "after", "over",
    "new", "its", "his", "her", "their", "this", "that", "will", "would",
}


def load_feeds(path="feeds.txt"):
    feeds = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3 or not parts[2].startswith("http"):
            continue
        flags = parts[3].upper() if len(parts) > 3 else ""
        feeds.append({
            "lane": parts[0], "outlet": parts[1], "url": parts[2],
            "fulltext": "FULLTEXT" in flags,
            "quiet": "QUIET" in flags,
        })
    return feeds


def clean_text(raw, limit=400):
    """Strip HTML tags and entities out of a feed summary."""
    if not raw:
        return ""
    text = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    return text[:limit] + ("..." if len(text) > limit else "")


def title_tokens(title):
    """Significant words in a headline, for duplicate detection."""
    words = re.findall(r"[a-z0-9]+", title.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def is_duplicate(tokens_a, tokens_b, threshold=0.55):
    """Two headlines describing the same story share most significant words."""
    if not tokens_a or not tokens_b:
        return False
    overlap = len(tokens_a & tokens_b)
    smaller = min(len(tokens_a), len(tokens_b))
    return smaller > 0 and (overlap / smaller) >= threshold


def fetch_fulltext(url):
    """Pull the article body. Best effort: returns '' on any failure."""
    try:
        resp, _ = fetch(url)
        if resp is None:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        # Prefer a semantic <article>; otherwise take the block with the
        # most paragraph text, which is almost always the article body.
        node = soup.find("article")
        if not node:
            candidates = soup.find_all(["div", "main", "section"])
            node = max(candidates,
                       key=lambda d: sum(len(p.get_text()) for p in d.find_all("p")),
                       default=None)
        if not node:
            return ""
        paras = [p.get_text(" ", strip=True) for p in node.find_all("p")]
        body = " ".join(p for p in paras if len(p) > 40)
        body = re.sub(r"\s+", " ", body).strip()
        return body[:FULLTEXT_CHARS]
    except Exception:
        return ""


def fetch_feed(feed):
    """Fetch one feed and return its recent items plus any failure note."""
    out = {"feed": feed, "items": [], "error": None, "newest": None}
    resp, note = fetch(feed["url"])
    if resp is None:
        out["error"] = note
        return out

    parsed = feedparser.parse(resp.content)
    if not parsed.entries:
        out["error"] = "feed returned zero items"
        return out

    now = datetime.now(timezone.utc)
    window = timedelta(hours=QUIET_WINDOW_HOURS if feed["quiet"] else WINDOW_HOURS)
    newest = None

    for entry in parsed.entries:
        stamp = entry.get("published_parsed") or entry.get("updated_parsed")
        if not stamp:
            continue
        try:
            when = datetime(*stamp[:6], tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        if when > now + timedelta(days=1):
            continue  # future-dated event listing, not a publication date
        if newest is None or when > newest:
            newest = when
        if now - when <= window:
            out["items"].append({
                "lane": feed["lane"],
                "outlet": feed["outlet"],
                "title": clean_text(entry.get("title", ""), 300),
                "summary": clean_text(entry.get("summary", "")),
                "link": entry.get("link", ""),
                "when": when,
                "fulltext": "",
                "wants_fulltext": feed["fulltext"],
            })

    out["newest"] = newest
    if newest:
        age_days = (now - newest).days
        limit = QUIET_STALE_DAYS if feed["quiet"] else NORMAL_STALE_DAYS
        if age_days > limit:
            out["error"] = f"stale: newest item {age_days} days old"
    return out


def deduplicate(items):
    """Collapse the same story reported by several outlets into one entry."""
    items.sort(key=lambda i: i["when"], reverse=True)
    kept = []
    for item in items:
        tokens = title_tokens(item["title"])
        item["_tokens"] = tokens
        match = None
        for k in kept:
            if is_duplicate(tokens, k["_tokens"]):
                match = k
                break
        if match:
            match.setdefault("also_in", []).append(item["outlet"])
            # Keep whichever version carries more detail.
            if len(item["summary"]) > len(match["summary"]):
                match["summary"] = item["summary"]
        else:
            kept.append(item)
    return kept


def main():
    feeds = load_feeds()
    now = datetime.now(timezone.utc)
    print(f"Fetching {len(feeds)} feeds...", file=sys.stderr)

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = list(pool.map(fetch_feed, feeds))

    all_items, failures = [], []
    for r in results:
        all_items.extend(r["items"])
        if r["error"]:
            failures.append(f"{r['feed']['outlet']} ({r['feed']['lane']}): {r['error']}")

    print(f"{len(all_items)} items in window, deduplicating...", file=sys.stderr)
    items = deduplicate(all_items)
    print(f"{len(items)} unique stories.", file=sys.stderr)

    # Full text only for flagged feeds, and only for stories that survived
    # deduplication, so we never fetch an article we are going to discard.
    wanted = [i for i in items if i["wants_fulltext"] and i["link"]]
    print(f"Fetching full text for {len(wanted)} articles...", file=sys.stderr)
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        bodies = list(pool.map(lambda i: fetch_fulltext(i["link"]), wanted))
    for item, body in zip(wanted, bodies):
        item["fulltext"] = body

    lines = []
    lines.append("=" * 70)
    lines.append(f"NEWS DIGEST for {now.strftime('%A %d %B %Y')}")
    lines.append(f"Built {now.strftime('%H:%M')} UTC")
    lines.append(f"{len(items)} unique stories from {len(feeds)} feeds")
    lines.append("=" * 70)
    lines.append("")
    lines.append("Every item below is dated. Check each date against today "
                 "before treating anything as new.")
    lines.append("")

    for group_name, lanes in LANE_GROUPS:
        group_items = [i for i in items if i["lane"] in lanes]
        if not group_items:
            continue
        lines.append("")
        lines.append("#" * 70)
        lines.append(f"## {group_name}")
        lines.append("#" * 70)
        for lane in lanes:
            lane_items = [i for i in group_items if i["lane"] == lane]
            if not lane_items:
                continue
            lines.append("")
            lines.append(f"--- {lane} ({len(lane_items)}) ---")
            for i in lane_items:
                also = ""
                if i.get("also_in"):
                    others = sorted(set(i["also_in"]))
                    also = f" [also carried by: {', '.join(others)}]"
                lines.append("")
                lines.append(f"* {i['title']}")
                lines.append(f"  {i['outlet']} | {i['when'].strftime('%d %b %H:%M')} UTC{also}")
                if i["summary"]:
                    lines.append(f"  {i['summary']}")
                if i["fulltext"]:
                    lines.append(f"  FULL TEXT: {i['fulltext']}")
                if i["link"]:
                    lines.append(f"  {i['link']}")

    lines.append("")
    lines.append("=" * 70)
    lines.append("SOURCES THAT FAILED TODAY")
    lines.append("=" * 70)
    if failures:
        lines.append("These produced nothing. Treat the lanes they cover as "
                     "unverified rather than quiet:")
        for f in sorted(failures):
            lines.append(f"  - {f}")
    else:
        lines.append("None. Every feed returned current items.")

    lines.append("")
    lines.append(f"Digest ends. Built {now.isoformat()}")

    text = "\n".join(lines)
    with open("digest.txt", "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"Wrote digest.txt ({len(text):,} characters)", file=sys.stderr)
    print(f"{len(failures)} feeds failed.", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())

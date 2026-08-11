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
FULLTEXT_CHARS = 2500    # cap per article, keeps the digest usable
MAX_ITEMS_PER_LANE = 12  # see cap_per_lane(); halves the digest's size

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, application/atom+xml, */*",
}

# Each output file must stay under roughly 100,000 characters: a reader
# fetching the digest truncated at about that point and silently lost
# every section after it. Splitting keeps everything readable.
FILE_SPLITS = [
    ("digest.txt", ["WORLD: EUROPE AND AMERICAS",
                    "WORLD: MIDDLE EAST AND AFRICA",
                    "WORLD: ASIA AND PACIFIC",
                    "POLITICS AND CONFLICT", "ECONOMY AND BUSINESS",
                    "SCIENCE AND TECHNOLOGY", "SOCIETY",
                    "WATCHLIST", "SPECIAL INTERESTS", "EDITORIAL"]),
]

# Order the digest by these groups so the brief reads top-down.
LANE_GROUPS = [
    ("WORLD: EUROPE AND AMERICAS",
     ["UK", "Europe", "Eastern Europe", "North America", "Latin America"]),
    ("WORLD: MIDDLE EAST AND AFRICA",
     ["Middle East", "East Africa", "Sub-Saharan Africa", "North Africa"]),
    ("WORLD: ASIA AND PACIFIC",
     ["South Asia", "East Asia", "Southeast Asia", "Central Asia", "Pacific"]),
    ("POLITICS AND CONFLICT", ["Politics", "Conflict", "Law"]),
    ("ECONOMY AND BUSINESS", ["Economy", "Business", "Mergers and Acquisitions"]),
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


# Ruislip, west London. The Norwegian Met Office API is free, needs no
# key, and was the one weather source that worked reliably. It does
# require a real User-Agent identifying the caller.
WEATHER_LAT, WEATHER_LON = 51.5765, -0.4213
WEATHER_PLACE = "Ruislip, west London"


def fetch_weather():
    """Today plus a five-day outlook. Returns lines, or a failure note."""
    url = (f"https://api.met.no/weatherapi/locationforecast/2.0/compact"
           f"?lat={WEATHER_LAT}&lon={WEATHER_LON}")
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers={
            "User-Agent": "daily-news-briefing/1.0 github.com/daily-news-briefing"
        })
        if resp.status_code != 200:
            return [f"  Weather unavailable: HTTP {resp.status_code}"]
        data = resp.json()
    except Exception as e:
        return [f"  Weather unavailable: {type(e).__name__}"]

    series = data.get("properties", {}).get("timeseries", [])
    if not series:
        return ["  Weather unavailable: empty forecast"]

    by_day = {}
    for point in series:
        try:
            when = datetime.fromisoformat(point["time"].replace("Z", "+00:00"))
            inst = point["data"]["instant"]["details"]
        except (KeyError, ValueError):
            continue
        day = when.date()
        d = by_day.setdefault(day, {"temps": [], "rain": 0.0, "symbols": [],
                                    "wind": []})
        if "air_temperature" in inst:
            d["temps"].append(inst["air_temperature"])
        if "wind_speed" in inst:
            d["wind"].append(inst["wind_speed"])
        nxt = point["data"].get("next_6_hours") or point["data"].get("next_1_hours")
        if nxt:
            d["rain"] += nxt.get("details", {}).get("precipitation_amount", 0) or 0
            sym = nxt.get("summary", {}).get("symbol_code")
            if sym:
                d["symbols"].append(sym.split("_")[0].replace("_", " "))

    lines = [f"  Location: {WEATHER_PLACE}"]
    for day in sorted(by_day)[:6]:
        d = by_day[day]
        if not d["temps"]:
            continue
        lo, hi = min(d["temps"]), max(d["temps"])
        sym = max(set(d["symbols"]), key=d["symbols"].count) if d["symbols"] else "unknown"
        wind = f", wind up to {max(d['wind']):.0f} m/s" if d["wind"] else ""
        label = "TODAY" if day == datetime.now(timezone.utc).date() else day.strftime("%a %d %b")
        lines.append(f"  {label}: {lo:.0f} to {hi:.0f}C, {sym}, "
                     f"{d['rain']:.1f}mm rain{wind}")
    return lines


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
        # FILTER must come LAST on the line: everything after it is taken
        # as the comma-separated keyword list, so keywords may contain
        # spaces. Pipes cannot be used, being the field separator.
        keywords = []
        if "FILTER:" in flags:
            keywords = [k.strip().lower()
                        for k in flags.split("FILTER:", 1)[1].split(",")
                        if k.strip()]
        feeds.append({
            "lane": parts[0], "outlet": parts[1], "url": parts[2],
            "fulltext": "FULLTEXT" in flags,
            "quiet": "QUIET" in flags,
            "keywords": keywords,
        })
    return feeds


def clean_text(raw, limit=340):
    """Strip HTML tags and entities out of a feed summary.

    340 chosen by testing ten real summaries whose content reached the
    final brief: at 260 the sodium-battery desalination detail was lost;
    at 340 none of the ten lost anything. Do not lower without rerunning
    that test.
    """
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
        if feed.get("keywords"):
            haystack = (entry.get("title", "") + " " +
                        entry.get("summary", "")).lower()
            if not any(k in haystack for k in feed["keywords"]):
                continue
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
    groups = []
    for item in items:
        item["_tokens"] = title_tokens(item["title"])
        match = None
        for g in groups:
            if is_duplicate(item["_tokens"], g[0]["_tokens"]):
                match = g
                break
        if match:
            match.append(item)
        else:
            groups.append([item])

    kept = []
    for group in groups:
        # Canonical = the version with the most substance, not merely the
        # newest. Otherwise a forum thread quoting a wire story outranks
        # the wire story itself, which happened on the first run.
        canonical = max(group, key=lambda i: (len(i.get("fulltext") or ""),
                                              len(i["summary"])))
        others = sorted({i["outlet"] for i in group
                         if i["outlet"] != canonical["outlet"]})
        if others:
            canonical["also_in"] = others
        kept.append(canonical)
    kept.sort(key=lambda i: i["when"], reverse=True)
    return kept


def cap_per_lane(items, cap=None):
    """Keep only the top `cap` stories in each lane.

    The brief this feeds is now a ~1,500-word, under-ten-minute briefing,
    so the drafting step needs a few dozen stories to choose from, not
    nine hundred. Uncapped, the wire lanes swamp the file: East Asia alone
    ran 85 items on 11 Aug against a 16-item Health lane, and the whole
    digest came to 466,000 characters - which costs far more to read than
    the brief it produces costs to write.

    The cap is per lane, not global, so it only bites on the high-volume
    wire lanes. All 41 lanes stay represented and the small standing lanes
    (Chainlink, Agronomics, Cameras, Urbanism) are untouched - a cap that
    trimmed those would defeat the point of having them.

    NOTHING IS DROPPED. Past the cap, items are DEMOTED - kept in the file
    as a one-line title so the drafting step can still see the story
    exists, just without the summary and link. This is deliberate, and it
    is the second version of this function. The first one deleted the tail
    outright, and an experiment against the 11 Aug digest showed exactly
    what that cost: of the stories that actually made that morning's
    brief, 75 would have been deleted before the drafting step ever saw
    them.

    The reason is that LANES ARE ASSIGNED BY FEED, NOT BY TOPIC. SCMP sits
    in the East Asia lane but carried that day's "Todd Blanche sworn in as
    US attorney general"; Al Jazeera sits in Middle East but carried a US
    childhood-vaccination story; Al-Monitor sits in North Africa but
    carried Trump on Iran compensation. Capping the East Asia lane does
    not cap East Asia news, it caps whatever SCMP happened to publish,
    across every topic there is. Deduplication runs globally and keeps one
    canonical copy, so a story lives in exactly one lane - meaning a lane
    cap can be the only thing standing between a major story and oblivion.
    Demotion removes that failure mode: worst case a story appears as a
    bare headline instead of a headline plus summary.

    FULL-TEXT-FLAGGED ITEMS ARE EXEMPT and always keep their full entry.
    These are the economy, politics, editorial and Chainlink feeds that
    carry whole article bodies - the fuel for the analysis, which the
    brief protects above all other content.

    Ranking among the rest, highest first:
      1. Cross-outlet pickup (len of also_in). A weak signal - the same
         experiment found most of the demoted-but-used stories had none -
         which is survivable now that ranking low costs a story its
         summary rather than its existence.
      2. Recency, as the tiebreak.
    """
    cap = MAX_ITEMS_PER_LANE if cap is None else cap
    by_lane = {}
    for item in items:
        by_lane.setdefault(item["lane"], []).append(item)

    for lane_items in by_lane.values():
        exempt = [i for i in lane_items if i.get("wants_fulltext")]
        rest = [i for i in lane_items if not i.get("wants_fulltext")]
        rest.sort(key=lambda i: (len(i.get("also_in") or []), i["when"]),
                  reverse=True)
        for i in exempt + rest[:cap]:
            i["demoted"] = False
        for i in rest[cap:]:
            i["demoted"] = True

    items.sort(key=lambda i: i["when"], reverse=True)
    return items


def main():
    feeds = load_feeds()
    now = datetime.now(timezone.utc)
    print("Fetching weather...", file=sys.stderr)
    weather_lines = fetch_weather()
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

    items = cap_per_lane(items)
    demoted = sum(1 for i in items if i.get("demoted"))
    print(f"{len(items) - demoted} full entries, {demoted} demoted to "
          f"headline-only (per-lane cap {MAX_ITEMS_PER_LANE}).", file=sys.stderr)

    # Full text only for flagged feeds, and only for stories that survived
    # deduplication, so we never fetch an article we are going to discard.
    wanted = [i for i in items if i["wants_fulltext"] and i["link"]]
    print(f"Fetching full text for {len(wanted)} articles...", file=sys.stderr)
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        bodies = list(pool.map(lambda i: fetch_fulltext(i["link"]), wanted))
    fulltext_failed = []
    for item, body in zip(wanted, bodies):
        item["fulltext"] = body
        if not body:
            fulltext_failed.append(f"{item['outlet']}: {item['title'][:60]}")
    if fulltext_failed:
        print(f"Full text failed for {len(fulltext_failed)} of {len(wanted)}",
              file=sys.stderr)

    def header(part_name, part_of):
        h = []
        h.append("=" * 70)
        h.append(f"NEWS DIGEST for {now.strftime('%A %d %B %Y')}  [{part_of}]")
        h.append(f"Built {now.strftime('%H:%M')} UTC")
        h.append(f"{len(items)} unique stories from {len(feeds)} feeds")
        h.append("=" * 70)
        h.append("")
        h.append("Every item below is dated. Check each date against today "
                 "before treating anything as new.")
        h.append("")
        return h

    def render_group(group_name, lanes):
        out = []
        group_items = [i for i in items if i["lane"] in lanes]
        if not group_items:
            return out
        out.append("")
        out.append("#" * 70)
        out.append(f"## {group_name}")
        out.append("#" * 70)
        for lane in lanes:
            lane_items = [i for i in group_items if i["lane"] == lane]
            if not lane_items:
                continue
            full = [i for i in lane_items if not i.get("demoted")]
            demoted = [i for i in lane_items if i.get("demoted")]
            out.append("")
            out.append(f"--- {lane} ({len(lane_items)}) ---")
            for i in full:
                also = ""
                if i.get("also_in"):
                    also = f" [also carried by: {', '.join(sorted(set(i['also_in'])))}]"
                out.append("")
                out.append(f"* {i['title']}")
                out.append(f"  {i['outlet']} | {i['when'].strftime('%d %b %H:%M')} UTC{also}")
                if i["summary"]:
                    out.append(f"  {i['summary']}")
                if i["fulltext"]:
                    out.append(f"  FULL TEXT: {i['fulltext']}")
                if i["link"]:
                    out.append(f"  {i['link']}")
            if demoted:
                out.append("")
                out.append(f"  ALSO IN {lane.upper()} ({len(demoted)}), headline only. "
                           "These are real stories that cleared the same date "
                           "filter as everything above; they ranked lower on "
                           "cross-outlet pickup, which is a weak signal. If one "
                           "matters, use it - you have the headline, so say only "
                           "what the headline supports.")
                for i in demoted:
                    out.append(f"  - {i['title']} ({i['outlet']})")
        return out

    def footer():
        f = []
        f.append("")
        f.append("#" * 70)
        f.append("## WEATHER")
        f.append("#" * 70)
        f.append("")
        f.extend(weather_lines)
        if fulltext_failed:
            f.append("")
            f.append("=" * 70)
            f.append("FULL TEXT UNAVAILABLE")
            f.append("=" * 70)
            f.append("Flagged for full-text analysis but only the summary "
                     "could be retrieved, usually a paywall. Do not treat "
                     "the summary as the whole article:")
            for x in fulltext_failed[:20]:
                f.append(f"  - {x}")
        f.append("")
        f.append("=" * 70)
        f.append("SOURCES THAT FAILED TODAY")
        f.append("=" * 70)
        if failures:
            f.append("These produced nothing. Treat the lanes they cover as "
                     "unverified rather than quiet:")
            for x in sorted(failures):
                f.append(f"  - {x}")
        else:
            f.append("None. Every feed returned current items.")
        return f

    total_parts = len(FILE_SPLITS)
    for idx, (filename, group_names) in enumerate(FILE_SPLITS, start=1):
        label = "full digest"
        lines = header(filename, label)
        for group_name, lanes in LANE_GROUPS:
            if group_name in group_names:
                lines.extend(render_group(group_name, lanes))
        # The failure list goes on every part: whichever one gets read,
        # the reader must see which lanes are unverified.
        lines.extend(footer())
        lines.append("")
        lines.append(f"End of {label}. Built {now.isoformat()}")
        text = "\n".join(lines)
        with open(filename, "w", encoding="utf-8") as fh:
            fh.write(text)
        flag = "" if len(text) < 100_000 else "  <-- OVER 100k, may truncate"
        print(f"Wrote {filename} ({len(text):,} characters){flag}",
              file=sys.stderr)

    print(f"{len(failures)} feeds failed.", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())

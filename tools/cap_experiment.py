#!/usr/bin/env python3
"""Did capping each lane at 12 stories cost the brief anything?

Replays the cap against the EXACT item set this morning's brief was
drafted from (digest.txt at commit 8f76b8c, 903 stories, uncapped), then
asks whether any story the cap would have dropped actually made it into
the brief that was written from the uncapped file.

A story that was dropped by the cap AND appears in the brief is a real
loss - the cap would have cost the brief that story. A story dropped by
the cap and absent from the brief cost nothing: the drafting step had it
available and chose not to use it.
"""
import re
import sys
from datetime import datetime

MONTHS = {m: i for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}

STOP = set("""the a an and or but of in on at to for from with by as is are was
were be been being this that these those it its his her their our your my we
they he she you i not no non over under after before new news say says said
will would can could may might must have has had do does did more most other
another such into than then them there here what which who whom whose when
where why how all any both each few many some own same so too very just also
about against between during through above below up down out off again further
once only if because until while at by for with about into through during
report reports latest update updates first second third year years day days
week weeks month months time times world global amid amid ahead back set gets
get make makes made take takes taken come comes came top big large small""".split())


def parse_digest(path):
    """Parse the rendered digest back into per-item records."""
    items = []
    lane = None
    cur = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            m = re.match(r"^--- (.+?) \((\d+)\) ---$", line)
            if m:
                lane = m.group(1)
                continue
            if line.startswith("* "):
                if cur:
                    items.append(cur)
                cur = {"lane": lane, "title": line[2:].strip(),
                       "also_in": 0, "fulltext": False, "when": None,
                       "summary": ""}
                continue
            if cur is None:
                continue
            # metadata line: "  Outlet | 11 Aug 06:12 UTC [also carried by: x, y]"
            m = re.match(r"^  (.+?) \| (\d{2} \w{3} \d{2}:\d{2}) UTC(.*)$", line)
            if m and cur["when"] is None:
                cur["outlet"] = m.group(1)
                d, mon, hm = m.group(2).split()[0], m.group(2).split()[1], m.group(2).split()[2]
                hh, mm = hm.split(":")
                cur["when"] = datetime(2026, MONTHS[mon], int(d), int(hh), int(mm))
                tail = m.group(3)
                a = re.search(r"\[also carried by: (.+?)\]", tail)
                if a:
                    cur["also_in"] = len([x for x in a.group(1).split(",") if x.strip()])
                continue
            if line.startswith("  FULL TEXT:"):
                cur["fulltext"] = True
                continue
            if line.startswith("  ") and not cur["summary"] and not line.strip().startswith("http"):
                cur["summary"] = line.strip()
    if cur:
        items.append(cur)
    return [i for i in items if i["lane"] and i["when"]]


def cap_per_lane(items, cap=12):
    """Same logic as build_digest.cap_per_lane: full-text exempt, then
    rank remaining on cross-outlet pickup, then recency."""
    by_lane = {}
    for it in items:
        by_lane.setdefault(it["lane"], []).append(it)
    kept, dropped = [], []
    for lane_items in by_lane.values():
        exempt = [i for i in lane_items if i["fulltext"]]
        capped = [i for i in lane_items if not i["fulltext"]]
        capped.sort(key=lambda i: (i["also_in"], i["when"]), reverse=True)
        kept.extend(exempt + capped[:cap])
        dropped.extend(capped[cap:])
    return kept, dropped


def tokens(text):
    words = re.findall(r"[A-Za-z][A-Za-z'\-]{2,}", text)
    return {w.lower() for w in words if w.lower() not in STOP and len(w) > 3}


def proper_nouns(title):
    """Capitalised words not at sentence start - the strongest match signal."""
    words = re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", title)
    return {w.lower() for w in words if w.lower() not in STOP}


def match_score(item, brief_text, brief_tokens):
    """How strongly does this digest item appear in the brief?"""
    t = tokens(item["title"])
    if not t:
        return 0.0, set()
    hit = t & brief_tokens
    frac = len(hit) / len(t)
    pn = proper_nouns(item["title"])
    pn_hit = pn & brief_tokens
    # require proper-noun evidence when the title has any, to cut false
    # positives from generic vocabulary
    if pn and not pn_hit:
        return 0.0, set()
    return frac, hit


def main():
    items = parse_digest("/tmp/digest_morning.txt")
    brief = open("/tmp/briefing_morning.txt", encoding="utf-8").read().lower()
    brief_tokens = tokens(brief)

    print(f"Parsed {len(items)} items from the morning digest "
          f"across {len({i['lane'] for i in items})} lanes.")
    kept, dropped = cap_per_lane(items)
    print(f"Cap at 12: {len(kept)} kept, {len(dropped)} dropped.\n")

    THRESH = 0.6
    def scored(pool):
        out = []
        for it in pool:
            frac, hit = match_score(it, brief, brief_tokens)
            if frac >= THRESH:
                out.append((frac, it, hit))
        out.sort(key=lambda x: -x[0])
        return out

    hits_dropped = scored(dropped)
    hits_kept = scored(kept)

    print(f"KEPT items matching the brief:    {len(hits_kept):>4} of {len(kept)} "
          f"({len(hits_kept)/len(kept)*100:.1f}%)  <- base rate")
    print(f"DROPPED items matching the brief: {len(hits_dropped):>4} of {len(dropped)} "
          f"({len(hits_dropped)/len(dropped)*100:.1f}%)\n")

    print("=" * 72)
    print("CANDIDATE LOSSES - dropped by the cap, yet appear in the brief")
    print("=" * 72)
    for frac, it, hit in hits_dropped[:40]:
        print(f"\n[{frac:.0%}] {it['lane']} | {it.get('outlet','?')} | "
              f"also_in={it['also_in']}")
        print(f"  {it['title'][:150]}")
        print(f"  matched: {', '.join(sorted(hit))[:120]}")


if __name__ == "__main__":
    main()

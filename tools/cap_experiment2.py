#!/usr/bin/env python3
"""Refinement: are the cap's casualties genuinely lost, or did the same
story survive in the kept set via another feed?

build_digest deduplicates GLOBALLY (not per lane) before the cap runs, so
each story should already appear exactly once. If that holds, a dropped
item that appears in the brief is a true loss. This checks it rather than
assuming it.
"""
import re
from cap_experiment import parse_digest, cap_per_lane, tokens, match_score

items = parse_digest("/tmp/digest_morning.txt")
brief = open("/tmp/briefing_morning.txt", encoding="utf-8").read().lower()
brief_tokens = tokens(brief)
kept, dropped = cap_per_lane(items)

kept_tok = [(i, tokens(i["title"])) for i in kept]

true_losses, covered = [], []
for it in dropped:
    frac, hit = match_score(it, brief, brief_tokens)
    if frac < 0.6:
        continue
    dt = tokens(it["title"])
    best, best_ov = None, 0.0
    for k, kt in kept_tok:
        if not kt:
            continue
        ov = len(dt & kt) / max(1, min(len(dt), len(kt)))
        if ov > best_ov:
            best_ov, best = ov, k
    if best_ov >= 0.5:
        covered.append((it, best, best_ov))
    else:
        true_losses.append((frac, it, best, best_ov))

print(f"Dropped items appearing in the brief:      {len(true_losses)+len(covered)}")
print(f"  ...same story survived in kept set:      {len(covered)}")
print(f"  ...GENUINELY LOST (no kept equivalent):  {len(true_losses)}")

by_lane = {}
for frac, it, _, _ in true_losses:
    by_lane.setdefault(it["lane"], []).append(it)

print("\nTrue losses by lane (lane had >12 non-fulltext items):")
for lane, its in sorted(by_lane.items(), key=lambda x: -len(x[1])):
    print(f"  {lane:<28} {len(its):>3}")

print("\n" + "=" * 72)
print("SAMPLE OF GENUINELY LOST STORIES THAT MADE THIS MORNING'S BRIEF")
print("=" * 72)
for frac, it, best, ov in sorted(true_losses, key=lambda x: -x[0])[:25]:
    print(f"\n[{frac:.0%} match] {it['lane']} | {it.get('outlet','?')}")
    print(f"  {it['title'][:140]}")

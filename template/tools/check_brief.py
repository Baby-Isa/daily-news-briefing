#!/usr/bin/env python3
"""Check a drafted briefing against the countable rules. daily-run.md, Part B.

Usage: python3 tools/check_brief.py [briefing.txt]

These are the rules that drift when nobody counts them. Every limit comes
from config.json, so changing a length or a section budget there changes
what is enforced here.

Exit 0: all clear. Exit 1: problems listed, one per line, each written as
an instruction the drafter can act on.

  MUST FIX   mechanical faults that break the audio or the format.
  DRIFT      the brief is moving away from its agreed shape. Send the draft
             back ONCE to fix these; if they remain, publish anyway and put
             them in the run log. A style fault never costs a day.
"""
import json
import re
import sys

BANNED = [
    "as previously flagged", "as previously mentioned", "as previously reported",
    "as we flagged", "as flagged", "as mentioned", "as a reminder",
    "turning to", "turning now to", "elsewhere in", "meanwhile, over in",
    "it's worth noting", "it is worth noting", "in a development that",
]
CAVEATS = ["headline only", "per a headline", "not in the digest",
           "could not check", "could not verify"]
DAYS = "monday|tuesday|wednesday|thursday|friday|saturday|sunday|yesterday"
OPENER = "here are the biggest news stories and how they connect"


def words(text):
    return len(text.split())


def split_sections(text, names):
    """Return [(section name, body)] using the plain 'Name.' header lines."""
    lookup = {n.lower(): n for n in names}
    sections, current, body = [], None, []
    for para in [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]:
        key = para.rstrip(".").lower()
        if key in lookup and len(para.split()) <= 8:
            if current is not None:
                sections.append((current, "\n\n".join(body)))
            current, body = lookup[key], []
        elif para.lower().startswith(OPENER):
            if current is not None:
                sections.append((current, "\n\n".join(body)))
            current, body = "Big picture", [para]
        else:
            if current is None:
                current = "(before the first section)"
            body.append(para)
    if current is not None:
        sections.append((current, "\n\n".join(body)))
    return sections


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "briefing.txt"
    cfg = json.load(open("config.json", encoding="utf-8"))
    text = open(path, encoding="utf-8").read().strip()
    low = text.lower()
    must, drift = [], []

    # --- mechanical -------------------------------------------------------
    digits = re.findall(r"[^\n]*\d[^\n]*", text)
    if digits:
        must.append(f"{len(digits)} line(s) contain digits; spell every number out. "
                    f"First: '{digits[0][:70]}'")
    if re.search(r"(\*\*|^#+\s|^\s*[-*]\s)", text, re.M):
        must.append("markdown found (**, #, or a bullet); this is read aloud, use plain sentences")
    if not text.endswith((".", "?", "!", '"')):
        must.append("the brief stops mid-sentence; finish the final section")

    # --- length -----------------------------------------------------------
    total = words(text)
    w = cfg["words"]
    if total > w["max"]:
        drift.append(f"{total} words, over the {w['max']} limit; cut the weakest items, never the analysis")
    elif total < w["min"]:
        drift.append(f"{total} words, under the {w['min']} floor; a section is probably missing")

    # --- sections ---------------------------------------------------------
    budgets = {s["name"]: s for s in cfg["sections"]}
    sections = split_sections(text, list(budgets))
    found = [n for n, _ in sections]
    for name, body in sections:
        if name not in budgets:
            must.append(f"text appears {name}; every paragraph belongs under a section name")
            continue
        n, budget = words(body), budgets[name]["budget"]
        allowed = max(int(budget * 1.4) + 15, budget + 30)
        if n > allowed:
            drift.append(f"{name} runs {n} words against a budget of {budget}; "
                         f"bring it under {allowed}")
    for name, s in budgets.items():
        if s["tier"] == "guaranteed" and name not in found:
            if name == "Weather" and not cfg.get("weather", {}).get("enabled", True):
                continue
            drift.append(f"guaranteed section '{name}' is missing; it needs at least one line")
    order = [n for n in budgets if n in found]
    if [n for n in found if n in budgets] != order:
        drift.append("sections are out of order; follow the order in config.json")

    weather = dict(sections).get("Weather")
    if weather:
        sentences = [x for x in re.split(r"(?<=[.!?])\s+", weather) if x.strip()]
        if len(sentences) > 3:
            drift.append(f"weather runs {len(sentences)} sentences; the shape is the next "
                         "three days in one sentence, then ONE joke")

    # --- habits that crept in before --------------------------------------
    for phrase in BANNED:
        if re.search(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", low):
            drift.append(f"banned phrase '{phrase}'; say the thing directly")
    callbacks = len(re.findall(rf"\bon ({DAYS}),? (we|i) (said|mentioned|reported|noted|flagged)|"
                               rf"\b({DAYS}) we (said|mentioned|reported|noted)", low))
    limit = cfg.get("memory", {}).get("max_callbacks", 2)
    if callbacks > limit:
        drift.append(f"{callbacks} look-backs to earlier episodes; keep the best {limit}")
    caveats = sum(low.count(c) for c in CAVEATS)
    if caveats > 2:
        drift.append(f"{caveats} hedged items ('headline only', 'could not check'); "
                     "drop claims the brief cannot stand behind instead of airing them with caveats")

    print(f"{total} words; sections: " + ", ".join(f"{n} {words(b)}" for n, b in sections))
    for m in must:
        print("MUST FIX:", m)
    for d in drift:
        print("DRIFT:", d)
    if not must and not drift:
        print("All checks passed.")
    return 1 if (must or drift) else 0


if __name__ == "__main__":
    sys.exit(main())

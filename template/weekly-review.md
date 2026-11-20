# The weekly self-review

Once a week the briefing checks itself, so that nobody has to. The aim is
to pull the briefing BACK to its agreed shape, never to move the shape.

Hand the whole job to one helper (subagent) on the Sonnet model, with this
file as its instructions. The main session only relays the result.

## The fence

**May change without asking:**

- `this-week.md` - the correction note the drafter reads every morning.
- `feeds.txt` - only to repair or switch off a source that has been broken
  for a week.
- `config.json` `pronunciations` - when the listener has reported a
  mispronounced word.

**Must never change without the listener saying so:** `profile.md`,
`house-style.md`, the files in `examples/`, and anything else in
`config.json` (lengths, sections, budgets, voice, timing). If the review
thinks one of those is wrong, it says so in its message and waits.

## The review

1. `git checkout main && git pull origin main`. Read `house-style.md`,
   `profile.md`, `config.json`, the files in `examples/`, the past week in
   `archive/`, the last ten lines of `run-log.md`, and the current
   `this-week.md`.

2. **Measure the week.** Run `python3 tools/check_brief.py archive/<day>.txt`
   on each archived day and note the word count, the per-section counts
   and any DRIFT lines.

3. **Compare with the standard.** Against the `examples/` episodes and
   `house-style.md`, look for anything present on three or more days:
   - a section regularly over its budget, or a guaranteed one missing;
   - the weather growing beyond two sentences, or a joke format repeating;
   - the big-picture opening missing on days the stories clearly connected,
     or forced on days they did not;
   - items that state a thing happened without the payload;
   - analysis squeezed out of Economy and markets;
   - look-backs that are habit instead of news ("as mentioned..."), or the
     same continuing story re-explained every day;
   - hedged items ("headline only") aired instead of dropped;
   - anything the listener asked for in `profile.md` that never appears.
   Also check whether last week's corrections worked. If one made things
   worse, remove it.

4. **Write the correction note.** REPLACE `this-week.md` entirely with at
   most six short lines, each a specific instruction with the evidence in
   brackets:

       - Hold Conflict to one line per development (ran 210-260 words on
         four days against a budget of 160).

   If the week was clean, the note says only: `Nothing to correct.`

5. **Repair sources.** From `run-log.md`, list every source that failed
   on five or more of the past seven days. For each:
   - Diagnose before replacing. Run `python3 tools/test_feed.py "<url>"`.
     If it works here, the publisher is blocking GitHub or was briefly
     down: leave it alone.
   - If it has moved, fix the address.
   - If it is dead, find a replacement, test it the same way, and swap it
     in only if the test says GOOD. Otherwise put a `#` in front of the
     dead line.
   - A watchlist search that is merely quiet is not broken: flag it `RARE`.

6. **Commit and push** as `Weekly review YYYY-MM-DD`, with one line per
   change in the commit message. Add a line to `run-log.md`:
   `- YYYY-MM-DD - REVIEW - <what was corrected, what was repaired>.`

7. **Report** to the main session in under 100 words.

## What the main session tells the listener

Nothing, unless one of these is true - then one short message:

- two or more days were missed this week (say why, if the log shows it);
- a source the listener asked for by name is dead and has no replacement;
- the review believes a fenced file should change (say what and why, and
  ask for a yes).

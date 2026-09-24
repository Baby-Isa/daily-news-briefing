# Daily run - the working instructions

This is the checklist the daily Routine follows. The Routine fires into the one
long-lived session that has this repository attached (see HANDOFF.md section 8e
for why), and that session hands the work to two subagents so its own context
stays small:

- **PART A** is done by a DRAFTING subagent.
- **PART B** is done by a separate PUBLISHING subagent, which checks the draft
  independently before anything is pushed.

The main session's own job is only: run `date -u`, launch Part A, launch Part B,
and report. Edit this file to change how a day runs - no Routine update needed.

---

## PART A - DRAFT (drafting subagent)

Working copy: `/home/user/daily-news-briefing`, branch `main`. Run
`git pull origin main` first. Do NOT commit or push - Part B does that.

1. Read these IN FULL before anything else. They are the system's entire memory.
   - `briefing-prompt.md` - the AUTHORITATIVE spec. Overrides anything here.
   - `story-threads.md` - ongoing threads, with their own prune/revive conditions.
   - `aired-items.md` - every consumer item already broadcast, the refused list,
     and the weather angles already used.
   - `HANDOFF.md` sections 3, 5 and 8a - the files, the failures that have cost
     whole days, and what earlier runs learned.
2. Check `digest.txt`'s header. If it is not today's date, rebuild it:
   `python3 build_digest.py` in the background (it exceeds the two-minute
   foreground limit), then confirm the header. A local rebuild's failure list is
   unreliable - this container's IP is blocked by some publishers.
3. Read `digest.txt` in CHUNKS with offset until the literal line
   "End of full digest." It is two-tier: the "ALSO IN <LANE>" headline-only lists
   must be read too, saying only what a headline supports. Lane names describe the
   FEED, not the topic.
4. Note today's weekday and the Editorial Picks rotation (spec section 13), the
   WEATHER block, the SOURCES THAT FAILED block verbatim, and any thread whose
   prune or revive condition has come due - handle each by its own stated terms.
5. Draft `briefing.txt` (full replacement; read the current one first for format).
   - Hard word limit and ceiling as the spec states. Count before finishing.
   - EVERY ITEM CARRIES ITS PAYLOAD outranks brevity: recover a missing fact by
     web search where the spec permits, say the gap out loud, or cut the item.
   - Zero digits - this is text-to-speech input.
   - No markdown, bullets or headers beyond the plain section-name lines.
   - Nothing from `aired-items.md` re-run without a genuinely new fact.
   - No weather angle used in the past week; the two worn constructions sparingly.
   - Nothing asserted that has not happened yet.
6. Update `story-threads.md` and append today's items and weather angle to
   `aired-items.md` in their existing formats.
7. Report back in under 250 words: word count, web searches, what the gadgets
   section ran and why each cleared `aired-items.md`, thread changes, weather
   angle, and anything left out or unverified.

---

## PART B - VERIFY, PUBLISH, CONFIRM (publishing subagent)

Working copy: `/home/user/daily-news-briefing`, branch `main`. Do not rewrite the
brief's content - check it, and if a check fails, fix only the mechanical fault
(a stray digit, a markdown mark) or report it.

1. Verify the draft yourself; do not take the drafter's word:
   - `wc -w briefing.txt` against the spec's hard limit.
   - `grep -coE "[0-9]" briefing.txt` must print 0.
   - No markdown (`**`, `##`, leading `- ` or `* `).
   - The closing failed-sources line matches the digest's SOURCES THAT FAILED
     block, and is absent entirely when that block says none failed.
   - `git diff --stat` shows `briefing.txt`, `story-threads.md` and
     `aired-items.md` all changed. All three must move together.
2. Append one line to `run-log.md` under `## Log`, newest first:
   `- YYYY-MM-DD — OK — <words>, <one line on the day>.` (PARTIAL or FAILED with
   the reason if something did not pass.)
3. `git add briefing.txt story-threads.md aired-items.md run-log.md`, commit as
   `Briefing YYYY-MM-DD`, `git pull --rebase origin main`, then
   `git push origin main`. This triggers the podcast render.
4. Confirm the render. GitHub Pages' CDN lags, so check the branch itself:
   poll `git fetch origin gh-pages && git log -1 --format=%cd origin/gh-pages`
   every 45 seconds (never one long sleep) until it shows today, then:
   - `git ls-tree --name-only origin/gh-pages` must list exactly `audio`,
     `feed.xml`, `index.html`. Anything else (`models`, `_site`, `_tts_work`) is a
     leaked TTS model - report it loudly.
   - `git ls-tree origin/gh-pages:audio | grep <YYYY-MM-DD>` shows today's mp3.
   - `curl -fsS https://raw.githubusercontent.com/Baby-Isa/daily-news-briefing/gh-pages/feed.xml`
     contains today's title; read its `<itunes:duration>`.
   A healthy render lands five to eight minutes after the push.
5. Report back in under 150 words: pushed commit hash, word count, episode
   duration, gh-pages clean or not, anything that failed.

---

## If anything stops the run

- **Rate limit on a subagent:** do not retry at once and do not abandon the day.
  Schedule a wakeup with `send_later` for just after the reset the error names,
  BEFORE ending the turn, and resume then. 31 August and 6 September were lost for
  lack of this.
- **Anything else before the push:** still append a FAILED line to `run-log.md`
  saying exactly what happened, and commit and push that file on its own. A failed
  day must leave a trace.
- **If you changed how the system runs** (a feed, a budget, a rule), write it into
  the repository before finishing. The reasoning is lost otherwise.

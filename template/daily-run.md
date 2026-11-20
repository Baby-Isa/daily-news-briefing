# The daily run

The scheduled task fires into the one long-lived Claude session that set
this briefing up. That session does almost nothing itself: it checks the
clock, starts the news build, and hands the work to two helpers
(subagents), so its own conversation stays small for months.

- **Part A** is done by a DRAFTING helper.
- **Part B** is done by a separate PUBLISHING helper, which checks the
  draft independently before anything goes out.

Run both helpers on the Sonnet model: it writes the brief well and uses
far less of the listener's allowance. Change how a day runs by editing
this file; the scheduled tasks never need touching.

---

## Step 1 - Clock, branch, guard (main session)

1. Run `date -u` and say the real time. Never infer it from the fact that
   the prompt arrived: a delayed firing looks identical to a punctual one.
2. Run `git checkout main && git pull origin main`. A rebuilt container
   can come back on the session's own branch, and work done there
   publishes nothing.
3. Work out today's date in the listener's time zone (`config.json`,
   `timezone`): `TZ=<zone> date +%F`.
4. **Guard.** Run `git log origin/main --format=%s -30`. If a commit named
   exactly `Briefing <today>` is there, today is already published: stop
   and say nothing more than "Already published today."
5. If `config.json` says `"days": "weekdays"` and today is Saturday or
   Sunday there, stop.
6. If several firings have arrived at once (the session was asleep), run
   TODAY only. Tell the drafting helper the date of the last aired
   briefing (the newest file in `archive/`), and tell the publishing
   helper to add a FAILED line to `run-log.md` for each missed day.

## Step 2 - Fresh news (main session)

Start the news build on GitHub, whose servers are not blocked by
publishers the way this container is: use the GitHub Actions tool, method
`run_workflow`, this repository's owner and name, `workflow_id`
`digest.yml`, `ref` `main`.

Then run, in the foreground with a ten-minute limit:

    python3 tools/wait_for_digest.py

Exit 0 means a fresh `digest.txt` is in the working copy. If the tool is
missing, the trigger fails, or the wait exits 1, build here instead:
`python3 build_digest.py` in the background (about four minutes), and tell
both helpers that the failed-sources list from a local build is not
reliable.

## Step 3 - Launch Part A, then Part B, then report (main session)

Give each helper the date, anything from step 1.6, and the instruction to
follow its part of this file exactly. When Part B reports, check for
yourself: `git log -1 --format='%s %cd' origin/main` and
`git log -1 --format=%cd origin/gh-pages`.

Then report in two or three lines: episode live, length, anything that
went wrong. If nothing went wrong, that is the whole message. Message the
listener at more length only if something needs their hand.

---

## PART A - DRAFT (drafting helper)

Working copy: this repository, branch `main`. Do NOT commit or push.

1. Read these in full before anything else:
   - `house-style.md` - how to write. Authoritative on style.
   - `profile.md` - what this listener wants covered.
   - `config.json` - word limits, section names, order, budgets and tiers.
   - every file in `examples/` - the standard to match.
   - `this-week.md` - corrections from the last weekly review. Apply them.
   - `editor-note.md`, if it exists: a one-off instruction from the
     listener that applies only on the date at its top.
   - every file in `archive/` - what was actually said in the past week.
     Use it for facts and continuity, never as a style model.
   - `threads.md` - things to watch for.
2. Check `digest.txt`'s header shows today's date. Read it in chunks to the
   line beginning "End of full digest.", including the "ALSO IN" lists, the
   WEATHER block and the SOURCES THAT FAILED block.
3. Write `briefing.txt` (a full replacement), following `house-style.md`.
   Count the words. Then run `python3 tools/check_brief.py` and fix
   everything it lists before you finish.
4. Rewrite `threads.md` IN FULL (do not append). Keep its header. At most
   twelve entries, newest first, each one line in exactly this form:

       - [expires YYYY-MM-DD] Topic | said Thu 19 Nov: what the brief said | watch: what would change it

   Set the expiry seven days after the entry was last updated, or the day
   after a dated event it is waiting for, whichever is later. Drop
   anything resolved.
5. Report back in under 200 words: word count, what you searched the web
   for, which earlier episodes you linked back to, every failed source,
   and anything you left out because you could not stand behind it.

---

## PART B - CHECK, PUBLISH, CONFIRM (publishing helper)

Working copy: this repository. Confirm `git branch --show-current` prints
`main`; if not, stop and report. Do not rewrite the brief's content.

1. Run `python3 tools/check_brief.py`.
   - MUST FIX lines: fix them yourself if mechanical (a stray digit, a
     bullet mark). Otherwise report and stop.
   - DRIFT lines: if the drafting helper has not already had one attempt
     at them, report them back so the main session can send the draft back
     ONCE. If they remain after that, publish anyway and record them in the
     run log. A style fault never costs a day.
2. Run `python3 tools/housekeeping.py`. It archives today's brief, deletes
   old archive files and caps `threads.md`.
3. Add one line to `run-log.md` under `## Log`, newest first:
   `- YYYY-MM-DD - OK - <words> words; <any DRIFT>; failed sources: <list or none>.`
   Use PARTIAL or FAILED with the reason if something did not pass.
4. Commit and push:

       git add briefing.txt threads.md run-log.md archive
       git commit -m "Briefing YYYY-MM-DD"
       git pull --rebase origin main
       git push origin main

   The commit name must be exactly `Briefing YYYY-MM-DD` (the listener's
   local date): the guard and the backup check look for it. The push
   starts the audio render.
5. Confirm the render with ONE command, in the FOREGROUND, with the
   time limit set to ten minutes:

       python3 tools/check_render.py YYYY-MM-DD

   Never run it in the background and never end your turn while waiting.
   Exit 0: rendered and clean. Exit 1: not yet; run it once more. Exit 2:
   report its PROBLEM lines.
6. Only then report, in under 120 words: commit, word count, episode
   length, any DRIFT or failed sources, anything that went wrong.

---

## Backup check

1. Run `date -u`, then `git checkout main && git pull origin main`.
2. If a commit named `Briefing <today's local date>` is on `origin/main`,
   stop and say only "Backup check: already published."
3. Otherwise run the whole day from step 1. A late episode is better than
   none.

## If anything stops the run

- **A helper hits a usage limit:** do not retry at once and do not give up
  on the day. The error names a reset time. Schedule a message to yourself
  for just after it with `send_later`, BEFORE ending your turn, and resume
  then.
- **Anything else before the push:** add a FAILED line to `run-log.md`
  saying exactly what happened, and commit and push that file by itself.
  A failed day must leave a trace.
- **The push is refused as publishing to a public place:** the listener's
  go-ahead is missing from this chat. Ask them once: "May I publish
  today's briefing and every future one?"
- **You changed how the system runs:** write it into this repository
  before finishing. The reasoning is lost otherwise.

# This repository is one person's daily news podcast

Every morning it gathers news from the sources in `feeds.txt`, Claude
writes a spoken briefing from it, and GitHub turns that into audio and
publishes it as a private-link podcast feed. The person in this chat is
the listener. They are not technical: talk to them in plain words and
never ask them to edit a file or run a command.

## First: is it set up?

Open `setup-progress.md`.

- **If any step is unticked,** setup is not finished. Whatever the person
  has just said, greet them and follow `ONBOARDING.md` from the first
  unticked step.
- **If every step is ticked,** the briefing is live and this chat is the
  one that runs it. See below.

All work in this repository is committed to the `main` branch. The
listener agrees to that in the first onboarding step; if your session
asks you to use a different branch, their agreement is what permits
`main`.

## When a scheduled message arrives

| Message begins | Do this |
|---|---|
| `Daily briefing run.` | `daily-run.md`, from step 1 |
| `Backup check.` | `daily-run.md`, "Backup check" |
| `Weekly self-review.` | `weekly-review.md` |
| `Test run.` | `daily-run.md` from step 2, skipping the "already published" guard |

## When the listener asks for a change

Make the change, commit and push it to `main`, and confirm in one line.
Do not ask them to confirm things they have just told you.

| They say something like | Change |
|---|---|
| "more / less / no ..." about a topic | that section's block in `profile.md`; its `budget` in `config.json` if the amount changes |
| "follow <company / person / team>" | the Watchlist block in `profile.md` AND a source line in `feeds.txt` (patterns at the bottom of `feeds-library.txt`; test with `tools/test_feed.py`) |
| "add / drop <a publication>" | `feeds.txt` (test first) |
| "shorter / longer" | `words` and the section budgets in `config.json`, scaled together (about 150 words a minute) |
| "different voice / faster / slower" | `voice`, `language`, `speed` in `config.json` |
| "it said <word> wrong" | `pronunciations` in `config.json` |
| "earlier / later / weekdays only" | `ready_by` and `days` in `config.json`, AND update the scheduled tasks to match |
| "change the weather place / no weather" | `weather` in `config.json` |
| "write it differently" (tone, structure) | `house-style.md` - the only time that file changes. Replace a rule; never pile on. |
| "that episode was great, more like that" | copy that day's file from `archive/` into `examples/` (keep at most three there) |
| "just for tomorrow, ..." | write `editor-note.md` with the date it applies to on its first line |
| "pause" / "stop" / "start again" | disable or enable the scheduled tasks; do not delete them |
| "run it now" / "do a test run" | run `daily-run.md` from step 2, skipping the "already published" guard. Today's episode is replaced, not duplicated; tell them their app may need a pull-to-refresh. |
| "test it every hour" | create ONE extra scheduled task named `Briefing test (hourly)`, hourly, in this session, with the prompt `Test run. Follow daily-run.md from step 2, skipping the "already published" guard.` Say that each run uses allowance. Delete it when they say "stop testing", and ask whether to stop after six runs. |

After a change to content or style, offer once to re-run today's episode
so they can hear it.

## Where everything is

| File | What it holds | Who changes it |
|---|---|---|
| `profile.md` | what the briefing covers | the listener, through you |
| `config.json` | length, sections and budgets, voice, speed, timing, weather place | the listener, through you |
| `feeds.txt` | the news sources read each morning | you, when asked; the weekly review, for repairs |
| `feeds-library.txt` | optional sources and patterns to copy from | nobody, normally |
| `house-style.md` | how the briefing is written | only on the listener's request |
| `examples/` | approved episodes the drafter imitates | only on the listener's request |
| `this-week.md` | corrections from the latest weekly review | the weekly review only |
| `threads.md` | up to twelve things to watch for | the daily run (rewritten whole) |
| `archive/` | the last seven briefings as aired | `tools/housekeeping.py` only |
| `run-log.md` | one line per day: what happened | the daily run |
| `daily-run.md`, `weekly-review.md` | the run sheets | rarely |
| `build_digest.py`, `build_podcast_episode.py`, `tools/`, `.github/` | the machinery | leave alone unless something is broken |

## If something is broken

Read `run-log.md` first; it records what actually happened each day.

- **No episode today:** check the clock, then follow "Backup check" in
  `daily-run.md`. If the cause was a usage limit, tell the listener plainly
  that the briefing paused because their Claude allowance ran out and will
  resume when it resets.
- **The episode sounds wrong** (a mispronounced name, too long, a missing
  section): fix the cause in the files above, do not just patch today's
  text.
- **A source keeps failing:** diagnose before replacing
  (`weekly-review.md`, step 5).
- **The podcast address stopped working:** check
  `https://<owner>.github.io/<repository>/feed.xml`; if it returns 404,
  the Pages setting in step 7 of `ONBOARDING.md` has been switched off.

Never run two chats with live scheduled tasks for this repository: they
would race to publish. If this chat is ever replaced, create the tasks in
the new one, confirm them, and only then delete the old ones.

# Brief for Fable: the daily news briefing, as it actually runs

Written 20 November 2026 by the Claude session that runs the daily pipeline
(`session_014xb3kPhnNdAY7g7h54eHm1`). The repository tells you how the system
is *meant* to work. This document tells you how it has *actually* behaved over
the last four weeks, what changed in the last few days, and what the owner now
wants your help with.

Read this first, then `HANDOFF.md` (especially sections 1-5, 8e and 8f) and
`daily-run.md`.

---

## 0. Your job

The owner made this podcast for themselves. On 19 November they shared one
episode with a senior contact, an executive or managing partner at a
private-equity firm. **He liked it, wants to use it, and wants to play around
with it himself.**

The owner wants your help to **plan** how to do that. Planning is the job, not
building yet. Specifically:

- What is the best way to give him his own version (his interests, his length,
  his tone) with the least friction for a busy, non-technical senior person?
- What should the owner offer him first, and what can wait?
- What has to be built, and in what order?
- What will it cost him and the owner (money, Claude usage, time), and what
  could break?

This contact matters to the owner professionally. The first impression has to
be smooth. A half-working setup handed to him is worse than none.

**Do not touch the live pipeline while planning.** That means no edits to
`briefing.txt`, `daily-run.md`, `briefing-prompt.md` or the workflows, and no
changes to the scheduled tasks. The owner's own daily episode depends on them.
Any build work for the contact should happen in a separate repository unless
the owner decides otherwise.

---

## 1. What the thing is, in one paragraph

Every morning, about 160 RSS and Google News feeds are pulled into a news
digest. A Claude session reads the digest and writes a spoken brief of about
nine minutes, following a long personal spec (`briefing-prompt.md`). A free,
offline text-to-speech model (Kokoro, voice `bf_isabella`) turns the brief into
an mp3. The mp3 is published as a podcast feed on GitHub Pages:
`https://Baby-Isa.github.io/daily-news-briefing/` (the RSS feed is `feed.xml`).
The owner listens in a podcast app. The repository is `Baby-Isa/daily-news-briefing`.

There are **no API keys and no paid services** apart from the owner's Claude
subscription. The digest build and the audio render run on free GitHub
Actions. Hosting is free GitHub Pages.

---

## 2. The real daily timeline (all times UTC; London is UTC+0 in winter)

| Time (approx.) | What happens | Where |
|---|---|---|
| 04:37, 05:23, 06:11 | GitHub cron attempts to build the digest. They are often late or dropped, so an external pinger also fires about 06:00. Whichever lands first builds; the rest no-op. | `.github/workflows/digest.yml` |
| ~06:03 | `digest.txt` committed ("Digest YYYY-MM-DD"): about 1,100 stories, about 470 in full and the rest as headlines only. | GitHub Actions |
| ~06:39 | The daily scheduled task fires into the long-lived Claude session. | trigger `trig_01Y59gAE8otKZrSYA6CDKVNS`, cron `30 6 * * *` (actually fires about 06:39) |
| 06:40-06:44 | A **drafting subagent** (Sonnet) does Part A of `daily-run.md`: reads the spec, the memory files and the digest, and writes `briefing.txt`. It also updates `story-threads.md` and `aired-items.md`. Takes 3-7 minutes. | the session |
| 06:44-06:50 | A **publishing subagent** (Sonnet) does Part B: independent checks (word count, zero digits, no markdown, failed-sources line), a `run-log.md` line, then commit and push to `main`. It then runs `tools/check_render.py` until the episode is live. | the session |
| ~06:44 | Pushing `briefing.txt` triggers the render workflow. | `.github/workflows/podcast.yml` |
| ~06:48-06:50 | Kokoro renders the mp3. `gh-pages` is rebuilt with only `audio/`, `feed.xml` and `index.html`, and the episode is live. | GitHub Actions |
| 06:50 | The session reports to the owner in three or four lines. | the session |
| 09:07 | The backup check fires. If today's "Briefing" commit exists it does nothing; otherwise it runs the whole day. | trigger `trig_01QrACsoLLyo9Rr2dK4h5CnM` |

A normal day costs the owner two Sonnet subagent runs. The drafter uses about
250-390k tokens and the publisher about 60-70k. The main session itself stays
small.

---

## 3. What four weeks of running it actually looked like (24 Oct to 20 Nov)

**Reliability.** Every day from 27 October to 20 November published: 25 days in
a row, with episodes live by about 06:50 UTC. The last failures were 24-26 October. On those
days the owner's Claude usage limit ran out, the session did not wake, and the
scheduled firings queued up and all arrived the next morning together. That
pattern is expected roughly weekly when the owner runs low on usage. It is
**not** a pipeline fault and should not be designed around (owner's
instruction, recorded in HANDOFF 8f).

**Session migration (27 October).** The scheduled tasks moved from the old
session to this one. On the first morning, Auto mode's safety classifier
**refused to let the session publish** ("Create Public Surface"), because a
push to `main` publishes a public podcast. That `.claude/settings.json` was
identical made no difference. What fixed it was the owner writing in the chat:
"Publish today's brief and all future briefs." After that, every day
published without friction. **Any new session, including one built for the PE
contact, will hit the same block on its first morning unless its owner gives
that go-ahead in its chat first.**

**Recurring quality patterns** (from the subagents' daily reports):

- **Word count always sits just under the 1,450 cap** (1,239-1,447). The spec
  says "cut narrative, never analysis". In practice the drafter fills to the
  cap.
- **Weather drifted into extended conceits:** "the box set", "the gym",
  "free trial", "the heating invoice", "piggy bank", "screensaver",
  "last orders". `aired-items.md` tracks which angles have been used so they
  don't repeat, which in practice pushed the drafter toward ever more
  elaborate metaphors. The owner found these long and not funny.
- **Web search is often stale or empty.** Typically 3-8 searches a day, many
  returning 2025 or older results. The drafter then falls back to "headline
  only" or says the gap out loud on air. Caveated, headline-only items appear
  most days.
- **Corrections of yesterday's brief** appear about every other day (a wrong
  weekday, a sports result, a dollar figure, a premature "seeking" that became
  "dismissed"). The drafter handles these honestly, on air.
- **The memory files have grown too large.** `story-threads.md` is about 160 KB and
  `aired-items.md` about 107 KB. From about 10 November the drafter sometimes
  read them only in part (newest entries, truncated lines). That raises the
  risk of repeating stale items. Archiving older entries was proposed to the
  owner, not yet answered.
- **Feeds fail occasionally:** Google News OriginTrail went stale for 46+ days, Green
  Queen returned 403 once, the Google News acquisitions feed was rate-limited
  (429) once, and CSM Culture failed once. The weather source failed once (503); the drafter
  fetched met.no directly. OriginTrail needs replacing (raised, not yet
  answered).

**When the news comes in** (measured 19 November, nine briefs, about 286
items matched back to digest timestamps):

| When published (UTC) | Share of items in the brief |
|---|---|
| Same day, 03:30-06:00 | 16% |
| Same day, 00:00-03:30 | 16% |
| Previous day, 18:00-24:00 | 34% |
| Previous day, 12:00-18:00 | 20% |
| Previous day, before 12:00 | 10% |
| 2+ days old | 3-4% |

About two-thirds of each brief is the previous day's news. A real third comes
in overnight (UK papers, embargoed releases, the Asian working day). This
matters if anyone wants an earlier episode: drafting at 03:30 UTC loses about
16% of the input.

---

## 4. The 19 November episode (the one the PE contact heard)

The owner felt the brief had gone flat and was too heavy on conflict and
politics, with long weather bits and not enough insight. The aim was one
excellent episode to share, without redesigning the system.

**What was done:**

1. **`editor-note.md`** (in the repo; applies to 2026-11-19 only).
   `daily-run.md` now tells the drafter to read `editor-note.md` if it exists
   and to apply it only on the date at its top. The note asked for:
   - about 1,150 words instead of 1,450;
   - weather as today plus the next two days, with short practical needling
     jokes and no conceits;
   - a "how it connects" passage straight after the weather, stitching the
     day's stories into one argument (for example how the midterms and the
     Iran war constrain the US response, and what Tehran may read into it);
   - one tight line per conflict or politics development, and headline-only
     claims dropped rather than caveated;
   - the economy analysis protected (named theory where it fits: Phillips
     curve, Taylor rule) with one line on what markets are pricing;
   - M&A led by UK and European mid-market and private-equity deals, with the
     deal logic in a clause.
2. **The owner was in Miami (UTC-5)** and wanted to hear it before London
   morning. So the session:
   - forced an early digest build at 03:20 UTC by dispatching `digest.yml`
     with `force: true` through the GitHub tools (this works and is better
     than building locally, where some publishers block the container);
   - drafted and published at about 03:30 UTC;
   - took the owner's feedback and re-published;
   - forced a second digest build at 05:41 UTC, scanned only the stories
     published since 03:10, and hand-added five items (an IEA energy-security
     warning, the Shenzhen Trump-Xi-Putin summit, Hegseth in Caracas, an IMF
     debt warning, and Deutsche Bank Italy from the FT);
   - put the final version live at **05:47 UTC: 8 min 22 s, 1,254 words**,
     commit `1f6a781`.
3. **The owner's feedback on the early draft:**
   - "Did you speed up the voice? It's very fast." The voice speed had not
     changed; the denser, shorter prose made it sound faster. It is now
     **0.9x permanently** (`build_podcast_episode.py`, `KOKORO_SPEED` default `0.9`).
   - Weather became **two sentences: the next three days plus ONE joke.** The
     owner's model line: "the next three days are clear but cold, the clouds
     look stormy but won't rain, so you'll take the umbrella all three days
     and regret it every time."
   - The first news section opens with **"Here are the biggest news stories
     and how they connect…"**, used only when they really connect, and has no
     header line.
4. **Guard added to the daily scheduled task:** if today's "Briefing" commit
   already exists, it does nothing. This protects hand-finished or early
   episodes from being overwritten. It fired correctly at 06:39 on 19 November.

**20 November reverted to normal** because the editor note was one-off: 1,447
words, conceit weather ("the heating invoice"), no "how it connects" opener.
At 0.9x that runs **9 min 52 s**. The owner has been asked whether to make the
19 November style the permanent default; **no answer yet.** Treat this as an
open decision. The PE contact heard the 19 November style, not the normal one.

---

## 5. Things that are not obvious from the repo

- **The scheduled tasks are bound to one Claude session.** A new chat does not
  run the brief and does not see this conversation. To move them, follow
  HANDOFF 8f. Never run two sessions with live daily tasks, because they would
  race to publish.
- **The owner's go-ahead to publish lives in the chat, not the repo.** See
  section 3.
- **The owner reads reports on a phone and wants them short:** three or four lines a
  day, and decisions put to them plainly.
- **The spec is deeply personal:** Arsenal, Ruislip weather, seven-seater cars,
  Micro Four Thirds cameras, Chainlink, cultivated meat, specific airlines,
  Kenya and Tanzania, a financial-economics background. About 830 lines,
  refined over months by trial and error. HANDOFF section 10's rule, "test the
  replacement against the thing it replaces, on real data", is the culture
  here.
- **Usage limits are the real constraint.** The owner runs out of Claude usage
  early in some weeks, and while that lasts the session doesn't wake. A second
  person's daily runs on the owner's account would compete for the same
  allowance.
- **GitHub Pages is public:** the feed URL and episode text are visible to
  anyone with the link. The repo's own visibility hasn't been checked in this
  session. If it is public, the spec (the owner's interests) is public too.

---

## 6. Options already discussed for the PE contact (12 November)

The session gave the owner this view before the contact had heard anything:

1. **Do not point him at the owner's repo.** It is a personal system full of the
   owner's interests, history and logs.
2. **Template route (self-serve):** a clean template repo with the pipeline, a
   generic placeholder spec, the 187-feed library tagged by topic and region,
   and an `ONBOARDING.md` that Claude follows when he says "set up my
   briefing". It would:
   - interview him (interests, regions, sports, length, tone; a voice note is
     fine);
   - pick feeds from the library and find and test new ones for niche topics;
   - write his spec and render one sample episode;
   - turn on GitHub Pages and create his daily scheduled task.

   Friction:
   - he needs a GitHub account and a paid Claude plan with Claude Code, and
     each daily run uses his allowance;
   - his spec is public on free Pages unless he pays for GitHub;
   - he must give the publish go-ahead in his own chat;
   - he needs a long-lived session for continuity between days.
3. **White-glove route (recommended then for this contact):** "Send me a
   two-minute voice note on what you follow, and it'll be in your podcast app
   by Monday." The owner, with Claude, runs his onboarding, so he never
   touches GitHub. He becomes the template's first real user and the owner
   acts as product owner. Hand over self-serve later if he wants it.

Variants not yet weighed:

- **A second feed from the owner's own pipeline:** a second spec and feed
  folder in a separate repo, run by the same session or a sibling session.
  It's the cheapest to build, but it costs the owner's usage and makes the
  owner responsible for his episode every day.
- **What "play around with it himself" means:** tweaking his own spec
  (topics, length, tone) by chatting with Claude is very different from
  operating the pipeline. Find out which he means before choosing a route.

---

## 7. Questions to put to the owner early

1. What does the contact mean by "play around": change what's in his brief,
   or run and own the whole thing?
2. Whose Claude account pays for his daily runs, and is the owner happy for
   his runs to share the owner's usage allowance?
3. Does he have, or will he create, a GitHub account? Is a public spec
   acceptable to him?
4. What does he want in it? What length, tone and voice? (Kokoro has other
   British and American voices.)
5. How much ongoing involvement does the owner want: a product owner for one
   person, or a repeatable template for more people later?
6. Separately, for the owner's own brief: make the 19 November style permanent?
   Archive the memory files? Replace the OriginTrail feed?

---

## 8. Useful facts and commands

- **Repo files:** `briefing-prompt.md` (spec), `daily-run.md` (the two-part
  checklist), `feeds.txt` (187 lines), `build_digest.py`,
  `build_podcast_episode.py` (TTS; `VOICE`, `SPEED`), `tools/check_render.py`,
  `story-threads.md`, `aired-items.md`, `run-log.md` (one line a day),
  `editor-note.md` (one-off, 19 November), `HANDOFF.md`.
- **Force a digest rebuild:** dispatch `digest.yml` on `main` with
  `force: true`. It lands in about 2-3 minutes. A forced build makes that
  day's later cron attempts no-op.
- **Re-rendering the same date** replaces that day's feed item (same GUID).
  Podcast apps that already downloaded it may keep the old audio; the web page
  always plays the latest.
- **Reading this session's transcript** from another cloud session:
  `list_events` with session id `session_014xb3kPhnNdAY7g7h54eHm1`. It is
  long; ask narrow questions with `kinds` filters.
- **Commits** end with the Claude co-author and session lines. Daily brief
  commits are named exactly "Briefing YYYY-MM-DD", and the backup check
  greps for that name.

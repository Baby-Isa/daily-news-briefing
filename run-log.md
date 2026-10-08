# Run log

One line per day, most recent first. Written by the pipeline itself as close
to its last action as possible, whether the day succeeded or not, so a bad
run leaves a trace here instead of vanishing with the session that hit it.

This file exists because the 22 September run drafted a real episode, then
hit a push failure, and left no record anywhere - not in the repo, not
reliably in the push notification. It was found only because the owner
happened to ask why nothing had arrived. See HANDOFF.md section 8d for the
full diagnosis and fix.

**Read this before trusting a "quiet" day.** No entry for today by the time
you'd expect one is itself a signal - it means either the run has not fired
yet, or it failed before reaching the point where it could write even this.

## Format

`YYYY-MM-DD — STATUS — one line on what happened.`

STATUS is one of: **OK** (episode drafted, verified, pushed, render
confirmed), **PARTIAL** (pushed but one check failed, e.g. render not
confirmed or a source count looked wrong), **FAILED** (did not reach a
pushable state - say why, as specifically as you can: rate limit, a blocked
permission, a subagent error, something else).

## Log

- 2026-10-08 — OK — 1420 words, Holborn and St Pancras by-election, Meloni's resignation threat over her electoral law, the AfD and BSW majority in Saxony-Anhalt, and Arteta's new Arsenal deal; no sources failed.
- 2026-10-07 — OK — 1418 words, Badenoch's youth employer national insurance cut and her Iron Dome walk-back, a seventh arrest over the RAF Fairford threat and Vance's enrichment demand on Iran, Puigdemont's warrant lifted ahead of Spain's election; no sources failed.
- 2026-10-06 — OK — 1437 words, Conservative conference's Britannia Shield air-defence pledge, Brazil's Flavio Bolsonaro edging Lula ahead of a runoff, US B-1 bombers pulled from RAF Fairford over an Iran drone threat, and Spain's snap election; no sources failed.
- 2026-10-05 — FAILED — no brief; the 06:30 Routine firing and the 09:07 backup were both delivered to the session's queue but the session did not wake to run them until 6 October.
- 2026-10-04 — FAILED — no brief; same cause (main and backup firings queued, session did not wake).
- 2026-10-03 — FAILED — no brief; same cause (main and backup firings queued, session did not wake).
- 2026-10-02 — OK — 1413 words, Drumcree talks collapsing, US troops and a third carrier heading for Iran, Putin ruling out a ceasefire, and Morocco's first woman prime minister; no sources failed.
- 2026-10-01 — OK — 1399 words, Burnham floating a rejoin of the EU, Russia's heaviest energy strike in months on Ukraine, the US completing its Iraq withdrawal, and Tennessee's failed execution of Christa Pike; no sources failed.
- 2026-09-30 — OK — 1428 words, Burnham's first conference speech as prime minister, US forces leaving their last Iraq bases, Dangote's Lamu refinery breaking ground, and Hurricane Polo and Indonesia's fires; no sources failed.
- 2026-09-29 — OK — 1439 words, Burnham's first Labour conference speech as leader, Iran's Hormuz talks via Qatari mediators, the Reserve Bank of Australia's fourth hike, and the FAA pausing Seven Three Seven Max Ten certification; no sources failed.
- 2026-09-28 — OK — 1421 words — Five men arrested near RAF Fairford over a
  suspected terror plot with a possible Iran link, Netanyahu's surprise Abu
  Dhabi visit, Serbia's Vucic resigning to shift into the prime minister's
  chair, The Hague convicting four KLA wartime commanders, and Cricket
  Australia chair Mike Baird's resignation over the Big Bash sale; no sources
  failed today.
- 2026-09-27 — OK — 1374 words — Iran's Hormuz reopening offer rejected by
  Trump, Manchester City found guilty on all but one financial misconduct
  charge, BASF-Evonik merger talks, OpenAI's second capable-model pause after
  an agent escaped its test environment, and Burnham's Your First Home
  help-to-buy scheme; no sources failed today.
- 2026-09-26 — FAILED — no brief; the Routine firing (trig_01HhCAjvDB7a7rz5SQUH9Keg) was not delivered to the session until 27 September.
- 2026-09-25 — PARTIAL — 1457 words (7 over the 1,450 hard limit, within the
  1,500 real ceiling; not a mechanical fault so left as drafted) — Iran's
  seven-day Hormuz ceasefire offer, Trump-Xi summit truce extended to 10
  January with no tariff deal, Netanyahu's isolation deepening ahead of
  Israel's 27 October election, UK mortgage rates topping 7% for the first
  time in 20 months, and George Lucas's Museum of Narrative Art opening in
  LA; no sources failed today.
- 2026-09-24 — OK — 1450 words, evening publish (recovered from the morning
  automated failure below) covering Meta's Vision Pro-rivalling VR glasses,
  an FDA panel backing Grail's multi-cancer blood test, and Anthropic's
  Claude reportedly finding a CRISPR-like gene-editing system; no sources
  failed today.
- 2026-09-24 — FAILED (automated run), recovered by hand in the evening —
  The fresh session fired at 06:41 UTC, stopped after two and a half minutes
  and one dollar, and wrote nothing, not even this line. The add_repo step
  added on the 23rd did not give it push access. Fresh-session mode has now
  failed three times out of three and is ABANDONED. The Routine fires into
  the long-lived session that has the repo attached, with subagents doing the
  work (HANDOFF.md section 8e, daily-run.md). Today's episode was produced
  through that new path as its first test.
- 2026-09-23 — FAILED, recovered by hand — RESOLVED. Fresh session fired at
  06:41 UTC, drafted a real 1,420-word brief, then hit `git push` refused by
  the proxy: "Baby-Isa/daily-news-briefing is not in this session's
  authorized repository set" (a 403). Root cause: a fresh session starts
  with no repository attached, and nothing in the Routine prompt ever called
  `add_repo` to attach one with push access - the 22 September permission
  theory was wrong, never actually triggered by either failure. Found by
  reading the session's own transcript directly in the Claude Code app
  (screenshotted by the owner), which no tool available to this session
  could do. Fixed: step 1 of the Routine prompt now calls `add_repo(owner:
  Baby-Isa, repo: daily-news-briefing, access: push)` before anything else,
  every firing. See HANDOFF.md section 8d for full detail. Recovered by hand
  the same morning; episode published, 8:57 duration.
- 2026-09-22 — FAILED, recovered by hand — Fresh session did real drafting
  work (21 min, $5.25) but never pushed. This file did not exist yet, so
  nothing was written at the time; reconstructed after the fact from
  `get_session` data. Root cause: Auto mode auto-denies a first-time `git
  push` with no prior approval and no human present to grant one. Recovered
  the same day in an interactive session and fixed via `.claude/settings.json`
  (see HANDOFF.md section 8d). This log did not exist to catch it - it exists
  now so the next failure, whatever kind, does not need to be reconstructed
  by hand.

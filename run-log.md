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

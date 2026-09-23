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

- 2026-09-23 — FAILED, recovered by hand — Fresh session fired at 06:41 UTC,
  ran for seventeen minutes, spent seven dollars and around a hundred seventy
  thousand tokens on real work (session cse_01SYbgx6tnh2LzMzVm9e8KT2, status
  IDLE/REVIEW_READY), and again pushed nothing: no Briefing commit, and no
  run-log.md entry either, meaning it did not even reach step 12's fallback
  logging. Written retroactively from the owner's account, not by the session
  itself, since that step did not run. permission_mode was "auto" throughout
  (permission_mode_seq: "1" - never switched, unlike 22 September where a
  human happened to intervene). The 22 September fix
  (`.claude/settings.json` granting `Bash(git push *)`) was present in the
  repo before this session started and should have been pulled at step one,
  so either that fix did not actually resolve the push block, or today's
  failure has a different cause entirely - a stuck render check, a subagent
  error, something else. Could not be diagnosed further: the session is not
  reachable for live messaging and no transcript/event-log tool was
  available from this session to inspect what it actually hit. UNRESOLVED -
  see HANDOFF.md section 8d, which will be updated once more is known.
- 2026-09-22 — FAILED, recovered by hand — Fresh session did real drafting
  work (21 min, $5.25) but never pushed. This file did not exist yet, so
  nothing was written at the time; reconstructed after the fact from
  `get_session` data. Root cause: Auto mode auto-denies a first-time `git
  push` with no prior approval and no human present to grant one. Recovered
  the same day in an interactive session and fixed via `.claude/settings.json`
  (see HANDOFF.md section 8d). This log did not exist to catch it - it exists
  now so the next failure, whatever kind, does not need to be reconstructed
  by hand.

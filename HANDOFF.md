# Operating handbook: the daily briefing and podcast

Written 7 September 2026, to hand this project from the Claude session
that built it (`session_01EQuGkzqBpFS9VvKo7EMbu9`, about a month old and
getting expensive to run) to a fresh one.

Read this file first. Then read `briefing-prompt.md`, which is the
authoritative specification for the brief itself and outranks this file
on anything to do with what the brief says or how it reads. This file is
about running the machine, not about writing.

---

## 1. What the thing is

Every morning a podcast episode appears in the owner's podcast app: a
tightly written news brief, about nine and a half minutes, read by a
synthetic British voice. It is assembled from ~159 RSS feeds and shaped
by a long specification that has been tuned daily since roughly July.

Nothing about it is interactive. The owner does not want to talk to it.
They want to wake up and press play.

## 2. The chain, in order

    05:xx UTC   cron-job.org POSTs workflow_dispatch to digest.yml
                (currently 06:03 UTC - see section 6)
        |
    ~3 min      digest.yml runs build_digest.py, fetches ~159 feeds,
                writes digest.txt (~275KB), commits it to main
        |
    06:30 UTC   A Claude Routine wakes the drafting session
        |
    ~10 min     The session delegates to a subagent, which reads
                briefing-prompt.md + story-threads.md + digest.txt and
                writes briefing.txt, then updates story-threads.md
        |
    push        Both files commit together as `Briefing YYYY-MM-DD`
        |
    ~5 min      podcast.yml renders briefing.txt with Kokoro TTS and
                force-pushes gh-pages as a fresh orphan commit
        |
    live        https://Baby-Isa.github.io/daily-news-briefing/feed.xml

Everything except the drafting step is automated and reliable. The
drafting step is the fragile one, and it is the reason this file exists.

## 3. Files

| File | What it is |
|---|---|
| `briefing-prompt.md` | The spec. ~780 lines. Authoritative. Read it in full every day; do not skim it or work from memory of it. |
| `feeds.txt` | 159 feeds, `lane \| outlet \| url \| flags`. |
| `build_digest.py` | Fetches, dedupes, caps, renders `digest.txt`. |
| `aired-items.md` | **The second memory file.** Every consumer item that has aired, so a product that ran on Monday is not re-run on Wednesday. Read at the start of every draft and checked item by item. Read its own explanation - it exists because a projector was nearly aired twice. |
| `story-threads.md` | Continuity between days. ~17 live threads, each dated, with recorded prune and revive conditions. Read at the start of every draft, updated and committed at the end. This is the only memory the system has. |
| `digest.txt` | Today's input. Regenerated daily, committed. |
| `briefing.txt` | Today's output. What gets read aloud. |
| `build_podcast_episode.py` | Kokoro TTS + feed.xml generation. |
| `.github/workflows/digest.yml` | Builds the digest. Has a date guard so repeat pings no-op in ~15s. |
| `.github/workflows/podcast.yml` | Renders and publishes. Triggered by any push touching `briefing.txt`. |
| `daily-run.md` | **The working instructions for a day** - Part A for the drafting subagent, Part B for the publishing subagent. Edit this to change how a run works. See section 8e. |
| `.claude/settings.json` | Pre-approves exactly what the pipeline uses so an unattended firing never stalls on a permission prompt. See section 8e. |
| `run-log.md` | One line per day, success or failure, written as the pipeline's last action. The record of what actually happened when nobody was watching - read this first if a day looks wrong, before guessing. |

### Feed flags

Flags go in the fourth `|` field of `feeds.txt`:

- `FULLTEXT` - fetch the article body, not just the summary. These are
  the analysis fuel and are exempt from the per-lane cap.
- `QUIET` - low-volume feed; 168h window and a 45-day stale threshold
  instead of 24h / 7 days.
- `RARE` - publishes irregularly; staleness clock off entirely. Genuine
  fetch and parse errors are still reported.
- `FILTER:a,b,c` - keep only items matching a keyword (title + summary).
- `EXCLUDE:a,b,c` - drop items matching a keyword (**title only**, on
  purpose: the words that mark a how-to appear innocently inside real
  stories' summaries).

`FILTER` and `EXCLUDE` swallow everything after them, so each must be
last on its line and only one can appear per feed.

### The two-tier digest

`digest.txt` is capped at 12 full entries per lane (`MAX_ITEMS_PER_LANE`).
Everything past the cap is **demoted to a headline-only list**, not
deleted, under `ALSO IN <LANE> (n), headline only:`.

This distinction was expensive to learn. The first version of the cap
deleted the overflow. Replaying it against a real 903-item morning
showed it would have lost 75 genuine stories - PC Andrew Harper, a
Minnesota Senate primary, Kioxia/SK Hynix, Tundu Lissu - because **lanes
are assigned by FEED, not by topic**. The South China Morning Post sits
in "East Asia" and carries US politics. Never reason about an item from
the lane it is in; read what it says.

## 4. How to run a day

`daily-run.md` is the operational checklist (section 8e) and is
written to be self-contained. The short version:

1. **Run `date -u` and state the real time.** Never infer it from the
   fact that the prompt just arrived. On 24 August this session woke 8.5
   hours late and reported the run as on-time because nobody looked at a
   clock.
2. Pull `main`. Check `digest.txt`'s header build time. Rebuild only if
   it is a different date or more than ~2 hours old; otherwise use it and
   save four minutes.
3. Read `briefing-prompt.md` in full.
4. Delegate the draft to a general-purpose subagent, with the day's
   rotation, any dated threads falling due, and any failed feeds.
5. Commit `briefing.txt` and `story-threads.md` **together** as
   `Briefing YYYY-MM-DD` and push.
6. Verify the render by **step progression, not elapsed time**.
7. Report: episode live, duration, render time, failed sources, notable
   thread changes.

### Rebuilding locally

`build_digest.py` fetches 159 feeds and takes about four minutes, which
exceeds the 2-minute foreground timeout. Always run it with
`run_in_background: true`.

The container may have lost its Python packages after a restart:
`python3 -m pip install --quiet --user feedparser beautifulsoup4`.

**A local rebuild's failure list is not trustworthy.** This container's
datacenter IP gets blocked by some publishers. On 7 September a local
rebuild reported AllAfrica and PetaPixel as failed while the GitHub
Actions build from the same morning reported zero failures. Check the
Actions-built digest before telling the drafting agent a lane is
unverified.

## 5. The failure modes that have actually cost days

**Rate limits, twice.** 31 August and 6 September were both lost
entirely. The pattern is identical: the drafting subagent hits the
account's weekly limit, the error names a reset time, and the session
goes quiet without scheduling anything, because the failure kills the
thing that was supposed to handle the failure.

If a draft fails on a rate limit: **schedule a wakeup past the named
reset immediately, before doing anything else**, using `send_later`.
Do not retry in place. Do not end the turn without scheduling something.
On 6 September the reset was 27 hours out and the day was simply gone.

**Sleeping through the wake-up.** On 7 September the Routine fired at
06:35 and the session did not respond until 17:17. Both this and the
rate-limit failure get less likely in a fresh session, which is the main
reason for this handover.

**apt in CI.** On 19 August the render hung 26 minutes on a stalled
Ubuntu mirror, then timed out at 5 minutes on a retry. `ffmpeg` is NOT
preinstalled on `ubuntu-latest`. It now comes from a static build
published as a GitHub release asset - same infrastructure the runner
already uses. Do not reintroduce `apt-get` here.

**Publishing the model to gh-pages.** The publish step must
`rm -rf _site _tts_work models` before `git add -A`. This leak has
happened twice.

**Reading elapsed time as progress.** A run whose `updated_at` sits a
few seconds after `created_at` and never moves is **stuck**, not slow.
Pull the job steps. A healthy render does steps 1-9 in under 30 seconds
and then sits in step 10 for four to five minutes.

**Commit messages with embedded quotes** break `git commit -m "..."`.
Use `git commit -F - <<'EOF'` heredocs.

## 6. The external cron

cron-job.org POSTs `workflow_dispatch` to `digest.yml` every morning,
because GitHub's own `schedule` events are unreliable - with a single
trigger, the 2 August run landed 5h43m late and 3 August never arrived.
`digest.yml` also keeps three GitHub cron attempts as a fallback, and
the date guard makes all of them idempotent.

Observed ping times: 04:44 UTC through 5 September, **06:03 UTC from 6
September onwards**. That leaves 24 minutes before the Routine fires.

**Resolved 7 September 2026:** the owner confirmed the cron-job.org
timezone dropdown is set to **UTC**, not Europe/London. So 06:03 stays
06:03 UTC through the 25 October clock change and keeps its existing
margin ahead of the Routine year-round. Nothing to do. (Had it been
London, the job would have started firing at 07:03 UTC - after the
Routine - which degrades gracefully, since the Routine would see a stale
digest and rebuild, but wastes four minutes a day.)

## 7. The self-bound handover (history; the current design is section 8e)

The Routine is **self-bound**: it fires into the session that created
it. That was chosen deliberately - `create_new_session_on_fire` proved
much less reliable. It also means a new session needs its own Routine,
and the old one must be removed or both will fire.

Do this in order:

1. Create the new Routine with `create_trigger`, `cron_expression`
   `"30 6 * * *"`, no `persistent_session_id` (omitting it self-binds),
   `initiation: "human_request"`, and the prompt in section 8 verbatim.
2. Confirm it exists with `list_triggers`.
3. **Only then** delete the old one. As of 21 September 2026 the live
   Routine is `trig_01Ump6g9urpzR8cC2i9RACVC`, bound to
   `session_01U9cR8hx8suZHqMamQ5XLrS`. Confirm the current id with
   `list_triggers` rather than trusting this line, which goes stale at
   every handover.

If step 3 happens first and step 1 fails, the briefing silently stops.

## 8. The Routine prompt, verbatim

Paste this as the `prompt` argument. It is written for a session that
already has the repo checked out and carries its context forward.

```
Daily firing of the news briefing + podcast pipeline, into this same ongoing session (self-bound, not a fresh session).

FIRST: run `date -u` and state the real time. On 24 August a session woke 8.5 hours after the routine fired and the run was briefly reported as on-time because the clock was never checked. Never infer the time from the fact that this prompt just arrived.

0. Read HANDOFF.md if you have not already in this session. It is the operating handbook.

1. In Baby-Isa/daily-news-briefing (checked out at /home/user/daily-news-briefing), checkout and pull main.

2. Check digest.txt's header build time against now. Rebuild only if it is genuinely stale - a different date, or more than about two hours old. An external cron builds it each morning; if that build is recent, USE IT and skip to step 3, which saves a four-minute rebuild. If you must rebuild: run `python3 build_digest.py` in the background (it fetches ~159 feeds and exceeds the 2-minute foreground timeout), wait, confirm the header shows today, then commit as `Digest YYYY-MM-DD` and push. Note that a LOCAL rebuild's failure list is unreliable - this container's IP is blocked by some publishers - so check the Actions-built digest before calling a lane unverified.

3. Read briefing-prompt.md in full. It is the authoritative spec and it overrides anything in this prompt. Do not carry instructions from here that contradict it.

4. Delegate reading digest.txt and drafting to a general-purpose subagent. Tell it to:
   - Read briefing-prompt.md in full and follow it exactly; it is authoritative.
   - Respect the hard word limit and ceiling the spec states, and count words before finishing.
   - Treat "EVERY ITEM CARRIES ITS PAYLOAD" as outranking brevity: recover a missing fact by web search where the spec permits, or say the gap out loud, or cut the item. Never gesture at significance.
   - Open with weather in the spec's comedic register, following the spec's CURRENT weather rule. Do NOT ask for all five days named individually; that requirement was withdrawn on 12 August and the spec now wants today in detail, the week as a trend, and any day that breaks the pattern.
   - Read digest.txt in chunks to "End of full digest."; it is two-tier, so read the "ALSO IN <LANE>" headline-only lists too, saying only what a headline supports.
   - Remember lane names describe the FEED, not the topic.
   - Read story-threads.md first, reference advancing threads explicitly, act on any thread whose recorded prune or revive date has arrived, and update the file before finishing.
   - Read aired-items.md and check EVERY gadget, camera, projector and car item against it before using one. A restatement is not news; a genuine follow-on - a missing price now published, a date confirmed, a reversal, a rumour becoming real - is, and should be said as a follow-up. Add today's consumer items to that file before finishing, and prune entries older than about a fortnight that have stopped resurfacing.
   - Report back its word count, what it web-searched, and its thread changes.
   Pass on today's weekday rotation, any dated threads due, and any feed that failed, so it can scope claims correctly.

5. Commit briefing.txt AND story-threads.md together as `Briefing YYYY-MM-DD` and push. This triggers podcast.yml.

6. Verify the render by STEP PROGRESSION, not elapsed time. If a run's updated_at sits seconds after created_at and does not move, it is stuck, not slow - pull the job steps and logs. Then confirm gh-pages advanced and today's episode is in feed.xml with a clean description and no stray directories.

7. IF THE DRAFTING AGENT FAILS ON A RATE LIMIT: do not retry immediately and do not abandon the day. The error names a reset time. IMMEDIATELY schedule a wakeup for just after it with send_later, BEFORE ending the turn or doing anything else, then retry the draft when it fires. Monday 31 August and Sunday 6 September were both lost entirely because the limit hit in the morning and nothing was scheduled to retry after the reset.

8. Report briefly: episode live, duration, render time, any failed sources, and notable thread changes.
```

## 8a. What the 8-21 September fortnight taught

Fourteen consecutive episodes, none missed, all inside ten minutes, all
rendered first attempt. What changed and why, so none of it is relearned:

**The gadgets budget is 85, not 70, with a landmark provision to ~120.**
Measured output over nine days was 81, 76, 88, 82, 73, 61, 21, 90 - the
only days under 70 were days when almost nothing shipped. The owner
raised it on 16 September after Apple's first foldable got 26 words.
The section is honest about thin days on its own - it has run 21 and 22
words saying nothing shipped - so a higher ceiling does not invite
padding, it stops forcing a choice between two complete items and one
stripped one.

**The voice reads at 151 wpm at the slow end, not 153.** Fourteen real
episodes measured 151.3 to 165.8. The old figure was described as the
slow end and was not. At 151 the 1,520 ceiling is 10:02, so the working
ceiling is now 1,500 and 1,450 remains the number to hit.

**Diagnose a failed feed before replacing it. The four failures this
fortnight had four different causes:**
- *Rest of World* (3 days): the URL had moved. `/feed/` now 301s to
  `/feed/latest/`; following the redirect doubled requests against a
  host throttling Actions egress. One-line fix, worked next morning.
  Note it ran OPPOSITE to section 4's warning - the container fetched
  it fine and only the Actions runner saw 429.
- *CSM Politics* (1 day): nothing wrong. The endpoint was healthy and
  the publisher had stopped filing. Left alone; it recovered by itself.
  The available "fix" would have hidden a true signal.
- *OriginTrail and three Agronomics feeds*: staleness flags that should
  never have been armed. The spec itself says silence in those lanes is
  expected. `RARE` silences only the staleness clock; genuine fetch and
  parse errors still report.
- *Space.com* (4 days): publisher-side. Serves HTTP 200 and a valid RSS
  envelope containing zero items; three candidate URLs all returned
  zero. Routed through Google News `site:` on 21 September - the
  Pulitzer Center pattern. **Revert to the first-party feed if it
  starts serving items again.**

**Test a replacement for FRESHNESS, not item count.** The Google News
route was checked for how many of its first twelve items were under 48
hours old, because section 10 records East Africa's route looking
healthy at 100 entries while serving month-old news.

**Hold contradictions open rather than picking the tidier side.** Two
worked examples. Hormuz: Aramco cutting European refiners off versus a
commander reporting shipments at a six-month high - both were carried
for two days until a vessel count (twelve this weekend against
thirty-five the weekend before) settled it. The Mexican peso: sliding
toward 17.3 in one source, near multi-year highs in another - asserted
in neither direction, still open. A brief that picks early is a brief
that is confidently wrong.

**Refuse the obvious inference when the digest does not support it.**
An Argentinian judge suspended an unnamed Falklands oil project on 17
September. Sea Lion is the obvious candidate. Six consecutive briefs
declined to name it because no item ever connected them.

**Check figures that contradict themselves.** A MercoPress item had
Rockhopper raising twenty million in the headline and two hundred
million in the body. Reading the whole entry plus one search resolved
it to twenty. A tenfold error would have been undetectable to the
listener.

**Weather gags wear out.** The "I told you X, it's Y" walk-back ran four
days straight and had to be rested; it is genuinely funny once a
fortnight and a tic if used more. The same is true of making a
self-contradictory forecast label the joke, used twice in eight days.
Vary the angle or drop it.

## 8b. FRESH-SESSION MODE - ABANDONED 24 September 2026 (see section 8e)

**Do not go back to this without reading 8d and 8e.** Three firings out of
three failed to publish. Kept for the record.

**The system no longer uses a self-bound Routine and no longer needs a manual
handover.** From 22 September the Routine fires with
`create_new_session_on_fire: true`, so every morning runs in a brand new
session that starts at zero context and is discarded afterwards.

**Why this changed.** A self-bound session accumulates roughly 50,000 tokens a
day and has to be handed over by a human every two weeks. The 7-21 September
session reached 569,000 tokens and $251 before being retired. Cost grew daily
because every turn re-sent the whole accumulated conversation, while the actual
work - the drafting subagent - is a flat 250,000 to 300,000 tokens a day
regardless. Fresh sessions make the daily cost flat and remove the handover
entirely.

**Why it is safe now and was not before.** Section 7 records that
`create_new_session_on_fire` was tried and judged "much less reliable", and the
reason was never written down. What HAS changed is that the knowledge no longer
lives in a conversation. Four files now hold it:

| File | Holds |
|---|---|
| `briefing-prompt.md` | the authoritative spec |
| `story-threads.md` | news continuity, with dated prune and revive conditions |
| `aired-items.md` | consumer items already broadcast, and weather angles already used |
| `HANDOFF.md` | how the machine runs, and what earlier runs learned |

A cold session reading those four knows essentially what a two-week-old session
knew. Fresh-daily was rejected when it meant amnesia; it now means a clean start
with full notes.

**THE ONE RULE THAT KEEPS THIS WORKING.** Every run must commit
`briefing.txt`, `story-threads.md` AND `aired-items.md` together. The files are
the memory. A run that updates the brief but not the other two leaves the next
morning blind, and nobody will notice until a product airs twice or a thread
goes unfollowed.

**If fresh-session mode turns out to be unreliable** - firings that do not
arrive, or sessions that start without the repository - revert to the self-bound
design in section 7, which is known to work: fourteen consecutive episodes
between 8 and 21 September, none missed. The cost of that fallback is the
fortnightly manual handover, not correctness.

## 8c. The fresh-session Routine prompt, verbatim (retired - history only)

Paste this as the `prompt` argument, with `create_new_session_on_fire: true`
and no `persistent_session_id`. It is written to be completely self-contained,
because the session reading it has no history.

```
Daily run of the news briefing and podcast pipeline. You are a FRESH session with no memory of previous runs. Everything you need is in the repository at Baby-Isa/daily-news-briefing. Trust the files, not any instinct about what happened yesterday - you were not there.

FIRST: run `date -u` and state the real time. On 24 August a session woke 8.5 hours after its routine fired and reported the run as on-time because the clock was never checked. Never infer the time from the fact that this prompt just arrived.

1. FIRST ACTION, BEFORE ANYTHING ELSE: call add_repo with owner Baby-Isa, repo daily-news-briefing, access push. A brand new session starts with NO repository attached - this is not optional and not a one-time setup, it must run every single firing. Skipping this is exactly what silently lost 22 and 23 September: both did real drafting work and then found git push refused by the proxy with "not in this session's authorized repository set" - a 403, nothing to do with file permissions. If add_repo reports the repo is already present, that is fine, continue. Then follow its own instructions (register_repo_root if it says to) before proceeding.

1b. Checkout and pull main.

2. READ THESE FOUR FILES BEFORE ANYTHING ELSE. They are the entire memory of this system.
   - HANDOFF.md - the operating handbook. Read it in full. Section 8a records what earlier runs learned; section 5 records the failures that have cost whole days; section 8d records the 22-23 September push failures and their real cause and fix (this step).
   - briefing-prompt.md - the AUTHORITATIVE specification for the brief. It overrides anything in this prompt. Do not skim it.
   - story-threads.md - ongoing news threads, with recorded prune and revive dates.
   - aired-items.md - every consumer item already broadcast, plus the weather angles already used. This is what stops a product running twice and a joke running four days straight.

3. Check digest.txt's header build time against now. An external cron builds it around 06:03 UTC each morning. Rebuild ONLY if it is genuinely stale - a different date, or more than about two hours old. If recent, USE IT; that saves four minutes. If you must rebuild, run `python3 build_digest.py` in the background (it fetches ~159 feeds and exceeds the 2-minute foreground timeout), confirm the header shows today, then commit as `Digest YYYY-MM-DD` and push. A LOCAL rebuild's failure list is unreliable - this container's IP is blocked by some publishers - so prefer the Actions-built digest before calling any lane unverified.

4. Note these before delegating, because the drafting agent needs them:
   - today's weekday and the Editorial Picks rotation it implies (spec section 13);
   - the SOURCES THAT FAILED block at the end of digest.txt, verbatim;
   - the WEATHER block near the end of digest.txt;
   - any thread in story-threads.md whose prune or revive date has arrived or is within a few days;
   - the Consumer tech lane's line number and item count.

5. Delegate reading digest.txt and drafting to a general-purpose subagent. Give it, in its prompt:
   - Instructions to read briefing-prompt.md IN FULL and follow it exactly; it is authoritative.
   - Instructions to read story-threads.md and aired-items.md in full before drafting.
   - The hard word limit and ceiling the spec states, and an instruction to count words before finishing.
   - "EVERY ITEM CARRIES ITS PAYLOAD" outranks brevity: recover a missing fact by web search where the spec permits, or say the gap out loud, or cut the item. Never gesture at significance.
   - The weather data verbatim, plus the angles already used from aired-items.md so it does not repeat one.
   - An instruction to read digest.txt in CHUNKS with offset until it reaches the literal line "End of full digest." It is two-tier, so the "ALSO IN <LANE>" headline-only lists must be read too, saying only what a headline supports.
   - The reminder that lane names describe the FEED, not the topic.
   - Today's rotation, the failed feeds, and any dated threads falling due.
   - A request to report back its word count, what it web-searched, what the gadgets section did, and its thread changes.

6. VERIFY THE DRAFT YOURSELF before committing. Do not take the agent's word for any of it:
   - `wc -w briefing.txt` against the spec's hard limit.
   - `grep -coE "[0-9]" briefing.txt` should be 0 - this is text-to-speech input and every number and date is spelled out.
   - No markdown, bullets or headers.
   - The closing failed-sources line matches the digest's failed block, and is absent entirely when nothing failed.
   - Nothing from aired-items.md has been re-run without a genuinely new fact.
   - Nothing is asserted that has not happened yet - a decision due this afternoon, a match kicking off later, a print released after the digest was built.

7. Append one line to run-log.md following its own format (STATUS OK/PARTIAL/FAILED plus what happened). Commit briefing.txt, story-threads.md, aired-items.md AND run-log.md together as `Briefing YYYY-MM-DD` and push. This triggers podcast.yml. All four files must move together or tomorrow's run loses its memory.

8. Verify the render WITHOUT relying on connector tools. Poll the published feed until today's episode appears:
   curl -fsS https://Baby-Isa.github.io/daily-news-briefing/feed.xml | grep "DD Mon 2026"
   A healthy render takes four to six minutes. Then confirm gh-pages advanced and is clean:
   git fetch origin gh-pages && git ls-tree --name-only origin/gh-pages
   It must contain exactly audio, feed.xml and index.html. If models, _site or _tts_work appear, the publish step has leaked the TTS model - that has happened twice and must be fixed, not ignored.
   If the render looks stuck, judge it by STEP PROGRESSION, not elapsed time: a run whose updated_at sits seconds after created_at and never moves is stuck, not slow.

9. IF THE DRAFTING AGENT FAILS ON A RATE LIMIT: do not retry immediately and do not abandon the day. The error names a reset time. IMMEDIATELY schedule a wakeup for just after it with send_later, BEFORE ending the turn or doing anything else, then retry the draft when it fires. Monday 31 August and Sunday 6 September were both lost entirely because the limit hit in the morning and nothing was scheduled to retry after the reset.

10. Report briefly: episode live, duration, render time, any failed sources, notable thread changes, and anything you had to leave out or could not verify.

11. Before you finish, if you changed anything about how the system runs - a feed, a budget, a rule - write it into the repository. You will not be here tomorrow and neither will your reasoning unless it is in a file.

12. IF ANYTHING STOPS YOU BEFORE STEP 7 - a rate limit you cannot wait out, a subagent error, a push still refused even after step 1's add_repo, anything at all that stops the normal pipeline - do not just end the turn. Your last action must be `git add run-log.md`, commit and push run-log.md BY ITSELF with a STATUS FAILED line describing what happened and why, as specifically as you can. This is the only way anyone finds out something went wrong instead of guessing from a vanished notification: both 22 and 23 September did real work, hit a push failure, and left no trace anywhere at all - the 23rd because the run never reached this step either. If run-log.md itself cannot be pushed, that is the one scenario nothing here can fix; say so as directly as you can in your final report, since that report may be the only surviving trace.
```

## 8d. The 22-23 September push failures, and the real fix

**Superseded below - read the 23 September update first.** The diagnosis
this section originally recorded (Auto-mode self-permission denial, fixed by
`.claude/settings.json`) was wrong. It was a reasonable theory from the
evidence available on 22 September, but 23 September repeated the exact same
symptom - real drafting work, nothing pushed - with that fix already in the
repo and never even triggered. The transcript (finally readable directly in
the Claude Code app, not through any tool available to the session
investigating it) showed the actual error: `git push` was refused by the git
proxy with "Baby-Isa/daily-news-briefing is not in this session's authorized
repository set" - a 403, not a permission-mode block.

**Real root cause.** A fresh session created by `create_new_session_on_fire`
starts with NO repository attached. `create_trigger` has no `source_url` or
equivalent field the way `create_session` does, so there is no way to
pre-attach one when the Routine is created. Read access (clone, pull) works
anyway - both the 22nd and 23rd fully cloned, read the digest, and drafted a
complete brief - but PUSH requires an explicit session-level grant via the
`add_repo` tool (`owner: Baby-Isa, repo: daily-news-briefing, access: push`),
and nothing in the Routine prompt ever called it. Both failures share this
one cause; the settings.json permission theory was never actually tested by
either failure.

**The fix.** Step 1 of the Routine prompt (section 8c) now opens with an
explicit `add_repo` call, before checkout, before anything else, every
single time - a fresh session cannot be assumed to have the repo attached
just because the last one did; each firing is a new session with nothing.

The `.claude/settings.json` grant from 22 September is harmless and left in
place - it just never did anything, on either day.

**ORIGINAL 22 SEPTEMBER NOTE, kept for the record - diagnosis superseded above.**

The first live firing of fresh-session mode (22 September, 06:34 UTC) did real
drafting work - 21 minutes, $5.25, a genuine draft - and then pushed nothing to
GitHub. The session went idle without error and, being a fresh session, was
gone by the time this was noticed; it could not be reached to ask what
happened. Today's episode was recovered by hand in an interactive session.

**Root cause.** Fresh Routine sessions run in Auto mode, which auto-*denies*
certain actions outright rather than prompting for them - there is no
"waiting for a human" state to notice, the action just silently fails. A
`git push` from a session with no prior approval history is denied this way:
a fresh session has never had a chance to establish that pushing is fine, and
nobody is present to grant it interactively. This was confirmed directly: an
attempt to fix it by writing `.claude/settings.json` from *this* session, also
in Auto mode, was itself auto-denied with reason `[Self-Modification]` - Auto
mode will not let a session grant itself more permission than it already has,
which is presumably the same mechanism that blocked the push. The fix could
only be written after the owner switched the session to Accept Edits mode by
hand; that mode does not run the same self-permission check.

**The fix.** `.claude/settings.json` now carries a durable, repo-level grant:

```json
{
  "permissions": {
    "allow": ["Bash(git push *)"]
  }
}
```

This is read at the start of any session working in this checkout, fresh or
not, so `git push` no longer needs a first-time approval that nobody is there
to give. It is scoped to `git push` specifically, not a blanket Bash grant.

**This theory turned out to be wrong.** 23 September failed the same way
with this fix already in place and never triggered - see the top of this
section for the real cause and fix (a missing `add_repo` call, step 1 of
section 8c).

**Also added 22 September: `run-log.md`.** The gap that made the first
failure hard to diagnose was not just the push - it was having nowhere to
look. `run-log.md` gets a line every day, success or failure, as close to
the pipeline's last action as the prompt can arrange (step 12 in section
8c). It worked exactly as intended once for real: the 23 September entry was
written by hand from the owner's account within the hour, instead of being
reconstructed days later from a dead session. It is not bulletproof - if
`git push` itself cannot reach GitHub at all (as opposed to being refused
for a fixable reason), the log entry cannot land either, and the push
notification, read directly in the app rather than trusted secondhand, is
what actually broke this case open. Email notifications were considered as
a second channel and declined (would have required deleting and recreating
the Routine, losing its run-history bookkeeping, for a channel run-log.md
mostly makes redundant) - the Routine stays push-only.

**Two failures, one afternoon apart, taught the operational lesson worth
keeping:** a theory formed from indirect evidence (cost, duration,
permission_mode, an inability to reach the session) is still a guess. The
transcript itself, read directly, found the real cause in one look. If a
third failure ever happens, read the session's own transcript in the app
FIRST, before theorizing from metadata again.

## 8e. THE CURRENT DESIGN, from 24 September 2026: self-bound, subagents do the work

**Why fresh-session mode was abandoned.** It failed to publish on all three
days it ran (22, 23, 24 September). Two of the failures were confirmed from
the session transcript: `git push` was refused by the git proxy because a
brand-new session has no repository attached. Adding an `add_repo` call to the
prompt did not fix it. On 24 September the session stopped after two and a
half minutes, having spent one dollar, and published nothing. An unattended
session cannot grant itself push access. The Routine tools (`create_trigger`,
`update_trigger`) have no field for attaching a repository ahead of time, so
there is no way to fix this from inside a session. Every attempt to push
through it cost a lost episode.

**What replaced it.** The Routine (`trig_01TVRoeXyNB2Zvyswj7LxFpf`,
`30 6 * * *`) fires into the ONE long-lived session that was created with this
repository attached (`session_01U9cR8hx8suZHqMamQ5XLrS`). That session has
pushed successfully every time it was asked, including fourteen consecutive
unattended mornings from 8 to 21 September. Nothing about access has to be set
up per run, because it was set up once, at creation.

**Why it does not balloon any more.** The old self-bound design grew about
50,000 tokens a day because the session did the reading, verifying and
committing itself. Now it does almost nothing. It checks the clock, launches a
DRAFTING subagent, then a separate PUBLISHING subagent, and relays a three-line
report. Subagent context is discarded when each one finishes. The working
instructions live in **`daily-run.md`**, so a change to how a day runs is a
git commit, not a Routine update. The conversation also compacts itself
automatically, so no fortnightly manual handover is needed.

**Permissions.** `.claude/settings.json` pre-approves exactly what the pipeline
uses (git, the digest build, curl, a few read-only shell tools, file
read/edit/write, web search/fetch, `send_later`). That way an unattended
firing cannot stop at an approval prompt nobody is there to answer, whichever
permission mode the session happens to be in.

**If this session ever has to be replaced** (deleted, archived, or broken),
the replacement must be a session created WITH the repository attached. On
claude.ai/code, that means starting a new session on Baby-Isa/daily-news-briefing.
Then, from inside that new session: create a self-bound Routine with the same
prompt, confirm it with `list_triggers`, and only then delete the old one.
Never go back to `create_new_session_on_fire` unless the product gains a way
to attach a repository to the Routine itself.

## 9. Where things stand, 7 September 2026

Working and stable: the digest build, the external cron, the TTS render,
the publish step, the two-tier cap, the continuity file, episode length
(consistently 9:00-9:43 against a ten-minute target).

Recently changed:

- **A standalone gadgets and consumer tech section** (spoken section 8),
  added 5 September, first aired 7 September. New `Consumer tech` lane -
  The Verge, Engadget, Tom's Hardware. Budget raised from 40 to 70 words
  on 7 September after the first outing showed 40 could not carry the
  two properly-sourced items the section's own rules demand.
- **The `EXCLUDE` flag**, added at the same time, because Engadget
  publishes a lot of service journalism. 29 terms now, each one chosen
  from noise that actually appeared and tested against all 87 distinct
  Consumer tech titles before being committed.

Open questions for the owner (the cron-job.org timezone question was
answered on 7 September - it is UTC; see section 6):

- Whether to run weekdays only. **Asked and answered on 12 September:
  keep weekends.** Saturday carries the Longreads Top 5, which only
  works on a Saturday build; Sunday carries the Pulitzer Center and,
  since 13 September, the returned Weekend Intelligence. Weekdays-only
  would cost three rotation slots.
- **Section 5 and section 7 of briefing-prompt.md contradict each other
  on cameras.** Section 7 says "mirrorless releases"; section 5's
  boundary rule names only Micro Four Thirds and LUMIX. A Canon
  full-frame launch therefore belongs in Special Interests under one
  and Gadgets under the other. Raised with the owner on 16 September,
  not yet answered. It ran in Gadgets that day. One line fixes it once
  he says which he meant.
- **Should the review exclusion be relaxed for seven-seaters?** The
  Skoda Peaq appeared only as a review on 21 September and was cut,
  correctly under the standing rule. But a car can launch and never
  reach him if the only coverage is a review. Raised, not yet answered.
- ~~Whether the gadgets section holds at 70 words.~~ **Answered: it is
  85 now, raised by the owner on 16 September. See section 8a.**
- **Scheduled for 12 September 2026, 10:00 UTC** (`send_later`
  `trig_014gnjE2QAkcBHUzkN2seRq6`): review what the drafting session
  reads into its own context each morning. The subagent's reads are
  discarded with it, but the parent still accumulates, and step 3 of the
  Routine prompt - read `briefing-prompt.md` in full, ~10,800 tokens -
  is the dominant daily cost and roughly half the parent's growth. The
  subagent reads the spec itself anyway, so the parent's copy is largely
  redundant. Deliberately NOT changed yet: the owner asked to run it as
  is for a few days first, so the brief can be checked as it comes
  through, including the new gadgets section. If this session is lost
  before the review fires, the scheduled reminder goes with it - carry
  the question into the next one from here.

**Standing check until then (8-12 September):** each morning, read the
drafted brief and confirm the gadgets and consumer tech section behaved -
present with a name, a delta, a price and a date per item when something
shipped, correctly and silently absent when nothing did, and inside its
70 words. Say what it did in the daily report rather than only that the
episode published.

## 10. How to work on this

The single most useful habit this project has produced: **check before
replacing**. It changed the answer three separate times.

- East Africa's Google News `site:` route looked healthy at 100 entries
  and was serving month-old news.
- Broader UK private-equity queries returned fresher items that were
  *worse* - law-firm marketing and opinion pieces.
- A HomeTheaterReview replacement turned out to be worse than the query
  already configured.

Test the replacement against the thing it replaces, on real data, before
committing it. Every filter term and budget number in here was set that
way, and the ones that were guessed instead had to be fixed later.

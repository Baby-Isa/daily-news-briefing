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
| `story-threads.md` | Continuity between days. ~17 live threads, each dated, with recorded prune and revive conditions. Read at the start of every draft, updated and committed at the end. This is the only memory the system has. |
| `digest.txt` | Today's input. Regenerated daily, committed. |
| `briefing.txt` | Today's output. What gets read aloud. |
| `build_podcast_episode.py` | Kokoro TTS + feed.xml generation. |
| `.github/workflows/digest.yml` | Builds the digest. Has a date guard so repeat pings no-op in ~15s. |
| `.github/workflows/podcast.yml` | Renders and publishes. Triggered by any push touching `briefing.txt`. |

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

The Routine's prompt (section 7) is the operational checklist and is
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

## 7. First thing to do in the new session

The Routine is **self-bound**: it fires into the session that created
it. That was chosen deliberately - `create_new_session_on_fire` proved
much less reliable. It also means a new session needs its own Routine,
and the old one must be removed or both will fire.

Do this in order:

1. Create the new Routine with `create_trigger`, `cron_expression`
   `"30 6 * * *"`, no `persistent_session_id` (omitting it self-binds),
   `initiation: "human_request"`, and the prompt in section 8 verbatim.
2. Confirm it exists with `list_triggers`.
3. **Only then** delete the old one:
   `delete_trigger` on `trig_01FfwTCufC7zht1Kgdoofwgn`.

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
   - Report back its word count, what it web-searched, and its thread changes.
   Pass on today's weekday rotation, any dated threads due, and any feed that failed, so it can scope claims correctly.

5. Commit briefing.txt AND story-threads.md together as `Briefing YYYY-MM-DD` and push. This triggers podcast.yml.

6. Verify the render by STEP PROGRESSION, not elapsed time. If a run's updated_at sits seconds after created_at and does not move, it is stuck, not slow - pull the job steps and logs. Then confirm gh-pages advanced and today's episode is in feed.xml with a clean description and no stray directories.

7. IF THE DRAFTING AGENT FAILS ON A RATE LIMIT: do not retry immediately and do not abandon the day. The error names a reset time. IMMEDIATELY schedule a wakeup for just after it with send_later, BEFORE ending the turn or doing anything else, then retry the draft when it fires. Monday 31 August and Sunday 6 September were both lost entirely because the limit hit in the morning and nothing was scheduled to retry after the reset.

8. Report briefly: episode live, duration, render time, any failed sources, and notable thread changes.
```

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

- Whether to run weekdays only. Never asked, never answered.
- Whether the gadgets section holds at 70 words or wants trimming again
  after a week of evidence.
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

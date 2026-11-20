# Onboarding: setting up a new listener

**For Claude.** You are setting up a personal daily news podcast for the
person in this chat. They are senior, busy and not technical. They should
never see a file name, a command, an error message or the word "repository"
unless something needs their hand. Everything they are asked can be
answered with "yes".

Follow the steps in order. After each step, tick it in `setup-progress.md`,
commit and push to `main`, so that a closed tab or a dropped connection
resumes at the next step instead of starting again. If you arrive in this
chat and some steps are already ticked, say "Welcome back - picking up
where we left off" and continue from the first unticked step.

How to talk:

- One question per message. Short. Plain words.
- Show the default, then: **Reply yes to continue, or tell me what to add
  or remove.**
- Accept anything: "yes", "y", "fine", a voice-dictated ramble. Work out
  what they meant; ask again only if you truly cannot tell.
- If they say "yes to the rest", "use the defaults" or similar, accept
  every remaining default in that step and move on.
- Never lecture. Never explain how it works unless asked.

---

## Step 0 - Quiet checks (say nothing unless one fails)

1. Run `git checkout main && git pull origin main`. All setup work happens
   on `main`. Your session may tell you to work on a branch of its own;
   the listener's go-ahead in step 1 is what permits `main`.
2. Find the repository's owner and name: `git remote get-url origin`.
3. Note the time: `date -u`.

If the pull fails, the GitHub connection is missing. Say:

> I can't reach your copy of the briefing yet. Please open
> claude.ai/connect-github, approve the connection, and tick your new
> briefing repository when it asks which ones to allow. Then come back and
> say "done".

## Step 1 - Welcome, and the one permission

Send this, adapting only the greeting:

> Hello - I'm going to set up your personal morning news briefing: a short
> podcast, written fresh each morning around what you care about, that
> appears in your podcast app before you start your day.
>
> It takes about fifteen minutes. I'll ask what you want covered, one topic
> at a time, with a sensible default for each - so you can simply reply
> **yes** all the way through and adjust later.
>
> Two quick things first:
> 1. **May I save your settings and publish each day's episode to your own
>    copy of the briefing?** Episodes go to a web address only you will
>    have; it isn't listed anywhere, though anyone you gave the link to
>    could listen.
> 2. **What phone do you use, and do you already use a podcast app?**

Wait for a clear yes to the first question. Without it, stop: explain that
nothing can be saved or published until they agree. Record the phone and
app in `setup-progress.md`.

Then, in the background while you carry on talking:

- Make a first test push (tick step 1, commit, `git push origin main`).
  If the push is refused, give the connect-github instruction from step 0.
- Start a first news build so there is real news ready for the sample:
  use the GitHub Actions tool to run a workflow - method `run_workflow`,
  the owner and repository from step 0, `workflow_id` `digest.yml`, `ref`
  `main`. If no such tool is available, run `python3 build_digest.py` in
  the background instead (it takes about four minutes).

## Step 2 - About them

> To pitch it right: in a sentence or two, what do you do, and what do you
> most want from a morning briefing? (Feel free to dictate.)

Write what they say into `profile.md` under "The listener", and adjust
"Always lead with" if their answer changes the lens. If they would rather
skip, keep the default.

## Step 3 - The ten topics, one at a time

Send each of these as its own message, exactly in this form, and wait for
the reply before sending the next. After each reply, update that section's
block in `profile.md` (and its budget in `config.json` if they ask for more
or less of it). If they remove a topic entirely, set its tier in
`config.json` to "threshold" and write "Left out at the listener's request"
in its block - do not delete the section.

> **1 of 10 - Politics**
> Included by default: the major political headlines · the UK · the United
> States · Europe.
> Day-to-day political noise is kept to a line; anything that changes law,
> tax or who governs gets proper treatment.
> Is there another country or region you want followed closely?
> Reply **yes** to continue, or tell me what to add or remove.

> **2 of 10 - Conflict and world affairs**
> Included by default: the major wars and crises, a tight line on each new
> development · the most significant stories from the rest of the world
> (Asia, Africa, Latin America, the Middle East) · natural disasters as a
> single line.
> Reply **yes** to continue, or tell me what to add or remove.

> **3 of 10 - Economy and markets**
> Included by default: central bank decisions (Federal Reserve, Bank of
> England, European Central Bank) · inflation, jobs and growth figures
> against what was expected · sterling and the dollar · what markets are
> pricing, and why.
> This is the heart of the briefing: written as analysis, not a list of
> numbers.
> Reply **yes** to continue, or tell me what to add or remove.

> **4 of 10 - Business**
> Included by default: big company news that says something about a whole
> sector · UK business conditions (costs, tax, regulation) · the
> artificial intelligence investment boom.
> Left out by default: routine executive appointments.
> Are there particular industries you want watched?
> Reply **yes** to continue, or tell me what to add or remove.

> **5 of 10 - Deals and private equity**
> Included by default: UK and European mid-market and private-equity deals
> (buyouts, take-privates, exits, fund raises) · financing conditions ·
> the largest global deals when they say something about the cycle.
> Each deal comes with its logic in a line: why this asset, why now.
> Reply **yes** to continue, or tell me what to add or remove.

> **6 of 10 - Science and technology**
> Included by default: artificial intelligence · space · biotech and
> medical breakthroughs · energy research.
> Discoveries and launches, not products.
> Reply **yes** to continue, or tell me what to add or remove.

> **7 of 10 - Consumer tech**
> Included by default: major product launches only (phones, computers,
> cars, devices), with what's new, the price and when you can buy it.
> Skipped on days nothing notable ships.
> Reply **yes** to continue, tell me what to add, or say **drop it**.

> **8 of 10 - Energy, climate and infrastructure**
> Included by default: energy prices and security · climate policy that
> changes what things cost · major infrastructure projects.
> Reply **yes** to continue, or tell me what to add or remove.

> **9 of 10 - Health, law and society**
> Included by default: only the big moments - a landmark court ruling, a
> major health development, a significant social shift.
> Reply **yes** to continue, or tell me what to add or remove.

> **10 of 10 - Culture and sport**
> Included by default: major sporting results and events · the biggest
> film, television and book releases.
> Do you follow a team or a sport? I can cover it every day.
> Reply **yes** to continue, or tell me what to add or remove.

If they name a team, a region, an industry or any new interest in this
step, note it for step 5: it needs a source.

## Step 4 - Watchlist

> **Your watchlist.** Are there specific names you want flagged whenever
> they're in the news - companies, people, funds, sectors, a competitor?
> I'll check for each one every morning and stay silent when there's
> nothing.
>
> One caution: your settings are stored in your own online folder, which
> is public by default. I'd suggest not listing anything you would not
> want a third party to know you are watching - or tell me and I'll explain
> how to make it private.
>
> List them, or reply **none**.

Write each name into the Watchlist block of `profile.md` with what counts
as news about it. If they ask about privacy: a private repository hides
the settings, needs a paid GitHub plan (about four dollars a month) for
the podcast address to keep working, and the audio itself stays reachable
by anyone who has the address. Offer to walk them through it after setup.

## Step 5 - Sources

> **Sources.** I'll choose the news sources to match everything you've
> just told me. Are there any you particularly want included - or any you
> want kept out?
> Reply **yes** to leave it to me.

Then do the work without narrating it:

- `feeds.txt` already covers the ten default topics. Remove lanes for
  anything they dropped.
- For each new interest, copy matching lines from `feeds-library.txt`, or
  build one using the patterns at the bottom of that file. Each watchlist
  name gets a Google News search line under the lane `Watchlist`, flagged
  `RARE`.
- For each source they asked for by name, find its RSS feed.
- **Test every line you add:** `python3 tools/test_feed.py "<url>"`. Add
  only GOOD or QUIET results. A failure in this container can be a false
  alarm (some publishers block it); if a well-known publication fails
  here, add it anyway and check the first real digest's "SOURCES THAT
  FAILED" list.
- Tell them plainly, in one message, about anything that will not work as
  they might expect: "The Financial Times and similar paid sites only give
  me headlines and short summaries, not full articles - I use them, but
  can't quote the detail."

## Step 6 - Format

Send one message:

> **How it sounds.** Here's the default - the same style as the episode
> you've heard:
>
> - **Length:** about eight minutes
> - **Tone:** crisp and analytical, with one dry joke in the weather
> - **Opens with:** the weather for [their city?], then how the day's
>   biggest stories connect
> - **Voice:** British, female, at a measured pace
> - **Ready by:** 6:45 each morning, every day
>
> Reply **yes**, or change anything - for example "five minutes", "no
> weather", "weekdays only", "ready by 6", "a male voice".
>
> And one thing I need: **which town or city should the weather be for,
> and what should I call the show?** ("Morning Briefing" is fine.)

Apply the answers in `config.json`:

- Length: about 150 words a minute at this pace. Set `words.target`, with
  `min` about 13% below and `max` about 9% above, and scale each section
  budget by the same proportion.
- Weather place: set `place`, `lat` and `lon` (look the coordinates up;
  check them by building the digest and reading its WEATHER block). "No
  weather" sets `enabled` to false.
- Time zone: set `timezone` to theirs (an IANA name such as
  `Europe/London`). Ask only if their city leaves it unclear.
- Voice: British female `bf_isabella` (default) or `bf_emma`; British
  male `bm_george` or `bm_lewis`; American female `af_heart` or `af_bella`;
  American male `am_michael`. American voices need `language` set to
  `en-us`.
- Ready-by time: explain once, only if they ask for earlier than 6:00,
  that about a third of each day's news arrives overnight, so a very early
  episode misses some of it.
- If a place or name is likely to be mispronounced, add it to
  `pronunciations`.

Also update the "Tone and weather" block in `profile.md`.

## Step 7 - The first episode

> Thank you - that's everything I need. I'm writing your first episode
> now from this morning's news. It takes about ten minutes; I'll tell you
> the moment it's ready.

Then:

1. If you changed `feeds.txt`, commit and push it, then start a fresh news
   build (as in step 1) and run `python3 tools/wait_for_digest.py`.
2. Run the day exactly as `daily-run.md` describes, from Part A.
3. When `tools/check_render.py` reports the episode rendered, check the
   public address: `curl -fsS -o /dev/null -w "%{http_code}" <feed url>`,
   where the feed url is `https://<owner>.github.io/<repository>/feed.xml`
   in lower case. Retry for up to three minutes.

If the address still returns 404, the website setting is off. Ask them:

> One setting needs your tap. Open **github.com/<owner>/<repository>/settings/pages**.
> Under "Branch", choose **gh-pages**, leave the folder as "/ (root)", and
> press **Save**. Tell me when that's done.

(If that page says the feature needs an upgrade, their copy is private on
a free plan. The choice is to make it public - Settings, General, bottom of
the page, "Change visibility" - or to upgrade GitHub. Explain both
briefly and let them choose.)

## Step 8 - On their phone

Send the instructions for their phone and app, with the feed address on
its own line so it can be copied:

- **iPhone, Apple Podcasts:** "Open Podcasts. Tap **Library**, then the
  **three dots** at the top right, then **Follow a Show by URL**. Paste
  the address below and tap **Follow**."
- **Android or iPhone, Pocket Casts:** "Tap **Discover**, paste the
  address into the search box, and tap **Subscribe**."
- **Android, AntennaPod:** "Tap **Add Podcast**, then **Add podcast by RSS
  address**, and paste the address."
- **Overcast:** "Tap **+**, then **Add URL**, and paste the address."
- **Spotify cannot do this.** If that is all they use, suggest Apple
  Podcasts on iPhone or Pocket Casts on Android (both free).

Also give the plain web address (`https://<owner>.github.io/<repository>/`)
as a fallback: it plays the latest episode in any browser.

> Have a listen to today's episode and tell me what you'd change - or
> reply **yes** if you're happy and I'll set it to arrive every morning.

Apply any feedback to `profile.md` or `config.json`. If they want to hear
the change, re-run the day and tell them their app may need a
pull-to-refresh to fetch the new version.

## Step 9 - Switch on the daily run

Create four scheduled tasks **in this session** (so each fires back into
this same chat, which is the only one with permission to publish). Use the
scheduled-task tool (`create_trigger`), with no `persistent_session_id`
and without `create_new_session_on_fire`, and `initiation` set to
`human_request`. Write every schedule in their own time zone using the
`CRON_TZ=<their zone>` prefix.

| Name | When | Prompt |
|---|---|---|
| Daily briefing | 35 minutes before the ready-by time (06:10 for 06:45), on their chosen days | `Daily briefing run. Follow daily-run.md in this repository exactly, starting at step 1.` |
| Briefing backup check | 2 hours 30 minutes after the daily run, same days | `Backup check. Follow the "Backup check" section of daily-run.md.` |
| Briefing late check | 13:10, same days | `Backup check. Follow the "Backup check" section of daily-run.md.` |
| Weekly self-review | Sundays at 16:20 | `Weekly self-review. Follow weekly-review.md in this repository exactly.` |

Confirm all four with `list_triggers`. Record their ids in
`setup-progress.md`.

Also schedule one message to yourself three days from now (`send_later`,
`initiation` `human_request`): `Day-three check-in: ask the listener, in
two lines, whether anything in the briefing should change, and apply what
they say.`

Change `SETUP STATUS` in `profile.md` to `complete`, tick the step, commit
and push.

## Step 10 - Close

> You're all set. A new episode will be in your podcast app by
> [time] every [day/weekday].
>
> **To change anything, just tell me here** - "less politics", "add the
> Financial Times", "make it shorter", "follow Arsenal", "it said that name
> wrong". Keep this chat; it's the one that runs your briefing.
>
> Two things worth knowing:
> - Writing each episode uses some of your Claude allowance. If you ever
>   run out for the week, the briefing pauses and picks up again when it
>   resets.
> - I'll check in with you in three days to fine-tune it. After that I
>   review it myself every week and only message you if something needs
>   you.

Do not mention GitHub, files or settings again unless they ask.

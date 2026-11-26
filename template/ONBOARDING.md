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
- A yes/no question ends: **Reply yes or no.**
- A topic question ends: **Type "Yes" to continue or write
  additions/changes.**
- Accept anything: "yes", "y", "fine", a voice-dictated ramble. Work out
  what they meant; ask again only if you truly cannot tell.
- If they say "yes to the rest", "use the defaults" or similar, accept
  every remaining default in that step and move on.
- Never lecture. Never explain how it works unless asked.
- Never send them to GitHub unless a check below fails. They did all the
  GitHub steps before opening this chat (see README.md).

Rules learned from the first real setup (23 November 2026):

- **Reading is not access.** The copy is public, so a pull succeeds even
  when Claude cannot save to it. Only a push proves access.
- **Keep the address's capitals.** GitHub's web addresses are
  case-sensitive. Build the podcast address from `git remote get-url
  origin` exactly as written: `https://<owner>.github.io/<Repository>/`.
- **This container cannot reach news sites or the podcast address.** Its
  network blocks publishers and `github.io`. Test sources and the feed
  through GitHub (steps 4 and 6), never with a local fetch.
- **Edit `profile.md` by heading, never by line number.** Replace the
  whole block under the heading you are changing.
- **When something returns "not found", check the address before blaming
  a delay.**

---

## Step 0 - Quiet set-up (say nothing)

1. `git checkout main && git pull origin main`. All setup work happens on
   `main`. Your session may tell you to work on a branch of its own; the
   listener's yes in step 1 is what permits `main`.
2. `git config pull.rebase true` (the news build commits to `main` while
   you work, so every push needs a rebase first; always
   `git pull --rebase origin main` before `git push origin main`).
3. `python3 -c "import feedparser" || python3 -m pip install -q -r requirements.txt`
4. Note the owner and repository name, capitals included:
   `git remote get-url origin`. Note the time: `date -u`.

## Step 1 - Welcome, and the one permission

Send this:

> Hello - I'm going to set up your personal morning news briefing: a short
> podcast, written fresh each morning around what you care about, that
> appears in your podcast app before you start your day.
>
> It takes about fifteen minutes. I'll ask what you want covered, one topic
> at a time, with a sensible default for each. At the end I'll give you a
> link to add to your podcast app, and your first episode.
>
> Two quick things first:
>
> 1. **May I save your settings and publish each day's episode to your own
>    copy of the briefing?** Episodes go to a web address only you will
>    have. It isn't listed anywhere, but anyone you gave the link to could
>    listen. **Reply yes or no.**
> 2. **Which podcast app do you use?** (e.g. Apple Podcasts, Pocket Casts,
>    Overcast)

Wait for a clear yes to the first question. Without it, stop: explain that
nothing can be saved or published until they agree. Record the app in
`setup-progress.md`.

### Then check the two things they set up on GitHub

Do these now, before any topic questions, so that any trip back to GitHub
happens once, at the start.

**Check A - can I save?** Tick step 1, commit, `git pull --rebase origin
main`, `git push origin main`. If the push is refused:

> Before we go on, I need one thing from you. I can read your copy of the
> briefing but I'm not yet allowed to save to it.
>
> **Open this link: github.com/apps/claude/installations/select_target**
>
> It opens in a web browser, and you may be asked to sign in to GitHub and
> to Claude there. Choose your account, select your briefing copy
> (**<Repository>**), and press **Install & Authorize**.
>
> Then come back to this chat, in the app or wherever you're reading this,
> and type **continue**.

**Check B - is the podcast address switched on?**

1. Note the time: `SINCE=$(date -u +%s)`.
2. Make sure a `gh-pages` branch exists and touch it:
   `git fetch origin gh-pages` - if that fails, the copy was made without
   its second branch; create one: an orphan branch `gh-pages` holding only
   a one-line `index.html` and an empty `.nojekyll`, and push it. If it
   exists, check it out, change one character in `index.html`, commit,
   push, and return to `main`.
3. Wait one minute, then list this repository's workflow runs with the
   GitHub Actions tool (method `list_workflow_runs`, no workflow id). A run
   named **pages build and deployment** created after `SINCE` means the
   address is on. Check twice, a minute apart, before deciding it is off.

If it is off:

> One setting needs switching on so your podcast has an address.
>
> Sign in to GitHub in your web browser first (if you're not signed in,
> the page below shows "not found"). Then open
> **github.com/<owner>/<Repository>/settings/pages**. Under **Branch**
> choose **gh-pages**, leave the folder as **/ (root)**, and press
> **Save**.
>
> On a phone you can also get there from your copy's page: **Settings**
> (under the "..." menu), then **Pages**.
>
> Then come back here and type **continue**.

Repeat the check after they return. If the Pages screen says the feature
needs an upgrade, their copy is private on a free plan: the choice is to
make it public (Settings, General, bottom of the page, "Change
visibility") or to upgrade GitHub. Explain both in two lines and let them
choose.

## Step 2 - The ten topics, one at a time

Send each of these as its own message, exactly in this form, and wait for
the reply before sending the next. After each reply, replace that
section's block in `profile.md` (and its budget in `config.json` if they
ask for more or less of it). If they remove a topic entirely, set its
tier in `config.json` to "threshold" and write "Left out at the listener's
request" in its block; do not delete the section. Note any new interest
(a country, an industry, a team): it needs a source in step 4.

> **1 of 10 - Politics**
>
> Included by default:
> - the major political headlines
> - the UK, the United States and Europe
> - anything that changes law, tax or who governs
>
> Minimised:
> - day-to-day political noise is kept to a line
>
> Type "Yes" to continue or write additions/changes (e.g. another country
> to follow).

> **2 of 10 - Conflict and world affairs**
>
> Included by default:
> - major wars and crises (a line each)
> - the biggest stories from Asia, Africa, Latin America and the Middle
>   East
>
> Minimised:
> - natural disasters are summarised in one line
>
> Type "Yes" to continue or write additions/changes.

> **3 of 10 - Economy and markets**
>
> Included by default:
> - central bank decisions (Federal Reserve, Bank of England, European
>   Central Bank)
> - inflation, jobs and growth figures, against what was expected
> - sterling, the dollar, and what markets are pricing
>
> Minimised:
> - daily market moves with no cause behind them
>
> Type "Yes" to continue or write additions/changes.

> **4 of 10 - Business**
>
> Included by default:
> - company news that says something about a whole sector
> - UK business conditions (costs, tax, regulation)
> - the artificial intelligence investment boom
>
> Minimised:
> - routine executive appointments and routine results
>
> Type "Yes" to continue or write additions/changes (e.g. an industry to
> watch).

> **5 of 10 - Deals and private equity**
>
> Included by default:
> - UK and European buyouts, take-privates, exits and fund raises
> - financing conditions
> - the largest global deals, each with its logic in a line
>
> Minimised:
> - small add-on acquisitions
>
> Type "Yes" to continue or write additions/changes.

> **6 of 10 - Science and technology**
>
> Included by default:
> - artificial intelligence
> - space
> - biotech, medical breakthroughs and energy research
>
> Minimised:
> - products you can buy (those are next)
>
> Type "Yes" to continue or write additions/changes.

> **7 of 10 - Consumer tech**
>
> Included by default:
> - major launches (phones, computers, cars, devices) with what's new, the
>   price and the date
>
> Minimised:
> - rumours, deals and buying guides; skipped on days nothing ships
>
> Type "Yes" to continue, write additions/changes, or "drop it".

> **8 of 10 - Energy, climate and infrastructure**
>
> Included by default:
> - energy prices and security
> - climate policy that changes what things cost
> - major infrastructure projects
>
> Minimised:
> - conference process and pledges without money attached
>
> Type "Yes" to continue or write additions/changes.

> **9 of 10 - Health, law and society**
>
> Included by default:
> - landmark court rulings
> - major health developments
> - significant social shifts
>
> Minimised:
> - everything else; this section appears only on big days
>
> Type "Yes" to continue or write additions/changes.

> **10 of 10 - Culture and sport**
>
> Included by default:
> - major sporting results and events
> - the biggest film, television and book releases
>
> Minimised:
> - celebrity news is left out
>
> Type "Yes" to continue or write additions/changes (e.g. a team or sport
> to follow).

Where a request could sit in two sections, put it in one and say which:
all mergers and acquisitions live in Deals and private equity.

## Step 3 - Watchlist

> **Your watchlist**
>
> Any specific names to flag whenever they're in the news: companies,
> people, funds, a competitor? I check for each every morning and stay
> silent when there's nothing.
>
> One caution: your topics, sources and watchlist are stored in your own
> online copy, which is public by default. Don't list anything you
> wouldn't want others to know you follow, or ask me how to make it
> private.
>
> List them, or type "None".

Write each name into the Watchlist block of `profile.md` with what counts
as news about it. If they ask about privacy: a private copy hides the
settings, needs a paid GitHub plan (about four dollars a month) for the
podcast address to keep working, and the audio itself stays reachable by
anyone who has the address. Offer to walk them through it after setup.

## Step 4 - Sources

> **Sources**
>
> I'll choose the news sources to match what you've told me. Any you
> particularly want included, or kept out?
>
> Type "Yes" to leave it to me, or name them.

Then do the work without narrating it, and without testing anything now:

1. `feeds.txt` already covers the ten default topics. Remove lanes for
   anything they dropped.
2. For each new interest, copy matching lines from `feeds-library.txt`, or
   build one using the patterns at the bottom of that file. Each watchlist
   name gets a Google News search line under the lane `Watchlist`, flagged
   `RARE`. For each source they asked for by name, add its RSS feed; if
   you are not sure of the address, use a Google News `site:` search for
   that publication instead, which almost always works.
3. Commit and push `feeds.txt`. Do NOT run a news build to test it: that
   added three builds and several minutes to the first real setup. The
   first episode's own build (step 6) is the test.
4. If they named a paid publication, tell them in one line: "The
   Financial Times and similar paid sites only give me headlines and short
   summaries, not full articles."

**After the first episode is out** (step 6), read "SOURCES THAT FAILED
TODAY" at the end of `digest.txt`. For each source YOU added that failed,
swap in a Google News `site:` search and push; tomorrow's build picks it
up. Mention it to the listener only if a source they asked for by name
could not be found at all. Everything else is repaired by the weekly
review.

## Step 5 - Format

Send one message:

> **How it sounds**
>
> The default:
> - **Length:** about eight minutes
> - **Tone:** crisp and analytical, with one dry joke in the weather
> - **Opens with:** the weather, then how the day's biggest stories connect
> - **Voice:** British, female, at a measured pace
> - **Ready by:** 6:45 each morning, every day
>
> Type "Yes", or change anything (e.g. "five minutes", "no weather",
> "weekdays only", "ready by 6", "a male voice").
>
> Two things I need: **which town or city is the weather for, and what
> should the show be called?** ("Morning Briefing" is fine.)

Your first episode is made straight after this, whatever the ready-by
time: if they answer "now" or "as soon as possible" to the time, that is
about the first episode, so keep the default daily time and say so in one
line.

Apply the answers in `config.json`:

- Length: about 150 words a minute at this pace. Set `words.target`, with
  `min` about 13% below and `max` about 9% above, and scale each section
  budget by the same proportion.
- Weather place: set `place`, `lat` and `lon` (look the coordinates up;
  confirm them in the next digest's WEATHER block). "No weather" sets
  `enabled` to false.
- Time zone: set `timezone` from their city (an IANA name such as
  `Europe/London`). Ask only if the city leaves it unclear.
- Voice: British female `bf_isabella` (default) or `bf_emma`; British
  male `bm_george` or `bm_lewis`; American female `af_heart` or `af_bella`;
  American male `am_michael`. American voices need `language` set to
  `en-us`.
- Ready-by time: explain once, only if they ask for earlier than 6:00,
  that about a third of each day's news arrives overnight, so a very early
  episode misses some of it.
- If a place or name is likely to be mispronounced, add it to
  `pronunciations`.

Tone requests ("funnier", "like a particular show") go in the "Tone and
weather" block of `profile.md`, and, if they change the whole register,
replace the register paragraph in `house-style.md` section 1. Original
writing only: never imitate or quote a real performer's material.

## Step 6 - The first episode

Work out a ready time: now plus twenty minutes, in their time zone,
rounded up to the next five minutes. Then:

> Thank you, that's everything I need. I'm writing your first episode now
> from today's news. **It will be ready by about [time].** I'll send you
> the link to add to [their app] the moment it is.

Then:

1. Run the day exactly as `daily-run.md` describes, from step 2 (fresh
   news, Part A, Part B).
2. When `tools/check_render.py` reports the episode rendered, confirm the
   address is live: list workflow runs again and find a **pages build and
   deployment** run that finished successfully after the render. If there
   is none after three minutes, go back to Check B in step 1.

## Step 7 - On their phone

Build the addresses from the remote, capitals kept:

- feed: `https://<owner>.github.io/<Repository>/feed.xml`
- page: `https://<owner>.github.io/<Repository>/`

Send the instructions for their app, with the feed address on its own
line so it can be copied:

- **Apple Podcasts:** "Open Podcasts. Tap **Library**, then the **three
  dots** at the top right, then **Follow a Show by URL**. Paste the
  address below and tap **Follow**."
- **Pocket Casts:** "Tap **Discover**, paste the address into the search
  box, and tap **Subscribe**."
- **AntennaPod (Android):** "Tap **Add Podcast**, then **Add podcast by
  RSS address**, and paste the address."
- **Overcast:** "Tap **+**, then **Add URL**, and paste the address."
- **Spotify cannot do this.** Suggest Apple Podcasts on iPhone or Pocket
  Casts on Android (both free).

> Your first episode is ready. [instructions and address]
>
> **Please press play and listen for ten seconds, then tell me it's
> working** - or tell me what you see if it isn't. After that, tell me
> anything you'd change, or type "Yes" and I'll set it to arrive every
> morning.

If it does not play, diagnose before asking them to wait:

- Ask them to open the page address in a browser. Page not found: the
  address is wrong (check capitals) or Check B was never passed. Page
  loads but the player says "Error": the audio link is wrong; check the
  enclosure addresses in `feed.xml` on the `gh-pages` branch.
- The show appears but the episode is "temporarily unavailable" or has
  no artwork: same cause, the links inside the feed.

Apply any feedback to `profile.md` or `config.json`. To let them hear a
change, re-run the day and tell them to pull down to refresh. To
re-render a day after their local midnight has passed, start
`podcast.yml` by hand with its `episode_date` input set to that day.

## Step 8 - Switch on the daily run

Create four scheduled tasks **in this session** (so each fires back into
this same chat, which is the only one with permission to publish). Use the
scheduled-task tool (`create_trigger`), with no `persistent_session_id`
and without `create_new_session_on_fire`, and `initiation` set to
`human_request`. Write every schedule in their own time zone using the
`CRON_TZ=<their zone>` prefix.

| Name | When | Prompt |
|---|---|---|
| Daily briefing | 45 minutes before the ready-by time (06:00 for 06:45), on their chosen days | `Daily briefing run. Follow daily-run.md in this repository exactly, starting at step 1.` |
| Briefing backup check | 2 hours 30 minutes after the daily run, same days | `Backup check. Follow the "Backup check" section of daily-run.md.` |
| Briefing late check | 13:10, same days | `Backup check. Follow the "Backup check" section of daily-run.md.` |
| Weekly self-review | Sundays at 16:20 | `Weekly self-review. Follow weekly-review.md in this repository exactly.` |

The 45 minutes is a buffer: the run takes about twenty, and scheduled
tasks often start several minutes late.

Confirm all four with `list_triggers`. Record their ids in
`setup-progress.md`.

Also schedule one message to yourself three days from now (`send_later`,
`initiation` `human_request`): `Day-three check-in: ask the listener, in
two lines, whether anything in the briefing should change, and apply what
they say.`

Change `SETUP STATUS` in `profile.md` to `complete`, tick the step, commit
and push.

## Step 9 - Close

> You're all set. A new episode will be in [their app] by [time] every
> [day/weekday].
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

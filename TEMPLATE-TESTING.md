# Testing the briefing template before anyone else sees it

The `template/` folder on this branch is the shareable version of the
briefing. Nothing in it runs while it sits inside this repository. This
page is the test plan. It is for the owner and is NOT copied into the
template.

## 1. Move it into its own repository

1. On GitHub, create a new **empty** repository (no README), for example
   `morning-briefing-template`. Private is fine for now.
2. Tell Claude its name. Claude copies everything in `template/` to the
   root of that repository and pushes.
3. In the new repository: **Settings → General → tick "Template
   repository"**.
4. When the tests below pass, make it public (private templates can only
   be used by you).

## 2. The dry run: be the new listener

Use a GitHub account that has never seen this project (a second account
of your own is ideal), and do it on a phone where you can.

| # | Step | Passes when |
|---|---|---|
| 1 | Open the template link, press **Use this template**, create a copy | The copy exists, with a green "Actions" tab |
| 2 | Connect Claude at claude.ai/connect-github and pick the copy | The copy appears in the Code tab's repository list |
| 3 | Start a session on the copy and type "hello" | Claude sends the welcome and asks the two questions, with no mention of files |
| 4 | Answer "yes" to everything | Each of the ten topics arrives one at a time; nothing stalls on a permission prompt |
| 5 | Close the tab halfway through, reopen, say "hi" | Claude resumes at the next unanswered step |
| 6 | Let it build the first episode | An episode is live within about fifteen minutes |
| 7 | **Pages:** does the podcast address work straight away? | Either it works, or Claude gives the one-tap instruction and it works after |
| 8 | Follow the phone instructions | The show appears in the podcast app with cover art and plays |
| 9 | Ask for a change ("make it five minutes", "follow Tesco") | Claude changes it and confirms in one line |
| 10 | Check the four scheduled tasks exist | Daily, two backups and weekly, in local time |

## 3. Leave it alone for a week

| Check | Passes when |
|---|---|
| First unattended morning | Episode is live by the chosen time. This is the test of the publish permission. |
| Every morning | `run-log.md` gains one OK line a day |
| Word count and shape | Lengths stay in the band; weather stays two sentences; the "how they connect" opening appears on most days |
| Continuity | At least one link back of the form "On Thursday we said ... today ..." and never "as previously flagged" |
| Memory | `archive/` never holds more than seven files; `threads.md` never more than twelve lines |
| Sunday | A `Weekly review` commit appears and `this-week.md` is rewritten |
| Usage | Note how much of the weekly Claude allowance one day costs. This decides which plan a listener needs. |

## 4. Break it on purpose

| Break | Passes when |
|---|---|
| Put a dead address in `feeds.txt` | It is logged daily, and the next weekly review repairs or switches it off |
| Paste twenty lines into `threads.md` | The next run cuts it back to twelve |
| Disable the daily task for one morning | The backup check publishes a late episode |
| Ask for a re-run after the day is published | The same day is replaced, not duplicated |

## 5. Not yet proven (the dry run settles these)

- Whether GitHub switches the podcast website on by itself in a fresh copy.
- Whether a fresh Claude session has the tool that starts the news build
  (the fallback is a local build, which works but loses a few sources).
- Whether "yes" to the first onboarding question is enough for unattended
  publishing on day two.
- Whether a fresh session will work on `main` without further prompting.
- The voice render with the new settings file. The speech code itself is
  unchanged from the live pipeline, but it has only been tested here with
  the voice step stubbed out.

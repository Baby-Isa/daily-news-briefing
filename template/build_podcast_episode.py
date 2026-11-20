#!/usr/bin/env python3
"""
TURN briefing.txt INTO A PODCAST EPISODE.

Reads the plain-text briefing (written by the daily Claude run),
renders it to speech with Kokoro (kokoro-onnx, a small local
open-weight neural TTS model), converts to MP3 with ffmpeg, and updates
a podcast RSS feed in a site directory ready to publish via GitHub
Pages.

This runs in GitHub Actions, not in the Claude Code Remote sandbox: it
needs ffmpeg, which the sandbox can't reliably install over its proxy.

Design decisions worth knowing:

- Kokoro, not edge-tts or Piper. It's Apache 2.0 (no license questions),
  runs entirely offline once its ~350MB of model+voice-bank files are
  downloaded (no account, no per-request network call, nothing an
  upstream service can rate-limit or block), and it topped the TTS
  Arena leaderboard in early 2026 - genuinely better quality than
  either prior engine by most accounts, at a real CPU cost (measured
  locally at roughly 0.4x real-time: about 9-10 minutes to render a
  full ~3,500-word briefing on a shared 2-vCPU runner). The voice,
  speed, show title and time zone all come from config.json.

- No manual chunking. Kokoro's own .create() call already splits long
  text into <=510-phoneme batches internally (preferring punctuation
  boundaries) and concatenates the results before returning - the
  chunk_text() logic every previous engine needed here is simply not
  necessary with Kokoro's API.

- The gh-pages branch is rebuilt as a fresh orphan commit every run,
  keeping only the retained episodes. Without this, deleted MP3s would
  still bloat the branch's git history forever; an orphan commit means
  the branch's on-disk size is always just "however many episodes we
  kept," never "every episode ever published."
"""

import datetime
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

# Everything personal lives in config.json, never in this file.
CONFIG = json.load(open("config.json", encoding="utf-8"))
LOCAL_TZ = ZoneInfo(CONFIG.get("timezone", "Europe/London"))
RETENTION_DAYS = int(CONFIG.get("episodes_kept", 14))

# Words the voice reads wrong from the correct spelling go in config.json
# under "pronunciations", as  "Written": "Spoken"  - for example
# "Ruislip": "Rye-slip". This is voice-only: it is applied to a copy of the
# text right before synthesis, never to briefing.txt or the feed
# description, which keep the real spelling. Matching is whole-word and
# case-insensitive.
PRONUNCIATION_FIXES = CONFIG.get("pronunciations", {})


def apply_pronunciation_fixes(text):
    for written, spoken in PRONUNCIATION_FIXES.items():
        text = re.sub(rf"\b{re.escape(written)}\b", spoken, text, flags=re.IGNORECASE)
    return text

PODCAST_TITLE = CONFIG.get("show_title", "Morning Briefing")
PODCAST_DESCRIPTION = CONFIG.get("show_description", "A personal daily news briefing, read aloud.")
PODCAST_AUTHOR = PODCAST_TITLE

# Full voice list: https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
VOICE = CONFIG.get("voice", "bf_isabella")
LANG = CONFIG.get("language", "en-gb")
PODCAST_LANGUAGE = LANG
SPEED = float(CONFIG.get("speed", 0.9))
MODEL_PATH = os.environ.get("KOKORO_MODEL_PATH", "models/kokoro-v1.0.onnx")
VOICES_PATH = os.environ.get("KOKORO_VOICES_PATH", "models/voices-v1.0.bin")


def make_cover(path):
    """Draw simple square cover art carrying the show title.

    Podcast apps show a grey box without one. Best effort: if Pillow or a
    font is missing the episode still publishes, just without artwork.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        size = 1400
        img = Image.new("RGB", (size, size), (18, 32, 47))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, size - 36, size, size], fill=(214, 164, 72))
        try:
            bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            big = ImageFont.truetype(bold, 150)
            small = ImageFont.truetype(bold, 54)
        except OSError:
            return False
        words, lines, line = PODCAST_TITLE.split(), [], ""
        for w in words:
            trial = (line + " " + w).strip()
            if draw.textlength(trial, font=big) > size - 240 and line:
                lines.append(line)
                line = w
            else:
                line = trial
        lines.append(line)
        y = 300
        for ln in lines[:4]:
            draw.text((120, y), ln, font=big, fill=(245, 240, 230))
            y += 190
        draw.text((120, size - 190), "DAILY  ·  READ ALOUD", font=small, fill=(214, 164, 72))
        img.save(path, "PNG")
        return True
    except Exception as e:  # never let artwork stop an episode
        print(f"Cover art skipped: {type(e).__name__}: {e}")
        return False


def synthesize_episode(briefing_text, work_dir, episode_mp3_path):
    # Imported here, not at module level, so the rest of this script (feed
    # logic, retention pruning) stays importable/testable without kokoro_onnx
    # and its heavier dependencies (onnxruntime, soundfile) installed.
    from kokoro_onnx import Kokoro
    import soundfile as sf

    print(f"Loading Kokoro model (voice {VOICE}, lang {LANG})...")
    kokoro = Kokoro(MODEL_PATH, VOICES_PATH)

    spoken_text = apply_pronunciation_fixes(briefing_text)
    print(f"Synthesizing {len(spoken_text)} characters...")
    samples, sample_rate = kokoro.create(spoken_text, voice=VOICE, speed=SPEED, lang=LANG)

    wav_path = os.path.join(work_dir, "episode.wav")
    sf.write(wav_path, samples, sample_rate)

    subprocess.run(
        ["ffmpeg", "-y", "-i", wav_path, "-c:a", "libmp3lame", "-q:a", "4", episode_mp3_path],
        check=True,
    )
    os.remove(wav_path)


def get_duration_seconds(mp3_path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", mp3_path,
        ],
        check=True, capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def format_duration(seconds):
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def load_existing_items(feed_path):
    """Return existing <item> elements as dicts, oldest concerns aside."""
    if not os.path.exists(feed_path):
        return []
    tree = ET.parse(feed_path)
    items = []
    for item in tree.getroot().find("channel").findall("item"):
        enclosure = item.find("enclosure")
        items.append({
            "title": item.findtext("title", ""),
            "description": item.findtext("description", ""),
            "pubDate": item.findtext("pubDate", ""),
            "guid": item.findtext("guid", ""),
            "url": enclosure.get("url") if enclosure is not None else "",
            "length": enclosure.get("length") if enclosure is not None else "0",
            "type": enclosure.get("type") if enclosure is not None else "audio/mpeg",
            "duration": item.findtext("{http://www.itunes.com/dtds/podcast-1.0.dtd}duration", ""),
        })
    return items


def build_feed_xml(items, feed_url, site_url, cover_url=None):
    ET.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
    itunes_ns = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"

    # register_namespace + the itunes_ns-qualified tags below make ElementTree
    # emit the xmlns:itunes declaration itself - adding it here too would
    # duplicate the attribute and make the written file unparseable.
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = PODCAST_TITLE
    ET.SubElement(channel, "link").text = site_url
    ET.SubElement(channel, "description").text = PODCAST_DESCRIPTION
    ET.SubElement(channel, "language").text = PODCAST_LANGUAGE
    ET.SubElement(channel, itunes_ns + "author").text = PODCAST_AUTHOR
    ET.SubElement(channel, itunes_ns + "explicit").text = "false"
    # A personal feed: ask directories not to list it.
    ET.SubElement(channel, itunes_ns + "block").text = "Yes"
    if cover_url:
        ET.SubElement(channel, itunes_ns + "image", {"href": cover_url})
        image = ET.SubElement(channel, "image")
        ET.SubElement(image, "url").text = cover_url
        ET.SubElement(image, "title").text = PODCAST_TITLE
        ET.SubElement(image, "link").text = site_url
    atom_link = ET.SubElement(channel, "{http://www.w3.org/2005/Atom}link")
    atom_link.set("href", feed_url)
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    # newest first
    for it in sorted(items, key=lambda x: x["pubDate"], reverse=True):
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = it["title"]
        ET.SubElement(item, "description").text = it["description"]
        ET.SubElement(item, "pubDate").text = it["pubDate"]
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = it["guid"]
        ET.SubElement(item, "enclosure", {
            "url": it["url"], "length": str(it["length"]), "type": it["type"],
        })
        if it.get("duration"):
            ET.SubElement(item, itunes_ns + "duration").text = it["duration"]

    return ET.ElementTree(rss)


def main():
    briefing_path = sys.argv[1] if len(sys.argv) > 1 else "briefing.txt"
    site_dir = sys.argv[2] if len(sys.argv) > 2 else "_site"
    pages_base_url = os.environ["PAGES_BASE_URL"].rstrip("/").lower()  # e.g. https://someone.github.io/my-briefing

    if not os.path.exists(briefing_path):
        print(f"No {briefing_path} found - nothing to do.")
        return

    with open(briefing_path, "r", encoding="utf-8") as f:
        briefing_text = f.read().strip()

    # The episode is dated in the listener's own time zone, not UTC.
    today = datetime.datetime.now(LOCAL_TZ).date()
    date_str = today.isoformat()

    audio_dir = os.path.join(site_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    episode_filename = f"{date_str}.mp3"
    episode_path = os.path.join(audio_dir, episode_filename)

    work_dir = "_tts_work"
    os.makedirs(work_dir, exist_ok=True)
    synthesize_episode(briefing_text, work_dir, episode_path)

    duration = get_duration_seconds(episode_path)
    size_bytes = os.path.getsize(episode_path)
    print(f"Episode built: {episode_path} ({size_bytes / 1_000_000:.1f} MB, {format_duration(duration)})")

    feed_path = os.path.join(site_dir, "feed.xml")
    existing_items = load_existing_items(feed_path)
    existing_items = [it for it in existing_items if not it["guid"].endswith(date_str)]

    weekday_date = today.strftime("%A %d %B %Y")
    description_snippet = briefing_text[:280].rsplit(" ", 1)[0] + "…"
    new_item = {
        "title": f"Briefing — {weekday_date}",
        # Raw text, not html.escape()'d: ElementTree XML-escapes .text content
        # itself on write, so escaping it here too would double-escape it
        # (a real bug this caught: "It's" became "It&amp;#x27;s" in the feed).
        "description": description_snippet,
        "pubDate": datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000"),
        "guid": f"daily-briefing-{date_str}",
        "url": f"{pages_base_url}/audio/{episode_filename}",
        "length": str(size_bytes),
        "type": "audio/mpeg",
        "duration": format_duration(duration),
    }
    all_items = existing_items + [new_item]

    # Prune anything past the retention window, and delete its audio file.
    cutoff = today - datetime.timedelta(days=RETENTION_DAYS)
    kept, dropped = [], []
    for it in all_items:
        try:
            item_date = datetime.date.fromisoformat(it["guid"].replace("daily-briefing-", ""))
        except ValueError:
            kept.append(it)  # unknown format - keep rather than risk losing it
            continue
        (kept if item_date >= cutoff else dropped).append(it)

    for it in dropped:
        fname = it["url"].rsplit("/", 1)[-1]
        fpath = os.path.join(audio_dir, fname)
        if os.path.exists(fpath):
            os.remove(fpath)
            print(f"Pruned episode past retention window: {fname}")

    feed_url = f"{pages_base_url}/feed.xml"
    cover_url = f"{pages_base_url}/cover.png" if make_cover(os.path.join(site_dir, "cover.png")) else None
    tree = build_feed_xml(kept, feed_url, pages_base_url, cover_url)
    tree.write(feed_path, encoding="utf-8", xml_declaration=True)
    print(f"Feed updated: {feed_path} ({len(kept)} episode(s) retained)")

    # A plain page for the feed address: play the latest episode in a
    # browser, and copy the feed link into a podcast app. Rewritten every
    # run so it always points at today. noindex keeps it out of search.
    newest = sorted(kept, key=lambda x: x["guid"], reverse=True)[0]
    with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(
            "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<meta name='robots' content='noindex, nofollow'>"
            f"<title>{PODCAST_TITLE}</title>"
            "<style>body{font-family:system-ui,sans-serif;max-width:34rem;margin:3rem auto;"
            "padding:0 1rem;line-height:1.5;color:#12202f}audio{width:100%}"
            "code{word-break:break-all;background:#f1ede4;padding:.2rem .4rem}</style></head><body>"
            f"<h1>{PODCAST_TITLE}</h1>"
            f"<p>{newest['title']} ({newest['duration']})</p>"
            f"<audio controls src='{newest['url']}'></audio>"
            "<p>To get this every morning, add this address to your podcast app "
            "(in Apple Podcasts: Library, then the three dots, then "
            "<em>Follow a Show by URL</em>):</p>"
            f"<p><code>{feed_url}</code></p>"
            "</body></html>"
        )
    # Tell GitHub Pages to serve the files as they are.
    open(os.path.join(site_dir, ".nojekyll"), "w").close()


if __name__ == "__main__":
    main()

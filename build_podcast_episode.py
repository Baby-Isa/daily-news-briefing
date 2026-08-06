#!/usr/bin/env python3
"""
TURN briefing.txt INTO A PODCAST EPISODE.

Reads the plain-text briefing (written by the Cowork Routine each
morning), renders it to speech with Kokoro (kokoro-onnx, a small local
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
  full ~3,500-word briefing on a shared 2-vCPU runner). Voice is
  bf_isabella (British English, female) - user's pick.

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
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

RETENTION_DAYS = 14  # how many episodes stay in the feed

PODCAST_TITLE = "Daily Morning Briefing"
PODCAST_DESCRIPTION = "A personal daily news briefing, read aloud."
PODCAST_LANGUAGE = "en-gb"
PODCAST_AUTHOR = "Daily News Briefing"

# bf_isabella: British English, female - user's pick. Full voice list at
# https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
VOICE = os.environ.get("KOKORO_VOICE", "bf_isabella")
LANG = os.environ.get("KOKORO_LANG", "en-gb")
SPEED = float(os.environ.get("KOKORO_SPEED", "1.0"))
MODEL_PATH = os.environ.get("KOKORO_MODEL_PATH", "models/kokoro-v1.0.onnx")
VOICES_PATH = os.environ.get("KOKORO_VOICES_PATH", "models/voices-v1.0.bin")


def synthesize_episode(briefing_text, work_dir, episode_mp3_path):
    # Imported here, not at module level, so the rest of this script (feed
    # logic, retention pruning) stays importable/testable without kokoro_onnx
    # and its heavier dependencies (onnxruntime, soundfile) installed.
    from kokoro_onnx import Kokoro
    import soundfile as sf

    print(f"Loading Kokoro model (voice {VOICE}, lang {LANG})...")
    kokoro = Kokoro(MODEL_PATH, VOICES_PATH)

    print(f"Synthesizing {len(briefing_text)} characters...")
    samples, sample_rate = kokoro.create(briefing_text, voice=VOICE, speed=SPEED, lang=LANG)

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


def build_feed_xml(items, feed_url, site_url):
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
    pages_base_url = os.environ["PAGES_BASE_URL"].rstrip("/")  # e.g. https://baby-isa.github.io/daily-news-briefing

    if not os.path.exists(briefing_path):
        print(f"No {briefing_path} found - nothing to do.")
        return

    with open(briefing_path, "r", encoding="utf-8") as f:
        briefing_text = f.read().strip()

    today = datetime.datetime.now(datetime.timezone.utc).date()
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
    tree = build_feed_xml(kept, feed_url, pages_base_url)
    tree.write(feed_path, encoding="utf-8", xml_declaration=True)
    print(f"Feed updated: {feed_path} ({len(kept)} episode(s) retained)")

    index_path = os.path.join(site_dir, "index.html")
    if not os.path.exists(index_path):
        with open(index_path, "w") as f:
            f.write(
                f"<!doctype html><html><head><meta charset='utf-8'>"
                f"<title>{PODCAST_TITLE}</title></head><body>"
                f"<h1>{PODCAST_TITLE}</h1>"
                f"<p>Podcast feed: <a href='feed.xml'>feed.xml</a></p>"
                f"</body></html>"
            )


if __name__ == "__main__":
    main()

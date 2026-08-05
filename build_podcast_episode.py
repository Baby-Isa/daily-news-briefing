#!/usr/bin/env python3
"""
TURN briefing.txt INTO A PODCAST EPISODE.

Reads the plain-text briefing (written by the Cowork Routine each
morning), renders it to speech with Piper (a local, offline neural TTS
engine), stitches the pieces into one MP3 with ffmpeg, and updates a
podcast RSS feed in a site directory ready to publish via GitHub Pages.

This runs in GitHub Actions, not in the Claude Code Remote sandbox: it
needs ffmpeg, which the sandbox can't reliably install over its proxy.
The briefing text itself is produced upstream by a Claude session,
which is the part that actually needs judgement; this script is purely
mechanical.

Design decisions worth knowing:

- Piper, not a cloud TTS API. It runs entirely offline once the voice
  model is downloaded, so there's no account, no billing, no quota,
  and nothing that can rate-limit or silently break an unattended
  daily job. The trade is a voice that's good but a notch more
  synthetic than a commercial neural API - worth it for something that
  has to "just work" every morning with no one watching.

- No hard chunk-size limit to respect (Piper has none), but the text
  is still split on paragraph boundaries so each synthesis call stays
  small: a bad chunk fails cheaply, and per-paragraph calls keep
  memory bounded on the runner. The sentence-level fallback for an
  overlong paragraph is kept as a defensive backstop.

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

MAX_CHUNK_BYTES = 20000  # generous; Piper has no request-size limit to respect
RETENTION_DAYS = 14      # how many episodes stay in the feed

PODCAST_TITLE = "Daily Morning Briefing"
PODCAST_DESCRIPTION = "A personal daily news briefing, read aloud."
PODCAST_LANGUAGE = "en-gb"
PODCAST_AUTHOR = "Daily News Briefing"

# PIPER_MODEL_PATH / PIPER_CONFIG_PATH point at the .onnx + .onnx.json the
# workflow downloads and caches. Voice tier is being A/B'd between
# en_GB-cori-medium (confirmed ~82s to render a ~4,500-word briefing on
# GitHub's shared runners, from real step timestamps) and en_GB-cori-high
# (better quality, timing not yet confirmed) - see whichever is currently
# wired up in podcast.yml.
LENGTH_SCALE = os.environ.get("PIPER_LENGTH_SCALE", "1.0")        # >1 slower, <1 faster
SENTENCE_SILENCE = os.environ.get("PIPER_SENTENCE_SILENCE", "0.3")  # seconds of pause between sentences


def chunk_text(text, max_bytes=MAX_CHUNK_BYTES):
    """Split into pieces under max_bytes, breaking on paragraph then
    sentence boundaries so no chunk ever cuts off mid-sentence."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    def fits(candidate):
        return len(candidate.encode("utf-8")) <= max_bytes

    for para in paragraphs:
        candidate = (current + "\n\n" + para).strip() if current else para
        if fits(candidate):
            current = candidate
            continue
        # Current chunk is full; flush it.
        if current:
            chunks.append(current)
            current = ""
        if fits(para):
            current = para
            continue
        # A single paragraph is itself too long: split on sentences.
        sentences = para.replace("\n", " ").split(". ")
        piece = ""
        for i, sentence in enumerate(sentences):
            s = sentence if sentence.endswith(".") or i == len(sentences) - 1 else sentence + "."
            candidate = (piece + " " + s).strip() if piece else s
            if fits(candidate):
                piece = candidate
            else:
                if piece:
                    chunks.append(piece)
                piece = s
        if piece:
            current = piece

    if current:
        chunks.append(current)
    return chunks


def synthesize_chunk(text, model_path, config_path, out_path):
    subprocess.run(
        [
            "piper",
            "--model", model_path,
            "--config", config_path,
            "--output_file", out_path,
            "--length-scale", LENGTH_SCALE,
            "--sentence-silence", SENTENCE_SILENCE,
        ],
        input=text, capture_output=True, text=True, check=True,
    )


def synthesize_episode(briefing_text, model_path, config_path, work_dir, episode_mp3_path):
    chunks = chunk_text(briefing_text)
    if not chunks:
        raise RuntimeError("briefing.txt produced no text chunks to synthesize")
    print(f"Synthesizing {len(chunks)} chunk(s) with Piper ({os.path.basename(model_path)})...")

    chunk_paths = []
    for i, chunk in enumerate(chunks):
        out_path = os.path.join(work_dir, f"chunk_{i:03d}.wav")
        synthesize_chunk(chunk, model_path, config_path, out_path)
        chunk_paths.append(out_path)
        print(f"  chunk {i + 1}/{len(chunks)}: {len(chunk)} chars -> {out_path}")

    # Always route through ffmpeg, even for a single chunk: Piper only
    # ever produces WAV, and the episode needs to end up as MP3.
    concat_list_path = os.path.join(work_dir, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for p in chunk_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list_path,
            "-c:a", "libmp3lame", "-q:a", "4",
            episode_mp3_path,
        ],
        check=True,
    )
    for p in chunk_paths:
        os.remove(p)


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
    model_path = os.environ["PIPER_MODEL_PATH"]
    config_path = os.environ["PIPER_CONFIG_PATH"]

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
    synthesize_episode(briefing_text, model_path, config_path, work_dir, episode_path)

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

#!/usr/bin/env python3
"""
Shared fetching, with escalation.

Lesson from the previous version, which broke 35 working feeds: do NOT
send elaborate browser headers by default. Two specific traps, both hit:

  - Accept-Encoding with "br" (Brotli) requires a library that is not
    installed by default. Without it the body arrives as raw compressed
    bytes and the parser reports zero items even though the fetch
    succeeded. We now leave Accept-Encoding alone entirely and let
    requests negotiate only what it can actually decode.

  - Sec-Fetch-Mode: navigate, plus text/html in Accept, tells a server
    this is a browser opening a page. Several then returned the HTML
    article listing instead of the feed.

So: start simple, escalate only when a request is actually refused.
Most sites want a plain feed request. A handful want to see a browser.
Escalating for everyone breaks the majority to please the few.
"""

import threading
import time
from urllib.parse import urlparse

import requests

TIMEOUT = 25
ATTEMPTS = 3

# Per-domain rate limiting.
#
# Every Google News feed failed with 503 in one run while succeeding
# individually in another. That is rate limiting, not blocking: eight
# parallel workers hitting one host looks like abuse from a single
# datacenter address. Some hosts need requests spaced out, so we hold a
# per-domain lock and enforce a minimum gap.
MIN_INTERVAL = {
    "news.google.com": 3.0,
    "www.travelweekly.co.uk": 10.0,
    "restofworld.org": 10.0,
}
_last_request = {}
_rate_lock = threading.Lock()


def _throttle(url):
    """Wait if this domain needs spacing between requests."""
    host = urlparse(url).netloc
    gap = MIN_INTERVAL.get(host)
    if not gap:
        return
    while True:
        with _rate_lock:
            now = time.monotonic()
            last = _last_request.get(host, 0.0)
            wait = gap - (now - last)
            if wait <= 0:
                _last_request[host] = now
                return
        time.sleep(wait)

# Level 1: what a feed reader sends. This is what worked for 106 feeds.
# Note the deliberate absence of Accept-Encoding.
FEED_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": ("application/rss+xml, application/atom+xml, "
               "application/xml;q=0.9, text/xml;q=0.9, */*;q=0.5"),
    "Accept-Language": "en-GB,en;q=0.9",
}

# Level 2: a declared feed reader. Some sites allow these while
# blocking anything that looks like a generic script.
READER_HEADERS = {
    "User-Agent": "FeedFetcher-Google; (+http://www.google.com/feedfetcher.html)",
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
}

# Level 3: a full browser fingerprint. Only for sites refusing both of
# the above. This is the header set that broke everything as a default.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.4 Safari/605.1.15"
    ),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/webp,*/*;q=0.8"),
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}

BLOCKED_CODES = (401, 403, 429)


def _looks_like_feed(resp):
    """Reject an HTML page served where a feed was expected."""
    head = resp.content[:600].lstrip()
    if head.startswith(b"<?xml") or b"<rss" in head or b"<feed" in head:
        return True
    if b"<rdf:RDF" in head:
        return True
    ctype = resp.headers.get("Content-Type", "").lower()
    if "html" in ctype and b"<rss" not in resp.content[:3000]:
        return False
    return True


def fetch(url):
    """Fetch a URL, escalating politely if refused.

    Returns (response, note). response is None if all attempts failed.
    """
    last = "no attempt made"

    for attempt in range(ATTEMPTS):
        try:
            _throttle(url)
            resp = requests.get(url, headers=FEED_HEADERS, timeout=TIMEOUT,
                                allow_redirects=True)

            if resp.status_code == 200:
                if _looks_like_feed(resp):
                    return resp, "ok"
                # HTML served where a feed was expected: try the reader
                # identity, which some sites use to decide what to send.
                try:
                    alt = requests.get(url, headers=READER_HEADERS,
                                       timeout=TIMEOUT, allow_redirects=True)
                    if alt.status_code == 200 and _looks_like_feed(alt):
                        return alt, "ok (needed feed-reader identity)"
                except requests.RequestException:
                    pass
                return resp, "warning: response looks like HTML, not a feed"

            if resp.status_code == 429:
                # Explicitly "slow down". Wait properly and retry.
                last = "HTTP 429 (rate limited)"
                time.sleep(min(30, 8 * (2 ** attempt)))
                continue

            if resp.status_code in BLOCKED_CODES:
                for label, hdrs in (("feed-reader", READER_HEADERS),
                                    ("browser", BROWSER_HEADERS)):
                    try:
                        alt = requests.get(url, headers=hdrs, timeout=TIMEOUT,
                                           allow_redirects=True)
                        if alt.status_code == 200:
                            return alt, f"ok (needed {label} identity)"
                    except requests.RequestException:
                        pass
                return None, (f"HTTP {resp.status_code} - refused all three "
                              f"identities, likely datacenter IP blocking")

            # 415 means the server disliked our Accept header. Retry
            # once asking for anything at all.
            if resp.status_code == 415:
                try:
                    bare = {"User-Agent": FEED_HEADERS["User-Agent"]}
                    alt = requests.get(url, headers=bare, timeout=TIMEOUT,
                                       allow_redirects=True)
                    if alt.status_code == 200:
                        return alt, "ok (server rejected the Accept header)"
                except requests.RequestException:
                    pass
                return None, "HTTP 415 - server rejected our Accept header"

            if resp.status_code >= 500:
                last = f"HTTP {resp.status_code} (server error)"
                # Exponential, not linear: a 503 from a busy host needs
                # real time, not two seconds.
                time.sleep(min(30, 5 * (2 ** attempt)))
                continue

            return None, f"HTTP {resp.status_code}"

        except requests.exceptions.SSLError:
            try:
                resp = requests.get(url, headers=FEED_HEADERS, timeout=TIMEOUT,
                                    verify=False, allow_redirects=True)
                if resp.status_code == 200:
                    return resp, "ok (certificate problem, verification skipped)"
            except requests.RequestException:
                pass
            return None, "SSL certificate error"

        except requests.exceptions.RequestException as e:
            last = f"connection failed ({type(e).__name__})"
            time.sleep(2 * (attempt + 1))

    return None, f"{last} after {ATTEMPTS} attempts"

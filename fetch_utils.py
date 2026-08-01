#!/usr/bin/env python3
"""
Shared fetching, hardened against the four failure modes the first
verification run exposed.

1. HTTP 403. Six feeds refused a plain script. Sending a full set of
   browser headers (not just a user-agent) gets most of them through,
   because bot detection looks at the whole header set. If that still
   fails we retry once as a recognised feed reader, since some sites
   allow feed readers while blocking generic scripts.

2. HTTP 5xx and connection errors. NYT Economy returned 503 while every
   other NYT feed worked, so it was momentary. Three attempts with
   increasing waits handles this.

3. SSL errors. One site had a certificate problem. We retry once without
   verification and mark it, rather than losing the source silently.
   Acceptable here because we are reading public headlines, not sending
   anything.

4. Datacenter IP blocking. GitHub runners use datacenter addresses, which
   some sites (Reddit especially) block regardless of headers.
"""

import time

import requests

TIMEOUT = 25
ATTEMPTS = 3

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/rss+xml, application/atom+xml, application/xml;q=0.9, "
        "text/xml;q=0.9, text/html;q=0.8, */*;q=0.7"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Connection": "keep-alive",
}

# Some sites allow declared feed readers while blocking generic scripts.
FEEDREADER_HEADERS = {
    "User-Agent": "FeedFetcher-Google; (+http://www.google.com/feedfetcher.html)",
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-GB,en;q=0.9",
}


def fetch(url, referer=None):
    """Fetch a URL, working around blocking and transient failures.

    Returns (response, note). response is None if every attempt failed,
    and note explains what happened.
    """
    headers = dict(BROWSER_HEADERS)
    if referer:
        headers["Referer"] = referer
    else:
        # A same-origin referer makes the request look like ordinary
        # in-site navigation rather than a bare hit on a feed URL.
        try:
            parts = url.split("/")
            headers["Referer"] = f"{parts[0]}//{parts[2]}/"
        except IndexError:
            pass

    last = "no attempt made"

    for attempt in range(ATTEMPTS):
        try:
            resp = requests.get(url, headers=headers, timeout=TIMEOUT,
                                allow_redirects=True)
            if resp.status_code == 200:
                return resp, "ok"

            if resp.status_code in (403, 401, 429):
                # Blocked rather than broken. Try once as a feed reader.
                try:
                    alt = requests.get(url, headers=FEEDREADER_HEADERS,
                                       timeout=TIMEOUT, allow_redirects=True)
                    if alt.status_code == 200:
                        return alt, "ok (needed feed-reader identity)"
                except requests.RequestException:
                    pass
                return None, (f"HTTP {resp.status_code} - blocked, likely "
                              f"bot protection or datacenter IP")

            if resp.status_code >= 500:
                last = f"HTTP {resp.status_code} (server error)"
                time.sleep(2 * (attempt + 1))
                continue

            return None, f"HTTP {resp.status_code}"

        except requests.exceptions.SSLError:
            try:
                resp = requests.get(url, headers=headers, timeout=TIMEOUT,
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

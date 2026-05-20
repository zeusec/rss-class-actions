#!/usr/bin/env python3
import os
import re
import sys
import time
import yaml
import html
import signal
import base64
import sqlite3
import logging
import requests
import feedparser
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

REPO = Path(__file__).parent
FEEDS_FILE = REPO / "feeds.yaml"
DB_FILE = Path(os.environ.get("DB_FILE") or REPO / "seen.db")
AVATAR_FILE = REPO / "gavel.png"
WEBHOOK_NAME = "Class Action Alert"
DEFAULT_POLL_INTERVAL_MINUTES = 15
HTTP_TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.3"
EPOCH = time.struct_time((1970, 1, 1, 0, 0, 0, 0, 1, 0))

log = logging.getLogger("rss-class-actions")
_running = True

def _stop(*_):
    global _running
    _running = False

def strip_html(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()

def guid(entry):
    return getattr(entry, "id", None) or getattr(entry, "link", None)

def ts(entry):
    return getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)

def open_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS seen (feed_url TEXT, guid TEXT, posted_at INTEGER, PRIMARY KEY (feed_url, guid))")
    return conn

def mark_seen(conn, url, guids):
    now = int(time.time())
    conn.executemany("INSERT OR IGNORE INTO seen VALUES (?, ?, ?)", [(url, g, now) for g in guids])

def fetch_feed(url):
    try:
        r = requests.get(url, timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
    except requests.RequestException as e:
        return None, str(e)
    parsed = feedparser.parse(r.content)
    if parsed.bozo and not parsed.entries:
        return None, str(parsed.bozo_exception)
    return parsed, None

def set_webhook_identity(webhook):
    avatar = base64.b64encode(AVATAR_FILE.read_bytes()).decode()
    payload = {"name": WEBHOOK_NAME, "avatar": f"data:image/png;base64,{avatar}"}
    try:
        r = requests.patch(webhook, json=payload, timeout=HTTP_TIMEOUT)
        if r.status_code >= 400:
            log.warning("webhook patch %d: %s", r.status_code, r.text[:200])
    except requests.RequestException as e:
        log.warning("webhook patch failed: %s", e)

def build_embed(feed_name, entry):
    t = ts(entry)
    when = datetime(*t[:6], tzinfo=timezone.utc).strftime("%b %d, %H:%MZ") if t else ""
    footer = f"{when} • github.com/zeusec/rss-class-actions" if when else "github.com/zeusec/rss-class-actions"
    return {
        "author": {"name": feed_name[:256]},
        "title": (getattr(entry, "title", None) or "(no title)")[:256],
        "url": getattr(entry, "link", None),
        "description": strip_html(getattr(entry, "summary", ""))[:300],
        "footer": {"text": footer},
    }

def post_to_discord(webhook, embed):
    while _running:
        try:
            r = requests.post(webhook, json={"embeds": [embed]}, timeout=HTTP_TIMEOUT)
        except requests.RequestException as e:
            log.warning("discord post failed: %s", e)
            return False
        if r.status_code == 429:
            time.sleep(float(r.headers.get("Retry-After", "1")))
            continue
        if r.status_code >= 400:
            log.warning("discord %d: %s", r.status_code, r.text[:200])
            return False
        if int(r.headers.get("X-RateLimit-Remaining", "1")) <= 0:
            time.sleep(float(r.headers.get("X-RateLimit-Reset-After", "0")))
        return True
    return False

def poll_once(conn, feeds, webhook, backlog):
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=max(1, len(feeds))) as ex:
        fetched = list(ex.map(lambda f: (f, fetch_feed(f["url"])), feeds))
    log.info("fetched %d feeds in %.1fs", len(fetched), time.monotonic() - t0)
    seeded, pool = [], []
    for feed, (parsed, err) in fetched:
        if err:
            log.warning("%s: %s", feed["name"], err)
            continue
        url = feed["url"]
        visible = [(ts(e) or EPOCH, e, guid(e)) for e in parsed.entries if guid(e)]
        if not visible:
            continue
        untracked = conn.execute("SELECT 1 FROM seen WHERE feed_url=? LIMIT 1", (url,)).fetchone() is None
        if untracked:
            mark_seen(conn, url, [g for _, _, g in visible])
            seeded.append(feed["name"])
        if backlog > 0:
            pool.extend((t, feed, e, g) for t, e, g in visible)
        elif not untracked:
            existing = {row[0] for row in conn.execute("SELECT guid FROM seen WHERE feed_url=?", (url,))}
            pool.extend((t, feed, e, g) for t, e, g in visible if g not in existing)
    conn.commit()
    if seeded:
        log.info("first-encounter seeded %d feeds", len(seeded))
    pool.sort(key=lambda c: c[0], reverse=True)
    to_post = pool[:backlog] if backlog > 0 else pool
    posted = 0
    for _, feed, entry, g in reversed(to_post):
        if not _running:
            break
        if post_to_discord(webhook, build_embed(feed["name"], entry)):
            mark_seen(conn, feed["url"], [g])
            posted += 1
    conn.commit()
    log.info("posted %d (seeded=%d, backlog=%d)", posted, len(seeded), backlog)

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv(REPO / ".env")
    webhook = os.environ.get("DISCORD_WEBHOOK_URL") or sys.exit("DISCORD_WEBHOOK_URL not set")
    backlog = int(os.environ.get("BACKLOG") or 0)
    poll_interval_minutes = int(os.environ.get("POLL_INTERVAL") or DEFAULT_POLL_INTERVAL_MINUTES)
    if poll_interval_minutes < 1:
        sys.exit("POLL_INTERVAL must be >= 1 minute")
    poll_interval_seconds = poll_interval_minutes * 60
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    with open(FEEDS_FILE) as f:
        feeds = yaml.safe_load(f) or []
    conn = open_db()
    set_webhook_identity(webhook)
    log.info("starting: %d feeds, backlog=%d, poll_interval=%dm", len(feeds), backlog, poll_interval_minutes)
    while _running:
        poll_once(conn, feeds, webhook, backlog)
        backlog = 0
        for _ in range(poll_interval_seconds):
            if not _running:
                break
            time.sleep(1)
    conn.close()

if __name__ == "__main__":
    main()

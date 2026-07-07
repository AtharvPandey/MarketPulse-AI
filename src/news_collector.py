"""
news_collector.py
------------------
PHASE 1 of MarketPulse AI.

Job of this file (and only this file): pull fresh headlines from a few
trusted RSS feeds and save them as one clean JSON list.

It does NOT summarize, tag sectors, or pick stocks — that's Phase 2's job.
Keeping this file "dumb" on purpose (just fetch + clean) is what makes the
whole project modular: if a feed URL breaks, you only touch this file.
"""

import feedparser
import json
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# 1. THE SOURCES
# ---------------------------------------------------------------------------
# Each entry is: a human-readable name + the RSS feed URL for that source.
# Feel free to add/remove feeds here later -- this is the ONLY place you'd
# ever need to edit to change your news sources.

RSS_FEEDS = {
    "Moneycontrol - Latest News": "https://www.moneycontrol.com/rss/latestnews.xml",
    "Economic Times - Markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "LiveMint - Markets": "https://www.livemint.com/rss/markets",
    "Investing.com - Global Markets": "https://www.investing.com/rss/news.rss",
}

# Some news sites reject requests that don't look like they're coming from a
# real browser (they block Python's default "identity string" for bots/scrapers).
# Sending a normal browser User-Agent fixes this in most cases.
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
}

# How far back to look for "fresh" news. RSS feeds contain recent items,
# but we don't want month-old headlines sneaking in if a feed updates slowly.
FRESHNESS_WINDOW_HOURS = 15


def is_recent(published_time_struct, hours=FRESHNESS_WINDOW_HOURS):
    """
    Check whether a feed item was published within the last `hours` hours.

    RSS feeds give us the published date as a `time.struct_time` object
    (a slightly clunky Python format). We convert it to a real datetime
    and compare it to "now" minus our freshness window.
    """
    if not published_time_struct:
        # Some feed items don't include a timestamp at all -- we keep
        # them rather than silently dropping potentially useful news,
        # but flag this in the returned dict (see below).
        return True

    published_dt = datetime(*published_time_struct[:6], tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return published_dt >= cutoff


def fetch_feed(source_name, url):
    """
    Fetch and parse a single RSS feed, returning a clean list of headline
    dictionaries. If the feed fails (site down, bad URL, etc.), we don't
    crash the whole script -- we just skip that source and keep going.
    """
    collected = []
    try:
        parsed = feedparser.parse(url, request_headers=REQUEST_HEADERS)

        # Debug info: shows the HTTP status code (200 = OK, 403 = blocked,
        # 404 = feed doesn't exist) and how many total entries came back
        # BEFORE we filter for freshness. This tells us whether a "0 fresh
        # headlines" result means "feed is dead" or "just no recent news".
        http_status = parsed.get("status", "n/a")
        print(f"  [debug] HTTP status: {http_status}, "
              f"total entries in feed: {len(parsed.entries)}")

        # feedparser sets `bozo=1` when something went wrong parsing the feed
        # (e.g. malformed XML). We still try to use whatever entries came
        # back, but we print a warning so you know that source is flaky.
        if parsed.bozo:
            print(f"  [warning] '{source_name}' feed had parsing issues, "
                  f"continuing with whatever was recovered.")

        for entry in parsed.entries:
            published_struct = entry.get("published_parsed")

            if not is_recent(published_struct):
                continue  # skip stale news

            collected.append({
                "source": source_name,
                "title": entry.get("title", "").strip(),
                "link": entry.get("link", "").strip(),
                "published": (
                    datetime(*published_struct[:6], tzinfo=timezone.utc).isoformat()
                    if published_struct else None
                ),
            })

    except Exception as e:
        # Real-world lesson: a single broken feed should NEVER take down
        # your whole pipeline. We log the error and move on.
        print(f"  [error] Could not fetch '{source_name}': {e}")

    return collected


def collect_all_news():
    """
    Loop through every feed in RSS_FEEDS, collect fresh headlines from each,
    and return one combined list.
    """
    all_news = []
    print("Collecting news from all sources...\n")

    for source_name, url in RSS_FEEDS.items():
        print(f"Fetching: {source_name}")
        items = fetch_feed(source_name, url)
        print(f"  -> {len(items)} fresh headline(s) found\n")
        all_news.extend(items)

    return all_news


def save_to_json(news_items, filepath="../data/raw_news.json"):
    """
    Save the collected news as a JSON file -- this becomes the input for
    Phase 2 (the AI summarizer/sector-tagger).
    """
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(news_items, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(news_items)} total headlines to {filepath}")


def main():
    news = collect_all_news()
    save_to_json(news)


if __name__ == "__main__":
    main()
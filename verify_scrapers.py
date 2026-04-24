# -*- coding: utf-8 -*-
"""
Scraper verification script.
Tests each scraper independently with a short time window.
Does NOT run the AI pipeline or insert into Supabase.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
load_dotenv()

import httpx

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.scrapers.hackernews import HackerNewsScraper
from src.scrapers.rss import RSSScraper
from src.scrapers.reddit import RedditScraper
from src.scrapers.github import GitHubScraper
from src.scrapers.telegram import TelegramScraper
from src.domain.models import (
    HackerNewsConfig, RSSSourceConfig, RedditConfig, RedditSubredditConfig,
    GitHubSourceConfig, TelegramConfig, TelegramChannelConfig
)

# Use a wide window (7 days) so we always get results regardless of recent activity
SINCE = datetime.now(timezone.utc) - timedelta(days=7)

PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"
WARN = "[WARN]"

results = {}


async def test_hackernews(client):
    name = "HackerNews"
    try:
        cfg = HackerNewsConfig(enabled=True, fetch_top_stories=5, min_score=100)
        scraper = HackerNewsScraper(cfg, client)
        items = await scraper.fetch(SINCE)
        if items:
            print(f"  {PASS} {name}: fetched {len(items)} item(s)")
            print(f"       Sample: \"{items[0].title[:70]}\"")
            results[name] = "PASS"
        else:
            print(f"  {WARN} {name}: connected but 0 items returned (score threshold may be too high)")
            results[name] = "WARN"
    except Exception as e:
        print(f"  {FAIL} {name}: {e}")
        results[name] = "FAIL"


async def test_rss(client):
    name = "RSS"
    feeds = [
        RSSSourceConfig(name="EdSurge", url="https://feeds.feedburner.com/EdSurge", enabled=True, category="edtech"),
        RSSSourceConfig(name="TechCrunch Education", url="https://techcrunch.com/category/education/feed/", enabled=True, category="competitors"),
    ]
    passed = 0
    failed = 0
    for feed in feeds:
        try:
            scraper = RSSScraper([feed], client)
            items = await scraper.fetch(SINCE)
            if items:
                print(f"  {PASS} RSS [{feed.name}]: {len(items)} item(s)")
                print(f"       Sample: \"{items[0].title[:70]}\"")
                passed += 1
            else:
                print(f"  {WARN} RSS [{feed.name}]: 0 items (feed may be empty or slow)")
                passed += 1  # connected OK, just no recent items
        except Exception as e:
            print(f"  {FAIL} RSS [{feed.name}]: {e}")
            failed += 1
    results[name] = "FAIL" if failed == len(feeds) else ("WARN" if failed > 0 else "PASS")


async def test_reddit(client):
    name = "Reddit"
    # Reddit public JSON API – no credentials required
    cfg = RedditConfig(
        enabled=True,
        subreddits=[
            RedditSubredditConfig(subreddit="edtech", enabled=True, sort="hot",
                                  time_filter="week", fetch_limit=5, min_score=1),
        ],
        users=[],
        fetch_comments=0,
    )
    try:
        scraper = RedditScraper(cfg, client)
        items = await scraper.fetch(SINCE)
        if items:
            print(f"  {PASS} {name}: fetched {len(items)} item(s)")
            print(f"       Sample: \"{items[0].title[:70]}\"")
            results[name] = "PASS"
        else:
            print(f"  {WARN} {name}: 0 items (subreddit may be quiet or rate-limited)")
            results[name] = "WARN"
    except Exception as e:
        print(f"  {FAIL} {name}: {e}")
        results[name] = "FAIL"


async def test_github(client):
    name = "GitHub"
    # Public repos – no token required, but rate-limited to 60 req/hr unauthenticated
    token = os.environ.get("GITHUB_TOKEN")
    sources = [
        GitHubSourceConfig(type="repo_releases", owner="openSIS", repo="openSIS-Classic", enabled=True),
    ]
    try:
        scraper = GitHubScraper(sources, client)
        items = await scraper.fetch(SINCE)
        if items:
            print(f"  {PASS} {name}: fetched {len(items)} release(s)")
            print(f"       Sample: \"{items[0].title[:70]}\"")
            results[name] = "PASS"
        else:
            note = "(no token → 60 req/hr limit; no new releases in last 7 days is normal)" if not token else "(no new releases in last 7 days)"
            print(f"  {WARN} {name}: 0 items {note}")
            results[name] = "WARN"
    except Exception as e:
        print(f"  {FAIL} {name}: {e}")
        results[name] = "FAIL"


async def test_telegram(client):
    name = "Telegram"
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")

    if not api_id or not api_hash:
        print(f"  {SKIP} {name}: TELEGRAM_API_ID / TELEGRAM_API_HASH not set in .env")
        print(f"       → Get credentials at https://my.telegram.org/apps")
        results[name] = "SKIP"
        return

    cfg = TelegramConfig(
        enabled=True,
        channels=[TelegramChannelConfig(channel="edtechreview", enabled=True, fetch_limit=5)],
    )
    try:
        scraper = TelegramScraper(cfg, client)
        items = await scraper.fetch(SINCE)
        if items:
            print(f"  {PASS} {name}: fetched {len(items)} message(s)")
            print(f"       Sample: \"{items[0].title[:70]}\"")
            results[name] = "PASS"
        else:
            print(f"  {WARN} {name}: 0 items from @edtechreview")
            results[name] = "WARN"
    except Exception as e:
        print(f"  {FAIL} {name}: {type(e).__name__}: {e}")
        results[name] = "FAIL"


async def main():
    print("=" * 60)
    print("  Morning Pulse — Scraper Verification")
    print(f"  Window: last 7 days from {SINCE.strftime('%Y-%m-%d %H:%M')} UTC")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=20.0) as client:
        print("\n[1/5] Hacker News")
        await test_hackernews(client)

        print("\n[2/5] RSS Feeds")
        await test_rss(client)

        print("\n[3/5] Reddit (public JSON API)")
        await test_reddit(client)

        print("\n[4/5] GitHub (public releases)")
        await test_github(client)

        print("\n[5/5] Telegram")
        await test_telegram(client)

    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    for scraper, status in results.items():
        print(f"  [{status:<4}]  {scraper}")

    failed = [k for k, v in results.items() if v == "FAIL"]
    if failed:
        print(f"\n  [FAIL] {len(failed)} scraper(s) failed: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("\n  All scrapers operational. WARN = connected but no recent data in window.")


if __name__ == "__main__":
    asyncio.run(main())

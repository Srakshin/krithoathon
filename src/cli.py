"""Command-line entry point for Horizon."""

from __future__ import annotations

import argparse
import asyncio
import sys

from dotenv import load_dotenv
from rich.console import Console

from .pipeline import HorizonOrchestrator
from .storage.file_store import FileStore


console = Console()

CONFIG_TEMPLATE = """
{
  "version": "1.0",
  "ai": {
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "api_key_env": "GOOGLE_API_KEY",
    "temperature": 0.3,
    "max_tokens": 8192
  },
  "sources": {
    "github": [
      {
        "type": "user_events",
        "username": "torvalds",
        "enabled": true
      }
    ],
    "hackernews": {
      "enabled": true,
      "fetch_top_stories": 30,
      "min_score": 100
    },
    "rss": [
      {
        "name": "Example Blog",
        "url": "https://example.com/feed.xml",
        "enabled": true,
        "category": "software-engineering",
        "strategy": "auto"
      }
    ],
    "web": [
      {
        "name": "EdTech Competitor Search",
        "url": "https://example.com/edtech/search",
        "enabled": true,
        "category": "competitors",
        "strategy": "auto",
        "page_kind": "listing",
        "max_items": 10,
        "allowed_domains": ["example.com"],
        "browser": {
          "wait_until": "networkidle",
          "item_selector": "article",
          "title_selector": "h2, h3",
          "link_selector": "a[href]",
          "summary_selector": "p"
        }
      }
    ]
  },
  "filtering": {
    "ai_score_threshold": 7.0,
    "time_window_hours": 24,
    "keywords": ["teacher tools"],
    "minimum_topic_score": 2.0
  }
}

The root .env file should include:
GOOGLE_API_KEY=your_gemini_api_key_here
GROK_API_KEY=your_grok_api_key_here
GROK_MODEL=grok-4.20
GROK_BASE_URL=https://api.x.ai/v1
GITHUB_TOKEN=your_github_token_here
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
# Optional browser auth/session vars referenced from config:
# COMPETITOR_SEARCH_BROWSER_HEADERS_JSON={"Authorization":"Bearer ..."}
# COMPETITOR_SEARCH_BROWSER_COOKIES_JSON=[{"name":"session","value":"...","domain":"example.com","path":"/"}]
# COMPETITOR_SEARCH_BROWSER_STORAGE_STATE_PATH=C:\\path\\to\\storage-state.json
# COMPETITOR_SEARCH_BROWSER_SESSION_STORAGE_JSON={"token":"..."}
# COMPETITOR_SEARCH_BROWSER_PROXY_URL=http://user:pass@host:port
"""


def print_banner() -> None:
    banner = r"""
[bold blue]
  _    _            _
 | |  | |          (_)
 | |__| | ___  _ __ _ ___  ___  _ __
 |  __  |/ _ \| '__| |_  / / _ \| '_ \
 | |  | | (_) | |  | |/ / | (_) | | | |
 |_|  |_|\___/|_|  |_/___| \___/|_| |_|
[/bold blue]
[cyan]  AI-Driven Information Aggregation System[/cyan]
    """
    console.print(banner)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Horizon - AI-Driven Information Aggregation System")
    parser.add_argument("--hours", type=int, help="Force fetch from last N hours")
    return parser


def print_config_template() -> None:
    console.print(CONFIG_TEMPLATE)


def main() -> None:
    print_banner()
    args = build_parser().parse_args()
    load_dotenv()

    storage = FileStore(data_dir="data")

    try:
        config = storage.load_config()
    except FileNotFoundError:
        console.print("[bold red]Configuration file not found.[/bold red]\n")
        console.print(
            "Run [bold cyan]python -m src.configuration.setup_wizard[/bold cyan] or create "
            "[cyan]data/config.json[/cyan] from this template:\n"
        )
        print_config_template()
        raise SystemExit(1)
    except Exception as exc:
        console.print(f"[bold red]Error loading configuration: {exc}[/bold red]")
        raise SystemExit(1)

    try:
        asyncio.run(HorizonOrchestrator(config, storage).run(force_hours=args.hours))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        raise SystemExit(0)
    except Exception as exc:
        console.print(f"\n[bold red]Fatal error: {exc}[/bold red]")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

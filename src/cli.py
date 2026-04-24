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
    "provider": "anthropic",
    "model": "claude-sonnet-4.5-20250929",
    "api_key_env": "ANTHROPIC_API_KEY",
    "temperature": 0.3,
    "max_tokens": 4096
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
        "category": "software-engineering"
      }
    ]
  },
  "filtering": {
    "ai_score_threshold": 7.0,
    "time_window_hours": 24
  }
}

Also create a .env file with:
ANTHROPIC_API_KEY=your_api_key_here
GITHUB_TOKEN=your_github_token_here
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
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
            "Run [bold cyan]uv run horizon-wizard[/bold cyan] or create "
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

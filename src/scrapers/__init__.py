"""Source scrapers for Horizon."""

from .base_scraper import BaseScraper
from .github import GitHubScraper
from .hackernews import HackerNewsScraper
from .reddit import RedditScraper
from .rss import RSSScraper
from .telegram import TelegramScraper
from .web import WebScraper

__all__ = [
    "BaseScraper",
    "GitHubScraper",
    "HackerNewsScraper",
    "RedditScraper",
    "RSSScraper",
    "TelegramScraper",
    "WebScraper",
]

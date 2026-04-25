"""RSS feed scraper implementation."""

import asyncio
import calendar
import logging
import os
import re
from datetime import datetime, timezone
from typing import List
from email.utils import parsedate_to_datetime
import httpx
import feedparser

from .base_scraper import BaseScraper
from .web import WebScraper
from ..domain.models import ContentItem, FetchStrategy, RSSSourceConfig, SourceType, WebSourceConfig

logger = logging.getLogger(__name__)


class RSSScraper(BaseScraper):
    """Scraper for RSS/Atom feeds."""

    def __init__(self, sources: List[RSSSourceConfig], http_client: httpx.AsyncClient):
        """Initialize RSS scraper.

        Args:
            sources: List of RSS feed configurations
            http_client: Shared async HTTP client
        """
        super().__init__({"sources": sources}, http_client)
        self.browser_fallback = WebScraper([], http_client)

    async def fetch(self, since: datetime) -> List[ContentItem]:
        """Fetch RSS feed items.

        Args:
            since: Only fetch items published after this time

        Returns:
            List[ContentItem]: Fetched content items
        """
        items = []
        sources = self.config["sources"]

        for source in sources:
            if not source.enabled:
                continue

            if source.strategy == FetchStrategy.BROWSER:
                feed_items = await self._fetch_feed_via_browser(source, since)
            else:
                feed_items = await self._fetch_feed(source, since)
            items.extend(feed_items)

        return items

    async def _fetch_feed(
        self,
        source: RSSSourceConfig,
        since: datetime
    ) -> List[ContentItem]:
        """Fetch items from a single RSS feed.

        Args:
            source: RSS feed configuration
            since: Only fetch items after this time

        Returns:
            List[ContentItem]: Feed content items
        """
        items = []

        try:
            feed_url = re.sub(
                r'\$\{(\w+)\}',
                lambda m: os.environ.get(m.group(1), m.group(0)).strip(),
                str(source.url),
            )

            response = await self._get_with_retry(source, feed_url)

            feed = feedparser.parse(response.text)

            for entry in feed.entries:
                published_at = self._parse_date(entry)
                if not published_at or published_at < since:
                    continue

                feed_id = str(source.url).split("//")[1].replace("/", "_")
                entry_id = entry.get("id", entry.get("link", ""))

                content = self._extract_content(entry)

                item = ContentItem(
                    id=self._generate_id("rss", feed_id, str(hash(entry_id))),
                    source_type=SourceType.RSS,
                    title=entry.get("title", "Untitled"),
                    url=entry.get("link", str(source.url)),
                    content=content,
                    author=entry.get("author", source.name),
                    published_at=published_at,
                    metadata={
                        "feed_name": source.name,
                        "category": source.category,
                        "tags": [tag.term for tag in entry.get("tags", [])],
                    }
                )
                items.append(item)

            if not items and source.strategy == FetchStrategy.AUTO:
                browser_items = await self._fetch_feed_via_browser(source, since)
                if browser_items:
                    logger.info("Used browser fallback for RSS source %s", source.name)
                    return browser_items

        except httpx.HTTPError as e:
            logger.warning("Error fetching RSS feed %s: %s", source.name, e)
            if source.strategy == FetchStrategy.AUTO:
                return await self._fetch_feed_via_browser(source, since)
        except Exception as e:
            logger.warning("Error parsing RSS feed %s: %s", source.name, e)
            if source.strategy == FetchStrategy.AUTO:
                return await self._fetch_feed_via_browser(source, since)

        return items

    async def _fetch_feed_via_browser(
        self,
        source: RSSSourceConfig,
        since: datetime,
    ) -> List[ContentItem]:
        web_source = WebSourceConfig(
            name=source.name,
            url=source.url,
            enabled=source.enabled,
            category=source.category,
            strategy=FetchStrategy.BROWSER,
            timeout_seconds=source.timeout_seconds,
            retry_attempts=source.retry_attempts,
        )

        browser_items = await self.browser_fallback._try_browser(web_source, since)
        if not browser_items:
            return []

        feed_id = str(source.url).split("//")[1].replace("/", "_")
        converted: List[ContentItem] = []
        for item in browser_items:
            native_id = item.id.split(":")[-1]
            converted.append(
                item.model_copy(
                    update={
                        "id": self._generate_id("rss", feed_id, native_id),
                        "source_type": SourceType.RSS,
                    }
                )
            )
        return converted

    async def _get_with_retry(self, source: RSSSourceConfig, url: str) -> httpx.Response:
        attempts = max(1, int(source.retry_attempts))
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = await self.client.get(
                    url,
                    follow_redirects=True,
                    timeout=source.timeout_seconds,
                )
                response.raise_for_status()
                return response
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    "Error fetching RSS feed %s (attempt %s/%s): %s",
                    source.name,
                    attempt,
                    attempts,
                    exc,
                )
                if attempt == attempts:
                    break
                await asyncio.sleep(min(1.5 * attempt, 5.0))

        if last_error is None:  # pragma: no cover - defensive
            raise httpx.HTTPError(f"Unknown RSS fetch failure for {source.name}")
        raise last_error

    def _parse_date(self, entry: dict) -> datetime:
        """Parse publication date from feed entry.

        Args:
            entry: Feed entry data

        Returns:
            datetime: Parsed publication date or None
        """
        for field in ["published", "updated", "created"]:
            if field in entry:
                try:
                    if f"{field}_parsed" in entry and entry[f"{field}_parsed"]:
                        return datetime.fromtimestamp(
                            calendar.timegm(entry[f"{field}_parsed"]),
                            tz=timezone.utc
                        )
                    date_str = entry[field]
                    return parsedate_to_datetime(date_str)
                except Exception:
                    continue

        return None

    def _extract_content(self, entry: dict) -> str:
        """Extract text content from feed entry.

        Args:
            entry: Feed entry data

        Returns:
            str: Extracted text content
        """
        if "summary" in entry:
            return entry.summary
        elif "description" in entry:
            return entry.description
        elif "content" in entry and entry.content:
            return entry.content[0].get("value", "")

        return ""

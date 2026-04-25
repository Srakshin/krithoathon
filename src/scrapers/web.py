"""Generic web scraper with HTTP-first and browser-fallback strategies."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlparse

import feedparser
import httpx

from .base_scraper import BaseScraper
from ..domain.models import ContentItem, FetchStrategy, SourceType, WebPageKind, WebSourceConfig
from ..filtering import TopicalContentFilter
from ..services import BrowserService, RenderedPage

logger = logging.getLogger(__name__)
WHITESPACE_RE = re.compile(r"\s+")
JS_SHELL_MARKERS = ("__next", "__nuxt", "id=\"root\"", "app-root", "enable javascript")


@dataclass
class ExtractionAttempt:
    items: list[ContentItem]
    should_try_browser: bool = False


class WebScraper(BaseScraper):
    """Scrape public web pages, result pages, and feed-like sources."""

    def __init__(
        self,
        sources: list[WebSourceConfig],
        http_client: httpx.AsyncClient,
        content_filter: TopicalContentFilter | None = None,
        browser_service: BrowserService | None = None,
    ):
        super().__init__({"sources": sources}, http_client)
        self.content_filter = content_filter
        self.browser_service = browser_service or BrowserService()

    async def fetch(self, since: datetime) -> list[ContentItem]:
        items: list[ContentItem] = []
        for source in self.config["sources"]:
            if not source.enabled:
                continue
            source_items = await self._fetch_source(source, since)
            items.extend(source_items)
        return items

    async def _fetch_source(self, source: WebSourceConfig, since: datetime) -> list[ContentItem]:
        strategy = source.strategy
        if strategy == FetchStrategy.API:
            logger.warning(
                "Web source %s requested API mode but no API endpoint is configured. Using HTTP instead.",
                source.name,
            )
            strategy = FetchStrategy.HTTP

        if strategy == FetchStrategy.HTTP:
            attempt = await self._fetch_via_http(source, since)
            return attempt.items

        if strategy == FetchStrategy.BROWSER:
            browser_items = await self._try_browser(source, since)
            if browser_items:
                return browser_items
            logger.warning("Browser strategy returned no items for %s; falling back to HTTP.", source.name)
            attempt = await self._fetch_via_http(source, since)
            return attempt.items

        attempt = await self._fetch_via_http(source, since)
        if attempt.items and not attempt.should_try_browser:
            return attempt.items

        browser_items = await self._try_browser(source, since)
        return browser_items or attempt.items

    async def _fetch_via_http(self, source: WebSourceConfig, since: datetime) -> ExtractionAttempt:
        attempts = max(1, int(source.retry_attempts))
        last_error: Exception | None = None

        for attempt_num in range(1, attempts + 1):
            try:
                response = await self.client.get(
                    str(source.url),
                    follow_redirects=True,
                    timeout=source.timeout_seconds,
                )
                response.raise_for_status()
                return self._extract_from_document(
                    source,
                    html=response.text,
                    final_url=str(response.url),
                    since=since,
                    title_hint="",
                    body_text="",
                    browser_rendered=False,
                )
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    "HTTP fetch failed for %s (attempt %s/%s): %s",
                    source.name,
                    attempt_num,
                    attempts,
                    exc,
                )
                if attempt_num == attempts:
                    break
                await asyncio.sleep(min(1.5 * attempt_num, 5.0))

        if last_error is not None:
            logger.warning("Falling back from HTTP to browser for %s after error: %s", source.name, last_error)
        return ExtractionAttempt(items=[], should_try_browser=True)

    async def _try_browser(self, source: WebSourceConfig, since: datetime) -> list[ContentItem]:
        try:
            rendered = await self.browser_service.fetch(source)
        except Exception as exc:  # pragma: no cover - browser/runtime-dependent
            logger.warning("Browser fetch failed for %s: %s", source.name, exc)
            return []

        attempt = self._extract_from_rendered_page(source, rendered, since)
        return attempt.items

    def _extract_from_rendered_page(
        self,
        source: WebSourceConfig,
        rendered: RenderedPage,
        since: datetime,
    ) -> ExtractionAttempt:
        return self._extract_from_document(
            source,
            html=rendered.html,
            final_url=rendered.final_url,
            since=since,
            title_hint=rendered.title,
            body_text=rendered.text,
            browser_rendered=True,
        )

    def _extract_from_document(
        self,
        source: WebSourceConfig,
        *,
        html: str,
        final_url: str,
        since: datetime,
        title_hint: str,
        body_text: str,
        browser_rendered: bool,
    ) -> ExtractionAttempt:
        feed_items = self._extract_feed_items(source, html, final_url, since)
        if feed_items:
            return ExtractionAttempt(items=feed_items)

        soup = self._make_soup(html)
        if soup is None:
            return ExtractionAttempt(items=[], should_try_browser=not browser_rendered)

        if self._is_listing_page(source, soup):
            items = self._extract_listing_items(source, soup, final_url, since)
        else:
            item = self._extract_page_item(source, soup, final_url, since, title_hint, body_text)
            items = [item] if item else []

        should_try_browser = False
        if not browser_rendered and not items:
            combined_text = self._clean_text(f"{title_hint} {body_text} {html[:3000]}")
            should_try_browser = self._looks_like_js_shell(combined_text)

        return ExtractionAttempt(items=items, should_try_browser=should_try_browser)

    def _extract_feed_items(
        self,
        source: WebSourceConfig,
        document: str,
        final_url: str,
        since: datetime,
    ) -> list[ContentItem]:
        parsed = feedparser.parse(document)
        if not parsed.entries:
            return []

        if source.page_kind not in {WebPageKind.AUTO, WebPageKind.FEED}:
            return []

        items: list[ContentItem] = []
        feed_id = self._feed_id(source)
        for entry in parsed.entries:
            published_at = self._parse_entry_date(entry) or datetime.now(timezone.utc)
            if published_at < since:
                continue

            entry_url = entry.get("link") or final_url
            title = self._clean_text(entry.get("title", "")) or source.name
            content = self._clean_text(self._entry_content(entry))

            if not self._is_relevant_candidate(
                title=title,
                summary="",
                content=content,
                url=entry_url,
                metadata={"feed_name": source.name, "category": source.category},
            ):
                continue

            entry_id = entry.get("id", entry_url)
            items.append(
                ContentItem(
                    id=self._generate_id("web", feed_id, str(hash(entry_id))),
                    source_type=SourceType.WEB,
                    title=title,
                    url=entry_url,
                    content=content,
                    author=self._clean_text(entry.get("author", "")) or None,
                    published_at=published_at,
                    metadata={
                        "feed_name": source.name,
                        "category": source.category,
                        "page_kind": source.page_kind.value,
                        "fetch_strategy": source.strategy.value,
                        "tags": [tag.term for tag in entry.get("tags", [])],
                    },
                )
            )

        return items

    def _extract_listing_items(
        self,
        source: WebSourceConfig,
        soup: Any,
        final_url: str,
        since: datetime,
    ) -> list[ContentItem]:
        nodes = self._listing_nodes(source, soup)
        items: list[ContentItem] = []
        seen_urls: set[str] = set()

        for index, node in enumerate(nodes[: max(1, int(source.max_items))]):
            link_node = self._select_one(node, source.browser.link_selector)
            title_node = self._select_one(node, source.browser.title_selector)
            summary_node = self._select_one(node, source.browser.summary_selector)
            date_node = self._select_one(node, source.browser.date_selector)

            if getattr(node, "name", "") == "a" and link_node is None:
                link_node = node

            if title_node is None and getattr(node, "name", "") in {"h1", "h2", "h3", "a"}:
                title_node = node

            if link_node is None:
                link_node = getattr(node, "find", lambda *args, **kwargs: None)("a", href=True)

            title = self._clean_text(
                self._node_text(title_node) or self._node_text(link_node) or self._node_text(node)
            )
            if not title:
                continue

            href = link_node.get("href") if link_node else final_url
            item_url = urljoin(final_url, href or final_url)
            if not self._is_allowed_url(source, item_url) or item_url in seen_urls:
                continue
            seen_urls.add(item_url)

            summary = self._clean_text(self._node_text(summary_node))
            content = summary or self._clean_text(self._node_text(node))
            if len(content) > 6000:
                content = content[:6000].rstrip() + "..."

            published_at = self._parse_node_date(date_node) or datetime.now(timezone.utc)
            if published_at < since:
                continue

            metadata = {
                "feed_name": source.name,
                "category": source.category,
                "page_kind": source.page_kind.value,
                "fetch_strategy": source.strategy.value,
                "source_url": str(source.url),
            }
            if not self._is_relevant_candidate(
                title=title,
                summary=summary,
                content=content,
                url=item_url,
                metadata=metadata,
            ):
                continue

            items.append(
                ContentItem(
                    id=self._generate_id("web", self._feed_id(source), f"{index}:{hash(item_url)}"),
                    source_type=SourceType.WEB,
                    title=title,
                    url=item_url,
                    content=content,
                    author=None,
                    published_at=published_at,
                    metadata=metadata,
                )
            )

        return items

    def _extract_page_item(
        self,
        source: WebSourceConfig,
        soup: Any,
        final_url: str,
        since: datetime,
        title_hint: str,
        body_text: str,
    ) -> ContentItem | None:
        title = self._clean_text(
            title_hint
            or self._meta_content(soup, "property", "og:title")
            or self._meta_content(soup, "name", "twitter:title")
            or self._node_text(soup.find("h1"))
            or self._node_text(getattr(soup, "title", None))
            or source.name
        )

        content_root = soup.select_one("main") or soup.select_one("article") or getattr(soup, "body", None) or soup
        content = self._clean_text(body_text or self._node_text(content_root))
        if len(content) > 8000:
            content = content[:8000].rstrip() + "..."

        published_at = self._page_published_at(soup) or datetime.now(timezone.utc)
        if published_at < since:
            return None

        metadata = {
            "feed_name": source.name,
            "category": source.category,
            "page_kind": source.page_kind.value,
            "fetch_strategy": source.strategy.value,
            "source_url": str(source.url),
        }
        if not self._is_relevant_candidate(
            title=title,
            summary="",
            content=content,
            url=final_url,
            metadata=metadata,
        ):
            return None

        return ContentItem(
            id=self._generate_id("web", self._feed_id(source), str(hash(final_url))),
            source_type=SourceType.WEB,
            title=title,
            url=final_url,
            content=content,
            author=None,
            published_at=published_at,
            metadata=metadata,
        )

    def _listing_nodes(self, source: WebSourceConfig, soup: Any) -> list[Any]:
        selector = source.browser.item_selector
        if selector:
            nodes = soup.select(selector)
            if nodes:
                return nodes

        article_nodes = soup.select("article")
        if article_nodes:
            return article_nodes

        link_nodes = []
        for candidate in soup.select("main a[href], h1 a[href], h2 a[href], h3 a[href], a[href]"):
            if self._clean_text(self._node_text(candidate)):
                link_nodes.append(candidate)
            if len(link_nodes) >= max(1, int(source.max_items)):
                break
        return link_nodes

    def _is_listing_page(self, source: WebSourceConfig, soup: Any) -> bool:
        if source.page_kind == WebPageKind.PAGE:
            return False
        if source.page_kind == WebPageKind.LISTING:
            return True
        if source.browser.item_selector:
            return True
        return len(soup.select("article")) > 1

    def _page_published_at(self, soup: Any) -> datetime | None:
        candidates = [
            self._meta_content(soup, "property", "article:published_time"),
            self._meta_content(soup, "name", "pubdate"),
            self._meta_content(soup, "name", "timestamp"),
        ]
        for value in candidates:
            parsed = self._parse_date_value(value)
            if parsed:
                return parsed

        time_node = soup.find("time")
        return self._parse_node_date(time_node)

    def _is_allowed_url(self, source: WebSourceConfig, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False

        if source.allowed_domains:
            hostname = parsed.hostname or ""
            if not any(hostname == domain or hostname.endswith(f".{domain}") for domain in source.allowed_domains):
                return False

        lower_url = url.lower()
        if source.include_url_patterns and not any(pattern.lower() in lower_url for pattern in source.include_url_patterns):
            return False
        if any(pattern.lower() in lower_url for pattern in source.exclude_url_patterns):
            return False
        return True

    def _is_relevant_candidate(
        self,
        *,
        title: str,
        summary: str,
        content: str,
        url: str,
        metadata: dict[str, Any],
    ) -> bool:
        if self.content_filter is None:
            return True
        return self.content_filter.is_relevant_payload(
            title=title,
            summary=summary,
            content=content,
            url=url,
            metadata=metadata,
        )

    @staticmethod
    def _feed_id(source: WebSourceConfig) -> str:
        return str(source.url).split("//", 1)[-1].replace("/", "_")

    @staticmethod
    def _entry_content(entry: Any) -> str:
        if entry.get("summary"):
            return entry.get("summary", "")
        if entry.get("description"):
            return entry.get("description", "")
        if entry.get("content"):
            return entry["content"][0].get("value", "")
        return ""

    def _make_soup(self, html: str) -> Any:
        try:
            from bs4 import BeautifulSoup
        except ImportError as exc:  # pragma: no cover - depends on local install
            raise RuntimeError("beautifulsoup4 is required for generic web scraping.") from exc

        return BeautifulSoup(html, "html.parser")

    @staticmethod
    def _clean_text(value: str | None) -> str:
        text = unescape(value or "")
        return WHITESPACE_RE.sub(" ", text).strip()

    @staticmethod
    def _node_text(node: Any) -> str:
        if node is None:
            return ""
        if getattr(node, "name", None) == "title":
            return getattr(node, "string", "") or ""
        if hasattr(node, "get_text"):
            return node.get_text(" ", strip=True)
        return str(node)

    @staticmethod
    def _select_one(node: Any, selector: str | None) -> Any:
        if node is None or not selector or not hasattr(node, "select_one"):
            return None
        return node.select_one(selector)

    def _meta_content(self, soup: Any, attr_name: str, attr_value: str) -> str:
        tag = soup.find("meta", attrs={attr_name: attr_value})
        if not tag:
            return ""
        return self._clean_text(tag.get("content", ""))

    def _parse_node_date(self, node: Any) -> datetime | None:
        if node is None:
            return None
        datetime_value = getattr(node, "get", lambda *args, **kwargs: None)("datetime")
        parsed = self._parse_date_value(datetime_value or self._node_text(node))
        return parsed

    def _parse_entry_date(self, entry: Any) -> datetime | None:
        for field in ("published", "updated", "created"):
            candidate = entry.get(field)
            parsed = self._parse_date_value(candidate)
            if parsed:
                return parsed
        return None

    def _parse_date_value(self, value: Any) -> datetime | None:
        raw = self._clean_text(str(value or ""))
        if not raw:
            return None

        try:
            if raw.isdigit():
                parsed = datetime.fromtimestamp(int(raw), tz=timezone.utc)
            else:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = parsedate_to_datetime(raw)
            except (TypeError, ValueError):
                return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _looks_like_js_shell(value: str) -> bool:
        lower = value.lower()
        return any(marker in lower for marker in JS_SHELL_MARKERS)

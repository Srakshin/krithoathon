"""Telegram public channel scraper implementation."""

import logging
import os
import re
from datetime import datetime
from typing import List, Optional

import httpx
from telethon import TelegramClient
from telethon.tl.types import MessageEntityTextUrl

from .base_scraper import BaseScraper
from ..domain.models import ContentItem, TelegramConfig, TelegramChannelConfig, SourceType

logger = logging.getLogger(__name__)


class TelegramScraper(BaseScraper):
    """Scraper for Telegram public channels via Telethon."""

    def __init__(self, config: TelegramConfig, http_client: httpx.AsyncClient):
        super().__init__(config.model_dump(), http_client)
        self.telegram_config = config
        
        # Read API credentials from environment variables
        api_id_str = os.environ.get("TELEGRAM_API_ID")
        self.api_id = int(api_id_str) if api_id_str and api_id_str.isdigit() else None
        self.api_hash = os.environ.get("TELEGRAM_API_HASH")
        
        self.session_path = "data/edtech_session"
        
        if not self.api_id or not self.api_hash:
            logger.warning("TELEGRAM_API_ID or TELEGRAM_API_HASH not set in environment. Telegram scraping disabled.")

    async def fetch(self, since: datetime) -> List[ContentItem]:
        if not self.config.get("enabled", True) or not self.api_id or not self.api_hash:
            return []

        # Make sure data directory exists for the session file
        os.makedirs(os.path.dirname(self.session_path), exist_ok=True)

        items = []
        try:
            # Note: Telethon requires an active event loop to connect
            async with TelegramClient(self.session_path, self.api_id, self.api_hash) as client:
                for channel_cfg in self.telegram_config.channels:
                    if not channel_cfg.enabled:
                        continue
                        
                    channel_items = await self._fetch_channel(client, channel_cfg, since)
                    items.extend(channel_items)
        except Exception as e:
            logger.warning("Error during Telegram scraping session: %r", e)

        return items

    async def _fetch_channel(self, client: TelegramClient, cfg: TelegramChannelConfig, since: datetime) -> List[ContentItem]:
        items = []
        try:
            async for message in client.iter_messages(cfg.channel, limit=cfg.fetch_limit):
                if message.date and message.date >= since and message.text:
                    item = self._parse_message(message, cfg.channel)
                    if item:
                        items.append(item)
        except Exception as e:
            logger.warning("Error fetching Telegram channel %s: [%s] %r", cfg.channel, type(e).__name__, e)
            
        return items

    def _parse_message(
        self, message, channel: str
    ) -> Optional[ContentItem]:
        if not message.text:
            return None

        text = message.text.strip()
        if not text:
            return None

        msg_id = str(message.id)
        published_at = message.date

        title = self._make_title(text)

        msg_url = f"https://t.me/{channel}/{msg_id}"
        
        canonical_url = msg_url

        # Check message entities for text_link
        if message.entities:
            for entity in message.entities:
                if isinstance(entity, MessageEntityTextUrl):
                    href = entity.url
                    if href.startswith("http") and "t.me" not in href:
                        canonical_url = href
                        break

        return ContentItem(
            id=self._generate_id("telegram", channel, msg_id),
            source_type=SourceType.TELEGRAM,
            title=title,
            url=canonical_url,
            content=text,
            author=channel,
            published_at=published_at,
            metadata={"msg_url": msg_url, "channel": channel},
        )

    @staticmethod
    def _make_title(text: str) -> str:
        first_para = text.split("\n\n")[0].replace("\n", " ").strip()

        if len(first_para) <= 80:
            return first_para

        # Try to break at a Chinese sentence-ending punctuation within first 80 chars
        match = re.search(r"[。！？]", first_para[:80])
        if match:
            return first_para[: match.end()]

        # Fallback: hard truncate
        return first_para[:80]

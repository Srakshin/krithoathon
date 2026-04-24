import asyncio
import httpx
from datetime import datetime, timedelta, timezone
import json
import os
from dotenv import load_dotenv

from src.scrapers.telegram import TelegramScraper
from src.domain.models import TelegramConfig, TelegramChannelConfig

async def main():
    load_dotenv()
    
    # Read channels from config.json
    with open("data/config.json", "r") as f:
        config_data = json.load(f)
        telegram_channels = config_data.get("sources", {}).get("telegram", {}).get("channels", [])
        
    channels = [TelegramChannelConfig(**c) for c in telegram_channels]
    telegram_config = TelegramConfig(enabled=True, channels=channels)
    
    async with httpx.AsyncClient() as http_client:
        scraper = TelegramScraper(telegram_config, http_client)
        since = datetime.now(timezone.utc) - timedelta(days=1)
        
        print("\nFetching last 24h EdTech updates...\n")
        items = await scraper.fetch(since)
        
        print(f"\nFound {len(items)} messages.")
        for item in items:
            print("-" * 40)
            print(f"Channel: {item.author}")
            print(f"Date: {item.published_at}")
            print(f"Content: {item.content[:150]}...")

if __name__ == "__main__":
    # Force UTF-8 encoding for Windows terminals to avoid charmap errors
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    asyncio.run(main())

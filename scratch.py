import asyncio
from src.server import _load_orchestrator
from datetime import datetime, timedelta, timezone

async def main():
    orchestrator = _load_orchestrator()
    since = datetime.now(timezone.utc) - timedelta(hours=72)
    try:
        print("Fetching items...")
        fetched_items = await orchestrator.fetch_all_sources(since)
        print(f"Fetched {len(fetched_items)} items.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

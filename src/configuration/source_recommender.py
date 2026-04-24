"""AI-powered source recommendation for the setup wizard."""

import asyncio
from typing import List, Dict, Optional

from ..ai.client import create_ai_client
from ..ai.utils import parse_json_response
from ..domain.models import AIConfig
from .recommendation_prompts import RECOMMEND_SYSTEM, RECOMMEND_USER


async def get_ai_recommendations(
    ai_config: AIConfig,
    interests: str,
    existing_sources: List[Dict],
) -> List[Dict]:
    """Ask AI to recommend additional sources beyond presets.

    Args:
        ai_config: AI configuration for creating the client.
        interests: User's interest description.
        existing_sources: Already-selected sources (for dedup context).

    Returns:
        List of recommended source dicts with origin="ai".
    """
    try:
        client = create_ai_client(ai_config)
    except (ValueError, Exception):
        return []

    existing_lines = []
    for src in existing_sources:
        desc = src.get("description", src.get("type", "unknown"))
        existing_lines.append(f"  - [{src.get('type', '?')}] {desc}")
    existing_str = "\n".join(existing_lines) if existing_lines else "  (none)"

    user_prompt = RECOMMEND_USER.format(
        interests=interests,
        existing_sources=existing_str,
    )

    try:
        response = await client.complete(
            system=RECOMMEND_SYSTEM,
            user=user_prompt,
        )
    except Exception:
        return []

    result = parse_json_response(response)
    if result is None:
        return []

    sources = result.get("sources", [])
    for src in sources:
        src["origin"] = "ai"

    return sources


def get_ai_recommendations_sync(
    ai_config: AIConfig,
    interests: str,
    existing_sources: List[Dict],
) -> List[Dict]:
    """Synchronous wrapper for get_ai_recommendations."""
    return asyncio.run(get_ai_recommendations(ai_config, interests, existing_sources))

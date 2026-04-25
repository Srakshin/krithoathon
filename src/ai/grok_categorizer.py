"""Grok API categorization for stored market-intelligence records."""

from __future__ import annotations

import json
import os
from typing import Any

from ..domain.models import AIConfig, AIProvider
from .client import create_ai_client
from .utils import parse_json_response

TARGET_CATEGORIES = (
    "Competitor Updates",
    "User Pain Points",
    "Emerging Tech Trends",
    "Market Opportunities",
    "Customer Feedback Signals",
)

GROK_CATEGORY_SYSTEM = """
You categorize stored EdTech market-intelligence records.

Choose exactly one category for every record:
- Competitor Updates: launches, releases, pricing changes, partnerships, acquisitions, hiring, roadmap moves, or product updates from vendors and competitors.
- User Pain Points: explicit frustrations, delays, complaints, repetitive manual work, workflow bottlenecks, or unmet needs from teachers, admins, parents, or students. Example: "Grading takes too long."
- Emerging Tech Trends: new AI capabilities, infrastructure shifts, research breakthroughs, adoption patterns, or new technology directions that matter to the education market.
- Market Opportunities: unserved niches, funding trends, changing regulations, budget allocations, or broader economic shifts that present a chance for growth or entry.
- Customer Feedback Signals: user reviews, product testimonials, community sentiment, bug reports, feature requests, or direct feedback on specific existing tools.

Return valid JSON only in this shape:
{
  "items": [
    {
      "id": 123,
      "category": "Competitor Updates",
      "summary": "One concise sentence explaining the most useful business insight."
    }
  ]
}

Rules:
- Every input record must appear exactly once in the output.
- Use only the provided record data.
- Keep summaries short, specific, and plain text.
- Never invent missing facts.
""".strip()

GROK_CATEGORY_USER = """
Categorize the following records that have already been stored in the database.

Records:
{records}
""".strip()


def _chunked(records: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [records[index : index + size] for index in range(0, len(records), size)]


def _normalize_category(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    if "competitor" in text:
        return "Competitor Updates"
    if "pain" in text or "frustr" in text or "complaint" in text:
        return "User Pain Points"
    if "trend" in text or "tech" in text or "emerging" in text:
        return "Emerging Tech Trends"
    if "market" in text or "opportunit" in text:
        return "Market Opportunities"
    if "feedback" in text or "signal" in text or "review" in text:
        return "Customer Feedback Signals"
    return None


KEYWORD_CATEGORY_MAP = [
    ("Competitor Updates",        ["launch", "release", "acquired", "acquisition", "partnership", "funding", "product update", "competitor", "rival", "pricing", "new feature"]),
    ("User Pain Points",          ["problem", "issue", "struggle", "difficult", "frustrated", "complaint", "pain", "challenge", "fail", "broken", "hard to"]),
    ("Emerging Tech Trends",      ["ai", "artificial intelligence", "machine learning", "automation", "trend", "research", "innovation", "emerging", "technology", "digital transformation"]),
    ("Market Opportunities",      ["opportunity", "market", "growth", "invest", "demand", "gap", "unserved", "potential", "expand", "scale"]),
    ("Customer Feedback Signals", ["review", "feedback", "testimonial", "rating", "recommend", "feature request", "survey", "community"]),
]


def _keyword_categorize(title: str, summary: str) -> str:
    text = (title + " " + summary).lower()
    for category, keywords in KEYWORD_CATEGORY_MAP:
        if any(kw in text for kw in keywords):
            return category
    return "Emerging Tech Trends"  # default fallback


class GrokCategorizer:
    """Categorize stored scraper records with Gemini."""

    def __init__(self) -> None:
        self.model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash-latest")
        self.api_key_env = "GOOGLE_API_KEY"
        self.client = create_ai_client(
            AIConfig(
                provider=AIProvider.GEMINI,
                model=self.model,
                api_key_env=self.api_key_env,
                temperature=0.1,
                max_tokens=4096,
            )
        )

    async def categorize_records(
        self,
        records: list[dict[str, Any]],
        *,
        batch_size: int = 15,
    ) -> dict[int, dict[str, str]]:
        """Return category/summary updates keyed by database record id.
        
        Falls back to keyword-based categorization if Gemini quota is exceeded.
        """

        categorized: dict[int, dict[str, str]] = {}

        try:
            for batch in _chunked(records, batch_size):
                categorized.update(await self._categorize_batch(batch))
        except Exception as exc:
            print(f"Gemini categorization failed ({exc}), falling back to keyword-based categorization.")
            # Keyword-based fallback so data always displays on dashboard
            for record in records:
                rec_id = int(record["id"])
                if rec_id not in categorized:
                    categorized[rec_id] = {
                        "category": _keyword_categorize(record.get("title", ""), record.get("summary", "")),
                        "summary": record.get("summary") or record.get("title", ""),
                    }
            return categorized

        # Fill any remaining gaps with keyword fallback (partial success)
        for record in records:
            rec_id = int(record["id"])
            if rec_id not in categorized:
                categorized[rec_id] = {
                    "category": _keyword_categorize(record.get("title", ""), record.get("summary", "")),
                    "summary": record.get("summary") or record.get("title", ""),
                }

        return categorized

    async def _categorize_batch(
        self,
        records: list[dict[str, Any]],
    ) -> dict[int, dict[str, str]]:
        prompt_records = [
            {
                "id": int(record["id"]),
                "title": record.get("title") or "",
                "source": record.get("source") or "",
                "url": record.get("url") or "",
                "stored_summary": record.get("summary") or "",
            }
            for record in records
        ]

        response = await self.client.complete(
            system=GROK_CATEGORY_SYSTEM,
            user=GROK_CATEGORY_USER.format(
                records=json.dumps(prompt_records, ensure_ascii=False, indent=2)
            ),
        )

        payload = parse_json_response(response)
        if not isinstance(payload, dict):
            raise ValueError("Grok response was not valid JSON.")

        items = payload.get("items")
        if not isinstance(items, list):
            raise ValueError("Grok response did not include an 'items' array.")

        record_lookup = {int(record["id"]): record for record in records}
        categorized: dict[int, dict[str, str]] = {}

        for item in items:
            if not isinstance(item, dict):
                continue

            try:
                record_id = int(item.get("id"))
            except (TypeError, ValueError):
                continue

            if record_id not in record_lookup:
                continue

            category = _normalize_category(item.get("category"))
            if not category:
                raise ValueError(
                    f"Grok returned an unsupported category for record id {record_id}: "
                    f"{item.get('category')!r}"
                )

            summary = " ".join(str(item.get("summary") or "").split()).strip()
            if not summary:
                summary = (
                    str(record_lookup[record_id].get("summary") or "").strip()
                    or str(record_lookup[record_id].get("title") or "").strip()
                )

            categorized[record_id] = {
                "category": category,
                "summary": summary,
            }

        return categorized

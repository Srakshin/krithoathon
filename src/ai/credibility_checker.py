"""Credibility / fake-news scoring for scraped EdTech items."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from ..domain.models import AIConfig, AIProvider
from .client import create_ai_client
from .utils import parse_json_response

# ---------------------------------------------------------------------------
# Domain reputation table (fallback when Gemini quota is exhausted)
# ---------------------------------------------------------------------------
DOMAIN_SCORES: dict[str, int] = {
    # Highly credible education publishers
    "nytimes.com": 90,
    "edutopia.org": 85,
    "edsurge.com": 82,
    "techcrunch.com": 78,
    "chronicle.com": 88,
    "insidehighered.com": 85,
    "hechingerreport.org": 83,
    "educationweek.org": 87,
    "kqed.org": 80,
    "theatlantic.com": 82,
    "wired.com": 75,
    "venturebeat.com": 70,
    # Community / social – lower baseline
    "reddit.com": 45,
    "news.ycombinator.com": 60,
    "t.me": 40,
    "twitter.com": 38,
    "x.com": 38,
    "facebook.com": 35,
    "medium.com": 55,
    "substack.com": 52,
    "quora.com": 42,
}

CREDIBILITY_LABELS = [
    (80, "High Credibility"),
    (55, "Moderate Credibility"),
    (30, "Low Credibility"),
    (0, "Unverified"),
]

CREDIBILITY_PROMPT_SYSTEM = """
You are a credibility analyst specializing in EdTech and education journalism.

For each item, output a score from 0 to 100 assessing how factually reliable the article/post is.

Scoring criteria:
- **Source reputation** (30 pts): Is it from a known, established outlet vs anonymous post?
- **Factual specificity** (25 pts): Does it cite specific dates, studies, numbers, or named parties?
- **Tone** (20 pts): Is it objective/neutral or uses clickbait/sensationalist language?
- **Verifiability** (15 pts): Can the core claim be independently verified?
- **Corroboration** (10 pts): Is the event reported by multiple credible sources?

Return ONLY valid JSON in this exact shape:
{
  "items": [
    {
      "id": 0,
      "confidence_score": 72,
      "credibility_label": "Moderate Credibility",
      "credibility_reason": "One concise sentence explaining the score."
    }
  ]
}

Labels must be one of: "High Credibility", "Moderate Credibility", "Low Credibility", "Unverified"
""".strip()

CREDIBILITY_PROMPT_USER = """
Score the credibility of these news items:

{records}
""".strip()


def _score_to_label(score: int) -> str:
    for threshold, label in CREDIBILITY_LABELS:
        if score >= threshold:
            return label
    return "Unverified"


def _domain_from_url(url: str) -> str:
    match = re.search(r"https?://(?:www\.)?([^/]+)", str(url))
    return match.group(1).lower() if match else ""


def _fallback_score(item: dict[str, Any]) -> dict[str, Any]:
    """Score based on source domain reputation when Gemini is unavailable."""
    domain = _domain_from_url(item.get("url", ""))
    score = 50  # neutral default

    for known_domain, domain_score in DOMAIN_SCORES.items():
        if known_domain in domain:
            score = domain_score
            break

    # Bonus for items that have a proper summary (more detail = more credible)
    summary = item.get("summary", "") or ""
    if len(summary) > 100:
        score = min(score + 5, 100)

    # Penalty for very short or missing titles
    title = item.get("title", "") or ""
    if len(title) < 15:
        score = max(score - 10, 0)

    label = _score_to_label(score)
    return {
        "confidence_score": score,
        "credibility_label": label,
        "credibility_reason": f"Score based on source domain reputation ({domain or 'unknown'}).",
    }


def _chunked(records: list, size: int) -> list[list]:
    return [records[i : i + size] for i in range(0, len(records), size)]


class CredibilityChecker:
    """Score scraped items for credibility using Gemini with a domain fallback."""

    def __init__(self) -> None:
        self.model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash-latest")
        self.client = create_ai_client(
            AIConfig(
                provider=AIProvider.GEMINI,
                model=self.model,
                api_key_env="GOOGLE_API_KEY",
                temperature=0.1,
                max_tokens=4096,
            )
        )

    async def score_items(
        self,
        items: list[dict[str, Any]],
        *,
        batch_size: int = 15,
    ) -> dict[int, dict[str, Any]]:
        """Return credibility scores keyed by temporary item id.

        Falls back to domain-reputation scoring if Gemini quota is exceeded.
        """
        scored: dict[int, dict[str, Any]] = {}

        try:
            for batch in _chunked(items, batch_size):
                scored.update(await self._score_batch(batch))
        except Exception as exc:
            print(f"Gemini credibility scoring failed ({exc}), using domain fallback.")
            for item in items:
                rec_id = int(item["id"])
                if rec_id not in scored:
                    scored[rec_id] = _fallback_score(item)
            return scored

        # Fill gaps with fallback
        for item in items:
            rec_id = int(item["id"])
            if rec_id not in scored:
                scored[rec_id] = _fallback_score(item)

        return scored

    async def _score_batch(
        self, records: list[dict[str, Any]]
    ) -> dict[int, dict[str, Any]]:
        prompt_records = [
            {
                "id": int(r["id"]),
                "title": r.get("title", ""),
                "source": r.get("source", ""),
                "url": r.get("url", ""),
                "summary": (r.get("summary", "") or "")[:300],
            }
            for r in records
        ]

        response = await self.client.complete(
            system=CREDIBILITY_PROMPT_SYSTEM,
            user=CREDIBILITY_PROMPT_USER.format(
                records=json.dumps(prompt_records, ensure_ascii=False, indent=2)
            ),
        )

        payload = parse_json_response(response)
        if not isinstance(payload, dict):
            raise ValueError("Credibility response was not valid JSON.")

        items_list = payload.get("items")
        if not isinstance(items_list, list):
            raise ValueError("Credibility response missing 'items' array.")

        result: dict[int, dict[str, Any]] = {}
        for item in items_list:
            if not isinstance(item, dict):
                continue
            try:
                rec_id = int(item.get("id"))
            except (TypeError, ValueError):
                continue

            score = max(0, min(100, int(item.get("confidence_score", 50))))
            label = item.get("credibility_label", _score_to_label(score))
            if label not in {l for _, l in CREDIBILITY_LABELS}:
                label = _score_to_label(score)

            reason = str(item.get("credibility_reason", "")).strip()
            result[rec_id] = {
                "confidence_score": score,
                "credibility_label": label,
                "credibility_reason": reason,
            }

        return result

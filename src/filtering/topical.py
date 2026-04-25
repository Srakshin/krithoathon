"""Topical relevance filtering for Horizon content."""

from __future__ import annotations

import re
from typing import Any

from ..domain.models import ContentItem, FilteringConfig

NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


class TopicalContentFilter:
    """Keep the dataset focused on EdTech, school software, and teacher tools."""

    def __init__(self, config: FilteringConfig):
        combined_keywords = list(config.focus_keywords or []) + list(config.keywords or [])
        self.focus_keywords = self._dedupe(combined_keywords)
        self.exclude_keywords = self._dedupe(config.exclude_keywords or [])
        self.minimum_topic_score = float(config.minimum_topic_score)
        self.strict_relevance = bool(config.strict_relevance)

    def is_relevant_item(self, item: ContentItem) -> bool:
        relevant, _, _ = self.evaluate_item(item)
        return relevant

    def evaluate_item(self, item: ContentItem) -> tuple[bool, float, list[str]]:
        return self.evaluate_fields(
            title=item.title,
            summary=item.ai_summary,
            content=item.content,
            url=str(item.url),
            metadata=item.metadata,
        )

    def is_relevant_payload(
        self,
        *,
        title: str = "",
        summary: str = "",
        content: str = "",
        url: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        relevant, _, _ = self.evaluate_fields(
            title=title,
            summary=summary,
            content=content,
            url=url,
            metadata=metadata,
        )
        return relevant

    def evaluate_fields(
        self,
        *,
        title: str = "",
        summary: str = "",
        content: str = "",
        url: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, float, list[str]]:
        metadata = metadata or {}

        title_text = self._normalize(title)
        summary_text = self._normalize(summary)
        content_text = self._normalize(content)
        url_text = self._normalize(url)
        meta_text = self._normalize(self._flatten_metadata(metadata))
        combined_text = " ".join(
            part for part in [title_text, summary_text, content_text, url_text, meta_text] if part
        )

        score = 0.0
        matches: list[str] = []

        for keyword in self.focus_keywords:
            if self._matches(keyword, title_text):
                score += 2.5
                matches.append(keyword)
                continue
            if self._matches(keyword, summary_text):
                score += 2.0
                matches.append(keyword)
                continue
            if self._matches(keyword, meta_text) or self._matches_context(keyword, url_text):
                score += 1.75
                matches.append(keyword)
                continue
            if self._matches(keyword, content_text):
                score += 1.0
                matches.append(keyword)

        blocked = any(self._matches(blocked_kw, combined_text) for blocked_kw in self.exclude_keywords)
        relevant = score >= self.minimum_topic_score
        if not relevant and not self.strict_relevance:
            relevant = bool(matches)

        if blocked and score < self.minimum_topic_score + 1.0:
            relevant = False

        return relevant, score, self._dedupe(matches)

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            normalized = (value or "").strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append(normalized)
        return result

    @staticmethod
    def _normalize(value: Any) -> str:
        return " ".join(str(value or "").lower().split())

    def _matches(self, keyword: str, text: str) -> bool:
        if not text:
            return False

        compact_keyword = self._compact(keyword)
        if compact_keyword and len(compact_keyword) <= 4:
            pattern = rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])"
            return re.search(pattern, text) is not None

        return keyword in text

    def _matches_context(self, keyword: str, text: str) -> bool:
        if not text:
            return False
        if keyword in text:
            return True

        compact_keyword = self._compact(keyword)
        compact_text = self._compact(text)
        if not compact_keyword or not compact_text:
            return False
        return compact_keyword in compact_text

    @staticmethod
    def _compact(value: str) -> str:
        return NON_ALNUM_RE.sub("", value.lower())

    def _flatten_metadata(self, payload: Any) -> str:
        if isinstance(payload, dict):
            return " ".join(self._flatten_metadata(value) for value in payload.values())
        if isinstance(payload, list):
            return " ".join(self._flatten_metadata(value) for value in payload)
        return str(payload or "")

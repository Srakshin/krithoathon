from datetime import datetime, timezone

from src import server
from src.domain.models import ContentItem, SourceType


def test_normalize_scraped_item_shapes_reddit_content() -> None:
    item = ContentItem(
        id="reddit-1",
        source_type=SourceType.REDDIT,
        title="Teachers are overwhelmed",
        url="https://example.com/reddit-1",
        content="<p>Teachers are overwhelmed by admin work and parent updates.</p>",
        published_at=datetime(2026, 4, 25, 6, 30, tzinfo=timezone.utc),
        metadata={"subreddit": "Teachers"},
    )

    normalized = server._normalize_scraped_item(item)

    assert normalized["source"] == "reddit"
    assert normalized["source_label"] == "Reddit"
    assert normalized["sub_source"] == "r/Teachers"
    assert normalized["category"] == "User Pain Points"
    assert normalized["summary"] == "Teachers are overwhelmed by admin work and parent updates."


def test_normalize_scraped_item_marks_github_as_competitor_update() -> None:
    item = ContentItem(
        id="github-1",
        source_type=SourceType.GITHUB,
        title="openSIS released v1.2.0",
        url="https://github.com/openSIS/openSIS-Classic/releases/tag/v1.2.0",
        content="New release with attendance and reporting improvements.",
        published_at=datetime(2026, 4, 25, 5, 0, tzinfo=timezone.utc),
        metadata={"repo": "openSIS/openSIS-Classic"},
    )

    normalized = server._normalize_scraped_item(item)

    assert normalized["source_label"] == "GitHub"
    assert normalized["sub_source"] == "openSIS/openSIS-Classic"
    assert normalized["category"] == "Competitor Updates"


def test_build_digest_payload_groups_records_and_counts_sources() -> None:
    records = [
        {
            "title": "A",
            "url": "https://example.com/a",
            "source": "reddit",
            "source_label": "Reddit",
            "category": "User Pain Points",
            "summary": "Teacher pain point",
            "published_at": "2026-04-25T06:00:00+00:00",
        },
        {
            "title": "B",
            "url": "https://example.com/b",
            "source": "rss",
            "source_label": "RSS",
            "category": "Emerging Tech Trends",
            "summary": "Trend",
            "published_at": "2026-04-25T05:00:00+00:00",
        },
        {
            "title": "C",
            "url": "https://example.com/c",
            "source": "rss",
            "source_label": "RSS",
            "category": "Emerging Tech Trends",
            "summary": "Another trend",
            "published_at": "2026-04-25T04:00:00+00:00",
        },
    ]

    payload = server._build_digest_payload(
        records,
        user_id="user-123",
        date="2026-04-25",
        message="Fetched successfully.",
    )

    assert payload["date"] == "2026-04-25"
    assert payload["message"] == "Fetched successfully."
    assert payload["total_items"] == 3
    assert list(payload["categories"]) == [
        "User Pain Points",
        "Emerging Tech Trends",
    ]
    assert payload["source_counts"] == {
        "RSS": 2,
        "Reddit": 1,
    }


def test_storage_error_message_for_permission_failures() -> None:
    message = server._storage_error_message(Exception("new row violates row-level security policy"))
    assert "Supabase blocked the insert" in message

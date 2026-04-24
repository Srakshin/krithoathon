import pytest
from datetime import datetime, timezone
import json
import os

from src.domain.models import Config, FilteringConfig, ContentItem, SourceType, AIConfig, AIProvider, SourcesConfig
from src.pipeline import HorizonOrchestrator
from src.ai.analyzer import ContentAnalyzer
from src.ai.summarizer import DailySummarizer
from src.storage.file_store import FileStore


def test_keyword_filtering():
    """Verify that keyword filtering correctly includes only items matching keywords in title or content."""
    filtering = FilteringConfig(
        ai_score_threshold=7.0,
        time_window_hours=24,
        keywords=["edtech", "teacher"]
    )
    config = Config(
        version="1.0",
        ai=AIConfig(provider=AIProvider.ANTHROPIC, model="test", api_key_env="K"),
        sources=SourcesConfig(),
        filtering=filtering
    )
    store = FileStore("data_test")
    orchestrator = HorizonOrchestrator(config, store)
    
    items = [
        ContentItem(id="1", source_type=SourceType.RSS, title="Some random tech news", url="http://example.com/1", published_at=datetime.now(timezone.utc)),
        ContentItem(id="2", source_type=SourceType.RSS, title="Great EdTech update", url="http://example.com/2", published_at=datetime.now(timezone.utc)),
        ContentItem(id="3", source_type=SourceType.RSS, title="Another post", content="Teachers love this tool", url="http://example.com/3", published_at=datetime.now(timezone.utc)),
    ]
    
    filtered = orchestrator._keyword_filter(items)
    
    assert len(filtered) == 2
    assert filtered[0].id == "2"
    assert filtered[1].id == "3"


class MockAIClient:
    def __init__(self, response_text):
        self.response_text = response_text
        
    async def complete(self, system, user):
        return self.response_text


@pytest.mark.asyncio
async def test_analyzer_scoring_and_irrelevance():
    """Verify that the analyzer correctly parses float scores and categorizations."""
    client = MockAIClient('{"category": "Irrelevant", "summary": "just noise", "score": 2.5}')
    analyzer = ContentAnalyzer(client)
    
    item = ContentItem(id="1", source_type=SourceType.RSS, title="Noise", url="http://example.com", published_at=datetime.now(timezone.utc))
    
    res = await analyzer.analyze_batch([item])
    
    assert len(res) == 1
    assert res[0].category == "Irrelevant"
    assert res[0].ai_score == 2.5
    
    # Test penalizing an irrelevant item that hallucinated a high score
    client_high = MockAIClient('{"category": "Irrelevant", "summary": "just noise", "score": 8.0}')
    analyzer_high = ContentAnalyzer(client_high)
    item_high = ContentItem(id="2", source_type=SourceType.RSS, title="Noise", url="http://example.com", published_at=datetime.now(timezone.utc))
    res2 = await analyzer_high.analyze_batch([item_high])
    
    assert res2[0].ai_score == 0.0


@pytest.mark.asyncio
async def test_summarizer_grouping():
    """Verify the daily summarizer properly groups configured categories and explicitly ignores Irrelevant items."""
    summarizer = DailySummarizer()
    
    items = [
        ContentItem(id="1", source_type=SourceType.RSS, title="Trend info", url="http://x.com/1", published_at=datetime.now(timezone.utc), category="Emerging Tech Trends", ai_score=9.0),
        ContentItem(id="2", source_type=SourceType.RSS, title="Competitor launch", url="http://x.com/2", published_at=datetime.now(timezone.utc), category="Competitor Updates", ai_score=8.5),
        ContentItem(id="3", source_type=SourceType.RSS, title="Random spam", url="http://x.com/3", published_at=datetime.now(timezone.utc), category="Irrelevant", ai_score=2.0)
    ]
    
    summary = await summarizer.generate_summary(items, "2026-04-24", 10, "en")
    
    assert "### Emerging Tech Trends" in summary
    assert "### Competitor Updates" in summary
    assert "Trend info" in summary
    assert "Competitor launch" in summary
    
    # Should be omitted completely
    assert "Random spam" not in summary
    # Cat never populated, so shouldn't appear
    assert "User Pain Points" not in summary


def test_file_store_saving(tmp_path):
    """Verify storing functions create valid markdown files."""
    data_dir = tmp_path / "data"
    store = FileStore(str(data_dir))
    
    content = "# Test Summary\n\nData goes here"
    store.save_summary(content, "2026-04-24", "en")
    
    expected_path = data_dir / "summaries" / "2026-04-24-summary-en.md"
    assert expected_path.exists()
    assert expected_path.read_text("utf-8") == content

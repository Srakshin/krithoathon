"""Core data and configuration models for Horizon."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl


class SourceType(str, Enum):
    GITHUB = "github"
    HACKERNEWS = "hackernews"
    RSS = "rss"
    REDDIT = "reddit"
    TELEGRAM = "telegram"


class ContentItem(BaseModel):
    id: str
    source_type: SourceType
    title: str
    url: HttpUrl
    content: Optional[str] = None
    author: Optional[str] = None
    published_at: datetime
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)
    ai_score: Optional[float] = None
    ai_reason: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_tags: list[str] = Field(default_factory=list)
    category: Optional[str] = None


class AIProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    ALI = "ali"
    GEMINI = "gemini"
    DOUBAO = "doubao"
    MINIMAX = "minimax"


class AIConfig(BaseModel):
    provider: AIProvider
    model: str
    base_url: Optional[str] = None
    api_key_env: str
    temperature: float = 0.3
    max_tokens: int = 4096
    languages: list[str] = Field(default_factory=lambda: ["en"])


class GitHubSourceConfig(BaseModel):
    type: str
    username: Optional[str] = None
    owner: Optional[str] = None
    repo: Optional[str] = None
    enabled: bool = True


class HackerNewsConfig(BaseModel):
    enabled: bool = True
    fetch_top_stories: int = 30
    min_score: int = 100


class RSSSourceConfig(BaseModel):
    name: str
    url: HttpUrl
    enabled: bool = True
    category: Optional[str] = None


class RedditSubredditConfig(BaseModel):
    subreddit: str
    enabled: bool = True
    sort: str = "hot"
    time_filter: str = "day"
    fetch_limit: int = 25
    min_score: int = 10


class RedditUserConfig(BaseModel):
    username: str
    enabled: bool = True
    sort: str = "new"
    fetch_limit: int = 10


class RedditConfig(BaseModel):
    enabled: bool = True
    subreddits: list[RedditSubredditConfig] = Field(default_factory=list)
    users: list[RedditUserConfig] = Field(default_factory=list)
    fetch_comments: int = 5


class TelegramChannelConfig(BaseModel):
    channel: str
    enabled: bool = True
    fetch_limit: int = 20


class TelegramConfig(BaseModel):
    enabled: bool = True
    channels: list[TelegramChannelConfig] = Field(default_factory=list)


class SourcesConfig(BaseModel):
    github: list[GitHubSourceConfig] = Field(default_factory=list)
    hackernews: HackerNewsConfig = Field(default_factory=HackerNewsConfig)
    rss: list[RSSSourceConfig] = Field(default_factory=list)
    reddit: RedditConfig = Field(default_factory=RedditConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)


class EmailConfig(BaseModel):
    imap_server: str
    imap_port: int = 993
    smtp_server: str
    smtp_port: int = 465
    email_address: str
    password_env: str = "EMAIL_PASSWORD"
    sender_name: str = "Horizon Daily"
    subscribe_keyword: str = "SUBSCRIBE"
    unsubscribe_keyword: str = "UNSUBSCRIBE"
    enabled: bool = False


class FilteringConfig(BaseModel):
    ai_score_threshold: float = 7.0
    time_window_hours: int = 24
    keywords: list[str] = Field(default_factory=list)


class Config(BaseModel):
    version: str = "1.0"
    ai: AIConfig
    sources: SourcesConfig
    filtering: FilteringConfig
    email: Optional[EmailConfig] = None

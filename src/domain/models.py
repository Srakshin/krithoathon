"""Core data and configuration models for Horizon."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl


DEFAULT_TOPIC_KEYWORDS = [
    "edtech",
    "education technology",
    "school management software",
    "student information system",
    "sis",
    "learning management system",
    "lms",
    "gradebook",
    "attendance",
    "parent communication",
    "classroom management",
    "lesson planning",
    "teacher tools",
    "teacher productivity",
    "assessment tools",
    "assignments",
    "curriculum tools",
    "school erp",
    "school administration software",
    "school operations",
    "classroom ai",
    "classroom ai tools",
    "k-12 software",
    "higher ed software",
    "tutoring platform",
    "learning platform",
    "parent portal",
]

DEFAULT_EXCLUDE_KEYWORDS = [
    "cryptocurrency",
    "crypto",
    "stock market",
    "celebrity",
    "entertainment",
    "movie",
    "music",
    "sports",
    "gaming",
    "politics",
    "election",
]


class SourceType(str, Enum):
    GITHUB = "github"
    HACKERNEWS = "hackernews"
    RSS = "rss"
    REDDIT = "reddit"
    TELEGRAM = "telegram"
    WEB = "web"


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


class FetchStrategy(str, Enum):
    API = "api"
    HTTP = "http"
    BROWSER = "browser"
    AUTO = "auto"


class WebPageKind(str, Enum):
    AUTO = "auto"
    PAGE = "page"
    LISTING = "listing"
    FEED = "feed"


class FetchControls(BaseModel):
    strategy: FetchStrategy = FetchStrategy.AUTO
    timeout_seconds: float = 30.0
    retry_attempts: int = 2


class BrowserAuthConfig(BaseModel):
    headers_env: Optional[str] = None
    cookies_env: Optional[str] = None
    storage_state_env: Optional[str] = None
    session_storage_env: Optional[str] = None
    proxy_env: Optional[str] = None
    user_agent_env: Optional[str] = None


class BrowserSourceConfig(BaseModel):
    wait_until: str = "networkidle"
    wait_for_selector: Optional[str] = None
    item_selector: Optional[str] = None
    title_selector: Optional[str] = None
    summary_selector: Optional[str] = None
    link_selector: Optional[str] = None
    date_selector: Optional[str] = None
    scroll_steps: int = 0
    scroll_pause_ms: int = 1200
    auth: BrowserAuthConfig = Field(default_factory=BrowserAuthConfig)


class GitHubSourceConfig(FetchControls):
    type: str
    username: Optional[str] = None
    owner: Optional[str] = None
    repo: Optional[str] = None
    enabled: bool = True


class HackerNewsConfig(FetchControls):
    enabled: bool = True
    fetch_top_stories: int = 30
    min_score: int = 100


class RSSSourceConfig(FetchControls):
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


class RedditConfig(FetchControls):
    enabled: bool = True
    subreddits: list[RedditSubredditConfig] = Field(default_factory=list)
    users: list[RedditUserConfig] = Field(default_factory=list)
    fetch_comments: int = 5


class TelegramChannelConfig(BaseModel):
    channel: str
    enabled: bool = True
    fetch_limit: int = 20


class TelegramConfig(FetchControls):
    enabled: bool = True
    channels: list[TelegramChannelConfig] = Field(default_factory=list)


class WebSourceConfig(FetchControls):
    name: str
    url: HttpUrl
    enabled: bool = True
    category: Optional[str] = None
    page_kind: WebPageKind = WebPageKind.AUTO
    max_items: int = 10
    allowed_domains: list[str] = Field(default_factory=list)
    include_url_patterns: list[str] = Field(default_factory=list)
    exclude_url_patterns: list[str] = Field(default_factory=list)
    browser: BrowserSourceConfig = Field(default_factory=BrowserSourceConfig)


class SourcesConfig(BaseModel):
    github: list[GitHubSourceConfig] = Field(default_factory=list)
    hackernews: HackerNewsConfig = Field(default_factory=HackerNewsConfig)
    rss: list[RSSSourceConfig] = Field(default_factory=list)
    reddit: RedditConfig = Field(default_factory=RedditConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    web: list[WebSourceConfig] = Field(default_factory=list)


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
    focus_keywords: list[str] = Field(default_factory=lambda: DEFAULT_TOPIC_KEYWORDS.copy())
    exclude_keywords: list[str] = Field(default_factory=lambda: DEFAULT_EXCLUDE_KEYWORDS.copy())
    minimum_topic_score: float = 2.0
    strict_relevance: bool = True


class Config(BaseModel):
    version: str = "1.0"
    ai: AIConfig
    sources: SourcesConfig
    filtering: FilteringConfig
    email: Optional[EmailConfig] = None

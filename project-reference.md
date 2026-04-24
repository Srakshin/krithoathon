# Horizon Project Reference

This file is the high-level map of the repository so you can understand the project without re-reading the entire codebase each time.

## What This Project Does

Horizon is an AI-assisted information aggregation system. It:

1. Loads a user-defined config from `data/config.json`
2. Fetches items from configured sources
3. Deduplicates raw items across sources
4. Scores each item with AI
5. Filters to important items using a score threshold
6. Optionally deduplicates overlapping topics with AI
7. Enriches important items with background context using web search + AI
8. Renders daily Markdown summaries in one or more languages
9. Saves summaries locally, publishes them into `docs/_posts`, and can email them to subscribers

There is also an MCP server layer that exposes the pipeline as staged tools and stores per-run artifacts.

## Main Entrypoints

- `src/cli.py`
  Runs the normal Horizon pipeline from the command line via `horizon`.
- `src/configuration/setup_wizard.py`
  Interactive setup wizard exposed as `horizon-wizard`.
- `src/mcp/server.py`
  MCP server entrypoint exposed as `horizon-mcp`.

## Core Runtime Flow

The main runtime lives in `src/pipeline.py` as `HorizonOrchestrator`.

Execution order:

1. Load config with `FileStore`
2. Optionally process email subscribe/unsubscribe messages
3. Determine `since` timestamp from `time_window_hours` or `--hours`
4. Fetch from all enabled sources concurrently
5. Merge cross-source duplicates by normalized URL
6. Score items with AI using `ContentAnalyzer`
7. Keep only items with `ai_score >= ai_score_threshold`
8. Merge topic duplicates using an AI dedup pass
9. Enrich kept items with background knowledge using `ContentEnricher`
10. Generate one summary per configured language with `DailySummarizer`
11. Save summary to `data/summaries/`
12. Copy summary into `docs/_posts/` for GitHub Pages
13. Optionally email summary to subscribers
14. Print token usage totals for the run

## Directory Map

### `src/`

- `src/cli.py`
  CLI entrypoint, banner, config loading, top-level error handling.
- `src/pipeline.py`
  Main orchestrator and end-to-end runtime flow.

### `src/domain/`

- `src/domain/models.py`
  Pydantic models for:
  - content items
  - source configs
  - AI config
  - filtering config
  - email config
  - full project config

`ContentItem` is the main object moving through the pipeline.

Important `ContentItem` fields:

- `id`, `source_type`, `title`, `url`
- `content`, `author`, `published_at`
- `metadata`
- `ai_score`, `ai_reason`, `ai_summary`, `ai_tags`

### `src/scrapers/`

Each scraper returns `list[ContentItem]`.

- `src/scrapers/base_scraper.py`
  Abstract scraper interface and ID generation helper.
- `src/scrapers/github.py`
  Supports:
  - GitHub user public events
  - GitHub repo releases
- `src/scrapers/hackernews.py`
  Fetches top HN stories, filters by score and time, includes top comments.
- `src/scrapers/rss.py`
  Fetches RSS/Atom feeds, supports env-var substitution inside feed URLs like `${LWN_KEY}`.
- `src/scrapers/reddit.py`
  Fetches subreddit posts and user submissions, can also fetch top comments.
- `src/scrapers/telegram.py`
  Scrapes public Telegram channels from `https://t.me/s/...` HTML previews.

### `src/ai/`

- `src/ai/client.py`
  Multi-provider AI client abstraction. Supported providers:
  - Anthropic
  - OpenAI
  - Gemini
  - DashScope/Ali
  - Doubao via OpenAI-compatible client
  - MiniMax
- `src/ai/analyzer.py`
  First AI pass. Produces score, reason, summary, and tags.
- `src/ai/enricher.py`
  Second AI pass. Extracts concepts, runs DuckDuckGo web searches, then generates grounded context and multilingual detailed summaries.
- `src/ai/summarizer.py`
  Pure Markdown renderer for the final daily digest.
- `src/ai/prompts.py`
  Prompt definitions for analysis, enrichment, and topic dedup.
- `src/ai/utils.py`
  Robust JSON extraction from AI responses.
- `src/ai/tokens.py`
  In-memory token usage tracker for the current process.

### `src/storage/`

- `src/storage/file_store.py`
  Handles:
  - config load/save
  - daily summary save
  - subscriber list storage

### `src/notifications/`

- `src/notifications/email_service.py`
  IMAP inbox processing for subscribe/unsubscribe requests and SMTP summary delivery.

### `src/configuration/`

- `src/configuration/setup_wizard.py`
  Interactive config creation flow.
- `src/configuration/preset_library.py`
  Loads recommended source presets from API or local JSON and matches them to user interests.
- `src/configuration/source_recommender.py`
  Uses AI to suggest extra sources beyond presets.
- `src/configuration/recommendation_prompts.py`
  Prompts for the setup wizard's AI recommendation step.
- `src/configuration/tag_aliases.py`
  Multilingual tag aliases used for matching interests to preset sources.

### `src/mcp/`

This is a staged service wrapper around the normal Horizon pipeline.

- `src/mcp/server.py`
  Exposes MCP tools and resources.
- `src/mcp/service.py`
  High-level staged pipeline service.
- `src/mcp/run_store.py`
  Persists run artifacts under `data/mcp-runs/`.
- `src/mcp/horizon_adapter.py`
  Dynamically loads the local Horizon repo, resolves config paths, filters enabled sources, and loads optional secrets.
- `src/mcp/errors.py`
  Structured MCP error type.

### `src/discovery/`

- `src/discovery/related_story_search.py`
  Searches HN Algolia and Reddit for related stories.

Note: this discovery module exists but is not wired into the main orchestrator flow right now.

## Config Model

Primary runtime config path:

- `data/config.json`

Template/example:

- `data/config.example.json`

Main config sections:

- `ai`
  Provider, model, API key env var, temperature, max tokens, output languages.
- `sources`
  Top-level source settings for GitHub, Hacker News, RSS, Reddit, and Telegram.
- `filtering`
  `ai_score_threshold` and `time_window_hours`.
- `email`
  Optional email delivery and subscription handling settings.

## Important Environment Variables

Common runtime keys:

- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`
- `MINIMAX_API_KEY`
- `DASHSCOPE_API_KEY`
- `GITHUB_TOKEN`

Email-related:

- Whatever `email.password_env` points to, defaulting to `EMAIL_PASSWORD`

Wizard/preset related:

- `HORIZON_API_URL`
- `HORIZON_OFFLINE`

MCP-related:

- `HORIZON_PATH`
- `HORIZON_MCP_SECRETS_PATH`

## Outputs and Persistence

### Local data outputs

- `data/config.json`
  Main runtime configuration
- `data/summaries/horizon-YYYY-MM-DD-<lang>.md`
  Final generated summary
- `data/subscribers.json`
  Subscriber list
- `data/mcp-runs/<run_id>/`
  MCP staged artifacts and metadata

### Site publishing outputs

- `docs/_posts/YYYY-MM-DD-summary-<lang>.md`
  GitHub Pages post generated from the daily summary
- `docs/feed-en.xml`
- `docs/feed-zh.xml`
- `docs/index.md`
  Jekyll home page for the published summaries

## MCP Pipeline Stages

The staged MCP workflow is:

1. `raw`
   Fetched items after cross-source URL dedup
2. `scored`
   Items after AI scoring
3. `filtered`
   Items above threshold, optionally topic-deduped
4. `enriched`
   Filtered items after context enrichment

Main MCP tools exposed in `src/mcp/server.py`:

- `hz_validate_config`
- `hz_fetch_items`
- `hz_score_items`
- `hz_filter_items`
- `hz_enrich_items`
- `hz_generate_summary`
- `hz_run_pipeline`
- `hz_list_runs`
- `hz_get_run_meta`
- `hz_get_run_stage`
- `hz_get_run_summary`
- `hz_get_metrics`

## Source-Specific Notes

### GitHub

- Auth is optional but `GITHUB_TOKEN` improves rate limits.
- Supports user events and repo releases.

### Hacker News

- Pulls top stories from Firebase API.
- Includes up to 5 top comments in `content`.

### RSS

- Feed URLs can include environment placeholders.
- Entry content prefers `summary`, then `description`, then `content`.

### Reddit

- Uses Reddit JSON endpoints directly.
- Supports subreddit and user modes.
- Includes top comments if `fetch_comments > 0`.

### Telegram

- Works only for public channels.
- Scrapes HTML preview pages, not the Telegram API.

## AI Behavior Summary

### Analysis pass

Implemented in `src/ai/analyzer.py`.

For each item, AI returns:

- `score`
- `reason`
- `summary`
- `tags`

### Topic dedup pass

Implemented inside `HorizonOrchestrator.merge_topic_duplicates()`.

- Sends titles, tags, and summaries for all selected items in one AI call
- Keeps the highest-scored item in each duplicate group
- Merges duplicate content into the kept item

### Enrichment pass

Implemented in `src/ai/enricher.py`.

For each important item:

1. AI proposes concepts that need explanation
2. DuckDuckGo search fetches web context
3. AI produces:
   - localized title
   - detailed summary
   - background
   - community discussion
   - source citations

### Final summary rendering

Implemented in `src/ai/summarizer.py`.

This renderer:

- sorts items in score order
- creates a table of contents
- formats summary/background/discussion/citations/tags
- supports English and Chinese labels
- has an empty-summary fallback

## Tests

The current tests focus mostly on MCP and AI client behavior.

- `tests/test_minimax_client.py`
  MiniMax client initialization and request behavior.
- `tests/test_mcp_adapter.py`
  Repo/config path resolution and secret loading.
- `tests/test_mcp_errors.py`
  MCP error object behavior.
- `tests/test_mcp_run_store.py`
  Run artifact persistence.
- `tests/test_mcp_service_smoke.py`
  Service-level staged pipeline smoke tests.

## Typical Commands

Install and run with `uv`:

```bash
uv run horizon-wizard
uv run horizon
uv run horizon --hours 6
uv run horizon-mcp
uv run pytest
```

## What To Edit For Common Changes

If you want to:

- add a new content source:
  implement a new scraper under `src/scrapers/`, add config models in `src/domain/models.py`, and wire it into `src/pipeline.py` and MCP source filtering if needed
- change AI scoring behavior:
  update `src/ai/prompts.py` and possibly `src/ai/analyzer.py`
- change summary layout:
  edit `src/ai/summarizer.py`
- change enrichment/citations:
  edit `src/ai/enricher.py`
- change setup recommendations:
  edit `src/configuration/preset_library.py`, `data/presets.json`, and `src/configuration/source_recommender.py`
- change staged MCP behavior:
  edit `src/mcp/service.py` and `src/mcp/server.py`

## Active vs Auxiliary Modules

Hot path in normal CLI runs:

- `src/cli.py`
- `src/pipeline.py`
- `src/domain/models.py`
- `src/storage/file_store.py`
- `src/scrapers/*`
- `src/ai/client.py`
- `src/ai/analyzer.py`
- `src/ai/enricher.py`
- `src/ai/summarizer.py`
- `src/notifications/email_service.py`

Used mainly during setup:

- `src/configuration/*`

Used mainly for integrations and tooling:

- `src/mcp/*`

Present but not currently integrated into the main orchestration path:

- `src/discovery/related_story_search.py`

## Mental Model

The cleanest way to think about the project is:

- `scrapers` gather raw signals
- `pipeline` coordinates the flow
- `ai` decides importance and adds context
- `summarizer` turns selected items into publishable Markdown
- `storage` and `notifications` handle persistence and delivery
- `mcp` exposes the same pipeline as reusable staged tools

## Maintenance Note

Keep this file updated when any of the following change:

- source types
- config schema
- pipeline stages
- AI providers
- summary output locations
- MCP tools or run artifact layout

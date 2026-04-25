"""FastAPI server for Morning Pulse digests and manual scraper fetches.

Route protection is handled via Supabase access-token validation.
Start with: ``uvicorn src.server:app --reload``
"""

from __future__ import annotations

import logging
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from typing import Annotated, Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import AuthError, Client, create_client
from supabase.lib.client_options import SyncClientOptions

from .ai.grok_categorizer import GrokCategorizer, TARGET_CATEGORIES
from .domain.models import ContentItem, SourceType
from .pipeline import HorizonOrchestrator
from .storage.file_store import FileStore

load_dotenv()

logger = logging.getLogger("morning_pulse")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_FETCH_HOURS = 24

SOURCE_LABELS = {
    SourceType.GITHUB.value: "GitHub",
    SourceType.HACKERNEWS.value: "Hacker News",
    SourceType.RSS.value: "RSS",
    SourceType.REDDIT.value: "Reddit",
    SourceType.TELEGRAM.value: "Telegram",
    SourceType.WEB.value: "Web",
}

TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
PREFERRED_CATEGORY_ORDER = [
    *TARGET_CATEGORIES,
    "Market Signals",
    "Uncategorized",
]

# ---------------------------------------------------------------------------
# Supabase configuration
# ---------------------------------------------------------------------------
SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY: str = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_ANON_KEY must be set in the environment."
    )

# Shared client used only for auth/token verification.
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def _build_db_client(access_token: str | None = None) -> Client:
    """Create a client for database reads/writes.

    Prefer the service-role key when present; otherwise scope requests to the
    currently authenticated user's bearer token so RLS policies apply.
    """

    if SUPABASE_SERVICE_ROLE_KEY:
        return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    if not access_token:
        raise RuntimeError("An authenticated access token is required for database access.")

    client = create_client(
        SUPABASE_URL,
        SUPABASE_ANON_KEY,
        options=SyncClientOptions(
            headers={"Authorization": f"Bearer {access_token}"},
            auto_refresh_token=False,
            persist_session=False,
        ),
    )
    client.postgrest.auth(access_token)
    return client


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Morning Pulse API",
    description="Serves digests and manual scraper fetches with Supabase auth.",
    version="0.2.0",
)

frontend_origin = os.environ.get("FRONTEND_URL", "").rstrip("/")
allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
if frontend_origin and frontend_origin not in allowed_origins:
    allowed_origins.append(frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_bearer_scheme = HTTPBearer()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _fetch_authenticated_user(token: str):
    """Resolve the current Supabase user for a bearer token."""

    try:
        response = supabase.auth.get_user(token)
    except AuthError as exc:
        raise _unauthorized(f"Invalid authentication token: {exc}")
    except Exception as exc:  # pragma: no cover - defensive network failure path
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to verify authentication right now: {exc}",
        )

    user = response.user if response else None
    if not user:
        raise _unauthorized("Authenticated user could not be resolved.")
    if user.aud != "authenticated":
        raise _unauthorized("Invalid authentication audience.")

    return user


def _verify_supabase_jwt(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
) -> dict[str, str | None]:
    """Validate a Supabase access token and return basic user claims."""

    user = _fetch_authenticated_user(credentials.credentials)
    return {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "aud": user.aud,
    }


def _get_authenticated_request(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
) -> dict[str, Any]:
    """Return auth claims plus a request-scoped Supabase DB client."""

    user = _fetch_authenticated_user(credentials.credentials)
    return {
        "claims": {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "aud": user.aud,
        },
        "token": credentials.credentials,
        "db": _build_db_client(credentials.credentials),
    }


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------
def _is_missing_table_error(exc: Exception) -> bool:
    """Return True if the exception signals that the table doesn't exist yet."""

    msg = str(exc)
    return "PGRST205" in msg or "does not exist" in msg or "schema cache" in msg


def _is_permission_error(exc: Exception) -> bool:
    """Return True for common RLS / permission-denied errors."""

    msg = str(exc).lower()
    return (
        "permission denied" in msg
        or "row-level security" in msg
        or "violates row-level security policy" in msg
        or "42501" in msg
    )


def _storage_error_message(exc: Exception) -> str:
    """Translate DB write failures into user-facing guidance."""

    if _is_missing_table_error(exc):
        return (
            "Fetched scraper data, but couldn't store it because the "
            "'market_intelligence' table is missing. Run 'supabase_setup.sql' "
            "in the Supabase SQL Editor, then try again."
        )

    if _is_permission_error(exc):
        return (
            "Fetched scraper data, but Supabase blocked the insert. Re-run "
            "'supabase_setup.sql' to add authenticated insert access, or set "
            "'SUPABASE_SERVICE_ROLE_KEY' on the backend."
        )

    return f"Fetched scraper data, but couldn't store it in Supabase: {exc}"


def _read_error_message(exc: Exception) -> str:
    """Translate DB read failures into user-facing guidance."""

    if _is_missing_table_error(exc):
        return (
            "The database table 'market_intelligence' does not exist yet. Run "
            "'supabase_setup.sql' in the Supabase SQL Editor, then reload."
        )

    if _is_permission_error(exc):
        return (
            "The dashboard couldn't read from Supabase because the current RLS "
            "policies block access. Re-run 'supabase_setup.sql' or configure "
            "'SUPABASE_SERVICE_ROLE_KEY' on the backend."
        )

    return f"Failed to read digest data from Supabase: {exc}"


# ---------------------------------------------------------------------------
# Digest shaping helpers
# ---------------------------------------------------------------------------
def _today_window() -> tuple[str, str, str]:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return today, f"{today}T00:00:00+00:00", f"{today}T23:59:59+00:00"


def _plain_text(value: str | None) -> str:
    if not value:
        return ""

    text = unescape(TAG_RE.sub(" ", value))
    text = text.replace("\xa0", " ")
    return WHITESPACE_RE.sub(" ", text).strip()


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def _source_label(source: str | SourceType | None) -> str:
    if isinstance(source, SourceType):
        source = source.value
    return SOURCE_LABELS.get(source or "", "Web")


def _sub_source_label(item: ContentItem) -> str | None:
    meta = item.metadata or {}
    if meta.get("subreddit"):
        return f"r/{meta['subreddit']}"
    if meta.get("feed_name"):
        return str(meta["feed_name"])
    if meta.get("channel"):
        return f"@{meta['channel']}"
    if meta.get("repo"):
        return str(meta["repo"])
    if item.author:
        return item.author
    return None


def _build_summary(item: ContentItem) -> str:
    summary = _plain_text(item.ai_summary)
    if summary:
        return _truncate(summary, 320)

    content = _plain_text(item.content)
    if content:
        return _truncate(content, 320)

    return _truncate(_plain_text(item.title), 180)


def _normalize_scraped_item(item: ContentItem) -> dict[str, Any]:
    return {
        "title": item.title,
        "url": str(item.url),
        "source": item.source_type.value,
        "source_label": _source_label(item.source_type),
        "sub_source": _sub_source_label(item),
        "summary": _build_summary(item),
        "published_at": item.published_at.astimezone(timezone.utc).isoformat(),
    }


def _fetch_records_by_urls(db: Client, urls: list[str]) -> list[dict[str, Any]]:
    unique_urls = list(dict.fromkeys(url for url in urls if url))
    if not unique_urls:
        return []

    response = db.table("market_intelligence").select("*").in_("url", unique_urls).execute()
    return response.data or []


def _build_records_to_insert(
    items: list[dict[str, Any]],
    existing_urls: set[str],
) -> list[dict[str, Any]]:
    return [
        {
            "title": item["title"],
            "url": item["url"],
            "source": item["source"],
            "category": None,
            "summary": item["summary"],
        }
        for item in items
        if item.get("url") and item["url"] not in existing_urls
    ]


def _needs_grok_analysis(record: dict[str, Any]) -> bool:
    category = str(record.get("category") or "").strip()
    return category not in TARGET_CATEGORIES


async def _categorize_records_in_database(
    db: Client,
    records: list[dict[str, Any]],
) -> int:
    if not records:
        return 0

    categorizer = GrokCategorizer()
    updates = await categorizer.categorize_records(records)

    for record_id, values in updates.items():
        (
            db.table("market_intelligence")
            .update(
                {
                    "category": values["category"],
                    "summary": values["summary"],
                }
            )
            .eq("id", record_id)
            .execute()
        )

    return len(updates)


def _normalize_db_record(record: dict[str, Any]) -> dict[str, Any]:
    published_at = record.get("published_at") or record.get("created_at")
    return {
        "title": record.get("title"),
        "url": record.get("url"),
        "source": record.get("source"),
        "source_label": _source_label(record.get("source")),
        "sub_source": record.get("sub_source"),
        "category": record.get("category") or "Uncategorized",
        "summary": record.get("summary") or "",
        "published_at": published_at,
        "created_at": record.get("created_at"),
    }


def _sort_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda record: record.get("published_at") or record.get("created_at") or "",
        reverse=True,
    )


def _group_digest_records(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in _sort_records(records):
        grouped[record.get("category") or "Uncategorized"].append(record)

    ordered: dict[str, list[dict[str, Any]]] = {}
    for category in PREFERRED_CATEGORY_ORDER:
        if category in grouped:
            ordered[category] = grouped[category]

    for category in sorted(grouped):
        if category not in ordered:
            ordered[category] = grouped[category]

    return ordered


def _source_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for record in records:
        counts[_source_label(record.get("source"))] += 1
    return dict(sorted(counts.items()))


def _build_digest_payload(
    records: list[dict[str, Any]],
    *,
    user_id: str | None,
    date: str | None = None,
    message: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    digest_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    payload = {
        "date": digest_date,
        "greeting": f"Good morning! Here's your Morning Pulse for {digest_date}.",
        "message": message,
        "total_items": len(records),
        "user_id": user_id,
        "source_counts": _source_counts(records),
        "categories": _group_digest_records(records),
    }
    if extra:
        payload.update(extra)
    return payload


def _load_orchestrator() -> HorizonOrchestrator:
    storage = FileStore(data_dir=str(DATA_DIR))
    try:
        config = storage.load_config()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Configuration file not found. Create 'data/config.json' before "
                f"running the scrapers. Details: {exc}"
            ),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load scraper configuration: {exc}",
        )

    return HorizonOrchestrator(config, storage)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    """Health-check / landing endpoint."""

    return {
        "service": "Morning Pulse API",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Basic health check for process and database configuration."""

    database = {
        "mode": "service_role" if SUPABASE_SERVICE_ROLE_KEY else "user_token",
        "table_ready": None,
        "message": (
            "Add SUPABASE_SERVICE_ROLE_KEY for server-side probing, or use an "
            "authenticated dashboard request to verify DB access."
        ),
    }

    if SUPABASE_SERVICE_ROLE_KEY:
        try:
            service_client = _build_db_client()
            service_client.table("market_intelligence").select("id").limit(1).execute()
            database["table_ready"] = True
            database["message"] = "market_intelligence table is reachable."
        except Exception as exc:
            database["table_ready"] = False
            database["message"] = _read_error_message(exc)

    return {
        "service": "Morning Pulse API",
        "status": "operational",
        "database": database,
    }


@app.post("/setup-db")
async def setup_db(request: dict[str, Any] = Depends(_get_authenticated_request)):
    """Try to create the market_intelligence table via RPC if available."""

    create_sql = """
    CREATE TABLE IF NOT EXISTS public.market_intelligence (
        id           BIGSERIAL PRIMARY KEY,
        created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        title        TEXT,
        url          TEXT,
        source       TEXT,
        category     TEXT,
        summary      TEXT
    );
    ALTER TABLE public.market_intelligence ENABLE ROW LEVEL SECURITY;

    DROP POLICY IF EXISTS "Authenticated users can read" ON public.market_intelligence;
    DROP POLICY IF EXISTS "Authenticated users can insert" ON public.market_intelligence;
    DROP POLICY IF EXISTS "Service role can insert" ON public.market_intelligence;

    CREATE POLICY "Authenticated users can read"
        ON public.market_intelligence
        FOR SELECT
        TO authenticated
        USING (true);

    CREATE POLICY "Authenticated users can insert"
        ON public.market_intelligence
        FOR INSERT
        TO authenticated
        WITH CHECK (true);

    CREATE POLICY "Service role can insert"
        ON public.market_intelligence
        FOR INSERT
        TO service_role
        WITH CHECK (true);
    """

    try:
        request["db"].rpc("exec_sql", {"sql": create_sql}).execute()
        return {"status": "ok", "message": "Table created/verified via RPC."}
    except Exception as rpc_exc:
        return {
            "status": "manual_action_required",
            "message": (
                "Could not auto-create the table via RPC. Please run "
                "'supabase_setup.sql' in the Supabase SQL Editor."
            ),
            "sql_file": "supabase_setup.sql",
            "rpc_error": str(rpc_exc),
        }


@app.post("/seed-data")
async def seed_data(request: dict[str, Any] = Depends(_get_authenticated_request)):
    """Insert demo data into market_intelligence so the dashboard shows content."""

    today = datetime.now(timezone.utc).isoformat()
    db = request["db"]

    demo_records = [
        {
            "created_at": today,
            "title": "Google Classroom adds AI-powered grading assistant",
            "url": "https://edu.google.com/blog/2026/ai-grading",
            "source": "rss",
            "category": "Competitor Updates",
            "summary": (
                "Google Classroom launched an AI grading assistant that drafts "
                "feedback for short-answer questions and cuts teacher workload."
            ),
        },
        {
            "created_at": today,
            "title": "Microsoft Teams for Education introduces live transcript and AI notes",
            "url": "https://techcrunch.com/2026/teams-edu-ai",
            "source": "rss",
            "category": "Competitor Updates",
            "summary": (
                "Microsoft Teams for Education rolls out real-time transcription "
                "and AI-generated lesson notes for K-12 tenants."
            ),
        },
        {
            "created_at": today,
            "title": "Teachers overwhelmed by admin tasks in Reddit megathread",
            "url": "https://reddit.com/r/Teachers/comments/example",
            "source": "reddit",
            "category": "User Pain Points",
            "summary": (
                "A large Reddit discussion highlights the hours teachers spend "
                "each week on report cards, attendance, and parent communication."
            ),
        },
        {
            "created_at": today,
            "title": "Parents frustrated with fragmented school communication apps",
            "url": "https://reddit.com/r/Parents/comments/example2",
            "source": "reddit",
            "category": "User Pain Points",
            "summary": (
                "Parents describe juggling several school communication tools for "
                "a single child, creating confusion and missed updates."
            ),
        },
        {
            "created_at": today,
            "title": "LLMs enabling real-time curriculum personalization at scale",
            "url": "https://news.ycombinator.com/item?id=42000001",
            "source": "hackernews",
            "category": "Emerging Tech Trends",
            "summary": (
                "An open-source framework enables small local LLMs to tailor "
                "lessons per student without sending data to external clouds."
            ),
        },
        {
            "created_at": today,
            "title": "Adaptive learning algorithms reduce student dropout by 22%",
            "url": "https://edsurge.com/news/2026-adaptive-learning",
            "source": "rss",
            "category": "Emerging Tech Trends",
            "summary": (
                "A multi-year pilot suggests AI-driven adaptive learning paths "
                "can improve retention in community college settings."
            ),
        },
    ]

    try:
        result = db.table("market_intelligence").insert(demo_records).execute()
        return {
            "status": "ok",
            "inserted": len(result.data or demo_records),
            "message": "Demo data seeded. Refresh the dashboard to see it.",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_storage_error_message(exc),
        )


@app.get("/daily-brief")
async def daily_brief(request: dict[str, Any] = Depends(_get_authenticated_request)):
    """Return today's saved Morning Pulse digest for the authenticated user."""

    today, start, end = _today_window()
    db = request["db"]

    try:
        response = (
            db.table("market_intelligence")
            .select("*")
            .gte("created_at", start)
            .lte("created_at", end)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
                if _is_missing_table_error(exc) or _is_permission_error(exc)
                else status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=_read_error_message(exc),
        )

    records = [_normalize_db_record(record) for record in (response.data or [])]
    return _build_digest_payload(records, user_id=request["claims"].get("sub"), date=today)


@app.post("/fetch-intelligence")
async def fetch_intelligence(
    request: dict[str, Any] = Depends(_get_authenticated_request),
    hours: int = Query(DEFAULT_FETCH_HOURS, ge=1, le=168),
):
    """Run scrapers on demand, store raw data first, then categorize it with Grok."""

    orchestrator = _load_orchestrator()
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    db = request["db"]
    today, _, _ = _today_window()

    try:
        fetched_items = await orchestrator.fetch_all_sources(since)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scraper fetch failed: {exc}",
        )

    merged_items = orchestrator.merge_cross_source_duplicates(fetched_items)
    normalized_items = [_normalize_scraped_item(item) for item in merged_items]
    normalized_items = _sort_records(normalized_items)
    inserted_count = 0
    duplicates_skipped = 0
    if not normalized_items:
        return _build_digest_payload(
            [],
            user_id=request["claims"].get("sub"),
            date=today,
            message=f"No scraper items were found in the last {hours} hours.",
            extra={
                "status": "ok",
                "storage_status": "stored",
                "analysis_status": "skipped",
                "raw_fetched_count": len(fetched_items),
                "deduplicated_count": 0,
                "inserted_count": 0,
                "duplicates_skipped": 0,
                "categorized_count": 0,
                "hours": hours,
            },
        )

    urls = [item["url"] for item in normalized_items if item.get("url")]

    try:
        existing_records = _fetch_records_by_urls(db, urls)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_read_error_message(exc),
        )

    existing_urls = {
        record.get("url")
        for record in existing_records
        if record.get("url")
    }
    records_to_insert = _build_records_to_insert(normalized_items, existing_urls)
    duplicates_skipped = len(normalized_items) - len(records_to_insert)

    try:
        if records_to_insert:
            result = db.table("market_intelligence").insert(records_to_insert).execute()
            inserted_count = len(result.data or records_to_insert)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_storage_error_message(exc),
        )

    try:
        stored_records = _fetch_records_by_urls(db, urls)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_read_error_message(exc),
        )

    records_needing_analysis = [
        record
        for record in stored_records
        if _needs_grok_analysis(record)
    ]

    try:
        categorized_count = await _categorize_records_in_database(db, records_needing_analysis)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Scraper data was stored in Supabase, but Grok returned an invalid "
                f"categorization response: {exc}"
            ),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Scraper data was stored in Supabase, but Grok categorization failed. "
                f"Check GROK_API_KEY and model access. Details: {exc}"
            ),
        )

    try:
        final_records = _fetch_records_by_urls(db, urls)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_read_error_message(exc),
        )

    normalized_records = [_normalize_db_record(record) for record in final_records]
    normalized_records = _sort_records(normalized_records)

    message = (
        f"Fetched {len(normalized_items)} deduplicated scraper items, stored "
        f"{inserted_count} new records in Supabase, and categorized "
        f"{categorized_count} stored records with Grok."
    )
    if duplicates_skipped:
        message += f" Reused {duplicates_skipped} records that were already in the database."

    return _build_digest_payload(
        normalized_records,
        user_id=request["claims"].get("sub"),
        date=today,
        message=message,
        extra={
            "status": "ok",
            "storage_status": "stored",
            "analysis_status": "completed",
            "raw_fetched_count": len(fetched_items),
            "deduplicated_count": len(normalized_items),
            "inserted_count": inserted_count,
            "duplicates_skipped": duplicates_skipped,
            "categorized_count": categorized_count,
            "hours": hours,
        },
    )

@app.get("/preferences")
async def get_preferences(request: dict[str, Any] = Depends(_get_authenticated_request)):
    """Retrieve user preferences."""
    db = request["db"]
    user_id = request["claims"]["sub"]
    
    try:
        response = db.table("user_preferences").select("*").eq("user_id", user_id).execute()
        if response.data:
            return response.data[0]
        return {}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch preferences: {exc}"
        )


@app.post("/preferences")
async def save_preferences(
    preferences: dict[str, Any],
    request: dict[str, Any] = Depends(_get_authenticated_request)
):
    """Save user preferences."""
    db = request["db"]
    user_id = request["claims"]["sub"]
    
    preferences["user_id"] = user_id
    preferences["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    try:
        check = db.table("user_preferences").select("user_id").eq("user_id", user_id).execute()
        if check.data:
            db.table("user_preferences").update(preferences).eq("user_id", user_id).execute()
        else:
            db.table("user_preferences").insert(preferences).execute()
            
        return {"status": "ok", "message": "Preferences saved successfully"}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save preferences: {exc}"
        )

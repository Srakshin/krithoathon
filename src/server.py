"""Lightweight FastAPI server for serving Morning Pulse daily digests.

Route protection is handled via Supabase JWT validation.
Start with:  uvicorn src.server:app --reload
"""

import os
from datetime import datetime, timezone
from typing import Annotated

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

load_dotenv()

# ---------------------------------------------------------------------------
# Supabase client (shared across requests)
# ---------------------------------------------------------------------------
SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY: str = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_JWT_SECRET: str = os.environ.get("SUPABASE_JWT_SECRET", "")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_ANON_KEY must be set in the environment."
    )

if not SUPABASE_JWT_SECRET:
    raise RuntimeError(
        "SUPABASE_JWT_SECRET must be set in the environment. "
        "Find it in your Supabase dashboard → Settings → API → JWT Secret."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Morning Pulse API",
    description="Serves AI-generated daily intelligence digests with Supabase auth.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bearer-token scheme used by Supabase Auth
_bearer_scheme = HTTPBearer()


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------
def _verify_supabase_jwt(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
) -> dict:
    """Decode and validate a Supabase JWT.

    Returns the decoded payload on success.
    Raises 401 Unauthorized on any validation failure.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


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


@app.get("/daily-brief")
async def daily_brief(user: dict = Depends(_verify_supabase_jwt)):
    """Return today's Morning Pulse digest.

    Requires a valid Supabase JWT in the ``Authorization: Bearer <token>`` header.

    The endpoint queries the ``market_intelligence`` table for all rows
    whose ``created_at`` falls on today's date (UTC) and returns them
    grouped by category.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        response = (
            supabase.table("market_intelligence")
            .select("*")
            .gte("created_at", f"{today}T00:00:00+00:00")
            .lte("created_at", f"{today}T23:59:59+00:00")
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch today's digest: {exc}",
        )

    records = response.data or []

    # Group items by category for a structured digest
    categorized: dict[str, list[dict]] = {}
    for record in records:
        category = record.get("category") or "Uncategorized"
        categorized.setdefault(category, []).append(
            {
                "title": record.get("title"),
                "url": record.get("url"),
                "source": record.get("source"),
                "summary": record.get("summary"),
            }
        )

    return {
        "date": today,
        "greeting": f"Good morning! Here's your Morning Pulse for {today}.",
        "total_items": len(records),
        "user_id": user.get("sub"),
        "categories": categorized,
    }

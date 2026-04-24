from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from supabase_auth.errors import AuthInvalidJwtError

from src import server


def _credentials() -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")


def test_verify_supabase_jwt_returns_basic_user_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_user = SimpleNamespace(
        id="user-123",
        email="user@example.com",
        role="authenticated",
        aud="authenticated",
    )

    monkeypatch.setattr(
        server.supabase.auth,
        "get_user",
        lambda token: SimpleNamespace(user=fake_user),
    )

    claims = server._verify_supabase_jwt(_credentials())

    assert claims == {
        "sub": "user-123",
        "email": "user@example.com",
        "role": "authenticated",
        "aud": "authenticated",
    }


def test_verify_supabase_jwt_rejects_invalid_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_invalid_token(token: str):
        raise AuthInvalidJwtError("bad token")

    monkeypatch.setattr(server.supabase.auth, "get_user", _raise_invalid_token)

    with pytest.raises(HTTPException) as exc_info:
        server._verify_supabase_jwt(_credentials())

    assert exc_info.value.status_code == 401
    assert "Invalid authentication token" in exc_info.value.detail


def test_verify_supabase_jwt_rejects_non_authenticated_audiences(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_user = SimpleNamespace(
        id="user-123",
        email="user@example.com",
        role="anon",
        aud="anon",
    )

    monkeypatch.setattr(
        server.supabase.auth,
        "get_user",
        lambda token: SimpleNamespace(user=fake_user),
    )

    with pytest.raises(HTTPException) as exc_info:
        server._verify_supabase_jwt(_credentials())

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid authentication audience."

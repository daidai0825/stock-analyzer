"""Tests for JWT authentication endpoints.

All tests use an in-memory SQLite database via aiosqlite so no external
PostgreSQL instance is required.  The application's ``get_db`` dependency is
overridden to inject the test session, and the ``Base`` metadata is created
fresh for every test module.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models.base import Base

# ---------------------------------------------------------------------------
# In-memory test database setup
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
_test_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db() -> AsyncSession:
    async with _test_session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
async def create_tables():
    """Create all ORM tables once per test module and drop them afterwards."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Async HTTP client wired to the FastAPI app with a test DB override."""
    from app.db.session import get_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def registered_user(client: AsyncClient) -> dict:
    """Register a test user and return the response payload."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "username": "testuser", "password": "secret123"},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
async def auth_token(client: AsyncClient, registered_user: dict) -> str:
    """Obtain a valid JWT for the registered test user."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "secret123"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


async def test_register_valid_data_returns_201(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "username": "newuser", "password": "password123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert body["username"] == "newuser"
    assert body["is_active"] is True
    assert "id" in body
    assert "created_at" in body
    # password must never be echoed back
    assert "password" not in body
    assert "hashed_password" not in body


async def test_register_duplicate_email_returns_409(client: AsyncClient, registered_user: dict):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": registered_user["email"],
            "username": "anotherusername",
            "password": "password123",
        },
    )
    assert resp.status_code == 409


async def test_register_duplicate_username_returns_409(
    client: AsyncClient, registered_user: dict
):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "another@example.com",
            "username": registered_user["username"],
            "password": "password123",
        },
    )
    assert resp.status_code == 409


async def test_register_short_password_returns_422(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "username": "shortpw", "password": "abc"},
    )
    assert resp.status_code == 422


async def test_register_invalid_email_returns_422(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "username": "bademail", "password": "password123"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


async def test_login_correct_credentials_returns_token(
    client: AsyncClient, registered_user: dict
):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "secret123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20  # non-trivial JWT string


async def test_login_via_email_accepted(client: AsyncClient, registered_user: dict):
    """The login endpoint should accept the email address in the username field."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": registered_user["email"], "password": "secret123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password_returns_401(client: AsyncClient, registered_user: dict):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


async def test_login_unknown_user_returns_401(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "irrelevant"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------


async def test_me_with_valid_token_returns_user(
    client: AsyncClient, registered_user: dict, auth_token: str
):
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == registered_user["username"]
    assert body["email"] == registered_user["email"]


async def test_me_without_token_returns_401(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_me_with_invalid_token_returns_401(client: AsyncClient):
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer thisisnotavalidtoken"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Protected endpoints
# ---------------------------------------------------------------------------


async def test_create_watchlist_without_token_returns_401(client: AsyncClient):
    resp = await client.post(
        "/api/v1/watchlists",
        json={"name": "My List", "symbols": ["AAPL"]},
    )
    assert resp.status_code == 401


async def test_create_watchlist_with_valid_token_succeeds(
    client: AsyncClient, auth_token: str
):
    resp = await client.post(
        "/api/v1/watchlists",
        json={"name": "My Authenticated List", "symbols": ["AAPL", "MSFT"]},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["data"]["name"] == "My Authenticated List"


async def test_create_portfolio_without_token_returns_401(client: AsyncClient):
    resp = await client.post(
        "/api/v1/portfolios",
        json={"name": "My Portfolio"},
    )
    assert resp.status_code == 401


async def test_create_portfolio_with_valid_token_succeeds(
    client: AsyncClient, auth_token: str
):
    resp = await client.post(
        "/api/v1/portfolios",
        json={"name": "My Authenticated Portfolio"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["data"]["name"] == "My Authenticated Portfolio"

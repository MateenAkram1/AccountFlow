"""Shared pytest fixtures for authenticated API tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient

from accountflow.core.config import clear_settings_cache
from accountflow.core.security import CSRF_HEADER, CSRF_VALUE
from accountflow.db.sows import clear_sow_store_cache
from accountflow.db.store import clear_run_store_cache
from accountflow.db.tokens import clear_token_store_cache
from accountflow.db.users import clear_user_store_cache
from accountflow.db.vault import clear_vault_cache
from accountflow.main import app
from accountflow.providers.registry import clear_provider_cache


@pytest.fixture
def auth_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("STT_PROVIDER", "mock")
    monkeypatch.setenv("INTEGRATIONS_MOCK", "true")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-key-for-unit-tests")
    monkeypatch.setenv("CREDENTIALS_FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("TURSO_DATABASE_URL", "")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "")
    # Isolate token store
    tokens = tmp_path / "tokens.db"
    monkeypatch.setenv("TEST_TOKENS_PATH", str(tokens))

    clear_settings_cache()
    clear_provider_cache()
    clear_user_store_cache()
    clear_vault_cache()
    clear_run_store_cache()
    clear_token_store_cache()
    clear_sow_store_cache()

    # Point TokenStore at temp path
    from accountflow.db import tokens as tokens_mod

    original = tokens_mod.TokenStore.__init__

    def _init(self, db_path=None):
        original(self, db_path or tokens)

    monkeypatch.setattr(tokens_mod.TokenStore, "__init__", _init)

    yield
    clear_settings_cache()
    clear_provider_cache()
    clear_user_store_cache()
    clear_vault_cache()
    clear_run_store_cache()
    clear_token_store_cache()
    clear_sow_store_cache()


@pytest.fixture
def mock_env(auth_env):
    """Backward-compatible alias used by older tests."""
    yield


CSRF_HEADERS = {CSRF_HEADER: CSRF_VALUE}


async def register_and_login(
    client: AsyncClient,
    email: str = "alice@example.com",
    password: str = "password123",
    name: str = "Alice",
) -> dict:
    resp = await client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": name},
    )
    if resp.status_code == 400 and "already exists" in resp.text:
        resp = await client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture
async def authed_client(auth_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await register_and_login(client)
        yield client

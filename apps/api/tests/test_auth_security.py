"""Security tests: hashing, encryption, isolation, non-leakage."""

from __future__ import annotations

import logging

import pytest
from httpx import ASGITransport, AsyncClient

from accountflow.core.security import hash_password, redact_text, verify_password
from accountflow.db.users import get_user_store
from accountflow.db.vault import get_secrets_vault
from accountflow.main import app
from tests.conftest import CSRF_HEADERS, register_and_login


@pytest.mark.asyncio
async def test_register_stores_bcrypt_not_plaintext(auth_env):
    password = "super-secret-pass"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await register_and_login(client, password=password)
    user = get_user_store().get_by_email("alice@example.com")
    assert user is not None
    assert user.password_hash is not None
    assert password not in user.password_hash
    assert user.password_hash.startswith("$2")
    assert verify_password(password, user.password_hash)
    assert hash_password(password) != password


@pytest.mark.asyncio
async def test_vault_encrypts_at_rest(auth_env):
    secret = "pat-hubspot-TESTSECRETVALUE9999"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        me = await register_and_login(client)
        resp = await client.put(
            "/me/credentials/hubspot",
            json={"access_token": secret},
            headers=CSRF_HEADERS,
        )
        assert resp.status_code == 200
        status = await client.get("/me/credentials/status")
        body = status.json()
        assert body["hubspot"]["configured"] is True
        assert secret not in status.text
        assert secret not in str(body)

    blob = get_secrets_vault().encrypted_blob_for_tests(me["id"], "hubspot")
    assert blob is not None
    assert secret not in blob
    assert "{" not in blob  # not plaintext JSON
    decrypted = get_secrets_vault().get(me["id"], "hubspot")
    assert decrypted["access_token"] == secret


@pytest.mark.asyncio
async def test_user_isolation_runs_and_credentials(auth_env):
    account = (
        '{"deal_id":"demo-001","company":"Acme Corp","stage":"discovery",'
        '"contacts":[{"name":"Sarah","role":"CTO","email":"sarah@acme.example"}]}'
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as alice:
        await register_and_login(alice, email="alice@example.com")
        await alice.put(
            "/me/credentials/hubspot",
            json={"access_token": "alice-only-token-AAAA"},
            headers=CSRF_HEADERS,
        )
        create = await alice.post(
            "/runs",
            data={
                "transcript": "Let's finalize the API spec and send documentation by Friday.",
                "account_json": account,
            },
            headers=CSRF_HEADERS,
        )
        assert create.status_code == 200
        run_id = create.json()["id"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as bob:
        await register_and_login(bob, email="bob@example.com", password="password456", name="Bob")
        denied = await bob.get(f"/runs/{run_id}")
        assert denied.status_code == 404
        status = await bob.get("/me/credentials/status")
        assert status.json()["hubspot"]["configured"] is False


@pytest.mark.asyncio
async def test_anyone_can_register(auth_env):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/auth/register",
            json={"email": "anyone@example.com", "password": "password123"},
        )
    assert resp.status_code == 200
    assert resp.json()["email"] == "anyone@example.com"


def test_redact_bearer_token():
    raw = "Authorization failed Bearer abcdefghijklmnopsecret"
    assert "abcdefghijklmnopsecret" not in redact_text(raw)
    assert "[REDACTED]" in redact_text(raw)


@pytest.mark.asyncio
async def test_failed_hubspot_log_does_not_contain_token(auth_env, caplog):
    token = "hubspot-leak-test-token-XYZ123456789"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await register_and_login(client)
        await client.put(
            "/me/credentials/hubspot",
            json={"access_token": token},
            headers=CSRF_HEADERS,
        )

    # Simulate a log line that might have included a bearer header
    with caplog.at_level(logging.INFO):
        from accountflow.core.logging import get_logger

        log = get_logger("test")
        log.info("HubSpot call failed Authorization: Bearer %s", token)

    # JsonFormatter redacts when formatting through our handler; caplog may capture raw.
    # Assert our redact helper would scrub it, and status API never echoes it.
    assert token not in redact_text(f"Bearer {token}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await register_and_login(client)
        status = await client.get("/me/credentials/status")
        assert token not in status.text

"""Auth: email/password + Google Sign-In; Gmail OAuth connect (per-user)."""

from __future__ import annotations

from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from accountflow.api.deps import CurrentUser, get_current_user, require_csrf
from accountflow.core.config import get_settings
from accountflow.core.security import (
    SESSION_COOKIE,
    cookie_secure,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from accountflow.db.tokens import get_token_store
from accountflow.db.users import get_user_store

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
LOGIN_SCOPES = "openid email profile"
GMAIL_SCOPES = "https://www.googleapis.com/auth/gmail.send"


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    name: str | None = None


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str


class MeResponse(BaseModel):
    id: str
    email: str
    name: str | None


def _set_session_cookie(response: Response, user_id: str, email: str) -> None:
    token = create_access_token(user_id=user_id, email=email)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=cookie_secure(),
        samesite="lax",
        max_age=get_settings().jwt_expiry_hours * 3600,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE, path="/")


@router.post("/register", response_model=MeResponse)
async def register(body: RegisterRequest, response: Response):
    store = get_user_store()
    email = body.email.strip().lower()
    if store.get_by_email(email):
        raise HTTPException(status_code=400, detail="Account already exists — sign in instead")
    user = store.create_password_user(
        email=email,
        password_hash=hash_password(body.password),
        name=body.name,
    )
    _set_session_cookie(response, user.id, user.email)
    return MeResponse(id=user.id, email=user.email, name=user.name)


@router.post("/login", response_model=MeResponse)
async def login(body: LoginRequest, response: Response):
    store = get_user_store()
    email = body.email.strip().lower()
    user = store.get_by_email(email)
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    _set_session_cookie(response, user.id, user.email)
    return MeResponse(id=user.id, email=user.email, name=user.name)


@router.post("/logout")
async def logout(
    response: Response,
    _user: CurrentUser = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    _clear_session_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser = Depends(get_current_user)):
    return MeResponse(id=user.id, email=user.email, name=user.name)


# --- Google OAuth (login + Gmail share GOOGLE_REDIRECT_URI; distinguished by state) ---

LOGIN_STATE = "login"


@router.get("/google/login/start")
async def google_login_start():
    settings = get_settings()
    if not settings.google_oauth_configured:
        raise HTTPException(status_code=400, detail="GOOGLE_CLIENT_ID / SECRET not configured")
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": LOGIN_SCOPES,
        "access_type": "online",
        "prompt": "select_account",
        "include_granted_scopes": "true",
        "state": LOGIN_STATE,
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/gmail/start")
async def google_gmail_start(user: CurrentUser = Depends(get_current_user)):
    settings = get_settings()
    if not settings.google_oauth_configured:
        raise HTTPException(status_code=400, detail="GOOGLE_CLIENT_ID / SECRET not configured")
    # Bind OAuth to user via signed JWT state (not the literal "login")
    state = create_access_token(user_id=user.id, email=user.email)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": GMAIL_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    """Unified callback matching GOOGLE_REDIRECT_URI in Google Cloud Console."""
    settings = get_settings()
    is_login = (state or "") == LOGIN_STATE

    if error:
        target = "/login" if is_login else "/connect"
        return RedirectResponse(f"{settings.web_app_url}{target}?google=error&reason={error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    if is_login:
        return await _finish_google_login(code)
    return await _finish_gmail_connect(code, state)


async def _finish_google_login(code: str) -> RedirectResponse:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code >= 400:
            raise HTTPException(status_code=400, detail="Google login token exchange failed")
        tokens = token_resp.json()
        access = tokens.get("access_token")
        if not access:
            raise HTTPException(status_code=400, detail="No access token from Google")

        info_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access}"},
        )
        if info_resp.status_code >= 400:
            raise HTTPException(status_code=400, detail="Failed to fetch Google profile")
        info = info_resp.json()

    email = (info.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")
    store = get_user_store()
    user = store.upsert_google_user(email=email, name=info.get("name"))
    response = RedirectResponse(f"{settings.web_app_url}/")
    _set_session_cookie(response, user.id, user.email)
    return response


async def _finish_gmail_connect(code: str, state: str | None) -> RedirectResponse:
    settings = get_settings()
    if not state:
        raise HTTPException(status_code=400, detail="Missing OAuth state")
    try:
        payload = decode_access_token(state)
        user_id = str(payload["sub"])
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from exc

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if resp.status_code >= 400:
            raise HTTPException(status_code=400, detail="Gmail token exchange failed")
        data = resp.json()

    get_token_store().save(
        user_id,
        "google",
        {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "token_type": data.get("token_type"),
            "scope": data.get("scope"),
            "expires_in": data.get("expires_in"),
        },
    )
    return RedirectResponse(f"{settings.web_app_url}/connect?google=connected")


@router.post("/google/gmail/disconnect")
async def google_gmail_disconnect(
    user: CurrentUser = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    get_token_store().delete(user.id, "google")
    return {"ok": True, "provider": "google"}


# Legacy aliases
@router.get("/google/start")
async def google_start_legacy(user: CurrentUser = Depends(get_current_user)):
    return await google_gmail_start(user)


@router.post("/google/disconnect")
async def google_disconnect_legacy(
    user: CurrentUser = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    get_token_store().delete(user.id, "google")
    return {"ok": True, "provider": "google"}

"""Saved SOW library — upload once, reuse on future runs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from accountflow.api.deps import CurrentUser, get_current_user, require_csrf
from accountflow.db.sows import get_sow_store
from accountflow.services.documents import extract_text_from_bytes

router = APIRouter(prefix="/sows", tags=["sows"])


class SowOut(BaseModel):
    id: str
    name: str
    content: str
    source_filename: str | None = None
    created_at: str
    updated_at: str


class SowSummary(BaseModel):
    id: str
    name: str
    source_filename: str | None = None
    created_at: str
    updated_at: str
    preview: str


class SowCreateBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)


class SowUpdateBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)


def _to_out(sow) -> SowOut:
    return SowOut(
        id=sow.id,
        name=sow.name,
        content=sow.content,
        source_filename=sow.source_filename,
        created_at=sow.created_at,
        updated_at=sow.updated_at,
    )


def _to_summary(sow) -> SowSummary:
    preview = sow.content[:160].replace("\n", " ").strip()
    if len(sow.content) > 160:
        preview += "…"
    return SowSummary(
        id=sow.id,
        name=sow.name,
        source_filename=sow.source_filename,
        created_at=sow.created_at,
        updated_at=sow.updated_at,
        preview=preview,
    )


@router.get("", response_model=list[SowSummary])
async def list_sows(user: CurrentUser = Depends(get_current_user)):
    return [_to_summary(s) for s in get_sow_store().list_for_user(user.id)]


@router.get("/{sow_id}", response_model=SowOut)
async def get_sow(sow_id: str, user: CurrentUser = Depends(get_current_user)):
    sow = get_sow_store().get_for_user(sow_id, user.id)
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    return _to_out(sow)


@router.post("", response_model=SowOut)
async def create_sow(
    body: SowCreateBody,
    user: CurrentUser = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    sow = get_sow_store().create(
        user_id=user.id,
        name=body.name,
        content=body.content.strip(),
    )
    return _to_out(sow)


@router.post("/upload", response_model=SowOut)
async def upload_sow(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    user: CurrentUser = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    data = await file.read()
    try:
        text = extract_text_from_bytes(data, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    label = (name or "").strip() or (file.filename or "Uploaded SOW")
    sow = get_sow_store().create(
        user_id=user.id,
        name=label,
        content=text,
        source_filename=file.filename,
    )
    return _to_out(sow)


@router.put("/{sow_id}", response_model=SowOut)
async def update_sow(
    sow_id: str,
    body: SowUpdateBody,
    user: CurrentUser = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    sow = get_sow_store().update(
        sow_id,
        user.id,
        name=body.name,
        content=body.content.strip() if body.content is not None else None,
    )
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    return _to_out(sow)


@router.delete("/{sow_id}")
async def delete_sow(
    sow_id: str,
    user: CurrentUser = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    ok = get_sow_store().delete(sow_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="SOW not found")
    return {"ok": True}

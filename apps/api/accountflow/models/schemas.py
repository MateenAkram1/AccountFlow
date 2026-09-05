from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class ScopeFlagType(str, Enum):
    IN_SCOPE = "IN_SCOPE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    TIMELINE_DRIFT = "TIMELINE_DRIFT"
    BUDGET_SIGNAL = "BUDGET_SIGNAL"
    SCOPE_CREEP = "SCOPE_CREEP"
    AMBIGUOUS = "AMBIGUOUS"


class Severity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Contact(BaseModel):
    name: str
    role: str | None = None
    email: str | None = None


class AccountDossier(BaseModel):
    deal_id: str
    company: str
    stage: str
    amount: float | None = None
    close_date: str | None = None
    contacts: list[Contact] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ScopeItem(BaseModel):
    id: str
    description: str
    section: str | None = None


class ScopeCorpus(BaseModel):
    source: str
    items: list[ScopeItem] = Field(default_factory=list)
    timeline: str | None = None
    budget_cap: float | None = None
    raw_text: str | None = None


class ScopeFlag(BaseModel):
    type: ScopeFlagType
    request: str
    evidence_quote: str
    sow_reference: str | None = None
    severity: Severity = Severity.NONE
    recommended_workflow: str | None = None


class ScopeReport(BaseModel):
    flags: list[ScopeFlag] = Field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None


class EmailDraft(BaseModel):
    mode: Literal["external", "internal", "manager"] = "external"
    to: list[str] = Field(default_factory=list)
    subject: str
    body: str
    evidence_quotes: list[str] = Field(default_factory=list)


class CRMUpdate(BaseModel):
    field: str
    value: str
    evidence_quote: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)


class TaskItem(BaseModel):
    summary: str
    description: str
    owner: str | None = None
    due_date: str | None = None
    evidence_quote: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)


class ActionPackage(BaseModel):
    summary: str
    emails: list[EmailDraft] = Field(default_factory=list)
    crm_updates: list[CRMUpdate] = Field(default_factory=list)
    tasks: list[TaskItem] = Field(default_factory=list)
    scope_report: ScopeReport | None = None


class GradeResult(BaseModel):
    passed: bool
    dimension: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    item: str | None = None


class GradeReport(BaseModel):
    results: list[GradeResult] = Field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)


class ApprovedSections(BaseModel):
    emails: bool = False
    crm: bool = False
    tasks: bool = False
    workflow: str | None = None
    jira_project_key: str | None = None


class ApprovedPayload(BaseModel):
    emails: list[EmailDraft] | None = None
    crm_updates: list[CRMUpdate] | None = None
    tasks: list[TaskItem] | None = None
    sections: ApprovedSections = Field(default_factory=ApprovedSections)
    jira_project_key: str | None = None


class ExecutionStepResult(BaseModel):
    step: str
    success: bool
    external_id: str | None = None
    message: str | None = None
    error: str | None = None


class ExecutionLog(BaseModel):
    run_id: str
    steps: list[ExecutionStepResult] = Field(default_factory=list)
    completed_at: datetime | None = None


class Transcript(BaseModel):
    text: str
    source: Literal["upload", "audio", "paste"] = "paste"
    duration_seconds: float | None = None


class RunStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class RunRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str | None = None
    status: RunStatus = RunStatus.PENDING
    transcript: Transcript | None = None
    account: AccountDossier | None = None
    scope_corpus: ScopeCorpus | None = None
    action_package: ActionPackage | None = None
    grade_report: GradeReport | None = None
    approved: ApprovedPayload | None = None
    execution_log: ExecutionLog | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())

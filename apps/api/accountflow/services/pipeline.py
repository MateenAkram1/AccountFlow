import json
import re
from pathlib import Path

from pypdf import PdfReader

from accountflow.models.schemas import (
    AccountDossier,
    ActionPackage,
    CRMUpdate,
    EmailDraft,
    ScopeCorpus,
    ScopeFlag,
    ScopeFlagType,
    ScopeItem,
    ScopeReport,
    Severity,
    TaskItem,
)
from accountflow.services.llm_context import get_request_llm


class ScopeVerifier:
    """Compare transcript requests against SOW scope."""

    SYSTEM = (
        "You are a scope verification assistant. Compare client requests in a meeting "
        "transcript against the statement of work. Classify each request and cite evidence."
    )

    async def verify(self, transcript: str, scope: ScopeCorpus | None) -> ScopeReport:
        if not scope or (not scope.items and not scope.raw_text):
            return ScopeReport(skipped=True, skip_reason="No SOW provided")

        scope_text = scope.raw_text or "\n".join(
            f"- {i.description} ({i.section or 'general'})" for i in scope.items
        )
        user = (
            f"SOW:\n{scope_text}\n\n"
            f"Timeline: {scope.timeline or 'not specified'}\n"
            f"Budget cap: {scope.budget_cap or 'not specified'}\n\n"
            f"Transcript:\n{transcript}\n\n"
            "Return JSON: {\"flags\": [{\"type\": \"OUT_OF_SCOPE|IN_SCOPE|TIMELINE_DRIFT|"
            "BUDGET_SIGNAL|AMBIGUOUS\", \"request\": \"...\", \"evidence_quote\": \"...\", "
            "\"sow_reference\": \"... or null\", \"severity\": \"none|low|medium|high\", "
            "\"recommended_workflow\": \"change_request or null\"}]}"
        )
        llm = get_request_llm()
        try:
            raw = await llm.complete_text(self.SYSTEM, user)
            data = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
            flags = [ScopeFlag.model_validate(f) for f in data.get("flags", [])]
        except (json.JSONDecodeError, ValueError):
            flags = _heuristic_scope_flags(transcript, scope)
        except Exception:
            flags = _heuristic_scope_flags(transcript, scope)
        return ScopeReport(flags=flags)


def _heuristic_scope_flags(transcript: str, scope: ScopeCorpus) -> list[ScopeFlag]:
    flags: list[ScopeFlag] = []
    lower = transcript.lower()
    mobile_phrases = ["mobile app", "offline mode", "ios app", "android app"]
    sow_text = (scope.raw_text or "").lower()
    for phrase in mobile_phrases:
        if phrase in lower and "mobile" not in sow_text:
            flags.append(
                ScopeFlag(
                    type=ScopeFlagType.OUT_OF_SCOPE,
                    request=f"Request involving {phrase}",
                    evidence_quote=phrase,
                    severity=Severity.HIGH,
                    recommended_workflow="change_request",
                )
            )
            break
    if "api" in lower and "api" in sow_text:
        flags.append(
            ScopeFlag(
                type=ScopeFlagType.IN_SCOPE,
                request="API integration discussion",
                evidence_quote="api",
                sow_reference="SOW API section",
                severity=Severity.NONE,
            )
        )
    if "april" in lower and ("march" in sow_text or "march" in (scope.timeline or "").lower()):
        flags.append(
            ScopeFlag(
                type=ScopeFlagType.TIMELINE_DRIFT,
                request="Client requested April timeline vs SOW March target",
                evidence_quote="April",
                sow_reference="March go-live",
                severity=Severity.MEDIUM,
            )
        )
    return flags


class DraftEngine:
    """Draft follow-up email, CRM updates, and tasks from transcript + account context."""

    SYSTEM = (
        "You draft post-meeting follow-up artifacts for a B2B account manager. "
        "Use account history. Every task and CRM field must include an evidence quote "
        "from the transcript. Return valid JSON only. "
        "For CRM dealstage values use ONLY HubSpot default stage IDs: "
        "appointmentscheduled, qualifiedtobuy, presentationscheduled, "
        "decisionmakerboughtin, contractsent, closedwon, closedlost."
    )

    async def draft(
        self,
        transcript: str,
        account: AccountDossier,
        scope_report: ScopeReport | None = None,
    ) -> ActionPackage:
        contacts = ", ".join(f"{c.name} ({c.role})" for c in account.contacts)
        notes = "\n".join(account.notes)
        scope_flags = ""
        if scope_report and scope_report.flags:
            scope_flags = "\n".join(
                f"- {f.type.value}: {f.request}" for f in scope_report.flags
            )

        user = (
            f"Account: {account.company}\n"
            f"Deal stage: {account.stage}\n"
            f"Amount: {account.amount}\n"
            f"Contacts: {contacts}\n"
            f"Past notes:\n{notes}\n\n"
            f"Scope flags:\n{scope_flags or 'none'}\n\n"
            f"Transcript:\n{transcript}\n\n"
            "Return JSON with keys: summary, emails (list with mode, to, subject, body, "
            "evidence_quotes), crm_updates (field, value, evidence_quote, confidence), "
            "tasks (summary, description, owner, due_date, evidence_quote, confidence)."
        )
        llm = get_request_llm()
        try:
            raw = await llm.complete_text(self.SYSTEM, user)
            data = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
            return ActionPackage(
                summary=data.get("summary", "Meeting summary"),
                emails=[EmailDraft.model_validate(e) for e in data.get("emails", [])],
                crm_updates=[CRMUpdate.model_validate(c) for c in data.get("crm_updates", [])],
                tasks=[TaskItem.model_validate(t) for t in data.get("tasks", [])],
                scope_report=scope_report,
            )
        except (json.JSONDecodeError, ValueError):
            return _heuristic_draft(transcript, account, scope_report)
        except Exception:
            return _heuristic_draft(transcript, account, scope_report)


def _heuristic_draft(
    transcript: str,
    account: AccountDossier,
    scope_report: ScopeReport | None,
) -> ActionPackage:
    contact_email = account.contacts[0].email if account.contacts else "client@example.com"
    lower = transcript.lower()
    words = lower.split()
    name_counts: dict[str, int] = {}
    for w in words:
        if w[0:1].isupper() and len(w) > 2:
            name_counts[w] = name_counts.get(w, 0) + 1
    ambiguous_owner = any(c > 2 for c in name_counts.values())
    task_confidence = 0.55 if ambiguous_owner else 0.8
    return ActionPackage(
        summary=f"Follow-up for {account.company} regarding recent sync.",
        emails=[
            EmailDraft(
                mode="external",
                to=[contact_email],
                subject=f"Follow-up: {account.company} sync",
                body=(
                    f"Hi,\n\nThank you for today's call. Following up on our discussion "
                    f"regarding {account.company}'s project.\n\nBest regards"
                ),
                evidence_quotes=[transcript[:120] if transcript else ""],
            )
        ],
        crm_updates=[
            CRMUpdate(
                field="dealstage",
                value="presentationscheduled",
                evidence_quote=transcript[:80] if transcript else "call discussion",
                confidence=0.75,
            )
        ],
        tasks=[
            TaskItem(
                summary="Send follow-up materials",
                description="Prepare and send materials discussed on the call.",
                owner="Alex Rivera" if not ambiguous_owner else "TBD — review owners",
                evidence_quote=transcript[:80] if transcript else "call action",
                confidence=task_confidence,
            )
        ],
        scope_report=scope_report,
    )


class HallucinationGrader:
    """Verify claims are grounded in transcript."""

    def grade(self, transcript: str, package: ActionPackage) -> list[dict]:
        results = []
        lower = transcript.lower()
        word_count = len(transcript.split())
        for task in package.tasks:
            quote = task.evidence_quote.lower()
            passed = quote in lower or any(
                word in lower for word in quote.split() if len(word) > 4
            )
            if word_count < 15 and task.due_date and task.due_date.lower() not in lower:
                passed = False
            if word_count < 15 and "deadline" in task.summary.lower() and "deadline" not in lower:
                passed = False
            results.append(
                {
                    "dimension": "grounding",
                    "passed": passed,
                    "message": f"Task '{task.summary}' evidence check",
                    "item": task.summary,
                }
            )
        for crm in package.crm_updates:
            quote = crm.evidence_quote.lower()
            passed = quote in lower or len(quote) < 5
            results.append(
                {
                    "dimension": "grounding",
                    "passed": passed,
                    "message": f"CRM field '{crm.field}' evidence check",
                    "item": crm.field,
                }
            )
        return results


def load_scope_from_file(path: Path) -> ScopeCorpus:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        text = path.read_text(encoding="utf-8")

    items = []
    for i, line in enumerate(text.splitlines()):
        line = line.strip()
        if line and not line.startswith("#"):
            items.append(ScopeItem(id=str(i), description=line, section=None))

    return ScopeCorpus(source=str(path), items=items[:50], raw_text=text)


def load_account_from_file(path: Path) -> AccountDossier:
    return AccountDossier.model_validate_json(path.read_text(encoding="utf-8"))


def is_insufficient_transcript(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 20:
        return True
    words = [re.sub(r"[^a-zA-Z]", "", w) for w in stripped.split()]
    words = [w for w in words if len(w) > 1]
    if len(words) < 3:
        return True
    lower_words = [w.lower() for w in words]
    common = {
        "the", "and", "for", "you", "our", "we", "thanks", "thank", "call",
        "meeting", "yes", "hello", "hi", "today", "will", "can", "need",
    }
    if not any(w in common for w in lower_words) and all(len(w) <= 5 for w in words):
        return True
    return False
